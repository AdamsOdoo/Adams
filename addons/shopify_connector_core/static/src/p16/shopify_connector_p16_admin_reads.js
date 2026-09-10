/** @odoo-module **/

/*
 * Read/settings mixin for the subordinate P16 administrator surface.
 *
 * P16 remains a presentation client for named server DTOs.  Moving its
 * bounded reads and draft shaping out of the action component keeps the
 * subordinate surface below the controller-size limit without creating a
 * second root or a second state owner.
 */

import { _t } from "@web/core/l10n/translation";
import {
    P16_APPLICATION_MODEL,
    P16_DETAIL_METHODS,
    P16_STORE_LIST_LIMIT,
    P16_SURFACES,
    asArray,
    asObject,
    fieldInputValue,
    fieldIsReadOnly,
    normalizeEnvelope,
    safeErrorMessage,
    settingsGroups,
} from "./shopify_connector_p16_contract";

function setupDraftValues(value) {
    const source = asObject(value);
    const result = {};
    for (const [stepKey, rawValues] of Object.entries(source)) {
        const values = asObject(rawValues);
        const safe = {};
        for (const [key, item] of Object.entries(values)) {
            if (
                !key || key.length > 80 || /token|secret|password|credential|authorization/i.test(key) ||
                (item !== null && typeof item !== "string" && typeof item !== "boolean" && typeof item !== "number") ||
                (typeof item === "number" && !Number.isFinite(item))
            ) {
                continue;
            }
            safe[key] = typeof item === "string" ? item.slice(0, 2000) : item;
        }
        result[stepKey] = safe;
    }
    return result;
}

