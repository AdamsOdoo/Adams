import hashlib
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.shopify_connector_core.tools.redaction import redact


SHOPIFY_TAX_FINGERPRINT_VERSION = 1
TAX_RATE_QUANTUM = Decimal('0.000001')
TAX_TITLE_PREVIEW_MAX_LEN = 80
TAX_SOURCE_PREVIEW_MAX_LEN = 48
_EMAIL_RE = re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b')
_PHONE_RE = re.compile(r'(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)')


def _decimal_rate(value, label):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError('%s must be a decimal value.' % label) from exc
    if not parsed.is_finite():
        raise ValidationError('%s must be finite.' % label)
    return parsed


def canonical_tax_rate(rate, rate_percentage):
    """Return the verified canonical percentage string (never a float)."""
    proportion = _decimal_rate(rate, 'TaxLine.rate')
    percentage = _decimal_rate(
        rate_percentage, 'TaxLine.ratePercentage',
    )
    if (proportion * Decimal('100') - percentage).copy_abs() > TAX_RATE_QUANTUM:
        raise ValidationError(
            'TaxLine.rate and TaxLine.ratePercentage disagree.'
        )
    try:
        quantized = percentage.quantize(TAX_RATE_QUANTUM)
    except InvalidOperation as exc:
        raise ValidationError(
            'TaxLine.ratePercentage cannot be represented at six decimals.'
        ) from exc
    rendered = format(quantized, 'f').rstrip('0').rstrip('.')
    return rendered or '0'


def _length_prefixed(parts):
    payload = bytearray()
    for part in parts:
        encoded = part.encode('utf-8')
        payload.extend(len(encoded).to_bytes(8, byteorder='big'))
        payload.extend(encoded)
    return bytes(payload)


def build_tax_fingerprint(
    rate, rate_percentage, title, source, channel_liable, price_included,
):
    """Build the accepted v1, fold-free, full-tuple SHA-256 fingerprint."""
    if not isinstance(title, str):
        raise ValidationError('TaxLine.title must be a string.')
    if source is not None and not isinstance(source, str):
        raise ValidationError('TaxLine.source must be a string or null.')
    if channel_liable is not None and not isinstance(channel_liable, bool):
        raise ValidationError('TaxLine.channelLiable must be Boolean or null.')
    if not isinstance(price_included, bool):
        raise ValidationError('Order.taxesIncluded must be Boolean.')
    rate_key = canonical_tax_rate(rate, rate_percentage)
    title_norm = unicodedata.normalize('NFC', title)
    source_norm = (
        unicodedata.normalize('NFC', source)
        if source is not None else '\u2205'
    )
    liable = (
        'null' if channel_liable is None
        else 'true' if channel_liable else 'false'
    )
    inclusion = 'included' if price_included else 'excluded'
    serialized = _length_prefixed((
        str(SHOPIFY_TAX_FINGERPRINT_VERSION), rate_key, title_norm,
        source_norm, liable, inclusion,
    ))
    return 'v%d:%s' % (
        SHOPIFY_TAX_FINGERPRINT_VERSION,
        hashlib.sha256(serialized).hexdigest(),
    )


def safe_tax_preview(value, limit):
    value = redact(value or '')
    value = _EMAIL_RE.sub('[redacted-email]', value)
    value = _PHONE_RE.sub('[redacted-phone]', value)
    return value[:limit]


# ----------------------------------------------------------------------
# THE ONE ELIGIBILITY RULE. There is exactly one, and everything that has an
# opinion about whether an Odoo tax may stand for a Shopify tax asks it here:
# the mapping model's own constraint, the decision wizard's candidate list, the
# importer's non-binding suggestions, and the importer's validation of a
# resolved tax. Four copies of this rule drifted once already and the drift is
# what F4 found; `test_tax_posture_rule_is_shared` proves the search predicate
# and the per-record predicate still agree on every tax in the database.
# ----------------------------------------------------------------------

def tax_posture_included(tax):
    """Odoo's EFFECTIVE tax-inclusion posture for one tax.

    `account.tax.price_include` (Odoo 19, `addons/account/models/account_tax.py`
    at pin `30bde9ff`, `_compute_price_include`) is:

        price_include_override == 'tax_included'
        or (company_price_include == 'tax_included' and not
            price_include_override)

    -- that is, the override when one is set, and the COMPANY DEFAULT
    (`res.company.account_price_include`) when one is not. `price_include_override`
    is an override and is legitimately empty on an ordinary tax.

    Reading the raw override instead of this was F4. On a company whose default
    is `tax_excluded` -- Odoo's own default -- every ordinary tax has
    `price_include_override = False`, so `override == 'tax_excluded'` was false
    for all of them and NO tax in the database was eligible for an excluded
    Shopify tax. The merchant was told to "create the tax first and come back",
    and creating it did not help.
    """
    return bool(tax.price_include)


