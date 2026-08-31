"""Shared real-connection fixtures for the P10 runtime concurrency proofs."""

from contextlib import contextmanager
from datetime import datetime, timezone
import queue
import threading
import time
import uuid
from unittest.mock import patch

from odoo import SUPERUSER_ID, api
from odoo.sql_db import db_connect

from ..models.shopify_connector_v2_runtime_repository import (
    OdooReadOnlyRuntimeRepository,
)
from ..runtime.p10_coordinator import CLAIM_TRANSACTION
from ..tools.api_version import SHOPIFY_API_VERSION


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class V2RuntimeConnectionMixin:
    """Real connections and bounded worker helpers for P10 tests."""

    STATEMENT_TIMEOUT_MS = 12000
    LOCK_TIMEOUT_MS = 4000
    WORKER_TIMEOUT_SECONDS = 15

    def _open_bounded(self):
        """Open one pooled cursor with transaction-local safety limits."""
        cr = db_connect(self.env.cr.dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _new_env(self, allowed_company_ids=None):
        cr = self._open_bounded()
        context = {}
        if allowed_company_ids is not None:
            context['allowed_company_ids'] = list(allowed_company_ids)
        try:
            env = api.Environment(cr, SUPERUSER_ID, context)
        except BaseException:
            try:
                cr.rollback()
            finally:
                cr.close()
            raise
        return cr, env

    @contextmanager
    def _real_registry_cursor(self, backend_pids=None):
        """Make the repository's production side cursor genuinely pooled.

        In Odoo's ``registry_enter_test_mode`` the registry cursor helper may
        return a ``TestCursor`` tied to the TransactionCase connection.  The
        runtime itself is not changed for this proof: only the test-mode
        helper is redirected to a fresh ``db_connect`` cursor.  Recording the
        backend PID makes an accidental shared session observable.
        """

        def open_cursor(*_args, **_kwargs):
            cr = self._open_bounded()
            if backend_pids is not None:
                cr.execute('SELECT pg_backend_pid()')
                backend_pids.append(cr.fetchone()[0])
            return cr

        with patch.object(
            self.registry, 'cursor', side_effect=open_cursor,
        ):
            yield

    def _run_threads(self, workers, timeout=None):
        """Run bounded worker callables and return one result per worker."""
        timeout = timeout or self.WORKER_TIMEOUT_SECONDS
        results = queue.Queue(maxsize=len(workers))

        def invoke(name, worker):
            started = time.monotonic()
            try:
                value = worker()
                results.put((name, {
                    'ok': True,
                    'value': value,
                    'elapsed': time.monotonic() - started,
                }))
            except BaseException as exc:  # report, then fail below
                results.put((name, {
                    'ok': False,
                    'exception_class': type(exc).__name__,
                    'sqlstate': getattr(exc, 'pgcode', False),
                    'elapsed': time.monotonic() - started,
                }))

        threads = [
            threading.Thread(
                name='p10-runtime-%s' % name,
                target=invoke,
                args=(name, worker),
                daemon=True,
            )
            for name, worker in workers.items()
        ]
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + timeout
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))

        alive = [thread.name for thread in threads if thread.is_alive()]
        self.assertFalse(
            alive,
            'P10 PostgreSQL workers exceeded the bounded deadline: %s' % alive,
        )
        records = {}
        while len(records) < len(workers):
            try:
                name, record = results.get(timeout=1)
            except queue.Empty as exc:
                self.fail('P10 worker did not report within the deadline')
                raise exc
            self.assertNotIn(name, records, 'worker reported twice')
            records[name] = record
        failures = {
            name: record for name, record in records.items()
            if not record['ok']
        }
        self.assertFalse(
            failures,
            'P10 worker failure(s): %r' % failures,
        )
        return {name: record['value'] for name, record in records.items()}


