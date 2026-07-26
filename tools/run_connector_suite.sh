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
# suite in a real browser. It is `-standard` because it builds the full unit
# asset bundle and boots Chrome, which is exactly this list's cost profile.
#
# WARNING, and it applies to every browser test this runner executes: an
# `HttpCase` test SKIPS -- it does not fail -- when `websocket-client` is
# absent from the venv or when no Chrome/Chromium is resolvable, and a skip
# still reports `0 failed, 0 error(s)`. This script does NOT yet install
# `websocket-client`, does NOT resolve a browser, and does NOT fail on a skip;
# see TD-010. Until it does, a green run here is NOT evidence that any tour or
# HOOT test executed. Set ODOO_BROWSER_BIN and install websocket-client before
# quoting browser evidence from this runner. Keep this list
# in sync with docs/05-qa/pre-wave-5-debt-discovery.md §3; the guard test
# `test_phase_contract.py` fails if a `-standard` class exists that no tag here
# selects, so the two cannot drift apart silently.
NONSTANDARD_TAGS="shopify_connector_product_callsite_lifecycle,sc010b_performance,shopify_connector_customer_matching_benchmark,shopify_connector_customer_matching_concurrency,shopify_connector_customer_callsite_lifecycle,shopify_connector_order_discovery_concurrency,shopify_connector_drain_throughput,shopify_connector_hoot"

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
TEST_TAGS=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fresh-only)       RUN_WARM=0; RUN_NONSTANDARD=0; shift ;;
        --warm-only)        RUN_FRESH=0; RUN_NONSTANDARD=0; shift ;;
        # Deliberately opt-OUT, never opt-in. Forgetting a flag must never be
        # the reason a concurrency proof went unrun.
        --skip-nonstandard) RUN_NONSTANDARD=0; shift ;;
        --tags)             TEST_TAGS="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

log() { printf '[connector-suite] %s\n' "$*"; }

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
  "postgres": "$(psql -tAc 'select version();' postgres 2>/dev/null | head -1)",
  "postgres_server_version": "$(psql -tAc 'show server_version;' postgres 2>/dev/null | head -1 | tr -d '[:space:]')",
  "modules": "${MODULES}",
  "extra_modules": "${EXTRA_MODULES}",
  "standard_tags": "${STANDARD_TAGS}",
  "extra_test_tags": "${TEST_TAGS}",
  "nonstandard_tags": "${NONSTANDARD_TAGS}",
  "passes": {
    "fresh_install_standard": {"status": "${FRESH_STATUS}", "result": "${FRESH_RESULT}", "log": "fresh.log"},
    "warm_update_standard":   {"status": "${WARM_STATUS}",  "result": "${WARM_RESULT}",  "log": "warm.log"},
    "nonstandard_tags":       {"status": "${NONSTD_STATUS}", "result": "${NONSTD_RESULT}", "log": "nonstandard.log"}
  },
  "shopify_operations": "none",
  "evidence_class": "CI supporting evidence, NOT Odoo.sh exact-SHA acceptance (DEC-041 D8)"
}
EOF

log "summary written to ${SUMMARY}"
cat "$SUMMARY"
exit $OVERALL
