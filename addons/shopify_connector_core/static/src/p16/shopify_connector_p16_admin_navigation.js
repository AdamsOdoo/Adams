/** @odoo-module **/

/* Navigation and create-flow methods for the subordinate P16 surface. */

import { _t } from "@web/core/l10n/translation";

import {
    P16_SURFACES,
    asArray,
    asObject,
    canSelectSetupStep,
    findStoreItem,
    serverActionTarget,
    serverActions,
} from "./shopify_connector_p16_contract";

export function installP16AdminNavigationMethods(ActionClass) {
    Object.assign(ActionClass.prototype, {
        _initialSurface() {
            const context = asObject(this.props.action && this.props.action.context);
            return Object.values(P16_SURFACES).includes(context.p16_surface)
                ? context.p16_surface
                : P16_SURFACES.LIST;
        },

        _contextStoreId() {
            const context = asObject(this.props.action && this.props.action.context);
            const id = Number(context.p16_store_id || context.default_store_id || 0);
            return Number.isInteger(id) && id > 0 ? id : null;
        },

        async _loadInitialSurface() {
            if (
                !this.activeStoreId ||
                this.state.surface === P16_SURFACES.LIST ||
                this.state.surface === P16_SURFACES.CREATE
            ) {
                if (this.state.surface !== P16_SURFACES.CREATE) {
                    this._setSurface(P16_SURFACES.LIST);
                }
                return;
            }
            if (!this._knownStore(this.activeStoreId)) {
                this._setSurface(P16_SURFACES.LIST);
                return;
            }
            await this._loadSurface(this.state.surface);
        },

        _knownStore(storeId) {
            return Boolean(findStoreItem(this.listItems, storeId));
        },

        async openStore(storeId) {
            if (!this._companyContextIsCurrent()) {
                return;
            }
            if (!this._knownStore(storeId)) {
                this.state.surfaceMessage = _t(
                    "That store is no longer in the permitted list. Refresh and try again.",
                );
                return;
            }
            const nextStoreId = Number(storeId);
            if (nextStoreId !== this.activeStoreId) {
                this._invalidateContext();
            }
            this.state.selectedStoreId = nextStoreId;
            await this.openReadiness(storeId);
        },

        async openReadiness(storeId = this.activeStoreId) {
            if (!this._setSelectedStore(storeId)) {
                return;
            }
            this._setSurface(P16_SURFACES.READINESS);
            await this._loadSurface(P16_SURFACES.READINESS);
        },

        async openSetup(storeId = this.activeStoreId) {
            if (!this._setSelectedStore(storeId)) {
                return;
            }
            this._setSurface(P16_SURFACES.SETUP);
            await this._loadSurface(P16_SURFACES.SETUP);
        },

        async openSettings(storeId = this.activeStoreId) {
            if (!this._setSelectedStore(storeId)) {
                return;
            }
            this._setSurface(P16_SURFACES.SETTINGS);
            await this._loadSurface(P16_SURFACES.SETTINGS);
        },

        async openDiagnostics(storeId = this.activeStoreId) {
            if (!this._setSelectedStore(storeId)) {
                return;
            }
            this._setSurface(P16_SURFACES.DIAGNOSTICS);
            await this._loadSurface(P16_SURFACES.DIAGNOSTICS);
        },

        _setSelectedStore(storeId) {
            const id = Number(storeId);
            if (!this._companyContextIsCurrent()) {
                return false;
            }
            if (!Number.isInteger(id) || id <= 0 || !this._knownStore(id)) {
                this.state.surfaceMessage = _t(
                    "That store is not available in the current company scope.",
                );
                return false;
            }
            if (id !== this.activeStoreId) {
                this._invalidateContext();
            }
            this.state.selectedStoreId = id;
            this.state.surfaceMessage = "";
            return true;
        },

        _companyContextIsCurrent() {
            if (this._disposed) {
                return false;
            }
            const current = this.activeCompanyId;
            if (current === this.state.companyId) {
                return true;
            }
            void this.revalidateCompanyContext(current);
            return false;
        },

        async retrySurface() {
            if (this.state.surface === P16_SURFACES.LIST) {
                await this.loadStores();
            } else {
                await this._loadSurface(this.state.surface);
            }
        },

        backToList() {
            this._invalidateContext();
            this._setSurface(P16_SURFACES.LIST);
            this.state.surfaceMessage = "";
        },

        newStore() {
            if (!this.canShowAddStore) {
                this.state.surfaceMessage = _t(
                    "Store creation is not available for this role.",
                );
                return;
            }
            this._setSurface(P16_SURFACES.CREATE);
            this.state.surfaceMessage = "";
            this.state.createName = "";
            this.state.createDomain = "";
        },

        onCreateName(value) {
            this.state.createName = typeof value === "string" ? value : "";
        },

        onCreateDomain(value) {
            this.state.createDomain = typeof value === "string" ? value : "";
        },

        async submitCreate() {
            if (
                this.createDisabled ||
                !this.canShowAddStore ||
                !this._companyContextIsCurrent()
            ) {
                if (!this.canShowAddStore) {
                    this.state.surfaceMessage = _t(
                        "Store creation is not available for this role.",
                    );
                }
                return;
            }
            const requestContext = this._contextSnapshot({ storeId: null });
            const result = await this._command("create_store_v1", {
                generation: 0,
                payload: {
                    name: this.state.createName.trim(),
                    shop_domain: this.state.createDomain.trim(),
                },
                context: requestContext,
            });
            if (!result || result.status === "conflict" || result.status === "blocked") {
                return;
            }
            if (!this._contextIsCurrent(requestContext)) {
                return null;
            }
            const createdId = Number(result.store_id || 0);
            await this.loadStores();
            if (!this._contextIsCurrent(requestContext)) {
                return null;
            }
            if (createdId && this._knownStore(createdId)) {
                this.state.selectedStoreId = createdId;
                this._invalidateContext();
                this._setSurface(P16_SURFACES.SETUP);
                await this._loadSurface(P16_SURFACES.SETUP);
            } else {
                this._setSurface(P16_SURFACES.LIST);
            }
        },

        selectSetupStep(stepKey) {
            if (canSelectSetupStep(
                asArray(this.setup.steps),
                this.setupCurrentStep.step_key,
                stepKey,
            )) {
                this.state.setupStepKey = stepKey;
                this.state.surfaceMessage = "";
            } else {
                this.state.surfaceMessage = _t(
                    "Complete the current setup step before opening a later step.",
                );
            }
        },

        openNativeManageStores(action = null) {
            const candidates = [
                action,
                ...serverActions(this.state.listEnvelope && this.state.listEnvelope.data),
                ...serverActions(this.selectedItem),
            ];
            const authorized = candidates.find(
                (candidate) => candidate && candidate.key === "manage_stores",
            );
            const target = serverActionTarget(authorized);
            if (!target) {
                this.state.surfaceMessage = _t(
                    "The server did not return an authorized native Manage stores target. No navigation occurred.",
                );
                return;
            }
            this.action.doAction(target);
        },
    });
}
