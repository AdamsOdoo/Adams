# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Post-migration: seed Goal 2B feature flags on upgraded databases."""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    defaults = env['shopify.backend']._feature_flag_seed_values()
    seeded = {}
    for field_name, value in defaults.items():
        cr.execute(
            f"UPDATE shopify_backend SET {field_name} = %s WHERE {field_name} IS NULL",
            [value],
        )
        seeded[field_name] = cr.rowcount
    _logger.info("Seeded Shopify feature flag defaults on upgrade: %s", seeded)
