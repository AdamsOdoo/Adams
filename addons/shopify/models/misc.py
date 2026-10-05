import html
import json
import logging
import re
import traceback

import dateutil
import requests
from bs4 import BeautifulSoup, NavigableString
from pytz import timezone

_logger = logging.getLogger("Teqstars:Shopify")

# Task: T7609 - (connect, read) seconds allowed for one staged upload to the bucket.
STAGED_UPLOAD_TIMEOUT = (10, 300)

SHOPIFY_TO_ODOO_UOM_XML_ID = {
    'KILOGRAMS': 'uom.product_uom_kgm',
    'GRAMS': 'uom.product_uom_gram',
    'POUNDS': 'uom.product_uom_lb',
    'OUNCES': 'uom.product_uom_oz',

    'LITERS': 'uom.product_uom_litre',
    'CUBIC_METERS': 'uom.product_uom_cubic_meter',
    'GALLONS': 'uom.product_uom_gal',
    'FLUID_OUNCES': 'uom.product_uom_floz',
    'QUARTS': 'uom.product_uom_qt',
}

VOLUME_TO_M3 = {
    'MILLILITERS': 0.000001, 'CENTILITERS': 0.00001, 'PINTS': 0.000473176,
    'IMPERIAL_GALLONS': 0.00454609, 'IMPERIAL_QUARTS': 0.00113652, 'IMPERIAL_PINTS': 0.000568261, 'IMPERIAL_FLUID_OUNCES': 0.0000284131
}

