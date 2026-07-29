/** @odoo-module **/
// Part of the Shopify Connector (S1 guided setup).
//
// The 12-step setup wizard: one bounded Owl client action inside the normal
// Odoo web client. Standard action, standard ORM service, standard breadcrumbs.
// No SPA, no custom router, no external library, no CDN, no external font, no
// second store-management system.
//
// WHAT THIS COMPONENT IS ALLOWED TO DO. Render what the server sent, collect
// one decision per step, and call one guarded server method per step. It
// evaluates no guard, decides no default, derives no scope list and computes
// no readiness verdict — every one of those came from
// `shopify.connector.setup.wizard`, which delegates in turn to the services
// that already own them.
//
// NAVIGATION IS BY SEMANTIC STEP KEY, NOT BY POSITION. `state.stepKey` is a
// string — "credential", "location_mapping", "final_readiness" — and every
// branch, every guard, every server call and every deep link compares against
// one. The ordinal exists only to render "Step 7 of 12", and it is read out of
// the server's own step list rather than counted here. This is not stylistic:
// Wave 5 inserted a step into the middle of the accepted order, and a client
// that had switched on `state.step === 8` would have silently started running
// the Customer-notifications branch on the Source-of-truth screen. A string
// mismatch is a visible bug; a number that still matches is not.
//
// WHY THERE IS NO CLIENT-SIDE AUTHORIZATION. There is none to have. The server
// re-checks the Administrator role, record access and company consistency on
// every single entry point, including the read. Hiding a control is never what
// makes this safe.
//
// THE CREDENTIAL IS WRITE-ONLY AND THIS FILE IS WHERE THAT COULD QUIETLY STOP
// BEING TRUE. The token lives in a local variable for exactly as long as the
// RPC takes, is cleared immediately afterwards, is never written into
// `this.state`, never appears in a URL, and never comes back: the server
// returns `credential_present` as a boolean and nothing else.

