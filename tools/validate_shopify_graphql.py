#!/usr/bin/env python3
"""Validate connector GraphQL documents against Shopify Admin API 2026-07.

The schema snapshot is fetched from Shopify's unauthenticated developer schema
proxy and committed as gzip-compressed introspection JSON. Production Python
files are parsed with ``ast`` so the gate covers all literal query and mutation
documents without importing Odoo. A document added anywhere under a connector
addon is therefore included automatically.
"""

import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

from graphql import build_client_schema, parse, validate


API_VERSION = '2026-07'
SCHEMA_SHA256 = 'b1a0eeb54b6e5346810104712d5c02d862d1960ad08cfbdc98407780296bf70d'
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'tools' / 'shopify-admin-2026-07-introspection.json.gz'
DOCUMENT_START = re.compile(r'^\s*(query|mutation)\b[^\{]*\{')
PRINTF_SLOT = re.compile(r'%(?:\([^)]+\))?[di]')


def load_schema(path=SCHEMA_PATH):
    raw = gzip.decompress(path.read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SCHEMA_SHA256:
        raise RuntimeError(
            'Shopify schema snapshot digest mismatch: expected %s, got %s'
            % (SCHEMA_SHA256, digest)
        )
    payload = json.loads(raw)
    if payload.get('errors') or not (payload.get('data') or {}).get('__schema'):
        raise RuntimeError('Shopify schema snapshot has no valid __schema data.')
    return build_client_schema(payload['data'])


def discover_documents(root=ROOT):
    documents = []
    for path in sorted((root / 'addons').glob('shopify_connector_*/**/*.py')):
        if 'tests' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            source = node.value.strip()
            if not DOCUMENT_START.match(source):
                continue
            # This is a local dispatcher seam exercised with a fake transport,
            # not an Admin API document owned by any connector domain.
            if 'MutationDispatchSelftest' in source:
                continue
            # Page-size interpolation is the only formatting used by shipped
            # operation literals. Substitute a schema-valid integer; runtime
            # code still owns its actual bounded value.
            source = PRINTF_SLOT.sub('50', source)
            documents.append((path.relative_to(root), node.lineno, source))
    return documents


def validate_documents(schema, documents):
    failures = []
    for path, lineno, source in documents:
        try:
            document = parse(source)
        except Exception as exc:
            failures.append((path, lineno, 'parse: %s' % exc))
            continue
        for error in validate(schema, document):
            failures.append((path, lineno, error.message))
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema', type=Path, default=SCHEMA_PATH)
    args = parser.parse_args(argv)
    schema = load_schema(args.schema)
    documents = discover_documents()
    if not documents:
        print('No Shopify GraphQL documents discovered.', file=sys.stderr)
        return 2
    failures = validate_documents(schema, documents)
    if failures:
        for path, lineno, message in failures:
            print('%s:%d: %s' % (path, lineno, message), file=sys.stderr)
        return 1
    print(
        'Validated %d GraphQL documents against Shopify Admin API %s.'
        % (len(documents), API_VERSION)
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
