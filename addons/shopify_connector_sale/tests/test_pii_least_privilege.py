import ast
import json
import os
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


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
class TestPiiLeastPrivilege(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({
            'name': 'SEC-1 other company',
        })
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'SEC-1 customer store',
            'shop_domain': 'sec1-customer.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Binding = cls.env['shopify.connector.customer.binding']
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.Retention = cls.env['shopify.connector.pii.retention']
        cls.roles = {
            label: cls._role_user(label, xmlid)
            for label, xmlid in (
                ('auditor', 'group_shopify_connector_auditor'),
                ('operator', 'group_shopify_connector_operator'),
                ('reviewer', 'group_shopify_connector_reviewer'),
                ('admin', 'group_shopify_connector_admin'),
            )
        }

    @classmethod
    def _role_user(cls, label, group_xmlid):
        groups = [
            cls.env.ref('base.group_user').id,
            cls.env.ref('shopify_connector_core.%s' % group_xmlid).id,
        ]
        return cls.env['res.users'].create({
            'name': 'SEC-1 sale %s' % label,
            'login': 'sec1_sale_%s' % label,
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [
                cls.company.id,
                cls.other_company.id,
            ])],
            'group_ids': [(6, 0, groups)],
        })

    def _partner(self, name, company=None):
        values = {'name': name}
        if company is not None:
            values['company_id'] = company.id if company else False
        return self.env['res.partner'].create(values)

    def _binding(
        self, partner, gid='gid://shopify/Customer/SEC1',
        store=None, create_date=False,
    ):
        values = {
            'store_id': (store or self.store).id,
            'shopify_gid': gid,
            'partner_id': partner.id,
            'match_key': 'email',
            'shopify_display_name': 'Jane Sensitive',
            'shopify_email_snapshot': 'jane.sensitive@example.com',
            'shopify_phone_snapshot': '+971501234567',
        }
        binding = self.Binding.sudo().create(values)
        if create_date:
            self._backdate(binding, create_date)
        return self.Binding.browse(binding.id)

    def _plant_historic_binding(self, partner, gid):
        """Plant a binding whose partner is in ANOTHER company, with SQL.

        SEC-3 (#197) makes this shape impossible to create through the ORM: a
        store belongs to one company, and Odoo's `_check_company` refuses to
        bind a foreign-company partner to it -- under `sudo()` too, because it
        is a constraint rather than an access rule.

        The row is planted directly so the override guard is still exercised
        against exactly the case it exists for: a HISTORIC binding, created
        before that invariant existed, that a reviewer must not be able to
        override. Deleting this test instead would silently drop the only
        coverage of that legacy path.
        """
        self.env.cr.execute(
            "INSERT INTO shopify_connector_customer_binding "
            "(store_id, company_id, shopify_gid, partner_id, status, "
            " match_key, create_uid, create_date, write_uid, write_date) "
            "VALUES (%s, %s, %s, %s, 'active', 'email', 1, now(), 1, now()) "
            "RETURNING id",
            (self.store.id, self.store.company_id.id, gid, partner.id),
        )
        binding_id = self.env.cr.fetchone()[0]
        self.Binding.invalidate_model()
        return self.Binding.browse(binding_id)

    def _backdate(self, record, create_date):
        """Back-date ``create_date`` in a phase-independent way.

        Passing ``create_date`` straight into ``create()`` only works while the
        registry is still loading: Odoo 19 discards every ``LOG_ACCESS_COLUMNS``
        entry from create values unless ``env.uid == SUPERUSER_ID and not
        self.pool.ready``
        (`odoo/orm/models.py` L4780-L4784, odoo/odoo@19.0
        30bde9ff758834a4912c5ae55843d3a7dad849f1). ``pool.ready`` is False during
        at_install and True afterwards, so the old fixture silently produced a
        *freshly created* binding once this class moved to post_install under the
        issue #193 test-phase contract -- and the retention sweep then correctly
        declined to mask a record inside its retention window.

        Writing the column directly keeps the fixture honest in either phase.
        """
        self.env.cr.execute(
            'UPDATE shopify_connector_customer_binding '
            'SET create_date = %s WHERE id = %s',
            (create_date, record.id),
        )
        record.invalidate_recordset(['create_date'])

    def _audit_jobs(self, store=None):
        return self.Job.search([
            ('store_id', '=', (store or self.store).id),
            ('job_type', '=', 'core_manual_maintenance'),
        ], order='id')

    def _assert_one_audit(self, jobs_before, actor):
        jobs = self._audit_jobs()
        self.assertEqual(len(jobs), len(jobs_before) + 1)
        job = jobs[-1]
        logs = self.JobLog.search([
            ('job_id', '=', job.id),
            ('event_type', '=', 'manual_action'),
        ])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.actor_uid, actor)
        return logs

    def test_raw_pii_snapshot_readable_by_every_connector_role(self):
        """SEC-2 packet section C: no masked surface, both roles read raw.

        The pre-SEC-2 behaviour restricted the snapshot fields to
        reviewer+admin at field level and offered everyone else a masked
        display. Both halves are gone: the fields carry no `groups=`, so
        every connector role reads the raw operational value, and there is no
        masked variant to read instead.
        """
        binding = self._binding(self._partner('PII visibility', self.company))
        raw_fields = [
            'shopify_display_name',
            'shopify_email_snapshot',
            'shopify_phone_snapshot',
        ]
        for label in self.roles:
            values = binding.with_user(self.roles[label]).read(raw_fields)[0]
            self.assertEqual(
                values['shopify_email_snapshot'],
                'jane.sensitive@example.com',
                'raw snapshot must be readable by %s' % label,
            )
            self.assertEqual(values['shopify_phone_snapshot'], '+971501234567')
            self.assertEqual(values['shopify_display_name'], 'Jane Sensitive')
        for field_name in raw_fields:
            self.assertFalse(
                self.Binding._fields[field_name].groups,
                'SEC-2 removes the field-level group restriction from %s'
                % field_name,
            )

    def test_masked_snapshot_field_is_gone(self):
        """SEC-2 section H item 5: the masked field and its compute are gone."""
        self.assertNotIn('pii_snapshot_masked', self.Binding._fields)
        self.assertFalse(
            hasattr(self.Binding, '_compute_pii_snapshot_masked'),
        )

    def test_outsider_without_connector_role_is_denied(self):
        """SEC-2 section H item 3: raw read needs a connector role."""
        outsider = self.env['res.users'].create({
            'name': 'SEC-2 outsider',
            'login': 'sec2_pii_outsider',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        binding = self._binding(
            self._partner('Outsider probe', self.company),
            gid='gid://shopify/Customer/OutsiderProbe',
        )
        with self.assertRaises(AccessError):
            binding.with_user(outsider).read(['shopify_email_snapshot'])

    def test_legacy_masked_rows_are_flagged_not_reconstructed(self):
        """SEC-2 section E: irreversibly masked rows are marked, never guessed."""
        clean = self._binding(
            self._partner('Snapshot intact', self.company),
            gid='gid://shopify/Customer/SnapshotIntact',
        )
        self.assertFalse(clean.pii_snapshot_refresh_required)

        legacy = self._binding(
            self._partner('Snapshot masked', self.company),
            gid='gid://shopify/Customer/SnapshotMasked',
        )
        # Exactly what the pre-SEC-2 sweep left behind.
        legacy.sudo().write({
            'shopify_display_name': '***',
            'shopify_email_snapshot': '***',
            'shopify_phone_snapshot': '***',
        })
        legacy.invalidate_recordset()
        self.assertTrue(legacy.pii_snapshot_refresh_required)
        # The flag reports the loss; it never invents a replacement value.
        self.assertEqual(legacy.shopify_email_snapshot, '***')

    def test_binding_identity_write_and_create_denied_for_all_roles(self):
        binding = self._binding(self._partner('Identity current', self.company))
        target = self._partner('Identity target', self.company)
        for label, user in self.roles.items():
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({
                    'shopify_gid': 'gid://shopify/Customer/Forged',
                })
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({'partner_id': target.id})
            with self.assertRaises(AccessError, msg=label):
                self.Binding.with_user(user).create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/Create/%s' % label,
                    'partner_id': target.id,
                    'match_key': 'manual',
                })
        self.assertEqual(binding.partner_id.name, 'Identity current')

    def test_override_same_company_one_redacted_audit_and_actor(self):
        current = self._partner('Same current', self.company)
        target = self._partner('Same target', self.company)
        binding = self._binding(current)
        reviewer = self.roles['reviewer']
        before = self._audit_jobs()
        reason = (
            'approved duplicate correction for private@example.com '
            'using shpat_DUMMYSECRET123'
        )
        binding.with_user(reviewer).action_override_binding(target.id, reason)
        binding.invalidate_recordset()
        self.assertEqual(binding.partner_id, target)
        self.assertEqual(binding.status, 'manually_overridden')
        self.assertEqual(binding.match_key, 'manual')
        self.assertEqual(binding.override_uid, reviewer)
        logs = self._assert_one_audit(before, reviewer)
        self.assertIn('old_record_id=%d' % current.id, logs.message)
        self.assertIn('new_record_id=%d' % target.id, logs.message)
        self.assertNotIn('private@example.com', logs.message)
        self.assertNotIn('shpat_DUMMYSECRET123', logs.message)
        self.assertIn('[redacted-email]', logs.message)
        self.assertIn('***', logs.message)

    def test_admin_override_writes_exact_provenance_and_one_audit(self):
        current = self._partner('Admin current', self.company)
        target = self._partner('Admin target', self.company)
        binding = self._binding(
            current,
            gid='gid://shopify/Customer/AdminOverride',
        )
        admin = self.roles['admin']
        before = self._audit_jobs()
        binding.with_user(admin).action_override_binding(
            target.id,
            'admin approved customer@example.com',
        )
        binding.invalidate_recordset()
        self.assertEqual(binding.partner_id, target)
        self.assertEqual(binding.status, 'manually_overridden')
        self.assertEqual(binding.match_key, 'manual')
        self.assertEqual(binding.override_uid, admin)
        self.assertTrue(binding.override_at)
        self.assertEqual(
            binding.override_previous_candidate,
            'res.partner,%d' % current.id,
        )
        logs = self._assert_one_audit(before, admin)
        self.assertNotIn('customer@example.com', logs.message)
        self.assertIn('[redacted-email]', logs.message)

    def test_override_company_neutral_records_succeed(self):
        current = self._partner('Neutral current', False)
        target = self._partner('Neutral target', False)
        binding = self._binding(current)
        before = self._audit_jobs()
        binding.with_user(self.roles['reviewer']).action_override_binding(
            target.id,
            'company-neutral correction',
        )
        binding.invalidate_recordset()
        self.assertEqual(binding.partner_id, target)
        self._assert_one_audit(before, self.roles['reviewer'])

    def test_target_company_mismatch_has_no_write_or_audit(self):
        current = self._partner('Target mismatch current', self.company)
        target = self._partner('Target mismatch target', self.other_company)
        binding = self._binding(current)
        before = self._audit_jobs()
        with self.assertRaises(UserError):
            binding.with_user(self.roles['reviewer']).action_override_binding(
                target.id,
                'must fail before sudo',
            )
        binding.invalidate_recordset()
        self.assertEqual(binding.partner_id, current)
        self.assertEqual(self._audit_jobs(), before)

    def test_current_company_mismatch_has_no_write_or_audit(self):
        current = self._partner('Current mismatch current', self.other_company)
        target = self._partner('Current mismatch target', self.company)
        binding = self._plant_historic_binding(
            current, 'gid://shopify/Customer/HistoricMismatch')
        before = self._audit_jobs()
        with self.assertRaises(UserError):
            binding.with_user(self.roles['reviewer']).action_override_binding(
                target.id,
                'must fail before sudo',
            )
        binding.invalidate_recordset()
        self.assertEqual(binding.partner_id, current)
        self.assertEqual(self._audit_jobs(), before)

    def test_override_negative_rpc_matrix_no_write_or_audit(self):
        current = self._partner('Negative current', self.company)
        target = self._partner('Negative target', self.company)
        binding = self._binding(current)
        collision = self._binding(
            target,
            gid='gid://shopify/Customer/Collision',
        )
        self.assertTrue(collision)
        before = self._audit_jobs()
        for user, record_id, reason, error in (
            (self.roles['operator'], target.id, 'denied', AccessError),
            (self.roles['reviewer'], False, 'bad id', UserError),
            (self.roles['reviewer'], -1, 'bad id', UserError),
            (self.roles['reviewer'], '1', 'bad id', UserError),
            (self.roles['reviewer'], 999999999, 'missing', UserError),
            (self.roles['reviewer'], target.id, '', UserError),
            (self.roles['reviewer'], target.id, 'collision', UserError),
        ):
            with self.assertRaises(error):
                binding.with_user(user).action_override_binding(
                    record_id,
                    reason,
                )
            binding.invalidate_recordset()
            self.assertEqual(binding.partner_id, current)
            self.assertEqual(self._audit_jobs(), before)

    def test_non_overridable_seam_refuses_without_write_or_audit(self):
        current = self._partner('Non-overridable current', self.company)
        target = self._partner('Non-overridable target', self.company)
        binding = self._binding(current)
        before = self._audit_jobs()
        with patch.object(
            type(binding),
            '_odoo_binding_field_name',
            return_value=False,
        ):
            with self.assertRaises(UserError):
                binding.with_user(
                    self.roles['reviewer']
                ).action_override_binding(
                    target.id,
                    'must fail closed',
                )
        binding.invalidate_recordset()
        self.assertEqual(binding.partner_id, current)
        self.assertEqual(self._audit_jobs(), before)

    def test_override_atomic_rollback_when_audit_fails(self):
        current = self._partner('Atomic current', self.company)
        target = self._partner('Atomic target', self.company)
        binding = self._binding(current)
        before = self._audit_jobs()
        with patch.object(
            type(self.store),
            '_create_lifecycle_audit_job',
            side_effect=RuntimeError('synthetic audit failure'),
        ):
            with self.assertRaises(RuntimeError):
                with self.env.cr.savepoint():
                    binding.with_user(
                        self.roles['reviewer']
                    ).action_override_binding(target.id, 'atomic proof')
        binding.invalidate_recordset()
        self.assertEqual(binding.partner_id, current)
        self.assertFalse(binding.override_uid)
        self.assertEqual(self._audit_jobs(), before)

    def test_manual_mask_action_is_absent_for_every_role(self):
        """SEC-2 section H item 6: the manual mask action no longer exists.

        Asserting absence on the model is stronger than asserting an
        AccessError: an action that still exists but is merely denied to the
        current role is exactly the dormant capability Option 1 rejects in
        favour of Option 2.
        """
        self.assertFalse(
            hasattr(self.Retention, 'action_mask_customer_pii'),
        )
        self.assertFalse(
            hasattr(self.Retention, '_binding_models_with_pii'),
        )

    def test_sweep_redacts_logs_and_never_touches_a_business_record(self):
        """SEC-2 section H item 7 + the retained-redaction half of TA-C5.

        One sweep, two assertions that must both hold: aged log payloads are
        redacted (redaction stays mandatory) and the binding snapshots are
        returned byte-for-byte unchanged (masking is gone). Running both
        against a single sweep is what proves the two behaviours were
        separated rather than removed together.
        """
        old = fields.Datetime.now() - timedelta(days=3)
        binding = self._binding(
            self._partner('Sweep untouched', self.company),
            gid='gid://shopify/Customer/SweepUntouched',
            create_date=old,
        )
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': self.store.id,
            'log_redaction_retention_days': 1,
        })
        job = self.store.sudo()._create_lifecycle_audit_job(
            'SEC-2 redaction fixture carrier'
        )
        log = self.JobLog.sudo().create({
            'job_id': job.id,
            'event_type': 'note',
            'message': 'aged payload fixture',
            'payload_snapshot': json.dumps({
                'email': 'jane.sensitive@example.com',
                'nested': {'phone': '+971501234567', 'count': 2},
            }),
            'actor_uid': self.env.uid,
            'occurred_at': old,
        })

        self.Retention.run_sweep()

        binding.invalidate_recordset()
        self.assertEqual(
            binding.shopify_email_snapshot,
            'jane.sensitive@example.com',
            'the sweep must not mask a business record',
        )
        self.assertEqual(binding.shopify_phone_snapshot, '+971501234567')
        self.assertEqual(binding.shopify_display_name, 'Jane Sensitive')
        self.assertFalse(binding.pii_snapshot_refresh_required)

        log.invalidate_recordset()
        self.assertNotIn('jane.sensitive@example.com', log.payload_snapshot)
        self.assertNotIn('+971501234567', log.payload_snapshot)
        payload = json.loads(log.payload_snapshot)
        self.assertEqual(payload['email'], '***')
        self.assertEqual(payload['nested']['phone'], '***')

    def test_override_signature_has_no_model_or_company_argument(self):
        core_models = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'shopify_connector_core',
            'models',
            'shopify_connector_binding_mixin.py',
        )
        with open(core_models, encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=core_models)
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == 'action_override_binding'
        )
        self.assertEqual(
            [argument.arg for argument in method.args.args],
            ['self', 'new_record_id', 'reason'],
        )