import {
    Component,
    onWillStart,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";

// `localization` is a Proxy that THROWS for any parameter not yet loaded
// (`web/static/src/core/l10n/localization.js`), so reading it before the
// localization service has resolved would stop this component mounting. A
// surface must never fail to render over a locale parameter, and "ltr" is the
// documented default.
function localeDirection() {
    try {
        return localization.direction || "ltr";
    } catch {
        return "ltr";
    }
}

const MODEL = "shopify.connector.setup.wizard";

// The first step's key. Used only as the fallback when the server payload has
// not arrived yet; every other key in this file comes from that payload.
const FIRST_STEP_KEY = "welcome";

export class ShopifyConnectorSetupWizard extends Component {
    static template = "shopify_connector_core.SetupWizard";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.direction = localeDirection();
        this.headingRef = useRef("heading");

        this.state = useState({
            status: "loading", // "loading" | "ready" | "error"
            errorMessage: "",
            busy: false,
            stepKey: FIRST_STEP_KEY,
            data: null,
            // Per-step drafts. Nothing here is authoritative: each is sent to
            // the server, which writes it to the field that owns it and
            // returns the stored truth.
            form: {
                name: "",
                shopDomain: "",
                enabledDomains: [],
                matching: "",
                price: "",
                notification: false,
                notificationConfirmed: false,
                schedulePush: false,
                scopesRead: false,
                mapShopifyGid: "",
                mapOdooLocationId: "",
                // Which credential path the merchant is entering. Seeded from
                // the store's stored mode on load, so re-running setup shows
                // the path they actually use. The value is a mode NAME, never
                // a secret.
                credentialMode: "dev_dashboard_client_credentials",
            },
        });

        onWillStart(async () => {
            await this._load(this._contextStoreId());
        });

        // A11y: focus moves to the step heading on advance, so a keyboard or
        // screen-reader user lands on the new step's title rather than being
        // left at the bottom of the previous one.
        useEffect(
            () => {
                if (this.headingRef.el) {
                    this.headingRef.el.focus();
                }
            },
            () => [this.state.stepKey]
        );
    }

    _contextStoreId() {
        const context = (this.props.action && this.props.action.context) || {};
        return context.default_setup_store_id || null;
    }

    get steps() {
        return (this.state.data && this.state.data.steps) || [];
    }

    get store() {
        return (this.state.data && this.state.data.store) || {};
    }

    get summary() {
        return (this.state.data && this.state.data.summary) || {};
    }

    get locations() {
        return (
            (this.state.data && this.state.data.location_mapping) || {
                available: false,
                reason: "",
                locations: [],
                odoo_locations: [],
                refresh: { state: "none" },
                mapped_count: 0,
                unmapped_count: 0,
            }
        );
    }

    get readiness() {
        return (
            (this.state.data && this.state.data.readiness) || {
                ran: false,
                stale: false,
                checks: [],
                blocking: [],
                waiting: [],
            }
        );
    }

    get currentStep() {
        return this.steps.find((s) => s.key === this.state.stepKey) || {};
    }

    /** Position of the current step in the server's own ordered list. */
    get currentIndex() {
        return this.steps.findIndex((s) => s.key === this.state.stepKey);
    }

    get isFirstStep() {
        return this.currentIndex <= 0;
    }

    get isLastStep() {
        const index = this.currentIndex;
        return index >= 0 && index === this.steps.length - 1;
    }

    /** Is the current step one this store actually has to answer? */
    get currentStepApplies() {
        const step = this.currentStep;
        return step.applicable === undefined ? true : step.applicable;
    }

    stepClass(step) {
        let cls = "sc_setup_step";
        if (step.key === this.state.stepKey) {
            cls += " sc_setup_step--current";
        } else if (step.index < (this.currentStep.index || 0)) {
            cls += " sc_setup_step--done";
        }
        if (step.applicable === false) {
            cls += " sc_setup_step--skipped";
        }
        return cls;
    }

    checkClass(check) {
        return "sc_setup_check sc_setup_check--" + (check.tone || "neutral");
    }

    refreshState() {
        return (this.locations.refresh || {}).state || "none";
    }

    refreshLabel() {
        return {
            waiting: _t("Waiting"),
            running: _t("Running"),
            succeeded: _t("Succeeded"),
            failed: _t("Failed"),
            none: _t("Not run yet"),
        }[this.refreshState()];
    }

    // --- server round trips -------------------------------------------------

    async _load(storeId) {
        try {
            const data = await this.orm.call(MODEL, "get_setup_state", [], {
                store_id: storeId || null,
            });
            this._adopt(data, true);
            this.state.status = "ready";
            await this._onEnterStep();
        } catch (error) {
            this.state.status = "error";
            this.state.errorMessage = this._message(error);
        }
    }

    /** Adopt the server payload as the single source of truth. */
    _adopt(data, resume = false) {
        this.state.data = data;
        const store = data.store || {};
        this.state.form.name = store.name || "";
        this.state.form.shopDomain = store.shop_domain || "";
        this.state.form.enabledDomains = (data.domains || [])
            .filter((d) => d.enabled)
            .map((d) => d.key);
        // Deliberately NOT seeded from the stored values. The source-of-truth
        // step requires an explicit choice, and pre-selecting whatever the
        // backend default happens to be is precisely how a default becomes
        // "consent" without anybody consenting to it. A store that has already
        // been through setup shows its stored answer in the summary instead.
        this.state.form.matching = "";
        this.state.form.price = "";
        this.state.form.notification = false;
        this.state.form.notificationConfirmed = false;
        this.state.form.schedulePush = false;
        this.state.form.mapShopifyGid = "";
        this.state.form.mapOdooLocationId = "";
        // Seed the credential-path choice from what the store already uses, so
        // a rerun opens on the merchant's actual path. A store with no
        // credential yet defaults to the Dev Dashboard path, because that is
        // the app-creation flow Shopify currently gives a new merchant.
        if (store.credential_present && store.auth_mode) {
            this.state.form.credentialMode = store.auth_mode;
        }
        if (resume && data.resume_step_key) {
            this.state.stepKey = data.resume_step_key;
        }
    }

    /** The credential step's path switch. A mode name, never a secret. */
    setCredentialMode(mode) {
        this.state.form.credentialMode = mode;
        this.state.errorMessage = "";
    }

    _message(error) {
        return (
            (error && error.data && error.data.message) ||
            (error && error.message) ||
            _t("Something went wrong. Nothing was saved.")
        );
    }

    /** Run one guarded server call, surface its refusal, never swallow it. */
    async _call(method, kwargs) {
        if (this.state.busy) {
            return false;
        }
        this.state.busy = true;
        try {
            const data = await this.orm.call(MODEL, method, [], kwargs);
            this._adopt(data);
            this.state.errorMessage = "";
            return true;
        } catch (error) {
            this.state.errorMessage = this._message(error);
            return false;
        } finally {
            this.state.busy = false;
        }
    }

    // --- navigation ---------------------------------------------------------

    /**
     * Move to a step by KEY. Every navigation in this component goes through
     * here, including the readiness deep links, so there is exactly one place
     * a step transition can happen and exactly one place the on-enter work
     * can be triggered from.
     */
    async goToStep(stepKey) {
        if (!this.steps.some((s) => s.key === stepKey)) {
            return;
        }
        this.state.stepKey = stepKey;
        this.state.errorMessage = "";
        await this._onEnterStep();
    }

    async back() {
        const index = this.currentIndex;
        if (index > 0) {
            await this.goToStep(this.steps[index - 1].key);
        }
    }

    async _advance() {
        const index = this.currentIndex;
        if (index >= 0 && index < this.steps.length - 1) {
            await this.goToStep(this.steps[index + 1].key);
        }
    }

    /**
     * Work that happens on ARRIVING at a step, whichever direction it was
     * reached from.
     *
     * Final readiness is the one step with any: entering it must evaluate the
     * configuration as it is NOW, not replay a result recorded before the
     * choices above it were made. It re-runs only when there is nothing to
     * show or when what is shown is stale, so paging back and forth does not
     * queue a run per keystroke. `run_readiness` reads stored evidence and
     * contacts nothing.
     */
    async _onEnterStep() {
        if (this.state.stepKey !== "final_readiness") {
            return;
        }
        if (!this.store.id) {
            return;
        }
        if (this.readiness.ran && !this.readiness.stale) {
            return;
        }
        await this._call("run_readiness", { store_id: this.store.id });
    }

    async saveAndExit() {
        if (this.store.id) {
            await this.orm.call(MODEL, "save_and_exit", [], {
                store_id: this.store.id,
                // The KEY, never the ordinal. The server refuses an ordinal
                // outright rather than translating it.
                step_key: this.state.stepKey,
            });
        }
        this.notification.add(
            _t("Setup saved. You can pick up where you left off."),
            { type: "success" }
        );
        this.action.doAction("shopify_connector_core.action_shopify_connector_dashboard");
    }

    /** One handler per step, selected by KEY. Each calls one guarded method. */
    async continueStep() {
        const storeId = this.store.id;
        let ok = false;
        switch (this.state.stepKey) {
            case "welcome":
                ok = true;
                break;
            case "identity":
                ok = await this._call("save_store_identity", {
                    name: this.state.form.name,
                    shop_domain: this.state.form.shopDomain,
                    store_id: storeId || null,
                });
                break;
            case "credential":
                // Read from the DOM node and cleared immediately: the token is
                // never bound into component state, so it cannot be read back
                // out of it, serialised into a snapshot or survive a re-render.
                ok = await this._submitCredential();
                break;
            case "scopes":
                ok = await this._call("acknowledge_scopes", {
                    store_id: storeId,
                });
                break;
            case "test_connection":
                // Continue ADVANCES; it does not run the check. This step's
                // whole job is to show the operator an explicit pass or an
                // actionable failure, and a Continue that ran the probe and
                // moved on in the same click would never show either.
                if (this.store.test_connection_result !== "pass") {
                    this.state.errorMessage = _t(
                        "Run the connection test and get a pass before continuing."
                    );
                    return;
                }
                ok = true;
                break;
            case "directions":
                ok = await this._call("save_directions", {
                    store_id: storeId,
                    enabled_keys: this.state.form.enabledDomains,
                });
                break;
            case "location_mapping":
                ok = await this._call("acknowledge_location_mapping", {
                    store_id: storeId,
                });
                break;
            case "source_of_truth":
                ok = await this._call("save_source_of_truth", {
                    store_id: storeId,
                    matching: this.state.form.matching,
                    price: this.state.form.price,
                });
                break;
            case "notification":
                ok = await this._call("save_notification", {
                    store_id: storeId,
                    enabled: this.state.form.notification,
                    confirmed: this.state.form.notificationConfirmed,
                });
                break;
            case "first_push":
                ok = await this._call("save_first_push_schedule", {
                    store_id: storeId,
                    schedule_now: this.state.form.schedulePush,
                });
                break;
            case "final_readiness":
                if (!this.readiness.ran) {
                    this.state.errorMessage = _t(
                        "Run the readiness checks before continuing."
                    );
                    return;
                }
                ok = true;
                break;
            case "review":
                ok = await this._call("activate", { store_id: storeId });
                if (ok) {
                    this.notification.add(
                        _t("Your store is set up. Nothing is syncing yet — the dashboard shows what to do next."),
                        { type: "success" }
                    );
                    this.action.doAction(
                        "shopify_connector_core.action_shopify_connector_dashboard"
                    );
                }
                return;
        }
        if (ok) {
            await this._advance();
        }
    }

    /** The test-connection step's explicit action. Stays put, whatever happens. */
    async runTestConnection() {
        const ok = await this._call("run_test_connection", {
            store_id: this.store.id,
        });
        if (ok && this.store.test_connection_result !== "pass") {
            // A refusal the server RECORDED rather than raised. Surface the
            // reason it recorded: a failed test must never read as a pass.
            this.state.errorMessage =
                this.store.test_connection_reason ||
                _t("The connection test did not pass.");
        }
    }

    /** The final-readiness step's explicit "run again". */
    async runReadiness() {
        await this._call("run_readiness", { store_id: this.store.id });
    }

    /** The location step's refresh. Admits a job; contacts nothing from here. */
    async refreshLocations() {
        await this._call("refresh_shopify_locations", {
            store_id: this.store.id,
        });
    }

    /** The location step's create. Both identities explicit, both server-checked. */
    async createMapping() {
        if (!this.state.form.mapShopifyGid) {
            this.state.errorMessage = _t("Choose a Shopify location to map.");
            return;
        }
        if (!this.state.form.mapOdooLocationId) {
            this.state.errorMessage = _t("Choose an Odoo location to map it to.");
            return;
        }
        const ok = await this._call("save_location_mapping", {
            store_id: this.store.id,
            shopify_location_gid: this.state.form.mapShopifyGid,
            odoo_location_id: parseInt(this.state.form.mapOdooLocationId, 10),
        });
        if (ok) {
            this.state.form.mapShopifyGid = "";
            this.state.form.mapOdooLocationId = "";
        }
    }

    async _submitCredential() {
        if (this.state.form.credentialMode === "dev_dashboard_client_credentials") {
            return this._submitClientCredentials();
        }
        const input = document.querySelector(".sc_setup_token");
        const value = input ? input.value : "";
        if (!value) {
            this.state.errorMessage = _t(
                "Paste the Admin API access token to continue."
            );
            return false;
        }
        const ok = await this._call("save_credential", {
            store_id: this.store.id,
            token: value,
        });
        // Cleared whether or not the call succeeded. A token left in the DOM
        // is a token in every screenshot, DOM snapshot and error report taken
        // afterwards.
        if (input) {
            input.value = "";
        }
        return ok;
    }

    async _submitClientCredentials() {
        // Same discipline as the token path: read from the DOM nodes, never
        // bind into component state, clear both fields whatever the outcome.
        const idInput = document.querySelector(".sc_setup_client_id");
        const secretInput = document.querySelector(".sc_setup_client_secret");
        const clientId = idInput ? idInput.value : "";
        const clientSecret = secretInput ? secretInput.value : "";
        if (!clientId) {
            this.state.errorMessage = _t(
                "Enter the app's Client ID to continue."
            );
            return false;
        }
        if (!clientSecret) {
            this.state.errorMessage = _t(
                "Enter the app's Client secret to continue."
            );
            return false;
        }
        const ok = await this._call("save_client_credentials", {
            store_id: this.store.id,
            client_id: clientId,
            client_secret: clientSecret,
        });
        if (secretInput) {
            secretInput.value = "";
        }
        if (ok && idInput) {
            idInput.value = "";
        }
        return ok;
    }

    toggleDomain(key) {
        const list = this.state.form.enabledDomains;
        const index = list.indexOf(key);
        if (index === -1) {
            list.push(key);
        } else {
            list.splice(index, 1);
        }
    }

    isDomainEnabled(key) {
        return this.state.form.enabledDomains.includes(key);
    }

    async rerun() {
        const ok = await this._call("restart_setup", { store_id: this.store.id });
        if (ok) {
            await this.goToStep(FIRST_STEP_KEY);
        }
    }
}

registry.category("actions").add("shopify_connector_setup_wizard", ShopifyConnectorSetupWizard);
