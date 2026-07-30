"""Batch 1 correction: retire every token cache that cannot prove its provenance.

WHAT THIS MIGRATION IS FOR

`19.0.1.16.0` shipped a cached 24-hour access token whose only link to the
credential that minted it was `credential_id`. A rotation updates the credential
row in place, so that relation stayed valid after the identity had changed, and a
token minted from a superseded secret remained readable for up to 24 hours. The
correction adds `credential_epoch` and `auth_mode` to the cache row and makes
every read compare them.

A cache row written by the vulnerable implementation carries neither value, and
nothing can reconstruct them: the row cannot say which secret it came from, which
is precisely the defect. Such a row must therefore not be blessed with the
current epoch on upgrade -- that would launder exactly the tokens this correction
exists to reject. It is deleted instead.

Deleting it is safe and costs a merchant nothing observable. The token is
ephemeral by construction; the next Shopify call re-mints one from the credential
that is actually configured, through the corrected path, with provable
provenance. **No Shopify request is made during the upgrade** -- this is a
`DELETE`, and the re-mint happens later, on a live call, exactly where every
other exchange happens.

WHY THIS IS ALSO NOT A REPEAT OF `19.0.1.16.0`'s MISTAKE

That script's own `UPDATE ... WHERE auth_mode IS NULL` could never match a row.
`auth_mode` is `required=True` with a default, so Odoo's `_auto_init` adds the
column, backfills the default into every existing row and applies `NOT NULL`
*before* any `post-migrate` script runs -- the predicate was false by
construction and the script reported "0 row(s)" while claiming to have stated
something. It was harmless, and it was not evidence of anything.

This script's predicate CAN be true and is tested directly:
`test_client_credentials.py::TestVulnerableCacheUpgrade` seeds a pre-correction
cache row and asserts it is gone afterwards, and asserts that a second run of the
same script changes nothing (idempotency).

WHAT IT DELIBERATELY DOES NOT TOUCH

Offline-mode credentials, in any respect. No `access_token` is read, copied,
reinterpreted or moved; no `client_id` is inferred; no store state, verification
stamp or connection generation is written. A merchant on the offline path before
this upgrade is on it afterwards with the same token bytes, and the byte
preservation is asserted by `test_offline_token_bytes_survive_the_upgrade`.

`credential_epoch` on the credential row needs no backfill here for the same
reason `auth_mode` did not: it is `required=True, default=0`, so `_auto_init`
has already written `0` into every pre-existing row and constrained it non-null.
Every such credential therefore starts at epoch 0 and advances from its next
sanctioned mutation, which is exactly the intended meaning -- "this identity has
not been superseded since the upgrade". That is stated here rather than
re-asserted in SQL, because a predicate that cannot be true is not a statement.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    # `credential_epoch = 0` on a CACHE row is the fingerprint of the vulnerable
    # writer: `_auto_init` backfilled the new column with the field default, and
    # the corrected `_write_token_cache` never writes 0 -- the first sanctioned
    # mutation of any credential moves its epoch to 1, so every provable cache
    # row carries 1 or more. Rows whose token or expiry is missing are swept with
    # them: they can authenticate nothing and only exist to be misread.
    cr.execute(
        """
        DELETE FROM shopify_connector_store_access_token
              WHERE credential_epoch IS NULL
                 OR credential_epoch = 0
                 OR auth_mode IS NULL
                 OR access_token IS NULL
                 OR expires_at IS NULL
        """
    )
    removed = cr.rowcount
    if removed:
        _logger.warning(
            'Batch 1 credential-provenance correction: %s cached Shopify '
            'access token(s) were removed because they predate the provenance '
            'columns and cannot prove which credential minted them. A new '
            'token is obtained on the next Shopify call; no credential, and no '
            'offline access token, was changed.',
            removed,
        )
    else:
        _logger.info(
            'Batch 1 credential-provenance correction: no unprovable cached '
            'access tokens were present.'
        )
