import time
import threading


class ShopifyRateLimiter:
    """Adaptive rate limiter using Shopify's cost-based throttle status.

    Thread-safe via a lock — multiple cron workers may share the same
    backend object in memory.
    """

    def __init__(self, bucket_size=1000, restore_rate=50):
        self.available = float(bucket_size)
        self.bucket_size = float(bucket_size)
        self.restore_rate = float(restore_rate)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()
        # Metrics
        self.total_requests = 0
        self.total_cost = 0.0
        self.total_wait_time = 0.0
        self.throttle_count = 0

    def wait_if_needed(self, estimated_cost):
        """Block until enough budget is available.

        Reserves the cost up-front under the lock, then releases the lock
        before sleeping so other threads can be served in parallel.
        """
        wait = 0.0
        with self._lock:
            self._restore()
            self.total_requests += 1
            self.total_cost += estimated_cost
            if self.available < estimated_cost:
                wait = (estimated_cost - self.available) / self.restore_rate
                wait += 0.1  # buffer
                self.total_wait_time += wait
                self.throttle_count += 1
            # Reserve the budget NOW (may go negative briefly; _restore() will
            # catch up). Doing this inside the lock prevents other threads
            # from double-spending the same capacity while we sleep.
            self.available -= estimated_cost
        if wait > 0:
            time.sleep(wait)

    def update_from_response(self, extensions):
        """Update state from actual Shopify throttle response."""
        cost = extensions.get('cost', {})
        throttle = cost.get('throttleStatus', {})
        if throttle:
            with self._lock:
                self.available = float(throttle.get('currentlyAvailable', self.available))
                self.bucket_size = float(throttle.get('maximumAvailable', self.bucket_size))
                self.restore_rate = float(throttle.get('restoreRate', self.restore_rate))
                self.last_update = time.monotonic()

    def get_metrics(self):
        """Return rate limiter metrics for monitoring."""
        with self._lock:
            self._restore()
            return {
                'available_budget': round(self.available, 1),
                'bucket_size': round(self.bucket_size, 1),
                'restore_rate': round(self.restore_rate, 1),
                'total_requests': self.total_requests,
                'total_cost': round(self.total_cost, 1),
                'total_wait_seconds': round(self.total_wait_time, 2),
                'throttle_count': self.throttle_count,
            }

    def _restore(self):
        now = time.monotonic()
        elapsed = now - self.last_update
        self.available = min(
            self.available + elapsed * self.restore_rate,
            self.bucket_size,
        )
        self.last_update = now
