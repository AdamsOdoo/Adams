"""Batch 2 checkpoint 2: the governed route out of a tax-blocked order.

THE DEFECT THIS CLOSES. The order importer already does the hard part. It
canonicalises a Shopify `TaxLine` into a version-stamped fingerprint, refuses
to guess, and raises `odoo_validation_configuration` carrying sanitized,
structured evidence -- rate, inclusion posture, bounded title/source previews,
the fingerprint itself, and a bounded list of same-company sale taxes that
merely MATCH on rate and inclusion (`suggestion_basis:
rate_and_inclusion_only_non_binding`). All of that was reachable by nobody.
The job stopped, the evidence sat in a job-log row, and the only offered
control was a generic retry that re-ran the identical import and failed the
identical way.

WHAT THIS IS NOT. It is not a tax engine, not a remap state machine, and not
a second place to edit a mapping. It creates one mapping from evidence that
already exists, from an explicit human choice among candidates the mapping
model's own constraint would accept, and then resumes the exact job that was
waiting for it.

TWO RULES THAT SHAPE EVERYTHING BELOW.

*The fingerprint is never typed and never parsed out of prose.* It is read
from the structured `technical_detail` the importer serialised, after exact
schema validation. `reason` is a human sentence; recovering identity from it
would make a translation or a reworded message silently repoint a mapping.

*Suggestions are not decisions.* The importer's candidates match on rate and
inclusion only, which is explicitly non-binding -- two taxes can share a rate
and mean different things. The administrator selects, and the selection is
revalidated against the live database at confirm time rather than trusted
from when the dialog opened.
"""

import json

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.shopify_connector_sale.models.shopify_connector_tax_mapping import (
    SHOPIFY_TAX_FINGERPRINT_VERSION,
)

# The EXACT key set `_resolve_tax_ids` serialises. Exact, not "at least":
# a payload carrying extra keys is not the payload this route was written
# against, and treating it as one is how a future change to the importer
# would be absorbed silently instead of failing.
TAX_EVIDENCE_KEYS = frozenset({
    'rate_percentage',
    'included',
    'title_preview',
    'source_preview',
    'fingerprint',
    'suggested_account_tax_ids',
    'suggestion_basis',
})

# The job types whose failure can legitimately carry tax evidence. A scan
# never resolves a tax line, so a scan job offering this route would mean the
# evidence came from somewhere unexpected.
TAX_DECISION_JOB_TYPES = frozenset({'order_import_sync'})

# The state an unknown fingerprint actually leaves the job in.
# `odoo_validation_configuration` is a MANUAL_FIX_THEN_RETRY class, so the
# dispatcher routes it to `failed_retryable` -- NOT `blocked_manual_review`,
# which is reserved for the classes that double as a manual_review_subreason.
# Asserting the state this route really produces, rather than the one the
# phrase "blocked work" suggests, is the difference between a guard that runs
# and a guard that never matches.
TAX_DECISION_JOB_STATE = 'failed_retryable'
TAX_DECISION_ERROR_CLASS = 'odoo_validation_configuration'


def parse_tax_evidence(raw):
    """Return the validated evidence dict, or ``None``.

    Returns ``None`` rather than raising for anything that simply is not tax
    evidence -- most job logs are not -- so the caller can scan a job's
    history cheaply. Malformed evidence that CLAIMS to be tax evidence is
    still just ``None`` here; the wizard turns that into a refusal, because
    a half-readable payload must never become a mapping.
    """
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if set(payload) != TAX_EVIDENCE_KEYS:
        return None
    fingerprint = payload.get('fingerprint')
    if not isinstance(fingerprint, str):
        return None
    expected_prefix = 'v%d:' % SHOPIFY_TAX_FINGERPRINT_VERSION
    if not fingerprint.startswith(expected_prefix):
        return None
    digest = fingerprint[len(expected_prefix):]
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        return None
    if not isinstance(payload.get('rate_percentage'), str):
        return None
    if not isinstance(payload.get('included'), bool):
        return None
    suggested = payload.get('suggested_account_tax_ids')
    if not isinstance(suggested, list) or not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in suggested
    ):
        return None
    for key in ('title_preview', 'source_preview', 'suggestion_basis'):
        if not isinstance(payload.get(key), str):
            return None
    return payload


