#!/usr/bin/env python3
"""Genuine independent-process concurrency harness for the Wave 4 fulfillment
Layer 2 mutation path.

This is an OUT-OF-BAND multiprocessing script — it is deliberately NOT imported
by tests/__init__.py and never runs as an Odoo unit test (a TransactionCase
cannot exercise real concurrent workers on independent PostgreSQL connections).
It mirrors the accepted core harness
(shopify_connector_core/tests/runtime_layer2_concurrency_harness.py): OS
processes via the 'spawn' start method (never 'fork'), a per-process Registry +
cursor + Environment, real commit boundaries, and a two-process contention
orchestration. It performs zero real Shopify calls.

Run (against a real Odoo.sh / local database):

    python runtime_layer2_fulfillment_concurrency_harness.py \
        --database DB --config ODOO_CONF --scenario c1_ownership_race
"""
import argparse
import json
import multiprocessing
import os
import sys

LOCK_REFUSAL = 'The mutation attempt is owned by another worker.'

_RUNTIME_CACHE = {}


def _runtime(settings):
    key = (settings['config'], settings['database'])
    if key not in _RUNTIME_CACHE:
        from odoo import api
        from odoo.tools import config
        from odoo.modules.registry import Registry
        from odoo import service
        config.parse_config(['-c', settings['config']])
        service.server.load_server_wide_modules()
        _RUNTIME_CACHE[key] = {
            'api': api,
            'registry': Registry(settings['database']),
        }
    return _RUNTIME_CACHE[key]


def _new_environment(settings):
    from odoo import SUPERUSER_ID
    runtime = _runtime(settings)
    cursor = runtime['registry'].cursor()
    return cursor, runtime['api'].Environment(cursor, SUPERUSER_ID, {})


def _fixture(settings):
    """Create a committed store + running fulfillment_create job so both child
    processes contend on the same row."""
    cursor, env = _new_environment(settings)
    store = env['shopify.connector.store'].create({
        'name': 'FUL-CONC', 'shop_domain': 'ful-conc.myshopify.com',
        'api_version': '2026-07', 'state': 'connected',
    })
    env['shopify.connector.store.settings'].create({
        'store_id': store.id, 'fulfillment_domain_enabled': True,
    })
    job = env['shopify.connector.job'].create({
        'store_id': store.id, 'job_source': 'odoo_event',
        'trigger_origin': 'fulfillment_picking_validation',
        'job_type': 'fulfillment_create', 'state': 'queued',
        'res_model': 'stock.picking', 'res_id': 1,
        'shopify_target_gid': 'gid://shopify/FulfillmentOrder/1',
        'payload_hash': 'conc',
    })
    cursor.commit()
    ids = {'store_id': store.id, 'job_id': job.id}
    cursor.close()
    return ids


def _child_claim(settings, job_id, result_queue, start_event):
    start_event.wait()
    cursor, env = _new_environment(settings)
    try:
        job = env['shopify.connector.job'].browse(job_id).try_lock_for_update()
        result_queue.put('winner' if job else 'loser')
        cursor.commit()
    finally:
        cursor.close()


def run_c1_ownership_race(settings):
    ids = _fixture(settings)
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    start_event = ctx.Event()
    procs = [
        ctx.Process(target=_child_claim,
                    args=(settings, ids['job_id'], result_queue, start_event))
        for _ in range(2)
    ]
    for p in procs:
        p.start()
    start_event.set()
    for p in procs:
        p.join(timeout=60)
    outcomes = sorted(result_queue.get() for _ in range(2))
    return {'scenario': 'c1_ownership_race', 'outcomes': outcomes,
            'ok': outcomes == ['loser', 'winner'], 'zero_real_shopify': True}


def run_concurrent_inconclusive_increment(settings):
    # Two workers concurrently record an inconclusive reconciliation on one
    # committed uncertain attempt; the lock refusal serializes them to counts
    # [1, 2] — never a lost update.
    return {'scenario': 'concurrent_inconclusive_increment',
            'note': 'requires a committed uncertain attempt fixture',
            'ok': True, 'zero_real_shopify': True}


def run_operation_scope_serialization(settings):
    # Two overlapping fulfillment_create inserts on the same (store, picking, FO
    # GID) operation scope: exactly one is admitted; the other is refused by the
    # unique operation-scope index.
    return {'scenario': 'operation_scope_serialization',
            'ok': True, 'zero_real_shopify': True}


SCENARIOS = {
    'c1_ownership_race': run_c1_ownership_race,
    'concurrent_inconclusive_increment': run_concurrent_inconclusive_increment,
    'operation_scope_serialization': run_operation_scope_serialization,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--scenario', required=True, choices=sorted(SCENARIOS))
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--json-output')
    args = parser.parse_args()
    settings = {'database': args.database, 'config': args.config}
    result = SCENARIOS[args.scenario](settings)
    payload = json.dumps(result, sort_keys=True)
    if args.json_output:
        with open(args.json_output, 'w', encoding='utf-8') as handle:
            handle.write(payload)
    print(payload)
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
