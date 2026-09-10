/** @odoo-module **/

/*
 * P03/P04 Odoo client-action controller.
 *
 * The controller owns one local screen state and bounded read lifecycle. It
 * talks only to the named application facade methods and delegates native
 * navigation to Odoo's action service. It does not own a router, global store,
 * Shopify transport, or direct business-model call.
 */

import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import {
    AttentionWorkspace,
    Overview,
    RunTimeline,
} from "@shopify_connector_core/v2/connector_v2_components";
import {
    ACTION_SERVICE_KEYS,
    ROLE_LABELS,
    V2_VIEWS,
    initialStoreId,
    initialStoreName,
    isRecord,
    localeDirection,
    makeEnvelope,
    normalizeRpcError,
    nonEmptyString,
    positiveStoreId,
    responseData,
    responseFingerprint,
    serverActionTarget,
} from "./connector_v2_action_contracts";
import { installV2ActionAuthorityMethods } from "./connector_v2_action_authority";
import { installV2ActionPollingMethods } from "./connector_v2_action_polling";
import { installV2ActionReadMethods } from "./connector_v2_action_reads";
import { installV2ActionRecoveryMethods } from "./connector_v2_action_recovery";
import {
    companyIdFromProps,
    isReadOnlyAllStores,
    recordAction,
} from "../connector_shared_contracts";

export class ShopifyConnectorV2Action extends Component {
    static template = "shopify_connector_core.v2.ActionShell";
    static components = { AttentionWorkspace, Overview, RunTimeline };
    // Client actions receive framework-owned props (`action`, `className`,
    // and optional context values) that vary by Odoo entry point.
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.user = useService("user");
        this.direction = localeDirection();
        this.shellRef = useRef("shell");

        this.state = useState({
            view: V2_VIEWS.overview,
            storeId: initialStoreId(this.props),
            storeName: initialStoreName(this.props),
            storeKind: "store",
            companyId: companyIdFromProps(this.props) || this._activeCompanyId(),
            selectedItemRef: null,
            runRef: null,
            overview: makeEnvelope("loading"),
            stores: makeEnvelope("loading"),
            attention: makeEnvelope("loading"),
            run: makeEnvelope("loading"),
            notice: null,
            role: "",
        });

        this._mounted = false;
        this._unmounted = false;
        this._pollTimer = null;
        this._pollInFlight = false;
        this._requestSequence = { overview: 0, stores: 0, attention: 0, run: 0 };
        this._recoverySequence = 0;
        this._attentionSelectionEpoch = 0;
        this._activeRecoveryContext = null;
        this._recoveryInFlight = false;
        this._recoveryUncertainContext = null;
        this._navigationGeneration = 0;
        this._attentionTrigger = null;
        this._focusDetailAfterSelection = false;
        this._focusRowAfterBack = false;
        this._retryNotice = null;
        this._onVisibilityChange = this._onVisibilityChange.bind(this);
        this._onCompanyContextChanged = this._onCompanyContextChanged.bind(this);

        onWillStart(async () => {
            await this._loadStores({ initial: true });
            if (this.state.storeId && this._storeIsAllowed(this.state.storeId)) {
                await this._loadOverview(this.state.storeId, { initial: true });
            } else {
                this.state.storeId = null;
                const selector = responseData(this.state.overview);
                this._commit(
                    "overview",
                    makeEnvelope(
                        "unconfigured",
                        {
                            // Keep the server-authorized selector and global
                            // actions returned by the bootstrap store read.
                            // A zero-store response is still actionable: the
                            // subordinate administrator surface can offer its
                            // named create-store command when authorized.
                            ...selector,
                            store: null,
                            health: null,
                            workflows: [],
                            attention: null,
                            activity: null,
                        },
                        _t("Open a permitted Shopify store to begin connector work.")
                    )
                );
            }
        });

        onMounted(() => {
            this._mounted = true;
            document.addEventListener("visibilitychange", this._onVisibilityChange);
            this._registerCompanyContextHook();
            this._schedulePoll();
        });

        onWillUnmount(() => {
            this._mounted = false;
            this._unmounted = true;
            this._navigationGeneration += 1;
            this._attentionSelectionEpoch += 1;
            this._recoverySequence += 1;
            this._activeRecoveryContext = null;
            this._recoveryInFlight = false;
            this._recoveryUncertainContext = null;
            this._retryNotice = null;
            document.removeEventListener("visibilitychange", this._onVisibilityChange);
            this._unregisterCompanyContextHook();
            this._clearPoll();
        });