def eligible_sale_tax_domain(company, price_included, amount):
    """The search form of the same rule.

    `('price_include', '=', ...)` is a real searchable leaf: the field declares
    `search='_search_price_include'`, and Odoo 19's boolean domain optimisation
    (`odoo/orm/domains.py::_optimize_boolean_in`) rewrites `in [False]` to
    `not in [True]`, which is the one shape that search method accepts. So both
    postures resolve, in SQL, to the same override-or-company-default
    disjunction `tax_posture_included` computes in Python.

    Every other leaf is unchanged and deliberately narrow: exact company, active,
    sale, leaf percentage, exact rate, and not base-affecting.
    """
    return [
        ('company_id', '=', company.id),
        ('active', '=', True),
        ('type_tax_use', '=', 'sale'),
        ('amount_type', '=', 'percent'),
        ('amount', '=', amount),
        ('include_base_amount', '=', False),
        ('price_include', '=', bool(price_included)),
    ]


class ShopifyConnectorTaxMapping(models.Model):
    """Admin-maintained explicit mapping from Shopify evidence to Odoo tax."""

    _name = 'shopify.connector.tax.mapping'
    _description = 'Shopify Connector Tax Mapping'

    # SEC-3 (#197): opt in to Odoo 19's native company consistency check
    # (`odoo/orm/models.py` L451/L4516/L4743). Together with `check_company=True`
    # on the business relation below, a store can only ever bind a record of its
    # own company -- enforced on create AND write, and under `sudo()`.
    _check_company_auto = True

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store', required=True, index=True,
        ondelete='restrict',
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
    shopify_tax_evidence_key = fields.Char(
        required=True, index=True, readonly=True,
    )
    shopify_tax_fingerprint_version = fields.Integer(
        required=True, default=SHOPIFY_TAX_FINGERPRINT_VERSION, readonly=True,
    )
    shopify_price_included = fields.Boolean(readonly=True)
    title_preview = fields.Char(readonly=True)
    source_preview = fields.Char(readonly=True)
    account_tax_id = fields.Many2one(
        comodel_name='account.tax', required=True, ondelete='restrict',
        check_company=True,
    )

    _store_evidence_key_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_tax_evidence_key)',
        'This Shopify tax fingerprint is already mapped for the store.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            self._assert_evidence_key(vals.get('shopify_tax_evidence_key'))
            self._sanitize_previews(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if 'shopify_tax_evidence_key' in vals:
            self._assert_evidence_key(vals.get('shopify_tax_evidence_key'))
        self._sanitize_previews(vals)
        return super().write(vals)

    @api.model
    def _sanitize_previews(self, vals):
        if 'title_preview' in vals:
            vals['title_preview'] = safe_tax_preview(
                vals.get('title_preview'), TAX_TITLE_PREVIEW_MAX_LEN,
            )
        if 'source_preview' in vals:
            vals['source_preview'] = safe_tax_preview(
                vals.get('source_preview'), TAX_SOURCE_PREVIEW_MAX_LEN,
            )

    @api.model
    def _assert_evidence_key(self, key):
        key = key or ''
        expected_prefix = 'v%d:' % SHOPIFY_TAX_FINGERPRINT_VERSION
        digest = key[len(expected_prefix):] if key.startswith(expected_prefix) else ''
        if (
            len(digest) != 64
            or any(character not in '0123456789abcdef' for character in digest)
        ):
            raise ValidationError(
                'The tax evidence key must be a complete lowercase v1 '
                'SHA-256 fingerprint.'
            )

    @api.constrains(
        'store_id', 'account_tax_id', 'shopify_price_included',
        'shopify_tax_fingerprint_version',
    )
    def _check_mapping_safety(self):
        Settings = self.env['shopify.connector.store.settings']
        for mapping in self:
            settings = Settings.search([
                ('store_id', '=', mapping.store_id.id),
            ], limit=1)
            tax = mapping.account_tax_id
            if not settings or not settings.order_company_id:
                raise ValidationError(
                    'Order company must be configured before tax mapping.'
                )
            if tax.company_id != settings.order_company_id:
                raise ValidationError(
                    'The mapped tax must belong to the configured order company.'
                )
            if not tax.active or tax.type_tax_use != 'sale':
                raise ValidationError('The mapped tax must be an active sale tax.')
            if tax.amount_type != 'percent':
                raise ValidationError(
                    'Only independent leaf percentage taxes are supported.'
                )
            if tax.include_base_amount:
                raise ValidationError(
                    'Base-affecting compound taxes are not supported.'
                )
            # THE EFFECTIVE POSTURE, not the override. See
            # `tax_posture_included`: an ordinary tax on a company whose
            # default is `tax_excluded` carries no override at all, and reading
            # the override made every such tax permanently unmappable.
            if tax_posture_included(tax) != bool(mapping.shopify_price_included):
                raise ValidationError(
                    'The mapped tax inclusion posture does not match Shopify.'
                )
            if (
                mapping.shopify_tax_fingerprint_version
                != SHOPIFY_TAX_FINGERPRINT_VERSION
            ):
                raise ValidationError('Unsupported tax fingerprint version.')

    def unlink(self):
        if not self.env.su:
            raise AccessError('Shopify tax mappings cannot be deleted.')
        return super().unlink()
