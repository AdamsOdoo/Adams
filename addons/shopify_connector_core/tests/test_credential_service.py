import ast
import os

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

from ..models import shopify_connector_store_credential as credential_module
# Reusable AST source-guard helpers (control-room review 4692156428). Defined
# once in test_disconnect_quiescence (imported earlier by tests/__init__.py,
# mirroring the existing `from .test_api_client import ...` convention) so the
# executable-AST inspection is shared, not duplicated.
from .test_disconnect_quiescence import (
    guard_called_names,
    guard_fn_ast,
    guard_min_call_lineno,
    guard_str_constants,
)

DUMMY_TOKEN_1 = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
DUMMY_TOKEN_2 = 'shpat_DUMMYDUMMYDUMMY1111111111111111'
CREDENTIAL_VALUE_ERROR_MESSAGE = 'A non-empty credential value is required.'


def _sudo_sites_for_tree(filename, tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    raw = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'sudo'
        ):
            continue
        owner = parents.get(node)
        while owner and not isinstance(owner, ast.FunctionDef):
            owner = parents.get(owner)
        raw.append((
            owner.name if owner else False,
            ast.unparse(node.func.value),
            node.lineno,
        ))
    counters = {}
    sites = []
    for method, receiver, _line in sorted(
        raw, key=lambda site: (site[0], site[2])
    ):
        key = (filename, method, receiver)
        counters[key] = counters.get(key, 0) + 1
        sites.append(key + (counters[key],))
    return sites