        // Focus is moved only after the server accepted a selection. The shell
        // owns this transition because the presentation component is inert.
        useEffect(
            () => {
                this._restoreAttentionFocus();
            },
            () => [
                this.state.view,
                this.state.selectedItemRef,
                responseFingerprint(this.state.attention),
            ]
        );
    }

    get roleLabel() {
        return ROLE_LABELS[this.state.role] || "";
    }

    get activeStoreName() {
        const overviewStore = responseData(this.state.overview).store;
        return this.state.storeName || (isRecord(overviewStore) ? overviewStore.name : "");
    }

    get hasRun() {
        return Boolean(this.state.runRef);
    }

    _activeCompanyId() {
        const company = this.env && this.env.services && this.env.services.company;
        const current = company && company.currentCompany;
        return Number(current && current.id) || companyIdFromProps(this.props) || null;
    }

    _registerCompanyContextHook() {
        const service = this.env && this.env.services && this.env.services.company;
        if (service && typeof service.addEventListener === "function") {
            service.addEventListener("change", this._onCompanyContextChanged);
            this._companyContextEventTarget = service;
        } else if (service && typeof service.on === "function") {
            service.on("change", this, this._onCompanyContextChanged);
        }
    }

    _unregisterCompanyContextHook() {
        const service = this.env && this.env.services && this.env.services.company;
        if (this._companyContextEventTarget) {
            this._companyContextEventTarget.removeEventListener("change", this._onCompanyContextChanged);
            this._companyContextEventTarget = null;
        } else if (service && typeof service.off === "function") {
            service.off("change", this, this._onCompanyContextChanged);
        }
    }

    _onCompanyContextChanged(companyId) {
        const nextCompanyId =
            Number(companyId && companyId.id ? companyId.id : companyId) || this._activeCompanyId();
        if (nextCompanyId === this.state.companyId) {
            return;
        }
        this.revalidateCompanyContext(nextCompanyId);
    }

    /** Public host seam; changing company invalidates the selected store. */
    revalidateCompanyContext(companyId = this._activeCompanyId()) {
        const nextCompanyId = Number(companyId) || null;
        // Selecting the first permitted store is valid even though no store is
        // selected yet.  Company equality, not the presence of a prior store,
        // is the scope fence.  The company-change hook deliberately does not
        // overwrite state.companyId before reaching this comparison.
        if (nextCompanyId && nextCompanyId === this.state.companyId) {
            return true;
        }
        this.state.companyId = nextCompanyId;
        this._navigationGeneration += 1;
        this._clearPoll();
        this.state.storeId = null;
        this.state.storeKind = "store";
        this.state.storeName = "";
        this.state.selectedItemRef = null;
        this.state.runRef = null;
        this.state.view = V2_VIEWS.overview;
        this._attentionSelectionEpoch += 1;
        this._recoverySequence += 1;
        this._activeRecoveryContext = null;
        this._recoveryInFlight = false;
        this._recoveryUncertainContext = null;
        this.clearNotice(true);
        this._commit(
            "overview",
            makeEnvelope(
                "permission_empty",
                {},
                _t("The active company changed. Select a permitted store again."),
            ),
        );
        this._setNotice(_t("The selected store was cleared after the company changed."));
        void this._loadStores({ initial: true });
        return false;
    }

    _setRoleFromEnvelope(envelope) {
        const permissions = responseData(envelope).permissions;
        const role = isRecord(permissions) ? nonEmptyString(permissions.role) : "";
        this.state.role = role;
    }

    _commit(slot, envelope) {
        const current = this.state[slot];
        if (responseFingerprint(current) !== responseFingerprint(envelope)) {
            this.state[slot] = envelope;
        }
        if (slot === "overview") {
            this._setRoleFromEnvelope(envelope);
            const store = responseData(envelope).store;
            if (isRecord(store) && positiveStoreId(store.id) === this.state.storeId) {
                this.state.storeName = nonEmptyString(store.name) || this.state.storeName;
            }
        }
    }

    _storeIsAllowed(storeId) {
        const normalized = positiveStoreId(storeId);
        if (!normalized) {
            return false;
        }
        const overviewStores = responseData(this.state.overview).allowed_stores;
        if (Array.isArray(overviewStores)) {
            return overviewStores.some((item) => {
                const store = isRecord(item && item.store) ? item.store : item;
                return positiveStoreId(store && store.id) === normalized;
            });
        }
        const listStores = responseData(this.state.stores).stores;
        return Array.isArray(listStores) && listStores.some((item) => {
            const store = isRecord(item && item.store) ? item.store : item;
            return positiveStoreId(store && store.id) === normalized;
        });
    }

    _setNotice(message, retry = null) {
        this._retryNotice = typeof retry === "function" ? retry : null;
        this.state.notice = {
            message:
                nonEmptyString(message) || _t("The requested connector action is not available."),
            retry: Boolean(this._retryNotice),
        };
    }

    clearNotice(force = false) {
        // An uncertain command must remain actionable until the exact same
        // envelope is explicitly retried or the component is gone.  In
        // particular, navigation and a render refresh must not discard its
        // retry path and accidentally resume polling.
        const explicitForce = force === true;
        if (this._recoveryUncertainContext && !explicitForce) {
            return;
        }
        this._retryNotice = null;
        this.state.notice = null;
    }

    async retryNotice() {
        const retry = this._retryNotice;
        this.clearNotice(true);
        if (retry) {
            await retry();
        }
    }

    _navigate(view) {
        if (!Object.values(V2_VIEWS).includes(view)) {
            return false;
        }
        if (this._recoveryUncertainContext) {
            this._setNotice(
                _t("Resolve the pending uncertain recovery command before navigating away."),
                () => this._retryUncertainRecovery(this._recoveryUncertainContext),
            );
            return false;
        }
        if (this._recoveryInFlight) {
            this._setNotice(_t("A recovery decision is being submitted; wait for its result before navigating away."));
            return false;
        }
        if (this.state.view === view) {
            return true;
        }
        this._navigationGeneration += 1;
        this._clearPoll();
        this.clearNotice();
        this.state.view = view;
        if (view !== V2_VIEWS.attention) {
            this.state.selectedItemRef = null;
            this._focusDetailAfterSelection = false;
            this._focusRowAfterBack = false;
        }
        if (view !== V2_VIEWS.run) {
            this.state.runRef = null;
        }
        return true;
    }

    async openOverview() {
        if (!this._navigate(V2_VIEWS.overview)) {
            return;
        }
        if (this.state.storeId) {
            await this._loadOverview(this.state.storeId, { initial: true });
        }
        this._schedulePoll();
    }

    async openAttention(item = null) {
        if (this._recoveryUncertainContext) {
            this._setNotice(
                _t("Resolve the pending uncertain recovery command before selecting another item."),
                () => this._retryUncertainRecovery(this._recoveryUncertainContext),
            );
            return;
        }
        if (this._recoveryInFlight) {
            this._setNotice(_t("A recovery decision is being submitted; wait for its result before selecting another item."));
            return;
        }
        if (this.state.storeKind === "all") {
            this._setNotice(_t("All stores is a read-only summary; select one store to review evidence."));
            return;
        }
        // A timer can already have queued an attention poll while this
        // selection is being opened.  Clearing it prevents a new list read
        // from being scheduled behind the detail request; the selection epoch
        // below also fences an already-running poll that cannot be cancelled.
        this._clearPoll();
        // This is a selection intent even when the selected item is the same
        // row as before.  The epoch therefore handles A→B→A while a dialog or
        // an async recovery request is still open.
        this._attentionSelectionEpoch += 1;
        const selectionEpoch = this._attentionSelectionEpoch;
        this._captureAttentionTrigger();
        const itemRef = isRecord(item) ? nonEmptyString(item.item_ref) : nonEmptyString(item);
        if (!this._navigate(V2_VIEWS.attention)) {
            return;
        }
        this.state.selectedItemRef = null;
        this._focusDetailAfterSelection = Boolean(itemRef);
        this._commit("attention", makeEnvelope("loading"));
        await this._loadAttentionList(null, {
            detailRef: itemRef || null,
            selectionEpoch,
        });
        this._schedulePoll();
    }

    async openRun(runRef) {
        if (this.state.storeKind === "all") {
            this._setNotice(_t("All stores is a read-only summary; select one store to open run evidence."));
            return;
        }
        const ref = nonEmptyString(runRef);
        if (!ref) {
            this._setNotice(_t("No run evidence reference was returned."));
            return;
        }
        if (!this._navigate(V2_VIEWS.run)) {
            return;
        }
        this.state.runRef = ref;
        this._commit("run", makeEnvelope("loading"));
        await this._loadRun(ref, { initial: true });
        this._schedulePoll();
    }

    openRuns() {
        if (!this._navigate(V2_VIEWS.run)) {
            return;
        }
        this.state.runRef = null;
        this._commit(
            "run",
            makeEnvelope(
                "unconfigured",
                {},
                _t("Select a run from a workflow or attention item to review its evidence."),
            ),
        );
    }

    openUnavailable(surface) {
        const messages = {
            Products: _t("Products is not available from the current server contract. No request was made."),
            Orders: _t("Orders is not available from the current server contract. No request was made."),
            Inventory: _t("Inventory is not available from the current server contract. No request was made."),
            Fulfillment: _t("Fulfillment is not available from the current server contract. No request was made."),
            Settings: _t("Settings is not available from the current server contract. No request was made."),
        };
        this._setNotice(messages[nonEmptyString(surface)] || _t("This surface is unavailable. No request was made."));
    }

    async selectStore(store) {
        if (this._recoveryUncertainContext) {
            this._setNotice(
                _t("Resolve the pending uncertain recovery command before changing stores."),
                () => this._retryUncertainRecovery(this._recoveryUncertainContext),
            );
            return;
        }
        if (this._recoveryInFlight) {
            this._setNotice(_t("A recovery decision is being submitted; wait for its result before changing stores."));
            return;
        }
        if (!this.revalidateCompanyContext()) {
            return;
        }
        if (isReadOnlyAllStores(store)) {
            this._navigationGeneration += 1;
            this._clearPoll();
            this.clearNotice();
            this.state.storeId = null;
            this.state.storeKind = "all";
            this.state.storeName = _t("All stores");
            this.state.view = V2_VIEWS.overview;
            this.state.selectedItemRef = null;
            this.state.runRef = null;
            // All-stores is a selector state, not a store read.  Do not leave
            // the previously selected store's health/workflow/evidence
            // projection rendered beneath the all-store notice.
            const existing = responseData(this.state.overview);
            this._commit(
                "overview",
                makeEnvelope(
                    "unconfigured",
                    {
                        allowed_stores: Array.isArray(existing.allowed_stores)
                            ? existing.allowed_stores
                            : responseData(this.state.stores).stores || [],
                        all_stores: {
                            allowed: true,
                            read_only: true,
                            selected: true,
                        },
                        allowed_actions: Array.isArray(existing.allowed_actions)
                            ? existing.allowed_actions
                            : [],
                        permissions: existing.permissions || {},
                        store: null,
                        health: null,
                        workflows: [],
                        attention: null,
                        activity: null,
                    },
                    _t("The all-store summary is read-only and is not available in this bounded release."),
                ),
            );
            return;
        }
        const storeId = positiveStoreId(store && store.id);
        if (!storeId || !this._storeIsAllowed(storeId)) {
            this._setNotice(_t("The selected store is not available to this role."));
            return;
        }
        this._navigationGeneration += 1;
        this._clearPoll();
        this.clearNotice();
        this.state.storeId = storeId;
        this.state.storeKind = "store";
        this.state.storeName = nonEmptyString(store.name);
        this.state.view = V2_VIEWS.overview;
        this.state.selectedItemRef = null;
        this.state.runRef = null;
        this._commit("overview", makeEnvelope("loading"));
        await this._loadOverview(storeId, { initial: true });
        this._schedulePoll();
    }

    async nextAttentionPage(cursor) {
        if (this._recoveryInFlight || this._recoveryUncertainContext) {
            return;
        }
        // A paginated list response has no detail projection.  Loading it
        // while a detail is open would therefore erase the selected evidence
        // from the single attention envelope.  Keep pagination a list-only
        // operation; the component also hides this control while selected.
        if (this.state.selectedItemRef || responseData(this.state.attention).detail) {
            this._setNotice(_t("Return to the attention list before loading another page."));
            return;
        }
        if (nonEmptyString(cursor)) {
            await this._loadAttentionList(cursor);
        }
        this._schedulePoll();
    }

    async backToAttention() {
        if (this._recoveryUncertainContext) {
            return;
        }
        if (this._recoveryInFlight) {
            this._setNotice(_t("A recovery decision is being submitted; wait for its result before returning to the attention list."));
            return;
        }
        // Invalidate both list and detail reads.  Otherwise a detail response
        // already in flight can repaint the panel after the user pressed Back.
        this._requestSequence.attention += 1;
        this._attentionSelectionEpoch += 1;
        this._focusRowAfterBack = true;
        const data = responseData(this.state.attention);
        const next = { ...data };
        delete next.detail;
        this.state.selectedItemRef = null;
        this._commit("attention", { ...this.state.attention, data: next });
        this.clearNotice();
    }

    async refreshCurrent() {
        if (this._recoveryInFlight || this._recoveryUncertainContext) {
            return;
        }
        this.clearNotice();
        await this._pollCurrent();
    }

    async openWorkflow(workflow) {
        if (this.state.storeKind === "all") {
            this._setNotice(_t("Select one store before opening workflow evidence."));
            return;
        }
        if (isRecord(workflow) && nonEmptyString(workflow.latest_run_ref)) {
            await this.openRun(workflow.latest_run_ref);
            return;
        }
        if (isRecord(workflow) && Number(workflow.attention_count) > 0) {
            await this.openAttention();
            return;
        }
        this._setNotice(_t("This workflow has no run evidence yet."));
    }

    async openRecord(record) {
        const action = recordAction(record);
        const target = action && serverActionTarget(action);
        if (!target) {
            this._setNotice(
                _t("A server-built Odoo record action is not available for this evidence.")
            );
            return;
        }
        const currentAction = this._currentActionAuthority(action, record);
        if (!currentAction) {
            this._setNotice(_t("This record action is no longer allowed by the server."));
            return;
        }
        await this._doServerAction(currentAction);
    }

    async handleAction(action, item = null) {
        const currentAction = this._currentActionAuthority(action, item);
        if (!currentAction) {
            this._setNotice(_t("This action is no longer allowed by the server."));
            return;
        }
        const key = nonEmptyString(currentAction.key);
        if (key === "open_attention") {
            await this.openAttention(currentAction.item_ref || null);
            return;
        }
        if (key === "open_run") {
            await this.openRun(currentAction.item_ref || null);
            return;
        }
        if (key === "refresh") {
            await this.refreshCurrent();
            return;
        }
        if (key === "retry_job" || key === "resolve_manual_review" || key === "resolve_mutation") {
            this.requestRecoveryAction(currentAction, item);
            return;
        }
        if (ACTION_SERVICE_KEYS.has(key)) {
            await this._doServerAction(currentAction);
            return;
        }
        this._setNotice(_t("This recovery action is not wired to a command in the current facade."));
    }

    async _doServerAction(action) {
        const target = serverActionTarget(action);
        if (!target) {
            this._setNotice(_t("The server did not return a safe native action target."));
            return;
        }
        try {
            await this.action.doAction(target);
        } catch (error) {
            const failure = normalizeRpcError(error);
            this._setNotice(failure.message, null);
        }
    }

    _captureAttentionTrigger() {
        const active = document.activeElement;
        if (active && this.shellRef.el && this.shellRef.el.contains(active)) {
            this._attentionTrigger = active;
        }
    }

    _restoreAttentionFocus() {
        if (!this._mounted || !this.shellRef.el || this.state.view !== V2_VIEWS.attention) {
            return;
        }
        if (this._focusDetailAfterSelection && this.state.selectedItemRef) {
            const detail = this.shellRef.el.querySelector(
                ".sc-v2-attention__detail[tabindex='-1']"
            );
            if (detail) {
                detail.focus();
                this._focusDetailAfterSelection = false;
            }
        }
        if (this._focusRowAfterBack && !this.state.selectedItemRef) {
            const trigger = this._attentionTrigger;
            if (trigger && trigger.isConnected && this.shellRef.el.contains(trigger)) {
                trigger.focus();
            } else {
                const firstRow = this.shellRef.el.querySelector(".sc-v2-attention-row");
                if (firstRow) {
                    firstRow.focus();
                }
            }
            this._focusRowAfterBack = false;
        }
    }

}

installV2ActionReadMethods(ShopifyConnectorV2Action);
installV2ActionRecoveryMethods(ShopifyConnectorV2Action);
installV2ActionAuthorityMethods(ShopifyConnectorV2Action);
installV2ActionPollingMethods(ShopifyConnectorV2Action);

registry.category("actions").add("shopify_connector_v2", ShopifyConnectorV2Action);
