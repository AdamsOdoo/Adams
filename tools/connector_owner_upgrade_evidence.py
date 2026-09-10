"""Fail-closed evidence for the approved owner-upgrade then W2 CI lane.

Uses PostgreSQL catalog queries, so old databases need not load candidate ORM.
Snapshots only stable identities/relationships, never credentials or payloads.
"""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess


def query(db, sql):
    result = subprocess.run(['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-tAc', sql, db],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout.strip() or '[]')


def versions(db):
    return dict(query(db, "SELECT coalesce(json_agg(json_build_array(name, latest_version) ORDER BY name), '[]') FROM ir_module_module WHERE state='installed' AND name LIKE 'shopify\\_connector\\_%' ESCAPE '\\'"))


def number(version):
    return tuple(int(part) for part in version.split('.'))


def plan(root, installed):
    if 'shopify_connector_core' not in installed or 'shopify_connector_webhook' not in installed:
        raise ValueError('old fixture lacks required installed owners')
    if 'shopify_connector_product_webhook' in installed:
        raise ValueError('old fixture already contains W2')
    targets, migrations = {}, []
    for module, old in sorted(installed.items()):
        addon = root / 'addons' / module
        target = ast.literal_eval((addon / '__manifest__.py').read_text())['version']
        if number(old) > number(target):
            raise ValueError(f'unsupported downgrade: {module}')
        targets[module] = target
        for script in sorted((addon / 'migrations').glob('*/*-*.py')):
            version = script.parent.name
            if number(old) < number(version) <= number(target):
                migrations.append([module, version, script.stem])
    if not migrations:
        raise ValueError('old fixture requires no migrations')
    return {'installed_before': installed, 'target_versions': targets,
            'expected_migrations': migrations}


def snapshot(db):
    tables = query(db, "SELECT coalesce(json_agg(table_name ORDER BY table_name), '[]') FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' AND table_name LIKE 'shopify\\_connector\\_%' ESCAPE '\\'")
    result = {}
    for table in tables:
        if not re.fullmatch('[a-z_]+', table):
            raise ValueError('unexpected table identifier')
        columns = query(db, f"SELECT json_agg(column_name ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema='public' AND table_name='{table}'")
        if 'id' not in columns:
            continue
        selected = [c for c in columns if c in ('id', 'store_id', 'company_id') or c.endswith('_binding_id') or c.startswith('shopify_') and c.endswith('_id')]
        # Only identities are serialized; hashes of complete rows would silently
        # outlaw legitimate migration backfills and credential rotation.
        projection = ','.join('"' + c + '"' for c in selected)
        rows = query(db, f'SELECT coalesce(json_agg(row_to_json(s) ORDER BY s.id), \'[]\') FROM (SELECT {projection} FROM "{table}") s')
        result[table] = rows
    return result


def verify(evidence, current, after, log):
    for module, target in evidence['target_versions'].items():
        if current.get(module) != target:
            raise ValueError(f'owner version mismatch: {module}')
    for table, before in evidence['identities_before'].items():
        indexed = {row['id']: row for row in after.get(table, [])}
        for row in before:
            current_row = indexed.get(row['id'])
            if current_row is None or any(current_row.get(key) != value for key, value in row.items()):
                raise ValueError(f'identity/relationship changed: {table} id={row["id"]}')
    for module, version, script in evidence['expected_migrations']:
        pattern = rf'module {re.escape(module)}: Running upgrade \[[<>]?{re.escape(version)}[<>]?\] {re.escape(script)}(?:\s|$)'
        if not re.search(pattern, log):
            raise ValueError(f'migration did not execute: {module}/{version}/{script}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('before', 'after', 'reject-old'))
    parser.add_argument('--db', required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    if args.mode == 'reject-old':
        import importlib.util
        import psycopg2
        hook = args.root / 'addons/shopify_connector_product_webhook/pre_init.py'
        spec = importlib.util.spec_from_file_location('candidate_w2_preflight', hook)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def manifest(name):
            path = args.root / 'addons' / name / '__manifest__.py'
            return ast.literal_eval(path.read_text()) if path.exists() else {}
        with psycopg2.connect(dbname=args.db) as connection:
            connection.set_session(readonly=True)
            with connection.cursor() as cursor:
                try:
                    module.check_owner_versions(cursor, manifest)
                except RuntimeError as error:
                    if not str(error).startswith('W2 installation requires matching, fully upgraded connector owners.'):
                        raise
                    print('EXPECTED_READ_ONLY_PREFLIGHT_REJECTION: ' + str(error))
                else:
                    raise ValueError('old owner installation was incorrectly accepted')
        return
    if args.mode == 'before':
        evidence = plan(args.root, versions(args.db))
        evidence['identities_before'] = snapshot(args.db)
        evidence['preservation_scope'] = 'Existing stable row identities and connector relationships; empty tables do not establish populated-data preservation.'
        args.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
        print(','.join(evidence['target_versions']))
    else:
        evidence = json.loads(args.evidence.read_text())
        current, after = versions(args.db), snapshot(args.db)
        verify(evidence, current, after, args.log.read_text())
        evidence['verified_versions'] = current
        evidence['preserved_row_counts'] = {k: len(v) for k, v in evidence['identities_before'].items()}
        args.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
