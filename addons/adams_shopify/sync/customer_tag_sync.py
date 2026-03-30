import logging

from odoo import fields

_logger = logging.getLogger(__name__)


class CustomerTagSync:
    """Sync customer tags from Shopify into the shopify.customer.tag model."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend

    def sync_tags_from_bindings(self):
        """Parse tags from existing customer bindings and create tag records."""
        bindings = self.env['shopify.customer.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('sync_status', '=', 'synced'),
        ])

        tag_partner_map = {}  # {tag_name: [partner_ids]}

        for binding in bindings:
            tags_str = binding.shopify_tags or ''
            if not tags_str:
                continue
            partner = binding.odoo_id
            if not partner:
                continue
            tags = [t.strip() for t in tags_str.split(',') if t.strip()]
            for tag_name in tags:
                tag_partner_map.setdefault(tag_name, []).append(partner.id)

        created = updated = 0
        for tag_name, partner_ids in tag_partner_map.items():
            existing = self.env['shopify.customer.tag'].search([
                ('backend_id', '=', self.backend.id),
                ('name', '=', tag_name),
            ], limit=1)

            if existing:
                # Add any new partners
                current_ids = set(existing.partner_ids.ids)
                new_ids = set(partner_ids) - current_ids
                if new_ids:
                    existing.write({
                        'partner_ids': [(4, pid) for pid in new_ids],
                    })
                    updated += 1
            else:
                self.env['shopify.customer.tag'].create({
                    'backend_id': self.backend.id,
                    'name': tag_name,
                    'partner_ids': [(6, 0, list(set(partner_ids)))],
                })
                created += 1

        _logger.info("Customer tag sync: %d created, %d updated", created, updated)
        return created, updated
