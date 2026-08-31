"""Dependency-free guards for the final inert V2/P16 activation boundary.

These tests encode the concrete blockers found by the independent UI and P15
reviews.  They do not claim browser or ORM qualification; they prevent those
known defects from silently returning before the real Odoo gates run.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"
MODELS = CORE / "models"
V2 = CORE / "static" / "src" / "v2"
P16 = CORE / "static" / "src" / "p16"

if "shopify_connector_core" not in sys.modules:
    package = types.ModuleType("shopify_connector_core")
    package.__path__ = [str(CORE)]
    package.__package__ = "shopify_connector_core"
    sys.modules["shopify_connector_core"] = package

from shopify_connector_core.domain.p15_foundation import command_request_fingerprint  # noqa: E402


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def method_source(path: Path, name: str) -> str:
    text = source(path)
    tree = ast.parse(text)
    node = next(
        item for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    )
    return ast.get_source_segment(text, node) or ""


class TestV2ActivationClosure(unittest.TestCase):
    def test_no_store_bootstrap_keeps_authorized_selector_and_single_store_path(self):
        controller = source(V2 / "connector_v2_action_controller.js")
        reads = source(V2 / "connector_v2_action_reads.js")
        template = source(V2 / "connector_v2_components.xml")
        self.assertIn("...selector", controller)
        self.assertIn("allowed_stores", controller)
        self.assertIn(
            "nextCompanyId === this.state.companyId",
            controller,
        )
        self.assertNotIn(
            "companyId === this.state.companyId && this.state.storeId",
            controller,
        )
        self.assertIn("_mergeStoreSelectorIntoOverview", reads)
        self.assertIn("allowed_actions: allowedActions", reads)
        self.assertIn(
            "!stores.length &amp;&amp; !hasAllStoresOption",
            template,
        )
        self.assertNotIn("stores.length &lt;= 1", template)

    def test_v2_advertises_only_an_executable_store_admin_target(self):
        support = source(MODELS / "shopify_connector_ui_facade_support.py")
        overview_method = method_source(
            MODELS / "shopify_connector_ui_facade_overview.py",
            "_overview_allowed_actions",
        )
        shared = source(CORE / "static" / "src" / "connector_shared_contracts.js")
        self.assertIn("action_shopify_connector_p16_admin", support)
        self.assertIn('"tag": "shopify_connector_p16_admin"', support)
        self.assertIn("_authorized_store_admin_target", overview_method)
        self.assertNotIn('key="create_store"', overview_method)
        self.assertIn('new Set(["shopify_connector_p16_admin"])', shared)
        self.assertIn('target.type === "ir.actions.client"', shared)

    def test_every_advertised_recovery_action_has_a_named_command_adapter(self):
        controller = source(V2 / "connector_v2_action_controller.js")
        recovery = source(V2 / "connector_v2_action_recovery.js")
        replay = source(MODELS / "shopify_connector_recovery_replay.py")
        job = source(MODELS / "shopify_connector_recovery_job.py")
        self.assertIn("installV2ActionRecoveryMethods", controller)
        self.assertIn("this.requestRecoveryAction(currentAction, item)", controller)
        for key in ("retry_job", "resolve_manual_review", "resolve_mutation"):
            self.assertIn(f'"{key}"', recovery)
        self.assertIn('const RECOVERY_COMMAND = "resolve_attention_v1"', recovery)
        for endpoint in (
            "resolve_attention_v1",
            "retry_job_v1",
            "cancel_job_v1",
        ):
            self.assertIn(
                f'@recovery_command_replay_endpoint("{endpoint}")',
                replay,
            )
        self.assertIn('"arguments are not accepted."', job)
        self.assertNotIn("uuid4", job)

    def test_setup_progress_is_server_sequential_and_semantic_values_are_editable(self):
        setup = source(MODELS / "shopify_connector_p15_setup_commands.py")
        controls = source(P16 / "shopify_connector_p16_setup_controls.js")
        template = source(P16 / "shopify_connector_p16.xml")
        commands = source(P16 / "shopify_connector_p16_admin_commands.js")
        self.assertIn("requested_ordinal > current_ordinal + 1", setup)
        for step in ("directions", "source_of_truth", "notification", "first_push"):
            self.assertIn(f"{step}:", controls)
        self.assertIn("P16SetupStepControls", template)
        self.assertIn("onSetupValueChange", template)
        self.assertIn("this.state.setupDraftValues[stepKey]", commands)

    def test_p16_command_authority_is_exact_and_lifecycle_guarded(self):
        admin = source(P16 / "shopify_connector_p16_admin.js")
        commands = source(P16 / "shopify_connector_p16_admin_commands.js")
        server = source(MODELS / "shopify_connector_p15_commands.py")
        setup = source(MODELS / "shopify_connector_p15_setup_commands.py")
        self.assertNotIn('hasServerAction(data, "manage_stores")', admin)
        exact = {
            "create_store_v1": "create_store",
            "save_setup_step_v1": "save_setup_step",
            "replace_credential_v1": "replace_credential",
            "test_connection_v1": "test_connection",
        }
        for command, action in exact.items():
            self.assertIn(f'{command}: ["{action}"]', commands)
        self.assertNotIn('["create_store", "manage_stores"]', commands)
        self.assertGreaterEqual(server.count('store.state in ("disconnecting", "disconnected")'), 2)
        self.assertIn('store.state in ("disconnecting", "disconnected")', setup)

    def test_all_store_selection_erases_the_prior_store_projection(self):
        controller = source(V2 / "connector_v2_action_controller.js")
        select_start = controller.index("async selectStore(store)")
        select_end = controller.index("async handleAction", select_start)
        block = controller[select_start:select_end]
        for fragment in (
            "store: null",
            "health: null",
            "workflows: []",
            "attention: null",
            "activity: null",
        ):
            self.assertIn(fragment, block)

    def test_paused_and_retired_states_dominate_workflow_health(self):
        p15 = method_source(
            MODELS / "shopify_connector_p15_ui.py",
            "_p15_store_list_workflows",
        )
        overview = source(MODELS / "shopify_connector_ui_facade_overview.py")
        self.assertIn('activation_state == "retired"', p15)
        self.assertIn('activation_state == "paused"', p15)
        self.assertIn("WorkflowReadiness.PAUSED.value", p15)
        self.assertIn("StoreActivationState.RETIRED.value", overview)
        self.assertIn("StoreActivationState.PAUSED.value", overview)

    def test_attention_filters_are_pushed_before_caps_or_report_partial(self):
        query = source(MODELS / "shopify_connector_ui_facade_attention_query.py")
        provider = method_source(
            MODELS / "shopify_connector_ui_facade_attention_query.py",
            "_attention_provider_records",
        )
        inventory = method_source(
            MODELS / "shopify_connector_ui_facade_attention_query.py",
            "_inventory_attentions",
        )
        self.assertIn("[*base_domain, *domain_extra]", provider)
        self.assertIn("limit=self.MAX_ATTENTION_ITEMS + 1", provider)
        self.assertIn("partial=capped", provider)
        self.assertIn('("shopify_gid", "=", location.shopify_location_gid)', inventory)
        self.assertIn('status["partial"] = True', inventory)
        self.assertIn('status["filter_pushed"] = bool(exact_filter)', inventory)
        self.assertIn('if status["truncated"]:', inventory)
        self.assertIn("provider_truncation", source(
            MODELS / "shopify_connector_ui_facade_attention.py"
        ))
        self.assertIn("class AttentionCollection", query)

    def test_run_projection_exposes_every_bounded_collection(self):
        run = source(MODELS / "shopify_connector_ui_facade_run.py")
        for key in ("jobs", "timeline", "logs", "affected_records", "limits"):
            self.assertIn(f'"{key}"', run)
        self.assertIn("MAX_TIMELINE_EVENTS + 1", run)
        self.assertIn("jobs_truncated or len(logs)", run)
        self.assertIn("affected_truncated or jobs_truncated", run)
        self.assertIn("Duplicate mutation evidence", run)

    def test_v2_recovery_requires_and_receives_configuration_generation(self):
        attention = source(MODELS / "shopify_connector_ui_facade_attention.py")
        recovery = source(MODELS / "shopify_connector_recovery_commands.py")
        client = source(V2 / "connector_v2_action_recovery.js")
        self.assertGreaterEqual(attention.count('"configuration_generation"'), 2)
        self.assertIn(
            "target.is_v2 and context.expected_configuration_generation is None",
            recovery,
        )
        self.assertIn("command.expected_configuration_generation = config", client)

    def test_command_replay_fingerprint_binds_expected_generation(self):
        values = dict(company_id=1, store_id=2, command_id="command-1", command_name="save", payload={"value": 3})
        self.assertNotEqual(
            command_request_fingerprint(**values, expected_generation=4),
            command_request_fingerprint(**values, expected_generation=5),
        )
        for invalid in (True, -1):
            with self.assertRaises(ValueError):
                command_request_fingerprint(**values, expected_generation=invalid)

    def test_every_replay_fingerprint_call_binds_the_envelope_generation(self):
        expected_calls = {
            MODELS / "shopify_connector_p15_command_replay.py": 2,
            MODELS / "shopify_connector_recovery_replay.py": 1,
        }
        for path, expected_count in expected_calls.items():
            calls = [
                node
                for node in ast.walk(ast.parse(source(path)))
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "command_request_fingerprint"
            ]
            self.assertEqual(len(calls), expected_count, path)
            for call in calls:
                keyword = next(
                    (item for item in call.keywords if item.arg == "expected_generation"),
                    None,
                )
                self.assertIsNotNone(keyword, path)
                self.assertIsInstance(keyword.value, ast.Attribute, path)
                self.assertEqual(keyword.value.attr, "expected_generation", path)
                self.assertIsInstance(keyword.value.value, ast.Name, path)
                self.assertEqual(keyword.value.value.id, "envelope", path)

    def test_p16_async_reads_drop_stale_or_unmounted_responses(self):
        admin = source(P16 / "shopify_connector_p16_admin.js")
        reads = source(P16 / "shopify_connector_p16_admin_reads.js")
        for fragment in ("this._disposed = true", "this._listRequestSerial", "this._surfaceRequestSerial"):
            self.assertIn(fragment, admin)
        for fragment in ("this._disposed", "requestCompanyId !== this.state.companyId", "requestSurface !== this.state.surface", "requestStoreId !== this.activeStoreId"):
            self.assertIn(fragment, reads)

    def test_p16_lifecycle_copy_distinguishes_activation_states(self):
        contract = source(P16 / "shopify_connector_p16_contract.js")
        components = source(P16 / "shopify_connector_p16_components.js")
        for state in ("draft", "active", "paused", "retired"):
            self.assertIn(f'{state}: _t("{state.title()}")', contract)
        self.assertIn("P16_ACTIVATION_COPY[value.activation_state]", components)
        self.assertIn("`${activation} · ${connection}`", components)
        self.assertIn("activation_state: store.activation", components)

    def test_bounded_attention_and_run_truth_reaches_the_browser(self):
        attention_query = source(
            MODELS / "shopify_connector_ui_facade_attention_query.py"
        )
        run_projection = source(MODELS / "shopify_connector_ui_facade_run.py")
        attention_client = source(V2 / "connector_v2_attention.js")
        run_client = source(V2 / "connector_v2_run.js")
        templates = source(V2 / "connector_v2_components.xml")
        self.assertIn(
            "if len(filtered) > self.MAX_ATTENTION_ITEMS:",
            attention_query,
        )
        self.assertNotIn("if affected_truncated:\n                break", run_projection)
        self.assertIn('"allowed_actions": actions_truncated', run_projection)
        self.assertIn("this.data.partial || this.data.truncated", attention_client)
        self.assertIn('if (this.incompleteProjection)', attention_client)
        self.assertIn("this.run.truncation", run_client)
        self.assertIn('t-if="incompleteProjection"', templates)
        self.assertIn('t-if="incompleteEvidence"', templates)

    def test_async_command_results_are_bound_to_the_originating_context(self):
        p16_admin = source(P16 / "shopify_connector_p16_admin.js")
        p16_commands = source(P16 / "shopify_connector_p16_admin_commands.js")
        v2_controller = source(V2 / "connector_v2_action_controller.js")
        v2_recovery = source(V2 / "connector_v2_action_recovery.js")
        for fragment in (
            "this._commandRequestSerial",
            "requestCompanyId === this.state.companyId",
            "requestSurface === this.state.surface",
            "requestStoreId === this.activeStoreId",
            "if (!requestIsCurrent())",
        ):
            self.assertIn(fragment, p16_admin)
        self.assertIn("commandAuthorityCandidates", p16_commands)
        self.assertNotIn("component.selectedItem,", p16_commands)
        self.assertIn("this._recoverySequence = 0", v2_controller)
        for fragment in (
            "request.navigationGeneration === this._navigationGeneration",
            "request.companyId === Number(this.state.companyId)",
            "request.storeId === positiveStoreId(this.state.storeId)",
            "this.state.view === V2_VIEWS.attention",
        ):
            self.assertIn(fragment, v2_recovery)

    def test_v2_recovery_dialog_and_uncertain_transport_are_fail_closed(self):
        controller = source(V2 / "connector_v2_action_controller.js")
        reads = source(V2 / "connector_v2_action_reads.js")
        recovery = source(V2 / "connector_v2_action_recovery.js")
        for fragment in (
            "this._attentionSelectionEpoch = 0",
            "this._recoveryUncertainContext = null",
            "clearNotice(force = false)",
            "this._recoveryInFlight || this._recoveryUncertainContext",
            "this._attentionSelectionEpoch += 1",
        ):
            self.assertIn(fragment, controller)
        for fragment in (
            "if (this._recoveryInFlight || this._recoveryUncertainContext)",
            "async _loadAttentionList",
            "async _loadAttentionDetail",
        ):
            self.assertIn(fragment, reads)
        for fragment in (
            "selectionEpoch: this._attentionSelectionEpoch",
            "itemFingerprint: recoveryItemFingerprint(itemSnapshot)",
            "actionFingerprint: stableSerialize(actionSnapshot)",
            "const currentItem = this._selectedAttentionItem();",
            "const currentAction = serverRecoveryAction(currentItem, action);",
            "recoveryItemFingerprint(item) !== recoveryItemFingerprint(currentItem)",
            "stableSerialize(candidate) === wantedFingerprint",
            "confirm: () => this._submitRecovery(context)",
            "context.command",
            "explicitRetry: true",
            "!this._recoveryContextIsCurrent(context)",
            "this._recoveryInFlight && this._activeRecoveryContext === context",
            "this._markRecoveryUncertain(context, failure.message)",
            "await this._loadAttentionList(null, { initial: true });",
            "const originalStatus = nonEmptyString(result.original_status).toLowerCase();",
            "status === \"duplicate\"",
            "this._requestSequence.attention += 1",
        ):
            self.assertIn(fragment, recovery)
        self.assertNotIn("_selectedAttentionItem(fallback", recovery)
        self.assertNotIn("serverAllowsAction(this.state.attention, action)", recovery)
        self.assertNotIn("detailRef: currentItem.item_ref", recovery)
        self.assertIn("this._recoverySequence += 1", controller)
        self.assertIn("Resolve the pending uncertain recovery command before navigating away", controller)

    def test_v2_final_ui_audit_guards_are_present(self):
        attention = source(V2 / "connector_v2_attention.js")
        overview = source(V2 / "connector_v2_overview.js")
        run = source(V2 / "connector_v2_run.js")
        controller = source(V2 / "connector_v2_action_controller.js")
        authority = source(V2 / "connector_v2_action_authority.js")
        recovery = source(V2 / "connector_v2_action_recovery.js")
        action_template = source(V2 / "connector_v2_action.xml")
        components = source(V2 / "connector_v2_components.xml")

        for fragment in (
            'const RECOVERY_ACTION_PREFERENCE = [',
            'actionFor(actions, RECOVERY_ACTION_PREFERENCE)',
            'const selectedRef = nonEmptyString(this.props.selectedItemRef);',
            'detail && nonEmptyString(detail.item_ref) === selectedRef',
        ):
            self.assertIn(fragment, attention)
        for fragment in (
            'get attentionIncomplete()',
            'attention.partial || attention.truncated',
            't-if="!attentionItems.length &amp;&amp; attentionIncomplete"',
        ):
            self.assertIn(fragment, overview + components)
        for fragment in (
            'const RECOVERY_ACTION_KEYS = new Set([',
            'RECOVERY_ACTION_KEYS.has(candidate && candidate.key)',
            'return records.filter((record) => this._recordActionIsCurrent(record));',
            '_recordActionIsCurrent(record)',
            'stableSerialize(candidate) === stableSerialize(action)',
        ):
            self.assertIn(fragment, run)
        for fragment in (
            '_currentActionAuthority(action, item = null)',
            'stableSerialize(candidate) === wanted',
        ):
            self.assertIn(fragment, authority)
        for fragment in (
            'A recovery decision is being submitted; wait for its result before navigating away.',
            'this._requestSequence.attention += 1;',
        ):
            self.assertIn(fragment, controller)
        self.assertIn('t-on-click="() => this.clearNotice()"', action_template)
        for fragment in (
            'function recoveryItemFingerprint(item)',
            'request.itemFingerprint === recoveryItemFingerprint(currentItem)',
            'itemFingerprint: recoveryItemFingerprint(itemSnapshot)',
            'const originalStatus = nonEmptyString(result.original_status).toLowerCase();',
            'const definitiveRejection =',
            'if (!isRecord(result))',
            'if (!isAuthoritativeRpcRejection(error))',
            'this._schedulePoll();',
        ):
            self.assertIn(fragment, recovery)

    def test_v2_attention_selection_epoch_and_run_native_authority_are_bound(self):
        reads = source(V2 / "connector_v2_action_reads.js")
        controller = source(V2 / "connector_v2_action_controller.js")
        attention = source(V2 / "connector_v2_attention.js")
        action_contracts = source(V2 / "connector_v2_action_contracts.js")
        authority = source(V2 / "connector_v2_action_authority.js")
        run = source(V2 / "connector_v2_run.js")
        run_projection = source(MODELS / "shopify_connector_ui_facade_run.py")
        polling = source(V2 / "connector_v2_action_polling.js")

        for fragment in (
            "selectionEpoch = this._attentionSelectionEpoch",
            "this._attentionSelectionEpoch !== selectionEpoch",
            "_loadAttentionDetail(detailRef, generation, selectionEpoch)",
            "async _loadAttentionDetail(",
            "selectionEpoch = this._attentionSelectionEpoch",
            "() => this._loadAttentionDetail(ref, generation, selectionEpoch)",
        ):
            self.assertIn(fragment, reads)
        open_start = controller.index("async openAttention")
        clear_poll = controller.index("this._clearPoll();", open_start)
        epoch = controller.index("this._attentionSelectionEpoch += 1;", open_start)
        self.assertLess(clear_poll, epoch)
        for fragment in (
            "const selectionEpoch = this._attentionSelectionEpoch",
            "selectionEpoch,",
            "this.state.selectedItemRef || responseData(this.state.attention).detail",
        ):
            self.assertIn(fragment, controller)
        for fragment in (
            "const pollGeneration = this._navigationGeneration",
            "const pollSelectionEpoch = this._attentionSelectionEpoch",
            "pollSelectionEpoch === this._attentionSelectionEpoch",
            "const scheduledGeneration = this._navigationGeneration",
            "scheduledSelectionEpoch !== this._attentionSelectionEpoch",
        ):
            self.assertIn(fragment, polling)
        for fragment in (
            "Boolean(this.data.next_cursor) && !this.hasDetail",
            "this.data.next_cursor && !this.hasDetail",
        ):
            self.assertIn(fragment, attention)
        self.assertIn("nativeActionMatches(candidate, wanted)", action_contracts)
        self.assertIn("nativeActionMatches(candidate, action)", authority)
        self.assertIn("nativeActionMatches(candidate, action)", run)
        for fragment in (
            "for record in self._affected_record(job):",
            'key=action_key,',
            'target=target,',
            'label=_("Open affected record")',
        ):
            self.assertIn(fragment, run_projection)

    def test_p16_context_epoch_invalidates_navigation_company_and_unmount(self):
        admin = source(P16 / "shopify_connector_p16_admin.js")
        navigation = source(P16 / "shopify_connector_p16_admin_navigation.js")
        reads = source(P16 / "shopify_connector_p16_admin_reads.js")
        self.assertIn("this._contextEpoch = 0", admin)
        self.assertIn("this._invalidateContext();", admin)
        self.assertIn("this._contextEpoch += 1", admin)
        self.assertIn("this._listRequestSerial += 1", admin)
        self.assertIn("this._surfaceRequestSerial += 1", admin)
        self.assertIn("this._commandRequestSerial += 1", admin)
        company_invalidation = admin.index("this._invalidateContext();", admin.index("async revalidateCompanyContext"))
        company_assignment = admin.index("this.state.companyId = nextCompanyId", company_invalidation)
        self.assertLess(company_invalidation, company_assignment)
        self.assertIn("this._invalidateContext();\n            this._setSurface(P16_SURFACES.LIST)", navigation)
        self.assertIn("this._contextSnapshot", reads)
        self.assertIn("!this._contextIsCurrent(requestContext)", reads)

    def test_p16_authority_is_current_success_envelope_and_missing_store_fails_closed(self):
        admin = source(P16 / "shopify_connector_p16_admin.js")
        commands = source(P16 / "shopify_connector_p16_admin_commands.js")
        self.assertIn("normalizeEnvelope(envelope, \"loading\")", commands)
        self.assertIn('component.state[stateKey] !== "success"', commands)
        self.assertIn("commandName !== \"create_store_v1\" && !storeId", commands)
        self.assertIn("!authorityStoreId(candidate)", commands)
        self.assertNotIn("component.selectedItem", commands)
        self.assertIn("A cached list item is not a generation authority", admin)
        self.assertIn("[P16_SURFACES.DIAGNOSTICS]: this.state.diagnosticsEnvelope", admin)

    def test_p16_lifecycle_confirmation_captures_exact_context_and_generation(self):
        commands = source(P16 / "shopify_connector_p16_admin_commands.js")
        self.assertIn("const requestContext = this._contextSnapshot();", commands)
        self.assertIn("const requestGeneration = connectionGeneration(", commands)
        self.assertIn("requestContext,\n                    requestGeneration", commands)
        self.assertIn("if (requestContext && !this._contextIsCurrent(requestContext))", commands)
        self.assertIn("context: requestContext", commands)
        self.assertIn("this._contextIsCurrent(requestContext)", commands)

    def test_p16_commands_invalidate_serial_at_entry_and_recheck_after_rpc(self):
        admin = source(P16 / "shopify_connector_p16_admin.js")
        commands = source(P16 / "shopify_connector_p16_admin_commands.js")
        serial = admin.index("const requestSerial = ++this._commandRequestSerial;")
        disposed = admin.index("if (this._disposed)", serial)
        self.assertLess(serial, disposed)
        for block in (
            "saveSetupStep",
            "replaceCredential",
            "testConnection",
            "activate",
        ):
            start = commands.index(f"async {block}")
            end = commands.find("\n        async ", start + 1)
            section = commands[start:] if end < 0 else commands[start:end]
            self.assertIn("this._contextIsCurrent(requestContext)", section, block)
        settings = source(P16 / "shopify_connector_p16_admin_reads.js")
        start = settings.index("async saveSettingsGroup")
        self.assertIn("this._contextIsCurrent(requestContext)", settings[start:])


if __name__ == "__main__":
    unittest.main()
