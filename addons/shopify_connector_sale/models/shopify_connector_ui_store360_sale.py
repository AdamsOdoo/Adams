# Part of the Shopify Connector (Store 360 slice 1, sale-owned sections).
#
# Commercial, bridge, trend, top-product and order-lifecycle sections of
# the Store 360 payload. Contributed through the core dashboard's
# `_store_360_extra_sections` seam — core depends only on `base`/`web` and
# must stay installable alone, so everything that reads `sale.order` /
# `sale.order.line` lives here, in the module that owns the sale extension
# seam.
#
# THE SECURITY CONTRACT (spec §6.1, the accepted same-model principle):
# every commercial and lifecycle number is aggregated ON `sale.order` (or
# `sale.order.line` for line-grain numbers) AS THE CURRENT USER, with the
# caller's own ACLs and record rules fully active, and its drill-down is a
# native list of that SAME model built from the IDENTICAL server-built
# domain. No `sudo()`, no raw SQL, no client-supplied domain, no hidden
# record id, label, state or timestamp in the payload: a rule-restricted
# caller sees aggregates over exactly the records their own list shows.
#
# Mixed currencies are never combined (task §7.8): every monetary figure is
# partitioned by `currency_id` inside one grouped read; non-monetary counts
# (orders, units) may total across the partition.

import logging
from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

# The §9.3 checkpoint-age threshold: 3× the 15-minute scan cron.
_CHECKPOINT_FRESH = timedelta(minutes=45)

_ORDER_JOB_TYPES = ('order_import_scan', 'order_import_sync')
_G2_STATES = ('draft', 'queued', 'running', 'retry_waiting')
_G3_STATES = ('failed_retryable', 'failed_final', 'blocked_manual_review')

_KNOWN_FULFILLMENT_BUCKETS = ('FULFILLED', 'PARTIALLY_FULFILLED',
                              'UNFULFILLED')


