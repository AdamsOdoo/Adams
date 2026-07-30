#!/usr/bin/env bash
#
# Reproducible full-suite execution for the Odoo 19 <-> Shopify connector.
#
# DEC-041 D8 authorises "a minimal install-and-run-suites workflow on push/PR".
# The workflow in .github/workflows/connector-tests.yml is a thin wrapper around
# THIS script, deliberately: the same command must be runnable on a laptop, in a
# container, and in CI, or CI becomes a separate thing that drifts from what
# anyone can reproduce locally.
#
# What it does
#   1. checks out the EXACT Odoo commit pinned in tools/odoo-pin.txt, and
#      verifies it on every run so a cached checkout can never silently execute
#      a different Odoo
#   2. installs the connector modules into a disposable PostgreSQL database
#   3. runs THREE passes, each into its own database with its own log:
#        * fresh install + standard suite
#        * warm `-u` update + standard suite (issue #193: not interchangeable)
#        * the complete NON-STANDARD tag suite
#   4. verifies the checked-out connector commit against the commit the caller
#      says this run is testing ($SOURCE_HEAD_SHA), and ABORTS on a mismatch
#   5. writes durable per-pass logs and a machine-readable summary under
#      $ARTIFACT_DIR, recording the tested checkout SHA, the declared source
#      head and base, the event type, the worktree state, the exact Odoo SHA
#      and the Python/PostgreSQL versions
#
# Why the third pass exists. Eight connector test classes are tagged
# `-standard`, which is correct -- they are expensive and some spawn real OS
# processes -- but it also means `--test-enable` alone NEVER runs them. Four of
# them are the genuine concurrency proofs. Before this, running them required an
# operator to remember an optional `--tags` argument, so in practice they were
# never run at all and "full suite green" silently excluded them. They are now
# part of the default run and the tag list lives in this file, next to the code
# that uses it.
#
# What it deliberately does NOT do
#   * no Shopify store, credential, request, or mutation -- ever. There is no
#     code path here that reads a Shopify secret, and CI must never be given one.
#   * it does NOT replace Odoo.sh. Until equivalence is separately proven, the
#     exact-SHA Odoo.sh run remains the Tier-1 acceptance authority (DEC-041 D8).
#     This script produces supporting evidence, not acceptance.
#
# Usage
#   tools/run_connector_suite.sh [--fresh-only|--warm-only] [--skip-nonstandard]
#                                [--tags <extra-test-tags>]
#   tools/run_connector_suite.sh --self-test    # fail-closed assertions only
#
# Environment
#   ODOO_SRC      path to an odoo/odoo checkout (cloned if absent)
#   ODOO_PIN      immutable Odoo commit         (default: tools/odoo-pin.txt)
#   PGHOST/PGPORT PostgreSQL connection         (default: /tmp, 5432)
#   ARTIFACT_DIR  where logs/summary land       (default: ./ci-artifacts)
#   PYTHON        interpreter for the venv      (default: python3.12, else python3)
#   SOURCE_HEAD_SHA   commit this run is meant to test; verified, abort on
#                     mismatch (CI sets it; a laptop run normally does not)
#   SOURCE_BASE_SHA / SOURCE_EVENT_NAME / SOURCE_PR_NUMBER / SOURCE_RUN_URL
#                     recorded verbatim in the summary as provenance

set -euo pipefail

MODULES="shopify_connector_core,shopify_connector_product,shopify_connector_sale,shopify_connector_inventory,shopify_connector_fulfillment,shopify_connector_product_export"
# `account` and `stock` are installed explicitly. They are NOT connector
# dependencies, and that is exactly the point: they contribute the required
# columns behind issue #193, so a suite that omits them cannot reproduce the
# warm-update failure family it is supposed to guard.
EXTRA_MODULES="account,stock"

# The complete set of connector test tags that carry `-standard`. Every entry
# here is a test class that `--test-enable` alone will NOT run.
#
# `shopify_connector_hoot` (added 2026-07-26) runs the connector's HOOT unit
# suites in a real browser. `shopify_connector_visual` (added 2026-07-27)
# captures the rendered accessibility/visual evidence. Both are `-standard`
# because they build the full asset bundle and boot Chrome, which is exactly
# this list's cost profile.
#
# TD-010 IS CLOSED BELOW, NOT HERE. An `HttpCase` test SKIPS -- it does not
# fail -- when `websocket-client` is absent or no Chrome/Chromium resolves, and
# a skip still reports `0 failed, 0 error(s)`. That is the most dangerous shape
# a result can take. This script now installs `websocket-client`, resolves the
# browser explicitly, PROVES both before running anything browser-bearing, and
# FAILS on an unexpected skip, a missing tour, or a missing HOOT marker. See
# `preflight_browser` and `verify_browser_evidence`.
#
# Keep this list in sync with docs/05-qa/pre-wave-5-debt-discovery.md §3; the
# guard test `test_phase_contract.py` fails if a `-standard` class exists that
# no tag here selects, so the two cannot drift apart silently.
# `shopify_connector_export_mutation_route` (added 2026-07-27) drives the real
# Layer 2 mutation route through `run_drain()` to prove TD-013's expiry guard is
# bound into the production dispatch path and not merely into a helper. It is
# `-standard` because that route commits between C1 and C2 by design and so
# needs a genuine pooled connection, which the shared in-test cursor is not.
# `shopify_connector_export_reconcile_race` (added 2026-07-27) is the TD-015
# cross-transaction settlement proof: two genuine independent connections, a
# real SQLSTATE 40001, the dispatcher's bounded re-drive, and a sensitivity
# case that strands the store with the serialization boundary removed. It is
# `-standard` for the same reason and a stronger one -- a serialization
# failure cannot occur on a single shared connection at all.
# `shopify_connector_credential_provenance_race` (added 2026-07-30) is the
# Batch 1 obsolete-token proof. It is `-standard` for the same reason as the two
# above and one specific to it: `pg_try_advisory_xact_lock` is RE-GRANTABLE
# within a single PostgreSQL session, so on the shared in-test connection the
# refresh's losing/waiter branch cannot execute at all and a rotation cannot
# overtake the exchange it is racing. This class opens genuine `db_connect`
# sessions with distinct backend PIDs, and its first half is written to run
# unchanged against the vulnerable head as a before/after reproducer.
NONSTANDARD_TAGS="shopify_connector_product_callsite_lifecycle,sc010b_performance,shopify_connector_customer_matching_benchmark,shopify_connector_customer_matching_concurrency,shopify_connector_customer_callsite_lifecycle,shopify_connector_order_discovery_concurrency,shopify_connector_drain_throughput,shopify_connector_hoot,shopify_connector_visual,shopify_connector_export_mutation_route,shopify_connector_export_reconcile_race,shopify_connector_credential_provenance_race"

