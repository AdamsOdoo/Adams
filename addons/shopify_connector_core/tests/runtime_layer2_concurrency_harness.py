#!/usr/bin/env python3
"""Separate-process runtime proof for DEC-031 Layer 2 concurrency."""

import argparse
import json
import multiprocessing
import os
import queue
import time
import uuid


SCENARIOS = (
    'c1_ownership_race',
    'concurrent_inconclusive_increment',
    'concurrent_stale_sweep',
)
LOCK_REFUSAL = 'The mutation attempt is owned by another worker.'
_RUNTIMES = {}


def _runtime(settings):
    key = (settings['config'], settings['database'])
    if key in _RUNTIMES:
        return _RUNTIMES[key]
    import odoo
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


def _create_fixture(settings, outcome=False):
    runtime, cursor, environment = _new_environment(settings)
    try:
        domain = 'layer2-runtime-%s.myshopify.com' % uuid.uuid4().hex
        store = environment['shopify.connector.store'].create({
            'name': 'Layer 2 runtime concurrency',
            'shop_domain': domain,
            'api_version': '2026-07',
            'state': 'connected',
        })
        job = environment['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation': store.connection_generation,
            'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
        })
        token = False
        attempt = environment['shopify.connector.mutation.attempt']
        if outcome:
            from odoo.addons.shopify_connector_core.models import (
                shopify_connector_mutation_attempt as attempt_module,
            )

            token = uuid.uuid4().hex
            job.sudo().write({
                'state': 'running',
                'current_attempt_token': token,
                'owner_worker_ref': 'runtime:%s' % os.getpid(),
                'running_since': runtime['fields'].Datetime.now(),
            })
            attempt = attempt.with_context(**{
                attempt_module.C2_SENTINEL_CONTEXT:
                    attempt_module.C2_SIDE_CURSOR_SENTINEL,
            })._create_attempt_intent({
                'job_id': job.id,
                'attempt_token': token,
                'mutation_domain': 'mutation_dispatch_selftest',
                'expected_connection_generation':
                    store.connection_generation,
                'expected_store_identity': store.shop_domain,
                'shopify_idempotency_key': uuid.uuid4().hex,
            })
            if outcome != 'pending':
                attempt._record_direct_outcome(outcome)
        fixture = {
            'store_id': store.id,
            'job_id': job.id,
            'attempt_id': attempt.id or False,
            'token': token,
        }
        cursor.commit()
        return fixture
    except BaseException:
        cursor.rollback()
        raise
    finally:
        cursor.close()


def runtime_fields_now(settings):
    return _runtime(settings)['fields'].Datetime.now()


