"""Batch 2 §8.2: the transient half of the product match decision.

The durable record is the decision. This is the dialog that makes one, and it
owns exactly two responsibilities: show a reviewer what the importer actually
saw, and refuse to apply a choice that is no longer safe by the time they press
the button.

EVERY CHECK RUNS TWICE, AND THE SECOND TIME IS THE ONE THAT COUNTS. The gap
between opening a dialog and confirming it is where a concurrent resolution,
a re-import, a merchant editing the product on Shopify, an archived Odoo
product and a competing binding all land. So `_validated_decision` runs at
open AND at confirm, the eligible set is recomputed at both, and the confirm
path additionally takes a real row lock on the decision before it reads the
state it is about to act on.
"""

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_product.models\
    .shopify_connector_product_match_decision import (
        DECISION_LEVEL_TEMPLATE,
        DECISION_LEVEL_VARIANT,
        MATCH_DECISION_ERROR_CLASS,
        MATCH_DECISION_JOB_STATE,
        MATCH_DECISION_JOB_TYPES,
    )


class ShopifyConnectorProductMatchDecisionWizard(models.TransientModel):
    _name = 'shopify.connector.product.match.decision.wizard'
    _description = 'Shopify Connector Product Match Decision'

    decision_id = fields.Many2one(
        comodel_name='shopify.connector.product.match.decision',
        required=True, readonly=True, ondelete='cascade',
    )
    job_id = fields.Many2one(
        related='decision_id.job_id', readonly=True, string='Source job',
    )
    store_id = fields.Many2one(
        related='decision_id.store_id', readonly=True,
    )
    company_id = fields.Many2one(
        related='decision_id.company_id', readonly=True,
    )
    decision_level = fields.Selection(
        related='decision_id.decision_level', readonly=True,
    )
    shopify_product_gid = fields.Char(
        related='decision_id.shopify_product_gid', readonly=True,
        string='Shopify product',
    )
    shopify_variant_gid = fields.Char(
        related='decision_id.shopify_variant_gid', readonly=True,
        string='Shopify variant',
    )
    match_key = fields.Selection(
        related='decision_id.match_key', readonly=True,
    )
    title_preview = fields.Char(
        related='decision_id.title_preview', readonly=True,
    )
    sku_preview = fields.Char(
        related='decision_id.sku_preview', readonly=True,
    )
    barcode_preview = fields.Char(
        related='decision_id.barcode_preview', readonly=True,
    )
    options_preview = fields.Char(
        related='decision_id.options_preview', readonly=True,
    )
    candidate_total = fields.Integer(
        related='decision_id.candidate_total', readonly=True,
    )
    resolved_template_id = fields.Many2one(
        related='decision_id.resolved_template_id', readonly=True,
    )

    # The eligible sets, recomputed for THIS dialog. They are not the stored
    # candidate snapshot: that describes the database when the job failed.
    eligible_template_ids = fields.Many2many(
        comodel_name='product.template',
        relation='shopify_match_wizard_eligible_template_rel',
        column1='wizard_id', column2='template_id',
        readonly=True, string='Eligible Odoo products',
    )
    eligible_variant_ids = fields.Many2many(
        comodel_name='product.product',
        relation='shopify_match_wizard_eligible_variant_rel',
        column1='wizard_id', column2='variant_id',
        readonly=True, string='Eligible Odoo variants',
    )
    selected_template_id = fields.Many2one(
        comodel_name='product.template',
        string='This Shopify product is',
        help='The Odoo product this Shopify product means. Nothing is '
             'created for you; the choice is among the records that already '
             'carry the identifier Shopify sent.',
    )
    selected_variant_id = fields.Many2one(
        comodel_name='product.product',
        string='This Shopify variant is',
        help='The Odoo variant this Shopify variant means, under the product '
             'the import already resolved.',
    )

    @api.model
    def _assert_match_decision_reviewer(self):
        """The existing capability contract, restated on the server.

        Confirming resumes a `blocked_manual_review` job through
        `action_manual_retry`, which admits a Reviewer or an Administrator
        from that state and nobody else. Requiring the same two groups here
        means the dialog cannot offer a decision whose consequence the caller
        would then be refused -- and an Operator, who may start an import,
        still cannot decide what a product means.
        """
        user = self.env.user
        if not (
            user.has_group(
                'shopify_connector_core.group_shopify_connector_reviewer'
            )
            or user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Reviewer or Administrator may '
                'decide what a Shopify product matches.'
            )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        decision_id = self.env.context.get('default_decision_id')
        if not decision_id:
            return result
        self._assert_match_decision_reviewer()
        decision = self.env[
            'shopify.connector.product.match.decision'
        ].browse(decision_id)
        self._validated_decision(decision)
        eligible = decision.eligible_candidates()
        result['decision_id'] = decision.id
        if decision.decision_level == DECISION_LEVEL_TEMPLATE:
            result['eligible_template_ids'] = [(6, 0, eligible.ids)]
        else:
            result['eligible_variant_ids'] = [(6, 0, eligible.ids)]
        return result

    @api.model
    def _validated_decision(self, decision):
        """Every check §8.2.9 requires, in the caller's own environment."""
        if not decision.exists():
            raise UserError('That match decision no longer exists.')
        # ORIGINAL CALLER ACCESS, not the wizard's. Reading the decision under
        # elevation here would disclose a foreign store's catalog evidence to
        # a reviewer of a different company.
        decision.check_access('read')
        store = decision.store_id
        store.check_access('read')
        if not store.company_id:
            raise UserError(
                'That store has no company, so a match cannot be scoped.'
            )
        if store.company_id.id not in self.env.companies.ids:
            raise AccessError(
                'That store belongs to a company you are not working in.'
            )
        if decision.state != 'pending':
            raise UserError(
                'This match decision has already been made. Reopen the job '
                'to see where the import got to.'
            )
        job = decision.job_id
        if not job.exists():
            raise UserError('The job this decision belongs to is gone.')
        job.check_access('read')
        if job.store_id != store:
            raise UserError(
                'This decision and its job disagree about the store.'
            )
        if job.job_type not in MATCH_DECISION_JOB_TYPES:
            raise UserError('That job does not import a product.')
        if (
            job.state != MATCH_DECISION_JOB_STATE
            or job.error_class != MATCH_DECISION_ERROR_CLASS
        ):
            raise UserError(
                'That import is no longer blocked on an ambiguous match, so '
                'there is nothing for this decision to unblock.'
            )
        if (job.payload_hash or False) != (decision.job_payload_hash or False):
            raise UserError(
                'The Shopify product changed since this decision was raised. '
                'Reopen it so the choice is made against what is there now.'
            )
        return decision

    def action_confirm(self):
        """Record the decision and resume the exact job, once, atomically."""
        self.ensure_one()
        self._assert_match_decision_reviewer()
        decision = self.decision_id
        # A REAL ROW LOCK, taken before the state it guards is read. Two
        # reviewers confirming the same decision at once would otherwise both
        # read `pending`, both write, and both resume -- admitting the same
        # import twice. The loser waits here, then reads the state the winner
        # committed and is refused by the revalidation below.
        self.env.cr.execute(
            'SELECT id FROM shopify_connector_product_match_decision '
            'WHERE id = %s FOR UPDATE',
            (decision.id,),
        )
        decision.invalidate_recordset()
        # REVALIDATED, not trusted. Everything checked when the dialog opened
        # is checked again against the live database.
        self._validated_decision(decision)
        chosen = self._validated_choice(decision)
        self._assert_no_conflicting_binding(decision, chosen)
        values = {
            'state': 'confirmed',
            'resolved_uid': self.env.uid,
            'resolved_at': fields.Datetime.now(),
        }
        if decision.decision_level == DECISION_LEVEL_TEMPLATE:
            values['selected_template_id'] = chosen.id
        else:
            values['selected_variant_id'] = chosen.id
        job = decision.job_id
        try:
            with self.env.cr.savepoint():
                decision.sudo().write(values)
                # The resume is INSIDE the same savepoint as the decision.
                # A decision recorded without its resume would sit confirmed
                # against a job nobody ever runs again; a resume without its
                # decision would re-run the identical failing search. They
                # are one consequence and they commit or roll back together.
                job.action_manual_retry()
                decision.sudo().write({'resumed_job_state': job.state})
        except IntegrityError as exc:
            raise UserError(
                'That Odoo record was bound to this store while you were '
                'deciding. Reopen the decision so the choice is made against '
                'what is there now.'
            ) from exc
        return {
            'type': 'ir.actions.act_window',
            'name': 'Product match decision',
            'res_model': 'shopify.connector.product.match.decision',
            'res_id': decision.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _validated_choice(self, decision):
        """The chosen record, proved still eligible against live data.

        Eligibility is recomputed rather than compared against the stored
        snapshot: a candidate can have been archived, re-companied, bound to
        this store by a concurrent import, or had its SKU changed since the
        ambiguity was found. Any of those makes it a choice the importer
        would refuse, so the dialog refuses it first and says why.
        """
        if decision.decision_level == DECISION_LEVEL_TEMPLATE:
            chosen = self.selected_template_id
            noun = 'product'
        else:
            chosen = self.selected_variant_id
            noun = 'variant'
        if not chosen:
            raise UserError(
                'Choose the Odoo %s this Shopify %s means.' % (noun, noun)
            )
        if chosen.id not in decision.eligible_candidates().ids:
            raise UserError(
                'That Odoo %s is no longer an eligible match. It must still '
                'carry the identifier Shopify sent, belong to this store\'s '
                'company, and not already be bound to this store.' % (noun,)
            )
        return chosen

    def _assert_no_conflicting_binding(self, decision, chosen):
        """Refuse a choice a competing decision or import already took.

        The eligible set already excludes anything bound, so this is the
        narrow window between that read and this write -- and the case the
        eligible set cannot see: another PENDING-then-CONFIRMED decision for
        a different Shopify product that named the same Odoo record. The
        binding's own `UNIQUE` constraint is still the final arbiter (the
        confirm path catches its `IntegrityError`); this exists so the common
        case is a sentence rather than a constraint violation.
        """
        Decision = self.env[
            'shopify.connector.product.match.decision'
        ].sudo()
        field_name = (
            'selected_template_id'
            if decision.decision_level == DECISION_LEVEL_TEMPLATE
            else 'selected_variant_id'
        )
        competing = Decision.search([
            ('store_id', '=', decision.store_id.id),
            ('id', '!=', decision.id),
            (field_name, '=', chosen.id),
            ('state', 'in', ('confirmed', 'consumed')),
        ], limit=1)
        if competing:
            raise UserError(
                'Another Shopify %s has already been matched to that Odoo '
                'record for this store. One Odoo record can stand for only '
                'one Shopify %s.' % (
                    'variant' if decision.decision_level
                    == DECISION_LEVEL_VARIANT else 'product',
                    'variant' if decision.decision_level
                    == DECISION_LEVEL_VARIANT else 'product',
                )
            )
        return True
