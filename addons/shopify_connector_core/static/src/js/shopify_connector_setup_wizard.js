/** @odoo-module **/
// Part of the Shopify Connector (S1 guided setup).
//
// The 11-step setup wizard: one bounded Owl client action inside the normal
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
            step: 1,
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
            () => [this.state.step]
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

    get readiness() {
        return (
            (this.state.data && this.state.data.readiness) || {
                ran: false,
                checks: [],
                blocking: [],
            }
        );
    }

    get currentStep() {
        return this.steps.find((s) => s.index === this.state.step) || {};
    }

    get isFirstStep() {
        return this.state.step <= 1;
    }

    get isLastStep() {
        return this.state.step >= (this.state.data?.step_count || 11);
    }

    stepClass(step) {
        let cls = "sc_setup_step";
        if (step.index === this.state.step) {
            cls += " sc_setup_step--current";
        } else if (step.index < this.state.step) {
            cls += " sc_setup_step--done";
        }
        return cls;
    }

    checkClass(check) {
        return "sc_setup_check sc_setup_check--" + (check.tone || "neutral");
    }

    // --- server round trips -------------------------------------------------

    async _load(storeId) {
        try {
            const data = await this.orm.call(MODEL, "get_setup_state", [], {
                store_id: storeId || null,
            });
            this._adopt(data);
            this.state.status = "ready";
        } catch (error) {
            this.state.status = "error";
            this.state.errorMessage = this._message(error);
        }
    }

    /** Adopt the server payload as the single source of truth. */
    _adopt(data) {
        this.state.data = data;
        const store = data.store || {};
        this.state.form.name = store.name || "";
        this.state.form.shopDomain = store.shop_domain || "";
        this.state.form.enabledDomains = (data.domains || [])
            .filter((d) => d.enabled)
            .map((d) => d.key);
        // Deliberately NOT seeded from the stored values. Step 8 requires an
        // explicit choice, and pre-selecting whatever the backend default
        // happens to be is precisely how a default becomes "consent" without
        // anybody consenting to it. A store that has already been through
        // setup shows its stored answer in the summary instead.
        this.state.form.matching = "";
        this.state.form.price = "";
        this.state.form.notification = false;
        this.state.form.notificationConfirmed = false;
        this.state.form.schedulePush = false;
        if (data.resume_step && this.state.step === 1) {
            this.state.step = Math.min(
                data.resume_step,
                data.step_count || 11
            );
        }
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

    back() {
        if (!this.isFirstStep) {
            this.state.step -= 1;
            this.state.errorMessage = "";
        }
    }

    _advance() {
        if (!this.isLastStep) {
            this.state.step += 1;
        }
    }

    async saveAndExit() {
        if (this.store.id) {
            await this.orm.call(MODEL, "save_and_exit", [], {
                store_id: this.store.id,
                step_index: this.state.step,
            });
        }
        this.notification.add(
            _t("Setup saved. You can pick up where you left off."),
            { type: "success" }
        );
        this.action.doAction("shopify_connector_core.action_shopify_connector_dashboard");
    }

    /** One handler per step. Each calls exactly one guarded server method. */
    async continueStep() {
        const storeId = this.store.id;
        let ok = false;
        switch (this.state.step) {
            case 1:
                ok = true;
                break;
            case 2:
                ok = await this._call("save_store_identity", {
                    name: this.state.form.name,
                    shop_domain: this.state.form.shopDomain,
                    store_id: storeId || null,
                });
                break;
            case 3:
                // Read from the DOM node and cleared immediately: the token is
                // never bound into component state, so it cannot be read back
                // out of it, serialised into a snapshot or survive a re-render.
                ok = await this._submitCredential();
                break;
            case 4:
                ok = await this._call("acknowledge_scopes", {
                    store_id: storeId,
                });
                break;
            case 5:
                // Continue ADVANCES; it does not run the check. Step 5's
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
            case 6:
                if (!this.readiness.ran) {
                    this.state.errorMessage = _t(
                        "Run the readiness checks before continuing."
                    );
                    return;
                }
                ok = true;
                break;
            case 7:
                ok = await this._call("save_directions", {
                    store_id: storeId,
                    enabled_keys: this.state.form.enabledDomains,
                });
                break;
            case 8:
                ok = await this._call("save_source_of_truth", {
                    store_id: storeId,
                    matching: this.state.form.matching,
                    price: this.state.form.price,
                });
                break;
            case 9:
                ok = await this._call("save_notification", {
                    store_id: storeId,
                    enabled: this.state.form.notification,
                    confirmed: this.state.form.notificationConfirmed,
                });
                break;
            case 10:
                ok = await this._call("save_first_push_schedule", {
                    store_id: storeId,
                    schedule_now: this.state.form.schedulePush,
                });
                break;
            case 11:
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
            this._advance();
        }
    }

    /** Step 5's explicit action. Stays on the step, whatever the outcome. */
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

    /** Step 6's explicit action, and its "re-run readiness" secondary. */
    async runReadiness() {
        await this._call("run_readiness", { store_id: this.store.id });
    }

    async _submitCredential() {
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
        await this._call("restart_setup", { store_id: this.store.id });
        this.state.step = 1;
    }
}

registry.category("actions").add("shopify_connector_setup_wizard", ShopifyConnectorSetupWizard);
