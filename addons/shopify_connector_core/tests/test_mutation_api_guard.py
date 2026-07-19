import uuid
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
    canonical_sha256,
)


class TestMutationApiGuard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 API guard test',
            'shop_domain': 'layer2-api-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
        })
        token = uuid.uuid4().hex
        cls.job = cls.env['shopify.connector.job'].sudo().create({
            'store_id': cls.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
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
