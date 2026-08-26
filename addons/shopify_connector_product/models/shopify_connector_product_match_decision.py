"""Batch 2 §8.2: the durable route out of an ambiguous product match.

THE DEFECT THIS CLOSES. When two Odoo products carry the SKU a Shopify product
claims, the importer is right to refuse -- picking one silently is how a
connector binds a store's catalog to the wrong master data. But refusing was
the whole of it. `ambiguous_match` is a MANUAL_REVIEW class, so the job stopped
at `blocked_manual_review`; the raise carried a human sentence and no
structured evidence; and the only offered control was the generic
`action_resolve_manual_review`, which re-queues the identical job so the
identical search finds the identical two candidates and stops again. The
merchant could press it forever. Nothing durable ever recorded which Odoo
product they meant.

WHY THE DECISION CANNOT BE WRITTEN WHERE THE AMBIGUITY IS FOUND. Both raise
sites (`_resolve_template`, `_match_variant_candidate`) run inside
`import_product_sync`'s single `self.env.cr.savepoint()` block -- the block
that exists so a failure half-way through a product leaves no partial product
behind. A decision created there is rolled back by the same `ROLLBACK TO
SAVEPOINT` that discards the partial writes, and the job would end up blocked
with no decision attached. There is a test that proves exactly this
(`test_a_decision_written_inside_the_importer_savepoint_would_not_survive`),
because it is the entire reason for the seam below.

So the evidence travels out on the exception -- structured, sanitized and
size-bounded on `JobHandlerError.technical_detail` -- and the decision is
written by a product-owned extension of `_route_failure`, in the SAME
transaction that durably records the blocked job. Not a second queue, not a
second dispatcher, not a side channel: one override of one dispatcher method,
which calls `super()` first and then persists what the failure was about.

THREE RULES THAT SHAPE EVERYTHING BELOW.

*Identity is structural, never prose.* The evidence is read from the JSON
payload after exact-key schema validation. Recovering "which product" from a
translated or reworded sentence would repoint a binding on a wording change.

*Identity is OPAQUE, and display evidence is SANITIZED. They are never the
same value.* This is the correction that produced schema `v2`. `v1` passed the
Shopify Product GID, the ProductVariant GID, the remote `updatedAt` and the
exact SKU/barcode match values through `safe_match_preview` -- a DISPLAY
scrubber whose phone-number pattern (`\\d` then six or more digits/separators
then `\\d`) matches the numeric suffix of every real Shopify GID and every
numeric SKU, UPC-A and EAN-13. `gid://shopify/Product/7346299043911` was stored
as `gid://shopify/Product/[redacted-phone]`, so:

* the persisted `decision_key` could never equal the key `_confirmed_for`
  computes from the raw importer payload -- a confirmed decision was
  unconsumable and the job looped back to the same ambiguity;
* two different products whose GIDs both end in a long digit run collapsed to
  ONE identity, so `_persist_decision` could re-point product A's pending
  decision at product B's job and `_supersede_stale_siblings` could supersede
  an unrelated product;
* a numeric SKU became the literal string `[redacted-phone]`, so
  `eligible_candidates()` searched for a value no Odoo record carries and
  offered a reviewer nothing to choose.

So identity values are now retained BYTE-FOR-BYTE -- validated for type,
emptiness, length and control characters, and otherwise never touched -- and
the exact match values are carried as keyed fixed-length DIGESTS. The digest is
what makes exact-match eligibility provable without writing a merchant's SKU or
barcode into a job log. `safe_match_preview` survives, and is now used for
nothing but the four `*_preview` display fields.

*A decision belongs to one exact remote identity.* The key includes the
verbatim remote `updatedAt`. A merchant who edits the product on Shopify while
the decision is pending has changed the thing the decision was about; the old
decision is superseded and the fresh ambiguity gets a fresh review. The
importer consumes a confirmed decision only when the payload it just fetched
carries that same `updatedAt`.

*Candidates are recomputed, never replayed.* The stored candidate ids describe
the database when the job failed. The eligible set is recomputed at open and
again at confirm, with the same predicate the importer matches on, plus the
company-awareness and already-bound exclusion the importer's own binding
constraints would enforce anyway.

WHAT THIS IS NOT. It does not create Odoo products (§8.2.8 -- "create new" is
not required for P0 and the importer's own no-blind-create policy already owns
that path). It is not a matching engine: it selects among candidates the
importer already found. It never edits a protected binding field, never
touches attribute-structure conflict handling (which stays governed by
`product_import_attribute_conflict_mode`), and never contacts Shopify.
"""

import hashlib
import hmac
import json
import logging
import re

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

# The canonical source, the same one `shopify_connector_job_dispatch` imports
# from -- not its re-export, so this cannot start meaning something else.
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from odoo.addons.shopify_connector_core.tools.redaction import redact

_logger = logging.getLogger(__name__)

MATCH_EVIDENCE_SCHEMA = 'product_match_decision.v2'

# The identity version. It appears in the schema name, in the `decision_key`
# prefix and in the match-value digest prefix, so a row written under the
# corrupted `v1` identity rules can never be read, keyed or matched as though
# it had been written under these ones. Migration `19.0.2.8.0` supersedes the
# undecided `v1` rows fail-closed rather than reinterpreting them.
MATCH_IDENTITY_VERSION = 2
MATCH_VERSION_PREFIX = 'v%d:' % MATCH_IDENTITY_VERSION

# Size bounds. Every one of these is a bound on something a merchant controls
# from the Shopify side, so "it will be short in practice" is not an argument.
MATCH_TITLE_MAX_LEN = 120
MATCH_IDENTIFIER_MAX_LEN = 64
MATCH_OPTIONS_MAX_LEN = 160
MATCH_GID_MAX_LEN = 128
MATCH_UPDATED_AT_MAX_LEN = 64
MATCH_VALUES_LIMIT = 20
MATCH_CANDIDATE_LIMIT = 20

