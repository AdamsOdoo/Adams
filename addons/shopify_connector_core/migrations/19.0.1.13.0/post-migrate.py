"""SEC-2: rename the retained sweep cron away from masking wording.

The cron record is `noupdate="1"`, so an existing install keeps whatever name
it was created with. Its code (`model.run_sweep()`) is unchanged, but the job
it performs no longer masks any business record -- it redacts aged log/audit
evidence only. The displayed name is corrected here so an operator reading
the scheduled-actions list is not told the connector masks customer data.

`ir.cron` carries no `name` column of its own: Odoo 19 delegates it through
`_inherits = {'ir.actions.server': 'ir_actions_server_id'}`
(`odoo/addons/base/models/ir_cron.py` L104, odoo/odoo@19.0
30bde9ff758834a4912c5ae55843d3a7dad849f1), so the stored name lives on
`ir_act_server` and the update has to follow that foreign key. That column is
`jsonb` because the field is translatable, so the value is rebuilt rather than
assigned as text. Any stored translation of the *old* technical name is
dropped with it -- it named a behaviour that no longer exists, so carrying it
forward would leave a translated claim that the connector masks customer data.

Idempotent: renaming an already-renamed record is a no-op.
"""

CRON_NAME = 'Shopify Connector: Log Redaction Sweep'


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_act_server
           SET name = jsonb_build_object('en_US', %(name)s::text)
          FROM ir_cron, ir_model_data
         WHERE ir_model_data.module = 'shopify_connector_core'
           AND ir_model_data.name = 'ir_cron_shopify_connector_pii_retention'
           AND ir_model_data.model = 'ir.cron'
           AND ir_cron.id = ir_model_data.res_id
           AND ir_act_server.id = ir_cron.ir_actions_server_id
           AND ir_act_server.name ->> 'en_US' IS DISTINCT FROM %(name)s::text
        """,
        {'name': CRON_NAME},
    )
