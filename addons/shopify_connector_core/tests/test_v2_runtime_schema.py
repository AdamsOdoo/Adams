"""Focused P09 runtime-schema contracts.

The module is wired into normal connector test discovery together with its
ACLs, views and model registration.  It is tagged for post-install because the
shared Odoo business fixtures gain NOT NULL columns from modules outside the
core dependency closure during a warm install.
"""

import ast
import hashlib
import inspect
import json
import math
import re
import uuid

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_job_attempt import (
    ATTEMPT_CREATE_SURFACE,
    ATTEMPT_SERVICE_SENTINEL_CONTEXT,
    ATTEMPT_WRITE_CONTEXT,
    _bounded_json as _bounded_attempt_json,
    _non_negative_number,
    _safe_json as _safe_attempt_json,
    ShopifyConnectorJobAttempt,
)
from ..models.shopify_connector_job_runtime import JOB_LANE_SELECTION
from ..models.shopify_connector_store_settings_v2 import (
    V2_GATEWAY_MODE_SELECTION,
    V2_RUNTIME_MODE_SELECTION,
    V2_UI_MODE_SELECTION,
)
from ..models.shopify_connector_run import (
    RUN_CREATE_SURFACE,
    RUN_FINALIZE_NAME_SURFACE,
    RUN_SERVICE_SENTINEL_CONTEXT,
    RUN_TERMINAL_STATES,
    RUN_WRITE_CONTEXT,
    _bounded_json as _bounded_run_json,
    _safe_json as _safe_run_json,
    ShopifyConnectorRun,
)


