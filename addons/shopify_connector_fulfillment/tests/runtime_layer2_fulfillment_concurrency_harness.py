#!/usr/bin/env python3
"""Genuine independent-process concurrency harness for the Wave 4 fulfillment
Layer 2 mutation path (Stage R2A P1 correction).

This is an OUT-OF-BAND multiprocessing script — it is deliberately NOT imported
by tests/__init__.py and never runs as an Odoo unit test (a TransactionCase
cannot exercise real concurrent workers on independent PostgreSQL connections).
It mirrors the accepted core harness
(shopify_connector_core/tests/runtime_layer2_concurrency_harness.py): OS
processes via the 'spawn' start method (never 'fork'), a per-process Registry +
cursor + Environment, real commit boundaries, bounded timeouts, exit-code
capture, and durable-postcondition + cleanup/residue verification after every
scenario. It performs zero real Shopify calls.

Stage R1 disclosed that `run_concurrent_inconclusive_increment` and
`run_operation_scope_serialization` were hard-coded `ok: True` stubs that did
no concurrent work. Both are now genuine. This correction also adds the
missing frozen-family scenarios required by the Stage R2A control-room ruling
(PR #189 comment 5045580551): duplicate picking/tracking admission, the
reconciliation-job-per-attempt race, the review-release binding race, mode-
switch interaction with an in-flight Layer 2 job, and rollback-injection
recovery. See docs/05-qa/task-014-fulfillment-tracking-validation-results.md
for the family-by-family audit and the exact test this file's evidence
complements (test_fulfillment_concurrency.py's genuine in-suite
db_connect-based operation-scope overlap case).

Side effect note: `review_release_race` and `mode_switch_interaction` call
production actions gated on the `shopify_connector_core.group_shopify_
connector_admin` group. Their fixtures grant that group to the runtime
superuser account once, durably, so the gated call can be exercised as a real
operator would need it to be — this is idempotent (re-running never
duplicates the grant) and is not treated as fixture residue.

Run (against a real Odoo.sh / local database):

    python runtime_layer2_fulfillment_concurrency_harness.py \
        --database DB --config ODOO_CONF --scenario c1_ownership_race
"""
import argparse
import json
import multiprocessing
import os
import queue
import time
import uuid


SCENARIOS = (
    'c1_ownership_race',
    'operation_scope_serialization',
    'concurrent_inconclusive_increment',
    'duplicate_picking_admission',
    'duplicate_tracking_admission',
    'reconciliation_replacement_race',
    'review_release_race',
    'mode_switch_interaction',
    'rollback_injection_recovery',
)

JOB_TYPE_PICKING_ADMISSION = 'fulfillment_picking_admission'
JOB_TYPE_CREATE = 'fulfillment_create'
JOB_TYPE_TRACKING_ADMISSION = 'fulfillment_tracking_admission'
JOB_TYPE_TRACKING_UPDATE = 'fulfillment_tracking_update'
JOB_TYPE_MUTATION_RECONCILE = 'fulfillment_mutation_reconcile'
JOB_TYPE_MODE2_EVALUATION = 'fulfillment_mode2_evaluation'
TRIGGER_ORIGIN_PICKING = 'fulfillment_picking_validation'
TRIGGER_ORIGIN_TRACKING = 'fulfillment_tracking_change'

LOCK_REFUSAL = 'The mutation attempt is owned by another worker.'
_RUNTIMES = {}


# ---------------------------------------------------------------------------
# Per-process runtime bootstrap (mirrors the accepted core harness exactly).
# ---------------------------------------------------------------------------

def _runtime(settings):
    key = (settings['config'], settings['database'])
    if key in _RUNTIMES:
        return _RUNTIMES[key]
    from odoo import SUPERUSER_ID, api, fields
    from odoo.modules.registry import Registry
    from odoo.service import server
    from odoo.tools import config

    config.parse_config([
        '-c', settings['config'],
        '-d', settings['database'],
        '--stop-after-init',
    ])
    server.load_server_wide_modules()
    runtime = {
        'api': api,
        'fields': fields,
        'registry': Registry(settings['database']),
        'superuser_id': SUPERUSER_ID,
    }
    _RUNTIMES[key] = runtime
    return runtime


def _new_environment(settings):
    runtime = _runtime(settings)
    cursor = runtime['registry'].cursor()
    environment = runtime['api'].Environment(
        cursor, runtime['superuser_id'], {},
    )
    return runtime, cursor, environment


def _base_child_result(name, started):
    return {
        'child': name,
        'pid': os.getpid(),
        'outcome': 'unexpected_exception',
        'exception_class': False,
        'sqlstate': False,
        'retry_reasons': [],
        'elapsed_seconds': round(time.monotonic() - started, 6),
    }


def _scenario_summary(name):
    return {
        'scenario': name,
        'passed': False,
        'children': [],
        'cleanup': {},
        'failure': False,
    }


# ---------------------------------------------------------------------------
# Shared fixture builders.
# ---------------------------------------------------------------------------

def _fixture_store(environment, prefix):
    store = environment['shopify.connector.store'].create({
        'name': 'FUL-CONC-%s' % prefix,
        'shop_domain': 'ful-conc-%s-%s.myshopify.com' % (prefix, uuid.uuid4().hex[:8]),
        'api_version': '2026-07', 'state': 'connected',
    })
    environment['shopify.connector.store.settings'].create({
        'store_id': store.id, 'fulfillment_domain_enabled': True,
    })
    return store


def _fixture_sale_stack(environment, store):
    product = environment['product.product'].create({
        'name': 'FUL-CONC product', 'type': 'consu',
    })
    partner = environment['res.partner'].create({'name': 'FUL-CONC customer'})
    sale = environment['sale.order'].create({'partner_id': partner.id})
    order_binding = environment['shopify.connector.order.binding'].sudo().create({
        'store_id': store.id,
        'shopify_gid': 'gid://shopify/Order/%s' % uuid.uuid4().hex[:8],
        'sale_order_id': sale.id, 'status': 'active',
    })
    return product, partner, sale, order_binding


def _fixture_picking(environment, sale):
    stock_loc = environment.ref('stock.stock_location_stock')
    customer_loc = environment.ref('stock.stock_location_customers')
    picking_type = environment['stock.picking.type'].search(
        [('code', '=', 'outgoing')], limit=1,
    )
    return environment['stock.picking'].create({
        'picking_type_id': picking_type.id,
        'location_id': stock_loc.id,
        'location_dest_id': customer_loc.id,
        'sale_id': sale.id,
    })