# The bound on a value we will DIGEST. Deliberately generous and deliberately
# not a truncation: Shopify allows a 255-character SKU, and hashing a truncated
# copy would produce a digest that no live Odoo record could ever reproduce --
# an eligibility failure with no visible cause. A value longer than this
# produces no digest at all, which fails closed.
MATCH_VALUE_MAX_LEN = 512
# `v2:` + a SHA-256 hex digest.
MATCH_DIGEST_LEN = len(MATCH_VERSION_PREFIX) + 64
# Domain separation, so a digest from this route can never be confused with a
# digest computed elsewhere against the same database secret.
MATCH_DIGEST_LABEL = b'shopify.connector.product.match.decision/match_value/v2'

DECISION_LEVEL_TEMPLATE = 'template'
DECISION_LEVEL_VARIANT = 'variant'
DECISION_LEVELS = (DECISION_LEVEL_TEMPLATE, DECISION_LEVEL_VARIANT)

# The two match keys the importer's own priority order can produce. Name
# matching is not among them and never will be (RA-006).
MATCH_KEYS = ('sku_reference', 'barcode')
MATCH_KEY_FIELD = {'sku_reference': 'default_code', 'barcode': 'barcode'}

# The job types whose ambiguity this route answers. A scan never resolves a
# product match, so a scan offering this route would mean the evidence came
# from somewhere unexpected.
MATCH_DECISION_JOB_TYPES = frozenset({'product_import_sync'})

# The state an ambiguous match actually leaves the job in. `ambiguous_match` is
# a MANUAL_REVIEW class, so the dispatcher routes it to
# `blocked_manual_review` and sets `manual_review_subreason` to the same value.
# Asserting the state and subreason the dispatcher really produces, rather than
# the ones a phrase suggests, is the difference between a guard that runs and a
# guard that never matches.
MATCH_DECISION_JOB_STATE = 'blocked_manual_review'
MATCH_DECISION_ERROR_CLASS = 'ambiguous_match'

# The EXACT key set the importer serialises. Exact, not "at least": a payload
# carrying extra keys is not the payload this route was written against, and
# treating it as one is how a future importer change would be absorbed
# silently instead of failing.
MATCH_EVIDENCE_KEYS = frozenset({
    'schema',
    'level',
    'shopify_product_gid',
    'shopify_variant_gid',
    'remote_updated_at',
    'match_key',
    'match_value_digests',
    'resolved_template_id',
    'title_preview',
    'sku_preview',
    'barcode_preview',
    'options_preview',
    'candidate_ids',
    'candidate_total',
})

_EMAIL_RE = re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b')
_PHONE_RE = re.compile(r'(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)')

# Anything a remote identity may not contain. C0 controls, DEL, and the C1
# range: none of them appear in a Shopify GID or an ISO-8601 timestamp, and all
# of them are the shapes that make a value dangerous to log, render or compare.
_UNSAFE_IDENTITY_RE = re.compile(r'[\x00-\x1f\x7f-\x9f]')


def safe_match_preview(value, limit):
    """Redact, scrub and bound one merchant-controlled string FOR DISPLAY.

    Same discipline as `safe_tax_preview`: secret patterns first (a SKU is a
    free-text field and nothing stops a merchant pasting a token into one),
    then the two PII shapes a product title realistically carries, then the
    length bound. Never raises; a non-string becomes an empty string.

    THIS IS A DISPLAY FUNCTION AND NOTHING ELSE. It is lossy by design -- its
    phone pattern rewrites any run of seven or more digits, which is what every
    real Shopify GID suffix, every numeric SKU and every UPC-A/EAN-13 barcode
    is. Using it on an identity or on a match value is the `v1` defect: see the
    module docstring. Identity goes through `opaque_identity`; exact match
    values go through `match_value_digest`.
    """
    if not isinstance(value, str):
        value = '' if value in (None, False) else str(value)
    value = redact(value)
    value = _EMAIL_RE.sub('[redacted-email]', value)
    value = _PHONE_RE.sub('[redacted-phone]', value)
    return value[:limit]


def _bounded_identifier(value):
    return safe_match_preview(value, MATCH_IDENTIFIER_MAX_LEN)


def opaque_identity(value, limit):
    """One remote identity value, EXACTLY as received, or ``''``.

    Validated and never transformed. There is deliberately no `strip()`, no
    normalisation, no numeric-id extraction and no reconstruction: the value's
    only job is to be equal to itself across the importer, the durable
    decision, the uniqueness key, the supersession search and consumption, and
    every one of those operations is byte comparison. A value that fails any
    check returns ``''``, which every caller treats as "this ambiguity cannot
    be identified durably" and fails closed on.
    """
    if not isinstance(value, str):
        return ''
    if not value or len(value) > limit:
        return ''
    if _UNSAFE_IDENTITY_RE.search(value):
        return ''
    return value