# --- The browser-evidence contract (TD-010) ----------------------------------
#
# Odoo's console marker for a passing tour is the bare string "tour succeeded"
# with NO tour name in it (`web_tour/static/src/js/tour_service.js` at the pin),
# so a tour cannot be attributed from the marker alone. Attribution is by TEST
# identity instead, which `OdooTestResult` logs as `Starting <Class>.<method>`.
#
# This list is the expected inventory. The guard test
# `test_phase_contract.py::test_every_tour_test_is_listed_in_the_suite_runner`
# asserts it equals the set of test methods that actually call `start_tour`, so
# adding a tour without listing it here -- or dropping one -- fails a test
# rather than silently shrinking browser coverage.
REQUIRED_TOUR_TESTS="\
TestUiTours.test_navigation_tour \
TestUiTours.test_u2_navigation_tour \
TestUiU2InventoryActionTours.test_first_push_confirm_tour \
TestUiU2InventoryActionTours.test_first_push_reaches_confirmed_from_a_genuine_pending_pair \
TestUiU2InventoryActionTours.test_first_push_withdraw_tour_returns_the_pair_to_pending \
TestUiU2InventoryActionTours.test_location_withdraw_all_tour_returns_every_pair_to_pending \
TestUiU2InventoryActionTours.test_location_withdraw_all_refuses_a_decision_made_against_stale_state \
TestUiU2InventoryActionTours.test_location_withdraw_all_control_is_absent_for_a_connector_user \
TestUiU2InventoryActionTours.test_single_pair_withdrawal_refuses_a_decision_made_against_stale_state \
TestUiU2InventoryActionTours.test_first_push_pending_offers_no_control_tour \
TestUiU2InventoryActionTours.test_first_push_denied_for_a_role_the_server_refuses \
TestUiU2InventoryActionTours.test_push_toggle_tour \
TestUiU2InventoryActionTours.test_recheck_tour_enqueues_exactly_one_successor \
TestUiU2InventoryActionTours.test_recheck_blank_reason_is_refused_in_the_browser \
TestUiU2InventoryActionTours.test_quarantined_pair_is_not_reachable_by_an_operator \
TestUiU2SaleActionTours.test_order_approval_tour \
TestUiU2SaleActionTours.test_order_approval_denied_for_a_role_the_server_refuses \
TestU3ExportTours.test_export_navigation_tour \
TestU3ExportTours.test_export_review_tour_discloses_before_it_offers \
TestU3ExportTours.test_export_review_surface_is_keyboard_reachable \
TestU3ExportTours.test_media_resume_tour_reaches_the_resume_from_the_browser \
TestU3ExportTours.test_td015_checksum_acknowledgement_tour \
TestUiSetupTours.test_setup_wizard_traverses_all_twelve_steps \
TestUiSetupTours.test_the_dashboard_empty_state_opens_setup \
TestUiSetupTours.test_setup_resumes_at_the_step_it_was_left_on \
TestUiSetupTours.test_setup_is_operable_by_keyboard_alone \
TestUiSetupTours.test_the_location_step_shows_every_cached_location_and_maps_one \
TestUiSetupTours.test_a_blocking_readiness_row_deep_links_by_step_key"

# The HOOT suites, by the exact name `test_u3_hoot_suite.py` re-emits after it
# has verified each one. Keep in step with EXPECTED_SUITES in that file.
REQUIRED_HOOT_SUITES="shopify connector dashboard|shopify connector export diff|shopify connector setup wizard"

# THE ONE SANCTIONED SKIP. Bound to an exact test identity and an exact reason,
# deliberately: a general "one skip is allowed" rule would let ANY test skip,
# which is the hole TD-010 is about. This test is gated on
# SHOPIFY_LAYER2_RUN_PROCESS_DEATH=1 because it spawns and kills real OS
# processes (`test_mutation_recovery.py`).
ALLOWED_SKIP_TEST="TestMutationRecovery.test_real_process_death_harness"
ALLOWED_SKIP_REASON="real process-death harness is opt-in outside Odoo.sh"

# Restrict the STANDARD passes to the connector modules.
#
# `--test-enable` with no selector runs every installed module's tests --
# including the whole of `base`, `account` and `stock`. That is thousands of
# upstream Odoo tests which this repository does not own, cannot fix, and whose
# runtime does not fit any sane CI budget. Odoo's `/module` selector keeps the
# passes to the code this PR is responsible for. `account` and `stock` are still
# INSTALLED (see EXTRA_MODULES) -- they must be, or the #193 warm-update failure
# family cannot reproduce -- they are simply not re-tested here.
STANDARD_TAGS="/shopify_connector_core,/shopify_connector_product,/shopify_connector_sale,/shopify_connector_inventory,/shopify_connector_fulfillment,/shopify_connector_product_export"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ODOO_SRC="${ODOO_SRC:-${REPO_ROOT}/.odoo-src}"
ODOO_PIN_FILE="${REPO_ROOT}/tools/odoo-pin.txt"
ARTIFACT_DIR="${ARTIFACT_DIR:-${REPO_ROOT}/ci-artifacts}"
PGHOST="${PGHOST:-/tmp}"
PGPORT="${PGPORT:-5432}"
export PGHOST PGPORT

RUN_FRESH=1
RUN_WARM=1
RUN_NONSTANDARD=1
RUN_SELF_TEST=0
TEST_TAGS=""
# --- The migration passes (2026-07-30) ---------------------------------------
#
# WHY PASS 2 IS NOT A MIGRATION TEST, AND NEVER WAS.
#
# Pass 2 clones the database pass 1 installed and runs `-u` against the SAME
# working tree. `ir_module_module.latest_version` therefore already equals the
# manifest version, and Odoo's migration manager only runs a script when the
# installed version is STRICTLY LOWER
# (`odoo/modules/migration.py::migrate_module` -> `compare()`:
# `parsed_installed_version < parse_version(full_version) <= current_version`).
# So pass 2 executes ZERO `pre-migrate.py`/`post-migrate.py` files, by
# construction, on every run.
#
# That is not a defect in pass 2 -- it exists to catch the issue #193 warm-update
# registry family and it does. The defect was reporting it as migration
# evidence: PR #204's batch-1 records state "warm `-u` update + standard suite
# (migration 19.0.1.16.0 executed)" for a run in which that script provably did
# not execute. This block is the correction. `MIGRATION_FROM_REFS` names commits
# whose trees carry LOWER manifest versions, each is installed from its own
# extracted tree, and the candidate tree is then upgraded onto it -- which is the
# only shape in which a migration script runs at all.
#
# Proof, not inference: Odoo logs `module <addon>: Running upgrade <version>
# <name>` for every script it executes (migration.py at the pin), and
# `verify_migration_evidence` FAILS a migration pass that produced no such line
# for a connector module. The warm pass asserts the opposite -- that no such
# line appears -- so the two passes can never be confused for one another again.
#
#   50b770a3  the pre-client-credentials baseline this batch started from
#   0a15b176  the vulnerable deployed shape this correction changes
MIGRATION_FROM_REFS=(
    "50b770a315b53f0c05f0b8867bb801d75c6476ef"
    "0a15b176e60b77bf2f40195a9961591c788e14f8"
)
RUN_MIGRATION=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fresh-only)       RUN_WARM=0; RUN_NONSTANDARD=0; RUN_MIGRATION=0; shift ;;
        --warm-only)        RUN_FRESH=0; RUN_NONSTANDARD=0; RUN_MIGRATION=0; shift ;;
        # Deliberately opt-OUT, never opt-in. Forgetting a flag must never be
        # the reason a concurrency proof went unrun.
        --skip-nonstandard) RUN_NONSTANDARD=0; shift ;;
        # Same rule, same reason: opt-OUT only. A run that skips the genuine
        # version-to-version upgrade must say so in the summary, which it does.
        --skip-migration)   RUN_MIGRATION=0; shift ;;
        --migration-only)   RUN_FRESH=0; RUN_WARM=0; RUN_NONSTANDARD=0; shift ;;
        # Override the upgrade origins (space-separated refs), for a one-off
        # check against some other ancestor.
        --migration-from)   read -r -a MIGRATION_FROM_REFS <<< "$2"; shift 2 ;;
        # Proves the fail-closed checks actually fail. No database, no browser,
        # no Odoo: runs against synthetic logs and exits. See `self_test`.
        --self-test)        RUN_SELF_TEST=1; shift ;;
        --tags)             TEST_TAGS="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

log() { printf '[connector-suite] %s\n' "$*"; }