def _grant_group(environment, xmlid):
    group = environment.ref(xmlid)
    if group.id not in environment.user.sudo().group_ids.ids:
        environment.user.sudo().write({'group_ids': [(4, group.id)]})


# ---------------------------------------------------------------------------
# Shared child-process barrier orchestration (mirrors the accepted core
# harness's _run_children exactly, parameterized by a picklable child target).
# ---------------------------------------------------------------------------

def _run_children(settings, scenario, fixture, timeout, child_target,
                   names=('worker-1', 'worker-2')):
    context = multiprocessing.get_context('spawn')
    ready_queue = context.Queue()
    result_queue = context.Queue()
    start_event = context.Event()
    processes = [
        context.Process(
            name='fulfillment-%s-%s' % (scenario, name),
            target=child_target,
            args=(settings, fixture, name, ready_queue, start_event,
                  result_queue, timeout),
        )
        for name in names
    ]
    started = time.monotonic()
    for process in processes:
        process.start()

    ready = []
    deadline = started + timeout
    while len(ready) < len(processes) and time.monotonic() < deadline:
        try:
            ready.append(ready_queue.get(timeout=0.1))
        except queue.Empty:
            if all(not process.is_alive() for process in processes):
                break
    if len(ready) == len(processes):
        start_event.set()

    for process in processes:
        process.join(max(0.0, deadline - time.monotonic()))
    timed_out = [process for process in processes if process.is_alive()]
    for process in timed_out:
        process.terminate()
    for process in timed_out:
        process.join(5)

    exit_codes = {process.name: process.exitcode for process in processes}

    records = []
    result_deadline = time.monotonic() + 2
    while len(records) < len(processes) and time.monotonic() < result_deadline:
        try:
            records.append(result_queue.get(timeout=0.1))
        except queue.Empty:
            if all(not process.is_alive() for process in processes):
                continue
    reported = {record['child'] for record in records}
    for process, name in zip(processes, names):
        if name not in reported:
            records.append({
                'child': name,
                'pid': process.pid,
                'outcome': 'timeout' if process in timed_out else 'no_result',
                'exception_class': 'TimeoutError'
                    if process in timed_out else 'MissingResultError',
                'sqlstate': False,
                'retry_reasons': [],
                'elapsed_seconds': round(time.monotonic() - started, 6),
            })
    if len(ready) != len(processes):
        raise AssertionError('not every child initialized before release')
    if len(records) != len(processes):
        raise AssertionError('each child must report exactly once')
    if len({record['child'] for record in records}) != len(processes):
        raise AssertionError('duplicate child result')
    failures = [record for record in records if record['exception_class']]
    if failures:
        raise AssertionError('child failure: %r' % (failures,))
    for record in records:
        record['exitcode'] = exit_codes.get(
            'fulfillment-%s-%s' % (scenario, record['child']))
    return sorted(records, key=lambda record: record['child'])


def _finish_cleanup(summary, settings, fixture):
    if not fixture:
        return
    try:
        summary['cleanup'] = _cleanup_fixture(settings, fixture)
    except BaseException as exc:
        summary['passed'] = False
        if not summary['failure']:
            summary['failure'] = {
                'exception_class': type(exc).__name__, 'message': str(exc),
            }


def _cleanup_fixture(settings, fixture):
    store_id = fixture.get('store_id')

    # Pass 1: shopify_connector_* rows. Must precede the picking/sale/partner/
    # product deletions below -- the fulfillment binding FK-references
    # stock.picking, and the mutation attempt FK-references the job.
    _, cursor, environment = _new_environment(settings)
    del environment
    job_ids, attempt_ids = [], []
    try:
        if store_id:
            cursor.execute(
                'SELECT id FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            job_ids = [row[0] for row in cursor.fetchall()]
            if job_ids:
                cursor.execute(
                    'SELECT id FROM shopify_connector_mutation_attempt '
                    'WHERE job_id = ANY(%s)', (job_ids,),
                )
                attempt_ids = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                'DELETE FROM shopify_connector_job_log '
                'WHERE store_id = %s OR job_id = ANY(%s)',
                (store_id, job_ids),
            )
            if attempt_ids:
                cursor.execute(
                    'DELETE FROM shopify_connector_mutation_attempt '
                    'WHERE id = ANY(%s)', (attempt_ids,),
                )
            cursor.execute(
                'DELETE FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            cursor.execute(
                'DELETE FROM shopify_connector_fulfillment_binding '
                'WHERE store_id = %s', (store_id,),
            )
            cursor.execute(
                'DELETE FROM shopify_connector_fulfillment_inbound_evidence '
                'WHERE store_id = %s', (store_id,),
            )
            cursor.execute(
                'DELETE FROM shopify_connector_order_binding '
                'WHERE store_id = %s', (store_id,),
            )
            cursor.execute(
                'DELETE FROM shopify_connector_location WHERE store_id = %s',
                (store_id,),
            )
            cursor.execute(
                'DELETE FROM shopify_connector_store_settings '
                'WHERE store_id = %s', (store_id,),
            )
            cursor.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
        cursor.commit()
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()

    # Pass 2: Odoo-core demo rows, dependency order (picking -> sale lines ->
    # sale -> partner -> product), now safe since no fulfillment row still
    # references them.
    _, cursor, environment = _new_environment(settings)
    try:
        if fixture.get('picking_id'):
            picking = environment['stock.picking'].browse(fixture['picking_id'])
            if picking.exists():
                picking.unlink()
        if fixture.get('sale_id'):
            sale = environment['sale.order'].browse(fixture['sale_id'])
            if sale.exists():
                sale.order_line.unlink()
                sale.unlink()
        if fixture.get('partner_id'):
            partner = environment['res.partner'].browse(fixture['partner_id'])
            if partner.exists():
                partner.unlink()
        if fixture.get('product_id'):
            product = environment['product.product'].browse(fixture['product_id'])
            if product.exists():
                product.unlink()
        cursor.commit()
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()

    # Pass 3: residue verification.
    _, cursor, environment = _new_environment(settings)
    del environment
    try:
        residue = {}
        if store_id:
            checks = {
                'stores': (
                    'SELECT count(*) FROM shopify_connector_store '
                    'WHERE id = %s', (store_id,)),
                'settings': (
                    'SELECT count(*) FROM shopify_connector_store_settings '
                    'WHERE store_id = %s', (store_id,)),
                'jobs': (
                    'SELECT count(*) FROM shopify_connector_job '
                    'WHERE store_id = %s', (store_id,)),
                'bindings': (
                    'SELECT count(*) FROM shopify_connector_fulfillment_binding '
                    'WHERE store_id = %s', (store_id,)),
                'evidence': (
                    'SELECT count(*) FROM '
                    'shopify_connector_fulfillment_inbound_evidence '
                    'WHERE store_id = %s', (store_id,)),
                'order_bindings': (
                    'SELECT count(*) FROM shopify_connector_order_binding '
                    'WHERE store_id = %s', (store_id,)),
                'locations': (
                    'SELECT count(*) FROM shopify_connector_location '
                    'WHERE store_id = %s', (store_id,)),
            }
            if job_ids:
                checks['jobs_by_id'] = (
                    'SELECT count(*) FROM shopify_connector_job '
                    'WHERE id = ANY(%s)', (job_ids,))
            if attempt_ids:
                checks['attempts_by_id'] = (
                    'SELECT count(*) FROM shopify_connector_mutation_attempt '
                    'WHERE id = ANY(%s)', (attempt_ids,))
            for label, (statement, parameters) in checks.items():
                cursor.execute(statement, parameters)
                residue[label] = cursor.fetchone()[0]
        if fixture.get('picking_id'):
            cursor.execute(
                'SELECT count(*) FROM stock_picking WHERE id = %s',
                (fixture['picking_id'],),
            )
            residue['picking'] = cursor.fetchone()[0]
        if fixture.get('sale_id'):
            cursor.execute(
                'SELECT count(*) FROM sale_order WHERE id = %s',
                (fixture['sale_id'],),
            )
            residue['sale_order'] = cursor.fetchone()[0]
        if any(residue.values()):
            raise AssertionError('runtime fixture residue remains: %r' % (residue,))
        return residue
    finally:
        cursor.rollback()
        cursor.close()


