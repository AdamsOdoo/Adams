"""SEC-3 scope/company isolation and the permission boundary for U3."""

import json
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user, tagged

from ..models.shopify_connector_product_export_seams import (
    FORBIDDEN_SCOPES,
    REQUIRED_EXPORT_SCOPES,
    REQUIRED_MEDIA_SCOPES,
)
from .common import DUMMY_TOKEN, ExportCase, SHOP_DOMAIN


@tagged('post_install', '-at_install')
class TestExportSec3AndPermissions(ExportCase):

    # ------------------------------------------------------------------
    # SEC-3: company is inherited from the store, never chosen
    # ------------------------------------------------------------------

    def test_preview_company_follows_its_store(self):
        binding = self.bind_template(variant_gid=None)
        preview = self.make_preview(binding=binding)
        self.assertEqual(preview.company_id, self.store.company_id)

    def test_media_binding_company_follows_its_store(self):
        binding = self.bind_template(variant_gid=None)
        row = self.MediaBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_binding_id': binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': 'c' * 64,
            'connector_filename': 'odoo-1-cccccccc.png',
            'shopify_gid': 'gid://shopify/MediaImage/1',
        })
        self.assertEqual(row.company_id, self.store.company_id)

    def test_a_cross_store_media_parent_is_refused(self):
        """One company may own several stores, so a company check cannot see a
        cross-STORE link. The SEC-3 constraint can."""
        other_store = self.Store.sudo().create({
            'name': 'Other Store',
            'shop_domain': 'other-' + SHOP_DOMAIN,
            'api_version': self.store.api_version,
        })
        binding = self.bind_template(variant_gid=None)
        with self.assertRaises(ValidationError):
            self.MediaBinding.sudo().create({
                'store_id': other_store.id,
                'product_template_binding_id': binding.id,
                'media_role': 'primary',
                'odoo_image_checksum': 'd' * 64,
                'connector_filename': 'odoo-1-dddddddd.png',
                'shopify_gid': 'gid://shopify/MediaImage/2',
            })

    def test_a_cross_store_preview_parent_is_refused(self):
        other_store = self.Store.sudo().create({
            'name': 'Other Store 2',
            'shop_domain': 'other2-' + SHOP_DOMAIN,
            'api_version': self.store.api_version,
        })
        binding = self.bind_template(variant_gid=None)
        with self.assertRaises(ValidationError):
            self.Preview._preview_surface('_create_preview').create({
                'store_id': other_store.id,
                'product_template_id': self.template.id,
                'product_template_binding_id': binding.id,
                'export_path': 'update',
                'state': 'previewed',
                'diff': {},
                'apply_plan': {'steps': []},
                'blocked_differences': {'items': []},
                'previewed_at': fields.Datetime.now(),
                'expires_at': fields.Datetime.add(fields.Datetime.now(), hours=1),
            })

    def test_the_scope_quarantine_flag_is_not_caller_writable(self):
        binding = self.bind_template(variant_gid=None)
        row = self.MediaBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_binding_id': binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': 'e' * 64,
            'connector_filename': 'odoo-1-eeeeeeee.png',
            'shopify_gid': 'gid://shopify/MediaImage/3',
        })
        admin = new_test_user(
            self.env, login='export-admin',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_admin',
        )
        with self.assertRaises(AccessError):
            row.with_user(admin).write({'sec3_scope_quarantined': True})

    # ------------------------------------------------------------------
    # Least-privilege scopes
    # ------------------------------------------------------------------

    def test_write_themes_is_never_required_and_is_a_finding(self):
        self.assertIn('write_themes', FORBIDDEN_SCOPES)
        self.assertNotIn('write_themes', REQUIRED_EXPORT_SCOPES)
        self.assertNotIn('write_themes', REQUIRED_MEDIA_SCOPES)
        Check = self.env['shopify.connector.readiness.check']
        self.store.sudo().write({
            'granted_scopes': '["write_products", "write_files", '
                              '"write_themes"]',
        })
        result = Check._check_product_export_scopes(self.store)
        self.assertEqual(result['result'], Check.RESULT_FAIL)
        self.assertIn('write_themes', result['reason'])

    def test_export_requires_write_products(self):
        Check = self.env['shopify.connector.readiness.check']
        self.store.sudo().write({'granted_scopes': '["read_products"]'})
        result = Check._check_product_export_scopes(self.store)
        self.assertEqual(result['result'], Check.RESULT_FAIL)
        self.assertIn('write_products', result['reason'])

    def test_media_export_requires_write_files_not_write_images(self):
        """`fileUpdate` — the only READY-gated association mutation in 2026-07
        — accepts `write_files` or `write_themes` and NOT `write_images`."""
        Check = self.env['shopify.connector.readiness.check']
        self.settings.sudo().write({'media_source_of_truth': 'odoo'})
        self.store.sudo().write(
            {'granted_scopes': '["write_products", "write_images"]'}
        )
        result = Check._check_product_export_scopes(self.store)
        self.assertEqual(result['result'], Check.RESULT_FAIL)
        self.assertIn('write_files', result['reason'])
        self.store.sudo().write(
            {'granted_scopes': '["write_products", "write_files"]'}
        )
        result = Check._check_product_export_scopes(self.store)
        self.assertEqual(result['result'], Check.RESULT_PASS)

    def test_the_check_is_not_applicable_while_export_is_disabled(self):
        Check = self.env['shopify.connector.readiness.check']
        self.settings.sudo().write({'product_export_domain_enabled': False})
        self.store.sudo().write({'granted_scopes': '[]'})
        result = Check._check_product_export_scopes(self.store)
        self.assertEqual(result['result'], Check.RESULT_PASS)
        self.assertIn('Not applicable', result['reason'])

    # ------------------------------------------------------------------
    # Correction B (independent review, Defect #3): the domain-flag
    # extension seam, and a genuine Product-Export-only activation.
    # ------------------------------------------------------------------

    def test_product_export_domain_flag_is_registered_through_the_seam(self):
        """Not hand-added to a fixed core tuple: registered the same way
        `_get_checks` already registers `_check_product_export_scopes`."""
        Check = self.env['shopify.connector.readiness.check']
        self.assertIn(
            'product_export_domain_enabled', Check._accepted_domain_flags(),
        )

    def test_a_catalog_export_only_configuration_is_recognized_as_enabled(
        self,
    ):
        """The accuracy half of Defect #3, isolated from every other
        essential check: a store enabling ONLY Catalog export must be
        reported as having a sync domain enabled, not "No sync domain is
        enabled" -- the four core flags stay False throughout."""
        Check = self.env['shopify.connector.readiness.check']
        self.settings.sudo().write({
            'product_export_domain_enabled': True,
            'product_domain_enabled': False,
            'sale_domain_enabled': False,
            'inventory_domain_enabled': False,
            'fulfillment_domain_enabled': False,
        })
        result = Check._check_domain_flag_enablement(self.store)
        self.assertEqual(result['result'], Check.RESULT_PASS)

    def test_the_setup_wizard_scope_catalog_names_write_products(self):
        """Defect #3's companion accuracy gap: step 4's display list must
        not stay silent about a scope this installed module will need."""
        Check = self.env['shopify.connector.readiness.check']
        catalog = Check._governed_scope_catalog()
        self.assertIn(
            'write_products', {entry['scope'] for entry in catalog},
        )
        # `write_files` is conditional on a Store Settings choice S1 never
        # makes, so it must NOT be named unconditionally at step 4.
        self.assertNotIn(
            'write_files', {entry['scope'] for entry in catalog},
        )

    def test_a_product_export_only_store_can_activate_through_the_setup_wizard(
        self,
    ):
        """Defect #3, end to end, through the real production route:
        `shopify.connector.setup.wizard.activate()`. Every OTHER essential
        readiness check is satisfied directly (this test's subject is the
        domain-flag recognition, not the credential/scope/cron plumbing
        already covered by core's own setup-wizard suite), and the
        transport is a stand-in that fails the test if reached at all.  With
        W1 installed the first activation is intentionally a durable webhook
        reconciliation hand-off, not setup completion; the fixture proves
        that state before installing stored read-back evidence.
        """
        Check = self.env['shopify.connector.readiness.check']
        admin = new_test_user(
            self.env, login='export-activate-admin',
            groups=(
                'base.group_user,'
                'shopify_connector_core.group_shopify_connector_admin'
            ),
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'https://export-activate-test.example.test',
        )
        # W1 makes webhook proof fail closed once a store is connected.  This
        # test is specifically the pre-activation Product-Export-only setup
        # contract, so when the optional webhook addon is installed use a
        # fresh setup-incomplete store (the model's default lifecycle state)
        # rather than making a connected fixture look webhook-ready.  The
        # setup wizard then evaluates webhook_hmac as truthful Not required;
        # no readiness result or webhook evidence is force-written.
        webhook_installed = (
            'shopify.connector.webhook.registry' in self.env.registry.models
        )
        activation_store = self.store
        activation_settings = self.settings
        if webhook_installed:
            activation_store = self.Store.sudo().create({
                'name': 'Export Activation Only Store',
                'shop_domain': 'export-activate-only-%s.myshopify.com'
                % self.store.id,
            })
            self.env[
                'shopify.connector.store.credential'
            ].sudo()._credential_surface('_mutate_token').create({
                'store_id': activation_store.id,
                'access_token': DUMMY_TOKEN,
                # W1 webhook readiness needs an app client secret even for
                # this product-export-only journey.  Seed the same truthful
                # non-secret test evidence before activation so the first
                # stage can enqueue reconciliation and the second stage can
                # prove completion; an offline token alone is intentionally
                # gated by the installed webhook addon.
                'client_secret': 'export-activation-client-secret',
                'credential_state': 'present',
                'credential_epoch': 1,
            })
            activation_settings = self.env[
                'shopify.connector.store.settings'
            ].sudo().create({
                'store_id': activation_store.id,
                'product_export_domain_enabled': True,
                'price_source_of_truth': 'odoo_authoritative',
            })
        activation_store.sudo().write({
            # `ExportCase` creates the credential ROW directly (bypassing
            # `action_set_token`), so `credential_present` -- a plain
            # stored flag that service normally sets as a side effect --
            # stays at its default False unless set explicitly here.
            'credential_present': True,
            # The separate setup-incomplete fixture must also carry the
            # service's non-secret verification mirror: action_activate is
            # allowed to consume only current stored evidence.
            'credential_last_verified_at': fields.Datetime.now(),
            'last_test_connection_result': 'pass',
            'api_health_state': 'normal',
            'granted_scopes': json.dumps(sorted(
                set(Check.REQUIRED_MVP_SCOPES) | {'write_products'}
            )),
        })
        # The capability-aware fixture above already owns these values for a
        # new setup store; writing them again is harmless and keeps the
        # core-only path identical to the historical ExportCase fixture.
        activation_settings.sudo().write({
            'product_export_domain_enabled': True,
            'product_domain_enabled': False,
            'sale_domain_enabled': False,
            'inventory_domain_enabled': False,
            'fulfillment_domain_enabled': False,
        })
        if webhook_installed:
            self.assertEqual(activation_store.state, 'setup_incomplete')
            webhook_check = Check._check_webhook_hmac(activation_store)
            self.assertEqual(webhook_check['result'], Check.RESULT_PASS)
            self.assertTrue(webhook_check['not_applicable'])
            self.assertIn('Bootstrap / reconcile webhooks', webhook_check['reason'])
        Setup = self.env['shopify.connector.setup.wizard']
        setup_jobs = self.env['shopify.connector.job'].sudo()
        jobs_before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', activation_store.id),
            ('state', 'in', ('queued', 'running')),
        ])
        Client = type(self.env['shopify.connector.api.client'])

        def refuse(_self, _store, request, token=None, mutation_context=None):
            raise AssertionError(
                'product-export-only activation contacted Shopify'
            )

        with patch.object(Client, '_send', refuse):
            Setup.with_user(admin).activate(activation_store.id)
        activation_store.invalidate_recordset()
        activation_settings.invalidate_recordset()
        self.assertEqual(activation_store.last_readiness_result, 'pass')
        self.assertTrue(activation_settings.product_export_domain_enabled)
        self.assertFalse(activation_settings.product_domain_enabled)
        self.assertFalse(activation_settings.sale_domain_enabled)
        self.assertFalse(activation_settings.inventory_domain_enabled)
        self.assertFalse(activation_settings.fulfillment_domain_enabled)
        if webhook_installed:
            # The first activation only changes the lifecycle state and
            # admits one durable webhook reconciliation.  It must not write
            # setup_completed_at or redirect the operator as though proof
            # existed.  This is deliberately asserted through the production
            # setup service, not by forcing a store state in the fixture.
            self.assertEqual(activation_store.state, 'connected')
            self.assertFalse(activation_settings.setup_completed_at)
            pending_state = Setup.with_user(admin).get_setup_state(
                store_id=activation_store.id,
            )['store']
            self.assertEqual(pending_state['setup_completion_state'], 'pending')
            self.assertIn('read-back', pending_state['setup_completion_message'])
            initial_reconcile_jobs = setup_jobs.search([
                ('store_id', '=', activation_store.id),
                ('job_type', '=', 'webhook_subscription_reconcile'),
                ('job_source', '=', 'setup_readiness_check'),
            ])
            self.assertEqual(len(initial_reconcile_jobs), 1)

            # Exercise the real parent -> Layer-2 child progression without a
            # network call.  A terminal child failure is surfaced first, then
            # a sanctioned retry creates a new lineage; its create result is
            # pending until the final Shopify read-back evidence makes setup
            # completable, and the parent is never duplicated.
            from odoo.addons.shopify_connector_core.tools.api_version import (
                SHOPIFY_API_VERSION,
            )
            Credential = self.env['shopify.connector.store.credential']
            credential = Credential.sudo().search([
                ('store_id', '=', activation_store.id),
            ], limit=1)
            Credential.sudo()._credential_surface('_mutate_token').browse(
                credential.id,
            ).write({'client_secret': 'export-activation-client-secret'})
            Secret = self.env['shopify.connector.webhook.secret']
            Subscription = self.env['shopify.connector.webhook.subscription']
            Secret._ensure_for_store(activation_store)
            expected = Subscription._ensure_expected_for_store(activation_store)
            failed_child_job = Subscription._enqueue_subscription_mutation(
                expected[0], 'create', 'setup_readiness_check',
            )
            initial_reconcile_jobs.sudo().write({
                'state': 'running',
                'started_at': fields.Datetime.now(),
            })
            initial_reconcile_jobs.sudo().write({
                'state': 'succeeded',
                'finished_at': fields.Datetime.now(),
            })
            failed_child_job.sudo().write({
                'state': 'failed_final',
                'finished_at': fields.Datetime.now(),
            })
            Subscription._apply_subscription_consequence(
                failed_child_job, False, 'bootstrap', {
                    'action': 'fail_final',
                    'message': 'Controlled validation failure before retry.',
                },
            )
            failed_state = Setup.with_user(admin).get_setup_state(
                store_id=activation_store.id,
            )['store']
            self.assertEqual(
                failed_state['setup_completion_state'], 'action_required',
            )
            self.assertEqual(
                failed_state['setup_completion_code'], 'child_failed_final',
            )
            # The sanctioned subscription service creates a new bounded
            # lineage after the terminal failure.  The old row remains audit
            # evidence, but must not poison the retry or its later proof.
            retry_child_job = Subscription._enqueue_subscription_mutation(
                expected[0], 'create', 'setup_readiness_check',
            )
            self.assertNotEqual(retry_child_job.id, failed_child_job.id)
            self.assertEqual(failed_child_job.state, 'failed_final')
            self.assertEqual(expected[0].last_job_id, retry_child_job)
            pending_state = Setup.with_user(admin).get_setup_state(
                store_id=activation_store.id,
            )['store']
            self.assertEqual(
                pending_state['setup_completion_state'], 'pending',
            )
            self.assertEqual(
                pending_state['setup_completion_code'], 'child_work_pending',
            )
            self.assertIn('read-back', pending_state['setup_completion_message'])
            self.assertEqual(
                setup_jobs.search_count([
                    ('store_id', '=', activation_store.id),
                    ('job_type', '=', 'webhook_subscription_reconcile'),
                    ('job_source', '=', 'setup_readiness_check'),
                ]), 1,
            )
            retry_child_job.sudo().write({
                'state': 'running',
                'started_at': fields.Datetime.now(),
            })
            callback_digest = Secret._callback_url_digest_for_store(
                activation_store,
            )
            Subscription._apply_subscription_consequence(
                retry_child_job, False, 'bootstrap', {
                    'action': 'succeed',
                    'domain_payload': {
                        'shopify_subscription_gid': (
                            'gid://shopify/WebhookSubscription/export-%d'
                            % expected[0].id
                        ),
                        'actual_topic': expected[0].topic_enum,
                        'actual_uri_digest': callback_digest,
                        'actual_api_version': SHOPIFY_API_VERSION,
                        'actual_format': 'JSON',
                    },
                },
            )
            retry_child_job.sudo().write({
                'state': 'succeeded',
                'finished_at': fields.Datetime.now(),
            })
            pending_verification_state = Setup.with_user(admin).get_setup_state(
                store_id=activation_store.id,
            )['store']
            self.assertEqual(
                pending_verification_state['setup_completion_state'], 'pending',
            )
            self.assertEqual(
                pending_verification_state['setup_completion_code'],
                'child_work_pending',
            )
            # The dispatcher's reconciliation consequence is the local
            # representation of a verified Shopify read-back.  It advances
            # only the retried lineage to active; the remaining expected
            # rows receive the same stored proof below.
            Subscription._apply_subscription_consequence(
                retry_child_job, False, 'reconciliation', {
                    'action': 'succeed',
                    'domain_payload': {
                        'shopify_subscription_gid': (
                            'gid://shopify/WebhookSubscription/export-%d'
                            % expected[0].id
                        ),
                        'actual_topic': expected[0].topic_enum,
                        'actual_uri_digest': callback_digest,
                        'actual_api_version': SHOPIFY_API_VERSION,
                        'actual_format': 'JSON',
                    },
                },
            )
            retry_child_job.sudo().write({
                'state': 'succeeded',
                'finished_at': fields.Datetime.now(),
            })
            expected[0].invalidate_recordset()
            callback_digest = Secret._callback_url_digest_for_store(
                activation_store,
            )
            epoch = Subscription._credential_epoch(activation_store)
            self.assertEqual(
                expected[0].hmac_credential_epoch,
                epoch,
                'reconciliation consequence must persist its fenced epoch',
            )
            for subscription in expected[1:]:
                subscription._service_write({
                    'state': 'active',
                    'shopify_subscription_gid': (
                        'gid://shopify/WebhookSubscription/export-%d'
                        % subscription.id
                    ),
                    'actual_topic': subscription.topic_enum,
                    'actual_uri_digest': callback_digest,
                    'actual_api_version': SHOPIFY_API_VERSION,
                    'actual_format': 'JSON',
                    'last_reconciled_at': fields.Datetime.now(),
                    'hmac_credential_epoch': epoch,
                    'last_error': False,
                })
            # The fixture has now installed the worker's durable Shopify
            # read-back proof through the subscription service; no state is
            # force-written to hide an unfinished child.
            post_activation_webhook = Check._check_webhook_hmac(
                activation_store,
            )
            self.assertEqual(
                post_activation_webhook['result'], Check.RESULT_PASS,
            )
            with patch.object(Client, '_send', refuse):
                Setup.with_user(admin).activate(activation_store.id)
            activation_store.invalidate_recordset()
            activation_settings.invalidate_recordset()
            self.assertTrue(activation_settings.setup_completed_at)
            self.assertEqual(
                Setup.with_user(admin).get_setup_state(
                    store_id=activation_store.id,
                )['store']['setup_completion_state'],
                'complete',
            )
            self.assertEqual(
                setup_jobs.search_count([
                    ('store_id', '=', activation_store.id),
                    ('job_type', '=', 'webhook_subscription_reconcile'),
                    ('job_source', '=', 'setup_readiness_check'),
                ]),
                1,
                'repeated activation must not admit a duplicate reconciliation',
            )
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', activation_store.id),
                ('state', 'in', ('queued', 'running')),
            ]),
            jobs_before,
            'activation must admit no export job (the W1 reconciliation is '
            'a separate setup-readiness hand-off)',
        )

    # ------------------------------------------------------------------
    # The domain flag gates every export job type
    # ------------------------------------------------------------------

    def test_every_export_job_type_maps_to_the_domain_flag(self):
        from ..models.shopify_connector_product_export_seams import (
            EXPORT_JOB_TYPES,
        )
        Job = self.env['shopify.connector.job']
        for job_type in EXPORT_JOB_TYPES:
            with self.subTest(job_type=job_type):
                self.assertEqual(
                    Job._domain_flag_for_job_type(job_type),
                    'product_export_domain_enabled',
                )

    def test_a_job_cannot_start_while_the_domain_flag_is_off(self):
        self.settings.sudo().write({'product_export_domain_enabled': False})
        job = self.make_job(
            'product_export_preview', 'product.template', self.template.id,
        )
        with self.assertRaises(ValidationError):
            job.sudo().write({'state': 'running'})

    # ------------------------------------------------------------------
    # Preview requests and confirmations are role-gated
    # ------------------------------------------------------------------

    def test_preview_request_requires_operator_or_admin(self):
        auditor = new_test_user(
            self.env, login='export-auditor',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_auditor',
        )
        with self.assertRaises(AccessError):
            self.Service.with_user(auditor).enqueue_preview(
                self.template, self.store,
            )

    def test_preview_request_refuses_a_product_not_enabled_for_export(self):
        self.template.write({'shopify_export_enabled': False})
        with self.assertRaises(UserError):
            self.Service.enqueue_preview(self.template, self.store)

    def test_preview_request_refuses_a_store_with_export_disabled(self):
        self.settings.sudo().write({'product_export_domain_enabled': False})
        with self.assertRaises(UserError):
            self.Service.enqueue_preview(self.template, self.store)

    def test_reconnect_expiry_requires_administrator(self):
        operator = new_test_user(
            self.env, login='export-operator-2',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_operator',
        )
        with self.assertRaises(AccessError):
            self.store.with_user(
                operator
            ).action_shopify_export_reconnect_reconciliation()

    def test_reconnect_expires_every_open_preview(self):
        binding = self.bind_template(variant_gid=None)
        preview = self.make_preview(binding=binding, steps=[{
            'step': 'product_export_update', 'state': 'pending',
            'fields': ['title'],
        }])
        admin = new_test_user(
            self.env, login='export-admin-3',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_admin',
        )
        expired = self.store.with_user(
            admin
        ).action_shopify_export_reconnect_reconciliation()
        preview.invalidate_recordset()
        self.assertEqual(expired, 1)
        self.assertEqual(preview.state, 'expired')
