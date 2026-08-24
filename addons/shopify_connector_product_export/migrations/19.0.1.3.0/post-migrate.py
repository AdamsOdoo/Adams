"""Invalidate readiness evidence for the v2 custom-ID definition.

The former boolean proves only that the legacy ``single_line_text_field``
definition was created.  Shopify's ``ProductIdentifierInput.customId``
requires an ``id`` definition, so carrying that boolean through an upgrade
would skip the definition preflight and make the first create preview fail at
Shopify.  Clearing it is safe and idempotent: the next reviewed create preview
performs the authoritative definition read and schedules the guarded bootstrap
when necessary.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE shopify_connector_store_settings
           SET product_export_binding_namespace_ready = FALSE
         WHERE product_export_binding_namespace_ready IS TRUE
        """
    )