class ShopifyConnectorJobTaxDecision(models.Model):
    """The job-side seam: is there a tax decision waiting on this job?"""

    _inherit = 'shopify.connector.job'

    tax_decision_pending = fields.Boolean(
        compute='_compute_tax_decision_pending',
        string='Waiting for a tax mapping',
        help='This order stopped because a Shopify tax fingerprint has no '
             'explicit Odoo mapping for the store.',
    )

    def _compute_tax_decision_pending(self):
        for job in self:
            job.tax_decision_pending = bool(job._tax_decision_evidence())

    def _tax_decision_evidence(self):
        """The structured evidence this job is waiting on, or ``False``.

        Structural on every axis: job type, job state, error class, and a
        payload matching the exact schema. Nothing here reads `reason`.
        """
        self.ensure_one()
        if self.job_type not in TAX_DECISION_JOB_TYPES:
            return False
        if self.state != TAX_DECISION_JOB_STATE:
            return False
        if self.error_class != TAX_DECISION_ERROR_CLASS:
            return False
        logs = self.env['shopify.connector.job.log'].search(
            [('job_id', '=', self.id)], order='id desc',
        )
        for log in logs:
            evidence = parse_tax_evidence(log.technical_detail)
            if evidence:
                return evidence
        return False

    def action_open_tax_mapping_decision(self):
        """Open the decision dialog for this job (Administrator only)."""
        self.ensure_one()
        self.env['shopify.connector.tax.decision.wizard'] \
            ._assert_tax_decision_administrator()
        # The caller's own read access, in the caller's own environment,
        # before anything is disclosed about the job or its store.
        self.check_access('read')
        if not self._tax_decision_evidence():
            raise UserError(
                'This job is not waiting for a tax mapping decision.'
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Map this Shopify tax',
            'res_model': 'shopify.connector.tax.decision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_id': self.id},
        }


