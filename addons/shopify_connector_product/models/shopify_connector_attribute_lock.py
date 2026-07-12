from odoo import api, fields, models

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


class ShopifyConnectorAttributeLock(models.Model):
    """Connector-owned singleton serialization lock for global attribute
    resolve/create (Task 010B, D-010B-2).

    ``product.attribute`` and ``product.attribute.value`` are
    database-global and carry no upstream uniqueness constraint (verified
    against the Odoo 19.0 source: ``addons/product/models/
    product_attribute.py`` declares only a display-type CHECK, and
    ``product_attribute_value.py`` declares no name/attribute uniqueness),
    so two concurrent product imports could each observe "no such
    attribute" and each create one. A savepoint does not prevent this: a
    savepoint isolates rollback, not visibility, so two open transactions
    never see each other's uncommitted rows.

    The race is therefore prevented at creation time by a database-backed
    serialization lock. This model owns a single seeded ``noupdate=1`` row
    (``data/shopify_connector_attribute_lock.xml``). Before any global
    attribute resolve/create, the importer acquires that exact row with
    Odoo 19's official ``try_lock_for_update()`` primitive
    (``odoo/orm/models.py``: ``SELECT ... FOR UPDATE SKIP LOCKED``,
    non-blocking, returns the recordset of rows it could lock, releases on
    transaction commit/rollback). Because it is a single global row -- not
    per store -- it serializes attribute resolve/create across all stores,
    which is the correct scope since ``product.attribute`` is
    database-global.

    ``try_lock_for_update()`` uses ``SKIP LOCKED`` (never ``NOWAIT``), so a
    row already locked by a concurrent transaction is skipped and the call
    returns an empty recordset rather than blocking or raising. The
    importer therefore never proceeds with an unprotected global attribute
    creation: when the lock is unavailable it raises
    ``concurrency_race_conflict`` (an auto-retry class -- see
    ``shopify_connector_job_dispatch.py``), so the import backs off and, on
    a later attempt, acquires the lock, re-resolves, and reuses the first
    transaction's committed attribute instead of creating a duplicate.

    The lock is transaction-scoped, not critical-section-scoped: PostgreSQL
    holds a ``FOR UPDATE`` row lock until the acquiring transaction commits
    or rolls back, and releasing the importer's per-product ``savepoint``
    does NOT release it. Once acquired it therefore serializes the remaining
    database work of the holding transaction against any other transaction
    that needs the same row -- the global-attribute critical section and,
    because a ``run_drain`` batch may run several jobs in one transaction,
    potentially the rest of that batch. The Shopify request and any image
    download always happen BEFORE the lock is acquired, never while it is
    held, so network latency is never inside the lock. This is a
    correctness-first choice (guaranteeing exactly one attribute); the
    lock-hold duration and its throughput impact are an open runtime
    measurement obligation (Odoo.sh / dev-store), not a proven property.

    Stateless of any business data: the single row is a pure mutex anchor.
    It is never created, written, or unlinked at runtime -- only the
    ``noupdate`` seed writes it, and imports only read-lock it.
    """

    _name = 'shopify.connector.attribute.lock'
    _description = 'Shopify Connector Global Attribute Serialization Lock'

    name = fields.Char(
        required=True,
        readonly=True,
        default='Shopify Connector Global Attribute Lock',
    )

    @api.model
    def _acquire_or_raise(self):
        """Acquire the singleton lock row for the current transaction.

        Returns the locked ``shopify.connector.attribute.lock`` recordset.
        Uses ``try_lock_for_update()`` (``FOR UPDATE SKIP LOCKED``,
        non-blocking): if the row is already locked by a concurrent
        transaction the call returns empty and this method raises
        ``JobHandlerError('concurrency_race_conflict', ...)`` -- an
        auto-retry class -- so the import never creates a global attribute
        without first holding the lock.

        Raises ``JobHandlerError('data_shape_schema_mismatch', ...)`` if the
        seeded lock row is missing (a module-data/install problem, not a
        concurrency event).
        """
        row = self.search([], limit=1)
        if not row:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'The connector global attribute serialization lock row is '
                'missing -- the module data seed did not load. Attribute '
                'creation is blocked rather than run unprotected.',
            )
        locked = row.try_lock_for_update()
        if not locked:
            raise JobHandlerError(
                'concurrency_race_conflict',
                'Another product import is creating shared product '
                'attributes right now. This import will retry shortly '
                'rather than risk creating a duplicate global attribute.',
            )
        return locked
