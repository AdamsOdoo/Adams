# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for simulator error modes and chaos engineering features.
"""
from .common import SimulatorTestCase


class TestErrorModeConfig(SimulatorTestCase):
    """Test error mode configuration on sim.shopify.config."""

    def test_default_error_mode_is_none(self):
        """Default error mode should be 'none'."""
        self.assertEqual(self.sim_config.error_mode, 'none')

    def test_error_mode_selection_values(self):
        """Should accept all valid error mode values."""
        valid_modes = ['none', 'random_errors', 'always_error',
                       'rate_limit', 'timeout', 'user_errors']
        for mode in valid_modes:
            self.sim_config.write({'error_mode': mode})
            self.sim_config.invalidate_recordset()
            self.assertEqual(self.sim_config.error_mode, mode)

    def test_rate_limit_budget_tracking(self):
        """Rate limit budget should decrease with each extensions build."""
        self.sim_config.write({'rate_limit_available': 100.0})
        self.sim_config._build_extensions(50)
        self.sim_config.invalidate_recordset()
        # actualCost = 50 * 0.8 = 40
        self.assertAlmostEqual(self.sim_config.rate_limit_available, 60.0, places=1)

    def test_rate_limit_budget_floors_at_zero(self):
        """Budget should not go below zero."""
        self.sim_config.write({'rate_limit_available': 5.0})
        self.sim_config._build_extensions(100)
        self.sim_config.invalidate_recordset()
        self.assertEqual(self.sim_config.rate_limit_available, 0.0)


class TestSimulatorClientFactory(SimulatorTestCase):
    """Test that _make_api_client returns correct client type."""

    def test_simulator_client_has_rate_limiter(self):
        """SimulatorClient should have a real rate limiter."""
        from odoo.addons.shopify_connector_pro.shopify_api.client import ShopifyRateLimiter
        client = self.backend._make_api_client()
        self.assertIsInstance(client.rate_limiter, ShopifyRateLimiter)

    def test_simulator_client_has_noop_circuit_breaker(self):
        """SimulatorClient should have a no-op circuit breaker."""
        from ..lib.simulator_client import _SimCircuitBreaker
        client = self.backend._make_api_client()
        self.assertIsInstance(client.circuit_breaker, _SimCircuitBreaker)
        # Should always allow execution
        self.assertTrue(client.circuit_breaker.can_execute())

    def test_simulator_client_endpoint_uses_sim_url(self):
        """SimulatorClient endpoint should point to the simulator."""
        client = self.backend._make_api_client()
        self.assertIn('/shopify-sim/', client.endpoint)
        self.assertIn('graphql.json', client.endpoint)

    def test_simulator_client_session_has_token(self):
        """Session should include the access token header."""
        client = self.backend._make_api_client()
        token = client._session.headers.get('X-Shopify-Access-Token')
        self.assertEqual(token, self.backend.access_token)
