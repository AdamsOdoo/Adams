#!/usr/bin/env bash
# Session-local focused test loop. NOT part of the repository contract:
# `tools/run_connector_suite.sh` remains the only sanctioned validation entry
# point, and the definitive exact-head run is always that script. This exists
# purely so a single correction can be re-tested in seconds instead of minutes.
set -euo pipefail
TEMPLATE="${TEMPLATE:-p0core}"
MODULE="$1"; shift
TAGS="$1"; shift || true
DB="focus_$$"
ROOT=/home/user/Adams
STORE="${ROOT}/ci-artifacts/odoo-data/filestore"
dropdb --if-exists "$DB" 2>/dev/null || true
createdb -T "$TEMPLATE" "$DB"
[[ -d "${STORE}/${TEMPLATE}" ]] && { rm -rf "${STORE:?}/${DB}"; cp -a "${STORE}/${TEMPLATE}" "${STORE}/${DB}"; }
# Resolve a browser exactly as tools/run_connector_suite.sh does. Without
# this every HttpCase SKIPS with "Chrome executable not found" and reports a
# green run that proved nothing.
if [[ -z "${ODOO_BROWSER_BIN:-}" ]]; then
    for c in google-chrome chromium chromium-browser google-chrome-stable; do
        if command -v "$c" >/dev/null 2>&1; then ODOO_BROWSER_BIN="$(command -v "$c")"; break; fi
    done
fi
if [[ -z "${ODOO_BROWSER_BIN:-}" ]]; then
    for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome /opt/pw-browsers/chromium; do
        [[ -x "$c" ]] && { ODOO_BROWSER_BIN="$c"; break; }
    done
fi
[[ -n "${ODOO_BROWSER_BIN:-}" ]] || { echo "no browser resolved"; exit 2; }
export ODOO_BROWSER_BIN
LOG="/tmp/focus-${DB}.log"
set +e
( cd "${ROOT}/.odoo-src" && /home/user/.connector-venv/bin/python odoo-bin \
    -c "${ROOT}/ci-artifacts/odoo.conf" -d "$DB" --stop-after-init \
    --log-level=test -u "$MODULE" --test-tags "$TAGS" "$@" ) > "$LOG" 2>&1
RC=$?
set -e
grep -E "[0-9]+ failed, [0-9]+ error\(s\) of [0-9]+ tests" "$LOG" | tail -1 || echo "NO RESULT LINE"
if [[ $RC -ne 0 ]]; then
    echo "--- exit $RC; failures ---"
    grep -E "^(FAIL|ERROR):|odoo.tests.*(FAIL|ERROR)" "$LOG" | head -30
    grep -B2 -A 30 -E "^(FAIL|ERROR): " "$LOG" | head -120
fi
echo "LOG=$LOG DB=$DB"
dropdb --if-exists "$DB" 2>/dev/null || true
rm -rf "${STORE:?}/${DB}" 2>/dev/null || true
exit $RC
