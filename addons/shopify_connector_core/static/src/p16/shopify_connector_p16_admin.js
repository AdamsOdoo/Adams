/** @odoo-module **/
/*
 * P16 Administrator/multistore shell.
 *
 * The shell is intentionally thin: Manage Stores is a bounded P15 read, and
 * every detail surface is one named P15 read.  Commands are built only at the
 * moment of submit and the server reauthorizes/revalidates every one.  This
 * file never calls a Shopify endpoint, reads a credential, or keeps a global
 * client-side store.  It is not asset-wired until the W2 compatibility gate.
 * The bounded "get_store_list_v1" read lives in the adjacent read mixin; this
 * file retains only the subordinate surface coordinator and command seam.
 * Named commands such as "save_store_settings_group_v1" and
 * "replace_credential_v1" remain in the coordinator's fail-closed command
 * vocabulary; no command is synthesized when the server omits its action.
 */
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import {
    P16_APPLICATION_MODEL,
    P16_DETAIL_METHODS,
    P16_STORE_LIST_LIMIT,
    P16_SURFACES,
    asArray,
    asObject,
    commandEnvelope,
    connectionGeneration,
    findStoreItem,
    hasServerAction,
    nextSetupStep,
    normalizeEnvelope,
    phaseForStep,
    safeErrorMessage,
    serverActions,
    settingsGeneration,
    storeFromItem,
    storeItems,
} from "@shopify_connector_core/p16/shopify_connector_p16_contract";
import { companyIdFromProps } from "../connector_shared_contracts";
import {
    P16Components,
} from "@shopify_connector_core/p16/shopify_connector_p16_components";
import { installP16AdminReadMethods } from "./shopify_connector_p16_admin_reads";
import { installP16AdminNavigationMethods } from "./shopify_connector_p16_admin_navigation";
import {
    commandIsAdvertised,
    installP16AdminCommandMethods,
    P16_LIFECYCLE_COMMANDS,
} from "./shopify_connector_p16_admin_commands";
function localeDirection() {
    try {
        return localization.direction || "ltr";
    } catch {
        return "ltr";
    }
}
let nextP16InstanceId = 1;
export class ShopifyConnectorP16Admin extends Component {
    // P16 is a subordinate V2 administrator/settings surface, not a second
    // connector application root.
    static template = "shopify_connector_core.P16Admin";
    static props = { "*": true };
    static components = P16Components;
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.user = useService("user");
        this.direction = localeDirection();
        this.instanceId = `p16-admin-${nextP16InstanceId++}`;
        this._mounted = false;
        this._disposed = false;
        // One monotonic epoch represents the visible company/store/navigation
        // context.  Request serials still distinguish two reads in the same
        // context; the epoch invalidates every in-flight operation when that
        // context changes (including unmount).
        this._contextEpoch = 0;
        this._listRequestSerial = 0;
        this._surfaceRequestSerial = 0;
        this._commandRequestSerial = 0;
        this._onCompanyContextChanged = this._onCompanyContextChanged.bind(this);
        this.state = useState({
            surface: this._initialSurface(),
            listState: "loading",
            listEnvelope: null,
            search: "",
            selectedStoreId: null,
            companyId: companyIdFromProps(this.props) || this.activeCompanyId,
            setupState: "idle",
            setupEnvelope: null,
            setupStepKey: null,
            setupDraftValues: {},
            readinessState: "idle",
            readinessEnvelope: null,
            settingsState: "idle",
            settingsEnvelope: null,
            settingsDrafts: {},
            diagnosticsState: "idle",
            diagnosticsEnvelope: null,
            commandState: "idle",
            commandMessage: "",
            surfaceMessage: "",
            createName: "",
            createDomain: "",
        });
        onWillStart(async () => {
            await this.loadStores();
            const contextStoreId = this._contextStoreId();
            if (contextStoreId && this._knownStore(contextStoreId)) {
                this._setSelectedStore(contextStoreId);
            }
            await this._loadInitialSurface();
        });
        onMounted(() => {
            this._mounted = true;
            this._registerCompanyContextHook();
        });
        onWillUnmount(() => {
            this._disposed = true;
            this._mounted = false;
            this._invalidateContext();
            this._unregisterCompanyContextHook();
        });
    }

    _invalidateContext() {
        this._contextEpoch += 1;
        // Invalidate each independent async channel as well as the shared
        // epoch.  This makes the guard robust even for a caller that only
        // checks its channel serial (and makes unmount fail closed).
        this._listRequestSerial += 1;
        this._surfaceRequestSerial += 1;
        this._commandRequestSerial += 1;
        if (!this._disposed && this.state) {
            this.state.commandState = "idle";
            this.state.commandMessage = "";
        }
        return this._contextEpoch;
    }

    _contextSnapshot({
        companyId = this.state.companyId,
        storeId = this.activeStoreId,
        surface = this.state.surface,
    } = {}) {
        return Object.freeze({
            epoch: this._contextEpoch,
            companyId: Number(companyId) || null,
            storeId: storeId === null || storeId === undefined
                ? null
                : Number(storeId) || null,
            surface,
        });
    }

    _contextIsCurrent(context) {
        if (!context || this._disposed) {
            return false;
        }
        return context.epoch === this._contextEpoch &&
            context.companyId === (Number(this.state.companyId) || null) &&
            context.surface === this.state.surface &&
            (context.storeId === null || context.storeId === this.activeStoreId);
    }

    _setSurface(surface) {
        if (this.state.surface !== surface) {
            this._invalidateContext();
        }
        this.state.surface = surface;
    }

    get pageTitleId() {
        return `${this.instanceId}-page-title`;
    }

    get createTitleId() {
        return `${this.instanceId}-create-title`;
    }

    get setupTitleId() {
        return `${this.instanceId}-setup-title`;
    }
    get appDirection() {
        return this.direction;
    }
    get listItems() {
        return storeItems(this.state.listEnvelope);
    }
    get selectedItem() {
        return findStoreItem(this.listItems, this.state.selectedStoreId);
    }
    get selectedStore() {
        return storeFromItem(this.selectedItem) || {};
    }

    get selectedStoreName() {
        return this.selectedStore.name || _t("No store selected");
    }

    get canManageSelected() {
        // Server-returned actions are a presentation hint only.  P15 still
        // checks role/company/store on every named read and command.
        return hasServerAction(this.selectedItem, "open_setup") || hasServerAction(
            this.selectedItem,
            "open_store_settings",
        );
    }

    get canShowAddStore() {
        const data = asObject(this.state.listEnvelope && this.state.listEnvelope.data);
        // Creation is visible only when the server explicitly returns the
        // capability.  An empty list is not authorization evidence.
        return Boolean(
            data.can_create_store === true ||
                hasServerAction(data, "create_store"),
        );
    }

    get nativeManageAction() {
        return serverActions(
            this.state.listEnvelope && this.state.listEnvelope.data,
        ).find((action) => action.key === "manage_stores") || null;
    }

    get setup() {
        return asObject(this.state.setupEnvelope && this.state.setupEnvelope.data);
    }

    get readiness() {
        return asObject(this.state.readinessEnvelope && this.state.readinessEnvelope.data);
    }

    get readinessState() {
        return this.state.readinessState;
    }

    get settings() {
        return asObject(this.state.settingsEnvelope && this.state.settingsEnvelope.data);
    }

    get diagnostics() {
        return asObject(this.state.diagnosticsEnvelope && this.state.diagnosticsEnvelope.data);
    }

    get diagnosticsState() {
        return this.state.diagnosticsState;
    }

    get activeGeneration() {
        if (this.state.surface === P16_SURFACES.SETTINGS) {
            return settingsGeneration(this.state.settingsEnvelope);
        }
        const envelope = {
            [P16_SURFACES.SETUP]: this.state.setupEnvelope,
            [P16_SURFACES.READINESS]: this.state.readinessEnvelope,
            [P16_SURFACES.DIAGNOSTICS]: this.state.diagnosticsEnvelope,
        }[this.state.surface];
        // A cached list item is not a generation authority for a detail
        // command.  A missing/current-surface envelope intentionally yields
        // zero; the server must reject a command until a fresh read exists.
        return connectionGeneration(envelope, 0);
    }

    get activeSurfaceTitle() {
        return {
            [P16_SURFACES.LIST]: _t("Manage Stores"),
            [P16_SURFACES.CREATE]: _t("Add Store"),
            [P16_SURFACES.SETUP]: _t("Store Setup"),
            [P16_SURFACES.READINESS]: _t("Readiness and activation"),
            [P16_SURFACES.SETTINGS]: _t("Grouped Settings"),
            [P16_SURFACES.DIAGNOSTICS]: _t("Administrator diagnostics"),
        }[this.state.surface] || _t("Shopify Connector");
    }

    get setupCurrentStep() {
        const key = this.state.setupStepKey || this.setup.resume_step_key || "welcome";
        return asArray(this.setup.steps).find((step) => step.step_key === key) || {
            step_key: key,
            label: key,
            state: "pending",
        };
    }

    get setupStepIndex() {
        return Number(this.setupCurrentStep.display_ordinal || this.setupCurrentStep.index || 1);
    }

    get setupStepCount() {
        return asArray(this.setup.steps).length || 12;
    }

    get setupHasNext() {
        return Boolean(nextSetupStep(this.setup.steps, this.setupCurrentStep.step_key));
    }

    get setupValues() {
        return asObject(this.state.setupDraftValues[this.setupCurrentStep.step_key]);
    }

    onSetupValueChange(fieldKey, value) {
        const stepKey = this.setupCurrentStep.step_key;
        this.state.setupDraftValues = {
            ...this.state.setupDraftValues,
            [stepKey]: {
                ...asObject(this.state.setupDraftValues[stepKey]),
                [fieldKey]: value,
            },
        };
    }

    get setupGeneration() {
        return Number(this.setup.configuration_generation || 0);
    }

    get settingsGeneration() {
        return settingsGeneration(this.state.settingsEnvelope);
    }

    get readinessGeneration() {
        return connectionGeneration(this.state.readinessEnvelope, 0);
    }

    get serverActions() {
        return serverActions(this.diagnostics);
    }

    get diagnosticsAvailable() {
        return Boolean(this.diagnosticsEnvelopeLoaded);
    }

    get diagnosticsEnvelopeLoaded() {
        return this.state.diagnosticsState === "success" && Boolean(this.state.diagnosticsEnvelope);
    }

    get surfaceState() {
        if (this.state.surface === P16_SURFACES.LIST) {
            return this.state.listState;
        }
        const stateKey = `${this.state.surface}State`;
        return this.state[stateKey] ||
            (this.state.surface === P16_SURFACES.CREATE ? "unconfigured" : "loading");
    }

    get surfaceError() {
        return this.state.surfaceMessage || _t("No further explanation was supplied.");
    }

    get activeReadiness() {
        return this.readiness;
    }

    phaseForStep(stepKey) {
        return phaseForStep(stepKey);
    }

    get createDisabled() {
        return this.state.commandState === "loading" || !this.state.createName.trim() || !this.state.createDomain.trim();
    }

    get activeStoreId() {
        return Number(this.state.selectedStoreId) || null;
    }

    get actorUid() {
        return Number(this.user && (this.user.userId || this.user.user_id)) || null;
    }

    get activeCompanyId() {
        const context = asObject(this.user && this.user.context);
        const allowed = asArray(context.allowed_company_ids);
        const company = this.env && this.env.services && this.env.services.company;
        const current = company && company.currentCompany;
        return Number((current && current.id) || allowed[0] || companyIdFromProps(this.props)) || null;
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
        if (this._disposed) {
            return;
        }
        const nextCompanyId =
            Number(companyId && companyId.id ? companyId.id : companyId) || this.activeCompanyId;
        void this.revalidateCompanyContext(nextCompanyId);
    }

    /** Clear stale store DTOs before allowing a new company-scoped read. */
    async revalidateCompanyContext(companyId = this.activeCompanyId) {
        if (this._disposed) {
            return false;
        }
        const nextCompanyId = Number(companyId) || null;
        if (nextCompanyId === this.state.companyId) {
            return true;
        }
        this._invalidateContext();
        this.state.companyId = nextCompanyId;
        this.state.selectedStoreId = null;
        this.state.surface = P16_SURFACES.LIST;
        this.state.setupEnvelope = null;
        this.state.readinessEnvelope = null;
        this.state.settingsEnvelope = null;
        this.state.diagnosticsEnvelope = null;
        this.state.listEnvelope = normalizeEnvelope(
            {
                status: "permission_empty",
                message: _t("The active company changed. Refreshing permitted stores."),
                data: { stores: [] },
            },
            "permission_empty",
        );
        this.state.listState = "permission_empty";
        this.state.surfaceMessage = _t("The selected store was cleared after the company changed.");
        if (this._mounted) {
            await this.loadStores();
        }
        return false;
    }

    hasServerActionFor(value, key) {
        return hasServerAction(value, key);
    }

    async _command(commandName, {
        generation = 0,
        payload = {},
        context = null,
    } = {}) {
        // Starting any command invalidates a previous command immediately,
        // including one that is still waiting on an RPC or one rejected by a
        // current-surface authority check.
        const requestSerial = ++this._commandRequestSerial;
        if (this._disposed) {
            return null;
        }
        if (context && !this._contextIsCurrent(context)) {
            return null;
        }
        if (!this._companyContextIsCurrent()) {
            this.state.commandState = "conflict";
            this.state.commandMessage = _t("The active company changed. Refresh before submitting this request.");
            return null;
        }
        if (!commandIsAdvertised(this, commandName)) {
            this.state.commandState = "unavailable";
            this.state.commandMessage = _t(
                "This command is not authorized by the current server response. No request was submitted.",
            );
            return null;
        }
        let command;
        try {
            command = commandEnvelope({
                commandName,
                companyId: this.activeCompanyId,
                actorUid: this.actorUid,
                expectedGeneration: generation,
                storeId: commandName === "create_store_v1" ? null : this.activeStoreId,
                payload,
                trigger: "user",
            });
        } catch (error) {
            this.state.commandState = "terminal_error";
            this.state.commandMessage = safeErrorMessage(error && error.message);
            return null;
        }
        const requestCompanyId = command.company_id;
        const requestStoreId = command.store_id || null;
        const requestSurface = this.state.surface;
        const requestEpoch = this._contextEpoch;
        if (context && (
            context.epoch !== requestEpoch ||
            context.companyId !== requestCompanyId ||
            context.surface !== requestSurface ||
            (context.storeId !== null && context.storeId !== requestStoreId)
        )) {
            return null;
        }
        const requestIsCurrent = () => (
            !this._disposed &&
            requestSerial === this._commandRequestSerial &&
            requestEpoch === this._contextEpoch &&
            requestCompanyId === this.state.companyId &&
            requestSurface === this.state.surface &&
            (
                commandName === "create_store_v1" ||
                requestStoreId === this.activeStoreId
            )
        );
        this.state.commandState = "loading";
        this.state.commandMessage = "";
        try {
            const raw = await this.orm.call(
                P16_APPLICATION_MODEL,
                commandName,
                [command],
            );
            if (!requestIsCurrent()) {
                await this._refreshCurrentContext();
                return null;
            }
            const result = asObject(raw);
            this.state.commandState = normalizeEnvelope(raw, "success").state;
            this.state.commandMessage = safeErrorMessage(result.message);
            if (result.status === "conflict") {
                this.state.commandState = "conflict";
                this.state.surfaceMessage = _t("The server rejected this stale submission. Refresh to review the current state.");
            } else if (result.status === "blocked") {
                this.state.commandState = "stale";
                this.state.surfaceMessage = this.state.commandMessage;
            }
            return result;
        } catch (error) {
            if (!requestIsCurrent()) {
                await this._refreshCurrentContext();
                return null;
            }
            this.state.commandState = "terminal_error";
            this.state.commandMessage = this._errorMessage(error);
            this.state.surfaceMessage = this.state.commandMessage;
            return null;
        }
    }

}

installP16AdminReadMethods(ShopifyConnectorP16Admin);
installP16AdminCommandMethods(ShopifyConnectorP16Admin);
installP16AdminNavigationMethods(ShopifyConnectorP16Admin);

export const P16DetailMethods = P16_DETAIL_METHODS;
export const P16LifecycleCommands = P16_LIFECYCLE_COMMANDS;