class ShopifyConnectorUiStore360Sale(models.AbstractModel):
    _inherit = 'shopify.connector.ui.dashboard'

    # ------------------------------------------------------------------ #
    #  Section seam
    # ------------------------------------------------------------------ #
    def _store_360_extra_sections(self, ctx):
        sections = super()._store_360_extra_sections(ctx)
        bridge = self._store_360_bridge(ctx)
        sections['bridge'] = bridge
        try:
            sections['commercial'] = self._store_360_commercial(ctx)
            sections['lifecycle'] = self._store_360_lifecycle(ctx)
        except AccessError:
            # Honest no-permission variant (spec §9.4.3): the caller's own
            # sale ACL/rules refused the read. Never rendered as zeros;
            # connector health is unaffected.
            refusal = {'available': False, 'reason': 'no_permission'}
            sections['commercial'] = dict(refusal)
            sections['lifecycle'] = dict(refusal)
        return sections

    # ------------------------------------------------------------------ #
    #  Shared domains (the ONE C1 population definition)
    # ------------------------------------------------------------------ #
    def _store_360_order_domain(self, ctx, which='current', review=False):
        """The C1 population: imported, non-cancelled, non-quarantined
        Shopify orders of the selected scope, `date_order` in the window.
        The reconciled population excludes review rows; passing ``review``
        builds the separately disclosed review population with every other
        scope/exclusion term identical. Used verbatim for every order-grain
        aggregate AND its drill-down."""
        store = ctx['store']
        window = ctx['window']
        if which == 'current':
            start, end = window['start'], window['end']
            # INCLUSIVE current end: `end` is "now" truncated to the second,
            # and an order imported within that same second would satisfy
            # neither `< end` nor the next refresh's `>= start` shift — a
            # figure that silently drops the newest order for a second is
            # exactly the shape §7's truth rules forbid. The previous window
            # stays half-open below, so the two windows remain disjoint.
            end_term = ('date_order', '<=', end)
        else:
            start, end = window['prev_start'], window['prev_end']
            end_term = ('date_order', '<', end)
        domain = [
            ('shopify_connector_quarantined', '=', False),
            ('shopify_connector_cancelled_at', '=', False),
            ('shopify_connector_review', '=', bool(review)),
            ('state', '!=', 'cancel'),
            ('date_order', '>=', start),
            end_term,
        ]
        if len(store) == 1:
            domain.insert(0, ('shopify_connector_store_id', '=', store.id))
        else:
            domain.insert(0, ('shopify_connector_store_id', '!=', False))
        return domain

    def _store_360_line_domain(self, ctx, which='current'):
        """The C4/E1 goods-line population: Shopify goods lines (the
        `shopify_line_item_gid` marker excludes shipping/residual lines) of
        the C1 order population."""
        order_domain = self._store_360_order_domain(ctx, which)
        return [('shopify_line_item_gid', '!=', False)] + [
            ('order_id.%s' % field, operator, value)
            for field, operator, value in order_domain
        ]

    @api.model
    def _serialize_domain(self, domain):
        return [list(term) if isinstance(term, (list, tuple)) else term
                for term in domain]

    @api.model
    def _currency_info(self, currency):
        return {
            'id': currency.id,
            'name': currency.name,
            'symbol': currency.symbol,
            'decimal_places': currency.decimal_places,
            'position': currency.position,
        }

    # ------------------------------------------------------------------ #
    #  Commercial cards (C1–C4, C∆), trend (D1), products (E1/E2)
    # ------------------------------------------------------------------ #
    def _store_360_commercial(self, ctx):
        Order = self.env['sale.order'].with_context(tz=ctx['window']['tz'])
        Line = self.env['sale.order.line'].with_context(
            tz=ctx['window']['tz'])
        current_domain = self._store_360_order_domain(ctx, 'current')
        prev_domain = self._store_360_order_domain(ctx, 'previous')
        review_domain = self._store_360_order_domain(
            ctx, 'current', review=True,
        )

        current_rows = Order._read_group(
            current_domain, groupby=['currency_id'],
            aggregates=['amount_total:sum', '__count'],
        )
        prev_rows = {
            currency.id: (total, count)
            for currency, total, count in Order._read_group(
                prev_domain, groupby=['currency_id'],
                aggregates=['amount_total:sum', '__count'],
            )
        }
        review_blocks = []
        for currency, total, count in Order._read_group(
            review_domain, groupby=['currency_id'],
            aggregates=['amount_total:sum', '__count'],
        ):
            review_blocks.append({
                'currency': self._currency_info(currency),
                'value': total or 0.0,
                'count': count,
                'target': {
                    'res_model': 'sale.order',
                    'domain': self._serialize_domain(
                        review_domain + [('currency_id', '=', currency.id)]
                    ),
                    'name': _(
                        "Orders awaiting data review — %(currency)s",
                        currency=currency.name,
                    ),
                },
            })
        review_blocks.sort(key=lambda block: block['currency']['name'])
        blocks = []
        for currency, total, count in current_rows:
            prev_total, prev_count = prev_rows.get(
                currency.id, (0.0, 0),
            )
            blocks.append({
                'currency': self._currency_info(currency),
                'orders_target': {
                    'res_model': 'sale.order',
                    'domain': self._serialize_domain(
                        current_domain + [('currency_id', '=', currency.id)]
                    ),
                    'name': _("Imported Odoo orders — %(currency)s",
                              currency=currency.name),
                },
                'sales': total or 0.0,
                # Declared-scope lifecycle policy: every refund/divergence
                # lands in the separately disclosed review population and is
                # excluded from this reconciled population. Gross and net are
                # therefore equal here and reconciled refunds are zero; the
                # dashboard states that limitation instead of implying a
                # refund ledger the supported kernel does not maintain.
                'gross': total or 0.0,
                'refunds': 0.0,
                'net': total or 0.0,
                'orders': count,
                'aov': (total / count) if count else False,
                'previous': {
                    'sales': prev_total or 0.0,
                    'gross': prev_total or 0.0,
                    'refunds': 0.0,
                    'net': prev_total or 0.0,
                    'orders': prev_count,
                    'aov': (prev_total / prev_count) if prev_count else False,
                },
            })
        # A currency present only in the previous window still needs a
        # truthful comparison row (previous value non-zero, current zero).
        seen = {block['currency']['id'] for block in blocks}
        for currency_id, (prev_total, prev_count) in prev_rows.items():
            if currency_id in seen:
                continue
            currency = self.env['res.currency'].browse(currency_id)
            blocks.append({
                'currency': self._currency_info(currency),
                'orders_target': {
                    'res_model': 'sale.order',
                    'domain': self._serialize_domain(
                        current_domain + [('currency_id', '=', currency.id)]
                    ),
                    'name': _("Imported Odoo orders — %(currency)s",
                              currency=currency.name),
                },
                'sales': 0.0,
                'gross': 0.0,
                'refunds': 0.0,
                'net': 0.0,
                'orders': 0,
                'aov': False,
                'previous': {
                    'sales': prev_total or 0.0,
                    'gross': prev_total or 0.0,
                    'refunds': 0.0,
                    'net': prev_total or 0.0,
                    'orders': prev_count,
                    'aov': (prev_total / prev_count) if prev_count else False,
                },
            })
        blocks.sort(key=lambda block: -(block['sales'] or 0.0))

        current_line_domain = self._store_360_line_domain(ctx, 'current')
        prev_line_domain = self._store_360_line_domain(ctx, 'previous')
        units_rows = Line._read_group(
            current_line_domain, aggregates=['product_uom_qty:sum'],
        )
        prev_units_rows = Line._read_group(
            prev_line_domain, aggregates=['product_uom_qty:sum'],
        )
        units = (units_rows[0][0] or 0.0) if units_rows else 0.0
        prev_units = (prev_units_rows[0][0] or 0.0) if prev_units_rows else 0.0

        orders_total = sum(block['orders'] for block in blocks)
        result = {
            'available': True,
            'blocks': blocks,
            'orders_total': orders_total,
            'units': units,
            'previous_units': prev_units,
            'orders_target': {
                'res_model': 'sale.order',
                'domain': self._serialize_domain(current_domain),
                'name': _("Imported Odoo orders"),
            },
            'units_target': {
                'res_model': 'sale.order.line',
                'domain': self._serialize_domain(current_line_domain),
                'name': _("Imported Odoo order lines"),
            },
            'awaiting_review': {
                'count': sum(block['count'] for block in review_blocks),
                'blocks': review_blocks,
                'target': {
                    'res_model': 'sale.order',
                    'domain': self._serialize_domain(review_domain),
                    'name': _("Imported orders awaiting data review"),
                },
            },
            'refund_scope_note': _(
                "Refunded or otherwise divergent imported orders are shown "
                "under Awaiting data review and excluded from gross, net, "
                "refund, and average-order-value figures."
            ),
        }
        primary = blocks[0] if blocks else False
        result['trend'] = self._store_360_trend(
            ctx, Order, current_domain, prev_domain,
            primary['currency'] if primary else False,
        )
        result['products'] = self._store_360_products(
            ctx, Line, current_line_domain,
            primary['currency'] if primary else False,
        )
        return result

    def _store_360_trend(self, ctx, Order, current_domain, prev_domain,
                         primary_currency):
        """D1: per-bucket sums for the primary currency, plus the previous
        period as an aligned comparison series. Buckets are user-timezone
        (the tz travels in the read context); day granularity, hour-of-day
        for the 24h period."""
        window = ctx['window']
        if not primary_currency:
            return {'available': False, 'reason': 'no_data', 'buckets': []}
        currency_term = [('currency_id', '=', primary_currency['id'])]
        if ctx['period'] == '24h':
            groupby = 'date_order:hour_number'
        else:
            groupby = 'date_order:day'
        rows = Order._read_group(
            current_domain + currency_term,
            groupby=[groupby], aggregates=['amount_total:sum', '__count'],
        )
        prev_rows = Order._read_group(
            prev_domain + currency_term,
            groupby=[groupby], aggregates=['amount_total:sum', '__count'],
        )

        def _bucket_key(value):
            if value is None or value is False:
                return False
            if isinstance(value, int):
                return value
            return fields.Date.to_string(
                value.date() if hasattr(value, 'date') else value
            )

        current = {
            _bucket_key(group): (total or 0.0, count)
            for group, total, count in rows
        }
        previous = {
            _bucket_key(group): (total or 0.0, count)
            for group, total, count in prev_rows
        }
        buckets = []
        if ctx['period'] == '24h':
            ordered = list(range(24))
            for hour in ordered:
                buckets.append({
                    'label': '%02d:00' % hour,
                    'value': current.get(hour, (0.0, 0))[0],
                    'orders': current.get(hour, (0.0, 0))[1],
                    'previous': previous.get(hour, (0.0, 0))[0],
                })
        else:
            try:
                tz = pytz.timezone(window['tz'])
            except pytz.UnknownTimeZoneError:
                tz = pytz.utc
            start_local = pytz.utc.localize(
                window['start']).astimezone(tz)
            end_local = pytz.utc.localize(window['end']).astimezone(tz)
            prev_start_local = pytz.utc.localize(
                window['prev_start']).astimezone(tz)
            day = start_local.date()
            prev_day = prev_start_local.date()
            last_day = end_local.date()
            while day <= last_day:
                key = fields.Date.to_string(day)
                prev_key = fields.Date.to_string(prev_day)
                buckets.append({
                    'label': key,
                    'value': current.get(key, (0.0, 0))[0],
                    'orders': current.get(key, (0.0, 0))[1],
                    'previous': previous.get(prev_key, (0.0, 0))[0],
                })
                day += timedelta(days=1)
                prev_day += timedelta(days=1)
        return {
            'available': bool(buckets),
            'currency': primary_currency,
            'tz': window['tz'],
            'buckets': buckets,
            'target': {
                'res_model': 'sale.order',
                'domain': self._serialize_domain(
                    current_domain + currency_term),
                'name': _("Imported Odoo orders"),
            },
        }

    def _store_360_products(self, ctx, Line, current_line_domain,
                            primary_currency):
        """E1/E2: top five goods lines by untaxed subtotal within the
        primary currency; share basis is the TOTAL ELIGIBLE GOODS SUBTOTAL
        of the same population — never the tax-and-shipping-bearing
        headline (correction §6C)."""
        if not primary_currency:
            return {'available': False, 'reason': 'no_data', 'rows': []}
        currency_term = [
            ('order_id.currency_id', '=', primary_currency['id']),
        ]
        domain = current_line_domain + currency_term
        top_rows = Line._read_group(
            domain, groupby=['product_id'],
            aggregates=['price_subtotal:sum', 'product_uom_qty:sum'],
            order='price_subtotal:sum desc', limit=5,
        )
        denominator_rows = Line._read_group(
            domain, aggregates=['price_subtotal:sum'],
        )
        denominator = (
            denominator_rows[0][0] or 0.0
        ) if denominator_rows else 0.0
        rows = []
        for product, subtotal, qty in top_rows:
            line_domain = domain + [('product_id', '=', product.id)]
            rows.append({
                'product_id': product.id,
                'name': product.display_name,
                'value': subtotal or 0.0,
                'units': qty or 0.0,
                'share': (subtotal / denominator) if denominator else False,
                'target': {
                    'res_model': 'sale.order.line',
                    'domain': self._serialize_domain(line_domain),
                    'name': _("Order lines — %s", product.display_name),
                },
            })
        return {
            'available': bool(rows),
            'currency': primary_currency,
            'goods_subtotal_total': denominator,
            'rows': rows,
        }

    # ------------------------------------------------------------------ #
    #  Completeness / freshness bridge (G1–G3, spec §9.3 + §9.5)
    # ------------------------------------------------------------------ #
    def _store_360_bridge(self, ctx):
        store = ctx['store']
        if len(store) != 1:
            return {
                'available': False,
                'reason': 'select_store' if len(ctx['stores']) > 1
                          else 'no_store',
            }
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        Job = self.env['shopify.connector.job']
        g2_domain = [
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('state', 'in', _G2_STATES),
        ]
        g3_domain = [
            ('store_id', '=', store.id),
            ('job_type', 'in', list(_ORDER_JOB_TYPES)),
            ('state', 'in', list(_G3_STATES)),
            ('superseded_by_job_id', '=', False),
        ]
        g2 = Job.search_count(g2_domain)
        g3 = Job.search_count(g3_domain)
        reconciling = Job.search_count([
            ('store_id', '=', store.id),
            ('job_type', 'in', list(_ORDER_JOB_TYPES)),
            ('state', 'in', ('draft', 'queued', 'running', 'retry_waiting')),
            (
                'expected_connection_generation',
                '=', store.connection_generation,
            ),
        ]) > 0
        return self._store_360_bridge_state(
            store, settings, g2, g3, reconciling,
            g2_domain=g2_domain, g3_domain=g3_domain,
        )

    def _store_360_bridge_state(self, store, settings, g2, g3, reconciling,
                                g2_domain=None, g3_domain=None):
        """The §9.3 truth table with the 209f20a generation-bound
        conditions: checkpoint age alone can never return a reconnected
        store to Complete & current — the completion stamp must name the
        CURRENT connection generation, and when fulfillment-derived data is
        shown its stamp must match too."""
        now = fields.Datetime.now()
        checkpoint = settings.sale_order_last_import_checkpoint_at \
            if settings else False
        checkpoint_fresh = bool(
            checkpoint and (now - checkpoint) <= _CHECKPOINT_FRESH
        )
        scheduled = bool(store.order_sync_scheduled)
        synced_through = settings.sale_order_catchup_synced_through_at \
            if settings else False
        stamp_current = bool(
            settings
            and synced_through
            and settings.sale_order_catchup_generation
            == store.connection_generation
        )
        fulfillment_ok = True
        if (
            settings
            and 'fulfillment_catchup_generation' in settings._fields
            and settings.fulfillment_domain_enabled
        ):
            fulfillment_ok = (
                settings.fulfillment_catchup_generation
                == store.connection_generation
                and bool(settings.fulfillment_catchup_observed_through_at)
            )
        sale_disabled_with_history = bool(
            settings and not settings.sale_domain_enabled and checkpoint
        )
        disconnected = store.state in (
            'reconnect_needed', 'disconnected', 'disconnecting',
        )

        if (
            g3 > 0
            or disconnected
            or sale_disabled_with_history
        ):
            state = 'incomplete'
        elif (
            scheduled and store.state == 'connected'
            and g2 == 0 and g3 == 0
            and checkpoint_fresh
            and stamp_current
            and fulfillment_ok
        ):
            state = 'complete_current'
        elif g3 == 0 and (g2 > 0 or reconciling):
            state = 'processing'
        else:
            state = 'stale'

        copy = {
            'complete_current': _(
                "Complete & current — every discoverable importable order "
                "has landed."),
            'processing': _(
                "Reconciliation in progress — figures may rise shortly."),
            'stale': _(
                "Not proven current — order discovery has not completed a "
                "full pass for the current connection."),
            'incomplete': _(
                "Incomplete — order import needs attention before these "
                "figures can be trusted."),
        }
        result = {
            'available': True,
            'state': state,
            'text': copy[state],
            'synced_through': fields.Datetime.to_string(synced_through)
                if synced_through else False,
            'checkpoint': fields.Datetime.to_string(checkpoint)
                if checkpoint else False,
            'scheduled': scheduled,
            'g2': g2,
            'g3': g3,
            'reconciling': reconciling,
            'disconnected': disconnected,
            'g2_target': {
                'res_model': 'shopify.connector.job',
                'domain': self._serialize_domain(g2_domain or []),
                'name': _("Orders awaiting import"),
            },
            'g3_target': {
                'res_model': 'shopify.connector.job',
                'domain': self._serialize_domain(g3_domain or []),
                'name': _("Order imports needing attention"),
            },
            'discovery_target': {
                'res_model': 'shopify.connector.job',
                'domain': self._serialize_domain(
                    self._store_term(store) + [
                        ('job_type', 'in', (
                            'order_import_scan', 'order_import_sync',
                            'customer_import_sync',
                        )),
                    ]
                ),
                'name': _("Order discovery runs"),
            },
            'settings_target': {
                'res_model': 'shopify.connector.store.settings',
                'domain': self._serialize_domain([
                    ('store_id', '=', store.id),
                ]),
                'name': _("Order import settings"),
            },
            'store_target': {
                'res_model': 'shopify.connector.store',
                'domain': self._serialize_domain([('id', '=', store.id)]),
                'name': _("Store connection"),
            },
        }
        if state == 'incomplete':
            if g3 > 0:
                result['critical_text'] = _(
                    "A connector problem may make these figures incomplete — "
                    "review order imports."
                )
                result['critical_target'] = result['g3_target']
            elif sale_disabled_with_history and not disconnected:
                result['critical_text'] = _(
                    "Order import is disabled, so these figures are historic "
                    "and may be incomplete — review order import settings."
                )
                result['critical_target'] = result['settings_target']
            else:
                result['critical_text'] = _(
                    "The Shopify connection is unavailable, so these figures "
                    "are last known and may be incomplete."
                )
                result['critical_target'] = result['store_target']
        elif state == 'stale':
            result['critical_text'] = _(
                "Order discovery is not current yet — run or enable order "
                "import before relying on these figures."
            )
            result['critical_target'] = result['discovery_target']
        return result

    # ------------------------------------------------------------------ #
    #  Order lifecycle strips (L1–L4, L6) + sale-side exceptions (L7)
    # ------------------------------------------------------------------ #
    def _store_360_lifecycle(self, ctx):
        Order = self.env['sale.order']
        domain = self._store_360_order_domain(ctx, 'current')
        review_domain = self._store_360_order_domain(
            ctx, 'current', review=True,
        )

        def target(extra, name):
            return {
                'res_model': 'sale.order',
                'domain': self._serialize_domain(domain + extra),
                'name': name,
            }

        financial_rows = Order._read_group(
            domain,
            groupby=['shopify_connector_financial_status',
                     'shopify_connector_is_cod'],
            aggregates=['__count'],
        )
        # Exact (case-sensitive) bucket matching, deliberately: the drill-
        # down domains below use '=' on the same raw stored value, so the
        # python bucketing here and the domain the operator lands on can
        # never disagree. A value in any other casing is a schema surprise
        # and falls into the disclosed remainder — fail-closed, never
        # silently bucketed as healthy (task §7.11).
        paid = authorized = pending_non_cod = cod = other = 0
        for status, is_cod, count in financial_rows:
            if is_cod:
                cod += count
            elif status == 'PAID':
                paid += count
            elif status == 'AUTHORIZED':
                authorized += count
            elif status == 'PENDING':
                pending_non_cod += count
            else:
                other += count
        review = Order.search_count(review_domain)
        payment = {
            'buckets': [
                {
                    'id': 'paid', 'label': _("Paid"), 'count': paid,
                    'target': target(
                        [('shopify_connector_financial_status', '=', 'PAID'),
                         ('shopify_connector_is_cod', '=', False)],
                        _("Paid imported orders")),
                },
                {
                    'id': 'authorized',
                    'label': _("Authorized — capture pending"),
                    'count': authorized,
                    'target': target(
                        [('shopify_connector_financial_status', '=', 'AUTHORIZED'),
                         ('shopify_connector_is_cod', '=', False)],
                        _("Authorized imported orders")),
                },
                {
                    'id': 'pending_non_cod',
                    'label': _("Payment pending (non-COD)"),
                    'count': pending_non_cod,
                    'target': target(
                        [('shopify_connector_financial_status', '=', 'PENDING'),
                         ('shopify_connector_is_cod', '=', False)],
                        _("Payment-pending imported orders")),
                },
                {
                    'id': 'cod', 'label': _("Cash on delivery"),
                    'count': cod,
                    'target': target(
                        [('shopify_connector_is_cod', '=', True)],
                        _("COD imported orders")),
                },
                {
                    'id': 'review', 'label': _("Needs review"),
                    'count': review,
                    'target': {
                        'res_model': 'sale.order',
                        'domain': self._serialize_domain(review_domain),
                        'name': _("Imported orders needing review"),
                    },
                },
            ],
            'other': other,
        }

        freshness_rows = Order._read_group(
            domain,
            aggregates=['shopify_connector_evidence_refreshed_at:min'],
        )
        oldest_evidence = freshness_rows[0][0] if freshness_rows else False

        cod_domain = domain + [('shopify_connector_is_cod', '=', True)]
        approval_rows = Order._read_group(
            cod_domain, groupby=['shopify_connector_approval_state'],
            aggregates=['__count'],
        )
        commercial_rows = Order._read_group(
            cod_domain, groupby=['shopify_connector_cod_commercial_state'],
            aggregates=['__count'],
        )
        collection_rows = Order._read_group(
            cod_domain, groupby=['shopify_connector_cod_collection_state'],
            aggregates=['__count'],
        )

        def _by_value(rows):
            return {value: count for value, count in rows}

        approval = _by_value(approval_rows)
        commercial = _by_value(commercial_rows)
        collection = _by_value(collection_rows)
        cod_block = {
            'total': cod,
            'approval_pending': approval.get('pending', 0),
            'approval_pending_target': target(
                [('shopify_connector_is_cod', '=', True),
                 ('shopify_connector_approval_state', '=', 'pending')],
                _("COD orders awaiting approval")),
            'quotation': commercial.get('quotation', 0),
            'quotation_target': target(
                [('shopify_connector_is_cod', '=', True),
                 ('shopify_connector_cod_commercial_state', '=',
                  'quotation')],
                _("COD quotations")),
            'confirmed': commercial.get('confirmed', 0),
            'confirmed_target': target(
                [('shopify_connector_is_cod', '=', True),
                 ('shopify_connector_cod_commercial_state', '=',
                  'confirmed')],
                _("Confirmed COD orders")),
            'collection': [
                {
                    'id': value,
                    'label': label,
                    'count': collection.get(value, 0),
                    'target': target(
                        [('shopify_connector_is_cod', '=', True),
                         ('shopify_connector_cod_collection_state', '=',
                          value)],
                        label),
                }
                for value, label in (
                    ('nothing_collected', _("Nothing collected")),
                    ('partially_collected', _("Partially collected")),
                    ('fully_collected', _("Fully collected")),
                )
            ],
        }

        fulfillment_rows = Order._read_group(
            domain, groupby=['shopify_connector_fulfillment_status'],
            aggregates=['__count'],
        )
        fulfilled = partial = unfulfilled = not_observed = 0
        for status, count in fulfillment_rows:
            if status == 'FULFILLED':
                fulfilled += count
            elif status == 'PARTIALLY_FULFILLED':
                partial += count
            elif status == 'UNFULFILLED':
                unfulfilled += count
            else:
                not_observed += count
        progress = {
            'buckets': [
                {
                    'id': 'fulfilled', 'label': _("Fulfilled"),
                    'count': fulfilled,
                    'target': target(
                        [('shopify_connector_fulfillment_status', '=', 'FULFILLED')],
                        _("Fulfilled imported orders")),
                },
                {
                    'id': 'partially_fulfilled',
                    'label': _("Partially fulfilled"), 'count': partial,
                    'target': target(
                        [('shopify_connector_fulfillment_status', '=', 'PARTIALLY_FULFILLED')],
                        _("Partially fulfilled imported orders")),
                },
                {
                    'id': 'unfulfilled', 'label': _("Unfulfilled"),
                    'count': unfulfilled,
                    'target': target(
                        [('shopify_connector_fulfillment_status', '=', 'UNFULFILLED')],
                        _("Unfulfilled imported orders")),
                },
                {
                    'id': 'not_observed', 'label': _("Not yet observed"),
                    'count': not_observed,
                    'target': target(
                        [('shopify_connector_fulfillment_status', 'not in',
                          list(_KNOWN_FULFILLMENT_BUCKETS))],
                        _("Orders without an observed fulfillment status")),
                },
            ],
        }

        oldest_paid_unfulfilled = Order.search(
            domain + [
                ('shopify_connector_financial_status', '=', 'PAID'),
                ('shopify_connector_fulfillment_status', '=', 'UNFULFILLED'),
            ],
            order='date_order asc', limit=1,
        )
        oldest_block = False
        if oldest_paid_unfulfilled:
            oldest_block = {
                'age_relative': self._relative_time(
                    oldest_paid_unfulfilled.date_order,
                    fields.Datetime.now(),
                ),
                'target': target(
                    [('shopify_connector_financial_status', '=', 'PAID'),
                     ('shopify_connector_fulfillment_status', '=', 'UNFULFILLED')],
                    _("Paid, unfulfilled imported orders")),
            }

        return {
            'available': True,
            'payment': payment,
            'evidence_refreshed_oldest': fields.Datetime.to_string(
                oldest_evidence) if oldest_evidence else False,
            'cod': cod_block,
            'fulfillment_progress': progress,
            'oldest_paid_unfulfilled': oldest_block,
            'exceptions': self._store_360_lifecycle_exceptions(ctx),
        }

    def _store_360_lifecycle_exceptions(self, ctx):
        """Sale-side L7 items. These are connector-evidence counts and keep
        their native connector-model drill-downs (spec §6.1: L7 counts stay
        on their connector models — surfaces the caller can already list
        natively); the fulfillment module appends its own items through the
        section seam."""
        store = ctx['store']
        Binding = self.env['shopify.connector.order.binding']
        term = []
        if len(store) == 1:
            term = [('store_id', '=', store.id)]
        items = []
        approval_domain = term + [
            ('manual_gateway_approval_state', '=', 'pending'),
        ]
        approval_count = Binding.search_count(approval_domain)
        if approval_count:
            items.append({
                'id': 'cod_awaiting_approval',
                'severity': 'danger',
                'title': _("COD orders awaiting approval"),
                'count': approval_count,
                'why': _("A reviewer must approve these before they "
                         "confirm."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model': 'shopify.connector.order.binding',
                    'domain': self._serialize_domain(approval_domain),
                    'name': _("COD orders awaiting approval"),
                },
            })
        changed_domain = term + [
            ('status', '=', 'review'),
            ('financial_status_changed_at', '!=', False),
        ]
        changed_count = Binding.search_count(changed_domain)
        if changed_count:
            items.append({
                'id': 'payment_changed_after_import',
                'severity': 'warning',
                'title': _("Payment status changed after import"),
                'count': changed_count,
                'why': _("Shopify reports a different payment state than "
                         "when these orders were imported."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model': 'shopify.connector.order.binding',
                    'domain': self._serialize_domain(changed_domain),
                    'name': _("Payment status changed after import"),
                },
            })
        return items

    # ------------------------------------------------------------------ #
    #  Per-store sales cell for the multi-store region (H1)
    # ------------------------------------------------------------------ #
    def _store_360_stores_region(self, ctx):
        region = super()._store_360_stores_region(ctx)
        if not region.get('available'):
            return region
        try:
            Order = self.env['sale.order']
            window = ctx['window']
            rows = Order._read_group(
                [
                    ('shopify_connector_store_id', 'in', ctx['stores'].ids),
                    ('shopify_connector_quarantined', '=', False),
                    ('shopify_connector_cancelled_at', '=', False),
                    ('state', '!=', 'cancel'),
                    ('date_order', '>=', window['start']),
                    ('date_order', '<', window['end']),
                ],
                groupby=['shopify_connector_store_id', 'currency_id'],
                aggregates=['amount_total:sum', '__count'],
            )
        except AccessError:
            for row in region['rows']:
                row['sales'] = {'available': False,
                                'reason': 'no_permission'}
            return region
        per_store = {}
        for store, currency, total, count in rows:
            per_store.setdefault(store.id, []).append({
                'currency': self._currency_info(currency),
                'sales': total or 0.0,
                'orders': count,
            })
        for row in region['rows']:
            row['sales'] = {
                'available': True,
                'blocks': per_store.get(row['id'], []),
            }
        return region
