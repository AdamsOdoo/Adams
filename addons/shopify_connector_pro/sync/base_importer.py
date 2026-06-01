# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields
from odoo.tools import config

_logger = logging.getLogger(__name__)


class BaseImporter:
    """Base class for Shopify → Odoo import sync operations."""

    entity_name = ''  # Override: 'product', 'customer', etc.
    binding_model = ''  # Override: 'shopify.product.binding'

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.client = backend._make_api_client()

    def _create_log(self, operation='import'):
        return self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': self.entity_name,
            'operation': operation,
        })

    def _find_binding(self, shopify_id):
        """Find existing binding by shopify_id."""
        return self.env[self.binding_model].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', shopify_id),
        ], limit=1)

    def import_batch(self, shopify_nodes):
        """Import a batch of Shopify nodes.

        Args:
            shopify_nodes: iterable of Shopify GraphQL node dicts.

        Returns:
            Tuple of (success, errors, skipped) counts.
        """
        log = self._create_log()
        success = errors = skipped = 0
        error_details = []

        for node in shopify_nodes:
            shopify_id = node.get('id', '')
            try:
                new_checksum = self._compute_shopify_checksum(node)
                binding = self._find_binding(shopify_id)

                if binding and new_checksum == binding.sync_checksum:
                    skipped += 1
                    continue

                # Use savepoint so IntegrityError doesn't kill the whole batch
                with self.env.cr.savepoint():
                    self._import_one(node, binding)
                success += 1
            except Exception as e:
                error_name = type(e).__name__
                if 'IntegrityError' in error_name or 'UniqueViolation' in error_name:
                    _logger.info("Duplicate binding for %s %s — skipping", self.entity_name, shopify_id)
                    skipped += 1
                else:
                    # Under test mode, re-raise non-Integrity exceptions
                    # so field-name bugs and programming errors fail CI
                    # instead of being silently swallowed.
                    if config['test_enable']:
                        raise
                    _logger.warning(
                        "Import failed for %s %s: %s",
                        self.entity_name, shopify_id, e,
                    )
                    errors += 1
                    error_details.append(f"{shopify_id}: {e}")

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)

        # Surface import errors as a warning activity on the backend
        # so the merchant sees them in the UI (not just server logs).
        if errors > 0:
            detail_str = '\n'.join(error_details)
            summary = "Shopify %s import: %d error(s)" % (
                self.entity_name, errors,
            )
            note = "%d of %d %s failed to import.\n\n%s" % (
                errors,
                success + errors + skipped,
                self.entity_name,
                detail_str,
            )
            self.backend.activity_schedule(
                'mail.mail_activity_data_warning',
                summary=summary,
                note=note,
            )

        return success, errors, skipped

    def _compute_shopify_checksum(self, node):
        """Override: compute checksum from Shopify data."""
        raise NotImplementedError

    def _import_one(self, node, existing_binding=None):
        """Override: import a single Shopify node into Odoo."""
        raise NotImplementedError

    # ── Field mapping helpers ──────────────────────────────────────

    def _apply_import_mappings(self, vals, node):
        """Apply custom field mappings from backend configuration (import direction).

        Called AFTER hardcoded defaults so custom mappings can override.
        Skips composite Shopify fields (containing '+'), dotted Odoo fields,
        invalid Odoo fields, and missing Shopify keys — all gracefully.
        """
        mappings = self.env['shopify.field.mapping'].search([
            ('backend_id', '=', self.backend.id),
            ('entity', '=', self.entity_name),
            ('direction', 'in', ('import', 'both')),
            ('active', '=', True),
        ], order='sequence, id')

        if not mappings:
            return

        # Resolve target model from the binding's odoo_id field
        binding_model = self.env[self.binding_model]
        target_model_name = binding_model._fields['odoo_id'].comodel_name
        target_model = self.env[target_model_name]

        for mapping in mappings:
            shopify_field = mapping.shopify_field
            odoo_field = mapping.odoo_field

            # Skip composite fields (handled by hardcoded logic)
            if '+' in shopify_field:
                continue

            # Skip dotted Odoo fields (relational writes need special handling)
            if '.' in odoo_field:
                _logger.debug(
                    "Skipping dotted Odoo field %s in import mapping", odoo_field,
                )
                continue

            # Validate field exists on target model
            if odoo_field not in target_model._fields:
                _logger.warning(
                    "Import mapping skipped: field '%s' not found on model '%s'",
                    odoo_field, target_model._name,
                )
                continue

            # Traverse Shopify node to get value
            value = self._traverse_shopify_node(node, shopify_field)
            if value is None:
                continue

            # Type-compatibility validation before assignment
            field_def = target_model._fields[odoo_field]

            if field_def.type in ('many2one', 'one2many', 'many2many'):
                if not isinstance(value, int):
                    _logger.warning(
                        "Field mapping skipped: '%s' is a %s field but got %s "
                        "(mapping %s → %s, backend %s)",
                        odoo_field, field_def.type, type(value).__name__,
                        shopify_field, odoo_field, self.backend.id,
                    )
                    continue

            if field_def.type in ('integer', 'float', 'monetary'):
                if not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                        if field_def.type == 'integer':
                            value = int(value)
                    except (ValueError, TypeError):
                        _logger.warning(
                            "Field mapping skipped: '%s' is %s but value '%s' "
                            "is not numeric (mapping %s → %s, backend %s)",
                            odoo_field, field_def.type, value,
                            shopify_field, odoo_field, self.backend.id,
                        )
                        continue

            if field_def.type == 'boolean':
                if isinstance(value, str):
                    lower = value.lower()
                    if lower in ('true', '1', 'yes'):
                        value = True
                    elif lower in ('false', '0', 'no'):
                        value = False
                    else:
                        _logger.warning(
                            "Field mapping skipped: '%s' is boolean but '%s' "
                            "is not a recognized boolean string "
                            "(mapping %s → %s, backend %s)",
                            odoo_field, value,
                            shopify_field, odoo_field, self.backend.id,
                        )
                        continue

            vals[odoo_field] = value

    @staticmethod
    def _traverse_shopify_node(node, path):
        """Traverse a Shopify node dict using dot-separated path.

        Supports dict keys and integer list indices.
        Returns None if any segment is missing.

        Examples:
            'title'                          → node['title']
            'variants.edges.0.node.price'    → node['variants']['edges'][0]['node']['price']
        """
        current = node
        for segment in path.split('.'):
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(segment)
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(segment)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current