# --- Browser resolution and preflight (TD-010) -------------------------------
#
# Odoo resolves a browser by trying `google-chrome`, `chromium`,
# `chromium-browser` and `google-chrome-stable` ON PATH, and raises
# `unittest.SkipTest("Chrome executable not found")` when none matches
# (odoo/tests/common.py::_find_executable at the pin). `ODOO_BROWSER_BIN`
# short-circuits that lookup, and it is the only form that is reproducible:
# a machine whose Chromium lives at a path under none of those four names --
# a Playwright bundle, for instance -- silently skipped every browser test.
resolve_browser() {
    if [[ -n "${ODOO_BROWSER_BIN:-}" ]]; then
        echo "$ODOO_BROWSER_BIN"; return 0
    fi
    local candidate
    for candidate in google-chrome chromium chromium-browser google-chrome-stable; do
        if command -v "$candidate" >/dev/null 2>&1; then
            command -v "$candidate"; return 0
        fi
    done
    # Playwright's bundle, which this repository's containers ship.
    for candidate in /opt/pw-browsers/chromium-*/chrome-linux/chrome \
                     /opt/pw-browsers/chromium; do
        if [[ -x "$candidate" ]]; then echo "$candidate"; return 0; fi
    done
    return 1
}

# Prove the browser prerequisites BEFORE running anything that needs them.
# A skip discovered afterwards is a green run that proved nothing; a failure
# here is a red run that says exactly what is missing.
preflight_browser() {
    log "browser preflight"

    if [[ "$WEBSOCKET_VERSION" == "missing" ]]; then
        log "FATAL: websocket-client is not importable in ${VENV}."
        log "Every HttpCase browser test would SKIP -- and a skip still reports"
        log "'0 failed, 0 error(s)', so the run would look green while proving"
        log "nothing. Refusing to run (TD-010)."
        exit 2
    fi

    if ! ODOO_BROWSER_BIN="$(resolve_browser)"; then
        log "FATAL: no Chrome/Chromium could be resolved."
        log "Odoo would raise SkipTest('Chrome executable not found') for every"
        log "browser test and still report a green suite. Install Chromium or"
        log "set ODOO_BROWSER_BIN. Refusing to run (TD-010)."
        exit 2
    fi
    export ODOO_BROWSER_BIN
    if [[ ! -x "$ODOO_BROWSER_BIN" ]]; then
        log "FATAL: ODOO_BROWSER_BIN=${ODOO_BROWSER_BIN} is not executable."
        exit 2
    fi
    BROWSER_VERSION="$("$ODOO_BROWSER_BIN" --version 2>&1 | head -1 || true)"
    if [[ -z "$BROWSER_VERSION" ]]; then
        log "FATAL: ${ODOO_BROWSER_BIN} did not report a version, so it is not"
        log "a working browser binary."
        exit 2
    fi

    # The binary existing is not the same as the binary STARTING. A sandbox
    # that forbids user namespaces, or a missing shared library, produces a
    # binary that resolves and then dies -- which Odoo also turns into a skip.
    local probe_dir
    probe_dir="$(mktemp -d)"
    if ! "$ODOO_BROWSER_BIN" --headless=new --no-sandbox --disable-gpu \
            --disable-dev-shm-usage --user-data-dir="$probe_dir" \
            --dump-dom about:blank >/dev/null 2>&1; then
        rm -rf "$probe_dir"
        log "FATAL: ${ODOO_BROWSER_BIN} resolves but cannot render a page"
        log "headlessly. Odoo would turn the failed connection into a SkipTest."
        exit 2
    fi
    rm -rf "$probe_dir"

    log "browser: ${ODOO_BROWSER_BIN} (${BROWSER_VERSION})"
    log "websocket-client: ${WEBSOCKET_VERSION}"
}

# --- Browser-evidence verification (TD-010) ----------------------------------
#
# The whole point of TD-010: a browser test that did not execute must make this
# script exit non-zero. Odoo will not do it -- a skipped `HttpCase` is not a
# failure to unittest -- so the log is inspected after every pass.
#
# `EVIDENCE_ERRORS` accumulates rather than exiting on the first problem, so one
# run reports every missing piece instead of one per re-run.
EVIDENCE_ERRORS=()

evidence_fail() { EVIDENCE_ERRORS+=("$1"); log "EVIDENCE FAILURE: $1"; }

# Any skip that is not the single sanctioned one fails the run.
verify_no_unexpected_skips() {  # verify_no_unexpected_skips <log> <label>
    local logfile="$1" label="$2" occurrence identity
    # `OdooTestResult.addSkip` logs `skipped <Class>.<method> : <reason>`.
    #
    # Match per OCCURRENCE, not per LINE. The previous version extracted one
    # identity per line with a greedy `^.*`, which binds to the LAST skip on
    # the line, and tested the reason as a substring of the WHOLE line. Two
    # skips on one line therefore checked the last one and silently swallowed
    # the first:
    #
    #   ... skipped RealTest.test_x : Chrome not found; skipped \
    #       TestMutationRecovery.test_real_process_death_harness : real \
    #       process-death harness is opt-in outside Odoo.sh
    #
    # extracted the sanctioned identity, matched the sanctioned reason, and
    # `continue`d -- hiding a real browser skip, which is exactly the failure
    # TD-010 exists to prevent. `grep -o` emits every occurrence separately,
    # so identity and reason are always read from the SAME skip.
    #
    # `Subtest` lines are matched too. `OdooTestResult.getDescription` renders
    # a subtest as `Subtest <Class>.<method> (<params>) : <reason>`, which the
    # old pattern did not match at all, so every subtest skip was invisible.
    while IFS= read -r occurrence; do
        [[ -z "$occurrence" ]] && continue
        identity="$(sed -E 's/^skipped (Subtest )?([A-Za-z0-9_]+\.[A-Za-z0-9_]+).*$/\2/' <<<"$occurrence")"
        if [[ "$identity" == "$ALLOWED_SKIP_TEST" \
              && "$occurrence" == *"$ALLOWED_SKIP_REASON"* ]]; then
            log "${label}: sanctioned skip ${identity}"
            continue
        fi
        evidence_fail "${label}: unexpected skipped test -> ${occurrence#skipped }"
    done < <(grep -oE 'skipped (Subtest )?[A-Za-z0-9_]+\.[A-Za-z0-9_]+[^:]* : [^;]*' "$logfile" || true)
}

# Every required tour test must have STARTED and the run must contain one
# "tour succeeded" marker per required tour.
verify_tour_evidence() {  # verify_tour_evidence <log> <label>
    local logfile="$1" label="$2" test_id missing=0 expected=0 seen
    for test_id in $REQUIRED_TOUR_TESTS; do
        expected=$((expected + 1))
        if ! grep -q "Starting ${test_id} \.\.\." "$logfile"; then
            evidence_fail "${label}: required tour test ${test_id} never ran"
            missing=$((missing + 1))
        fi
    done
    seen="$(grep -c 'tour succeeded' "$logfile" || true)"
    log "${label}: ${seen} tour success markers, ${expected} required tours"
    if [[ "$seen" -lt "$expected" ]]; then
        evidence_fail "${label}: ${seen} 'tour succeeded' markers for ${expected} required tours -- a tour did not execute"
    fi
    return 0
}

# Both HOOT suites must have executed. `test_u3_hoot_suite.py` verifies the
# marker and the exact test count itself and re-emits a line this can read;
# see the note in that file about `assertLogs` swallowing the console.
verify_hoot_evidence() {  # verify_hoot_evidence <log> <label>
    local logfile="$1" label="$2" suite
    while IFS= read -r suite; do
        [[ -z "$suite" ]] && continue
        if ! grep -q "CONNECTOR-HOOT-EVIDENCE suite=\"${suite}\".*marker=ok" "$logfile"; then
            evidence_fail "${label}: HOOT suite '${suite}' produced no verified evidence line"
        else
            log "${label}: HOOT suite '${suite}' verified"
        fi
    done < <(tr '|' '\n' <<<"$REQUIRED_HOOT_SUITES")
}

# --- Migration evidence (2026-07-30) -----------------------------------------
#
# The one marker Odoo itself emits when it EXECUTES an upgrade script:
#   `module <addon>: Running upgrade <fmt_version> <name>`
# (`odoo/modules/migration.py` at the pin). Anything weaker -- "the pass was
# green", "the version is right", "a migrations/ directory exists" -- is
# compatible with zero scripts having run, which is exactly the false claim this
# check exists to make impossible.
MIGRATION_MARKER='Running upgrade'

