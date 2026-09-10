"""Odoo-shell fixture for the disposable old-W1 -> owner-upgrade -> W2 lane.

Run with W2_PRESERVATION_MODE=seed|verify and W2_PRESERVATION_SNAPSHOT.
No credentials or network calls. The old core's own self-test mutation strategy
creates unresolved evidence through the same C2/C3 surfaces as native tests.
SQL comparison deliberately requires every listed column to survive unchanged.
"""
import json
import os
from pathlib import Path

TABLES = {
    'shopify_connector_store': ('id', 'name', 'shop_domain', 'state', 'company_id', 'connection_generation'),
    'shopify_connector_job': ('id', 'store_id', 'job_source', 'job_type', 'original_job_type', 'state', 'payload_hash', 'manual_review_subreason'),
    'shopify_connector_job_log': ('id', 'job_id', 'store_id', 'event_type', 'from_state', 'to_state', 'message', 'occurred_at'),
    'shopify_connector_location': ('id', 'store_id', 'shopify_location_gid', 'name', 'shopify_location_active'),
    'shopify_connector_mutation_attempt': ('id', 'job_id', 'attempt_token', 'mutation_domain', 'store_id', 'expected_connection_generation', 'expected_store_identity', 'remote_mutation_intent', 'preconditions_snapshot', 'business_intent_fingerprint', 'exact_request_fingerprint', 'shopify_idempotency_key', 'idempotency_valid_until', 'transport_attempted', 'observed_outcome', 'resolution_disposition', 'resolution_source', 'resolution_reason', 'resolution_uid', 'resolution_at', 'inconclusive_reconciliation_count', 'remote_evidence_refs', 'created_at', 'transport_at', 'resolved_at'),
}


def snapshot(cr, ids):
    result = {}
    for table, columns in TABLES.items():
        cr.execute('SELECT %s FROM %s WHERE id = ANY(%%s) ORDER BY id' %
                   (', '.join(columns), table), (ids[table],))
        result[table] = [dict(zip(columns, row)) for row in cr.fetchall()]
        if len(result[table]) != len(ids[table]):
            raise AssertionError('Preserved fixture missing rows: ' + table)
    # JSON normalizes datetime values identically before and after migration.
    return json.loads(json.dumps(result, sort_keys=True, default=str))


def verify_snapshot(expected, actual):
    if expected != actual:
        changed = [table for table in TABLES if expected.get(table) != actual.get(table)]
        raise AssertionError('Legacy identity/history/uncertainty changed: ' + ', '.join(changed))


def seed(env):
    from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
        C2_SENTINEL_CONTEXT, C2_SIDE_CURSOR_SENTINEL,
    )
    store = env['shopify.connector.store'].sudo().create({
        'name': 'W2 owner upgrade preservation fixture',
        'shop_domain': 'w2-preservation.invalid.myshopify.com',
        'state': 'disconnected',
        'company_id': env.company.id,
    })
    job = env['shopify.connector.job.enqueue'].enqueue(
        store, 'setup_readiness_check', 'mutation_dispatch_selftest',
        payload_hash='w2-preservation-synthetic',
    )
    job.sudo().write({'state': 'running', 'current_attempt_token': 'w2-preservation-owner'})
    attempt = env['shopify.connector.mutation.attempt'].with_context(**{
        C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
    })._create_attempt_intent({
        'job_id': job.id, 'attempt_token': 'w2-preservation-owner',
        'mutation_domain': 'mutation_dispatch_selftest',
        'expected_connection_generation': store.connection_generation,
        'expected_store_identity': store.shop_domain,
        'remote_mutation_intent': {'synthetic': 'preserve-unresolved'},
        'preconditions_snapshot': {'synthetic': True},
        'business_intent_fingerprint': 'a' * 64,
        'exact_request_fingerprint': 'b' * 64,
        'shopify_idempotency_key': 'w2-preservation-no-network',
    })
    attempt._record_direct_outcome('uncertain', {'synthetic': 'unknown-after-send'})
    job._transition_blocked_manual_review(
        'unknown_system_error', 'duplicate_risk', 'Synthetic unresolved mutation: never resend',
    )
    location = env['shopify.connector.location'].sudo().create({
        'store_id': store.id, 'shopify_location_gid': 'gid://shopify/Location/990001',
        'name': 'Synthetic preserved location',
    })
    env.flush_all()
    logs = env['shopify.connector.job.log'].sudo().search([('job_id', '=', job.id)])
    if not logs:
        raise AssertionError('Seed did not create audit history')
    return dict(zip(TABLES, ([store.id], [job.id], logs.ids, [location.id], [attempt.id])))


def main(env):
    if not env.cr.dbname.startswith('connector_'):
        raise RuntimeError('Fixture requires disposable connector campaign database')
    mode = os.environ['W2_PRESERVATION_MODE']
    path = Path(os.environ['W2_PRESERVATION_SNAPSHOT'])
    if mode == 'seed':
        if path.exists():
            raise RuntimeError('Refusing to overwrite preservation snapshot')
        ids = seed(env)
        payload = {'ids': ids, 'rows': snapshot(env.cr, ids)}
        env.cr.commit()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    elif mode == 'verify':
        payload = json.loads(path.read_text())
        verify_snapshot(payload['rows'], snapshot(env.cr, payload['ids']))
    else:
        raise ValueError('Unknown preservation mode')
    print('W2_PRESERVATION_' + mode.upper() + '_PASSED')


if 'env' in globals():
    main(env)