# ---------------------------------------------------------------------------
# Scenario 1: c1_ownership_race -- mutation C1 ownership.
# ---------------------------------------------------------------------------

def _create_fixture_c1(settings):
    _, cursor, environment = _new_environment(settings)
    try:
        store = _fixture_store(environment, 'c1')
        job = environment['shopify.connector.job'].create({
            'store_id': store.id, 'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_PICKING,
            'job_type': JOB_TYPE_CREATE, 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 1,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/1',
            'payload_hash': 'conc-c1-%s' % uuid.uuid4().hex[:8],
        })
        cursor.commit()
        return {'store_id': store.id, 'job_id': job.id}
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def _child_c1(settings, fixture, name, ready_queue, start_event, result_queue,
              timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        _, cursor, environment = _new_environment(settings)
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        job = environment['shopify.connector.job'].browse(
            fixture['job_id']).try_lock_for_update()
        result['outcome'] = 'winner' if job else 'loser'
        cursor.commit()
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def run_c1_ownership_race(settings, timeout):
    summary = _scenario_summary('c1_ownership_race')
    fixture = False
    try:
        fixture = _create_fixture_c1(settings)
        summary['children'] = _run_children(
            settings, 'c1_ownership_race', fixture, timeout, _child_c1)
        outcomes = sorted(record['outcome'] for record in summary['children'])
        if outcomes != ['loser', 'winner']:
            raise AssertionError('C1 outcomes differ: %r' % (outcomes,))
        _, cursor, environment = _new_environment(settings)
        try:
            job = environment['shopify.connector.job'].browse(fixture['job_id'])
            if (job.state != 'queued' or job.current_attempt_token
                    or job.owner_worker_ref or job.running_since):
                raise AssertionError(
                    'C1 fixture job changed durably: state=%s token=%s '
                    'owner=%s running_since=%s' % (
                        job.state, job.current_attempt_token,
                        job.owner_worker_ref, job.running_since))
            if environment['shopify.connector.mutation.attempt'].search_count(
                    [('job_id', '=', job.id)]):
                raise AssertionError('C1 attempt residue')
        finally:
            cursor.rollback()
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


# ---------------------------------------------------------------------------
# Scenario 2: operation_scope_serialization -- two workers race to insert a
# fulfillment_create job holding the exact same (store, picking, FO GID)
# operation scope; the DB-level UNIQUE(store_id, operation_scope_key)
# constraint admits exactly one; after the winner terminalizes, a permitted
# replacement with the same scope is admitted.
# ---------------------------------------------------------------------------

def _create_fixture_scope(settings):
    _, cursor, environment = _new_environment(settings)
    try:
        store = _fixture_store(environment, 'scope')
        cursor.commit()
        return {
            'store_id': store.id,
            'res_id': 501,
            'target_gid': 'gid://shopify/FulfillmentOrder/501',
        }
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def _child_scope_insert(settings, fixture, name, ready_queue, start_event,
                         result_queue, timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        _, cursor, environment = _new_environment(settings)
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        from odoo.exceptions import ValidationError
        import psycopg2
        try:
            job = environment['shopify.connector.job'].sudo().create({
                'store_id': fixture['store_id'], 'job_source': 'manual_sync',
                'job_type': JOB_TYPE_CREATE, 'state': 'queued',
                'res_model': 'stock.picking', 'res_id': fixture['res_id'],
                'shopify_target_gid': fixture['target_gid'],
                'payload_hash': 'scope-%s-%s' % (name, uuid.uuid4().hex[:8]),
            })
            cursor.commit()
            result['outcome'] = 'admitted'
            result['job_id'] = job.id
        except (ValidationError, psycopg2.Error) as exc:
            cursor.rollback()
            result['outcome'] = 'refused'
            result['sqlstate'] = getattr(exc, 'pgcode', False)
            result['refusal_class'] = type(exc).__name__
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def run_operation_scope_serialization(settings, timeout):
    summary = _scenario_summary('operation_scope_serialization')
    fixture = False
    try:
        fixture = _create_fixture_scope(settings)
        summary['children'] = _run_children(
            settings, 'operation_scope_serialization', fixture, timeout,
            _child_scope_insert)
        outcomes = sorted(record['outcome'] for record in summary['children'])
        if outcomes != ['admitted', 'refused']:
            raise AssertionError('scope-insert outcomes differ: %r' % (outcomes,))
        winner = next(
            r for r in summary['children'] if r['outcome'] == 'admitted')

        runtime, cursor, environment = _new_environment(settings)
        try:
            Job = environment['shopify.connector.job']
            live = Job.search([
                ('store_id', '=', fixture['store_id']),
                ('shopify_target_gid', '=', fixture['target_gid']),
                ('operation_scope_key', '!=', False),
            ])
            if len(live) != 1 or live.id != winner['job_id']:
                raise AssertionError(
                    'unexpected live-scope holder set: %r (expected only %s)'
                    % (live.ids, winner['job_id']))
            live.sudo().write({
                'state': 'succeeded',
                'finished_at': runtime['fields'].Datetime.now(),
            })
            live.invalidate_recordset()
            if live.operation_scope_key:
                raise AssertionError(
                    'terminal job did not release its operation scope')
            replacement = Job.sudo().create({
                'store_id': fixture['store_id'], 'job_source': 'manual_sync',
                'job_type': JOB_TYPE_CREATE, 'state': 'queued',
                'res_model': 'stock.picking', 'res_id': fixture['res_id'],
                'shopify_target_gid': fixture['target_gid'],
                'payload_hash': 'scope-replacement-%s' % uuid.uuid4().hex[:8],
            })
            if not replacement.operation_scope_key:
                raise AssertionError(
                    'a permitted replacement was not admitted after release')
            still_live = Job.search([
                ('store_id', '=', fixture['store_id']),
                ('shopify_target_gid', '=', fixture['target_gid']),
                ('operation_scope_key', '!=', False),
            ])
            if still_live.ids != [replacement.id]:
                raise AssertionError(
                    'more than one live scope holder after release: %r'
                    % (still_live.ids,))
            cursor.commit()
        except BaseException:
            cursor.rollback()
            raise
        finally:
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


# ---------------------------------------------------------------------------
# Scenario 3: concurrent_inconclusive_increment -- two workers concurrently
# invoke the actual production _record_inconclusive_reconciliation on the
# same committed uncertain attempt; the production lock refusal / PG
# serialization failure is retried only through the accepted bounded policy;
# the durable final count proves no lost update.
# ---------------------------------------------------------------------------

def _create_fixture_inconclusive(settings):
    runtime, cursor, environment = _new_environment(settings)
    try:
        from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
            C2_SENTINEL_CONTEXT, C2_SIDE_CURSOR_SENTINEL,
        )
        store = _fixture_store(environment, 'inconc')
        token = uuid.uuid4().hex
        job = environment['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_PICKING,
            'job_type': JOB_TYPE_CREATE, 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 601,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/601',
            'payload_hash': 'inconc-%s' % uuid.uuid4().hex[:8],
        })
        job.sudo().write({
            'state': 'running', 'current_attempt_token': token,
            'owner_worker_ref': 'runtime:%s' % os.getpid(),
            'running_since': runtime['fields'].Datetime.now(),
        })
        attempt = environment['shopify.connector.mutation.attempt'].with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id, 'attempt_token': token,
            'mutation_domain': JOB_TYPE_CREATE,
            'expected_connection_generation': store.connection_generation,
            'expected_store_identity': store.shop_domain,
            'remote_mutation_intent': {}, 'preconditions_snapshot': {},
            'business_intent_fingerprint': 'bif-inconc',
            'exact_request_fingerprint': 'erf-inconc',
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        attempt._record_direct_outcome('uncertain', evidence={})
        cursor.commit()
        return {'store_id': store.id, 'job_id': job.id, 'attempt_id': attempt.id}
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def _child_inconclusive_increment(settings, fixture, name, ready_queue,
                                   start_event, result_queue, timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        runtime, cursor, environment = _new_environment(settings)
        del environment
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        cursor.rollback()
        cursor.close()
        cursor = False
        import psycopg2
        from odoo.exceptions import UserError
        retry_reasons = []
        value = None
        for retry_index in range(5):
            cursor = runtime['registry'].cursor()
            environment = runtime['api'].Environment(
                cursor, runtime['superuser_id'], {})
            try:
                value = environment[
                    'shopify.connector.mutation.attempt'
                ].browse(fixture['attempt_id'])._record_inconclusive_reconciliation(
                    {'worker': name},
                )
                cursor.commit()
                break
            except UserError as exc:
                cursor.rollback()
                if str(exc) != LOCK_REFUSAL:
                    raise
                retry_reasons.append('production_lock_not_acquired')
            except psycopg2.errors.SerializationFailure:
                cursor.rollback()
                retry_reasons.append('postgres_serialization_failure')
            finally:
                cursor.close()
                cursor = False
            if retry_index == 4:
                raise AssertionError('inconclusive retry budget exhausted')
            time.sleep(0.05)
        result['outcome'] = 'counted'
        result['value'] = value
        result['retry_reasons'] = retry_reasons
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def run_concurrent_inconclusive_increment(settings, timeout):
    summary = _scenario_summary('concurrent_inconclusive_increment')
    fixture = False
    try:
        fixture = _create_fixture_inconclusive(settings)
        summary['children'] = _run_children(
            settings, 'concurrent_inconclusive_increment', fixture, timeout,
            _child_inconclusive_increment)
        values = sorted(record['value'] for record in summary['children'])
        if values != [1, 2]:
            raise AssertionError('inconclusive counts differ: %r' % (values,))
        _, cursor, environment = _new_environment(settings)
        try:
            attempt = environment['shopify.connector.mutation.attempt'].browse(
                fixture['attempt_id'])
            if attempt.inconclusive_reconciliation_count != 2:
                raise AssertionError(
                    'durable count mismatch after concurrent increments: %s'
                    % attempt.inconclusive_reconciliation_count)
            # A third, sequential (non-concurrent) call proves the cap
            # threshold is reachable without the counter skipping or
            # duplicating a value once contention subsides.
            third = attempt._record_inconclusive_reconciliation(
                {'worker': 'sequential-third'})
            if third != 3:
                raise AssertionError(
                    'cap-adjacent third increment skipped a value: got %s'
                    % third)
            cursor.commit()
        except BaseException:
            cursor.rollback()
            raise
        finally:
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


# ---------------------------------------------------------------------------
# Scenarios 4/5: duplicate_picking_admission / duplicate_tracking_admission --
# two workers race the real _enqueue_once dedup choke point with identical
# args; the DB-level UNIQUE(store_id, idempotency_key) constraint admits
# exactly one durable job, and a loser that hits the collision resolves back
# to the same durable record instead of creating a duplicate.
# ---------------------------------------------------------------------------

def _create_fixture_duplicate_admission(settings, job_type, res_model, prefix):
    _, cursor, environment = _new_environment(settings)
    try:
        store = _fixture_store(environment, prefix)
        cursor.commit()
        return {
            'store_id': store.id, 'job_type': job_type, 'res_model': res_model,
            'res_id': 701, 'payload_hash': 'admit-%s' % uuid.uuid4().hex[:8],
        }
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def _create_fixture_duplicate_picking_admission(settings):
    return _create_fixture_duplicate_admission(
        settings, JOB_TYPE_PICKING_ADMISSION, 'stock.picking', 'dpa')


def _create_fixture_duplicate_tracking_admission(settings):
    return _create_fixture_duplicate_admission(
        settings, JOB_TYPE_TRACKING_ADMISSION,
        'shopify.connector.fulfillment.binding', 'dta')


def _child_duplicate_enqueue(settings, fixture, name, ready_queue, start_event,
                              result_queue, timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        _, cursor, environment = _new_environment(settings)
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        from odoo.exceptions import ValidationError
        import psycopg2
        store = environment['shopify.connector.store'].browse(
            fixture['store_id'])
        try:
            job = environment['shopify.connector.fulfillment.service']._enqueue_once(
                store, 'manual_sync', fixture['job_type'],
                fixture['payload_hash'], fixture['res_model'], fixture['res_id'],
                trigger_origin=False,
            )
            cursor.commit()
            result['outcome'] = 'admitted'
            result['job_id'] = job.id
        except (ValidationError, psycopg2.Error) as exc:
            cursor.rollback()
            existing = environment['shopify.connector.job'].search([
                ('store_id', '=', fixture['store_id']),
                ('job_type', '=', fixture['job_type']),
                ('res_model', '=', fixture['res_model']),
                ('res_id', '=', fixture['res_id']),
                ('payload_hash', '=', fixture['payload_hash']),
            ], limit=1)
            result['outcome'] = 'resolved_existing' if existing else 'refused'
            result['job_id'] = existing.id if existing else False
            result['refusal_class'] = type(exc).__name__
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def _run_duplicate_admission_scenario(settings, timeout, scenario_name, fixture_factory):
    summary = _scenario_summary(scenario_name)
    fixture = False
    try:
        fixture = fixture_factory(settings)
        summary['children'] = _run_children(
            settings, scenario_name, fixture, timeout, _child_duplicate_enqueue)
        outcomes = sorted(record['outcome'] for record in summary['children'])
        if outcomes.count('admitted') != 1:
            raise AssertionError(
                'expected exactly one admission, got: %r' % (outcomes,))
        loser_outcome = [o for o in outcomes if o != 'admitted'][0]
        if loser_outcome not in ('refused', 'resolved_existing'):
            raise AssertionError('unexpected loser outcome: %r' % (loser_outcome,))
        winner = next(
            r for r in summary['children'] if r['outcome'] == 'admitted')
        loser = next(
            r for r in summary['children'] if r['outcome'] != 'admitted')
        if loser['outcome'] == 'resolved_existing' and loser['job_id'] != winner['job_id']:
            raise AssertionError(
                'loser resolved to a different durable record than the winner')

        _, cursor, environment = _new_environment(settings)
        try:
            durable = environment['shopify.connector.job'].search([
                ('store_id', '=', fixture['store_id']),
                ('job_type', '=', fixture['job_type']),
                ('res_model', '=', fixture['res_model']),
                ('res_id', '=', fixture['res_id']),
                ('payload_hash', '=', fixture['payload_hash']),
            ])
            if len(durable) != 1:
                raise AssertionError(
                    'duplicate admission job rows durably exist: %r'
                    % (durable.ids,))
        finally:
            cursor.rollback()
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


def run_duplicate_picking_admission(settings, timeout):
    return _run_duplicate_admission_scenario(
        settings, timeout, 'duplicate_picking_admission',
        _create_fixture_duplicate_picking_admission)


def run_duplicate_tracking_admission(settings, timeout):
    return _run_duplicate_admission_scenario(
        settings, timeout, 'duplicate_tracking_admission',
        _create_fixture_duplicate_tracking_admission)


# ---------------------------------------------------------------------------
# Scenario 6: reconciliation_replacement_race -- two workers concurrently
# attempt to create a fulfillment_mutation_reconcile job for the SAME
# committed uncertain mutation.attempt; the DB-level partial UniqueIndex
# "(mutation_attempt_id) WHERE mutation_attempt_id IS NOT NULL" admits
# exactly one reconcile-job owner per attempt -- proving one shared reconcile
# and no second mutation reachable from post-C2 uncertainty.
# ---------------------------------------------------------------------------

def _child_reconcile_race(settings, fixture, name, ready_queue, start_event,
                           result_queue, timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        _, cursor, environment = _new_environment(settings)
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        from odoo.exceptions import ValidationError
        import psycopg2
        attempt = environment['shopify.connector.mutation.attempt'].browse(
            fixture['attempt_id'])
        try:
            job = environment['shopify.connector.job'].sudo().create({
                'store_id': fixture['store_id'], 'job_source': 'reconciliation',
                'job_type': JOB_TYPE_MUTATION_RECONCILE, 'state': 'queued',
                'payload_hash': 'reconcile-%s-%s' % (name, uuid.uuid4().hex[:8]),
                'mutation_attempt_id': attempt.id,
                'expected_connection_generation': attempt.expected_connection_generation,
            })
            cursor.commit()
            result['outcome'] = 'admitted'
            result['job_id'] = job.id
        except (ValidationError, psycopg2.Error) as exc:
            cursor.rollback()
            result['outcome'] = 'refused'
            result['refusal_class'] = type(exc).__name__
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def run_reconciliation_replacement_race(settings, timeout):
    summary = _scenario_summary('reconciliation_replacement_race')
    fixture = False
    try:
        fixture = _create_fixture_inconclusive(settings)
        summary['children'] = _run_children(
            settings, 'reconciliation_replacement_race', fixture, timeout,
            _child_reconcile_race)
        outcomes = sorted(record['outcome'] for record in summary['children'])
        if outcomes != ['admitted', 'refused']:
            raise AssertionError('reconcile-race outcomes differ: %r' % (outcomes,))
        _, cursor, environment = _new_environment(settings)
        try:
            reconciles = environment['shopify.connector.job'].search([
                ('mutation_attempt_id', '=', fixture['attempt_id']),
                ('job_type', '=', JOB_TYPE_MUTATION_RECONCILE),
            ])
            if len(reconciles) != 1:
                raise AssertionError(
                    'more than one reconcile job owns the same attempt: %r'
                    % (reconciles.ids,))
            original = environment['shopify.connector.job'].browse(
                fixture['job_id'])
            if original.state != 'running':
                raise AssertionError(
                    'original mutation job state disturbed by the race: %s'
                    % original.state)
        finally:
            cursor.rollback()
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


# ---------------------------------------------------------------------------
# Scenario 7: review_release_race -- two authorized _release_blocked_mutation
# calls overlap on the same fulfillment binding; the binding-level
# try_lock_for_update refuses the second; exactly one blocked job is
# released, exactly one permitted replacement is created, and lineage
# (superseded_by_job_id) is preserved.
# ---------------------------------------------------------------------------

def _create_fixture_review_release(settings):
    runtime, cursor, environment = _new_environment(settings)
    try:
        store = _fixture_store(environment, 'release')
        _grant_group(
            environment, 'shopify_connector_core.group_shopify_connector_admin')
        product, partner, sale, order_binding = _fixture_sale_stack(
            environment, store)
        picking = _fixture_picking(environment, sale)
        binding = environment['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/%s' % uuid.uuid4().hex[:8],
            'picking_id': picking.id, 'order_binding_id': order_binding.id,
            'status': 'active',
        })
        job = environment['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_TRACKING,
            'job_type': JOB_TYPE_TRACKING_UPDATE, 'state': 'queued',
            'res_model': 'shopify.connector.fulfillment.binding',
            'res_id': binding.id, 'shopify_target_gid': binding.shopify_gid,
            'payload_hash': uuid.uuid4().hex,
        })
        job.sudo().write({
            'state': 'failed_retryable',
            'error_class': 'shopify_temporary_server_network',
            'finished_at': runtime['fields'].Datetime.now(),
        })
        cursor.commit()
        return {
            'store_id': store.id, 'product_id': product.id,
            'partner_id': partner.id, 'sale_id': sale.id,
            'picking_id': picking.id, 'binding_id': binding.id, 'job_id': job.id,
        }
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def _child_release_race(settings, fixture, name, ready_queue, start_event,
                         result_queue, timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        _, cursor, environment = _new_environment(settings)
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        from odoo.exceptions import UserError
        binding = environment['shopify.connector.fulfillment.binding'].browse(
            fixture['binding_id'])
        try:
            new_job = environment[
                'shopify.connector.fulfillment.service'
            ]._release_blocked_mutation(
                binding, 'runtime concurrency release (%s)' % name)
            cursor.commit()
            result['outcome'] = 'released'
            result['new_job_id'] = new_job.id
        except UserError as exc:
            cursor.rollback()
            if 'held by another operation' not in str(exc):
                raise
            result['outcome'] = 'refused'
            result['message'] = str(exc)
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def run_review_release_race(settings, timeout):
    summary = _scenario_summary('review_release_race')
    fixture = False
    try:
        fixture = _create_fixture_review_release(settings)
        summary['children'] = _run_children(
            settings, 'review_release_race', fixture, timeout,
            _child_release_race)
        outcomes = sorted(record['outcome'] for record in summary['children'])
        if outcomes != ['refused', 'released']:
            raise AssertionError('review-release outcomes differ: %r' % (outcomes,))
        _, cursor, environment = _new_environment(settings)
        try:
            original = environment['shopify.connector.job'].browse(
                fixture['job_id'])
            if original.state != 'cancelled' or not original.superseded_by_job_id:
                raise AssertionError(
                    'predecessor not terminalized/linked: state=%s superseded=%s'
                    % (original.state, original.superseded_by_job_id))
            replacements = environment['shopify.connector.job'].search([
                ('res_model', '=', 'shopify.connector.fulfillment.binding'),
                ('res_id', '=', fixture['binding_id']),
                ('job_source', '=', 'manual_sync'),
            ])
            if len(replacements) != 1:
                raise AssertionError(
                    'more than one permitted replacement created: %r'
                    % (replacements.ids,))
            if replacements.id != original.superseded_by_job_id.id:
                raise AssertionError(
                    'lineage broken: replacement does not match '
                    'superseded_by_job_id')
        finally:
            cursor.rollback()
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


# ---------------------------------------------------------------------------
# Scenario 8: mode_switch_interaction -- overlap action_rollback_to_mode1
# with an already-running fulfillment_create job held under an uncommitted
# row lock; the switch must complete without depending on that lock (proven
# by real elapsed-time evidence, not just by inspecting the code), the
# in-flight mutation job must be untouched, and a queued Mode 2 evaluation
# job must be cancelled by the switch.
# ---------------------------------------------------------------------------

def _create_fixture_mode_switch(settings):
    runtime, cursor, environment = _new_environment(settings)
    try:
        store = _fixture_store(environment, 'modesw')
        _grant_group(
            environment, 'shopify_connector_core.group_shopify_connector_admin')
        settings_row = environment['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1)
        settings_row.sudo().write({'fulfillment_operating_mode': 'mode2'})
        token = uuid.uuid4().hex
        mutation_job = environment['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_PICKING,
            'job_type': JOB_TYPE_CREATE, 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 801,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/801',
            'payload_hash': 'modesw-mutation-%s' % uuid.uuid4().hex[:8],
        })
        mutation_job.sudo().write({
            'state': 'running', 'current_attempt_token': token,
            'owner_worker_ref': 'runtime:%s' % os.getpid(),
            'running_since': runtime['fields'].Datetime.now(),
        })
        eval_job = environment['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'reconciliation',
            'job_type': JOB_TYPE_MODE2_EVALUATION, 'state': 'queued',
            'res_model': 'shopify.connector.fulfillment.inbound.evidence',
            'res_id': 802, 'payload_hash': 'modesw-eval-%s' % uuid.uuid4().hex[:8],
        })
        cursor.commit()
        return {
            'store_id': store.id, 'mutation_job_id': mutation_job.id,
            'eval_job_id': eval_job.id, 'token': token,
        }
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def _child_hold_mutation_lock(settings, fixture, name, ready_queue, start_event,
                               result_queue, timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        _, cursor, environment = _new_environment(settings)
        job = environment['shopify.connector.job'].browse(
            fixture['mutation_job_id']).try_lock_for_update()
        if not job:
            raise AssertionError('could not acquire the fixture lock before the hold')
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        time.sleep(2.0)
        result['outcome'] = 'held'
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def _child_mode_switch_rollback(settings, fixture, name, ready_queue,
                                 start_event, result_queue, timeout):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        _, cursor, environment = _new_environment(settings)
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        settings_row = environment['shopify.connector.store.settings'].search(
            [('store_id', '=', fixture['store_id'])], limit=1)
        settings_row.sudo().action_rollback_to_mode1()
        cursor.commit()
        result['outcome'] = 'switched'
        result['exception_class'] = False
    except BaseException as exc:
        result['exception_class'] = type(exc).__name__
        result['sqlstate'] = getattr(exc, 'pgcode', False)
    finally:
        if cursor:
            cursor.rollback()
            cursor.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 6)
        result_queue.put(result)


def run_mode_switch_interaction(settings, timeout):
    summary = _scenario_summary('mode_switch_interaction')
    fixture = False
    try:
        fixture = _create_fixture_mode_switch(settings)
        # Two distinct child roles (not two identical workers), so this is
        # built by hand rather than through the generic _run_children helper.
        context = multiprocessing.get_context('spawn')
        ready_queue = context.Queue()
        result_queue = context.Queue()
        start_event = context.Event()
        holder = context.Process(
            name='fulfillment-mode_switch_interaction-holder',
            target=_child_hold_mutation_lock,
            args=(settings, fixture, 'holder', ready_queue, start_event,
                  result_queue, timeout),
        )
        switcher = context.Process(
            name='fulfillment-mode_switch_interaction-switcher',
            target=_child_mode_switch_rollback,
            args=(settings, fixture, 'switcher', ready_queue, start_event,
                  result_queue, timeout),
        )
        processes = [holder, switcher]
        started = time.monotonic()
        for process in processes:
            process.start()
        ready = []
        deadline = started + timeout
        while len(ready) < len(processes) and time.monotonic() < deadline:
            try:
                ready.append(ready_queue.get(timeout=0.1))
            except queue.Empty:
                if all(not p.is_alive() for p in processes):
                    break
        if len(ready) != len(processes):
            raise AssertionError('not every child initialized before release')
        start_event.set()
        for process in processes:
            process.join(max(0.0, deadline - time.monotonic()))
        timed_out = [p for p in processes if p.is_alive()]
        for p in timed_out:
            p.terminate()
        for p in timed_out:
            p.join(5)
        exit_codes = {process.name: process.exitcode for process in processes}
        records = []
        result_deadline = time.monotonic() + 2
        while len(records) < len(processes) and time.monotonic() < result_deadline:
            try:
                records.append(result_queue.get(timeout=0.1))
            except queue.Empty:
                if all(not p.is_alive() for p in processes):
                    continue
        if len(records) != len(processes):
            raise AssertionError('each child must report exactly once')
        summary['children'] = sorted(records, key=lambda r: r['child'])
        for record in summary['children']:
            record['exitcode'] = exit_codes.get(
                'fulfillment-mode_switch_interaction-%s' % record['child'])
        failures = [r for r in summary['children'] if r['exception_class']]
        if failures:
            raise AssertionError('child failure: %r' % (failures,))
        bad_exits = [
            r for r in summary['children']
            if r['exitcode'] not in (0, None) and not r['exception_class']
        ]
        if bad_exits:
            raise AssertionError(
                'child exited non-zero without a captured exception: %r'
                % (bad_exits,))
        holder_record = next(r for r in summary['children'] if r['child'] == 'holder')
        switcher_record = next(r for r in summary['children'] if r['child'] == 'switcher')
        if switcher_record['outcome'] != 'switched':
            raise AssertionError('mode switch was blocked/failed: %r' % (switcher_record,))
        if switcher_record['elapsed_seconds'] >= holder_record['elapsed_seconds']:
            raise AssertionError(
                'mode switch did not complete independently of the held '
                'mutation-job lock: switcher=%.3fs holder=%.3fs' % (
                    switcher_record['elapsed_seconds'],
                    holder_record['elapsed_seconds']))

        _, cursor, environment = _new_environment(settings)
        try:
            mutation_job = environment['shopify.connector.job'].browse(
                fixture['mutation_job_id'])
            if (mutation_job.state != 'running'
                    or mutation_job.current_attempt_token != fixture['token']):
                raise AssertionError(
                    'in-flight mutation job was disturbed by the mode '
                    'switch: state=%s token=%s' % (
                        mutation_job.state, mutation_job.current_attempt_token))
            eval_job = environment['shopify.connector.job'].browse(
                fixture['eval_job_id'])
            if eval_job.state != 'cancelled':
                raise AssertionError(
                    'queued mode2-evaluation job was not cancelled by the '
                    'switch: %s' % eval_job.state)
            settings_row = environment['shopify.connector.store.settings'].search(
                [('store_id', '=', fixture['store_id'])], limit=1)
            if settings_row.fulfillment_operating_mode != 'mode1':
                raise AssertionError(
                    'store did not roll back to mode1: %s'
                    % settings_row.fulfillment_operating_mode)
        finally:
            cursor.rollback()
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


# ---------------------------------------------------------------------------
# Scenario 9: rollback_injection_recovery -- one worker claims a job (writes
# the C1 ownership fields, uncommitted) then is killed with os._exit before
# it can commit; a second worker is genuinely refused while the crasher
# still holds the row; after the crash, PostgreSQL rolls back the dropped
# connection's transaction automatically and a fresh worker can claim the
# job cleanly, with zero residual owner/scope/attempt state.
# ---------------------------------------------------------------------------

def _create_fixture_rollback_injection(settings):
    _, cursor, environment = _new_environment(settings)
    try:
        store = _fixture_store(environment, 'rollback')
        job = environment['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_PICKING,
            'job_type': JOB_TYPE_CREATE, 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 901,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/901',
            'payload_hash': 'rollback-%s' % uuid.uuid4().hex[:8],
        })
        cursor.commit()
        return {'store_id': store.id, 'job_id': job.id}
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def _child_crash_after_claim(settings, fixture, ready_event, crash_event,
                              held_result_queue):
    runtime, cursor, environment = _new_environment(settings)
    del cursor
    job = environment['shopify.connector.job'].browse(
        fixture['job_id']).try_lock_for_update()
    if not job:
        held_result_queue.put({'claimed': False})
        ready_event.set()
        return
    job.sudo().write({
        'state': 'running',
        'current_attempt_token': 'crash-token-%s' % os.getpid(),
        'owner_worker_ref': 'runtime-crash:%s' % os.getpid(),
        'running_since': runtime['fields'].Datetime.now(),
    })
    job.flush_recordset(
        ['state', 'current_attempt_token', 'owner_worker_ref', 'running_since'])
    held_result_queue.put({'claimed': True, 'pid': os.getpid()})
    ready_event.set()
    crash_event.wait(30)
    # Deliberate hard crash: no commit, no cursor.close(), no graceful
    # unwind. The child process dies immediately; PostgreSQL rolls back the
    # entire uncommitted transaction when the dropped connection is reaped --
    # a genuine rollback-injection proof, not a simulated cursor.rollback().
    os._exit(37)