CORE_SUDO_SITES = [
    ('shopify_connector_binding_mixin.py',
     'action_override_binding', 'self', 1),
    ('shopify_connector_job.py', '_has_mutation_attempt_evidence',
     "self.env['shopify.connector.mutation.attempt']", 1),
    ('shopify_connector_job.py', '_compute_merchant_write_status',
     "self.env['shopify.connector.mutation.attempt']", 1),
    ('shopify_connector_job.py', '_reassign_to_historic_job_type',
     'job', 1),
    ('shopify_connector_job.py', '_reassign_to_historic_job_type',
     'job', 2),
    ('shopify_connector_job.py', '_transition_blocked_manual_review',
     'self', 1),
    ('shopify_connector_job.py', '_transition_failed_final', 'self', 1),
    ('shopify_connector_job.py', '_transition_failed_retryable',
     'self', 1),
    ('shopify_connector_job.py', '_transition_retry_waiting',
     'self', 1),
    ('shopify_connector_job.py', '_transition_skipped', 'self', 1),
    ('shopify_connector_job.py', 'action_resolve_manual_review',
     'self', 1),
    ('shopify_connector_job_actions.py', 'action_cancel', 'self', 1),
    ('shopify_connector_job_actions.py', 'action_manual_retry',
     'self', 1),
    ('shopify_connector_job_dispatch.py',
     '_apply_validated_consequence', 'job', 1),
    ('shopify_connector_job_dispatch.py', '_block_original_job',
     'job', 1),
    ('shopify_connector_job_dispatch.py',
     '_complete_reconciliation_job', 'job', 1),
    ('shopify_connector_job_dispatch.py', '_drain_mutation_one',
     'job', 1),
    ('shopify_connector_job_dispatch.py',
     '_ensure_reconciliation_job', 'Job', 1),
    ('shopify_connector_job_dispatch.py', '_invoke_handler', 'job', 1),
    ('shopify_connector_job_dispatch.py',
     '_recover_after_concurrency_conflict', 'locked', 1),
    ('shopify_connector_job_dispatch.py',
     '_recover_committed_attempt_to_reconciliation', 'job', 1),
    ('shopify_connector_job_dispatch.py', '_recover_layer2_owner',
     'job', 1),
    ('shopify_connector_job_dispatch.py', '_recover_pre_c2_failure',
     'job', 1),
    ('shopify_connector_job_dispatch.py', '_start_running', 'job', 1),
    ('shopify_connector_job_enqueue.py', 'enqueue',
     "self.env['shopify.connector.job']", 1),
    ('shopify_connector_job_log.py', '_system_append', 'self', 1),
    ('shopify_connector_mutation_attempt.py', '_surface', 'self', 1),
    ('shopify_connector_mutation_attempt.py',
     'action_resolve_mutation_attempt', 'job', 1),
    # PERF-1: the drain's per-pass cap. System-parameter reads are
    # admin-only in Odoo 19, so this read needs elevation. Read-only, and
    # the value is clamped to [1,500] before it reaches the loop.
    ('shopify_connector_job_dispatch.py',
     '_resolve_drain_batch_size',
     "self.env['ir.config_parameter']", 1),
    ('shopify_connector_pii_retention.py',
     '_attempt_evidence_retention_days',
     "self.env['ir.config_parameter']", 1),
    ('shopify_connector_pii_retention.py', 'run_sweep',
     "self.env['shopify.connector.store.settings']", 1),
    ('shopify_connector_pii_retention.py', 'run_sweep', 'JobLog', 1),
    ('shopify_connector_readiness_check.py',
     '_drain_cron_active_state', 'cron', 1),
    # S1 (2026-07-27). System-parameter reads are `base.group_system` in
    # Odoo 19, and readiness runs as the invoking connector administrator --
    # who is not necessarily an Odoo system administrator. Without this the
    # check raised AccessError and took the whole readiness run with it, which
    # `action_reconnect` could already reach in production.
    ('shopify_connector_readiness_check.py',
     '_web_base_url', "self.env['ir.config_parameter']", 1),
    ('shopify_connector_readiness_check.py', 'run_for_store', 'Job', 1),
    ('shopify_connector_readiness_check.py', 'run_for_store', 'job', 1),
    # ------------------------------------------------------------------
    # S1 guided setup (2026-07-27).
    #
    # Every elevation below runs AFTER `_resolve_store` has established the
    # Connector Administrator role, record access as the calling user, and
    # company consistency against `env.companies`. None of them can cross a
    # company boundary: `company_id` on both the settings row and every job
    # row is a stored related field through `store_id`, so a row's company is
    # its store's company by construction rather than by assignment.
    #
    # They exist because Odoo's merged ACL grants no connector group `create`
    # on `shopify.connector.store` or `shopify.connector.store.settings`, and
    # no `write` on the readonly progress columns -- deliberately, since all
    # three are structure rather than data. Setup is the one flow that has to
    # create them.
    ('shopify_connector_setup_wizard.py', '_settings_for', 'Settings', 1),
    ('shopify_connector_setup_wizard.py', '_settings_for', 'Settings', 2),
    # Wave 5: two writes, because a legacy row whose position does not
    # advance still gets its semantic step key backfilled -- the branch that
    # upgrades a pre-Wave-5 row in place rather than leaving it dependent on
    # the read-time numeric translation forever.
    ('shopify_connector_setup_wizard.py', '_record_progress', 'settings', 1),
    ('shopify_connector_setup_wizard.py', '_record_progress', 'settings', 2),
    # Wave 5: the readiness-staleness stamp. It lives on the settings model
    # rather than in the setup service because the INVENTORY domain has to be
    # able to set it too -- a location mapping is exactly what
    # `mapped_location` reads -- and a second copy of "which field means
    # stale" is how the two would drift. `readonly` structure, like the
    # setup-progress columns beside it, so the write is elevated for the same
    # reason they are; every caller has established its own authority first.
    ('shopify_connector_store_settings.py',
     '_mark_setup_readiness_stale', 'self', 1),
    ('shopify_connector_store_settings.py',
     '_clear_setup_readiness_stale', 'self', 1),
    ('shopify_connector_store_settings.py',
     '_ensure_canonical_settings_rows',
     "self.env['shopify.connector.store.settings']", 1),
    ('shopify_connector_setup_wizard.py', '_last_readiness_checks',
     "self.env['shopify.connector.job']", 1),
    ('shopify_connector_setup_wizard.py', '_last_readiness_checks',
     "self.env['shopify.connector.job.log']", 1),
    ('shopify_connector_setup_wizard.py', 'save_store_identity',
     "self.env['shopify.connector.store']", 1),
    ('shopify_connector_setup_wizard.py', 'save_store_identity',
     "self.env['shopify.connector.store']", 2),
    ('shopify_connector_setup_wizard.py', 'save_directions', 'settings', 1),
    ('shopify_connector_setup_wizard.py', 'save_source_of_truth',
     'settings', 1),
    ('shopify_connector_setup_wizard.py', 'save_notification', 'settings', 1),
    ('shopify_connector_setup_wizard.py', 'save_first_push_schedule',
     'settings', 1),
    ('shopify_connector_setup_wizard.py', 'activate', 'settings', 1),
    ('shopify_connector_setup_wizard.py', 'restart_setup', 'settings', 1),
    # SEC-3 (#197) scope-mixin seams. The upgrade sweep must see rows that the
    # fail-closed rules hide from every ordinary reader -- including, by
    # design, rows it is about to quarantine. The release action re-runs the
    # consistency check under sudo before clearing anything.
    ('shopify_connector_scope_mixin.py',
     '_sec3_quarantine_scope_mismatches', 'self', 1),
    ('shopify_connector_scope_mixin.py',
     'action_sec3_release_scope_quarantine', 'self', 1),
    ('shopify_connector_stale_owner_sweep.py',
     '_positive_int_parameter', "self.env['ir.config_parameter']", 1),
    ('shopify_connector_stale_owner_sweep.py', 'run_sweep', 'job', 1),
    ('shopify_connector_store.py', '_apply_probe_failure', 'job', 1),
    # TD-014 (PERF-1 / D-PERF1-4). Three elevations that write only
    # this store's own rate-head-room state and its derived health
    # state. No credential, no payload, no cross-store read: the
    # recovery sweep searches stores the cron user already sees.
    ('shopify_connector_store.py', '_apply_throttle_backpressure',
     'self', 1),
    ('shopify_connector_store.py', '_apply_throttle_backpressure',
     'self', 2),
    ('shopify_connector_store.py', '_audit_probe_superseded', 'job', 1),
    # SEC-3 (#197) ownership seams. Both are deliberate and both are recorded
    # here because this guard is the audit: a new sudo() in core is a change to
    # the trust surface, not an implementation detail.
    ('shopify_connector_store.py', '_backfill_company',
     "self.env['res.company']", 1),
    ('shopify_connector_store.py', 'action_assign_company', 'self', 1),
    ('shopify_connector_store.py', '_connector_scheduler_is_active',
     'cron', 1),
    ('shopify_connector_store.py', '_create_lifecycle_audit_job',
     'Job', 1),
    ('shopify_connector_store.py', '_create_lifecycle_audit_job',
     'job', 1),
    ('shopify_connector_store.py', '_record_throttle_status', 'self', 1),
    ('shopify_connector_store.py', '_recover_throttled_stores',
     'self', 1),
    ('shopify_connector_store.py', '_run_connection_probe', 'Job', 1),
    # Wave 5. The probe now obtains/refreshes a client-credentials token BEFORE
    # it creates its audit job, so a refresh failure has no job to record
    # against yet. This second elevation creates that job and hands it straight
    # to the unchanged `_apply_probe_failure`, so an authentication failure is
    # recorded exactly like every other one instead of escaping as an unhandled
    # error. Same store, same scope, same audit shape as ordinal 1.
    ('shopify_connector_store.py', '_run_connection_probe', 'Job', 2),
    ('shopify_connector_store.py', '_run_connection_probe', 'job', 1),
    ('shopify_connector_store.py', '_run_connection_probe', 'job', 2),
    ('shopify_connector_store.py',
     '_sweep_quiescing_business_jobs', 'job', 1),
    ('shopify_connector_store.py', 'action_force_disconnect', 'job', 1),
    ('shopify_connector_store_credential.py', '_get_access_token',
     'self', 1),
    # ------------------------------------------------------------------
    # Wave 5 -- the client-credentials mode.
    #
    # Every elevation below is the SAME elevation `_get_access_token` has
    # always had, factored into named helpers so the token cache and the
    # credential row are read through one place each rather than through a
    # `sudo()` repeated at every call site. Each is scoped to the single store
    # already being operated on, and none can cross a store or company
    # boundary: `store_id` is an explicit term in every search, and
    # `company_id` on both tables is a stored related field through `store_id`,
    # so a row's company is its store's company by construction.
    #
    # The credential and token-cache models are default-deny by design -- the
    # credential grants only the Administrator, and the token cache grants NO
    # group at all -- which is precisely why the connector's own internal reads
    # need a named, inventoried elevation rather than an ACL widening.
    # ------------------------------------------------------------------
    ('shopify_connector_store_credential.py', '_cached_token_row',
     "self.env['shopify.connector.store.access.token']", 1),
    ('shopify_connector_store_credential.py', '_credential_for',
     'self', 1),
    ('shopify_connector_store_credential.py', '_write_token_cache',
     "self.env['shopify.connector.store.access.token']", 1),
]
CORE_SUDO_PURPOSE_BY_OWNER = {
    ('shopify_connector_binding_mixin.py',
     'action_override_binding'): 'Audited binding override.',
    ('shopify_connector_job.py',
     '_has_mutation_attempt_evidence'): 'Protected evidence read.',
    ('shopify_connector_job.py',
     '_compute_merchant_write_status'): 'Protected acknowledgement read.',
    ('shopify_connector_job.py',
     '_reassign_to_historic_job_type'): 'Historic conversion.',
    ('shopify_connector_job.py',
     '_transition_blocked_manual_review'): 'Protected transition.',
    ('shopify_connector_job.py',
     '_transition_failed_final'): 'Protected transition.',
    ('shopify_connector_job.py',
     '_transition_failed_retryable'): 'Protected transition.',
    ('shopify_connector_job.py',
     '_transition_retry_waiting'): 'Protected transition.',
    ('shopify_connector_job.py',
     '_transition_skipped'): 'Protected transition.',
    ('shopify_connector_job.py',
     'action_resolve_manual_review'): 'Manual review resolution.',
    ('shopify_connector_job_actions.py',
     'action_cancel'): 'Audited cancellation.',
    ('shopify_connector_job_actions.py',
     'action_manual_retry'): 'Audited manual retry.',
    ('shopify_connector_job_dispatch.py',
     '_apply_validated_consequence'): 'Layer 2 consequence write.',
    ('shopify_connector_job_dispatch.py',
     '_block_original_job'): 'Fail-closed original-job write.',
    ('shopify_connector_job_dispatch.py',
     '_complete_reconciliation_job'): 'Read-job completion.',
    ('shopify_connector_job_dispatch.py',
     '_drain_mutation_one'): 'C1 ownership write.',
    ('shopify_connector_job_dispatch.py',
     '_ensure_reconciliation_job'): 'Reconciliation job creation.',
    ('shopify_connector_job_dispatch.py',
     '_invoke_handler'): 'Handler failure transition.',
    ('shopify_connector_job_dispatch.py',
     '_recover_after_concurrency_conflict'): 'Conflict recovery.',
    ('shopify_connector_job_dispatch.py',
     '_recover_committed_attempt_to_reconciliation'):
        'Post-C2 ownership cleanup.',
    ('shopify_connector_job_dispatch.py',
     '_recover_layer2_owner'): 'Layer 2 owner recovery.',
    ('shopify_connector_job_dispatch.py',
     '_recover_pre_c2_failure'): 'Pre-C2 owner recovery.',
    ('shopify_connector_job_dispatch.py',
     '_start_running'): 'Claim transition.',
    ('shopify_connector_job_enqueue.py',
     'enqueue'): 'Protected job creation.',
    ('shopify_connector_job_log.py',
     '_system_append'): 'System audit-log append.',
    ('shopify_connector_mutation_attempt.py',
     '_surface'): 'Closed attempt write surface.',
    ('shopify_connector_mutation_attempt.py',
     'action_resolve_mutation_attempt'): 'Resolved job consequence.',
    ('shopify_connector_job_dispatch.py',
     '_resolve_drain_batch_size'): 'Drain cap configuration.',
    ('shopify_connector_pii_retention.py',
     '_attempt_evidence_retention_days'): 'Retention configuration.',
    ('shopify_connector_pii_retention.py',
     'run_sweep'): 'Retention sweep and audit.',
    ('shopify_connector_readiness_check.py',
     '_drain_cron_active_state'): 'Read cron configuration.',
    ('shopify_connector_readiness_check.py',
     '_web_base_url'): 'Read public base-URL configuration.',
    ('shopify_connector_readiness_check.py',
     'run_for_store'): 'Readiness audit job lifecycle.',
    ('shopify_connector_setup_wizard.py',
     '_settings_for'): 'S1 store-settings row create.',
    ('shopify_connector_setup_wizard.py',
     '_record_progress'): 'S1 resume-point write.',
    ('shopify_connector_store_settings.py',
     '_mark_setup_readiness_stale'): 'S1 readiness-staleness stamp.',
    ('shopify_connector_store_settings.py',
     '_clear_setup_readiness_stale'): 'S1 readiness-staleness clear.',
    ('shopify_connector_store_settings.py',
     '_ensure_canonical_settings_rows'): (
        'Batch 2 canonical Store Settings row ensure. Elevated only to create '
        'the structural settings row for store ids the caller already '
        'resolved in its own environment; never used to discover a store.'
    ),
    ('shopify_connector_setup_wizard.py',
     '_last_readiness_checks'): 'S1 per-check readiness evidence read.',
    ('shopify_connector_setup_wizard.py',
     'save_store_identity'): 'S1 store row create.',
    ('shopify_connector_setup_wizard.py',
     'save_directions'): 'S1 domain enablement write.',
    ('shopify_connector_setup_wizard.py',
     'save_source_of_truth'): 'S1 source-of-truth write.',
    ('shopify_connector_setup_wizard.py',
     'save_notification'): 'S1 notification default write.',
    ('shopify_connector_setup_wizard.py',
     'save_first_push_schedule'): 'S1 first-push scheduling write.',
    ('shopify_connector_setup_wizard.py',
     'activate'): 'S1 completion stamp.',
    ('shopify_connector_setup_wizard.py',
     'restart_setup'): 'S1 re-run stamp.',
    ('shopify_connector_scope_mixin.py',
     '_sec3_quarantine_scope_mismatches'):
        'SEC-3 historic scope sweep over fail-closed rows.',
    ('shopify_connector_scope_mixin.py',
     'action_sec3_release_scope_quarantine'):
        'SEC-3 administrative quarantine release re-check.',
    ('shopify_connector_stale_owner_sweep.py',
     '_positive_int_parameter'): 'Read sweep configuration.',
    ('shopify_connector_stale_owner_sweep.py',
     'run_sweep'): 'Stale-owner cleanup.',
    ('shopify_connector_store.py',
     '_apply_probe_failure'): 'Probe failure transition.',
    ('shopify_connector_store.py',
     '_audit_probe_superseded'): 'Probe supersession audit.',
    # TD-014: PERF-1's backpressure lever, finally given an input.
    # `api_health_state`/`api_health_reason` and the four
    # `api_throttle_*` numerics are all readonly protected fields, so
    # the service that maintains them cannot write them unelevated.
    ('shopify_connector_store.py',
     '_record_throttle_status'): 'Rate head-room observation write.',
    ('shopify_connector_store.py',
     '_apply_throttle_backpressure'): 'Rate backpressure health write.',
    ('shopify_connector_store.py',
     '_recover_throttled_stores'): 'Rate deferral recovery sweep.',
    # Reads res.company to decide whether ownership is PROVABLE (exactly one
    # company) during install/update. Never writes a company it guessed.
    ('shopify_connector_store.py',
     '_backfill_company'): 'SEC-3 ownership backfill probe.',
    # Resolves a company-less historic store by explicit id -- it is invisible
    # to a normal read by construction, which is the point of the fail-closed
    # rule. Administrator-gated, refuses to re-home an already-owned store, and
    # validates the target company against the caller's own company_ids rather
    # than trusting the value passed in.
    ('shopify_connector_store.py',
     'action_assign_company'): 'SEC-3 administrative ownership remediation.',
    ('shopify_connector_store.py',
     '_create_lifecycle_audit_job'): 'Lifecycle audit carrier.',
    # Batch 2 correction (F7). `ir.cron` is Administrator-only by ACL, and an
    # Operator reading their own store's page is not one -- but the merchant-
    # facing "scheduled import" state is a lie unless it consults the cron that
    # would actually perform it. The elevation is the narrowest available: the
    # record is resolved from a module-owned external id through `env.ref`
    # BEFORE anything elevates, so `sudo()` is never used to DISCOVER a record,
    # only to read `active` on the one this module installed. It reads one
    # Boolean, writes nothing, and returns False for anything that is not a
    # live `ir.cron`.
    ('shopify_connector_store.py',
     '_connector_scheduler_is_active'):
        'Truthful scheduled-state projection: reads `active` on the '
        'module-owned cron already resolved by external id.',
    ('shopify_connector_store.py',
     '_run_connection_probe'): 'Probe audit job lifecycle.',
    ('shopify_connector_store.py',
     '_sweep_quiescing_business_jobs'): 'Disconnect job sweep.',
    ('shopify_connector_store.py',
     'action_force_disconnect'): 'Forced-disconnect audit.',
    ('shopify_connector_store_credential.py',
     '_get_access_token'): 'Single-store credential read.',
    ('shopify_connector_store_credential.py',
     '_cached_token_row'): 'Single-store token-cache read.',
    ('shopify_connector_store_credential.py',
     '_credential_for'): 'Single-store credential row read.',
    ('shopify_connector_store_credential.py',
     '_write_token_cache'): 'Single-store token-cache write.',
}

