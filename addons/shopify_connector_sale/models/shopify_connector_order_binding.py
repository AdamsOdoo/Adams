from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class ShopifyConnectorOrderBinding(models.Model):
    """Permanent, PII-free Shopify Order to Odoo sale-order binding."""

    _name = 'shopify.connector.order.binding'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Order Binding'

    sale_order_id = fields.Many2one(
        comodel_name='sale.order', required=True, index=True,
        ondelete='restrict',
    )
    shopify_order_name = fields.Char(readonly=True)
    shopify_legacy_resource_id = fields.Char(index=True, readonly=True)
    shopify_processed_at = fields.Datetime(readonly=True)
    shopify_updated_at_snapshot = fields.Datetime(readonly=True)
    shopify_created_at = fields.Datetime(readonly=True)
    shopify_currency_code = fields.Char(size=3, readonly=True)
    shopify_presentment_currency_code = fields.Char(size=3, readonly=True)
    shopify_taxes_included = fields.Boolean(readonly=True)
    shopify_financial_status_snapshot = fields.Char(readonly=True)
    shopify_previous_financial_status_snapshot = fields.Char(readonly=True)
    shopify_fulfillment_status_snapshot = fields.Char(readonly=True)
    shopify_cancelled_at = fields.Datetime(readonly=True)
    shopify_cancel_reason = fields.Char(readonly=True)
    shopify_order_total_amount = fields.Char(readonly=True)
    shopify_order_total_presentment = fields.Char(readonly=True)
    shopify_subtotal_amount = fields.Char(readonly=True)
    shopify_total_tax_amount = fields.Char(readonly=True)
    shopify_total_discounts_amount = fields.Char(readonly=True)
    shopify_total_shipping_amount = fields.Char(readonly=True)
    shopify_total_tip_amount = fields.Char(readonly=True)
    customer_resolution = fields.Selection(
        selection=[
            ('existing_binding', 'Existing Binding'),
            ('email_match', 'Email Match'),
            ('created', 'Created'),
            ('guest_email_match', 'Guest Email Match'),
            ('guest_created', 'Guest Created'),
            ('fallback', 'Fallback'),
            ('manual', 'Manual'),
        ],
        readonly=True,
    )
    shopify_last_imported_at = fields.Datetime(readonly=True)
    shopify_last_evidence_refresh_at = fields.Datetime(readonly=True)
    financial_status_changed_at = fields.Datetime(readonly=True)
    financial_status_trigger_source = fields.Char(readonly=True)

    manual_gateway_name = fields.Char(readonly=True)
    manual_gateway_evidence_state = fields.Selection(
        selection=[
            ('not_manual', 'Not Manual'),
            ('unambiguous', 'Unambiguous Manual Gateway'),
            ('mixed', 'Mixed or Ambiguous'),
        ],
        default='not_manual', readonly=True,
    )
    manual_gateway_approval_state = fields.Selection(
        selection=[
            ('not_required', 'Not Required'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('superseded', 'Superseded'),
        ],
        default='not_required', required=True, readonly=True,
    )
    manual_gateway_approved_by_uid = fields.Many2one(
        comodel_name='res.users', readonly=True,
    )
    manual_gateway_approved_at = fields.Datetime(readonly=True)
    manual_gateway_approved_shopify_updated_at = fields.Datetime(readonly=True)

    is_cod = fields.Boolean(readonly=True)
    cod_commercial_state = fields.Selection(
        selection=[
            ('imported', 'Imported'),
            ('quotation', 'Quotation'),
            ('confirmed', 'Confirmed'),
            ('review', 'Review'),
            ('cancelled', 'Cancelled'),
        ],
        readonly=True,
    )
    cod_fulfillment_state = fields.Selection(
        selection=[('not_dispatched', 'Not Dispatched')], readonly=True,
    )
    cod_collection_state = fields.Selection(
        selection=[
            ('nothing_collected', 'Nothing Collected'),
            ('partially_collected', 'Partially Collected'),
            ('fully_collected', 'Fully Collected'),
            ('discrepancy', 'Discrepancy'),
        ],
        readonly=True,
    )
    cod_order_value_amount = fields.Char(readonly=True)
    cod_fulfilled_value_amount = fields.Char(readonly=True)
    cod_collected_value_amount = fields.Char(readonly=True)
    cod_refunded_value_amount = fields.Char(readonly=True)
    cod_cancelled_value_amount = fields.Char(readonly=True)

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'An order binding with this Shopify GID already exists for this store.',
    )
    _store_sale_order_uniq = models.Constraint(
        'UNIQUE(store_id, sale_order_id)',
        'This sale order is already bound for this Shopify store.',
    )

    @api.model
    def _odoo_binding_field_name(self):
        return 'sale_order_id'

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'shopify_order_name',
            'shopify_legacy_resource_id',
            'shopify_processed_at',
            'shopify_updated_at_snapshot',
            'shopify_created_at',
            'shopify_currency_code',
            'shopify_presentment_currency_code',
            'shopify_taxes_included',
            'shopify_financial_status_snapshot',
            'shopify_previous_financial_status_snapshot',
            'shopify_fulfillment_status_snapshot',
            'shopify_cancelled_at',
            'shopify_cancel_reason',
            'shopify_order_total_amount',
            'shopify_order_total_presentment',
            'shopify_subtotal_amount',
            'shopify_total_tax_amount',
            'shopify_total_discounts_amount',
            'shopify_total_shipping_amount',
            'shopify_total_tip_amount',
            'customer_resolution',
            'shopify_last_imported_at',
            'shopify_last_evidence_refresh_at',
            'financial_status_changed_at',
            'financial_status_trigger_source',
            'manual_gateway_name',
            'manual_gateway_evidence_state',
            'manual_gateway_approval_state',
            'manual_gateway_approved_by_uid',
            'manual_gateway_approved_at',
            'manual_gateway_approved_shopify_updated_at',
            'is_cod',
            'cod_commercial_state',
            'cod_fulfillment_state',
            'cod_collection_state',
            'cod_order_value_amount',
            'cod_fulfilled_value_amount',
            'cod_collected_value_amount',
            'cod_refunded_value_amount',
            'cod_cancelled_value_amount',
        ))

    @api.model
    def _pii_snapshot_fields(self):
        return ()

    def action_approve_manual_gateway_order(self, reason=False):
        """Record approval intent and enqueue a read-only evidence refresh."""
        self.ensure_one()
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_reviewer'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Reviewer or Administrator may '
                'approve a manual-gateway order.'
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError('A non-empty approval reason is required.')
        # Connector Reviewer/Admin roles intentionally do not imply Odoo's
        # Sales groups.  Read only the two business-record fields required by
        # this sanctioned action so its accepted authorization does not rely
        # on a warm superuser cache or unrelated sale.order ACL membership.
        sale_order_evidence = self.sale_order_id.sudo().read(
            ['company_id', 'state'],
        )[0]
        if sale_order_evidence['company_id'][0] != self.env.company.id:
            raise AccessError(
                'Manual-gateway approval must run in the sale order company.'
            )
        if self.manual_gateway_approval_state == 'approved':
            return True
        if (
            self.manual_gateway_approval_state == 'pending'
            and self.manual_gateway_approved_at
        ):
            return True
        if self.manual_gateway_approval_state != 'pending':
            raise UserError('This order is not awaiting manual-gateway approval.')
        if sale_order_evidence['state'] != 'draft':
            raise UserError('Only a draft quotation can be approved.')
        settings = self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', self.store_id.id),
        ], limit=1)
        if not settings or settings.manual_gateway_policy != 'require_approval':
            raise UserError(
                'This store no longer requires manual-gateway approval.'
            )
        approved = settings._approved_manual_gateway_set()
        if (
            self.status == 'review'
            or self.manual_gateway_evidence_state != 'unambiguous'
            or not self.manual_gateway_name
            or self.manual_gateway_name.casefold() not in approved
        ):
            raise UserError(
                'The order no longer has one approved, unambiguous manual '
                'payment gateway.'
            )
        if (
            self.shopify_cancelled_at
            or (self.shopify_financial_status_snapshot or '').upper()
            in ('REFUNDED', 'PARTIALLY_REFUNDED', 'VOIDED', 'EXPIRED')
        ):
            raise UserError('Cancelled or reversed payment evidence is ineligible.')

        safe_reason = self._audit_safe_reason(reason)
        with self.env.cr.savepoint():
            self.sudo().write({
                'manual_gateway_approval_state': 'pending',
                'manual_gateway_approved_by_uid': self.env.uid,
                'manual_gateway_approved_at': fields.Datetime.now(),
                'manual_gateway_approved_shopify_updated_at': (
                    self.shopify_updated_at_snapshot
                ),
            })
            self.env['shopify.connector.job.enqueue'].enqueue(
                self.store_id,
                job_source='manual_sync',
                job_type='order_import_sync',
                payload_hash='approval:%d:%s' % (
                    self.id,
                    fields.Datetime.to_string(
                        self.shopify_updated_at_snapshot
                    ) if self.shopify_updated_at_snapshot else 'unknown',
                ),
                res_model='shopify.connector.store',
                res_id=self.store_id.id,
                shopify_target_gid=self.shopify_gid,
            )
            self.store_id._create_lifecycle_audit_job(
                'Manual gateway approval binding_id=%d sale_order_id=%d '
                'actor_uid=%d reason=%s' % (
                    self.id, self.sale_order_id.id, self.env.uid, safe_reason,
                )
            )
        return True