def _cleanup_fixture(settings, fixture):
    runtime, cursor, environment = _new_environment(settings)
    del runtime, environment
    store_id = fixture['store_id']
    job_id = fixture['job_id']
    try:
        cursor.execute(
            'SELECT id FROM shopify_connector_mutation_attempt '
            'WHERE job_id = %s',
            (job_id,),
        )
        attempt_ids = [row[0] for row in cursor.fetchall()]
        child_job_ids = []
        if attempt_ids:
            cursor.execute(
                'SELECT id FROM shopify_connector_job '
                'WHERE mutation_attempt_id = ANY(%s)',
                (attempt_ids,),
            )
            child_job_ids = [row[0] for row in cursor.fetchall()]
        fixture_job_ids = sorted(set([job_id] + child_job_ids))
        cursor.execute(
            'DELETE FROM shopify_connector_job_log '
            'WHERE store_id = %s OR job_id = ANY(%s)',
            (store_id, fixture_job_ids),
        )
        if child_job_ids:
            cursor.execute(
                'DELETE FROM shopify_connector_job '
                'WHERE id = ANY(%s)',
                (child_job_ids,),
            )
        cursor.execute(
            'DELETE FROM shopify_connector_mutation_attempt '
            'WHERE job_id = %s',
            (job_id,),
        )
        cursor.execute(
            'DELETE FROM shopify_connector_job '
            'WHERE id = %s OR store_id = %s',
            (job_id, store_id),
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

    runtime, cursor, environment = _new_environment(settings)
    del runtime, environment
    try:
        checks = {
            'stores': (
                'SELECT count(*) FROM shopify_connector_store '
                'WHERE id = %s', (store_id,),
            ),
            'original_jobs': (
                'SELECT count(*) FROM shopify_connector_job '
                'WHERE id = %s', (job_id,),
            ),
            'attempts': (
                'SELECT count(*) '
                'FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s OR id = ANY(%s)',
                (job_id, attempt_ids),
            ),
            'logs': (
                'SELECT count(*) FROM shopify_connector_job_log '
                'WHERE store_id = %s OR job_id = ANY(%s)',
                (store_id, fixture_job_ids),
            ),
        }
        if child_job_ids:
            checks['child_jobs'] = (
                'SELECT count(*) FROM shopify_connector_job '
                'WHERE id = ANY(%s)', (child_job_ids,),
            )
        residue = {}
        for label, (statement, parameters) in checks.items():
            cursor.execute(statement, parameters)
            residue[label] = cursor.fetchone()[0]
        if any(residue.values()):
            raise AssertionError('runtime fixture residue remains')
        return residue
    finally:
        cursor.rollback()
        cursor.close()


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


def _child_c1(environment, cursor, fixture, loser_reported, timeout):
    locked = environment['shopify.connector.job'].browse(
        fixture['job_id']
    ).try_lock_for_update()
    if locked:
        if not loser_reported.wait(timeout):
            raise TimeoutError('peer result timeout')
        return {'outcome': 'winner'}
    loser_reported.set()
    return {'outcome': 'loser'}


def _child_inconclusive(settings, runtime, fixture, timeout):
    del settings, timeout
    import psycopg2
    from odoo.exceptions import UserError

    retry_reasons = []
    for retry_index in range(5):
        cursor = runtime['registry'].cursor()
        environment = runtime['api'].Environment(
            cursor, runtime['superuser_id'], {},
        )
        try:
            count = environment[
                'shopify.connector.mutation.attempt'
            ].browse(
                fixture['attempt_id']
            )._record_inconclusive_reconciliation(False)
            cursor.commit()
            return {
                'outcome': 'counted',
                'value': count,
                'retry_reasons': retry_reasons,
            }
        except UserError as exc:
            cursor.rollback()
            if str(exc) != LOCK_REFUSAL:
                raise
            retry_reasons.append('production_lock_not_acquired')
        except psycopg2.errors.SerializationFailure:
            cursor.rollback()
            retry_reasons.append('postgres_serialization_failure')
        finally:
            cursor.rollback()
            cursor.close()
        if retry_index == 4:
            break
        time.sleep(0.05)
    raise AssertionError('inconclusive retry budget exhausted')


def _child_stale_sweep(environment, cursor, fixture, timeout):
    del fixture, timeout
    from unittest.mock import patch

    dispatch_class = type(environment['shopify.connector.job.dispatch'])
    with patch.object(
        dispatch_class,
        '_transport_mutation_dispatch_selftest',
        side_effect=AssertionError('mutation transport replayed'),
    ) as transport:
        value = environment[
            'shopify.connector.stale.owner.sweep'
        ].run_sweep()
        cursor.commit()
        if transport.called:
            raise AssertionError('mutation transport replayed')
    return {'outcome': 'sweep', 'value': value}


def _child_entry(
    settings, scenario, fixture, name, ready_queue, start_event,
    result_queue, loser_reported, timeout,
):
    started = time.monotonic()
    result = _base_child_result(name, started)
    cursor = False
    try:
        runtime, cursor, environment = _new_environment(settings)
        ready_queue.put({'child': name, 'pid': os.getpid()})
        if not start_event.wait(timeout):
            raise TimeoutError('start signal timeout')
        if scenario == 'c1_ownership_race':
            outcome = _child_c1(
                environment, cursor, fixture, loser_reported, timeout,
            )
        elif scenario == 'concurrent_inconclusive_increment':
            cursor.rollback()
            cursor.close()
            cursor = False
            outcome = _child_inconclusive(
                settings, runtime, fixture, timeout,
            )
        elif scenario == 'concurrent_stale_sweep':
            outcome = _child_stale_sweep(
                environment, cursor, fixture, timeout,
            )
        else:
            raise ValueError('unknown scenario')
        result.update(outcome)
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


def _run_children(settings, scenario, fixture, timeout):
    context = multiprocessing.get_context('spawn')
    ready_queue = context.Queue()
    result_queue = context.Queue()
    start_event = context.Event()
    loser_reported = context.Event()
    names = ('worker-1', 'worker-2')
    processes = [
        context.Process(
            name='layer2-%s-%s' % (scenario, name),
            target=_child_entry,
            args=(
                settings,
                scenario,
                fixture,
                name,
                ready_queue,
                start_event,
                result_queue,
                loser_reported,
                timeout,
            ),
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
        raise AssertionError('child failure')
    return sorted(records, key=lambda record: record['child'])


def _scenario_summary(name):
    return {
        'scenario': name,
        'passed': False,
        'children': [],
        'cleanup': {},
        'failure': False,
    }


def _finish_cleanup(summary, settings, fixture):
    if not fixture:
        return
    try:
        summary['cleanup'] = _cleanup_fixture(settings, fixture)
    except BaseException as exc:
        summary['passed'] = False
        summary['failure'] = {'exception_class': type(exc).__name__}


def run_c1_ownership_race(settings, timeout):
    summary = _scenario_summary('c1_ownership_race')
    fixture = False
    try:
        fixture = _create_fixture(settings)
        summary['children'] = _run_children(
            settings, summary['scenario'], fixture, timeout,
        )
        outcomes = sorted(
            record['outcome'] for record in summary['children']
        )
        if outcomes != ['loser', 'winner']:
            raise AssertionError('C1 outcomes differ')
        runtime, cursor, environment = _new_environment(settings)
        del runtime
        try:
            job = environment['shopify.connector.job'].browse(
                fixture['job_id']
            )
            if (
                job.state != 'queued'
                or job.current_attempt_token
                or job.owner_worker_ref
                or job.running_since
            ):
                raise AssertionError('C1 fixture changed durably')
            if environment[
                'shopify.connector.mutation.attempt'
            ].search_count([('job_id', '=', job.id)]):
                raise AssertionError('C1 attempt residue')
            if environment['shopify.connector.job.log'].search_count([
                ('job_id', '=', job.id),
            ]):
                raise AssertionError('C1 log residue')
        finally:
            cursor.rollback()
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


def run_concurrent_inconclusive_increment(settings, timeout):
    summary = _scenario_summary('concurrent_inconclusive_increment')
    fixture = False
    try:
        fixture = _create_fixture(settings, 'uncertain')
        summary['children'] = _run_children(
            settings, summary['scenario'], fixture, timeout,
        )
        values = sorted(record['value'] for record in summary['children'])
        if values != [1, 2]:
            raise AssertionError('inconclusive counts differ')

        from unittest.mock import patch

        runtime, cursor, environment = _new_environment(settings)
        del runtime
        try:
            attempt = environment[
                'shopify.connector.mutation.attempt'
            ].browse(fixture['attempt_id'])
            original = environment['shopify.connector.job'].browse(
                fixture['job_id']
            )
            reconciliation = environment[
                'shopify.connector.job'
            ].sudo().create({
                'store_id': original.store_id.id,
                'job_source': 'reconciliation',
                'job_type': 'mutation_dispatch_selftest_reconcile',
                'state': 'running',
                'payload_hash': 'cap:%s' % attempt.attempt_token,
                'mutation_attempt_id': attempt.id,
                'expected_connection_generation':
                    attempt.expected_connection_generation,
            })
            dispatch = environment['shopify.connector.job.dispatch']
            strategy = dict(dispatch._get_reconciliation_strategies()[
                attempt.mutation_domain
            ])
            strategy['reconcile'] = (
                lambda current_attempt, _reconciliation_job: {
                    'verdict': 'inconclusive',
                    'observed_store_identity':
                        current_attempt.expected_store_identity,
                    'action': 'reconcile',
                    'error_class': 'shopify_temporary_server_network',
                    'manual_review_subreason': False,
                    'message': 'Concurrent read remains inconclusive.',
                    'evidence': {'read': 'runtime-concurrent-cap'},
                }
            )
            with patch.object(
                type(dispatch),
                '_get_reconciliation_strategies',
                return_value={attempt.mutation_domain: strategy},
            ):
                dispatch._handle_mutation_dispatch_selftest_reconcile(
                    reconciliation
                )
            attempt.invalidate_recordset()
            original.invalidate_recordset()
            reconciliation.invalidate_recordset()
            if attempt.inconclusive_reconciliation_count != 3:
                raise AssertionError('inconclusive cap not reached')
            if (
                original.state != 'blocked_manual_review'
                or original.manual_review_subreason != 'duplicate_risk'
            ):
                raise AssertionError('original job did not block at cap')
            if reconciliation.state != 'succeeded':
                raise AssertionError('reconciliation job did not finish')
            logs = environment['shopify.connector.job.log'].search_count([
                ('job_id', '=', original.id),
                ('to_state', '=', 'blocked_manual_review'),
            ])
            if logs != 1:
                raise AssertionError('blocking transition log count differs')
            cursor.commit()
        except BaseException:
            cursor.rollback()
            raise
        finally:
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


def run_concurrent_stale_sweep(settings, timeout):
    summary = _scenario_summary('concurrent_stale_sweep')
    fixture = False
    try:
        fixture = _create_fixture(settings, 'pending')
        runtime, cursor, environment = _new_environment(settings)
        del runtime, environment
        try:
            cursor.execute(
                'UPDATE shopify_connector_job '
                "SET running_since = NOW() - INTERVAL '1 hour' "
                'WHERE id = %s',
                (fixture['job_id'],),
            )
            cursor.commit()
        finally:
            cursor.close()

        summary['children'] = _run_children(
            settings, summary['scenario'], fixture, timeout,
        )
        values = sorted(record['value'] for record in summary['children'])
        if values != [0, 1]:
            raise AssertionError('stale sweep outcomes differ')

        runtime, cursor, environment = _new_environment(settings)
        del runtime
        try:
            attempt = environment[
                'shopify.connector.mutation.attempt'
            ].browse(fixture['attempt_id'])
            original = environment['shopify.connector.job'].browse(
                fixture['job_id']
            )
            reconciliations = environment[
                'shopify.connector.job'
            ].search([('mutation_attempt_id', '=', attempt.id)])
            recovery = attempt.remote_evidence_refs.get('recovery') or []
            if len(reconciliations) != 1:
                raise AssertionError('reconciliation job count differs')
            if attempt.observed_outcome != 'uncertain' or attempt.resolved_at:
                raise AssertionError('attempt did not become unresolved')
            if (
                len(recovery) != 1
                or recovery[0].get('source') != 'stale_owner_sweep'
            ):
                raise AssertionError('stale recovery evidence differs')
            if (
                original.current_attempt_token
                or original.owner_worker_ref
                or original.running_since
            ):
                raise AssertionError('stale owner was not cleared')
            reconciliations.sudo().write({
                'state': 'running',
                'started_at': runtime_fields_now(settings),
            })
            environment[
                'shopify.connector.job.dispatch'
            ]._handle_mutation_dispatch_selftest_reconcile(reconciliations)
            attempt.invalidate_recordset()
            original.invalidate_recordset()
            reconciliations.invalidate_recordset()
            if attempt.effective_disposition() != 'applied':
                raise AssertionError('reconciliation verdict not applied')
            if original.state != 'succeeded':
                raise AssertionError('original job did not succeed')
            if reconciliations.state != 'succeeded':
                raise AssertionError('reconciliation job did not finish')
            cursor.commit()
        except BaseException:
            cursor.rollback()
            raise
        finally:
            cursor.close()
        summary['passed'] = True
    except BaseException as exc:
        summary['failure'] = {'exception_class': type(exc).__name__}
    finally:
        _finish_cleanup(summary, settings, fixture)
    return summary


def _parser():
    parser = argparse.ArgumentParser(
        description='Run separate-process Layer 2 concurrency proofs.',
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
    settings = {
        'config': options.config,
        'database': options.database,
    }
    selected = SCENARIOS if options.scenario == 'all' else (options.scenario,)
    runners = {
        'c1_ownership_race': run_c1_ownership_race,
        'concurrent_inconclusive_increment':
            run_concurrent_inconclusive_increment,
        'concurrent_stale_sweep': run_concurrent_stale_sweep,
    }
    results = [
        runners[scenario](settings, options.timeout)
        for scenario in selected
    ]
    summary = {
        'database': options.database,
        'scenario': options.scenario,
        'passed': all(result['passed'] for result in results),
        'results': results,
        'zero_real_shopify': True,
    }
    encoded = json.dumps(summary, sort_keys=True)
    print(encoded)
    if options.json_output:
        with open(options.json_output, 'w', encoding='utf-8') as output:
            output.write(encoded + '\n')
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
