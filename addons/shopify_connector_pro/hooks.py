# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, api


def _seed_feature_flag_defaults(env):
    """Seed new Goal 2B feature columns explicitly on existing rows."""
    Backend = env['shopify.backend'].sudo()
    defaults = Backend._feature_flag_seed_values()
    for field_name, value in defaults.items():
        env.cr.execute(
            f"UPDATE shopify_backend SET {field_name} = %s WHERE {field_name} IS NULL",
            [value],
        )


def post_init_hook(env_or_cr):
    """Ensure fresh installs have explicit values for new feature flags."""
    if hasattr(env_or_cr, '__getitem__'):
        env = env_or_cr
    else:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    _seed_feature_flag_defaults(env)