# Every connector-module `Running upgrade` line in a log, one per line.
migration_lines() {  # migration_lines <log>
    grep -oE "module (shopify_connector_[a-z_]+): ${MIGRATION_MARKER} [^ ]+ [^ ]+" \
        "$1" 2>/dev/null || true
}

# A migration pass that ran no script proved nothing and must fail.
verify_migration_evidence() {  # verify_migration_evidence <log> <label>
    local logfile="$1" label="$2" lines count
    lines="$(migration_lines "$logfile")"
    count="$(printf '%s' "$lines" | grep -c . || true)"
    if [[ "$count" -eq 0 ]]; then
        evidence_fail "${label}: no connector migration script executed -- a \
version-to-version upgrade that runs zero scripts is not migration evidence"
        return 0
    fi
    log "${label}: ${count} connector migration script(s) executed"
    while IFS= read -r line; do
        [[ -n "$line" ]] && log "${label}:   ${line}"
    done <<<"$lines"
    return 0
}

# The inverse assertion, for the same-version warm pass. If this ever finds a
# marker, the warm pass has stopped being a same-version update and the summary's
# description of it is wrong -- which is a reason to fail, not to relabel.
verify_no_migration_ran() {  # verify_no_migration_ran <log> <label>
    local logfile="$1" label="$2" lines
    lines="$(migration_lines "$logfile")"
    if [[ -n "$lines" ]]; then
        evidence_fail "${label}: a migration script executed during a \
SAME-VERSION update, so this pass is not the thing the summary calls it: ${lines}"
    else
        log "${label}: same-version update, zero migration scripts (expected)"
    fi
    return 0
}

# --- Fail-closed self-test (TD-010 regression verification) ------------------
#
# TD-010 is not closed by "the runner now checks"; it is closed by proving the
# checks FAIL when they should. These assertions run against synthetic logs, so
# they need no database, no browser and no Odoo -- they are deterministic and
# take milliseconds, which is why `test_suite_runner_fails_closed.py` can run
# them as an ordinary unit test on every pass.
#
# Invoked as `tools/run_connector_suite.sh --self-test`; exits before any
# Odoo, venv or PostgreSQL work.
self_test() {
    local tmp failures=0
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' RETURN

    _expect() {  # _expect <expected-error-count> <description>
        local want="$1" desc="$2" got="${#EVIDENCE_ERRORS[@]}"
        if [[ "$got" -eq "$want" ]]; then
            log "self-test PASS: ${desc}"
        else
            log "self-test FAIL: ${desc} (expected ${want} errors, got ${got})"
            failures=$((failures + 1))
        fi
        EVIDENCE_ERRORS=()
    }

    # A log with every required tour, both HOOT suites and only the sanctioned
    # skip is the one shape that must pass.
    local good="${tmp}/good.log" t
    : > "$good"
    for t in $REQUIRED_TOUR_TESTS; do
        printf 'INFO db mod: Starting %s ...\n' "$t" >> "$good"
        printf 'INFO db mod.browser: tour succeeded\n' >> "$good"
    done
    # Generated FROM `REQUIRED_HOOT_SUITES` rather than hand-listed beside it.
    # A hand-written copy of the inventory is exactly what went stale the first
    # time a third suite was added, and a self-test that fails because its own
    # fixture is out of date teaches operators to edit the number rather than
    # read the failure.
    local hoot_suite
    while IFS= read -r hoot_suite; do
        [[ -z "$hoot_suite" ]] && continue
        printf 'INFO db mod: CONNECTOR-HOOT-EVIDENCE suite="%s" passed=1 marker=ok\n' \
            "$hoot_suite" >> "$good"
    # `printf '%s\n'` and not `printf '%s'`: without the trailing newline the
    # final field has no line terminator, `read` returns non-zero for it, and
    # the loop body silently skips the LAST suite -- which is precisely the
    # suite a newly added one would be.
    done < <(printf '%s\n' "$REQUIRED_HOOT_SUITES" | tr '|' '\n')
    printf 'INFO db mod: skipped %s : %s\n' "$ALLOWED_SKIP_TEST" "$ALLOWED_SKIP_REASON" >> "$good"

    EVIDENCE_ERRORS=()
    verify_no_unexpected_skips "$good" self-test
    verify_tour_evidence "$good" self-test
    verify_hoot_evidence "$good" self-test
    _expect 0 "a complete log with only the sanctioned skip passes"

    # 1. An unsanctioned skip must fail, however innocuous it looks.
    local skipped="${tmp}/skipped.log"
    cp "$good" "$skipped"
    printf 'INFO db mod: skipped TestSomething.test_a_tour : Chrome executable not found\n' >> "$skipped"
    EVIDENCE_ERRORS=()
    verify_no_unexpected_skips "$skipped" self-test
    _expect 1 "an unsanctioned skip is an evidence failure"

    # 2. The sanctioned identity with a DIFFERENT reason is still a failure --
    #    the allowance is bound to the identity AND the reason, so a skip that
    #    borrows the name cannot ride through.
    local wrong_reason="${tmp}/wrong_reason.log"
    printf 'INFO db mod: skipped %s : websocket-client module is not installed\n' \
        "$ALLOWED_SKIP_TEST" > "$wrong_reason"
    EVIDENCE_ERRORS=()
    verify_no_unexpected_skips "$wrong_reason" self-test
    _expect 1 "the sanctioned test skipping for a DIFFERENT reason still fails"

    # 2b. Two skips on ONE line: a real skip followed by the sanctioned one.
    #     This is the shape that defeated the previous line-based check -- a
    #     greedy match bound the identity to the LAST skip and tested the
    #     reason against the whole line, so the real skip was swallowed and
    #     the run stayed green with a browser test silently not executed.
    local two_on_one="${tmp}/two_on_one.log"
    printf 'INFO db mod: skipped TestConnectorHootSuite.test_u0_dashboard : Chrome executable not found; skipped %s : %s\n' \
        "$ALLOWED_SKIP_TEST" "$ALLOWED_SKIP_REASON" > "$two_on_one"
    EVIDENCE_ERRORS=()
    verify_no_unexpected_skips "$two_on_one" self-test
    _expect 1 "a real skip sharing a line with the sanctioned one still fails"

    # 2c. A subtest skip. `getDescription` renders these as
    #     `Subtest <Class>.<method> (<params>) : <reason>`, which the previous
    #     pattern did not match at all -- every subtest skip was invisible.
    local subtest_skip="${tmp}/subtest_skip.log"
    printf 'INFO db mod: skipped Subtest TestConnectorHootSuite.test_u0_dashboard (i=1) : Chrome executable not found\n' \
        > "$subtest_skip"
    EVIDENCE_ERRORS=()
    verify_no_unexpected_skips "$subtest_skip" self-test
    _expect 1 "a skipped SUBTEST is not invisible to the skip check"

    # 3. A required tour that never ran must fail, even when the marker COUNT
    #    still adds up. This is the subtle case: identity is checked, not just
    #    arithmetic, so a log with the right number of successes but the wrong
    #    set of tests is still caught.
    local missing_tour="${tmp}/missing_tour.log"
    grep -v "Starting TestUiTours.test_navigation_tour " "$good" > "$missing_tour"
    EVIDENCE_ERRORS=()
    verify_tour_evidence "$missing_tour" self-test
    _expect 1 "a required tour that never ran fails even when marker counts add up"

    # 3b. And when the tour is gone entirely -- no start line, no marker --
    #     both checks fire.
    local dropped_tour="${tmp}/dropped_tour.log"
    grep -v "Starting TestUiTours.test_navigation_tour " "$good" \
        | awk '/tour succeeded/ && !seen { seen = 1; next } { print }' \
        > "$dropped_tour"
    EVIDENCE_ERRORS=()
    verify_tour_evidence "$dropped_tour" self-test
    _expect 2 "a tour dropped entirely fails on identity AND on marker count"

    # 4. Tours that "ran" but emitted no success marker -- the exact shape a
    #    skipped HttpCase produces -- must fail.
    local no_markers="${tmp}/no_markers.log"
    grep -v 'tour succeeded' "$good" > "$no_markers"
    EVIDENCE_ERRORS=()
    verify_tour_evidence "$no_markers" self-test
    _expect 1 "required tours with no success markers fail"

    # 5. A missing HOOT suite must fail.
    local no_hoot="${tmp}/no_hoot.log"
    local first_hoot_suite
    first_hoot_suite="$(printf '%s\n' "$REQUIRED_HOOT_SUITES" | cut -d'|' -f1)"
    grep -v "suite=\"${first_hoot_suite}\"" "$good" > "$no_hoot"
    EVIDENCE_ERRORS=()
    verify_hoot_evidence "$no_hoot" self-test
    _expect 1 "a HOOT suite with no verified evidence line fails"

    # 6. An empty log -- the shape of a pass that executed nothing at all.
    : > "${tmp}/empty.log"
    EVIDENCE_ERRORS=()
    verify_tour_evidence "${tmp}/empty.log" self-test
    verify_hoot_evidence "${tmp}/empty.log" self-test
    local hoot_count
    hoot_count="$(printf '%s\n' "$REQUIRED_HOOT_SUITES" | tr '|' '\n' | grep -c .)"
    local want=$(( $(printf '%s' "$REQUIRED_TOUR_TESTS" | wc -w) + 1 + hoot_count ))
    _expect "$want" "an empty log fails for every required tour and every HOOT suite"

    # 6b. Migration evidence. TD-010's rule applied to the false claim this
    #     batch corrected: the checks are only worth anything if they FAIL when
    #     they should, so both directions are asserted here.
    local mig_ok="${tmp}/migration_ok.log" mig_none="${tmp}/migration_none.log"
    printf 'INFO db odoo.modules.migration: module shopify_connector_core: %s 19.0.1.17.0 post-migrate.py\n' \
        "$MIGRATION_MARKER" > "$mig_ok"
    EVIDENCE_ERRORS=()
    verify_migration_evidence "$mig_ok" self-test
    _expect 0 "a log with a connector migration marker passes"

    # A green pass that ran NO script is the exact shape the previous cycle
    # published as "migration 19.0.1.16.0 executed". It must fail.
    printf 'INFO db odoo.tests.result: 0 failed, 0 error(s) of 2189 tests\n' \
        > "$mig_none"
    EVIDENCE_ERRORS=()
    verify_migration_evidence "$mig_none" self-test
    _expect 1 "a green migration pass that executed no script is an evidence failure"

    # An UPSTREAM module's upgrade is not this connector's evidence.
    local mig_foreign="${tmp}/migration_foreign.log"
    printf 'INFO db odoo.modules.migration: module account: %s 19.0.1.0 post-migrate.py\n' \
        "$MIGRATION_MARKER" > "$mig_foreign"
    EVIDENCE_ERRORS=()
    verify_migration_evidence "$mig_foreign" self-test
    _expect 1 "another module's upgrade is not connector migration evidence"

    # And the inverse check: a SAME-VERSION pass that somehow ran a script must
    # fail rather than be quietly relabelled.
    EVIDENCE_ERRORS=()
    verify_no_migration_ran "$mig_ok" self-test
    _expect 1 "a migration script during a same-version update is an evidence failure"
    EVIDENCE_ERRORS=()
    verify_no_migration_ran "$mig_none" self-test
    _expect 0 "a same-version update with no migration script passes"

    # 7. An unresolvable browser must abort the RUN, not warn. Checked in a
    #    subshell so the exit does not end the self-test.
    if ( ODOO_BROWSER_BIN="${tmp}/definitely-not-a-browser" \
         WEBSOCKET_VERSION="1.0.0" preflight_browser >/dev/null 2>&1 ); then
        log "self-test FAIL: preflight accepted a non-existent browser binary"
        failures=$((failures + 1))
    else
        log "self-test PASS: preflight aborts on an unresolvable browser"
    fi

    # 8. A missing websocket-client must abort the run.
    if ( WEBSOCKET_VERSION="missing" preflight_browser >/dev/null 2>&1 ); then
        log "self-test FAIL: preflight accepted a missing websocket-client"
        failures=$((failures + 1))
    else
        log "self-test PASS: preflight aborts when websocket-client is absent"
    fi

    if [[ "$failures" -ne 0 ]]; then
        log "SELF-TEST FAILED (${failures} problems). The runner does NOT fail closed."
        return 1
    fi
    log "self-test: all fail-closed assertions hold"
    return 0
}

