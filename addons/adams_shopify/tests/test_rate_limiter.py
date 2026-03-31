import time
import unittest

from ..shopify_api.rate_limiter import ShopifyRateLimiter


class TestRateLimiter(unittest.TestCase):

    def test_initial_state(self):
        """Rate limiter should start with full bucket."""
        rl = ShopifyRateLimiter(bucket_size=1000, restore_rate=50)
        self.assertEqual(rl.available, 1000.0)
        self.assertEqual(rl.bucket_size, 1000.0)
        self.assertEqual(rl.restore_rate, 50.0)

    def test_wait_if_needed_no_wait(self):
        """Should not wait when bucket has enough capacity."""
        rl = ShopifyRateLimiter(bucket_size=1000, restore_rate=50)
        start = time.monotonic()
        rl.wait_if_needed(10)
        elapsed = time.monotonic() - start
        # Should be nearly instant (< 50ms)
        self.assertLess(elapsed, 0.05)

    def test_wait_if_needed_deducts_cost(self):
        """Should deduct the estimated cost from available budget."""
        rl = ShopifyRateLimiter(bucket_size=1000, restore_rate=50)
        rl.wait_if_needed(100)
        # Available should be approximately 900 (minus small timing variance)
        self.assertLess(rl.available, 910)
        self.assertGreater(rl.available, 880)

    def test_update_from_response(self):
        """Should update state from Shopify throttle response."""
        rl = ShopifyRateLimiter(bucket_size=1000, restore_rate=50)
        rl.update_from_response({
            'cost': {
                'throttleStatus': {
                    'currentlyAvailable': 500,
                    'maximumAvailable': 2000,
                    'restoreRate': 100,
                },
            },
        })
        self.assertEqual(rl.available, 500.0)
        self.assertEqual(rl.bucket_size, 2000.0)
        self.assertEqual(rl.restore_rate, 100.0)

    def test_update_from_empty_response(self):
        """Should handle empty extensions gracefully."""
        rl = ShopifyRateLimiter(bucket_size=1000, restore_rate=50)
        rl.update_from_response({})
        self.assertEqual(rl.bucket_size, 1000.0)

    def test_restore_over_time(self):
        """Available points should restore over time."""
        rl = ShopifyRateLimiter(bucket_size=100, restore_rate=1000)
        rl.wait_if_needed(50)
        # After consuming 50, wait a tiny bit, should restore some
        time.sleep(0.05)
        rl._restore()
        # Should have restored ~50 points (1000/s * 0.05s)
        self.assertGreater(rl.available, 80)

    def test_bucket_cap(self):
        """Available should never exceed bucket_size."""
        rl = ShopifyRateLimiter(bucket_size=100, restore_rate=50)
        time.sleep(0.1)
        rl._restore()
        self.assertLessEqual(rl.available, 100.0)
