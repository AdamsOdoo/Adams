# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Base handler utilities: pagination, response wrapping, cursor encoding.
"""
import base64
import logging

_logger = logging.getLogger(__name__)


def encode_cursor(offset):
    """Encode an offset into a Shopify-style opaque cursor."""
    return base64.b64encode(f'eyJsYXN0X2lkIjo{offset}}}'.encode()).decode()


def decode_cursor(cursor_str):
    """Decode a Shopify-style cursor back to an offset."""
    try:
        decoded = base64.b64decode(cursor_str).decode()
        # Format: eyJsYXN0X2lkIjo{offset}}
        offset_str = decoded.replace('eyJsYXN0X2lkIjo', '').rstrip('}')
        return int(offset_str)
    except Exception:
        return 0


def paginate_records(records, first, after=None):
    """Apply cursor-based pagination to an Odoo recordset.

    Returns a dict with Shopify-style 'edges' and 'pageInfo'.
    Each record must have a ``_to_graphql_node()`` method.
    """
    offset = 0
    if after:
        offset = decode_cursor(after) + 1

    total = len(records)
    page = records[offset:offset + first]
    has_next = (offset + first) < total

    edges = []
    for i, rec in enumerate(page):
        edges.append({
            'cursor': encode_cursor(offset + i),
            'node': rec._to_graphql_node(),
        })

    end_cursor = encode_cursor(offset + len(page) - 1) if page else None

    return {
        'edges': edges,
        'pageInfo': {
            'hasNextPage': has_next,
            'endCursor': end_cursor,
        },
    }


def build_response(data, extensions, errors=None):
    """Build a Shopify-style GraphQL response envelope."""
    resp = {
        'data': data,
        'extensions': extensions,
    }
    if errors:
        resp['errors'] = errors
    return resp


def build_error_response(message, extensions=None):
    """Build a Shopify-style GraphQL error response."""
    resp = {
        'errors': [{'message': message}],
    }
    if extensions:
        resp['extensions'] = extensions
    return resp


def build_mutation_response(result_key, data, user_errors=None):
    """Build a mutation response with optional userErrors."""
    result = dict(data)
    result['userErrors'] = user_errors or []
    return {result_key: result}
