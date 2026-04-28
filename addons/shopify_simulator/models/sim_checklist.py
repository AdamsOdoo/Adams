# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Validation Checklist — pre-flight checks before running connector sync.

Checks if the simulator has enough data to support a successful connector
import/sync cycle. Runs from the UI and displays pass/fail results.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# ── Check definitions ─────────────────────────────────────
# Each check is (key, name, check_func(env, config) → (bool, str))

def _check_has_products(env, config):
    count = env['sim.shopify.product'].search_count(
        [('config_id', '=', config.id), ('status', '=', 'ACTIVE')])
    return count > 0, f'{count} active products'


def _check_has_customers(env, config):
    count = env['sim.shopify.customer'].search_count(
        [('config_id', '=', config.id)])
    return count > 0, f'{count} customers'


def _check_has_orders(env, config):
    count = env['sim.shopify.order'].search_count(
        [('config_id', '=', config.id)])
    return count > 0, f'{count} orders'


def _check_has_locations(env, config):
    count = env['sim.shopify.location'].search_count(
        [('config_id', '=', config.id), ('is_active', '=', True)])
    return count > 0, f'{count} active locations'


def _check_has_primary_location(env, config):
    count = env['sim.shopify.location'].search_count(
        [('config_id', '=', config.id), ('is_primary', '=', True)])
    return count == 1, 'primary location exists' if count == 1 else 'NO primary location!'


def _check_has_inventory(env, config):
    count = env['sim.shopify.inventory.level'].search_count(
        [('config_id', '=', config.id)])
    return count > 0, f'{count} inventory levels'


def _check_rate_limit_ok(env, config):
    ok = config.rate_limit_available > 100
    return ok, f'{config.rate_limit_available:.0f} available (need >100)'


def _check_error_mode_off(env, config):
    ok = config.error_mode == 'none'
    return ok, f'mode: {config.error_mode}'


def _check_backend_linked(env, config):
    ok = bool(config.backend_id and config.backend_id.use_simulator)
    return ok, 'backend linked + simulator mode ON' if ok else 'backend NOT in simulator mode'


def _check_access_token_match(env, config):
    if not config.backend_id:
        return False, 'no backend linked'
    ok = config.access_token == config.backend_id.access_token
    return ok, 'tokens match' if ok else 'TOKEN MISMATCH!'


CHECKS = [
    ('backend_linked', 'Backend Linked', _check_backend_linked),
    ('token_match', 'Access Token Match', _check_access_token_match),
    ('has_products', 'Has Products', _check_has_products),
    ('has_customers', 'Has Customers', _check_has_customers),
    ('has_orders', 'Has Orders', _check_has_orders),
    ('has_locations', 'Has Active Locations', _check_has_locations),
    ('primary_location', 'Primary Location Exists', _check_has_primary_location),
    ('has_inventory', 'Has Inventory Levels', _check_has_inventory),
    ('rate_limit_ok', 'Rate Limit Sufficient', _check_rate_limit_ok),
    ('error_mode_off', 'Error Mode: Normal', _check_error_mode_off),
]


class SimChecklist(models.TransientModel):
    _name = 'sim.checklist'
    _description = 'Simulator Validation Checklist'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade',
        string='Simulator Config',
        default=lambda self: self.env.context.get('default_config_id'),
    )
    result_html = fields.Html(
        string='Checklist Results', readonly=True, sanitize=False,
    )
    all_passed = fields.Boolean(string='All Passed', readonly=True)

    @api.onchange('config_id')
    def _onchange_run_checks(self):
        if self.config_id:
            self._run_checks()

    def action_run_checks(self):
        """Run all checks and update results."""
        self.ensure_one()
        self._run_checks()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sim.checklist',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _run_checks(self):
        """Execute all validation checks and build HTML report."""
        config = self.config_id
        if not config:
            self.result_html = '<p>Select a config to run checks.</p>'
            self.all_passed = False
            return

        lines = []
        all_ok = True
        for key, name, check_func in CHECKS:
            try:
                passed, detail = check_func(self.env, config)
            except Exception as exc:
                passed, detail = False, f'Error: {exc}'
            icon = '&#x2705;' if passed else '&#x274C;'
            color = '#28a745' if passed else '#dc3545'
            lines.append(
                f'<tr>'
                f'<td style="padding:4px 8px;">{icon}</td>'
                f'<td style="padding:4px 8px;color:{color};font-weight:bold;">'
                f'{name}</td>'
                f'<td style="padding:4px 8px;">{detail}</td>'
                f'</tr>'
            )
            if not passed:
                all_ok = False

        status_color = '#28a745' if all_ok else '#dc3545'
        status_text = 'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'
        html = (
            f'<div style="margin-bottom:12px;">'
            f'<strong style="color:{status_color};font-size:14px;">'
            f'{status_text}</strong></div>'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr style="background:#f8f9fa;">'
            f'<th style="padding:4px 8px;width:30px;"></th>'
            f'<th style="padding:4px 8px;text-align:left;">Check</th>'
            f'<th style="padding:4px 8px;text-align:left;">Detail</th>'
            f'</tr></thead><tbody>'
            + ''.join(lines)
            + '</tbody></table>'
        )
        self.result_html = html
        self.all_passed = all_ok
