from odoo import _

# Shopify caps volume pricing at 50 tiers per variant; mirror that ceiling here so the live UI surfaces it before the push round-trip fails.
MAX_TIERS_PER_VARIANT = 50

ERR_MIN_LT_1 = 'MIN_LT_1'
ERR_INCR_LT_1 = 'INCR_LT_1'
ERR_MAX_LT_MIN = 'MAX_LT_MIN'
ERR_MIN_INCR_MISALIGN = 'MIN_INCR_MISALIGN'
ERR_MAX_INCR_MISALIGN = 'MAX_INCR_MISALIGN'
ERR_INCR_MISALIGN_RANGE = 'INCR_MISALIGN_RANGE'
ERR_TIER_MIN_LE_RULE_MIN = 'TIER_MIN_LE_RULE_MIN'
ERR_TIER_MIN_LE_PREV_BREAK = 'TIER_MIN_LE_PREV_BREAK'
ERR_TIER_MIN_GT_RULE_MAX = 'TIER_MIN_GT_RULE_MAX'
ERR_TIER_INCR_MISALIGN = 'TIER_INCR_MISALIGN'
ERR_TIER_DUP_MIN = 'TIER_DUP_MIN'
ERR_TIER_PRICE_LE_ZERO = 'TIER_PRICE_LE_ZERO'
ERR_TIER_CAP_EXCEEDED = 'TIER_CAP_EXCEEDED'


def format_validation_msg(code, **ctx):
    """ Render a Shopify-style, field-specific validation message for the given error code.
        Keep messages aligned with Shopify Admin wording so users see identical phrasing in
        the live inline banner and the pre-push aggregator blocker.
    """
    if code == ERR_MIN_LT_1:
        return _("Minimum quantity must be at least 1 (got %s).") % ctx.get('value')
    if code == ERR_INCR_LT_1:
        return _("Increment must be at least 1 (got %s).") % ctx.get('value')
    if code == ERR_MAX_LT_MIN:
        return _("Maximum quantity (%s) cannot be lower than minimum quantity (%s).") % (ctx.get('maximum', 0), ctx.get('minimum', 1))
    if code == ERR_MIN_INCR_MISALIGN:
        return _("Minimum quantity (%s) must be a multiple of the increment (%s).") % (ctx.get('minimum', 0), ctx.get('increment', 1))
    if code == ERR_MAX_INCR_MISALIGN:
        return _("Maximum quantity (%s) must be a multiple of the increment (%s).") % (ctx.get('maximum', 0), ctx.get('increment', 1))
    if code == ERR_INCR_MISALIGN_RANGE:
        return _("The maximum (%s) must equal the minimum plus a whole number of increments(%s) .") % (ctx.get('maximum', 0), ctx.get('increment', 1))
    if code == ERR_TIER_MIN_LE_RULE_MIN:
        return _("Break %s: Quantity must be greater than minimum (%s).") % (ctx.get('break_index'), ctx.get('rule_min', 0))
    if code == ERR_TIER_MIN_LE_PREV_BREAK:
        return _("Break %s: Quantity must be greater than previous break.") % ctx.get('break_index')
    if code == ERR_TIER_MIN_GT_RULE_MAX:
        return _("Break %s: Quantity must not exceed maximum.") % ctx.get('break_index')
    if code == ERR_TIER_INCR_MISALIGN:
        return _("Break %s: Must be a multiple of increment (%s).") % (ctx.get('break_index'), ctx.get('increment', 1))
    if code == ERR_TIER_DUP_MIN:
        return _("Break %s: Quantity already used by another break.") % ctx.get('break_index')
    if code == ERR_TIER_PRICE_LE_ZERO:
        return _("Break %s: Price must be greater than zero.") % ctx.get('break_index')
    if code == ERR_TIER_CAP_EXCEEDED:
        return _("Volume pricing supports up to %s tiers per variant; this variant has %s.") % (MAX_TIERS_PER_VARIANT, ctx.get('count'))
    return _("Unknown validation error code: %s") % code