export function installP16AdminReadMethods(ActionClass) {
    Object.assign(ActionClass.prototype, {
        async loadStores({ append = false, cursor = null } = {}) {
            if (this._disposed) {
                return null;
            }
            const prior = append ? this.listItems : [];
            const requestContext = this._contextSnapshot({ storeId: null });
            const requestCompanyId = requestContext.companyId;
            const requestSurface = requestContext.surface;
            const requestSerial = ++this._listRequestSerial;
            this.state.listState = this.state.listEnvelope ? "refreshing" : "loading";
            this.state.surfaceMessage = "";
            try {
                // `get_store_list_v1` is a fixed server read; the browser
                // supplies no company list or arbitrary search domain.
                const raw = await this.orm.call(
                    P16_APPLICATION_MODEL,
                    "get_store_list_v1",
                    [],
                    {
                        search: this.state.search || false,
                        limit: P16_STORE_LIST_LIMIT,
                        cursor,
                    },
                );
                if (
                    requestSerial !== this._listRequestSerial ||
                    requestCompanyId !== this.state.companyId ||
                    requestSurface !== this.state.surface ||
                    !this._contextIsCurrent(requestContext)
                ) {
                    return null;
                }
                const envelope = normalizeEnvelope(raw, "success");
                const data = asObject(envelope.data);
                const stores = append ? [...prior, ...asArray(data.stores)] : asArray(data.stores);
                const merged = { ...data, stores };
                this.state.listEnvelope = normalizeEnvelope(
                    { ...asObject(envelope.raw), data: merged },
                    "success",
                );
                this.state.listState = stores.length
                    ? "success"
                    : this.state.search
                      ? "filtered_empty"
                      : "empty";
                if (this.state.selectedStoreId && !this._knownStore(this.state.selectedStoreId)) {
                    this._invalidateContext();
                    this.state.selectedStoreId = null;
                }
                return this.state.listEnvelope;
            } catch (error) {
                if (
                    requestSerial !== this._listRequestSerial ||
                    requestCompanyId !== this.state.companyId ||
                    requestSurface !== this.state.surface ||
                    !this._contextIsCurrent(requestContext)
                ) {
                    return null;
                }
                this.state.listState = "terminal_error";
                this.state.surfaceMessage = this._errorMessage(error);
                return null;
            }
        },

        onSearchInput(value) {
            this.state.search = typeof value === "string" ? value : "";
        },

        async onSearch() {
            await this.loadStores();
        },

        async onNextPage() {
            const data = asObject(this.state.listEnvelope && this.state.listEnvelope.data);
            if (data.has_more && data.next_cursor) {
                await this.loadStores({ append: true, cursor: data.next_cursor });
            }
        },

        async refreshList() {
            await this.loadStores();
        },

        async _refreshCurrentContext() {
            if (
                this._disposed ||
                (Number(this.state.companyId) || null) !== this.activeCompanyId
            ) {
                return null;
            }
            if (this.state.surface === P16_SURFACES.LIST) {
                return this.loadStores();
            }
            if (
                this.state.surface === P16_SURFACES.CREATE ||
                !this.activeStoreId ||
                !P16_DETAIL_METHODS[this.state.surface]
            ) {
                return null;
            }
            return this._loadSurface(this.state.surface);
        },

        async _loadSurface(surface) {
            const method = P16_DETAIL_METHODS[surface];
            if (!method || !this.activeStoreId || this._disposed) {
                return null;
            }
            const requestContext = this._contextSnapshot({ storeId: this.activeStoreId });
            const requestSerial = ++this._surfaceRequestSerial;
            const requestCompanyId = requestContext.companyId;
            const requestSurface = requestContext.surface;
            const requestStoreId = this.activeStoreId;
            const stateKey = `${surface}State`;
            this.state[stateKey] = "loading";
            this.state.surfaceMessage = "";
            try {
                const raw = await this.orm.call(
                    P16_APPLICATION_MODEL,
                    method,
                    [requestStoreId],
                );
                if (
                    requestSerial !== this._surfaceRequestSerial ||
                    requestCompanyId !== this.state.companyId ||
                    requestSurface !== this.state.surface ||
                    requestStoreId !== this.activeStoreId ||
                    !this._contextIsCurrent(requestContext)
                ) {
                    return null;
                }
                const envelope = normalizeEnvelope(raw, "success");
                const data = asObject(envelope.data);
                this.state[`${surface}Envelope`] = envelope;
                this.state[stateKey] = envelope.state;
                if (surface === P16_SURFACES.SETUP) {
                    this.state.setupStepKey = this.setup.resume_step_key || "welcome";
                    this.state.setupDraftValues = setupDraftValues(data.step_values);
                }
                if (surface === P16_SURFACES.SETTINGS) {
                    this._seedSettingsDrafts(envelope);
                }
                return envelope;
            } catch (error) {
                if (
                    requestSerial !== this._surfaceRequestSerial ||
                    requestCompanyId !== this.state.companyId ||
                    requestSurface !== this.state.surface ||
                    requestStoreId !== this.activeStoreId ||
                    !this._contextIsCurrent(requestContext)
                ) {
                    return null;
                }
                this.state[stateKey] = "terminal_error";
                this.state.surfaceMessage = this._errorMessage(error);
                return null;
            }
        },

        _seedSettingsDrafts(envelope) {
            const drafts = {};
            for (const group of settingsGroups(envelope)) {
                for (const field of asArray(group.fields)) {
                    drafts[`${group.key}.${field.key}`] = fieldInputValue(field);
                }
            }
            this.state.settingsDrafts = drafts;
        },

        onSettingChange(groupKey, fieldKey, value) {
            this.state.settingsDrafts = {
                ...this.state.settingsDrafts,
                [`${groupKey}.${fieldKey}`]: value,
            };
        },

        _settingsGroup(groupKey) {
            return (
                settingsGroups(this.state.settingsEnvelope).find((group) => group.key === groupKey) ||
                null
            );
        },

        async saveSettingsGroup(groupKey) {
            const group = this._settingsGroup(groupKey);
            if (!group || !this.hasServerActionFor(group, "open_store_settings")) {
                this.state.surfaceMessage = _t("Settings are not available for this role.");
                return;
            }
            const values = {};
            for (const field of asArray(group.fields)) {
                const key = `${group.key}.${field.key}`;
                if (
                    !Object.prototype.hasOwnProperty.call(this.state.settingsDrafts, key) ||
                    fieldIsReadOnly(field)
                ) {
                    continue;
                }
                values[field.key] = this.state.settingsDrafts[key];
            }
            if (!Object.keys(values).length) {
                this.state.surfaceMessage = _t("There are no editable settings in this group.");
                return;
            }
            const requestContext = this._contextSnapshot();
            const result = await this._command("save_store_settings_group_v1", {
                generation: this.settingsGeneration,
                payload: {
                    group_key: groupKey,
                    expected_fingerprint: group.fingerprint,
                    values,
                },
                context: requestContext,
            });
            if (
                result &&
                result.status !== "conflict" &&
                result.status !== "blocked" &&
                this._contextIsCurrent(requestContext)
            ) {
                await this._loadSurface(P16_SURFACES.SETTINGS);
            }
        },

        _errorMessage(error) {
            const data = asObject(error && error.data);
            return safeErrorMessage(data.message || data.detail || (error && error.message));
        },
    });
}