def _child_probe_lock(settings, fixture, expect, result_queue):
    _, cursor, environment = _new_environment(settings)
    try:
        job = environment['shopify.connector.job'].browse(
            fixture['job_id']).try_lock_for_update()
        outcome = 'locked' if job else 'refused'
        details = {}
        if job:
            details = {
                'state': job.state,
                'current_attempt_token': job.current_attempt_token,
                'owner_worker_ref': job.owner_worker_ref,
                'running_since': bool(job.running_since),
                'operation_scope_key': job.operation_scope_key,
            }
        cursor.rollback()
        result_queue.put({
            'outcome': outcome, 'expect': expect, 'details': details,
            'pid': os.getpid(),
        })
    except BaseException as exc:
        result_queue.put({
            'outcome': 'error', 'expect': expect,
            'exception_class': type(exc).__name__,
        })
    finally:
        cursor.close()


def run_rollback_injection_recovery(settings, timeout):
    summary = _scenario_summary('rollback_injection_recovery')
    fixture = False
    try:
        fixture = _create_fixture_rollback_injection(settings)
        context = multiprocessing.get_context('spawn')
        ready_event = context.Event()
        crash_event = context.Event()
        held_result_queue = context.Queue()
        probe_result_queue = context.Queue()

        crasher = context.Process(
            name='fulfillment-rollback_injection_recovery-crasher',
            target=_child_crash_after_claim,
            args=(settings, fixture, ready_event, crash_event, held_result_queue),
        )
        crasher.start()
        if not ready_event.wait(timeout):
            crasher.terminate()
            raise TimeoutError('crasher did not signal it held the lock')
        held = held_result_queue.get(timeout=timeout)
        if not held.get('claimed'):
            raise AssertionError('crasher could not claim the fixture job')

        probe_while_held = context.Process(
            name='fulfillment-rollback_injection_recovery-probe-held',
            target=_child_probe_lock,
            args=(settings, fixture, 'refused', probe_result_queue),
        )
        probe_while_held.start()
        probe_while_held.join(timeout)
        while_held = probe_result_queue.get(timeout=timeout)
        if while_held['outcome'] != 'refused':
            raise AssertionError(
                'a second worker was NOT refused while the crasher held the '
                'lock: %r' % (while_held,))

        crash_event.set()
        crasher.join(timeout)
        if crasher.is_alive():
            crasher.terminate()
            crasher.join(5)
            raise AssertionError(
                'crasher process did not terminate within the bounded timeout')
        if crasher.exitcode != 37:
            raise AssertionError(
                'crasher did not exit with the expected crash code: %r'
                % (crasher.exitcode,))

        # Bounded pause for PostgreSQL to reap the dropped backend connection
        # before the recovery probe -- not a raw sleep loop, one fixed wait.
        time.sleep(0.5)

        probe_after_crash = context.Process(
            name='fulfillment-rollback_injection_recovery-probe-recovered',
            target=_child_probe_lock,
            args=(settings, fixture, 'locked', probe_result_queue),
        )
        probe_after_crash.start()
        probe_after_crash.join(timeout)
        after_crash = probe_result_queue.get(timeout=timeout)
        if after_crash['outcome'] != 'locked':
            raise AssertionError(
                'a fresh worker could NOT claim the job after the crash: %r'
                % (after_crash,))
        details = after_crash['details']
        if (details.get('state') != 'queued' or details.get('current_attempt_token')
                or details.get('owner_worker_ref') or details.get('running_since')):
            raise AssertionError(
                'crashed claim left durable owner/state residue: %r' % (details,))
        if not details.get('operation_scope_key'):
            raise AssertionError(
                'the queued job unexpectedly lost its live operation scope')

        summary['children'] = [
            {'child': 'crasher', 'outcome': 'crashed',
             'exitcode': crasher.exitcode, 'exception_class': False},
            {'child': 'probe_while_held', 'outcome': while_held['outcome'],
             'exception_class': False},
            {'child': 'probe_after_crash', 'outcome': after_crash['outcome'],
             'exception_class': False},
        ]

        _, cursor, environment = _new_environment(settings)
        try:
            job = environment['shopify.connector.job'].browse(fixture['job_id'])
            if (job.state != 'queued' or job.current_attempt_token
                    or job.owner_worker_ref or job.running_since
                    or not job.operation_scope_key):
                raise AssertionError(
                    'final durable read shows leaked owner/scope state: %r'
                    % (job.read(['state', 'current_attempt_token',
                                 'owner_worker_ref', 'running_since',
                                 'operation_scope_key']),))
            if environment['shopify.connector.mutation.attempt'].search_count(
                    [('job_id', '=', job.id)]):
                raise AssertionError(
                    'an orphan mutation.attempt exists after the crash')
        finally:
            cursor.rollback()
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__, 'message': str(exc)}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