if [[ "$RUN_SELF_TEST" -eq 1 ]]; then
    self_test
    exit $?
fi

mkdir -p "$ARTIFACT_DIR"
SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
# A dirty worktree makes `rev-parse HEAD` a LIE about what was executed: the
# tests run against the files on disk, not against the commit. Record it, so a
# reader can never mistake a work-in-progress run for exact-SHA evidence.
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
    WORKTREE_DIRTY=true
    log "WARNING: worktree is DIRTY -- connector_sha ${SHA} does NOT describe"
    log "         what ran. This run is not exact-SHA evidence."
else
    WORKTREE_DIRTY=false
fi
SUMMARY="${ARTIFACT_DIR}/summary.json"

# --- Tested checkout vs intended source head ---------------------------------
# The caller may declare which commit this run is SUPPOSED to be testing.
# CI sets it; a laptop run normally does not.
#
# This exists because of a specific, confirmed failure. On a `pull_request`
# event `actions/checkout` defaults to `refs/pull/N/merge` -- a synthetic
# commit GitHub creates by merging the PR head into the base. It has a real
# SHA, exists in no branch, and was never reviewed. Actions run 30153827606
# published `connector_sha: 60ea6690…` for PR #203 whose head was `156a4a74…`;
# every number in that artifact was real, and every one of them described a
# commit the PR does not contain. Recording the difference is not enough -- a
# run that cannot prove it tested the intended commit must FAIL, not publish.
SOURCE_HEAD_SHA="${SOURCE_HEAD_SHA:-}"
SOURCE_BASE_SHA="${SOURCE_BASE_SHA:-}"
SOURCE_EVENT_NAME="${SOURCE_EVENT_NAME:-local}"
SOURCE_PR_NUMBER="${SOURCE_PR_NUMBER:-}"
SOURCE_RUN_URL="${SOURCE_RUN_URL:-}"
if [[ -n "$SOURCE_HEAD_SHA" && "$SOURCE_HEAD_SHA" != "$SHA" ]]; then
    log "FATAL: checked-out commit ${SHA} is not the intended source head"
    log "       ${SOURCE_HEAD_SHA} (event: ${SOURCE_EVENT_NAME})."
    log "Refusing to run. On a pull_request event this almost always means the"
    log "checkout took GitHub's synthetic merge ref instead of the PR head, and"
    log "every artifact this run produced would describe the wrong commit."
    exit 2
fi
log "testing ${SHA} (event: ${SOURCE_EVENT_NAME}${SOURCE_HEAD_SHA:+, source head verified})"

# --- Odoo source (immutable pin, verified every run) -------------------------
# `19.0` is a moving branch and a restored cache is an arbitrary old commit;
# neither is a pin. Resolve the exact SHA from tools/odoo-pin.txt, fetch it if
# the checkout is not already on it, and then VERIFY. A mismatch aborts rather
# than testing an Odoo nobody chose.
ODOO_PIN="${ODOO_PIN:-$(grep -vE '^\s*(#|$)' "$ODOO_PIN_FILE" | head -1 | tr -d '[:space:]')}"
if [[ ! "$ODOO_PIN" =~ ^[0-9a-f]{40}$ ]]; then
    log "FATAL: tools/odoo-pin.txt does not contain a 40-character commit SHA"
    exit 2