class V2RuntimeFixtureMixin:
    """Committed fixtures and complete teardown for P10 tests."""

    def _create_fixture(self, *, company_count=1, job_count=1):
        """Create connected/read-only stores, an admitted run and queued jobs."""
        if company_count not in (1, 2):
            raise ValueError('fixture supports one or two companies')
        if isinstance(job_count, bool) or not 0 < job_count <= 4:
            raise ValueError('fixture job count must be between 1 and 4')

        tag = uuid.uuid4().hex
        cr = self._open_bounded()
        stores = []
        runs = []
        jobs = []
        companies = []
        created_company_ids = []
        created_partner_ids = []
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            companies.append(env.company)
            if company_count == 2:
                company = env['res.company'].create({
                    'name': 'P10 concurrency company %s' % tag,
                })
                companies.append(company)
                created_company_ids.append(company.id)
                # res.company.create() creates the company's partner on Odoo
                # versions where partner_id is managed by the base model.  A
                # committed fixture must retain that identity for cleanup;
                # deleting only res_company would leave an orphan partner or
                # fail on the partner FK.
                if company.partner_id:
                    created_partner_ids.append(company.partner_id.id)

            for index, company in enumerate(companies):
                store = env['shopify.connector.store'].sudo().create({
                    'name': 'P10 concurrency store %s-%d' % (tag, index),
                    'shop_domain': 'p10-runtime-%s-%d.myshopify.com' % (
                        tag, index,
                    ),
                    'api_version': SHOPIFY_API_VERSION,
                    'state': 'connected',
                    'company_id': company.id,
                })
                settings = env[
                    'shopify.connector.store.settings'
                ].sudo().search([('store_id', '=', store.id)], limit=1)
                if not settings:
                    settings = env[
                        'shopify.connector.store.settings'
                    ].sudo().create({'store_id': store.id})
                # This fixture is intentionally configured without the mode
                # service's audit job.  The runtime only needs a committed,
                # canonical settings row and generation zero.
                env.flush_all()
                cr.execute(
                    'UPDATE shopify_connector_store_settings '
                    "SET v2_runtime_mode = 'read_only', "
                    'configuration_generation = 0 WHERE id = %s',
                    (settings.id,),
                )
                env.invalidate_all()
                stores.append({
                    'record': store,
                    'settings_id': settings.id,
                    'company_id': company.id,
                })

            # Each fixture store gets its own admitted run and jobs so company
            # A can never claim company B's work.
            for store_info in stores:
                store = env[
                    'shopify.connector.store'
                ].browse(store_info['record'].id)
                run = env['shopify.connector.run']._create_service({
                    'store_id': store.id,
                    'request_key': 'p10-runtime-%s-%s' % (tag, store.id),
                    'workflow': 'core',
                    'operation': 'runtime.concurrency',
                    'trigger': 'system',
                    'scope_summary': 'P10 runtime concurrency fixture',
                    'configuration_snapshot': {
                        'fixture': 'p10_runtime_concurrency',
                        'configuration_generation': 0,
                    },
                    'correlation_id': 'p10-runtime:%s:%s' % (tag, store.id),
                })
                run._admit_service(admitted_at=NOW.replace(tzinfo=None))
                runs.append(run.id)
                store_info['run_id'] = run.id

                for job_index in range(job_count):
                    job = env['shopify.connector.job'].sudo().create({
                        'store_id': store.id,
                        'run_id': run.id,
                        'job_source': 'setup_readiness_check',
                        'job_type': 'core_dispatch_selftest',
                        'state': 'queued',
                        'payload_hash': '%s-%d' % (tag, job_index),
                        'lane': 'interactive',
                        'lane_priority': 100,
                        'available_at': NOW.replace(tzinfo=None),
                        'expected_connection_generation':
                            store.connection_generation,
                        'expected_configuration_generation': 0,
                    })
                    jobs.append(job.id)
                    store_info.setdefault('job_ids', []).append(job.id)

            env.flush_all()
            fixture = {
                'tag': tag,
                'company_ids': [company.id for company in companies],
                'created_company_ids': created_company_ids,
                'created_partner_ids': created_partner_ids,
                'stores': stores,
                'store_ids': [item['record'].id for item in stores],
                'run_ids': runs,
                'job_ids': jobs,
            }
            cr.commit()
        except BaseException:
            cr.rollback()
            raise
        finally:
            cr.close()
        self.addCleanup(self._cleanup_fixture, fixture)
        return fixture

    def _cleanup_fixture(self, fixture):
        """Delete committed rows, then verify connector and base residue."""
        if not fixture:
            return
        store_ids = tuple(fixture.get('store_ids', ()))
        run_ids = tuple(fixture.get('run_ids', ()))
        job_ids = tuple(fixture.get('job_ids', ()))
        created_company_ids = tuple(fixture.get('created_company_ids', ()))
        created_partner_ids = tuple(fixture.get('created_partner_ids', ()))
        if not store_ids:
            return
        cr = self._open_bounded()
        try:
            cr.execute(
                'DELETE FROM shopify_connector_job_log '
                'WHERE store_id = ANY(%s)', (list(store_ids),),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job_attempt '
                'WHERE job_id = ANY(%s)', (list(job_ids),),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job '
                'WHERE store_id = ANY(%s)', (list(store_ids),),
            )
            cr.execute(
                'DELETE FROM shopify_connector_run '
                'WHERE id = ANY(%s)', (list(run_ids),),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store_settings '
                'WHERE store_id = ANY(%s)', (list(store_ids),),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store '
                'WHERE id = ANY(%s)', (list(store_ids),),
            )
            cr.commit()
            checks = {
                'stores': (
                    'SELECT count(*) FROM shopify_connector_store '
                    'WHERE id = ANY(%s)', (list(store_ids),),
                ),
                'runs': (
                    'SELECT count(*) FROM shopify_connector_run '
                    'WHERE id = ANY(%s)', (list(run_ids),),
                ),
                'jobs': (
                    'SELECT count(*) FROM shopify_connector_job '
                    'WHERE id = ANY(%s)', (list(job_ids),),
                ),
                'attempts': (
                    'SELECT count(*) FROM shopify_connector_job_attempt '
                    'WHERE job_id = ANY(%s)', (list(job_ids),),
                ),
            }
            residue = {}
            for label, (statement, params) in checks.items():
                cr.execute(statement, params)
                residue[label] = cr.fetchone()[0]
            self.assertFalse(
                any(residue.values()),
                'P10 fixture cleanup left connector residue: %s' % residue,
            )
        finally:
            cr.rollback()
            cr.close()

        if created_company_ids:
            # Company creation is an ORM operation with base-model side
            # effects (at least res.partner, and potentially version-specific
            # calendar/property defaults).  Unlink it in a fresh committed ORM
            # transaction so those dependencies use Odoo's own ondelete
            # handling; then explicitly unlink any captured partner that the
            # company unlink did not cascade.
            company_cr = self._open_bounded()
            try:
                cleanup_env = api.Environment(company_cr, SUPERUSER_ID, {})
                companies = cleanup_env['res.company'].sudo().browse(
                    list(created_company_ids),
                ).exists()
                partners = cleanup_env['res.partner'].sudo().browse(
                    list(created_partner_ids),
                ).exists()
                companies.unlink()
                partners.exists().unlink()
                cleanup_env.flush_all()
                company_cr.commit()
                company_cr.execute(
                    'SELECT count(*) FROM res_company WHERE id = ANY(%s)',
                    (list(created_company_ids),),
                )
                remaining_companies = company_cr.fetchone()[0]
                company_cr.execute(
                    'SELECT count(*) FROM res_partner WHERE id = ANY(%s)',
                    (list(created_partner_ids),),
                )
                remaining_partners = company_cr.fetchone()[0]
                self.assertEqual(
                    (remaining_companies, remaining_partners), (0, 0),
                    'P10 company cleanup left base-model residue',
                )
            except BaseException:
                company_cr.rollback()
                raise
            finally:
                company_cr.close()