RUNNERS = {
    'c1_ownership_race': run_c1_ownership_race,
    'operation_scope_serialization': run_operation_scope_serialization,
    'concurrent_inconclusive_increment': run_concurrent_inconclusive_increment,
    'duplicate_picking_admission': run_duplicate_picking_admission,
    'duplicate_tracking_admission': run_duplicate_tracking_admission,
    'reconciliation_replacement_race': run_reconciliation_replacement_race,
    'review_release_race': run_review_release_race,
    'mode_switch_interaction': run_mode_switch_interaction,
    'rollback_injection_recovery': run_rollback_injection_recovery,
}


def _parser():
    parser = argparse.ArgumentParser(
        description='Run separate-process fulfillment Layer 2 concurrency proofs.',
    )
    parser.add_argument('--database', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument(
        '--scenario', choices=SCENARIOS + ('all',), default='all',
    )
    parser.add_argument('--timeout', type=float, default=30.0)
    parser.add_argument('--json-output')
    return parser


def main(arguments=None):
    options = _parser().parse_args(arguments)
    settings = {'config': options.config, 'database': options.database}
    selected = SCENARIOS if options.scenario == 'all' else (options.scenario,)
    results = [RUNNERS[scenario](settings, options.timeout) for scenario in selected]
    summary = {
        'database': options.database,
        'scenario': options.scenario,
        'passed': all(result['passed'] for result in results),
        'results': results,
        'zero_real_shopify': True,
    }
    encoded = json.dumps(summary, sort_keys=True, default=str)
    print(encoded)
    if options.json_output:
        with open(options.json_output, 'w', encoding='utf-8') as output:
            output.write(encoded + '\n')
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
