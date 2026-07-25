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
#   1. fetches the pinned Odoo 19 source (or reuses a checkout you already have)
#   2. installs the connector modules into a disposable PostgreSQL database
#   3. runs a fresh-install pass and a warm-update pass, because issue #193
#      showed those two are NOT interchangeable
#   4. writes durable logs and a machine-readable summary under $ARTIFACT_DIR
#
# What it deliberately does NOT do
#   * no Shopify store, credential, request, or mutation -- ever. There is no
#     code path here that reads a Shopify secret, and CI must never be given one.
#   * it does NOT replace Odoo.sh. Until equivalence is separately proven, the
#     exact-SHA Odoo.sh run remains the Tier-1 acceptance authority (DEC-041 D8).
#     This script produces supporting evidence, not acceptance.
#
# Usage
#   tools/run_connector_suite.sh [--fresh-only|--warm-only] [--tags <test-tags>]
#
# Environment
#   ODOO_SRC      path to an odoo/odoo@19.0 checkout (cloned if absent)
#   ODOO_REF      Odoo git ref to pin           (default: 19.0)
#   PGHOST/PGPORT PostgreSQL connection         (default: /tmp, 5432)
#   ARTIFACT_DIR  where logs/summary land       (default: ./ci-artifacts)
#   PYTHON        interpreter for the venv      (default: python3.12, else python3)

set -euo pipefail

MODULES="shopify_connector_core,shopify_connector_product,shopify_connector_sale,shopify_connector_inventory,shopify_connector_fulfillment"
# `account` and `stock` are installed explicitly. They are NOT connector
# dependencies, and that is exactly the point: they contribute the required
# columns behind issue #193, so a suite that omits them cannot reproduce the
# warm-update failure family it is supposed to guard.
EXTRA_MODULES="account,stock"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ODOO_SRC="${ODOO_SRC:-${REPO_ROOT}/.odoo-src}"
ODOO_REF="${ODOO_REF:-19.0}"
ARTIFACT_DIR="${ARTIFACT_DIR:-${REPO_ROOT}/ci-artifacts}"
PGHOST="${PGHOST:-/tmp}"
PGPORT="${PGPORT:-5432}"
export PGHOST PGPORT

RUN_FRESH=1
RUN_WARM=1
TEST_TAGS=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fresh-only) RUN_WARM=0; shift ;;
        --warm-only)  RUN_FRESH=0; shift ;;
        --tags)       TEST_TAGS="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

mkdir -p "$ARTIFACT_DIR"
SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
SUMMARY="${ARTIFACT_DIR}/summary.json"

log() { printf '[connector-suite] %s\n' "$*"; }

# --- Odoo source -------------------------------------------------------------
if [[ ! -d "$ODOO_SRC/odoo" ]]; then
    log "cloning odoo/odoo@${ODOO_REF} into ${ODOO_SRC}"
    git clone --depth 1 --branch "$ODOO_REF" https://github.com/odoo/odoo.git "$ODOO_SRC"
fi
ODOO_SHA="$(git -C "$ODOO_SRC" rev-parse HEAD)"
log "odoo source ${ODOO_REF} @ ${ODOO_SHA}"

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

TAG_ARGS=()
[[ -n "$TEST_TAGS" ]] && TAG_ARGS=(--test-tags "$TEST_TAGS")

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
OVERALL=0

# --- Pass 1: fresh install ---------------------------------------------------
if [[ $RUN_FRESH -eq 1 ]]; then
    DB="connector_fresh_$$"
    log "fresh install + tests -> ${DB}"
    dropdb --if-exists "$DB" 2>/dev/null || true
    createdb "$DB"
    if run_odoo "$DB" "${ARTIFACT_DIR}/fresh.log" -i "${MODULES},${EXTRA_MODULES}" \
            --test-enable "${TAG_ARGS[@]}"; then
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
    dropdb --if-exists "$DB" 2>/dev/null || true
    createdb -T "$TEMPLATE_DB" "$DB"
    if run_odoo "$DB" "${ARTIFACT_DIR}/warm.log" -u "$MODULES" \
            --test-enable "${TAG_ARGS[@]}"; then
        WARM_STATUS="pass"
    else
        WARM_STATUS="fail"; OVERALL=1
    fi
    WARM_RESULT="$(result_line "${ARTIFACT_DIR}/warm.log")"
    log "warm: ${WARM_STATUS} ${WARM_RESULT}"
fi

# --- Durable summary ---------------------------------------------------------
# Exact SHAs are recorded so a reader can tell precisely what was executed.
# Evidence class is stamped here rather than left to a human summary, so this
# can never be quoted as Odoo.sh acceptance.
cat > "$SUMMARY" <<EOF
{
  "connector_sha": "${SHA}",
  "odoo_ref": "${ODOO_REF}",
  "odoo_sha": "${ODOO_SHA}",
  "python": "$("$VENV/bin/python" --version 2>&1)",
  "postgres": "$(psql -tAc 'select version();' postgres 2>/dev/null | head -1)",
  "modules": "${MODULES}",
  "extra_modules": "${EXTRA_MODULES}",
  "test_tags": "${TEST_TAGS}",
  "fresh_install": {"status": "${FRESH_STATUS}", "result": "${FRESH_RESULT}"},
  "warm_update":   {"status": "${WARM_STATUS}",  "result": "${WARM_RESULT}"},
  "shopify_operations": "none",
  "evidence_class": "CI supporting evidence, NOT Odoo.sh exact-SHA acceptance (DEC-041 D8)"
}
EOF

log "summary written to ${SUMMARY}"
cat "$SUMMARY"
exit $OVERALL
