"""Upgrade visible connector roles to the least-privilege implication graph.

Older installations may retain the historical direct User -> Reviewer edge.
The module data uses exact many-to-many replacement, and this migration mirrors
that contract through the ORM so a version-to-version upgrade has explicit,
repeatable evidence of the security transition.  It changes no user assignment,
credential, connector record, job, or Shopify state.
"""

import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    user = env.ref('shopify_connector_core.group_shopify_connector_user')
    admin = env.ref('shopify_connector_core.group_shopify_connector_admin')
    operator = env.ref('shopify_connector_core.group_shopify_connector_operator')
    reviewer = env.ref('shopify_connector_core.group_shopify_connector_reviewer')

    user.write({'implied_ids': [(6, 0, operator.ids)]})
    admin.write({'implied_ids': [(6, 0, (user | reviewer).ids)]})

    _logger.info(
        'Connector role upgrade: User now implies Operator only; '
        'Administrator implies User and Reviewer. Existing user assignments '
        'were preserved and no connector or Shopify operation was performed.'
    )
