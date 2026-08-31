"""P15 settings-row uniqueness and generation-fenced service writes."""

import json

from psycopg2 import IntegrityError

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from .shopify_connector_p15_shared import (
    P15_CONFIGURATION_POLICY_FIELDS,
    P15_SERVICE_SENTINEL,
    P15_SERVICE_SENTINEL_CONTEXT,
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
        """Bump each changed policy row once, regardless of write surface."""

        vals = dict(vals or {})
        # Generation is derived evidence, never a caller-selected setting.
        vals.pop("configuration_generation", None)
        tracked = tuple(sorted(
            set(vals).intersection(P15_CONFIGURATION_POLICY_FIELDS)
            .intersection(self._fields)
        ))
        before = {}
        if tracked and self:
            self.flush_recordset()
            self.env.cr.execute(
                "SELECT id FROM shopify_connector_store_settings "
                "WHERE id IN %s ORDER BY id FOR UPDATE",
                (tuple(sorted(self.ids)),),
            )
            locked = {row[0] for row in self.env.cr.fetchall()}
            if locked != set(self.ids):
                raise UserError(_(
                    "A store settings record changed while it was being saved."
                ))
            self.invalidate_recordset(list(tracked))
            for record in self.sorted("id"):
                before[record.id] = {
                    name: self._p15_generation_value(record[name])
                    for name in tracked
                }
        if not vals:
            return True
        result = super().write(vals)
        changed_ids = []
        if tracked:
            self.invalidate_recordset(list(tracked))
            for record in self.sorted("id"):
                if any(
                    before[record.id][name]
                    != self._p15_generation_value(record[name])
                    for name in tracked
                ):
                    changed_ids.append(record.id)
        for record_id in changed_ids:
            self.env.cr.execute(
                "UPDATE shopify_connector_store_settings "
                "SET configuration_generation = "
                "COALESCE(configuration_generation, 0) + 1 "
                "WHERE id = %s",
                (record_id,),
            )
        if changed_ids:
            self.invalidate_recordset(["configuration_generation"])
        return result

    @api.model
    def _p15_generation_value(self, value):
        """Normalize policy values for exact pre/post comparisons."""
        if hasattr(value, "ids"):
            return tuple(value.ids)
        if isinstance(value, dict):
            return json.dumps(
                value, sort_keys=True, separators=(",", ":"), default=str,
            )
        if isinstance(value, list):
            return json.dumps(
                value, sort_keys=True, separators=(",", ":"), default=str,
            )
        return value