class ShopifyConnectorTaxDecisionWizard(models.TransientModel):
    _name = 'shopify.connector.tax.decision.wizard'
    _description = 'Shopify Connector Tax Mapping Decision'

    job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    store_id = fields.Many2one(
        related='job_id.store_id', readonly=True,
    )
    company_id = fields.Many2one(
        related='job_id.store_id.company_id', readonly=True,
    )
    shopify_order_gid = fields.Char(
        related='job_id.shopify_target_gid', readonly=True,
        string='Shopify order',
    )
    # Readonly and never rendered as an input. §7.2.5: the administrator is
    # never asked to type or edit a fingerprint -- it identifies the evidence,
    # and a typed one would identify something else.
    shopify_tax_evidence_key = fields.Char(readonly=True, string='Fingerprint')
    rate_percentage = fields.Char(readonly=True, string='Rate (%)')
    price_included = fields.Boolean(
        readonly=True, string='Price includes tax',
    )
    title_preview = fields.Char(readonly=True, string='Shopify tax name')
    source_preview = fields.Char(readonly=True, string='Shopify tax source')
    candidate_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        readonly=True,
        string='Eligible Odoo taxes',
    )
    account_tax_id = fields.Many2one(
        comodel_name='account.tax',
        required=True,
        string='Map to Odoo tax',
        help='The Odoo tax this Shopify tax means. Nothing is created for '
             'you; if the right tax does not exist yet, create it first and '
             'come back.',
    )

    @api.model
    def _assert_tax_decision_administrator(self):
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may map a Shopify '
                'tax.'
            )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        job_id = self.env.context.get('default_job_id')
        if not job_id:
            return result
        self._assert_tax_decision_administrator()
        job = self.env['shopify.connector.job'].browse(job_id)
        evidence = self._validated_evidence(job)
        result.update({
            'job_id': job.id,
            'shopify_tax_evidence_key': evidence['fingerprint'],
            'rate_percentage': evidence['rate_percentage'],
            'price_included': evidence['included'],
            'title_preview': evidence['title_preview'],
            'source_preview': evidence['source_preview'],
            'candidate_tax_ids': [
                (6, 0, self._eligible_tax_ids(job, evidence))
            ],
        })
        return result

    @api.model
    def _validated_evidence(self, job):
        """Every check §7.2.3 requires, in the caller's own environment."""
        if not job.exists():
            raise UserError('That job no longer exists.')
        # ORIGINAL CALLER ACCESS, not the wizard's. Reading the job under
        # elevation here would disclose a foreign store's tax evidence to an
        # administrator of a different company.
        job.check_access('read')
        job.store_id.check_access('read')
        if job.store_id.company_id.id not in self.env.companies.ids:
            raise AccessError(
                'That store belongs to a company you are not working in.'
            )
        evidence = job._tax_decision_evidence()
        if not evidence:
            raise UserError(
                'This job is not waiting for a tax mapping decision. It may '
                'already have been resolved.'
            )
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', job.store_id.id)], limit=1,
        )
        if not settings or not settings.order_company_id:
            raise UserError(
                'The store has no configured order company, so a tax mapping '
                'cannot be validated.'
            )
        if settings.order_company_id != job.store_id.company_id:
            raise UserError(
                'The store and its order company disagree; resolve that '
                'before mapping a tax.'
            )
        return evidence

    @api.model
    def _eligible_tax_ids(self, job, evidence):
        """Recomputed, never taken from the payload.

        The stored `suggested_account_tax_ids` describe the database as it was
        when the job failed. A tax can have been archived, re-companied or had
        its inclusion posture changed since. Recomputing means the list on
        screen is a list the mapping model's constraint would actually accept
        -- and it is deliberately the SAME predicate that constraint enforces.
        """
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', job.store_id.id)], limit=1,
        )
        if not settings or not settings.order_company_id:
            return []
        expected = 'tax_included' if evidence['included'] else 'tax_excluded'
        try:
            amount = float(evidence['rate_percentage'])
        except (TypeError, ValueError):
            return []
        return self.env['account.tax'].search([
            ('company_id', '=', settings.order_company_id.id),
            ('active', '=', True),
            ('type_tax_use', '=', 'sale'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', amount),
            ('include_base_amount', '=', False),
            ('price_include_override', '=', expected),
        ], order='id', limit=20).ids

    def action_confirm(self):
        """Create the mapping and resume the exact job, once."""
        self.ensure_one()
        self._assert_tax_decision_administrator()
        job = self.job_id
        # REVALIDATED, not trusted. Everything checked when the dialog opened
        # is checked again here against the live database, because the gap
        # between the two is exactly where a concurrent resolution, a retry,
        # or an archived tax lands.
        evidence = self._validated_evidence(job)
        if evidence['fingerprint'] != self.shopify_tax_evidence_key:
            raise UserError(
                'The tax evidence changed while this dialog was open. Reopen '
                'it so the decision is made against what is there now.'
            )
        tax = self.account_tax_id
        if tax.id not in self._eligible_tax_ids(job, evidence):
            raise UserError(
                'That tax is no longer eligible for this Shopify tax. It must '
                'be an active same-company sale tax, a leaf percentage at the '
                'same rate, with the same tax-inclusion posture.'
            )
        mapping = self._create_mapping(job, evidence, tax)
        self._resume_blocked_job(job)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shopify Tax Mapping',
            'res_model': 'shopify.connector.tax.mapping',
            'res_id': mapping.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_mapping(self, job, evidence, tax):
        """Atomic, with the concurrent winner contained.

        `UNIQUE(store_id, shopify_tax_evidence_key)` is the arbiter. A second
        administrator confirming the same decision must not raise and must not
        create a second mapping -- their intent is already satisfied by the
        row that won.
        """
        Mapping = self.env['shopify.connector.tax.mapping']
        values = {
            'store_id': job.store_id.id,
            'shopify_tax_evidence_key': evidence['fingerprint'],
            'shopify_tax_fingerprint_version': SHOPIFY_TAX_FINGERPRINT_VERSION,
            'shopify_price_included': evidence['included'],
            'title_preview': evidence['title_preview'],
            'source_preview': evidence['source_preview'],
            'account_tax_id': tax.id,
        }
        try:
            with self.env.cr.savepoint():
                return Mapping.create(values)
        except IntegrityError:
            existing = Mapping.search([
                ('store_id', '=', job.store_id.id),
                ('shopify_tax_evidence_key', '=', evidence['fingerprint']),
            ], limit=1)
            if not existing:
                raise
            return existing
        except ValidationError:
            # The mapping model's own safety constraint refused. Surface it
            # rather than translating it: it is the authority on what a valid
            # mapping is, and this route deliberately does not restate its
            # rules in a second place.
            raise

    def _resume_blocked_job(self, job):
        """Resume the EXACT job, once, through the existing governed path.

        Not a fresh order scan: a scan would re-enumerate a window and admit
        unrelated work, while the thing that was waiting is this one order.
        `action_manual_retry` is the sanctioned requeue and carries its own
        role check, mutation-evidence guard and audit entry.

        If a concurrent confirmation already resumed it, the job is no longer
        in a retryable state and there is nothing left to do -- resuming twice
        would admit the same import twice.
        """
        if job.state != TAX_DECISION_JOB_STATE:
            return False
        job.action_manual_retry()
        return True
