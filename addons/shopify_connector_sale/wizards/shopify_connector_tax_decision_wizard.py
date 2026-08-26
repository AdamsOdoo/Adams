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
    eligible_sale_tax_domain,
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

# One refusal, for every reason a caller may not have this job: it does not
# belong to a company they work in, a record rule hides it, or the ACL refuses
# the model outright. Distinguishing them in the message is itself a disclosure
# -- "you may not read THAT store's job" confirms the job exists and is
# somebody else's -- so they are deliberately indistinguishable.
FOREIGN_JOB_REFUSAL = (
    'That job is not available to you. Open the tax mapping decision from a '
    'stopped order in a company you are working in.'
)

# Everything on this dialog that says WHICH decision it is. All of it is
# derived from the validated job on create and refused on write.
IDENTITY_SNAPSHOT_FIELDS = frozenset({
    'job_id',
    'store_id',
    'company_id',
    'shopify_order_gid',
    'shopify_tax_evidence_key',
    'rate_percentage',
    'price_included',
    'title_preview',
    'source_preview',
    'candidate_tax_ids',
})


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

    def _attention_resolution_action(self):
        """Make Needs Attention's primary action open the real tax dialog."""
        self.ensure_one()
        if self._tax_decision_evidence():
            return self.action_open_tax_mapping_decision()
        return super()._attention_resolution_action()


