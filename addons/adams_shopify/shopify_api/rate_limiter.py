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

    def wait_if_needed(self, estimated_cost):
        """Block until enough budget is available."""
        with self._lock:
            self._restore()
            if self.available < estimated_cost:
                wait = (estimated_cost - self.available) / self.restore_rate
                time.sleep(wait + 0.1)
                self._restore()
            self.available -= estimated_cost

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

    def _restore(self):
        now = time.monotonic()
        elapsed = now - self.last_update
        self.available = min(
            self.available + elapsed * self.restore_rate,
            self.bucket_size,
        )
        self.last_update = now
