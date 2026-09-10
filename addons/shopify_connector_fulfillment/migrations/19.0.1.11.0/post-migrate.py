"""Make fulfillment evidence company rules single-owner and fail closed.

Releases before 19.0.1.11.0 declared the evidence and evidence-line rule XML
IDs twice.  The first declaration was ``noupdate=1`` and permissive, so a warm
update could skip the later fail-closed definition.  Correct the existing rule
rows explicitly, then clear ``noupdate`` so the one canonical XML declaration
continues to own future updates.
"""

from odoo import SUPERUSER_ID, api


RULES = {
    'fulfillment_inbound_evidence_company_rule': {
        'name': 'Shopify Fulfillment Inbound Evidence: owning store company',
        'model': 'shopify.connector.fulfillment.inbound.evidence',
        'domain_force': "['&', ('company_id', 'in', company_ids), "
                        "('sec3_scope_quarantined', '=', False)]",
    },
    'fulfillment_inbound_evidence_line_company_rule': {
        'name': 'Shopify Fulfillment Inbound Evidence Line: owning store company',
        'model': 'shopify.connector.fulfillment.inbound.evidence.line',
        'domain_force': "['&', ('company_id', 'in', company_ids), "
                        "('sec3_scope_quarantined', '=', False)]",
    },
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Imd = env['ir.model.data'].sudo()
    for local_id, target in RULES.items():
        xmlid = 'shopify_connector_fulfillment.%s' % local_id
        rule = env.ref(xmlid, raise_if_not_found=False)
        rule = rule.sudo().exists() if rule else rule
        if not rule or rule._name != 'ir.rule' or len(rule) != 1:
            raise RuntimeError('Required fulfillment security rule is missing: %s' % xmlid)
        if rule.model_id.model != target['model']:
            raise RuntimeError('Fulfillment security rule targets the wrong model: %s' % xmlid)
        values = {
            'name': target['name'],
            'active': True,
            'global': True,
            'domain_force': target['domain_force'],
        }
        changed = {
            field: value
            for field, value in values.items()
            if rule[field] != value
        }
        if changed:
            rule.write(changed)
        metadata = Imd.search([
            ('module', '=', 'shopify_connector_fulfillment'),
            ('name', '=', local_id),
            ('model', '=', 'ir.rule'),
            ('res_id', '=', rule.id),
        ], limit=2)
        if len(metadata) != 1:
            raise RuntimeError('Fulfillment security XML ID is not unique: %s' % xmlid)
        if metadata.noupdate:
            metadata.write({'noupdate': False})