fi

if [[ ! -d "$ODOO_SRC/.git" ]]; then
    log "cloning odoo/odoo into ${ODOO_SRC}"
    git clone --filter=blob:none --no-checkout https://github.com/odoo/odoo.git "$ODOO_SRC"
fi
if [[ "$(git -C "$ODOO_SRC" rev-parse HEAD 2>/dev/null || echo none)" != "$ODOO_PIN" ]]; then
    log "checking out pinned Odoo commit ${ODOO_PIN}"
    git -C "$ODOO_SRC" fetch --filter=blob:none origin "$ODOO_PIN" 2>/dev/null \
        || git -C "$ODOO_SRC" fetch --filter=blob:none --depth 400 origin 19.0 || true
    # `|| true`: a failed checkout must fall through to the verification below,
    # so the operator gets the explanation rather than a bare git error.
    git -C "$ODOO_SRC" checkout --quiet --detach "$ODOO_PIN" 2>/dev/null || true
fi
ODOO_SHA="$(git -C "$ODOO_SRC" rev-parse HEAD)"
if [[ "$ODOO_SHA" != "$ODOO_PIN" ]]; then
    log "FATAL: Odoo checkout is ${ODOO_SHA} but the pin is ${ODOO_PIN}."
    log "Refusing to run: a cached or hand-modified checkout would make every"
    log "artifact below describe an Odoo commit that was not actually tested."
    exit 2
fi
log "odoo pinned and verified @ ${ODOO_SHA}"

# --- Python environment ------------------------------------------------------
# Odoo 19 pins two dependency sets, split on Python 3.12 (see its
# requirements.txt). 3.12 is the Noble target and the one that resolves cleanly,
# so prefer it and say so loudly when falling back.
PYTHON="${PYTHON:-$(command -v python3.12 || command -v python3)}"
VENV="${ODOO_SRC}/../.connector-venv"
if [[ ! -x "$VENV/bin/python" ]]; then
    log "creating venv with $($PYTHON --version 2>&1)"
    "$PYTHON" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip "setuptools<70" wheel
    "$VENV/bin/pip" install --quiet psycopg2-binary
    # psycopg2 is replaced by the binary wheel; python-ldap needs system headers
    # and is only used by auth_ldap, which this suite does not install.
    grep -viE '^(psycopg2|python-ldap)' "$ODOO_SRC/requirements.txt" > "$VENV/requirements.txt"
    "$VENV/bin/pip" install --quiet -r "$VENV/requirements.txt"
fi

# `websocket-client` is NOT in Odoo's requirements.txt, and without it every
# `HttpCase` raises `unittest.SkipTest("websocket-client module is not
# installed")` (odoo/tests/common.py at the pin) -- a SKIP, which still reports
# `0 failed, 0 error(s)`. Installed on EVERY run, not only when the venv is
# created, because a cached venv from before this change would otherwise keep
# silently skipping every browser test. This is idempotent and near-instant
# once satisfied.
"$VENV/bin/pip" install --quiet websocket-client
WEBSOCKET_VERSION="$("$VENV/bin/python" -c 'import websocket; print(websocket.__version__)' 2>/dev/null || echo missing)"

preflight_browser


# --- Odoo config -------------------------------------------------------------
CONF="${ARTIFACT_DIR}/odoo.conf"
cat > "$CONF" <<EOF
[options]
addons_path = ${ODOO_SRC}/addons,${REPO_ROOT}/addons
db_host = ${PGHOST}
db_port = ${PGPORT}
db_user = ${PGUSER:-$(whoami)}
data_dir = ${ARTIFACT_DIR}/odoo-data
without_demo = False
limit_time_real = 0
limit_time_cpu = 0
EOF

# The standard passes always carry the connector selector; --tags appends to it
# rather than replacing it, so an extra selector can never silently narrow the
# run to less than the connector suite.
STANDARD_TAG_ARGS=(--test-tags "$STANDARD_TAGS")
[[ -n "$TEST_TAGS" ]] && STANDARD_TAG_ARGS=(--test-tags "${STANDARD_TAGS},${TEST_TAGS}")

# --- Database clone: the FILESTORE has to come with it -----------------------
#
# `createdb -T` copies the database and nothing else. Odoo keeps attachment
# CONTENT on disk under `<data_dir>/filestore/<dbname>/`, and the copied
# database's `ir_attachment` rows still name checksums that only exist in the
# TEMPLATE's directory. The clone therefore comes up with a complete attachment
# table pointing at files that are not there.
#
# For most tests that is invisible, which is why it survived this long: nothing
# in the standard passes read an attachment's bytes. The moment a browser test
# runs it is fatal -- the web asset bundles ARE attachments, so they fail to
# load, `odoo.isTourReady(...)` never becomes true, and every tour fails with
# "The ready code was always falsy" while the fresh pass is green. The warm
# database was not reproducing a warm upgrade; it was reproducing a broken
# installation.
#
# Real upgrades keep the filestore. So does this now.
clone_db() {  # clone_db <template_db> <new_db>
    local src="$1" dst="$2"
    dropdb --if-exists "$dst" 2>/dev/null || true
    createdb -T "$src" "$dst"
    local store="${ARTIFACT_DIR}/odoo-data/filestore"
    if [[ -d "${store}/${src}" ]]; then
        rm -rf "${store}/${dst}"
        cp -a "${store}/${src}" "${store}/${dst}"
    fi
}

run_odoo() {  # run_odoo <db> <logfile> <args...>
    local db="$1" logfile="$2"; shift 2
    ( cd "$ODOO_SRC" && "$VENV/bin/python" odoo-bin -c "$CONF" -d "$db" \
        --stop-after-init --log-level=test "$@" ) > "$logfile" 2>&1
}

# Odoo exits non-zero on test failure, so the result line is the source of
# truth for *counts* and the exit code for pass/fail. Parse both.
result_line() { grep -E "[0-9]+ failed, [0-9]+ error\(s\) of [0-9]+ tests" "$1" | tail -1 || true; }

FRESH_STATUS="skipped"; FRESH_RESULT=""
WARM_STATUS="skipped";  WARM_RESULT=""
NONSTD_STATUS="skipped"; NONSTD_RESULT=""
OVERALL=0

# --- Pass 1: fresh install ---------------------------------------------------
if [[ $RUN_FRESH -eq 1 ]]; then
    DB="connector_fresh_$$"
    log "fresh install + tests -> ${DB}"
    dropdb --if-exists "$DB" 2>/dev/null || true
    createdb "$DB"
    if run_odoo "$DB" "${ARTIFACT_DIR}/fresh.log" -i "${MODULES},${EXTRA_MODULES}" \
            --test-enable "${STANDARD_TAG_ARGS[@]}"; then
        FRESH_STATUS="pass"
    else
        FRESH_STATUS="fail"; OVERALL=1
    fi
    FRESH_RESULT="$(result_line "${ARTIFACT_DIR}/fresh.log")"
    log "fresh: ${FRESH_STATUS} ${FRESH_RESULT}"
    verify_no_unexpected_skips "${ARTIFACT_DIR}/fresh.log" "fresh"
    verify_tour_evidence "${ARTIFACT_DIR}/fresh.log" "fresh"
    # Keep the fresh database as the warm pass's template.
    TEMPLATE_DB="$DB"
fi

