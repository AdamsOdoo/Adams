# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Centralized income-account validation for all paths that create
``account.move.line`` records (invoices, credit notes).

Every Shopify sync path that builds invoice or credit-note lines
must validate income accounts **before** calling ``_create_invoices()``
or ``account.move.create()``.  Without a valid account the SQL-level
``account_move_line_check_accountable_required_fields`` constraint
rejects the INSERT and — if not wrapped in a savepoint — poisons the
entire transaction.

This module provides a single implementation of that validation so
the check is done consistently everywhere and new paths cannot
accidentally skip it.

Usage::

    from .accounting import validate_order_income_accounts

    missing, fallback = validate_order_income_accounts(
        env, order, journal=journal,
    )
    if missing and not fallback:
        # schedule activity, abort
        ...
"""

import logging

_logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def validate_order_income_accounts(env, order, journal=None):
    """Check that every product on *order* can resolve an income account.

    Resolution order per product:

    1. ``product_tmpl.get_product_accounts(fiscal_pos=...)['income']``
    2. Fallback chain (only used when #1 fails):
       a. *journal* default account
       b. Account from the order's posted invoice lines
       c. Any ``income``-type account in the order's company

    Args:
        env: Odoo environment (``self.env``).
        order: ``sale.order`` recordset (single record).
        journal: Optional ``account.journal`` — its ``default_account_id``
            is the first fallback.  Pass the sales journal when creating
            credit notes; may be ``None`` for regular invoices (Odoo
            resolves accounts internally in ``_create_invoices``).

    Returns:
        ``(missing, fallback)`` where:

        *missing*
            ``list[str]`` of product display-names that lack an income
            account (via ``get_product_accounts``).  Empty when all
            products are configured correctly.

        *fallback*
            ``account.account`` recordset (possibly empty) — the best
            fallback account that can substitute for the missing
            per-product account.  Callers that build ``account.move``
            lines directly (credit notes) should use this as the
            ``account_id`` on lines whose product has no income account.

            For the regular invoice path (``_create_invoices``), the
            fallback is informational: if *missing* is non-empty **and**
            fallback is falsy, the caller should abort.
    """
    missing = []
    fiscal_pos = order.fiscal_position_id if order else None

    for line in order.order_line:
        product = line.product_id
        if not product:
            continue
        accounts = product.product_tmpl_id.get_product_accounts(
            fiscal_pos=fiscal_pos,
        )
        if not accounts.get('income'):
            missing.append(product.display_name)

    fallback = _resolve_fallback_income_account(env, order, journal)

    return missing, fallback


def schedule_account_activity(order, summary, products, error=None):
    """Schedule a warning activity on *order* about missing income accounts.

    Centralises the activity-scheduling so every caller produces
    identical, grep-friendly messages.

    Args:
        order: ``sale.order`` recordset.
        summary: Short summary for the activity (shown in kanban).
        products: Iterable of product display-names that are misconfigured.
        error: Optional exception or error string to include in the note.
    """
    parts = []
    if products:
        parts.append(
            "No income account for product(s): %s. "
            "Check the product category accounting tab or fiscal "
            "position mappings." % ', '.join(products)
        )
    if error:
        parts.append("Error: %s" % error)
    note = ' '.join(parts) or summary

    _logger.warning("Order %s: %s", order.name, note)
    order.activity_schedule(
        'mail.mail_activity_data_warning',
        summary=summary,
        note=note,
    )


def check_total_against_shopify(move, expected_total):
    """Permanent total-check guard (DEC-011/012, AUD-001 workstream).

    Compares the computed total of *move* against *expected_total* (the
    Shopify charged total stamped on the order binding, in the same
    currency as the move per items 1-2 of the currency workstream).

    Returns ``(ok, tolerance)``. ``ok`` is True when *expected_total* is
    falsy (no stamp — e.g. bindings created before the stamp field
    existed; the guard must not fire on legacy data) or when the
    difference is within tolerance (DEC-012: 2 × currency rounding —
    absorbs per-line rounding drift, catches any real tax/price error).
    """
    if not expected_total:
        return True, 0.0
    tolerance = 2 * (move.currency_id.rounding or 0.01)
    return abs(move.amount_total - expected_total) <= tolerance, tolerance


def schedule_total_mismatch_activity(order, move, expected_total, tolerance):
    """Visible degradation for a blocked posting (rule 5 / DEC-011)."""
    note = (
        "Invoice %(move)s totals %(computed).2f %(ccy)s but Shopify "
        "charged %(expected).2f %(ccy)s for order %(order)s (allowed "
        "difference: %(tol).2f). The invoice was left in DRAFT to protect "
        "your books. Common causes: a tax configured differently in Odoo "
        "than in Shopify (check Shopify > Configuration > Tax Mappings), "
        "or shipping taxes. Review the invoice, fix the cause, then post "
        "it manually — or run Retry Sync after fixing." % {
            'move': move.name or '(draft)',
            'computed': move.amount_total,
            'expected': expected_total,
            'ccy': move.currency_id.name,
            'order': order.name,
            'tol': tolerance,
        }
    )
    _logger.warning("Order %s: total-check guard blocked posting — %s",
                    order.name, note)
    order.activity_schedule(
        'mail.mail_activity_data_warning',
        summary="Shopify total mismatch — invoice NOT posted",
        note=note,
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _resolve_fallback_income_account(env, order, journal):
    """Find the best available fallback income account.

    Resolution chain:
    1. Journal default account
    2. Account from posted invoice lines on the same order
    3. Any income-type account in the company

    Returns an ``account.account`` recordset (may be empty).
    """
    company = order.company_id or env.company

    # 1. Journal default
    if journal and journal.default_account_id:
        return journal.default_account_id

    # 2. Posted invoice lines on same order
    posted_lines = order.invoice_ids.filtered(
        lambda i: i.state == 'posted' and i.move_type == 'out_invoice'
    ).mapped('invoice_line_ids').filtered(
        lambda l: l.display_type == 'product' and l.account_id
    )
    if posted_lines:
        return posted_lines[0].account_id

    # 3. Any income account in the company
    return env['account.account'].search([
        ('account_type', '=', 'income'),
        ('company_ids', 'in', [company.id]),
    ], limit=1)
