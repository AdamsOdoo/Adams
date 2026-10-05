/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { MarketplaceOnboarding } from "@base_marketplace/js/onboarding/marketplace_onboarding";

/**
 * Shopify-only extension of the marketplace onboarding wizard: when Save & Confirm
 * detects missing API scopes, show them inline on the Review & Confirm step
 * (instead of the popup wizard). Lives in the Shopify module so other marketplaces
 * are unaffected — `scopeCheck` stays null for them and the inline UI never shows.
 */
patch(MarketplaceOnboarding.prototype, {
    setup() {
        super.setup();
        // {missing:[], granted:[]} when Shopify's save returns missing scopes; else null.
        this.state.scopeCheck = null;
        // Which scope action is running ('ignore' | 'recheck' | null) — drives the
        // per-button spinner so one button's spinner never shows on the other.
        this.state.scopeBusy = null;
    },

    /** Leaving the scope-error view via Back returns to the editable steps. */
    onPrevious() {
        this.state.scopeCheck = null;
        super.onPrevious();
    },

    /** Jumping to an earlier step via the tabs also clears the scope-error view. */
    async onStepTabClick(step) {
        if (step < this.state.currentStep) {
            this.state.scopeCheck = null;
        }
        return super.onStepTabClick(step);
    },

    /** Intercept the save result: missing scopes → show the inline scope check. */
    _onSaveResult(res) {
        if (res && res.scope_check && (res.scope_check.missing || []).length) {
            this.state.scopeCheck = res.scope_check;
            this.state.hasSavedData = true;
            return true;
        }
        return super._onSaveResult(res);
    },

    /** Ignore the missing scopes, confirm the instance, and open it. */
    async onScopeIgnoreConfirm() {
        this.state.saving = true;
        this.state.scopeBusy = "ignore";
        try {
            await this.orm.call("mk.instance", "onboarding_ignore_scopes_and_confirm", [
                [this.state.instanceId],
                this.state.formData,
            ]);
            this.state.hasSavedData = true;
            this.notification.add(_t("Configuration saved."), { type: "success" });
            await this.openInstanceForm();
        } catch (error) {
            const msg = error.data?.message || error.message || String(error);
            this.notification.add(msg, { type: "danger" });
        } finally {
            this.state.saving = false;
            this.state.scopeBusy = null;
        }
    },

    /** Re-fetch granted scopes; if none missing now, confirm and open the instance. */
    async onScopeCheckAgain() {
        this.state.saving = true;
        this.state.scopeBusy = "recheck";
        try {
            const res = await this.orm.call("mk.instance", "get_onboarding_scope_check", [
                [this.state.instanceId],
            ]);
            this.state.scopeCheck = res;
            if (res && !(res.missing || []).length) {
                await this.orm.call("mk.instance", "onboarding_ignore_scopes_and_confirm", [
                    [this.state.instanceId],
                    this.state.formData,
                ]);
                this.state.hasSavedData = true;
                this.notification.add(_t("Configuration saved."), { type: "success" });
                await this.openInstanceForm();
            }
        } catch (error) {
            const msg = error.data?.message || error.message || String(error);
            this.notification.add(msg, { type: "danger" });
        } finally {
            this.state.saving = false;
            this.state.scopeBusy = null;
        }
    },
});