def check_variant_rule(rule):
    """ Run every Shopify quantity-rule check against a variant-price row and return rendered messages.
        Pure-data — takes a record, reads attrs, returns strings. No DB writes, no side effects.
    """
    errors = []
    minimum = rule.minimum_quantity or 0
    maximum = rule.maximum_quantity or 0
    increment = rule.increment or 0

    if minimum and minimum < 1:
        errors.append(format_validation_msg(ERR_MIN_LT_1, value=minimum))
    if increment and increment < 1:
        errors.append(format_validation_msg(ERR_INCR_LT_1, value=increment))
    if maximum and minimum and maximum < minimum:
        errors.append(format_validation_msg(ERR_MAX_LT_MIN, maximum=maximum, minimum=minimum))
    if increment and increment > 1 and minimum and minimum % increment != 0:
        errors.append(format_validation_msg(ERR_MIN_INCR_MISALIGN, minimum=minimum, increment=increment))
    if increment and increment > 1 and maximum and maximum % increment != 0:
        errors.append(format_validation_msg(ERR_MAX_INCR_MISALIGN, maximum=maximum, increment=increment))
    if maximum and minimum and increment and increment > 1 and maximum > minimum:
        if (maximum - minimum) % increment != 0:
            errors.append(format_validation_msg(ERR_INCR_MISALIGN_RANGE, minimum=minimum, maximum=maximum, increment=increment))
    return errors


def check_variant_tier_cap(tier_count):
    """ Return the cap-exceeded message when the variant carries more tiers than Shopify allows; otherwise None. """
    if tier_count > MAX_TIERS_PER_VARIANT:
        return format_validation_msg(ERR_TIER_CAP_EXCEEDED, count=tier_count)
    return None


def check_variant_tier(tier):
    """ Run every Shopify volume-tier check against a tier row and return rendered messages.
        Uses the parent variant-price row as the source of truth for rule_min/rule_max/increment,
        so the live compute and the push-time aggregator see identical context. Every emitted
        message carries a 1-based break_index so the form lists "Break N: …" exactly like
        Shopify's volume-pricing editor.
    """
    errors = []
    parent = tier.variant_price_id

    rule_min = (parent.minimum_quantity or 1) if parent else 1
    rule_max = (parent.maximum_quantity or 0) if parent else 0
    rule_increment = (parent.increment or 1) if parent else 1
    tier_min = tier.minimum_quantity or 0
    tier_price = tier.price or 0.0

    # Resolve this tier's ordinal AND the break directly above it in the parent's natural recordset order, which is the order rendered in the editable One2many list (insertion order while editing, model _order after reload). Sorting by minimum_quantity here would mislabel newly-added rows whose min sorts between existing ones.
    siblings = parent.quantity_price_break_ids if parent else tier
    break_index = 1
    prev_tier_min = None
    for idx, sib in enumerate(siblings, start=1):
        if sib == tier:
            break_index = idx
            break
        prev_tier_min = sib.minimum_quantity or 0

    # Shopify rule (matches the Admin volume-pricing editor): the first break must
    # exceed the rule minimum; every later break must exceed the break directly
    # above it. This cascading check also subsumes duplicates and out-of-order
    # breaks, so a single Shopify-worded message surfaces per row.
    if break_index == 1:
        if tier_min and tier_min <= rule_min:
            errors.append(format_validation_msg(ERR_TIER_MIN_LE_RULE_MIN, break_index=break_index, rule_min=rule_min))
    elif tier_min and prev_tier_min is not None and tier_min <= prev_tier_min:
        errors.append(format_validation_msg(ERR_TIER_MIN_LE_PREV_BREAK, break_index=break_index))

    if tier_price <= 0:
        errors.append(format_validation_msg(ERR_TIER_PRICE_LE_ZERO, break_index=break_index))

    if parent:
        if rule_max and tier_min and tier_min > rule_max:
            errors.append(format_validation_msg(ERR_TIER_MIN_GT_RULE_MAX, break_index=break_index, rule_max=rule_max))
        if rule_increment > 1 and tier_min and (tier_min - rule_min) % rule_increment != 0:
            errors.append(format_validation_msg(ERR_TIER_INCR_MISALIGN, break_index=break_index, increment=rule_increment))
    return errors