SUDO_INVENTORY_FIELDS = (
    'filename', 'method', 'receiver', 'duplicate_ordinal', 'purpose',
)


def canonical_core_sudo_inventory():
    return tuple(
        site + (
            CORE_SUDO_PURPOSE_BY_OWNER[(site[0], site[1])],
        )
        for site in CORE_SUDO_SITES
    )


def core_sudo_inventory_for_file(filename):
    return tuple(
        entry for entry in canonical_core_sudo_inventory()
        if entry[0] == filename
    )


def collect_core_sudo_sites(models_dir):
    sites = []
    for filename in sorted(os.listdir(models_dir)):
        if not filename.endswith('.py'):
            continue
        path = os.path.join(models_dir, filename)
        with open(path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=filename)
        sites.extend(_sudo_sites_for_tree(filename, tree))
    return tuple(sites)


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
class TestCredentialService(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Credential Service Test Store',
            'shop_domain': 'credential-service-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.user_auditor = cls._create_group_user(
            'auditor', 'group_shopify_connector_auditor'
        )
        cls.user_operator = cls._create_group_user(
            'operator', 'group_shopify_connector_operator'
        )
        cls.user_reviewer = cls._create_group_user(
            'reviewer', 'group_shopify_connector_reviewer'
        )
        cls.user_admin = cls._create_group_user(
            'admin', 'group_shopify_connector_admin'
        )

    @classmethod
    def _create_group_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'Credential Service Test %s' % label,
            'login': 'credential_service_test_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _credential_as_admin(self):
        return self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        )

    def search_credential(self):
        return self._credential_as_admin().search(
            [('store_id', '=', self.store.id)], limit=1
        )

    def _assert_dummy_absent_except_access_token(self, token):
        # fields_get() here is schema enumeration only (which char/text
        # fields exist), not a security oracle -- the actual assertion is
        # the value-content scan below, run as admin against already-
        # fetched records, unrelated to any ACL/visibility check.
        store_fields = self.store.fields_get()
        for field_name, field_info in store_fields.items():
            if field_info['type'] not in ('char', 'text'):
                continue
            value = self.store[field_name]
            if value:
                self.assertNotIn(token, value)
        credential = self._credential_as_admin().search(
            [('store_id', '=', self.store.id)]
        )
        if not credential:
            return
        credential_fields = credential.fields_get()
        for field_name, field_info in credential_fields.items():
            if field_name == 'access_token':
                continue
            if field_info['type'] not in ('char', 'text'):
                continue
            value = credential[field_name]
            if value:
                self.assertNotIn(token, value)

    def test_action_set_token_creates_row_and_mirrors(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(len(credential), 1)
        self.assertEqual(credential.credential_state, 'present')
        self.store.invalidate_recordset()
        self.assertTrue(self.store.credential_present)
        self._assert_dummy_absent_except_access_token(DUMMY_TOKEN_1)

    def test_action_replace_token_stamps_and_resets_verification(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({
            'credential_last_verified_at': '2026-07-07 00:00:00',
        })
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertTrue(self.store.credential_last_replaced_at)
        self.assertFalse(self.store.credential_last_verified_at)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.access_token, DUMMY_TOKEN_2)
        self._assert_dummy_absent_except_access_token(DUMMY_TOKEN_2)

    def test_action_set_token_update_on_connected_store_moves_to_reconnect_needed(self):
        # PR #121 Revision 5: credential mutation must invalidate
        # store.state, not just credential_last_verified_at --
        # business-job gating keys off store.state, so a 'connected'
        # store must not remain 'connected' after its token is
        # silently overwritten via action_set_token().
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({
            'state': 'connected',
            'credential_last_verified_at': '2026-07-07 00:00:00',
        })
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job_count_before = Job.search_count([])
        job_log_count_before = JobLog.search_count([])

        Credential.action_set_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertEqual(Job.search_count([]), job_count_before)
        self.assertEqual(JobLog.search_count([]), job_log_count_before)

    def test_action_replace_token_on_connected_store_moves_to_reconnect_needed(self):
        # PR #121 Revision 5: same invalidation requirement as
        # action_set_token(), for the replace path.
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({
            'state': 'connected',
            'credential_last_verified_at': '2026-07-07 00:00:00',
        })
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job_count_before = Job.search_count([])
        job_log_count_before = JobLog.search_count([])

        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertEqual(Job.search_count([]), job_count_before)
        self.assertEqual(JobLog.search_count([]), job_log_count_before)

    # ------------------------------------------------------------------
    # CORE-R2 (AR-047; review 4690639375 #3): store->credential lock order,
    # refuse-while-disconnecting, and connected-replacement epoch bump.
    # ------------------------------------------------------------------

    def test_set_token_refused_while_disconnecting(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnecting', 'connection_generation': 3})
        with self.assertRaises(UserError):
            Credential.action_set_token(self.store, DUMMY_TOKEN_2)
        # Original credential, mirrors, and generation are all unchanged.
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.connection_generation, 3)

    def test_replace_token_refused_while_disconnecting(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnecting', 'connection_generation': 3})
        with self.assertRaises(UserError):
            Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.connection_generation, 3)

    def test_connected_set_token_bumps_generation_exactly_once(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'connected', 'connection_generation': 5})
        Credential.action_set_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self.store.connection_generation, 6)
        self.assertFalse(self.store.credential_last_verified_at)

    def test_connected_replace_token_bumps_generation_exactly_once(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'connected', 'connection_generation': 5})
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self.store.connection_generation, 6)
        self.assertTrue(self.store.credential_last_replaced_at)

    def test_non_connected_set_token_does_not_bump_generation(self):
        # A set/replace on a non-connected, non-disconnecting store preserves the
        # state and adds NO extra generation bump (review §5.8).
        Credential = self._credential_as_admin()
        self.store.write({'state': 'reconnect_needed', 'connection_generation': 7})
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self.store.connection_generation, 7)

    def test_mutate_token_locks_store_before_credential_source(self):
        # store -> credential global lock order: _mutate_token takes the store
        # update lock (store._lock_store_for_lifecycle) BEFORE it reads/writes the
        # credential row, refuses while disconnecting, and uses no sudo().
        #
        # AST-robust (control-room review 4692156428): inspect the EXECUTABLE
        # body -- not raw source text -- so the method docstring's "normal ACL,
        # **no `sudo()`**" prose is NOT a false positive. All three original
        # safety assertions are preserved, now evaluated against real code.
        fn = guard_fn_ast(
            credential_module.ShopifyConnectorStoreCredential._mutate_token
        )
        lock_line = guard_min_call_lineno(fn, '_lock_store_for_lifecycle')
        search_line = guard_min_call_lineno(fn, 'search', receiver_name='self')
        self.assertIsNotNone(lock_line, 'the store lifecycle lock must be taken')
        self.assertIsNotNone(search_line, 'the credential row must be searched')
        self.assertLess(
            lock_line, search_line,
            'the store row must be locked before the credential row is read/written',
        )
        # refuse-while-disconnecting: the executable code compares the freshly
        # locked state against the 'disconnecting' literal.
        self.assertIn('disconnecting', guard_str_constants(fn))
        # no sudo() call anywhere in the mutation path (docstring prose excluded).
        self.assertNotIn('sudo', guard_called_names(fn))

    def test_action_clear_token_on_connected_store_requests_two_phase_disconnect(self):
        # CORE-R2 (reviews 4690804619 #2 + 4690807427): public clear on a
        # `connected` store must NOT clear immediately (an admitted lease can
        # outlive admission's FOR SHARE). It routes through the accepted two-phase
        # disconnect: state -> `disconnecting`, credential STILL present, exactly
        # one epoch bump, an audited request -- the controller clears at finalize.
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'connected'})
        self.store.invalidate_recordset()
        gen_before = self.store.connection_generation

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.disconnect_status, 'requested')
        self.assertTrue(self.store.credential_present)   # NOT cleared yet
        self.assertEqual(self.store.connection_generation, gen_before + 1)
        credential = self.search_credential()
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)

    def test_clear_token_requests_disconnect_when_reconnect_needed(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'reconnect_needed'})
        self.store.invalidate_recordset()
        gen_before = self.store.connection_generation

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.disconnect_status, 'requested')
        self.assertTrue(self.store.credential_present)   # NOT cleared yet
        self.assertEqual(self.store.connection_generation, gen_before + 1)
        credential = self.search_credential()
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)

    def test_action_clear_token_refused_while_disconnecting(self):
        # Public clear must refuse while a disconnect is in progress -- the
        # controller owns the clear at completed/timed_out.
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        # Credential untouched by the refused clear.
        credential = self.search_credential()
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)
        self.assertTrue(self.store.credential_present)

    def test_action_clear_token_direct_clear_from_setup_incomplete(self):
        # A never-connected store has no active-business-call posture, so the
        # public clear empties the credential directly (no disconnect request).
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.assertEqual(self.store.state, 'setup_incomplete')
        Job = self.env['shopify.connector.job']
        job_count_before = Job.search_count([])

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'setup_incomplete')
        self.assertFalse(self.store.credential_present)
        credential = self.search_credential()
        self.assertFalse(credential.access_token)
        self.assertEqual(credential.credential_state, 'absent')
        # A direct clear is not an audited lifecycle action -- no job rows.
        self.assertEqual(Job.search_count([]), job_count_before)

    def test_action_clear_token_direct_clear_from_disconnected(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnected'})
        Job = self.env['shopify.connector.job']
        job_count_before = Job.search_count([])

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnected')
        self.assertFalse(self.store.credential_present)
        self.assertEqual(Job.search_count([]), job_count_before)

    def test_action_clear_token_empties_and_preserves_history(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        replaced_at = self.store.credential_last_replaced_at
        Credential.action_clear_token(self.store)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(len(credential), 1)
        self.assertFalse(credential.access_token)
        self.assertEqual(credential.credential_state, 'absent')
        self.store.invalidate_recordset()
        self.assertFalse(self.store.credential_present)
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertFalse(self.store.credential_last_failure_reason)
        self.assertEqual(self.store.credential_last_replaced_at, replaced_at)
        self._assert_dummy_absent_except_access_token(DUMMY_TOKEN_2)

    def test_action_clear_token_idempotent_with_no_existing_row(self):
        Credential = self._credential_as_admin()
        Credential.action_clear_token(self.store)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertFalse(credential)

    # mute_logger: the second create() below intentionally triggers the
    # store_id UNIQUE constraint (shopify_connector_store_credential_
    # store_id_uniq); without muting, Odoo's `odoo.sql_db` logger emits
    # an avoidable ERROR-level "bad query" line for this expected failure.
    @mute_logger('odoo.sql_db')
    def test_duplicate_credential_row_for_same_store_raises(self):
        # A fresh, test-local store (not the shared class-level
        # `self.store`) so this scenario can never collide with a
        # credential row another test method left on the class store.
        Credential = self._credential_as_admin()
        store = self.env['shopify.connector.store'].create({
            'name': 'Duplicate Credential Test Store',
            'shop_domain': 'duplicate-credential-test.myshopify.com',
            'api_version': '2026-07',
        })
        # Batch 1 correction (§9.1): `create()` is refused outside the credential
        # service's own surface, so both creates below go through it. The
        # constraint being proven is the database's, not the guard's -- the guard
        # has its own coverage in `test_credential_access.py`.
        surface = Credential._credential_surface('_mutate_token')
        surface.create({'store_id': store.id, 'credential_epoch': 1})
        # The second create()'s UNIQUE(store_id) violation is a raw
        # database-level error (Odoo 19 `models.Constraint`, not a Python
        # `@api.constrains` ValidationError) -- run it under its own
        # savepoint so the expected failure does not poison the rest of
        # this test's transaction, mirroring the existing
        # `test_core_readiness_check_untouched_still_collides` pattern for
        # the job model's own unique constraint.
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                surface.create({'store_id': store.id, 'credential_epoch': 1})

    def test_empty_or_non_string_value_raises_without_echoing(self):
        Credential = self._credential_as_admin()
        for bad_value in ('', None, 12345):
            with self.assertRaises(ValidationError) as catcher:
                Credential.action_set_token(self.store, bad_value)
            self.assertEqual(
                str(catcher.exception), CREDENTIAL_VALUE_ERROR_MESSAGE
            )
            with self.assertRaises(ValidationError) as catcher:
                Credential.action_replace_token(self.store, bad_value)
            self.assertEqual(
                str(catcher.exception), CREDENTIAL_VALUE_ERROR_MESSAGE
            )

    def test_stamps_based_audit_reflects_acting_admin(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.create_uid, self.user_admin)
        self.assertEqual(credential.write_uid, self.user_admin)
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        credential.invalidate_recordset()
        self.assertEqual(credential.write_uid, self.user_admin)
        self.assertTrue(credential.write_date)

    def test_no_job_or_job_log_rows_written(self):
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job_count_before = Job.search_count([])
        job_log_count_before = JobLog.search_count([])
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        Credential.action_clear_token(self.store)
        self.assertEqual(Job.search_count([]), job_count_before)
        self.assertEqual(JobLog.search_count([]), job_log_count_before)

    def test_get_access_token_internal_and_write_paths_denied_for_non_admin(self):
        Credential = self.env['shopify.connector.store.credential']
        self._credential_as_admin().action_set_token(self.store, DUMMY_TOKEN_1)
        self.assertEqual(
            Credential._get_access_token(self.store), DUMMY_TOKEN_1
        )
        credential_as_operator = Credential.with_user(self.user_operator)
        with self.assertRaises(AccessError):
            credential_as_operator.action_set_token(self.store, DUMMY_TOKEN_2)
        with self.assertRaises(AccessError):
            credential_as_operator.action_replace_token(
                self.store, DUMMY_TOKEN_2
            )
        with self.assertRaises(AccessError):
            credential_as_operator.action_clear_token(self.store)

    def test_source_level_sanctioned_sudo_sites_guard(self):
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )
        actual = collect_core_sudo_sites(models_dir)
        expected_inventory = canonical_core_sudo_inventory()
        expected = tuple(entry[:4] for entry in expected_inventory)
        self.assertEqual(
            set(SUDO_INVENTORY_FIELDS),
            {
                'filename', 'method', 'receiver',
                'duplicate_ordinal', 'purpose',
            },
        )
        self.assertTrue(all(entry[4] for entry in expected_inventory))
        self.assertEqual(sorted(actual), sorted(expected))

    def test_sudo_inventory_detector_exposes_method_and_target(self):
        tree = ast.parse(
            "class Unsafe:\n"
            "    def bad(self):\n"
            "        return self.env['another.model'].sudo().search([])\n"
        )
        self.assertEqual(_sudo_sites_for_tree('unsafe.py', tree), [
            ('unsafe.py', 'bad', "self.env['another.model']", 1),
        ])

    def test_all_service_methods_decorated_with_api_model(self):
        # AST-based, matching the sudo guard's approach: proves the
        # decorator is actually present on each method definition, not
        # just mentioned somewhere in the file.
        target_methods = {
            'action_set_token',
            'action_replace_token',
            'action_clear_token',
            '_get_access_token',
        }
        credential_model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
            'shopify_connector_store_credential.py',
        )
        with open(credential_model_path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(
                source_file.read(), filename=credential_model_path
            )
        decorated_methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in target_methods:
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Attribute)
                        and decorator.attr == 'model'
                        and isinstance(decorator.value, ast.Name)
                        and decorator.value.id == 'api'
                    ):
                        decorated_methods.add(node.name)
        self.assertEqual(decorated_methods, target_methods)