class ShopifyConnectorTaxDecisionWizard(models.TransientModel):
    _name = 'shopify.connector.tax.decision.wizard'
    _description = 'Shopify Connector Tax Mapping Decision'

    # EVERY FIELD BELOW IS A VALIDATED SNAPSHOT. NOT ONE IS A `related`.
    #
    # THE DEFECT THIS CLOSES (F5). `store_id`, `company_id` and
    # `shopify_order_gid` used to be `related` fields reaching through
    # `job_id`. Odoo 19 gives a related field `compute_sudo=True` by default
    # (`odoo/orm/fields.py`, `related_sudo` -> `compute_sudo`, and
    # `Field.compute_value` does `records.sudo()`), so the chain was walked as
    # SUPERUSER: it answered whatever it was asked. The server-side guards all
    # lived on `default_get` and `action_confirm`, which is the intended UI
    # route -- and an ordinary `create({'job_id': <foreign job>})` over RPC is
    # not that route. A company-A Connector Administrator could name a
    # company-B job and read back that store's id and name, its company, and
    # the Shopify order GID, none of which any record rule would have shown
    # them directly.
    #
    # Snapshots cannot do that. They hold what `create` put there, `create`
    # puts there only what the caller's OWN access to the job proved they may
    # see, and `write` refuses to move any of them afterwards.
    job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    store_id = fields.Many2one(
        comodel_name='shopify.connector.store', readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company', readonly=True,
    )
    shopify_order_gid = fields.Char(
        readonly=True, string='Shopify order',
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
        job = self._authorized_job(job_id)
        evidence = self._validated_evidence(job)
        result.update(self._identity_snapshot(job, evidence))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """ORDINARY ORM CREATE IS IN SCOPE, AND IS GUARDED HERE.

        `default_get` is the UI route; `create` is what an RPC client calls,
        and it is the route F5 was reachable through. Every identity value on
        the new row is (re)derived here from a job the CALLER proved they may
        read -- caller-supplied `store_id`, `company_id`, `shopify_order_gid`,
        fingerprint, rate, posture, previews and candidate list are discarded
        rather than trusted, so a forged snapshot cannot become the record's
        answer to "what is this decision about?".

        `_add_missing_default_values` runs inside `super().create`, i.e. AFTER
        this override, so a UI save that legitimately omits every readonly
        field arrives here with no `job_id` at all. That case resolves the job
        from `default_job_id` in the context -- and then validates it exactly
        as it validates an explicitly supplied one.
        """
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            job = self._authorized_job(
                vals.get('job_id') or self.env.context.get('default_job_id')
            )
            evidence = self._validated_evidence(job)
            vals.update(self._identity_snapshot(job, evidence))
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        """The identity of an open decision is immutable.

        Re-pointing a validated wizard at a different job is indistinguishable
        from creating one for that job without the checks, so it is refused
        outright rather than re-validated. `account_tax_id` -- the one thing
        the administrator is actually deciding -- stays writable.
        """
        moved = sorted(set(vals) & IDENTITY_SNAPSHOT_FIELDS)
        if moved:
            raise UserError(
                'The job and tax evidence a mapping decision is about cannot '
                'be changed once the dialog is open (%s). Close it and open '
                'the decision from the order you mean.' % (', '.join(moved),)
            )
        return super().write(vals)

    @api.model
    def _identity_snapshot(self, job, evidence):
        """The only values that may ever populate the identity fields."""
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'company_id': job.store_id.company_id.id,
            'shopify_order_gid': job.shopify_target_gid or False,
            'shopify_tax_evidence_key': evidence['fingerprint'],
            'rate_percentage': evidence['rate_percentage'],
            'price_included': evidence['included'],
            'title_preview': evidence['title_preview'],
            'source_preview': evidence['source_preview'],
            'candidate_tax_ids': [
                (6, 0, self._eligible_tax_ids(job, evidence))
            ],
        }

    @api.model
    def _authorized_job(self, job_id):
        """Resolve a job this caller may actually see, or refuse telling them
        nothing about it.

        The refusal is deliberately one sentence with no record in it. Odoo's
        own access errors name the records they refuse, which for a
        cross-company probe is the disclosure the check exists to prevent, so
        both the ACL/record-rule refusal and the active-company refusal are
        re-raised as the same opaque message.
        """
        self._assert_tax_decision_administrator()
        try:
            job_id = int(job_id or 0)
        except (TypeError, ValueError):
            job_id = 0
        if not job_id:
            raise UserError(
                'A tax mapping decision must name the job it is about.'
            )
        job = self.env['shopify.connector.job'].browse(job_id)
        if not job.exists():
            raise UserError('That job no longer exists.')
        try:
            job.check_access('read')
            job.store_id.check_access('read')
            if job.store_id.company_id.id not in self.env.companies.ids:
                raise AccessError(FOREIGN_JOB_REFUSAL)
        except AccessError as exc:
            raise AccessError(FOREIGN_JOB_REFUSAL) from exc
        return job

    @api.model
    def _validated_evidence(self, job):
        """Every check §7.2.3 requires, in the caller's own environment."""
        if not job.exists():
            raise UserError('That job no longer exists.')
        # ORIGINAL CALLER ACCESS, not the wizard's. Reading the job under
        # elevation here would disclose a foreign store's tax evidence to an
        # administrator of a different company.
        try:
            job.check_access('read')
            job.store_id.check_access('read')
            if job.store_id.company_id.id not in self.env.companies.ids:
                raise AccessError(FOREIGN_JOB_REFUSAL)
        except AccessError as exc:
            raise AccessError(FOREIGN_JOB_REFUSAL) from exc
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
        try:
            amount = float(evidence['rate_percentage'])
        except (TypeError, ValueError):
            return []
        # ONE RULE, SHARED WITH THE CONSTRAINT. `eligible_sale_tax_domain` is
        # the search form of exactly what `_check_mapping_safety` enforces per
        # record, so a tax offered here cannot be refused there. It reads
        # Odoo's EFFECTIVE inclusion posture (`account.tax.price_include`)
        # rather than requiring an explicit `price_include_override`, which is
        # F4: on a company using Odoo's own `tax_excluded` default, no ordinary
        # tax carries an override and this list came back empty for every
        # excluded Shopify tax in existence.
        return self.env['account.tax'].search(
            eligible_sale_tax_domain(
                settings.order_company_id, evidence['included'], amount,
            ),
            order='id', limit=20,
        ).ids

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
        """Atomic, and FAIL-CLOSED on every collision it cannot account for.

        `UNIQUE(store_id, shopify_tax_evidence_key)` is the arbiter, and losing
        to it means somebody else decided what this Shopify tax means.

        THE DEFECT THIS CLOSES (F6). The previous version caught the
        `IntegrityError`, searched for whatever row held the key, and returned
        it as this call's result. `action_confirm` then reported success and
        resumed the order -- against a tax the administrator had not chosen and
        was never shown. An administrator who deliberately picked "VAT 20%
        (services)" could be told their decision was applied while the order
        was in fact resumed under "VAT 20% (goods)", and the audit trail would
        record the confirmation as having succeeded.

        THREE OUTCOMES, AND ONLY THE FIRST PROCEEDS.

        *A row exists in this transaction's own snapshot and IS the same
        choice.* This is the ordinary sequential case -- a second order hitting
        a fingerprint that was mapped earlier -- and it is the only branch that
        may return a row it did not create, because it has PROVED that row is
        the decision in front of it: same store, same fingerprint, same
        fingerprint version, same inclusion posture, same Odoo tax.

        *A row exists and is a DIFFERENT choice.* Refused, always. The
        administrator's decision was not applied and must not be reported as
        though it had been.

        *`create` collided with a row this snapshot cannot see.* Odoo cursors
        run REPEATABLE READ, so a mapping committed after this transaction
        started raises the unique violation from the index while remaining
        invisible to `search`. There is nothing to compare against, so there is
        nothing to prove, so this refuses -- rather than re-raising a raw
        `IntegrityError` at the administrator, which says nothing about what
        happened or what to do next.

        Refusing raises out of `action_confirm` before `_resume_blocked_job`,
        so a refused decision leaves no mapping, no resumed job and no audit
        entry claiming otherwise.
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
        except IntegrityError as exc:
            existing = Mapping.search([
                ('store_id', '=', job.store_id.id),
                ('shopify_tax_evidence_key', '=', evidence['fingerprint']),
            ], limit=1)
            if existing and self._is_same_tax_choice(existing, evidence, tax):
                return existing
            if existing:
                raise UserError(
                    'This Shopify tax is already mapped to a different Odoo '
                    'tax for this store, so your choice was not applied and '
                    'this order has not been resumed. Review the existing '
                    'mapping in the Tax Mappings workspace and retry the '
                    'order once it says what you mean.'
                ) from exc
            raise UserError(
                'Another administrator mapped this Shopify tax while you were '
                'deciding. Your choice was NOT applied and this order has not '
                'been resumed. Reopen the stopped order to see which mapping '
                'won and whether it is the one you meant.'
            ) from exc
        except ValidationError:
            # The mapping model's own safety constraint refused. Surface it
            # rather than translating it: it is the authority on what a valid
            # mapping is, and this route deliberately does not restate its
            # rules in a second place.
            raise

    @api.model
    def _is_same_tax_choice(self, existing, evidence, tax):
        """Is this existing row the exact decision the administrator made?

        Every component of the mapping's identity, not just the tax. A row
        agreeing on the tax but recording a different inclusion posture or a
        different fingerprint version is a different decision, and returning it
        would resume the order under a mapping nobody in this dialog chose.
        """
        return (
            existing.account_tax_id == tax
            and existing.shopify_tax_evidence_key == evidence['fingerprint']
            and existing.shopify_tax_fingerprint_version
            == SHOPIFY_TAX_FINGERPRINT_VERSION
            and bool(existing.shopify_price_included) == bool(
                evidence['included']
            )
        )

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