@tagged('post_install', '-at_install')
class TestV2RuntimeSchema(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag = uuid.uuid4().hex
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].sudo().create({
            'name': 'V2 runtime schema company %s' % cls.tag,
        })
        cls.store_a = cls._store('a', cls.company_a)
        cls.store_b = cls._store('b', cls.company_b)
        cls.job_a = cls._job(cls.store_a)
        cls.Run = cls.env['shopify.connector.run']
        cls.Attempt = cls.env['shopify.connector.job.attempt']

    @classmethod
    def _store(cls, label, company):
        return cls.env['shopify.connector.store'].sudo().create({
            'name': 'V2 runtime schema store %s' % label,
            'shop_domain': 'v2-runtime-%s-%s.myshopify.com' % (
                label, cls.tag,
            ),
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': company.id,
        })

    @classmethod
    def _job(cls, store):
        return cls.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
            'expected_connection_generation': store.connection_generation,
        })

    def _run_values(self, store=None, request_key=None, trigger='system'):
        return {
            'store_id': (store or self.store_a).id,
            'request_key': request_key or str(uuid.uuid4()),
            'workflow': 'core',
            'operation': 'runtime.schema.read',
            'trigger': trigger,
            'scope_summary': 'Store diagnostics',
            'scope_fingerprint': hashlib.sha256(
                b'v2-runtime-schema'
            ).hexdigest(),
            'configuration_snapshot': {
                'page_size': 25,
                'mode': 'read_only',
            },
            'correlation_id': 'test:%s' % uuid.uuid4(),
        }

    def _run(self, **kwargs):
        values = self._run_values(**kwargs)
        return self.Run._create_service(values)

    def _attempt(self, job=None, run=None, **kwargs):
        values = {
            'job_id': (job or self.job_a).id,
            'worker_ref': 'worker:v2-schema-test',
            'claim_token': str(uuid.uuid4()),
            'observations': {'page': 1},
        }
        if run:
            values['run_id'] = run.id
        values.update(kwargs)
        return self.Attempt._create_service(values)

    def test_run_service_create_has_store_rooted_company_and_human_reference(self):
        run = self._run()
        self.assertTrue(re.match(r'^RUN-\d{8}-\d+$', run.name), run.name)
        self.assertEqual(run.store_id, self.store_a)
        self.assertEqual(run.company_id, self.store_a.company_id)
        self.assertEqual(run.state, 'requested')
        self.assertEqual(run.configuration_snapshot['page_size'], 25)
        self.assertTrue(run.request_key)
        self.assertTrue(run.correlation_id)

    def test_run_request_identity_is_unique_per_store(self):
        request_key = str(uuid.uuid4())
        self._run(request_key=request_key)
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._run(request_key=request_key)

    def test_run_direct_create_and_write_are_closed(self):
        values = self._run_values()
        with self.assertRaises(AccessError):
            self.Run.sudo().create(values)
        run = self._run()
        with self.assertRaises(AccessError):
            run.sudo().write({'result_summary': 'forged'})
        with self.assertRaises(AccessError):
            run.sudo().with_context(**{
                RUN_WRITE_CONTEXT: RUN_CREATE_SURFACE,
                RUN_SERVICE_SENTINEL_CONTEXT: 'copied-string',
            }).write({'result_summary': 'forged'})

    def test_run_required_text_actor_and_fingerprint_guards(self):
        for field_name in (
            'request_key', 'correlation_id', 'operation', 'scope_summary',
        ):
            values = self._run_values()
            values[field_name] = '   '
            with self.assertRaises(ValidationError):
                with self.env.cr.savepoint():
                    self.Run._create_service(values)
        values = self._run_values(trigger='user')
        values['actor_uid'] = self.env.ref('base.user_admin').id + 1
        with self.assertRaises(AccessError):
            with self.env.cr.savepoint():
                self.Run._create_service(values)
        values = self._run_values()
        values['scope_fingerprint'] = 'not-a-digest'
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Run._create_service(values)

    def test_run_creation_surface_cannot_rewrite_name_or_other_fields(self):
        run = self._run()
        with self.assertRaises(AccessError):
            run._surface(RUN_CREATE_SURFACE).write({
                'result_summary': 'forged',
            })
        with self.assertRaises(ValidationError):
            run._surface(RUN_FINALIZE_NAME_SURFACE).write({
                'name': 'RUN-20260830-999999',
            })

    def test_run_lifecycle_and_terminal_immutability(self):
        run = self._run()
        run._admit_service()
        run._transition_service('running')
        run._finish_service('succeeded', 'Read-only run completed.')
        self.assertIn(run.state, RUN_TERMINAL_STATES)
        self.assertTrue(run.finished_at)
        with self.assertRaises(ValidationError):
            run._finish_service('succeeded', 'second finish')
        with self.assertRaises(ValidationError):
            run._surface('_finish_run').write({
                'result_summary': 'post-terminal mutation',
            })

    def test_attempt_service_create_links_job_run_and_company(self):
        run = self._run()
        attempt = self._attempt(run=run)
        self.assertEqual(attempt.job_id, self.job_a)
        self.assertEqual(attempt.run_id, run)
        self.assertEqual(attempt.store_id, self.store_a)
        self.assertEqual(attempt.company_id, self.store_a.company_id)
        self.assertEqual(attempt.attempt_no, 1)
        self.assertEqual(attempt.outcome, 'claimed')
        self.assertTrue(attempt.claimed_at)

    def test_attempt_cross_store_and_company_link_is_rejected(self):
        run_b = self._run(store=self.store_b)
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self._attempt(run=run_b)

    def test_attempt_direct_create_write_and_forged_context_are_closed(self):
        run = self._run()
        with self.assertRaises(AccessError):
            self.Attempt.sudo().create({
                'job_id': self.job_a.id,
                'worker_ref': 'forged',
                'claim_token': str(uuid.uuid4()),
            })
        attempt = self._attempt(run=run)
        with self.assertRaises(AccessError):
            attempt.sudo().write({'safe_message': 'forged'})
        with self.assertRaises(AccessError):
            attempt.sudo().with_context(**{
                ATTEMPT_WRITE_CONTEXT: ATTEMPT_CREATE_SURFACE,
                ATTEMPT_SERVICE_SENTINEL_CONTEXT: 'copied-string',
            }).write({'safe_message': 'forged'})

    def test_attempt_claim_create_rejects_lifecycle_and_terminal_values(self):
        forbidden_values = {
            'outcome': 'running',
            'started_at': fields.Datetime.now(),
            'heartbeat_at': fields.Datetime.now(),
            'finished_at': fields.Datetime.now(),
            'retry_decision': 'retry',
            'actual_cost': 1,
            'shopify_request_id': 'request-id',
            'request_digest': hashlib.sha256(b'request').hexdigest(),
        }
        for field_name, value in forbidden_values.items():
            with self.assertRaises(ValidationError, msg=field_name):
                with self.env.cr.savepoint():
                    self._attempt(**{field_name: value})

    def test_attempt_lifecycle_is_append_safe_and_terminal_is_immutable(self):
        attempt = self._attempt()
        attempt._start_service()
        attempt._heartbeat_service()
        attempt._finish_service(
            'succeeded',
            safe_message='Read-only attempt completed.',
            request_digest=hashlib.sha256(b'request').hexdigest(),
            response_digest=hashlib.sha256(b'response').hexdigest(),
        )
        self.assertTrue(attempt.finished_at)
        with self.assertRaises(ValidationError):
            attempt._heartbeat_service()
        with self.assertRaises(ValidationError):
            attempt._surface('_finish_attempt').write({
                'safe_message': 'post-terminal mutation',
            })
        # Retention is the only sanctioned terminal write surface and masks
        # bounded operator evidence without changing identity/outcome.
        attempt._mask_terminal_evidence()
        self.assertEqual(attempt.observations, {'masked': True})
        self.assertEqual(attempt.outcome, 'succeeded')

    def test_observations_are_redacted_bounded_and_costs_non_negative(self):
        attempt = self._attempt()
        secret = 'shpat_RUNTIME_SCHEMA_DO_NOT_PERSIST'
        attempt._observe_service(
            {
                'access_token': secret,
                'email': 'operator@example.invalid',
                'page': 2,
                'items': ['safe'] * 100,
            },
            requested_cost=3,
            actual_cost=2,
            budget_available=10,
            throttle_delay_ms=0,
        )
        encoded = json.dumps(attempt.observations)
        self.assertNotIn(secret, encoded)
        self.assertEqual(attempt.observations['access_token'], '***')
        self.assertEqual(attempt.observations['email'], '***')
        self.assertEqual(attempt.requested_cost, 3)
        self.assertEqual(attempt.actual_cost, 2)
        self.assertEqual(attempt.budget_available, 10)
        with self.assertRaises(ValidationError):
            attempt._observe_service({'page': 3}, requested_cost=-1)
        with self.assertRaises(ValidationError):
            attempt._observe_service({'page': 4}, throttle_delay_ms=True)
        with self.assertRaises(ValidationError):
            attempt._observe_service({'page': 5}, throttle_delay_ms=math.inf)
        # Long strings are bounded before persistence; they are never stored
        # as a raw response body or unbounded diagnostic payload.
        attempt._observe_service({'long': 'x' * 10000})
        self.assertLessEqual(
            len(json.dumps(attempt.observations).encode('utf-8')), 8192,
        )

    def test_attempt_number_is_positive_and_unique_per_job(self):
        first = self._attempt()
        second = self._attempt()
        self.assertEqual(first.attempt_no, 1)
        self.assertEqual(second.attempt_no, 2)
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._attempt(
                    attempt_no=1,
                    claim_token=str(uuid.uuid4()),
                )
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self._attempt(
                    attempt_no=0,
                    claim_token=str(uuid.uuid4()),
                )

    def test_runtime_models_do_not_define_credential_or_payload_fields(self):
        forbidden = {
            'access_token', 'password', 'secret', 'client_secret',
            'refresh_token', 'api_key', 'payload', 'variables', 'raw_body',
        }
        for model in (self.Run, self.Attempt):
            field_names = set(model._fields)
            self.assertFalse(forbidden.intersection(field_names), model._name)
        self.assertNotIn('mutation_attempt_id', self.Run._fields)
        self.assertIn('mutation_attempt_id', self.Attempt._fields)

    def test_job_runtime_expansion_is_nullable_and_uses_locked_lanes(self):
        self.assertEqual(
            [key for key, _label in JOB_LANE_SELECTION],
            [
                'safety_verification', 'interactive', 'webhook',
                'odoo_event', 'scheduled', 'reconciliation',
            ],
        )
        for field_name in (
            'run_id', 'parent_job_id', 'sequence', 'lane',
            'lane_priority', 'available_at', 'blocked_by_job_id',
        ):
            self.assertIn(field_name, self.job_a._fields)
        self.assertFalse(self.job_a.run_id)
        self.assertFalse(self.job_a.parent_job_id)
        self.assertFalse(self.job_a.lane)
        self.assertFalse(self.job_a.available_at)

    def test_job_runtime_relations_are_same_store_and_cycle_safe(self):
        run = self._run()
        child = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store_a.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
            'expected_connection_generation': (
                self.store_a.connection_generation
            ),
            'run_id': run.id,
            'parent_job_id': self.job_a.id,
            'sequence': 10,
            'lane': 'interactive',
            'lane_priority': 100,
            'available_at': fields.Datetime.now(),
        })
        self.assertEqual(child.run_id, run)
        self.assertEqual(child.parent_job_id, self.job_a)
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                child.sudo().write({'parent_job_id': child.id})

        foreign_job = self._job(self.store_b)
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                child.sudo().write({'blocked_by_job_id': foreign_job.id})

    def test_job_runtime_scheduling_values_reject_negative_numbers(self):
        for field_name in ('sequence', 'lane_priority'):
            with self.assertRaises(ValidationError, msg=field_name):
                with self.env.cr.savepoint():
                    self.job_a.sudo().write({field_name: -1})

    def test_job_runtime_identity_fields_are_closed_to_ordinary_rpc(self):
        run = self._run()
        admin = self.env.ref('base.user_admin')
        values = {
            'store_id': self.store_a.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
            'run_id': run.id,
            'lane': 'interactive',
        }
        with self.assertRaises(AccessError):
            with self.env.cr.savepoint():
                self.env['shopify.connector.job'].with_user(admin).create(values)
        with self.assertRaises(AccessError):
            with self.env.cr.savepoint():
                self.job_a.with_user(admin).write({'lane': 'interactive'})

    def test_v2_mode_controls_are_locked_audited_compare_and_set(self):
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().create({'store_id': self.store_a.id})
        self.assertEqual(settings.v2_ui_mode, 'legacy')
        self.assertEqual(settings.v2_gateway_mode, 'legacy')
        self.assertEqual(settings.v2_runtime_mode, 'legacy')
        self.assertEqual(settings.configuration_generation, 0)
        with self.assertRaises(AccessError):
            settings.sudo().write({'v2_ui_mode': 'pilot'})

        admin = self.env.ref('base.user_admin')
        settings = settings.with_user(admin).with_company(self.company_a)
        settings._set_v2_modes_service(
            {
                'v2_ui_mode': 'pilot',
                'v2_gateway_mode': 'compare_reads',
                'v2_runtime_mode': 'read_only',
            },
            reason='P09 isolated canary',
            expected_configuration_generation=0,
        )
        self.assertEqual(settings.configuration_generation, 1)
        self.assertEqual(settings.v2_ui_mode, 'pilot')
        with self.assertRaises(ValidationError):
            settings._set_v2_modes_service(
                {'v2_runtime_mode': 'subscriptions'},
                reason='stale request',
                expected_configuration_generation=0,
            )

    def test_v2_mode_vocabularies_are_exact(self):
        self.assertEqual(
            [key for key, _label in V2_UI_MODE_SELECTION],
            ['legacy', 'pilot', 'default'],
        )
        self.assertEqual(
            [key for key, _label in V2_GATEWAY_MODE_SELECTION],
            ['legacy', 'compare_reads', 'v2'],
        )
        self.assertEqual(
            [key for key, _label in V2_RUNTIME_MODE_SELECTION],
            [
                'legacy', 'read_only', 'subscriptions', 'inventory',
                'product_export', 'fulfillment', 'all',
            ],
        )

    def test_pure_metadata_guards_reject_bad_keys_numbers_and_collisions(self):
        with self.assertRaises(ValidationError):
            _safe_run_json({1: 'not a string key'})
        with self.assertRaises(ValidationError):
            _safe_attempt_json({'one': float('nan')})
        with self.assertRaises(ValidationError):
            _safe_attempt_json({
                'token@example.com': 1,
                'phone@example.com': 2,
            })
        with self.assertRaises(ValidationError):
            _non_negative_number(True, 'requested_cost')
        with self.assertRaises(ValidationError):
            _non_negative_number(math.inf, 'requested_cost')

    def test_runtime_json_boundaries_require_object_shapes(self):
        for value in ([], 'scalar', 1, False):
            with self.assertRaises(ValidationError, msg=repr(value)):
                _bounded_run_json(value, 'Configuration snapshot', 8192)
            with self.assertRaises(ValidationError, msg=repr(value)):
                _bounded_attempt_json(value)
        self.assertEqual(
            _bounded_run_json(
                {'mode': 'read_only'}, 'Configuration snapshot', 8192,
            ),
            {'mode': 'read_only'},
        )
        self.assertEqual(_bounded_attempt_json({'page': 1}), {'page': 1})

    def test_runtime_models_are_transport_free_and_do_not_create_mutation_evidence(self):
        for model_class in (ShopifyConnectorRun, ShopifyConnectorJobAttempt):
            tree = ast.parse(inspect.getsource(model_class))
            imported_modules = {
                alias.name.split('.')[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            self.assertNotIn('requests', imported_modules, model_class.__name__)
            self.assertNotIn('urllib', imported_modules, model_class.__name__)
        attempt_source = inspect.getsource(ShopifyConnectorJobAttempt)
        self.assertNotIn("shopify.connector.mutation.attempt'].create", attempt_source)
        self.assertNotIn('execute_business(', attempt_source)
        self.assertNotIn('_send(', attempt_source)
