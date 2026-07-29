"""Wave 5: put every existing credential row explicitly on the offline mode.

WHY THIS EXISTS AT ALL WHEN THE COLUMN HAS A DEFAULT

Odoo's `default=` applies to rows the ORM CREATES. A column added to a table
that already has rows is backfilled by Odoo with the field default at
`_auto_init` time in most cases -- but "in most cases" is not a property a
credential migration may rest on, and a NULL `auth_mode` would make
`_get_access_token` fall through to the offline branch by accident rather than
by decision. This states it.

WHAT IT DELIBERATELY DOES NOT DO

It never reinterprets a stored value. An existing `access_token` stays an
access token; nothing here copies it into `client_secret`, and nothing infers a
`client_id`. A merchant who was on the offline path before this upgrade is on
the offline path after it, with the same token, the same verification stamp and
the same store state. The client-credentials mode is opt-in through the setup
surface, never through an upgrade.

`client_credentials_present` is written as FALSE for the same reason: it is a
non-secret mirror of "this row has a client id and secret", and no pre-Wave-5
row does.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE shopify_connector_store_credential
           SET auth_mode = 'offline_access_token'
         WHERE auth_mode IS NULL
        """
    )
    backfilled = cr.rowcount
    cr.execute(
        """
        UPDATE shopify_connector_store_credential
           SET client_credentials_present = FALSE
         WHERE client_credentials_present IS NULL
        """
    )
    _logger.info(
        'Wave 5 credential migration: %s row(s) stated explicitly as the '
        'offline access-token mode. No stored token was reinterpreted.',
        backfilled,
    )