class V2RuntimeObservationMixin:
    """Claim/observation helpers for P10 test assertions."""

    def _claim_fixture(self, fixture, *, store_index=0, limit=None):
        """Claim fixture jobs once through the production repository."""
        store_info = fixture['stores'][store_index]
        cr, env = self._new_env(
            allowed_company_ids=(store_info['company_id'],),
        )
        try:
            with self._real_registry_cursor():
                claims = OdooReadOnlyRuntimeRepository(env).claim_due(
                    now=NOW,
                    worker_ref='p10-fixture-claim-%s' % uuid.uuid4(),
                    limit=limit or len(store_info.get('job_ids', ())) or 1,
                    phase=CLAIM_TRANSACTION,
                    handler_keys=('core_dispatch_selftest',),
                )
                return tuple(claims)
        finally:
            cr.rollback()
            cr.close()

    def _observe(self, statement, params=()):
        """Read one committed fact through a fresh independent cursor."""
        cr = self._open_bounded()
        try:
            cr.execute(statement, params)
            return cr.fetchall()
        finally:
            cr.rollback()
            cr.close()


class V2RuntimeConcurrencyMixin(
    V2RuntimeConnectionMixin,
    V2RuntimeFixtureMixin,
    V2RuntimeObservationMixin,
):
    """Combined helper surface used by the Odoo TransactionCase classes."""