def convert_shopify_datetime_to_utc(datetime):
    converted_datetime = ""
    if datetime:
        datetime = dateutil.parser.parse(datetime)
        converted_datetime = datetime.astimezone(timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S')
    return converted_datetime or False


def log_traceback_for_exception():
    _logger.error(traceback.format_exc())


def extract_numeric_id(gid):
    """
    Given a Shopify GID like:
        'gid://shopify/Product/8133669617876'
        'gid://shopify/ProductVariant/45642651959508'
    returns the trailing numeric ID as an integer.

    If the GID is malformed or missing, returns None.
    """
    if not isinstance(gid, str):
        return None
    match = re.search(r'/([^/]+)$', gid)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def exception_message(exception):
    """
    Task: T9096 - Readable message for an exception.
    MarketplaceException calls Exception.__init__ with (message, title, context), so its
    args tuple has three items and str() renders "('msg', None, None)". Take args[0] when
    it is there, otherwise fall back to str().
    """
    args = getattr(exception, 'args', None)
    if args and isinstance(args[0], str):
        return args[0]
    return str(exception)

def process_response(response):
    """
    Include the page information in response.
    """

    # Function to process and format the GraphQL response dynamically
    def traverse_json(data):
        if isinstance(data, dict):
            if 'edges' in data:
                nodes = [traverse_json(edge['node']) for edge in data['edges']]
                if 'pageInfo' in data:
                    return nodes + [{'pageInfo': data['pageInfo']}]
                return nodes

            result = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    result[key] = traverse_json(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [traverse_json(item) for item in data]
        else:
            return data

    return traverse_json(json.loads(response))


def upload_content_to_staged_target(target, file_content, filename, mimetype, log_prefix, session=None):
    """
    Task: T7609 - Send one file's bytes to the Google Cloud Storage target Shopify signed, shared by the
    bulk JSONL upload and by the media staging of an export/update.
    The form fields carry the policy Shopify signed and must be sent BEFORE the file part, and GCS
    answers 201 (not 200) on success. A plain function on purpose: it touches no ORM, so the media
    staging can call it from its upload threads.
    Args:
        target (dict): One entry of stagedUploadsCreate's ``stagedTargets``.
        file_content (bytes): Content to upload.
        filename (str): Name the file is stored under; Shopify reuses it for the media it creates.
        mimetype (str): Content type of ``file_content``; must match what the target was signed for.
        log_prefix (str): Operation label used in the error message.
        session (requests.Session): Optional connection pool to post through. The media staging hands
            one session per upload thread, which keeps the TLS connection to the bucket alive between
            images instead of paying a new handshake for every one of them.
    Returns:
        str: Empty when the upload succeeded, otherwise the message describing the refusal.
    """
    params = {p['name']: p['value'] for p in target.get('parameters', [])}
    files = {
        'Content-Type': (None, params.get('Content-Type', mimetype)),
        'success_action_status': (None, params.get('success_action_status', '201')),
        'acl': (None, params.get('acl', 'private')),
        'key': (None, params.get('key', '')),
        'x-goog-date': (None, params.get('x-goog-date', '')),
        'x-goog-credential': (None, params.get('x-goog-credential', '')),
        'x-goog-algorithm': (None, params.get('x-goog-algorithm', '')),
        'x-goog-signature': (None, params.get('x-goog-signature', '')),
        'policy': (None, params.get('policy', '')),
        'file': (filename, file_content, mimetype),
    }
    # A staged upload that never answers used to hold its worker forever; the timeout frees it and the
    # caller keeps the Odoo image URL for that one file.
    upload_resp = (session or requests).post(target.get('url', ''), files=files, timeout=STAGED_UPLOAD_TIMEOUT)
    if upload_resp.status_code != 201:
        return f"{log_prefix}: GCS upload failed. HTTP {upload_resp.status_code}: {upload_resp.text}"
    return ''


def _convert_shopify_rich_text_to_html(node):
    """
    T6290 - Recursively walks through Shopify's Rich Text JSON (AST) and converts all possible node combinations into valid Odoo HTML.
    Args:
        node (dict): Shopify rich text node in JSON format.
    Returns:
        str: Converted HTML string.
    """
    # if the node isn't a dictionary, return empty
    if not isinstance(node, dict):
        return ""

    node_type = node.get('type')

    # ---------------------------------------------------------
    # Handles combinations of bold, italic, and newlines
    # ---------------------------------------------------------
    if node_type == 'text':
        # Escape basic HTML characters to prevent rendering issues
        text_val = html.escape(node.get('value', ''))

        # Convert JSON newlines to HTML breaks
        text_val = text_val.replace('\n', '<br/>')

        # Preserve multiple spaces (indentation/tabs) by converting to non-breaking spaces
        text_val = text_val.replace('  ', '&nbsp;&nbsp;')

        # Apply formatting flags (Handles multiple at once!)
        if node.get('bold'):
            text_val = f"<strong>{text_val}</strong>"
        if node.get('italic'):
            text_val = f"<em>{text_val}</em>"
        return text_val

    # ---------------------------------------------------------
    # PARENT NODES (Process children recursively)
    # ---------------------------------------------------------
    # Recursively parse all children elements first
    children_html = "".join(
        _convert_shopify_rich_text_to_html(child)
        for child in node.get('children', [])
    )

    # ---------------------------------------------------------
    # WRAPPER TAGS (Wrap the parsed children in correct HTML)
    # ---------------------------------------------------------
    if node_type == 'root':
        return children_html

    elif node_type == 'paragraph':
        return f"<p>{children_html}</p>"

    elif node_type == 'heading':
        level = node.get('level', 1)
        return f"<h{level}>{children_html}</h{level}>"

    elif node_type == 'list':
        tag = 'ul' if node.get('listType') == 'unordered' else 'ol'
        return f"<{tag}>{children_html}</{tag}>"

    elif node_type == 'list-item':
        return f"<li>{children_html}</li>"

    elif node_type == 'link':
        url = node.get('url', '#')
        title = node.get('title') or ''
        target = node.get('target') or ''

        title_attr = f' title="{title}"' if title else ''
        target_attr = f' target="{target}"' if target else ''

        return f'<a href="{url}"{title_attr}{target_attr}>{children_html}</a>'

    return children_html


def convert_html_to_shopify_rich_text(html_content):
    """
    T6290 - Converts Odoo HTML strictly into Shopify's supported Rich Text JSON.
    Args:
        html_content (str): HTML string from Odoo field.
    Returns:
        str: JSON string in Shopify rich text format.
    """
    if not html_content:
        return json.dumps({"type": "root", "children": []})

    soup = BeautifulSoup(html_content, 'html.parser')

    SUPPORTED_TYPES = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'a']
    FORMATTING_TAGS = ['strong', 'b', 'em', 'i']

    def _parse_node(element, inherited_format=None):
        if inherited_format is None:
            inherited_format = {}

        if isinstance(element, NavigableString):
            val = str(element)
            if not val.strip() and '\n' not in val:
                return None
            node = {"type": "text", "value": val}
            node.update(inherited_format)
            return node

        tag = element.name

        if tag == 'br':
            return {"type": "text", "value": "\n"}

        if tag not in SUPPORTED_TYPES and tag not in FORMATTING_TAGS:
            return None

        if tag in FORMATTING_TAGS:
            new_format = inherited_format.copy()
            if tag in ['strong', 'b']:
                new_format["bold"] = True
            if tag in ['em', 'i']:
                new_format["italic"] = True

            child_results = []
            for child in element.children:
                res = _parse_node(child, inherited_format=new_format)
                if isinstance(res, list):
                    child_results.extend(res)
                elif res:
                    child_results.append(res)
            return child_results

        node = {"type": ""}
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            node["type"] = "heading"
            node["level"] = int(tag[1])
        elif tag == 'p':
            node["type"] = "paragraph"
        elif tag in ['ul', 'ol']:
            node["type"] = "list"
            node["listType"] = "unordered" if tag == 'ul' else "ordered"
        elif tag == 'li':
            node["type"] = "list-item"
        elif tag == 'a':
            node["type"] = "link"
            node["url"] = element.get('href', '#')
            node["title"] = element.get('title', None)
            node["target"] = element.get('target', None)

        children = []
        for child in element.children:
            result = _parse_node(child, inherited_format=inherited_format)
            if result:
                if isinstance(result, list):
                    children.extend(result)
                else:
                    children.append(result)

        node["children"] = children
        return node

    root_children = []
    for top_level in soup.contents:
        res = _parse_node(top_level)
        if not res:
            continue

        results_list = res if isinstance(res, list) else [res]
        for item in results_list:
            if item.get('type') in ['text', 'link']:
                if root_children and root_children[-1]['type'] == 'paragraph':
                    root_children[-1]['children'].append(item)
                else:
                    root_children.append({"type": "paragraph", "children": [item]})
            else:
                root_children.append(item)

    return json.dumps({"type": "root", "children": root_children}, ensure_ascii=False)


def convert_shopify_metafield_measurement(env, m_type, value, shopify_unit, reverse=False):
    """
    T6290 - Hybrid Converter for Shopify Metafield Measurements.
    Args:
        env (Environment): Odoo environment.
        m_type (str): Measurement type ('weight' or 'volume').
        value (float): Measurement value to convert.
        shopify_unit (str): Shopify unit (e.g., GRAMS, LITERS).
        reverse (bool, optional):
            - False: Shopify → Odoo (import)
            - True: Odoo → Shopify (export)
    Returns:
        float: Converted measurement value based on target unit.
    """
    if not value or m_type not in ('weight', 'volume'):
        return value

    shopify_uom_xml = SHOPIFY_TO_ODOO_UOM_XML_ID.get(shopify_unit)

    if shopify_uom_xml:
        shopify_uom = env.ref(shopify_uom_xml, raise_if_not_found=False)

        odoo_target_uom = False
        if m_type == 'weight':
            is_lb = env['ir.config_parameter'].sudo().get_param('product.weight_in_lbs') == '1'
            odoo_target_uom = env.ref('uom.product_uom_lb') if is_lb else env.ref('uom.product_uom_kgm')
        elif m_type == 'volume':
            is_ft3 = env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet') == '1'
            odoo_target_uom = env.ref('uom.product_uom_cubic_foot') if is_ft3 else env.ref('uom.product_uom_cubic_meter')

        if shopify_uom and odoo_target_uom:
            if reverse:
                return odoo_target_uom._compute_quantity(value, shopify_uom, round=False)
            else:
                return shopify_uom._compute_quantity(value, odoo_target_uom, round=False)

    elif m_type == 'volume':
        is_ft3 = env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet') == '1'
        if reverse:  # Odoo -> Shopify
            m3_val = value / 35.3147 if is_ft3 else value
            return round(m3_val / VOLUME_TO_M3.get(shopify_unit, 1.0), 8)
        else:  # Shopify -> Odoo
            m3_val = value * VOLUME_TO_M3.get(shopify_unit, 1.0)
            return round(m3_val * 35.3147 if is_ft3 else m3_val, 8)
    return value
