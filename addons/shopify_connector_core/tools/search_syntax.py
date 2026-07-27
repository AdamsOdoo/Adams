"""Encoding values into Shopify's search-query grammar.

The `query:` argument of a Shopify connection is a **second grammar carried
inside a GraphQL string**. Passing it as a GraphQL variable protects the
GraphQL layer and gives the search grammar no protection at all: the server
still parses the string it receives, so an unescaped value re-shapes the
query rather than being matched literally.

That matters most where a search is a *gate*. A duplicate check that returns
no rows because its query was mangled is indistinguishable from a duplicate
check that returns no rows because nothing matched -- the gate opens either
way. This module exists so no call site has to get that right by hand.

Grammar, from the official reference (https://shopify.dev/docs/api/usage/
search-syntax, read 2026-07-27):

    value       Any name, or any quoted string (single or double quotes are
                both permitted).
    name        Any sequence of non-whitespace, non-special characters.

and, verbatim:

    Special characters serve specific functions in search query syntax and
    need to be escaped with a backslash. For example, : \\ ( ).

So a value that is not a bare `name` must be quoted, and a quoted value must
escape the quote character and the backslash itself. The official metafield
guidance shows exactly that shape -- `description:\\"24\\\\\\" monitor\\"` --
i.e. `\\"` for a literal quote inside a double-quoted value.

This module always quotes rather than deciding per value whether quoting is
needed. A conditional quoter has to classify its input correctly on every
path to be safe; an unconditional one is correct by construction, and the
grammar permits a quoted string wherever it permits a name.
"""

# Whitespace is what separates terms, so a value containing any of it would
# split into several terms (with `AND` implied between them). Newlines and
# other control characters are not part of the grammar at all.
_FORBIDDEN = frozenset('\n\r\t\v\f\x00')


class ShopifySearchValueError(ValueError):
    """A value that cannot be encoded into the search grammar.

    Raised rather than encoded-as-best-we-can, so a caller using a search as
    a gate fails closed before transport instead of issuing a query whose
    empty result set it will read as 'no match'.
    """


def search_value(value):
    """Return `value` as a quoted, escaped Shopify search-query value.

    Raises `ShopifySearchValueError` for input that has no faithful encoding
    -- empty, non-string, or carrying a character the grammar has no way to
    represent. Never returns a bare, unquoted value.
    """
    if not isinstance(value, str):
        raise ShopifySearchValueError(
            'A Shopify search value must be a string, not %s.' % (
                type(value).__name__,
            )
        )
    if not value or not value.strip():
        raise ShopifySearchValueError(
            'A Shopify search value may not be empty or whitespace only.'
        )
    bad = _FORBIDDEN.intersection(value)
    if bad:
        raise ShopifySearchValueError(
            'A Shopify search value may not contain control characters '
            '(found %r).' % (sorted(bad),)
        )
    # Backslash first: escaping it after the quote would double-escape the
    # backslash this function just introduced.
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return '"%s"' % escaped


def search_term(field, value):
    """Return a single `field:"value"` term with `value` fully encoded."""
    return '%s:%s' % (field, search_value(value))
