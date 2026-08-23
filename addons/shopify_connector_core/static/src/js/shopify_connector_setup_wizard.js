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
    onWillUnmount,
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

// Finite one-shot backoff: no interval survives the setup session and no
// browser loop claims a background run must finish within an arbitrary time.
const LOCATION_REFRESH_BACKOFF_MS = [250, 500, 1000, 2000];

export class ShopifyConnectorSetupWizard extends Component {
    static template = "shopify_connector_core.SetupWizard";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.direction = localeDirection();
        this.headingRef = useRef("heading");
        this.panelRef = useRef("panel");

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
                scopesRead: false,
                mapShopifyGid: "",
                mapOdooLocationId: "",
                // Which credential path the merchant is entering. Seeded from
                // the store's stored mode on load, so re-running setup shows
                // the path they actually use. The value is a mode NAME, never
                // a secret.
                credentialMode: "dev_dashboard_client_credentials",
            },
            // The location step's bounded server-side search (Wave 5). Kept
            // OUTSIDE `form` so a mapping round trip does not clobber an
            // active search: mapping 5 of 300 locations means searching once
            // and mapping repeatedly. `items: null` means "no search active
            // — render the payload's first page".
            locationSearch: {
                shopify: {
                    query: "", items: null, total: 0, offset: 0,
                    // The server's continuation, echoed back on every page
                    // request. `nextOffset === false` means "exhausted", which
                    // is a different statement from "offset 0".
                    nextOffset: false, continuation: null, emptyReason: "",
                },
                odoo: {
                    query: "", items: null, total: 0, offset: 0,
                    nextOffset: false, continuation: null, emptyReason: "",
                },
            },
            // Per-Shopify-row Odoo choices.  Keeping the choice beside the
            // row removes the old two-list/two-search/global-select puzzle;
            // the server still validates both identities on every save.
            locationMappingChoices: {},
            locationRefreshStillRunning: false,
        });

        this.locationRefreshJobId = null;
        this.locationRefreshFollowGeneration = 0;
        this.locationRefreshTimer = null;
        this.locationRefreshTimerResolve = null;

        onWillStart(async () => {
            await this._load(
                this._contextStoreId(),
                this._contextStartsNewStore(),
            );
        });

        onWillUnmount(() => {
            this.locationRefreshFollowGeneration += 1;
            this._cancelLocationRefreshTimer();
        });

        // A11y: focus moves to the step heading on advance, so a keyboard or
        // screen-reader user lands on the new step's title rather than being
        // left at the bottom of the previous one.
        useEffect(
            () => {
                if (this.panelRef.el) {
                    this.panelRef.el.scrollTop = 0;
                }
                if (this.headingRef.el) {
                    this.headingRef.el.focus();
                }
            },
            // A store swap can leave the semantic step key unchanged (both
            // flows start on Welcome), so the store identity belongs in the
            // dependency list too.
            () => [this.state.stepKey, this.store.id]
        );
    }

    _contextStoreId() {
        const context = (this.props.action && this.props.action.context) || {};
        return context.default_setup_store_id || null;
    }

    _contextStartsNewStore() {
        const context = (this.props.action && this.props.action.context) || {};
        return Boolean(context.default_setup_new_store);
    }

    get steps() {
        return (this.state.data && this.state.data.steps) || [];
    }

    get phases() {
        return (this.state.data && this.state.data.phases) || [];
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
                mapping_complete: false,
                shopify_total: 0,
                odoo_total: 0,
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

    get currentPhase() {
        const key = this.currentStep.phase_key;
        return this.phases.find((phase) => phase.key === key) || {};
    }

    phaseSteps(phase) {
        const keys = new Set(phase.step_keys || []);
        return this.steps.filter((step) => keys.has(step.key));
    }

    phaseClass(phase) {
        let cls = "sc_setup_phase";
        const currentIndex = this.currentPhase.index || 0;
        if (phase.key === this.currentPhase.key) {
            cls += " sc_setup_phase--current";
        } else if (phase.index < currentIndex) {
            cls += " sc_setup_phase--done";
        }
        return cls;
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

    /** One navigation rule, mirrored by the server-side Continue guard. */
    get canContinue() {
        if (
            this.state.stepKey === "location_mapping" &&
            this.currentStepApplies
        ) {
            return Boolean(
                this.refreshState() === "succeeded" &&
                this.locations.mapping_complete
            );
        }
        return true;
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
            stale: _t("Out of date"),
            none: _t("Not run yet"),
        }[this.refreshState()];
    }

    // --- server round trips -------------------------------------------------

    async _load(storeId, newStore = false) {
        try {
            const data = await this.orm.call(MODEL, "get_setup_state", [], {
                store_id: storeId || null,
                new_store: newStore,
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
        this.state.form.mapShopifyGid = "";
        this.state.form.mapOdooLocationId = "";
        // Seed the credential-path choice from what the store already uses, so
        // a rerun opens on the merchant's actual path. A store with no
        // credential yet defaults to the Dev Dashboard path, because that is
        // the app-creation flow Shopify currently gives a new merchant.
        this.state.form.credentialMode = "dev_dashboard_client_credentials";
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

    /**
     * A setup rerun must not turn a stored write-only credential into a
     * mandatory re-entry.  The server deliberately returns only a boolean
     * presence mirror and the non-secret auth mode, so blank fields are the
     * operator's explicit choice to keep the existing credential. The boolean
     * only decides whether to request an action-time, non-secret server check;
     * it never authorizes reuse by itself. Supplying replacement values (or
     * choosing another mode) still takes the normal write-only path below.
     */
    _canReuseStoredCredential() {
        return Boolean(
            this.store.credential_present &&
            this.store.auth_mode === this.state.form.credentialMode
        );
    }

    async _retainExistingCredential() {
        return this._call("retain_existing_credential", {
            store_id: this.store.id,
            auth_mode: this.state.form.credentialMode,
        });
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
     * Location discovery starts on entry because it is part of the step, not
     * an optional utility action. Final readiness evaluates the configuration
     * as it is NOW, not a result recorded before the choices above it changed.
     */
    async _onEnterStep() {
        if (
            this.state.stepKey === "location_mapping" &&
            this.currentStepApplies &&
            this.store.id
        ) {
            const refresh = this.locations.refresh || {};
            if (
                ["waiting", "running"].includes(this.refreshState()) &&
                refresh.job_id
            ) {
                // Keep the screen interactive while the bounded follower
                // updates it in place; mounting must not wait through the
                // polling backoff.
                void this._followLocationRefresh(refresh.job_id);
                return;
            }
            // Cached rows render immediately, but every entry also requests a
            // fresh discovery pass. The server coalesces an equivalent active
            // refresh, so opening/re-entering this screen is the trigger and
            // the merchant never has to know that a manual refresh exists.
            void this.refreshLocations();
            return;
        }
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

    async startNewStore() {
        if (this.state.busy) {
            return;
        }
        this._resetLocationTransientState();
        this.state.busy = true;
        try {
            const data = await this.orm.call(MODEL, "get_setup_state", [], {
                store_id: null,
                new_store: true,
            });
            this._adopt(data, true);
            this.state.stepKey = FIRST_STEP_KEY;
            this.state.errorMessage = "";
        } catch (error) {
            this.state.errorMessage = this._message(error);
        } finally {
            this.state.busy = false;
        }
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
                    schedule_now: true,
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
                    if (["pending", "action_required"].includes(
                        this.store.setup_completion_state
                    )) {
                        this.notification.add(
                            this.store.setup_completion_message ||
                            _t("Setup is waiting for verification before it can be completed."),
                            { type: "warning" }
                        );
                        return;
                    }
                    this.notification.add(
                        _t("Activation started the selected read and import scans. Shopify writes still require their protected confirmation path; the dashboard shows progress and exceptions."),
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

    _resetLocationTransientState() {
        // A store swap must not carry a search result, server continuation,
        // mapping choice or poll handle into the new store's identity flow.
        // Advance the follower generation before cancelling its timer so an
        // already-resolving old-store request cannot resume polling.
        this.locationRefreshFollowGeneration += 1;
        this._cancelLocationRefreshTimer();
        this.locationRefreshJobId = null;
        this.state.locationRefreshStillRunning = false;
        this.state.locationMappingChoices = {};
        this.state.locationSearch = {
            shopify: {
                query: "", items: null, total: 0, offset: 0,
                nextOffset: false, continuation: null, emptyReason: "",
            },
            odoo: {
                query: "", items: null, total: 0, offset: 0,
                nextOffset: false, continuation: null, emptyReason: "",
            },
        };
    }

    _waitForLocationRefresh(delay, generation) {
        return new Promise((resolve) => {
            if (generation !== this.locationRefreshFollowGeneration) {
                resolve();
                return;
            }
            this.locationRefreshTimerResolve = resolve;
            this.locationRefreshTimer = setTimeout(() => {
                this.locationRefreshTimer = null;
                this.locationRefreshTimerResolve = null;
                resolve();
            }, delay);
        });
    }

    _cancelLocationRefreshTimer() {
        if (this.locationRefreshTimer !== null) {
            clearTimeout(this.locationRefreshTimer);
            this.locationRefreshTimer = null;
        }
        if (this.locationRefreshTimerResolve) {
            this.locationRefreshTimerResolve();
            this.locationRefreshTimerResolve = null;
        }
    }

    async _followLocationRefreshOnce(jobId) {
        return this._call("follow_location_refresh", {
            store_id: this.store.id,
            job_id: jobId,
        });
    }

    async _followLocationRefresh(jobId) {
        this._cancelLocationRefreshTimer();
        const generation = ++this.locationRefreshFollowGeneration;
        this.locationRefreshJobId = jobId;
        this.state.locationRefreshStillRunning = false;
        for (const delay of LOCATION_REFRESH_BACKOFF_MS) {
            await this._waitForLocationRefresh(delay, generation);
            if (generation !== this.locationRefreshFollowGeneration) {
                return;
            }
            const ok = await this._followLocationRefreshOnce(jobId);
            if (!ok || generation !== this.locationRefreshFollowGeneration) {
                return;
            }
            if (!["waiting", "running"].includes(this.refreshState())) {
                return;
            }
        }
        if (generation === this.locationRefreshFollowGeneration) {
            this.state.locationRefreshStillRunning = true;
        }
    }

    /** The location step's refresh. Admits a job; contacts nothing from here. */
    async refreshLocations() {
        const ok = await this._call("refresh_shopify_locations", {
            store_id: this.store.id,
        });
        const refresh = this.locations.refresh || {};
        if (ok && refresh.job_id) {
            await this._followLocationRefresh(refresh.job_id);
        }
    }

    async checkLocationRefresh() {
        if (!this.locationRefreshJobId) {
            return;
        }
        const ok = await this._followLocationRefreshOnce(
            this.locationRefreshJobId
        );
        if (ok && ["waiting", "running"].includes(this.refreshState())) {
            this.state.locationRefreshStillRunning = true;
        } else if (ok) {
            this.state.locationRefreshStillRunning = false;
        }
    }

    setLocationMappingChoice(shopifyGid, odooLocationId) {
        this.state.locationMappingChoices[shopifyGid] = odooLocationId;
        this.state.errorMessage = "";
    }

    /** The location step's create. Both identities explicit, both server-checked. */
    async createMapping(shopifyGid = null) {
        const selectedShopifyGid = shopifyGid || this.state.form.mapShopifyGid;
        const selectedOdooLocationId = shopifyGid
            ? this.state.locationMappingChoices[shopifyGid]
            : this.state.form.mapOdooLocationId;
        if (!selectedShopifyGid) {
            this.state.errorMessage = _t("Choose a Shopify location to map.");
            return;
        }
        if (!selectedOdooLocationId) {
            this.state.errorMessage = _t("Choose an Odoo location to map it to.");
            return;
        }
        // A selection the operator can no longer SEE must never be submitted.
        // `<select>` retains an assigned value after its `<option>` is gone, so
        // searching away from a chosen location used to leave the identity in
        // `state.form`, off screen, and send it on the next click.
        if (!shopifyGid) {
            this._revalidateLocationSelection("shopify");
            this._revalidateLocationSelection("odoo");
        }
        if (
            !this.visibleShopifyLocations.some(
                (row) => row.shopify_gid === selectedShopifyGid
            ) ||
            !this.visibleOdooLocations.some(
                (row) => String(row.id) === String(selectedOdooLocationId)
            )
        ) {
            this.state.errorMessage = _t(
                "The location you had chosen is no longer in the list on " +
                "screen, so nothing was mapped. Choose from the current list."
            );
            return;
        }
        const mappedGid = selectedShopifyGid;
        const mappedOdooId = parseInt(selectedOdooLocationId, 10);
        const mappedOdooName = (
            this.visibleOdooLocations.find(
                (row) => row.id === mappedOdooId
            ) || {}
        ).name || "";
        const ok = await this._call("save_location_mapping", {
            store_id: this.store.id,
            shopify_location_gid: mappedGid,
            odoo_location_id: mappedOdooId,
        });
        if (ok) {
            this.state.form.mapShopifyGid = "";
            this.state.form.mapOdooLocationId = "";
            delete this.state.locationMappingChoices[mappedGid];
            // Update the affected row IN PLACE rather than re-running the
            // search. Re-running it fetched a single page at the LAST requested
            // offset and replaced the accumulated results with it, so an
            // operator who had paged to row 150 and then mapped one location
            // watched rows 0-150 vanish and be replaced by rows 100-150. The
            // only thing a mapping changes about a row is its badge and its
            // target, and both are known here.
            for (const search of Object.values(this.state.locationSearch)) {
                if (search.items === null) {
                    continue;
                }
                for (const row of search.items) {
                    if (row.shopify_gid === mappedGid) {
                        row.mapped = true;
                        row.odoo_location_id = mappedOdooId;
                        row.odoo_location_name = mappedOdooName;
                    }
                }
            }
        }
    }

    // --- the location step's bounded server-side search ---------------------

    /** The rows the Shopify list/select actually renders. */
    get visibleShopifyLocations() {
        const search = this.state.locationSearch.shopify;
        return search.items !== null ? search.items : this.locations.locations;
    }

    /** The rows the Odoo select actually renders. */
    get visibleOdooLocations() {
        const search = this.state.locationSearch.odoo;
        return search.items !== null
            ? search.items
            : this.locations.odoo_locations;
    }

    /** Totals for the honest "Showing X of Y" line. */
    locationShowing(side) {
        const search = this.state.locationSearch[side];
        if (search.items !== null) {
            return { shown: search.items.length, total: search.total };
        }
        if (side === "shopify") {
            return {
                shown: this.locations.locations.length,
                total: this.locations.shopify_total ||
                    this.locations.locations.length,
            };
        }
        return {
            shown: this.locations.odoo_locations.length,
            total: this.locations.odoo_total ||
                this.locations.odoo_locations.length,
        };
    }

    locationHasMore(side) {
        const search = this.state.locationSearch[side];
        if (search.items !== null) {
            // The SERVER decides whether there is another page.
            return Boolean(search.nextOffset);
        }
        const showing = this.locationShowing(side);
        return showing.shown < showing.total;
    }

    /** Search is progressive disclosure, not empty-page furniture. */
    showLocationSearch(side) {
        const search = this.state.locationSearch[side];
        const total = side === "shopify"
            ? this.locations.shopify_total
            : this.locations.odoo_total;
        return search.items !== null || (total || 0) > 10;
    }

    async searchLocations(side) {
        await this._searchLocations(side, { offset: 0, append: false });
    }

    /** Enter in a search box searches; nothing else is intercepted. */
    async onLocationSearchKeydown(ev, side) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            // Awaited. Fire-and-forget meant an Enter-key search raced whatever
            // the operator did next, and its rejection had nowhere to go.
            await this.searchLocations(side);
        }
    }

    async loadMoreLocations(side) {
        const search = this.state.locationSearch[side];
        if (search.items !== null && !search.nextOffset) {
            // The server said the set is exhausted. Asking again would fetch
            // page 0 and append it to what is already shown.
            return;
        }
        await this._searchLocations(side, {
            // THE SERVER'S continuation, never the length of our own array.
            // Deriving the next offset from `items.length` is the same number
            // only while nothing else is true: a short page, a row removed
            // between pages, or two responses arriving out of order all make it
            // diverge, and the failure is silently skipped or duplicated
            // locations in the one list whose purpose is that every eligible
            // location is reachable.
            offset: search.items === null ? 0 : search.nextOffset,
            append: search.items !== null,
        });
    }

    clearLocationSearch(side) {
        // The SAME serialization the search itself obeys, and for a sharper
        // reason. Clearing is not a server call, so it looked safe to leave
        // outside the discipline -- but a clear issued while a search is in
        // flight is UNDONE by the response that arrives after it: the handler
        // assigns `search.items` unconditionally, so the operator is left with
        // an empty query box, the old query's results beneath it, and a
        // continuation token belonging to a query that is no longer displayed.
        // The next Load more then sends that token with an empty query and is
        // refused by the server, which is a refusal with no visible cause.
        if (this.state.busy) {
            return;
        }
        this.state.locationSearch[side] = {
            query: "",
            items: null,
            total: 0,
            offset: 0,
            nextOffset: false,
            continuation: null,
            // Every key the initial state declares, so a cleared side and a
            // never-searched side are the same SHAPE and not merely the same
            // to look at. `emptyReason` was the one omission, and a state
            // object that loses a key on a routine operator action is how a
            // reader of `search.emptyReason` starts seeing `undefined`.
            emptyReason: "",
        };
        // Clearing changes what is on screen, so a selection made inside the
        // cleared results may no longer be there.
        this._revalidateLocationSelection(side);
    }

    /**
     * Drop a selected identity the operator can no longer see.
     *
     * A `<select>` keeps whatever value was assigned to it even when the
     * matching `<option>` is gone, so searching away from a chosen location
     * left the GID (or the Odoo location id) sitting in `state.form`,
     * invisible, and the next Create mapping submitted it. The server would
     * still refuse an ineligible one -- the mapping service validates the GID
     * against this store's active cache and the Odoo location against the
     * caller's own rights -- but "the server catches it" is not the same as
     * "the operator mapped the location they were looking at", and a refusal
     * they cannot see the cause of is the worse outcome of the two.
     */
    _revalidateLocationSelection(side) {
        if (side === "shopify") {
            const visibleGids = new Set(
                this.visibleShopifyLocations.map((row) => row.shopify_gid)
            );
            for (const gid of Object.keys(this.state.locationMappingChoices)) {
                if (!visibleGids.has(gid)) {
                    delete this.state.locationMappingChoices[gid];
                }
            }
            const gid = this.state.form.mapShopifyGid;
            if (gid && !visibleGids.has(gid)) {
                this.state.form.mapShopifyGid = "";
            }
            return;
        }
        const visibleIds = new Set(
            this.visibleOdooLocations.map((row) => String(row.id))
        );
        for (const [gid, selectedId] of Object.entries(
            this.state.locationMappingChoices
        )) {
            if (selectedId && !visibleIds.has(String(selectedId))) {
                delete this.state.locationMappingChoices[gid];
            }
        }
        const id = this.state.form.mapOdooLocationId;
        if (id && !visibleIds.has(String(id))) {
            this.state.form.mapOdooLocationId = "";
        }
    }

    async _searchLocations(side, { offset, append }) {
        if (!this.store.id) {
            return;
        }
        // The SAME serialization every other wizard operation uses. Search was
        // the one call that bypassed `state.busy` entirely, so two searches
        // could be in flight at once and the later-resolving response won
        // regardless of which query it answered -- and the `disabled` bindings
        // on the Search and Load more buttons were inert, because nothing ever
        // set `busy` for them.
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const search = this.state.locationSearch[side];
            const page = await this.orm.call(MODEL, "search_location_options", [], {
                store_id: this.store.id,
                side,
                query: search.query || "",
                offset,
                continuation: offset ? search.continuation : null,
            });
            search.total = page.total;
            search.offset = page.offset;
            search.nextOffset = page.next_offset;
            search.continuation = page.continuation;
            search.emptyReason = page.empty_reason || "";
            if (append && search.items !== null) {
                // Belt and braces against a duplicate row even if a page were
                // ever served twice: identity, not position, decides.
                const seen = new Set(
                    search.items.map((row) => this._locationKey(side, row))
                );
                search.items = search.items.concat(
                    page.items.filter(
                        (row) => !seen.has(this._locationKey(side, row))
                    )
                );
            } else {
                search.items = page.items;
            }
            this.state.errorMessage = "";
            this._revalidateLocationSelection(side);
        } catch (error) {
            this.state.errorMessage = this._message(error);
        } finally {
            this.state.busy = false;
        }
    }

    _locationKey(side, row) {
        return side === "shopify" ? row.shopify_gid : String(row.id);
    }

    /** Why a list is empty, in the operator's words. Never one generic line. */
    locationEmptyReason(side) {
        const search = this.state.locationSearch[side];
        const reason = search.items !== null ? search.emptyReason : "";
        switch (reason) {
            case "no_results":
                return _t(
                    "No location matches this search. Clear the search to see " +
                    "the full list again, or try part of the name."
                );
            case "no_inventory_permission":
                return _t(
                    "You do not have access to Odoo's Inventory locations, so " +
                    "none can be listed. Ask an Odoo administrator for " +
                    "Inventory access."
                );
            case "no_cached_locations":
                return _t(
                    "No Shopify locations have been read for this store yet. " +
                    "Use Try again if automatic loading did not finish."
                );
            case "no_eligible_odoo_locations":
                return _t(
                    "There are no internal Odoo locations in this company yet. " +
                    "Create a warehouse first."
                );
            default:
                return "";
        }
    }

    async _submitCredential() {
        if (this.state.form.credentialMode === "dev_dashboard_client_credentials") {
            return this._submitClientCredentials();
        }
        const input = document.querySelector(".sc_setup_token");
        const value = input ? input.value : "";
        if (!value && this._canReuseStoredCredential()) {
            return this._retainExistingCredential();
        }
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
        if (!clientId && !clientSecret && this._canReuseStoredCredential()) {
            return this._retainExistingCredential();
        }
        try {
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
            if (ok && idInput) {
                idInput.value = "";
            }
            return ok;
        } finally {
            // Clear on every non-reuse path, including local validation. A
            // secret must not remain in a password input just because another
            // field was missing and no RPC was issued.
            if (secretInput) {
                secretInput.value = "";
            }
        }
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