# --- Pass 2: warm update -----------------------------------------------------
# This pass is the whole reason issue #193 existed: a fresh install can be green
# while `-u` fails, because the required column already exists in PostgreSQL but
# the contributing module is not yet in the registry. Never drop this pass.
if [[ $RUN_WARM -eq 1 ]]; then
    if [[ -z "${TEMPLATE_DB:-}" ]]; then
        TEMPLATE_DB="connector_warmbase_$$"
        log "building warm-update base -> ${TEMPLATE_DB}"
        dropdb --if-exists "$TEMPLATE_DB" 2>/dev/null || true
        createdb "$TEMPLATE_DB"
        run_odoo "$TEMPLATE_DB" "${ARTIFACT_DIR}/warm-base.log" \
            -i "${MODULES},${EXTRA_MODULES}"
    fi
    DB="connector_warm_$$"
    log "warm update + tests -> ${DB}"
    clone_db "$TEMPLATE_DB" "$DB"
    if run_odoo "$DB" "${ARTIFACT_DIR}/warm.log" -u "$MODULES" \
            --test-enable "${STANDARD_TAG_ARGS[@]}"; then
        WARM_STATUS="pass"
    else
        WARM_STATUS="fail"; OVERALL=1
    fi
    WARM_RESULT="$(result_line "${ARTIFACT_DIR}/warm.log")"
    log "warm: ${WARM_STATUS} ${WARM_RESULT}"
    verify_no_unexpected_skips "${ARTIFACT_DIR}/warm.log" "warm"
    verify_tour_evidence "${ARTIFACT_DIR}/warm.log" "warm"
    # This pass is a SAME-VERSION update and must never be quoted as migration
    # evidence. Asserted, not assumed.
    verify_no_migration_ran "${ARTIFACT_DIR}/warm.log" "warm"
fi

# --- Pass 2b: genuine version-to-version migrations --------------------------
# Install from an OLDER tree, then upgrade the candidate onto it. This is the
# only shape in which Odoo runs a migration script at all (see the
# MIGRATION_FROM_REFS comment above), and each pass proves a script ran, that the
# standard suite is green afterwards, and that a SECOND update is a no-op.
MIGRATION_RESULTS=()
MIGRATION_OVERALL="skipped"
if [[ $RUN_MIGRATION -eq 1 ]]; then
    MIGRATION_OVERALL="pass"
    for ref in "${MIGRATION_FROM_REFS[@]}"; do
        short="${ref:0:8}"
        label="migration-${short}"
        base_tree="${ARTIFACT_DIR}/base-${short}"
        log "genuine migration pass from ${short}"
        # FETCH IT IF IT IS MISSING, then fail closed only if that fails too.
        #
        # `actions/checkout` clones with `fetch-depth: 1` by default, so on CI
        # the ancestors these passes upgrade FROM are simply not in the object
        # store. Refusing outright was correct-but-useless there: it turned a
        # missing object into a red run on every push, and the obvious "fix"
        # would have been to weaken the guard.
        #
        # GitHub permits fetching a commit by its exact SHA, so the script
        # fetches what it needs instead of depending on how the caller cloned.
        # `--depth=1` keeps it cheap: these passes install from the tree at that
        # commit and never walk its history.
        if ! git -C "$REPO_ROOT" cat-file -e "${ref}^{commit}" 2>/dev/null; then
            log "${short} is not in this clone; fetching it"
            git -C "$REPO_ROOT" fetch --no-tags --depth=1 origin "$ref" \
                >/dev/null 2>&1 \
                || git -C "$REPO_ROOT" fetch --no-tags origin "$ref" \
                >/dev/null 2>&1 || true
        fi
        if ! git -C "$REPO_ROOT" cat-file -e "${ref}^{commit}" 2>/dev/null; then
            log "FATAL: ${ref} is not present in this clone and could not be"
            log "       fetched, so the genuine upgrade from it cannot run."
            log "       This is a REFUSAL, not a skip: a run that cannot"
            log "       perform the migration passes must not report as though"
            log "       it did."
            MIGRATION_OVERALL="fail"; OVERALL=1
            MIGRATION_RESULTS+=("{\"from\":\"${ref}\",\"status\":\"fail\",\"reason\":\"ref not in clone and could not be fetched\"}")
            continue
        fi
        # `git archive` rather than `git worktree`: it materialises the old
        # `addons/` tree with no `.git` metadata and no repository mutation, so a
        # failed run cannot leave a registered worktree behind for the next one
        # to trip over.
        rm -rf "$base_tree"; mkdir -p "$base_tree"
        git -C "$REPO_ROOT" archive "$ref" addons | tar -x -C "$base_tree"
        OLD_CONF="${ARTIFACT_DIR}/odoo-${label}.conf"
        sed "s|^addons_path = .*|addons_path = ${ODOO_SRC}/addons,${base_tree}/addons|" \
            "$CONF" > "$OLD_CONF"
        DB="connector_${label//-/_}_$$"
        dropdb --if-exists "$DB" 2>/dev/null || true
        createdb "$DB"
        # 1. install the OLD tree
        if ! ( cd "$ODOO_SRC" && "$VENV/bin/python" odoo-bin -c "$OLD_CONF" \
                -d "$DB" --stop-after-init --log-level=warn \
                -i "${MODULES},${EXTRA_MODULES}" ) \
                > "${ARTIFACT_DIR}/${label}-install.log" 2>&1; then
            log "FATAL: installing ${short} failed; see ${label}-install.log"
            MIGRATION_OVERALL="fail"; OVERALL=1
            MIGRATION_RESULTS+=("{\"from\":\"${ref}\",\"status\":\"fail\",\"reason\":\"old-tree install failed\"}")
            continue
        fi
        BEFORE_VERSIONS="$(psql -tAc \
            "SELECT name || '=' || latest_version FROM ir_module_module \
             WHERE name LIKE 'shopify_connector%' ORDER BY name" "$DB" \
            | tr '\n' ' ')"
        log "${label}: installed versions ${BEFORE_VERSIONS}"
        # 2. upgrade the CANDIDATE tree onto it, with the standard suite
        if run_odoo "$DB" "${ARTIFACT_DIR}/${label}.log" -u "$MODULES" \
                --test-enable "${STANDARD_TAG_ARGS[@]}"; then
            MIG_STATUS="pass"
        else
            MIG_STATUS="fail"; MIGRATION_OVERALL="fail"; OVERALL=1
        fi
        MIG_RESULT="$(result_line "${ARTIFACT_DIR}/${label}.log")"
        AFTER_VERSIONS="$(psql -tAc \
            "SELECT name || '=' || latest_version FROM ir_module_module \
             WHERE name LIKE 'shopify_connector%' ORDER BY name" "$DB" \
            | tr '\n' ' ')"
        log "${label}: ${MIG_STATUS} ${MIG_RESULT}"
        log "${label}: upgraded versions ${AFTER_VERSIONS}"
        verify_no_unexpected_skips "${ARTIFACT_DIR}/${label}.log" "$label"
        verify_tour_evidence "${ARTIFACT_DIR}/${label}.log" "$label"
        verify_migration_evidence "${ARTIFACT_DIR}/${label}.log" "$label"
        if [[ "$BEFORE_VERSIONS" == "$AFTER_VERSIONS" ]]; then
            evidence_fail "${label}: module versions did not change, so this \
was not a version-to-version upgrade at all"
        fi
        # 3. idempotency: a SECOND update must be green and run nothing again
        if run_odoo "$DB" "${ARTIFACT_DIR}/${label}-again.log" -u "$MODULES" \
                --test-enable "${STANDARD_TAG_ARGS[@]}"; then
            MIG_AGAIN="pass"
        else
            MIG_AGAIN="fail"; MIGRATION_OVERALL="fail"; OVERALL=1
        fi
        MIG_AGAIN_RESULT="$(result_line "${ARTIFACT_DIR}/${label}-again.log")"
        log "${label}: second update ${MIG_AGAIN} ${MIG_AGAIN_RESULT}"
        verify_no_unexpected_skips "${ARTIFACT_DIR}/${label}-again.log" \
            "${label}-again"
        verify_no_migration_ran "${ARTIFACT_DIR}/${label}-again.log" \
            "${label}-again"
        MIGRATION_RESULTS+=("{\"from\":\"${ref}\",\"status\":\"${MIG_STATUS}\",\
\"result\":\"${MIG_RESULT}\",\"second_update\":\"${MIG_AGAIN}\",\
\"second_update_result\":\"${MIG_AGAIN_RESULT}\",\
\"installed_versions_before\":\"${BEFORE_VERSIONS% }\",\
\"installed_versions_after\":\"${AFTER_VERSIONS% }\",\
\"migration_scripts\":$(migration_lines "${ARTIFACT_DIR}/${label}.log" \
    | wc -l | tr -d ' '),\"log\":\"${label}.log\"}")
        rm -rf "$base_tree"
    done