def match_value_digest(env, value):
    """A keyed, fixed-length digest of ONE exact match value, or ``''``.

    WHY A DIGEST AND NOT THE VALUE. The evidence this appears in travels out on
    an exception and is written to a job-log row, so it must not carry a
    merchant's SKU or barcode. But eligibility is an EXACT-match question, and
    a display-sanitized copy cannot answer it (`[redacted-phone]` equals
    `[redacted-phone]` for two different barcodes). A digest answers exactly the
    question that is asked -- "is this live record's identifier the one Shopify
    sent?" -- and answers nothing else.

    WHY IT IS KEYED. A bare SHA-256 of a 12-digit UPC is not a redaction: the
    whole space is enumerable in seconds. `database.secret` is Odoo's own
    per-database secret (`odoo/addons/base/models/ir_config_parameter.py` at the
    pin seeds it on first use), so the digest is meaningless outside this
    database and unrecoverable inside it. Both sides of every comparison are
    computed in the same database, which is the only place a comparison ever
    happens.

    Returns ``''`` -- never a partial or unkeyed digest -- when the value is
    unusable or the secret is absent.
    """
    if not isinstance(value, str) or not value:
        return ''
    if len(value) > MATCH_VALUE_MAX_LEN:
        return ''
    secret = env['ir.config_parameter'].sudo().get_param('database.secret')
    if not secret:
        return ''
    return '%s%s' % (MATCH_VERSION_PREFIX, hmac.new(
        MATCH_DIGEST_LABEL + secret.encode('utf-8'),
        value.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest())


def _is_match_digest(value):
    return (
        isinstance(value, str)
        and len(value) == MATCH_DIGEST_LEN
        and value.startswith(MATCH_VERSION_PREFIX)
        and all(
            character in '0123456789abcdef'
            for character in value[len(MATCH_VERSION_PREFIX):]
        )
    )


def build_match_evidence(
    env, level, shopify_product_gid, remote_updated_at, match_key, match_values,
    candidate_ids, candidate_total, title_preview='', sku_preview='',
    barcode_preview='', options_preview='', shopify_variant_gid='',
    resolved_template_id=0,
):
    """The serialised, bounded evidence one ambiguity produces.

    Identity in, verbatim; exact match values in, as keyed digests; merchant
    prose in, sanitized for display. Those three treatments are different on
    purpose and the module docstring says why.

    Returns a JSON string, or ``''`` when the ambiguity cannot be identified
    durably -- which happens when the remote payload carries no `updatedAt`, no
    product GID, an identity that fails validation, or no digestible match
    value. Fail closed: a decision whose remote identity cannot be pinned could
    be consumed against a product that has since changed, which is precisely
    the failure the identity rule exists to prevent. The job still blocks; it
    simply offers no decision.
    """
    product_gid = opaque_identity(shopify_product_gid, MATCH_GID_MAX_LEN)
    updated_at = opaque_identity(remote_updated_at, MATCH_UPDATED_AT_MAX_LEN)
    if not product_gid or not updated_at or level not in DECISION_LEVELS:
        return ''
    if match_key not in MATCH_KEYS:
        return ''
    variant_gid = opaque_identity(shopify_variant_gid, MATCH_GID_MAX_LEN)
    if level == DECISION_LEVEL_VARIANT and not variant_gid:
        return ''
    if level == DECISION_LEVEL_TEMPLATE and variant_gid:
        return ''
    digests = []
    for raw in match_values or ():
        digest = match_value_digest(env, raw)
        if digest and digest not in digests:
            digests.append(digest)
        if len(digests) >= MATCH_VALUES_LIMIT:
            break
    if not digests:
        return ''
    ids = [
        int(candidate)
        for candidate in list(candidate_ids or ())[:MATCH_CANDIDATE_LIMIT]
        if isinstance(candidate, int) and not isinstance(candidate, bool)
    ]
    payload = {
        'schema': MATCH_EVIDENCE_SCHEMA,
        'level': level,
        'shopify_product_gid': product_gid,
        'shopify_variant_gid': variant_gid,
        'remote_updated_at': updated_at,
        'match_key': match_key,
        'match_value_digests': sorted(digests),
        'resolved_template_id': int(resolved_template_id or 0),
        'title_preview': safe_match_preview(title_preview, MATCH_TITLE_MAX_LEN),
        'sku_preview': _bounded_identifier(sku_preview),
        'barcode_preview': _bounded_identifier(barcode_preview),
        'options_preview': safe_match_preview(
            options_preview, MATCH_OPTIONS_MAX_LEN,
        ),
        'candidate_ids': ids,
        'candidate_total': int(candidate_total or 0),
    }
    return json.dumps(payload, sort_keys=True)


def parse_match_evidence(raw):
    """Return the validated evidence dict, or ``None``.

    Returns ``None`` rather than raising for anything that simply is not
    product-match evidence -- most classified failures are not -- so the
    dispatcher seam can look at every routed failure cheaply. Evidence that
    CLAIMS to be product-match evidence but does not validate is also just
    ``None``: a half-readable payload must never become a decision.
    """
    if not raw or not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or set(payload) != MATCH_EVIDENCE_KEYS:
        return None
    if payload.get('schema') != MATCH_EVIDENCE_SCHEMA:
        return None
    if payload.get('level') not in DECISION_LEVELS:
        return None
    if payload.get('match_key') not in MATCH_KEYS:
        return None
    # Identity is re-validated on the way IN with the same function that
    # produced it, and compared for exact equality. `opaque_identity` returning
    # the value unchanged is the proof that nothing between the two ends
    # trimmed, normalised or rewrote it.
    for key, limit in (
        ('shopify_product_gid', MATCH_GID_MAX_LEN),
        ('remote_updated_at', MATCH_UPDATED_AT_MAX_LEN),
    ):
        value = payload.get(key)
        # Non-empty FIRST. `opaque_identity('')` is `''`, which equals itself,
        # so the round-trip test alone would let an empty required identity
        # through -- and an empty `remote_updated_at` is exactly the
        # unpinnable-version case the whole identity rule exists to refuse.
        if not isinstance(value, str) or not value:
            return None
        if opaque_identity(value, limit) != value:
            return None
    variant_gid = payload.get('shopify_variant_gid')
    if not isinstance(variant_gid, str):
        return None
    if variant_gid and opaque_identity(variant_gid, MATCH_GID_MAX_LEN) != variant_gid:
        return None
    for key, limit in (
        ('title_preview', MATCH_TITLE_MAX_LEN),
        ('sku_preview', MATCH_IDENTIFIER_MAX_LEN),
        ('barcode_preview', MATCH_IDENTIFIER_MAX_LEN),
        ('options_preview', MATCH_OPTIONS_MAX_LEN),
    ):
        value = payload.get(key)
        if not isinstance(value, str) or len(value) > limit:
            return None
    if payload['level'] == DECISION_LEVEL_VARIANT:
        if not payload['shopify_variant_gid']:
            return None
        if not isinstance(payload.get('resolved_template_id'), int) or isinstance(
            payload.get('resolved_template_id'), bool
        ):
            return None
        if payload['resolved_template_id'] <= 0:
            return None
    else:
        if payload['shopify_variant_gid']:
            return None
        if payload.get('resolved_template_id') != 0:
            return None
    digests = payload.get('match_value_digests')
    if (
        not isinstance(digests, list)
        or not digests
        or len(digests) > MATCH_VALUES_LIMIT
        or len(set(digests)) != len(digests)
        or not all(_is_match_digest(value) for value in digests)
    ):
        return None
    ids = payload.get('candidate_ids')
    if (
        not isinstance(ids, list)
        or len(ids) > MATCH_CANDIDATE_LIMIT
        or not all(
            isinstance(value, int) and not isinstance(value, bool) and value > 0
            for value in ids
        )
    ):
        return None
    total = payload.get('candidate_total')
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        return None
    return payload


def decision_key_for(level, product_gid, variant_gid, remote_updated_at):
    """The bounded identity of one ambiguity, for `UNIQUE(store_id, key)`.

    Hashed rather than concatenated so the column is bounded whatever Shopify
    sends, and length-prefixed so no combination of components can collide by
    running into one another. The human-readable components are separate
    fields on the record; this is the arbiter, not the display.

    THE COMPONENTS ARE THE RAW OPAQUE IDENTITIES. Under `v1` they were the
    display-sanitized copies, which is why two distinct products could produce
    one key and why the key computed at consumption time (from the raw payload)
    never equalled the key stored at persistence time (from the sanitized one).
    The `v2:` prefix is not decoration: a `v1` key is a different identity
    scheme and must never be consumed as though it were this one.
    """
    parts = (level, product_gid, variant_gid or '', remote_updated_at)
    canonical = '|'.join('%d:%s' % (len(part), part) for part in parts)
    return '%s%s' % (
        MATCH_VERSION_PREFIX,
        hashlib.sha256(canonical.encode('utf-8')).hexdigest(),
    )


class ShopifyConnectorProductMatchDecision(models.Model):
    """One ambiguous product or variant match, waiting on a human.

    Durable by construction: it outlives the importer transaction that found
    the ambiguity, the job that was blocked by it, and the session of whoever
    resolves it. Everything about the remote side is a sanitized, bounded
    snapshot -- this model never re-reads Shopify and holds no payload.
    """

    _name = 'shopify.connector.product.match.decision'
    # SEC-3 (#197): this row points at three other connector rows -- the job it
    # blocks and the two bindings it results in -- and one company may own
    # several stores, so company agreement alone would let a decision for
    # store A name a binding of store B. The scope mixin is the project's
    # existing answer: a constraint that fires under `sudo()` for new rows, and
    # a quarantine (never a re-home) for historic ones.
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Product Match Decision'
    _order = 'id desc'

    # SEC-3 (#197): opt in to Odoo 19's native company consistency check
    # (`odoo/orm/models.py` L451/L4516/L4743). With `check_company=True` on
    # both selection relations below, a decision can only ever select a record
    # of its own store's company -- enforced on create AND write, and under
    # `sudo()`. That is the write-side authority; the record rule is the
    # read-side one.
    _check_company_auto = True

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store', required=True, index=True,
        ondelete='restrict', readonly=True,
    )
    # SEC-3 (#197): company is inherited from the owning store and is never an
    # independent selector. Stored so record rules, searches and grouped reads
    # filter on it in SQL; readonly so it can never diverge from its store.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        comodel_name='shopify.connector.job', required=True, index=True,
        ondelete='restrict', readonly=True,
        string='Source job',
        help='The exact job that stopped on this ambiguity. Confirming the '
             'decision resumes this job and no other.',
    )
    decision_level = fields.Selection(
        selection=[
            (DECISION_LEVEL_TEMPLATE, 'Product'),
            (DECISION_LEVEL_VARIANT, 'Variant'),
        ],
        required=True, readonly=True, index=True,
    )
    # THE THREE OPAQUE IDENTITY COLUMNS. Verbatim remote values, never
    # sanitized, never normalised, never parsed. Every one of them is compared
    # for byte equality by `decision_key_for`, `_supersede_stale_siblings` and
    # `_confirmed_for`, so any transformation applied on the way in is a
    # transformation the importer's raw payload cannot reproduce on the way
    # out. That is exactly what went wrong in `v1`.
    shopify_product_gid = fields.Char(required=True, index=True, readonly=True)
    shopify_variant_gid = fields.Char(readonly=True)
    # The verbatim remote `updatedAt` of the payload the ambiguity was found
    # in. Stored as text so it round-trips exactly; a parsed datetime would
    # lose the identity this decision is keyed on.
    remote_updated_at = fields.Char(required=True, readonly=True)
    # The job's own enqueued identity (`payload_hash`), kept so a confirmation
    # can prove the job in front of it is still the job the decision was
    # recorded against.
    job_payload_hash = fields.Char(readonly=True)
    decision_key = fields.Char(required=True, index=True, readonly=True)

    match_key = fields.Selection(
        selection=[
            ('sku_reference', 'SKU'),
            ('barcode', 'Barcode'),
        ],
        required=True, readonly=True,
        help='Which identifier produced the ambiguous candidates. Product '
             'names are never matched on.',
    )
    # The exact identifier values the importer matched on, as keyed digests --
    # NEVER the values themselves. This column is durable evidence that also
    # reaches a job-log row, and a merchant's SKU or barcode does not belong in
    # either. Eligibility is decided by recomputing each live candidate's
    # digest and comparing digest to digest, which is exact-match semantics
    # with nothing disclosed. See `match_value_digest`.
    match_value_digests = fields.Text(readonly=True)
    resolved_template_id = fields.Many2one(
        comodel_name='product.template', readonly=True, ondelete='restrict',
        string='Under product',
        help='For a variant decision: the Odoo product the ambiguous variant '
             'must live under.',
    )

    title_preview = fields.Char(readonly=True, string='Shopify title')
    sku_preview = fields.Char(readonly=True, string='Shopify SKU')
    barcode_preview = fields.Char(readonly=True, string='Shopify barcode')
    options_preview = fields.Char(readonly=True, string='Shopify options')
    candidate_total = fields.Integer(
        readonly=True, string='Candidates found',
        help='How many eligible Odoo records the importer found. More than '
             'one is why it stopped.',
    )
    candidate_template_ids = fields.Many2many(
        comodel_name='product.template',
        relation='shopify_match_decision_candidate_template_rel',
        column1='decision_id', column2='template_id',
        readonly=True, string='Candidate products seen',
    )
    candidate_variant_ids = fields.Many2many(
        comodel_name='product.product',
        relation='shopify_match_decision_candidate_variant_rel',
        column1='decision_id', column2='variant_id',
        readonly=True, string='Candidate variants seen',
    )

    state = fields.Selection(
        selection=[
            ('pending', 'Waiting for a decision'),
            ('confirmed', 'Decided - import resuming'),
            ('consumed', 'Applied'),
            ('superseded', 'Superseded'),
        ],
        required=True, default='pending', readonly=True, index=True,
    )
    selected_template_id = fields.Many2one(
        comodel_name='product.template', readonly=True, ondelete='restrict',
        check_company=True, string='Chosen product',
    )
    selected_variant_id = fields.Many2one(
        comodel_name='product.product', readonly=True, ondelete='restrict',
        check_company=True, string='Chosen variant',
    )
    resolved_uid = fields.Many2one(
        comodel_name='res.users', readonly=True, string='Decided by',
    )
    resolved_at = fields.Datetime(readonly=True, string='Decided on')
    resumed_job_state = fields.Char(
        readonly=True, string='Job state after resume',
        help='The state the confirmation actually left the source job in. '
             'Recorded at confirm time, so it is evidence the resume '
             'happened rather than an assumption that it did.',
    )
    consumed_at = fields.Datetime(readonly=True)
    resulting_template_binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.template.binding',
        readonly=True, ondelete='set null', string='Resulting binding',
    )
    resulting_variant_binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.variant.binding',
        readonly=True, ondelete='set null', string='Resulting variant binding',
    )
    superseded_reason = fields.Char(readonly=True)
    # The live state of the source job. A stored copy would be a second
    # source of truth that goes stale the moment the job moves; this cannot.
    job_state = fields.Selection(
        related='job_id.state', readonly=True, string='Source job state',
    )

    _store_decision_key_uniq = models.Constraint(
        'UNIQUE(store_id, decision_key)',
        'This product match ambiguity is already recorded for the store.',
    )

    @api.model
    def _sec3_parent_scope_relations(self):
        """Every connector relation this row must agree with, on STORE.

        All three carry a `store_id` of their own, so the store axis -- which
        is strictly stronger than company, because one company may own several
        stores -- is available for each and is what is used.
        """
        return (
            ('job_id', 'store'),
            ('resulting_template_binding_id', 'store'),
            ('resulting_variant_binding_id', 'store'),
        )

    @api.constrains(
        'store_id', 'job_id', 'resulting_template_binding_id',
        'resulting_variant_binding_id',
    )
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()

    @api.depends(
        'decision_level', 'shopify_product_gid', 'shopify_variant_gid',
    )
    def _compute_display_name(self):
        for decision in self:
            decision.display_name = '%s %s' % (
                dict(self._fields['decision_level'].selection).get(
                    decision.decision_level, 'Match',
                ),
                decision.shopify_variant_gid or decision.shopify_product_gid
                or '',
            )

    @api.constrains(
        'decision_level', 'selected_template_id', 'selected_variant_id',
        'resolved_template_id',
    )
    def _check_selection_matches_level(self):
        """A decision can only ever select the kind of record it is about.

        The company agreement is Odoo's own `_check_company` job (opted into
        above); this constraint is about level coherence, which nothing else
        enforces: a variant decision selecting a `product.template` would
        satisfy every company check and still be meaningless.
        """
        for decision in self:
            if decision.decision_level == DECISION_LEVEL_TEMPLATE:
                if decision.selected_variant_id:
                    raise ValidationError(
                        'A product-level match decision selects a product, '
                        'not a variant.'
                    )
            else:
                if decision.selected_template_id:
                    raise ValidationError(
                        'A variant-level match decision selects a variant, '
                        'not a product.'
                    )
                if (
                    decision.selected_variant_id
                    and decision.resolved_template_id
                    and decision.selected_variant_id.product_tmpl_id
                    != decision.resolved_template_id
                ):
                    raise ValidationError(
                        'The chosen variant must belong to the product the '
                        'Shopify variant was resolved under.'
                    )

    # ------------------------------------------------------------------
    # Recording (the dispatcher seam calls this, in the failure transaction)
    # ------------------------------------------------------------------

    @api.model
    def _record_from_failure(self, job, error_class, technical_detail):
        """Persist the decision this classified failure is about, if any.

        Total by design: every non-matching shape simply returns ``False``.
        This runs on EVERY routed failure in a database where the product
        module is installed, so it must be cheap and it must never raise --
        an exception here would escape the dispatcher's own failure handling
        and abort a drain that had already correctly blocked the job.
        """
        if error_class != MATCH_DECISION_ERROR_CLASS:
            return False
        if not job or job.job_type not in MATCH_DECISION_JOB_TYPES:
            return False
        evidence = parse_match_evidence(technical_detail)
        if not evidence:
            return False
        store = job.store_id
        if not store or not store.company_id:
            # A store whose company cannot be proved owns nothing a decision
            # could be scoped to. Fail closed rather than create a row the
            # company rule would then hide from everybody.
            return False
        try:
            with self.env.cr.savepoint():
                return self._persist_decision(job, store, evidence)
        except IntegrityError:
            # The unique key is the arbiter. A concurrent worker recording the
            # same ambiguity is not an error: its row is exactly the row this
            # call wanted to exist.
            existing = self.sudo().search([
                ('store_id', '=', store.id),
                ('decision_key', '=', decision_key_for(
                    evidence['level'], evidence['shopify_product_gid'],
                    evidence['shopify_variant_gid'],
                    evidence['remote_updated_at'],
                )),
            ], limit=1)
            return existing or False
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # NEVER swallowed. A genuine 40001/40P01/55P03 aborts the WHOLE
            # transaction, not just the savepoint, so absorbing it here would
            # leave the dispatcher's own `cr.flush()` to raise
            # `InFailedSqlTransaction` -- an error outside the set it knows how
            # to recover from, escaping the drain loop. Re-raised unchanged so
            # the dispatcher's existing per-job recovery handles it, exactly as
            # `_invoke_handler` re-raises it for the same reason.
            raise
        except Exception:  # pragma: no cover - defensive dispatcher boundary
            _logger.exception(
                "Could not record the product match decision for job %s; the "
                "job stays blocked and offers no decision.", job.id,
            )
            return False

    @api.model
    def _persist_decision(self, job, store, evidence):
        key = decision_key_for(
            evidence['level'], evidence['shopify_product_gid'],
            evidence['shopify_variant_gid'], evidence['remote_updated_at'],
        )
        Decision = self.sudo()
        existing = Decision.search([
            ('store_id', '=', store.id), ('decision_key', '=', key),
        ], limit=1)
        if existing:
            # Same ambiguity, same remote identity, seen again -- the job may
            # have been re-queued and re-failed. Re-point it at the job that
            # is blocked NOW, so confirming resumes work that is actually
            # waiting, and leave any decision already made alone.
            #
            # SAFE ONLY BECAUSE THE KEY IS OPAQUE IDENTITY. `key` now covers
            # the verbatim level, product GID, variant GID and remote
            # `updatedAt`, so "same key" means "same Shopify product at the
            # same remote version" and nothing else. Under `v1` two unrelated
            # products could share a key, and this branch would then re-point
            # product A's pending decision at product B's job -- a reviewer
            # deciding about A would resume the import of B.
            if existing.state == 'pending' and existing.job_id != job:
                existing.write({
                    'job_id': job.id,
                    'job_payload_hash': job.payload_hash or False,
                })
            return existing
        # A decision for the SAME target at a DIFFERENT remote identity is
        # about a product that has since changed. It can no longer be applied
        # (the importer would refuse it anyway), so it is superseded rather
        # than left looking actionable.
        self._supersede_stale_siblings(store, evidence, key)
        values = {
            'store_id': store.id,
            'job_id': job.id,
            'job_payload_hash': job.payload_hash or False,
            'decision_level': evidence['level'],
            'shopify_product_gid': evidence['shopify_product_gid'],
            'shopify_variant_gid': evidence['shopify_variant_gid'] or False,
            'remote_updated_at': evidence['remote_updated_at'],
            'decision_key': key,
            'match_key': evidence['match_key'],
            'match_value_digests': json.dumps(
                sorted(evidence['match_value_digests']),
            ),
            'resolved_template_id': evidence['resolved_template_id'] or False,
            'title_preview': evidence['title_preview'] or False,
            'sku_preview': evidence['sku_preview'] or False,
            'barcode_preview': evidence['barcode_preview'] or False,
            'options_preview': evidence['options_preview'] or False,
            'candidate_total': evidence['candidate_total'],
            'state': 'pending',
        }
        # The candidate snapshot is filtered to records that still exist and
        # still belong to the store's company. A stale id from the payload
        # must never become an m2m row pointing at another company's product.
        if evidence['level'] == DECISION_LEVEL_TEMPLATE:
            values['candidate_template_ids'] = [(6, 0, self._same_company_ids(
                'product.template', evidence['candidate_ids'], store,
            ))]
        else:
            values['candidate_variant_ids'] = [(6, 0, self._same_company_ids(
                'product.product', evidence['candidate_ids'], store,
            ))]
        return Decision.create(values)

    @api.model
    def _same_company_ids(self, model_name, ids, store):
        if not ids:
            return []
        records = self.env[model_name].sudo().browse(ids).exists()
        return records.filtered(
            lambda record: not record.company_id
            or record.company_id == store.company_id
        ).ids

    @api.model
    def _supersede_stale_siblings(self, store, evidence, key):
        """Supersede this EXACT product/variant at an OLDER remote identity.

        Every leaf is opaque identity, so the search reaches the same Shopify
        product or variant and no other. Under `v1` these were the sanitized
        copies, and `shopify_product_gid = 'gid://shopify/Product/[redacted-
        phone]'` matched every product in the catalog whose numeric suffix was
        long enough -- so one new ambiguity superseded unrelated merchants'
        pending decisions wholesale.

        `remote_updated_at <` is the "older" half, and it is a deliberate
        BYTE comparison of an opaque value rather than a parsed timestamp. For
        Shopify's ISO-8601 UTC stamps the two orders coincide; where they would
        not, this refuses to act rather than guessing, which leaves the other
        decision pending and unconsumable for this identity (`_confirmed_for`
        keys on the exact identity) instead of silently retiring something that
        may describe a NEWER version than the payload in hand.
        """
        stale = self.sudo().search([
            ('store_id', '=', store.id),
            ('decision_level', '=', evidence['level']),
            ('shopify_product_gid', '=', evidence['shopify_product_gid']),
            (
                'shopify_variant_gid', '=',
                evidence['shopify_variant_gid'] or False,
            ),
            ('decision_key', '!=', key),
            ('remote_updated_at', '<', evidence['remote_updated_at']),
            ('state', 'in', ('pending', 'confirmed')),
        ])
        if stale:
            stale.write({
                'state': 'superseded',
                'superseded_reason': (
                    'The Shopify product changed after this decision was '
                    'recorded, so it no longer describes what would be '
                    'imported. A fresh decision was raised for the new '
                    'version.'
                ),
            })

    # ------------------------------------------------------------------
    # Eligibility (recomputed, never replayed)
    # ------------------------------------------------------------------

    def _match_value_digest_set(self):
        self.ensure_one()
        try:
            values = json.loads(self.match_value_digests or '[]')
        except (TypeError, ValueError):
            return frozenset()
        if not isinstance(values, list):
            return frozenset()
        return frozenset(
            value for value in list(values)[:MATCH_VALUES_LIMIT]
            if _is_match_digest(value)
        )

    def _identifier_matches(self, record, field_name, digests):
        """Does this LIVE record still carry an identifier Shopify sent?

        Digest to digest, recomputed from the record in front of us. Nothing
        here reads the remote value, and nothing here trusts the payload's
        opinion of which records matched.
        """
        value = record[field_name]
        if not value:
            return False
        return match_value_digest(self.env, value) in digests

    def eligible_candidates(self):
        """The candidates a decision could legitimately select, right now.

        TWO CHANGES FROM `v1`, AND BOTH ARE THE CORRECTION.

        *The search is gone.* `v1` re-searched the whole product table for the
        stored match values -- which were display-sanitized, so a numeric SKU
        searched for the literal string `[redacted-phone]` and matched nothing.
        Evaluation is now confined to the BOUNDED CANDIDATE SNAPSHOT the
        importer actually produced, which is also the only set the reviewer was
        ever shown evidence about.

        *Membership of that snapshot is not eligibility.* A candidate id is
        merchant-influenced data that arrived on an exception payload, so a
        forged id that happens to belong to the right company must not become
        selectable. Every candidate's LIVE identifier is digested here and
        compared against the exact remote evidence; one that does not carry the
        identifier Shopify sent is refused, whatever the payload claimed.

        The rest of the predicate is unchanged and is deliberately the one the
        importer matches on -- the store's already-bound exclusion and company
        agreement -- so the list on screen is a list the importer would accept
        and the binding's own `check_company` would not refuse.

        The already-bound exclusion is read under `sudo()` on purpose. It is
        an exclusion set: elevating it can only ever REMOVE a candidate, never
        add one, and it discloses nothing -- the ids never leave this method,
        and every row it reads belongs to the store already in scope. Reading
        it as the caller could hide a binding from the exclusion and let a
        candidate through that the importer would then refuse.
        """
        self.ensure_one()
        is_template = self.decision_level == DECISION_LEVEL_TEMPLATE
        empty = (
            self.env['product.template'].browse() if is_template
            else self.env['product.product'].browse()
        )
        digests = self._match_value_digest_set()
        if not digests or self.match_key not in MATCH_KEY_FIELD:
            return empty
        field_name = MATCH_KEY_FIELD[self.match_key]
        company = self.store_id.company_id
        if is_template:
            bound_ids = set(self.env[
                'shopify.connector.product.template.binding'
            ].sudo().search(
                [('store_id', '=', self.store_id.id)]
            ).mapped('product_template_id').ids)
            return self.candidate_template_ids.exists().filtered(
                lambda template: template.id not in bound_ids
                and (
                    not template.company_id or template.company_id == company
                )
                and any(
                    self._identifier_matches(variant, field_name, digests)
                    for variant in template.product_variant_ids
                )
            )
        if not self.resolved_template_id:
            return empty
        bound_ids = set(self.env[
            'shopify.connector.product.variant.binding'
        ].sudo().search(
            [('store_id', '=', self.store_id.id)]
        ).mapped('product_variant_id').ids)
        return self.candidate_variant_ids.exists().filtered(
            lambda product: product.id not in bound_ids
            and (not product.company_id or product.company_id == company)
            and product.product_tmpl_id == self.resolved_template_id
            and self._identifier_matches(product, field_name, digests)
        )

    # ------------------------------------------------------------------
    # Consumption (the importer calls this, inside its savepoint)
    # ------------------------------------------------------------------

    @api.model
    def _confirmed_for(
        self, store, level, product_gid, variant_gid, remote_updated_at,
        job=None,
    ):
        """The confirmed decision for this EXACT remote identity, or empty.

        The identity comparison is the whole guarantee. A product edited on
        Shopify after the decision was confirmed carries a different
        `updatedAt`, produces a different key, and therefore finds nothing
        here -- the ambiguity is raised again and reviewed again against what
        is there now.

        THE VALUES ARRIVE RAW AND ARE USED RAW. They come straight off the
        payload the importer just fetched, and they are validated by exactly
        the function that validated them when the decision was written, so
        either both ends agree byte for byte or this returns nothing. `v1`
        sanitized one end and not the other, which made every confirmed
        decision unconsumable and sent the merchant back to the same ambiguity.
        """
        product_gid = opaque_identity(product_gid or '', MATCH_GID_MAX_LEN)
        updated_at = opaque_identity(
            remote_updated_at or '', MATCH_UPDATED_AT_MAX_LEN,
        )
        if not product_gid or not updated_at or level not in DECISION_LEVELS:
            return self.browse()
        variant_gid = opaque_identity(variant_gid or '', MATCH_GID_MAX_LEN)
        if level == DECISION_LEVEL_VARIANT and not variant_gid:
            return self.browse()
        if level == DECISION_LEVEL_TEMPLATE and variant_gid:
            return self.browse()
        key = decision_key_for(
            level, product_gid, variant_gid, updated_at,
        )
        decision = self.sudo().search([
            ('store_id', '=', store.id),
            ('decision_key', '=', key),
            ('state', '=', 'confirmed'),
        ], limit=1)
        if not decision:
            return decision
        # THE JOB'S OWN ENQUEUED IDENTITY, checked at CONSUMPTION and not only
        # at confirmation. `_validated_decision` compares `payload_hash` when
        # the reviewer presses the button; this is the other end of the same
        # guarantee, and it is the one that runs while a binding is about to be
        # created. A decision recorded against one enqueued payload must not be
        # applied by work admitted under a different one.
        if job is not None and (
            (job.payload_hash or False)
            != (decision.job_payload_hash or False)
        ):
            return self.browse()
        return decision

    def action_open_decision(self):
        """Open the dialog from the decision itself, via the blocked job.

        Deliberately routed through the job rather than opening the wizard
        directly: `action_open_product_match_decision` is where the role
        assertion, the caller-environment access checks and the "is this job
        still blocked for this reason" test live, and having two ways in
        would mean two places for those checks to drift apart.
        """
        self.ensure_one()
        return self.job_id.action_open_product_match_decision()

    def _mark_consumed(self, template_binding=False, variant_binding=False):
        self.ensure_one()
        values = {
            'state': 'consumed',
            'consumed_at': fields.Datetime.now(),
        }
        if template_binding:
            values['resulting_template_binding_id'] = template_binding.id
        if variant_binding:
            values['resulting_variant_binding_id'] = variant_binding.id
        self.sudo().write(values)
        return True


