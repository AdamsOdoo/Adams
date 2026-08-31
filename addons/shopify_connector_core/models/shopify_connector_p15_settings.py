"""P15 settings-row uniqueness and generation-fenced service writes."""

from psycopg2 import IntegrityError

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from .shopify_connector_p15_shared import (
    P15_EDITABLE_SETTINGS_GROUP_FIELDS,
    P15_SERVICE_SENTINEL,
    P15_SERVICE_SENTINEL_CONTEXT,
    P15_SETTINGS_GROUP_FIELDS,
)
from .shopify_connector_store_settings_security import (
    SETTINGS_SERVICE_SENTINEL,
    SETTINGS_SERVICE_SENTINEL_CONTEXT,
    SETTINGS_WRITE_CONTEXT,
)


class ShopifyConnectorP15Settings(models.Model):
    """One effective settings row plus generation-fenced service writes."""

    _inherit = "shopify.connector.store.settings"

    @api.model
    def _p15_lock_generation(self, settings):
        settings.ensure_one()
        settings.flush_recordset()
        self.env.cr.execute(
            "SELECT configuration_generation "
            "FROM shopify_connector_store_settings WHERE id = %s FOR UPDATE",
            (settings.id,),
        )
        row = self.env.cr.fetchone()
        if not row:
            raise UserError(_("The store settings record is no longer available."))
        settings.invalidate_recordset(["configuration_generation"])
        return int(row[0] or 0)

    @api.model
    def _p15_get_or_create(self, store, *, lock_store=True):
        """Return exactly one settings row, creating only the structural row.

        The store-row lock is the parent serialization point.  The existing
        unique(store_id) constraint remains the final defence for historic or
        non-P15 writers; no duplicate row is copied or merged here.
        """

        store.ensure_one()
        if lock_store:
            store._lock_store_for_lifecycle()
        Settings = self.env["shopify.connector.store.settings"].sudo()
        rows = Settings.search(
            [("store_id", "=", store.id)], order="id asc", limit=2,
        )
        if len(rows) > 1:
            raise ValidationError(_(
                "More than one settings row exists for this store; resolve "
                "the duplicate before continuing."
            ))
        if not rows:
            try:
                with self.env.cr.savepoint():
                    rows = Settings._settings_service_create(
                        "_canonical_settings", {"store_id": store.id},
                    )
            except IntegrityError as exc:
                # A legacy writer raced the structural insert.  The unique
                # constraint is authoritative; surface a safe conflict after
                # rolling back only the savepoint in the caller if available.
                raise UserError(_(
                    "Store settings are being initialized; reload and try "
                    "again."
                )) from exc
        return rows.with_env(self.env)

    def _p15_service_write(self, values):
        """Private P15 write capability; callers validate the field allowlist.

        The existing settings and P09 mode sentinels are both installed by
        object identity.  A serialized RPC context can copy neither, while
        migrations/root fixtures retain their existing compatibility paths.
        """

        if not isinstance(values, dict) or not values:
            raise ValidationError(_("A settings change is required."))
        surface = self._v2_mode_surface().browse(self.ids)
        surface = surface.with_context(**{
            SETTINGS_WRITE_CONTEXT: "_setup",
            SETTINGS_SERVICE_SENTINEL_CONTEXT: SETTINGS_SERVICE_SENTINEL,
            P15_SERVICE_SENTINEL_CONTEXT: P15_SERVICE_SENTINEL,
        })
        return surface.write(values)

    def write(self, vals):
        """Advance configuration generation for ordinary editable writes.

        The generation is not caller-selectable.  The P15 grouped service
        writes it atomically with the validated values; an ordinary legacy
        editable settings write gets a serialized monotonic bump here.  Root,
        migration, and existing connector system writers remain untouched.
        """

        tracked = set(vals or {}).intersection(
            set().union(*P15_SETTINGS_GROUP_FIELDS.values())
        )
        service_write = (
            self.env.context.get(P15_SERVICE_SENTINEL_CONTEXT)
            is P15_SERVICE_SENTINEL
        )
        before = {}
        if tracked and not self.env.su and not service_write:
            for record in self:
                before[record.id] = {
                    name: record[name] for name in tracked if name in record._fields
                }
            self.flush_recordset()
            self.env.cr.execute(
                "SELECT id FROM shopify_connector_store_settings "
                "WHERE id IN %s ORDER BY id FOR UPDATE",
                (tuple(self.ids),),
            )
        result = super().write(vals)
        if tracked and not self.env.su and not service_write:
            changed = False
            for record in self:
                old = before.get(record.id, {})
                if any(old.get(name) != record[name] for name in tracked):
                    changed = True
                    break
            if changed and "configuration_generation" in self._fields:
                self.flush_recordset()
                self.env.cr.execute(
                    "SELECT MAX(configuration_generation) "
                    "FROM shopify_connector_store_settings WHERE id IN %s",
                    (tuple(self.ids),),
                )
                generation = int(self.env.cr.fetchone()[0] or 0) + 1
                self._p15_service_write({
                    "configuration_generation": generation,
                })
        return result