fi

# --- Pass 3: the non-standard tag suite --------------------------------------
# The eight `-standard` classes, run explicitly by tag. This pass gets its own
# database and its own log because several of these tests spawn real OS
# processes and commit; mixing them into the standard log made it impossible to
# tell which pass produced which residue.
if [[ $RUN_NONSTANDARD -eq 1 ]]; then
    if [[ -z "${TEMPLATE_DB:-}" ]]; then
        TEMPLATE_DB="connector_nsbase_$$"
        log "building non-standard base -> ${TEMPLATE_DB}"
        dropdb --if-exists "$TEMPLATE_DB" 2>/dev/null || true
        createdb "$TEMPLATE_DB"
        run_odoo "$TEMPLATE_DB" "${ARTIFACT_DIR}/nonstandard-base.log" \
            -i "${MODULES},${EXTRA_MODULES}"
    fi
    DB="connector_nonstandard_$$"
    log "non-standard tag suite -> ${DB}"
    clone_db "$TEMPLATE_DB" "$DB"
    if run_odoo "$DB" "${ARTIFACT_DIR}/nonstandard.log" -u "$MODULES" \
            --test-enable --test-tags "$NONSTANDARD_TAGS"; then
        NONSTD_STATUS="pass"
    else
        NONSTD_STATUS="fail"; OVERALL=1
    fi
    NONSTD_RESULT="$(result_line "${ARTIFACT_DIR}/nonstandard.log")"
    log "non-standard: ${NONSTD_STATUS} ${NONSTD_RESULT}"
    verify_no_unexpected_skips "${ARTIFACT_DIR}/nonstandard.log" "non-standard"
    verify_hoot_evidence "${ARTIFACT_DIR}/nonstandard.log" "non-standard"
fi

# --- The fail-closed decision ------------------------------------------------
# Odoo's own exit code covers failures and errors. It does NOT cover a test that
# never ran, which is the entire subject of TD-010. A run that cannot prove its
# browser evidence executed is not a green run.
BROWSER_EVIDENCE_STATUS="verified"
# A mode that does not RUN the HOOT pass has not verified HOOT, and must not
# say it has. `verify_hoot_evidence` is called only from the non-standard
# pass, so `--fresh-only`, `--warm-only` and `--skip-nonstandard` previously
# published `"browser_evidence": "verified"` alongside the full
# `required_hoot_suites` list while executing zero HOOT suites and emitting
# zero CONNECTOR-HOOT-EVIDENCE lines. `EVIDENCE_ERRORS` stayed empty, so the
# fail-closed branch below never fired. That is not a failure -- the mode is
# allowed to exclude the pass -- but reporting it as verified is.
if (( ! RUN_NONSTANDARD )); then
    BROWSER_EVIDENCE_STATUS="partial: tours verified, HOOT not executed"
fi
if (( ! RUN_FRESH || ! RUN_WARM )); then
    BROWSER_EVIDENCE_STATUS="${BROWSER_EVIDENCE_STATUS}; single-pass mode"
fi
if (( ${#EVIDENCE_ERRORS[@]} )); then
    BROWSER_EVIDENCE_STATUS="FAILED"
    OVERALL=1
    log "-------------------------------------------------------------------"
    log "BROWSER EVIDENCE VERIFICATION FAILED (${#EVIDENCE_ERRORS[@]} problems)."
    log "The suite's own pass/fail counts may be green; they do not describe"
    log "tests that never executed. This run is NOT browser evidence."
    for problem in "${EVIDENCE_ERRORS[@]}"; do log "  * ${problem}"; done
    log "-------------------------------------------------------------------"
fi

# --- Durable summary ---------------------------------------------------------
# Exact SHAs are recorded so a reader can tell precisely what was executed.
# Evidence class is stamped here rather than left to a human summary, so this
# can never be quoted as Odoo.sh acceptance.
cat > "$SUMMARY" <<EOF
{
  "tested_checkout_sha": "${SHA}",
  "connector_sha": "${SHA}",
  "source_head_sha": "${SOURCE_HEAD_SHA}",
  "source_base_sha": "${SOURCE_BASE_SHA}",
  "source_head_verified": $([[ -n "$SOURCE_HEAD_SHA" ]] && echo true || echo false),
  "github_event": "${SOURCE_EVENT_NAME}",
  "source_pr_number": "${SOURCE_PR_NUMBER}",
  "run_url": "${SOURCE_RUN_URL}",
  "connector_worktree_dirty": ${WORKTREE_DIRTY},
  "odoo_pin": "${ODOO_PIN}",
  "odoo_sha": "${ODOO_SHA}",
  "odoo_pin_verified": true,
  "python": "$("$VENV/bin/python" --version 2>&1)",
  "browser_bin": "${ODOO_BROWSER_BIN}",
  "browser_version": "${BROWSER_VERSION}",
  "websocket_client": "${WEBSOCKET_VERSION}",
  "browser_evidence": "${BROWSER_EVIDENCE_STATUS}",
  "required_tour_tests": $(printf '%s' "$REQUIRED_TOUR_TESTS" | wc -w | tr -d ' '),
  "required_hoot_suites": "${REQUIRED_HOOT_SUITES}",
  "hoot_suites_executed": $( (( RUN_NONSTANDARD )) && echo true || echo false ),
  "allowed_skip": "${ALLOWED_SKIP_TEST}",
  "postgres": "$(psql -tAc 'select version();' postgres 2>/dev/null | head -1)",
  "postgres_server_version": "$(psql -tAc 'show server_version;' postgres 2>/dev/null | head -1 | tr -d '[:space:]')",
  "modules": "${MODULES}",
  "extra_modules": "${EXTRA_MODULES}",
  "standard_tags": "${STANDARD_TAGS}",
  "extra_test_tags": "${TEST_TAGS}",
  "nonstandard_tags": "${NONSTANDARD_TAGS}",
  "passes": {
    "fresh_install_standard": {"status": "${FRESH_STATUS}", "result": "${FRESH_RESULT}", "log": "fresh.log"},
    "warm_update_standard":   {"status": "${WARM_STATUS}",  "result": "${WARM_RESULT}",  "log": "warm.log",
                               "kind": "SAME-VERSION module update",
                               "runs_migration_scripts": false,
                               "note": "Odoo runs an upgrade script only when the installed version is strictly lower than the manifest version, so this pass executes none by construction and is NOT migration evidence. The genuine upgrades are in migration_passes."},
    "nonstandard_tags":       {"status": "${NONSTD_STATUS}", "result": "${NONSTD_RESULT}", "log": "nonstandard.log"}
  },
  "migration_passes": {
    "status": "${MIGRATION_OVERALL}",
    "kind": "VERSION-TO-VERSION upgrade: installed from an older tree, candidate upgraded onto it",
    "evidence_marker": "module <addon>: ${MIGRATION_MARKER} <version> <script>",
    "runs": [$(IFS=,; echo "${MIGRATION_RESULTS[*]:-}")]
  },
  "shopify_operations": "none",
  "evidence_class": "CI supporting evidence, NOT Odoo.sh exact-SHA acceptance (DEC-041 D8)"
}
EOF

log "summary written to ${SUMMARY}"
cat "$SUMMARY"
exit $OVERALL