class ShopifyConnectorJobProductMatch(models.Model):
    """The job-side seam: is a product match decision waiting on this job?"""

    _inherit = 'shopify.connector.job'

    product_match_decision_ids = fields.One2many(
        comodel_name='shopify.connector.product.match.decision',
        inverse_name='job_id',
        string='Product match decisions',
    )
    product_match_decision_pending = fields.Boolean(
        compute='_compute_product_match_decision_pending',
        string='Waiting for a product match',
        help='This import stopped because more than one Odoo record carries '
             'the identifier the Shopify product claims.',
    )

    @api.depends('product_match_decision_ids.state', 'state', 'error_class')
    def _compute_product_match_decision_pending(self):
        for job in self:
            job.product_match_decision_pending = bool(
                job._pending_product_match_decision()
            )

    def _pending_product_match_decision(self):
        """The decision blocking this job, or an empty recordset.

        Structural on every axis: job type, job state, error class, and a
        decision row in `pending`. Nothing here reads a message.
        """
        self.ensure_one()
        if self.job_type not in MATCH_DECISION_JOB_TYPES:
            return self.env['shopify.connector.product.match.decision'].browse()
        if self.state != MATCH_DECISION_JOB_STATE:
            return self.env['shopify.connector.product.match.decision'].browse()
        if self.error_class != MATCH_DECISION_ERROR_CLASS:
            return self.env['shopify.connector.product.match.decision'].browse()
        return self.env[
            'shopify.connector.product.match.decision'
        ].sudo().search([
            ('job_id', '=', self.id), ('state', '=', 'pending'),
        ], limit=1)

    def action_resolve_manual_review(self):
        """Refuse the generic resolution while a real decision is waiting.

        §8.2.14. The generic route sets the job back to `queued` and clears
        the subreason -- which for an ambiguous match means running the exact
        same search again, finding the exact same candidates, and stopping
        again. Offering it as though it were a resolution is the
        false-capability failure this batch exists to remove. It is refused
        with the route that DOES resolve it named in the refusal.
        """
        for job in self:
            if job._pending_product_match_decision():
                raise UserError(
                    'This import is waiting for a product match decision, '
                    'not for a generic review. Re-queueing it would run the '
                    'same search and stop at the same ambiguity. Open '
                    '"Choose the matching Odoo product" on the job and pick '
                    'the record this Shopify product means.'
                )
        return super().action_resolve_manual_review()

    def action_open_product_match_decision(self):
        """Open the decision dialog for this job (Administrator only).

        Whoever may resolve a `blocked_manual_review` job may make this
        decision, because confirming it resumes exactly that job through
        exactly that route. An ordinary Connector User may start an import and
        may not decide a match.
        """
        self.ensure_one()
        self.env['shopify.connector.product.match.decision.wizard'] \
            ._assert_match_decision_reviewer()
        # The caller's own read access, in the caller's own environment,
        # before anything is disclosed about the job or its store.
        self.check_access('read')
        decision = self._pending_product_match_decision()
        if not decision:
            raise UserError(
                'This job is not waiting for a product match decision.'
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Choose the matching Odoo product',
            'res_model': 'shopify.connector.product.match.decision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_decision_id': decision.id},
        }

    def _attention_resolution_action(self):
        """Make Needs Attention's primary action open the real decision."""
        self.ensure_one()
        if self._pending_product_match_decision():
            return self.action_open_product_match_decision()
        return super()._attention_resolution_action()


class ShopifyConnectorProductMatchDispatch(models.AbstractModel):
    """The dispatcher seam, and the only reason it exists.

    `_route_failure` runs AFTER the importer's savepoint has already rolled
    back -- the exception that carries the evidence is what unwound it -- and
    in the same transaction that durably writes `blocked_manual_review`. That
    makes it the one place a decision can be recorded so that it survives
    exactly when the block survives, and disappears exactly when the block
    disappears. `super()` is called first so the job is transitioned before
    anything is linked to it, and so a failure to record can never leave the
    job un-routed.
    """

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _route_failure(self, job, error_class, reason, technical_detail=False):
        routed = super()._route_failure(
            job, error_class, reason, technical_detail,
        )
        self.env[
            'shopify.connector.product.match.decision'
        ]._record_from_failure(job, error_class, technical_detail)
        return routed
