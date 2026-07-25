import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
    canonical_sha256,
)


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestMutationApiGuard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 API guard test',
            'shop_domain': 'layer2-api-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        token = uuid.uuid4().hex
        cls.job = cls.env['shopify.connector.job'].sudo().create({
            'store_id': cls.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                cls.store.connection_generation,
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
            'owner_worker_ref': 'test:1',
            'running_since': fields.Datetime.now(),
        })
        cls.operation = 'mutation DoThing { shop { id } }'
        cls.variables = {'synthetic': True}
        cls.attempt = cls.env[
            'shopify.connector.mutation.attempt'
        ].with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': cls.job.id,
            'attempt_token': token,
            'mutation_domain': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                cls.store.connection_generation,
            'expected_store_identity': cls.store.shop_domain,
            'shopify_idempotency_key': uuid.uuid4().hex,
            'exact_request_fingerprint': canonical_sha256({
                'operation': cls.operation,
                'variables': cls.variables,
            }),
        })
        cls.context = {
            'job_id': cls.job.id,
            'attempt_id': cls.attempt.id,
            'attempt_token': token,
            'mutation_domain': 'mutation_dispatch_selftest',
        }
        cls.Client = cls.env['shopify.connector.api.client']

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    def test_query_and_false_positive_text_are_unaffected(self):
        self.assertTrue(self.Client._validate_graphql_operation(
            'query { shop { id } }', {},
        ))
        self.assertFalse(self.Client._graphql_contains_mutation(
            'query { shop { name(arg: "mutation { fake }") } } '
            '# mutation { comment }'
        ))

    def test_mutation_without_context_fails_closed(self):
        with self.assertRaises(UserError):
            self.Client._validate_graphql_operation(
                self.operation, self.variables,
            )

    def test_valid_exact_attempt_context_is_accepted(self):
        self.assertTrue(self.Client._validate_graphql_operation(
            self.operation, self.variables, self.context,
        ))

    def test_execute_business_accepts_only_the_valid_mutation_context(self):
        ClientClass = type(self.Client)
        with patch.object(
            ClientClass, '_admit_mutation',
            return_value=('synthetic-lease', 'synthetic-token', self.store),
        ) as admit, patch.object(
            ClientClass, '_send', return_value=object(),
        ) as transport, patch.object(
            ClientClass, '_normalize_response',
            return_value={'data': {'synthetic': True}},
        ), patch.object(
            ClientClass, '_release_lease',
        ) as release:
            with self.Client.execute_business(
                self.job,
                self.store,
                self.operation,
                self.variables,
                mutation_context=self.context,
            ) as result:
                self.assertEqual(result, {'data': {'synthetic': True}})
        admit.assert_called_once_with(
            self.job.id, self.store.id, self.context,
        )
        transport.assert_called_once()
        self.assertEqual(
            transport.call_args.kwargs['mutation_context'], self.context,
        )
        release.assert_called_once_with('synthetic-lease')

    def test_operation_and_variable_mismatch_are_refused_exactly(self):
        for operation, variables in (
            ('mutation  DoThing { shop { id } }', self.variables),
            (self.operation, {'synthetic': False}),
        ):
            with self.assertRaises(UserError):
                self.Client._validate_graphql_operation(
                    operation, variables, self.context,
                )

    def test_expired_and_nonrunning_contexts_are_refused(self):
        self.env.cr.execute(
            'UPDATE shopify_connector_mutation_attempt '
            'SET idempotency_valid_until = %s WHERE id = %s',
            (fields.Datetime.now(), self.attempt.id),
        )
        self.attempt.invalidate_recordset()
        with self.assertRaises(UserError):
            self.Client._validate_graphql_operation(
                self.operation, self.variables, self.context,
            )
        self.env.cr.execute(
            'UPDATE shopify_connector_mutation_attempt '
            'SET idempotency_valid_until = %s WHERE id = %s',
            (fields.Datetime.now() + timedelta(hours=1), self.attempt.id),
        )
        self.attempt.invalidate_recordset()
        self.job.sudo().write({'state': 'failed_final'})
        with self.assertRaises(UserError):
            self.Client._validate_graphql_operation(
                self.operation, self.variables, self.context,
            )

    def test_nonpending_attempt_context_is_refused(self):
        self.attempt._record_direct_outcome('uncertain')
        with self.assertRaises(UserError):
            self.Client._validate_graphql_operation(
                self.operation, self.variables, self.context,
            )

    def test_token_or_domain_mismatch_is_refused(self):
        for key, value in (
            ('attempt_token', 'wrong'),
            ('mutation_domain', 'real_inventory_forbidden'),
        ):
            context = dict(self.context)
            context[key] = value
            with self.assertRaises(UserError):
                self.Client._validate_graphql_operation(
                    self.operation, self.variables, context,
                )
