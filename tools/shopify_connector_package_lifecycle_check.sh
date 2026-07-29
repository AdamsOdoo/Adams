#!/usr/bin/env bash
#
# Wave 5 single-package lifecycle -- standalone qualification harness.
#
# Section 6/24C of the Wave 5 prompt requires proving the connector's
# package-lifecycle behaviour by ACTUALLY installing/uninstalling modules in
# disposable databases, not by inspecting the manifest graph alone: Odoo's
# own `ir_module.py::_button_immediate_function` refuses any module
# operation "inside tests" (`modules.module.current_test`), so this cannot
# be a `TransactionCase`/`SavepointCase` -- see
# `odoo/addons/base/tests/test_uninstall.py` at the pinned commit for
# Odoo's own precedent (a real, committing cursor outside the test-rollback
# machinery). This script is that standalone harness, mirroring
# `tools/run_connector_suite.sh`'s conventions (ODOO_SRC/PGHOST/PGPORT/venv)
# so it is runnable the same way, on a laptop or in CI.
#
# What it proves, in order, each as its own disposable database:
#   1. Fresh one-action install: `-i shopify_connector` alone installs the
#      complete six-module technical suite and every standard Odoo
#      application it needs (Section 8).
#   2. Warm adoption: the six technical modules installed under the OLD
#      (pre-Wave-5) manifests, then `-u`'d to the current code, correctly
#      adopt `shopify_connector` as a new dependency with no data loss
#      (Section 8, Section 24A).
#   3. Standard-dependency loss: uninstalling `stock` removes the
#      dependent technical modules but leaves `shopify_connector` and
#      `shopify_connector_core` installed, and the package detects the
#      paused state (Section 6 B/C/G, Section 10).
#   4. Restore/resume: reinstalling `stock`, then Recheck -> Restore Suite
#      -> Confirm Resume, with the state staying `dependency_paused` until
#      the final explicit confirmation (Section 13).
#   5. Direct-component-uninstall refusal, including a crafted
#      co-selection with a legitimate standard app (Section 9).
#   6. Complete-package uninstall: uninstalling `shopify_connector` cascades
#      to remove all six technical modules while standard Odoo applications
#      remain installed (Section 14).
#   7. The wider transitive cascade: uninstalling `product` (which brings
#      down `sale`/`stock`/`account`/all five domain technical modules)
#      still leaves the package and core installed (Section 24C).
#
# Zero Shopify operations anywhere in this script.
#
# Usage: tools/shopify_connector_package_lifecycle_check.sh
# Environment: ODOO_SRC, PGHOST, PGPORT, PGUSER, PYTHON (same meaning as
#   tools/run_connector_suite.sh).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ODOO_SRC="${ODOO_SRC:-${REPO_ROOT}/.odoo-src}"
ODOO_PIN_FILE="${REPO_ROOT}/tools/odoo-pin.txt"
PGHOST="${PGHOST:-/tmp}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-$(whoami)}"
export PGHOST PGPORT PGUSER

ARTIFACT_DIR="${ARTIFACT_DIR:-${REPO_ROOT}/ci-artifacts/lifecycle-check}"
mkdir -p "$ARTIFACT_DIR"

PYTHON="${PYTHON:-$(command -v python3.12 || command -v python3)}"
VENV="${ODOO_SRC}/../.connector-venv"
if [[ ! -x "$VENV/bin/python" ]]; then
    echo "FATAL: venv not found at $VENV -- run tools/run_connector_suite.sh first, or create it." >&2
    exit 1
fi

ODOO_PIN="$(grep -v '^#' "$ODOO_PIN_FILE" | grep -v '^\s*$' | tail -1)"
ACTUAL_ODOO_SHA="$(git -C "$ODOO_SRC" rev-parse HEAD 2>/dev/null || echo MISSING)"
if [[ "$ACTUAL_ODOO_SHA" != "$ODOO_PIN" ]]; then
    echo "FATAL: .odoo-src is at ${ACTUAL_ODOO_SHA}, pin requires ${ODOO_PIN}." >&2
    exit 1
fi
echo "odoo pinned and verified @ ${ACTUAL_ODOO_SHA}"

ADDONS_PATH="${ODOO_SRC}/odoo/addons,${ODOO_SRC}/addons,${REPO_ROOT}/addons"
SIX_MODULES="shopify_connector_core,shopify_connector_product,shopify_connector_product_export,shopify_connector_sale,shopify_connector_inventory,shopify_connector_fulfillment"

FAILED=0
STAGE=""

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILED=1; }

run_odoo() {  # run_odoo <db> <logfile> <args...>
    local db="$1" logfile="$2"; shift 2
    ( cd "$ODOO_SRC" && "$VENV/bin/python" odoo-bin -d "$db" \
        --addons-path="$ADDONS_PATH" --db_host="$PGHOST" --db_port="$PGPORT" \
        --without-demo=all --stop-after-init --log-level=warn "$@" \
    ) > "$logfile" 2>&1
}

run_shell() {  # run_shell <db> <script_file> <logfile>
    local db="$1" script="$2" logfile="$3"
    ( cd "$ODOO_SRC" && "$VENV/bin/python" odoo-bin shell -d "$db" \
        --addons-path="$ADDONS_PATH" --db_host="$PGHOST" --db_port="$PGPORT" \
        --log-level=warn --no-http < "$script" \
    ) > "$logfile" 2>&1
}

module_state() {  # module_state <db> <module_name>
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$1" -tAc \
        "SELECT state FROM ir_module_module WHERE name = '$2'"
}

drop_db() { dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" --if-exists "$1" 2>/dev/null || true; }

# ---------------------------------------------------------------------------
STAGE="1. Fresh one-action install"
echo "=== ${STAGE} ==="
DB="lc_fresh_$$"
drop_db "$DB"
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$DB"
if run_odoo "$DB" "${ARTIFACT_DIR}/1_fresh_install.log" -i shopify_connector; then
    ok=1
    for m in shopify_connector $SIX_MODULES; do
        m="${m//,/ }"
        for name in $m; do
            state="$(module_state "$DB" "$name")"
            [[ "$state" == "installed" ]] || { fail "$STAGE: $name state=$state (expected installed)"; ok=0; }
        done
    done
    app_flags="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB" -tAc \
        "SELECT name FROM ir_module_module WHERE name LIKE 'shopify_connector%' AND application = true")"
    [[ "$app_flags" == "shopify_connector" ]] || { fail "$STAGE: application=True set = [${app_flags}], expected only shopify_connector"; ok=0; }
    [[ $ok -eq 1 ]] && pass "$STAGE"
else
    fail "$STAGE: odoo-bin exited non-zero, see ${ARTIFACT_DIR}/1_fresh_install.log"
fi

# ---------------------------------------------------------------------------
STAGE="2. Warm adoption of a pre-Wave-5 database"
echo "=== ${STAGE} ==="
# Fixed historic commit (the PR #204 head this program branched Wave 5 work
# from), NOT `HEAD` -- this script itself lives at and after that commit, so
# `git archive HEAD` would extract the CURRENT (already-migrated) manifests
# once this change is committed, defeating the whole point of this stage.
PRE_WAVE5_SHA="4ac4ce2a5144907673fea1b753764823857916aa"
OLD_ADDONS="${ARTIFACT_DIR}/pre-wave5-addons"
rm -rf "$OLD_ADDONS"
for m in $SIX_MODULES; do
    for name in ${m//,/ }; do
        mkdir -p "${OLD_ADDONS}/${name}"
        git -C "$REPO_ROOT" archive "$PRE_WAVE5_SHA" -- "addons/${name}" \
            | tar -x -C "${OLD_ADDONS}/${name}" --strip-components=2
    done
done
WARM_DB="lc_warm_$$"
drop_db "$WARM_DB"
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$WARM_DB"
OLD_ADDONS_PATH="${ODOO_SRC}/odoo/addons,${ODOO_SRC}/addons,${OLD_ADDONS}"
( cd "$ODOO_SRC" && "$VENV/bin/python" odoo-bin -d "$WARM_DB" \
    --addons-path="$OLD_ADDONS_PATH" --db_host="$PGHOST" --db_port="$PGPORT" \
    --without-demo=all --stop-after-init --log-level=warn \
    -i "$SIX_MODULES" ) > "${ARTIFACT_DIR}/2a_old_install.log" 2>&1
cat > "${ARTIFACT_DIR}/seed_store.py" <<'EOF'
store = env['shopify.connector.store'].sudo().create({
    'name': 'Warm Adoption Check Store',
    'shop_domain': 'warm-adoption-check.myshopify.com',
})
env.cr.commit()
print("SEEDED:%d" % store.id)
EOF
( cd "$ODOO_SRC" && "$VENV/bin/python" odoo-bin shell -d "$WARM_DB" \
    --addons-path="$OLD_ADDONS_PATH" --db_host="$PGHOST" --db_port="$PGPORT" \
    --log-level=warn --no-http < "${ARTIFACT_DIR}/seed_store.py" \
    ) > "${ARTIFACT_DIR}/2b_seed_store.log" 2>&1 || true
if run_odoo "$WARM_DB" "${ARTIFACT_DIR}/2c_warm_upgrade.log" -u "$SIX_MODULES"; then
    ok=1
    [[ "$(module_state "$WARM_DB" shopify_connector)" == "installed" ]] || { fail "$STAGE: shopify_connector was not adopted as a new dependency"; ok=0; }
    for name in $SIX_MODULES; do
        for n in ${name//,/ }; do
            [[ "$(module_state "$WARM_DB" "$n")" == "installed" ]] || { fail "$STAGE: $n not installed after warm upgrade"; ok=0; }
        done
    done
    seeded_name="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$WARM_DB" -tAc \
        "SELECT name FROM shopify_connector_store WHERE shop_domain = 'warm-adoption-check.myshopify.com'")"
    [[ "$seeded_name" == "Warm Adoption Check Store" ]] || { fail "$STAGE: pre-existing store data lost across the warm upgrade"; ok=0; }
    [[ $ok -eq 1 ]] && pass "$STAGE"
else
    fail "$STAGE: warm upgrade exited non-zero, see ${ARTIFACT_DIR}/2c_warm_upgrade.log"
fi
drop_db "$WARM_DB"

# ---------------------------------------------------------------------------
STAGE="3. Standard-dependency loss (stock) + package survival"
echo "=== ${STAGE} ==="
cat > "${ARTIFACT_DIR}/uninstall_stock.py" <<'EOF'
stock = env['ir.module.module'].search([('name', '=', 'stock')])
stock.button_immediate_uninstall()
env.cr.commit()
try:
    env['shopify.connector.package'].assert_healthy()
    print("RESULT:UNEXPECTED_HEALTHY")
except Exception as e:
    print("RESULT:PAUSED:" + str(e).replace("\n", " "))
env.cr.commit()
EOF
if run_shell "$DB" "${ARTIFACT_DIR}/uninstall_stock.py" "${ARTIFACT_DIR}/3_uninstall_stock.log"; then
    ok=1
    [[ "$(module_state "$DB" shopify_connector)" == "installed" ]] || { fail "$STAGE: shopify_connector did not survive"; ok=0; }
    [[ "$(module_state "$DB" shopify_connector_core)" == "installed" ]] || { fail "$STAGE: shopify_connector_core did not survive"; ok=0; }
    [[ "$(module_state "$DB" shopify_connector_inventory)" == "uninstalled" ]] || { fail "$STAGE: shopify_connector_inventory did not cascade"; ok=0; }
    [[ "$(module_state "$DB" shopify_connector_fulfillment)" == "uninstalled" ]] || { fail "$STAGE: shopify_connector_fulfillment did not cascade"; ok=0; }
    grep -q "RESULT:PAUSED:" "${ARTIFACT_DIR}/3_uninstall_stock.log" || { fail "$STAGE: assert_healthy() did not detect the pause"; ok=0; }
    [[ $ok -eq 1 ]] && pass "$STAGE"
else
    fail "$STAGE: odoo shell exited non-zero, see ${ARTIFACT_DIR}/3_uninstall_stock.log"
fi

# ---------------------------------------------------------------------------
STAGE="4. Restore / explicit resume (never automatic)"
echo "=== ${STAGE} ==="
cat > "${ARTIFACT_DIR}/reinstall_stock.py" <<'EOF'
env['ir.module.module'].search([('name', '=', 'stock')]).button_immediate_install()
env.cr.commit()
EOF
run_shell "$DB" "${ARTIFACT_DIR}/reinstall_stock.py" "${ARTIFACT_DIR}/4a_reinstall_stock.log" || true
cat > "${ARTIFACT_DIR}/restore_resume.py" <<'EOF'
pkg = env['shopify.connector.package'].search([], limit=1)
print("STATE_BEFORE:" + pkg.state)
pkg.action_recheck_dependencies()
pkg.action_restore_suite()
print("STATE_AFTER_RESTORE:" + pkg.state)
pkg.action_confirm_resume()
print("STATE_AFTER_CONFIRM:" + pkg.state)
env.cr.commit()
EOF
if run_shell "$DB" "${ARTIFACT_DIR}/restore_resume.py" "${ARTIFACT_DIR}/4b_restore_resume.log"; then
    ok=1
    grep -q "STATE_BEFORE:dependency_paused" "${ARTIFACT_DIR}/4b_restore_resume.log" || { fail "$STAGE: did not start paused"; ok=0; }
    grep -q "STATE_AFTER_RESTORE:dependency_paused" "${ARTIFACT_DIR}/4b_restore_resume.log" || { fail "$STAGE: restore alone resumed automatically"; ok=0; }
    grep -q "STATE_AFTER_CONFIRM:healthy" "${ARTIFACT_DIR}/4b_restore_resume.log" || { fail "$STAGE: explicit confirm did not resume"; ok=0; }
    for name in $SIX_MODULES; do
        for n in ${name//,/ }; do
            [[ "$(module_state "$DB" "$n")" == "installed" ]] || { fail "$STAGE: $n not restored"; ok=0; }
        done
    done
    [[ $ok -eq 1 ]] && pass "$STAGE"
else
    fail "$STAGE: odoo shell exited non-zero, see ${ARTIFACT_DIR}/4b_restore_resume.log"
fi

# ---------------------------------------------------------------------------
STAGE="5. Direct component-uninstall refusal"
echo "=== ${STAGE} ==="
cat > "${ARTIFACT_DIR}/guard_probes.py" <<'EOF'
Module = env['ir.module.module']
core = Module.search([('name', '=', 'shopify_connector_core')])
stock = Module.search([('name', '=', 'stock')])

def probe(label, recordset):
    try:
        recordset.button_immediate_uninstall()
        print("RESULT:%s:ALLOWED_UNEXPECTED" % label)
    except Exception as e:
        print("RESULT:%s:REFUSED:%s" % (label, str(e).replace("\n", " ")))
    env.cr.rollback()

probe("DIRECT", core)
probe("CRAFTED_CO_SELECTION", core + stock)
EOF
if run_shell "$DB" "${ARTIFACT_DIR}/guard_probes.py" "${ARTIFACT_DIR}/5_guard_probes.log"; then
    ok=1
    grep -q "RESULT:DIRECT:REFUSED" "${ARTIFACT_DIR}/5_guard_probes.log" || { fail "$STAGE: direct uninstall was not refused"; ok=0; }
    grep -q "RESULT:CRAFTED_CO_SELECTION:REFUSED" "${ARTIFACT_DIR}/5_guard_probes.log" || { fail "$STAGE: crafted co-selection was not refused"; ok=0; }
    [[ "$(module_state "$DB" shopify_connector_core)" == "installed" ]] || { fail "$STAGE: core state changed despite refusal"; ok=0; }
    [[ $ok -eq 1 ]] && pass "$STAGE"
else
    fail "$STAGE: odoo shell exited non-zero, see ${ARTIFACT_DIR}/5_guard_probes.log"
fi

# ---------------------------------------------------------------------------
STAGE="6. Complete package uninstall"
echo "=== ${STAGE} ==="
cat > "${ARTIFACT_DIR}/full_uninstall.py" <<'EOF'
env['ir.module.module'].search([('name', '=', 'shopify_connector')]).button_immediate_uninstall()
env.cr.commit()
EOF
if run_shell "$DB" "${ARTIFACT_DIR}/full_uninstall.py" "${ARTIFACT_DIR}/6_full_uninstall.log"; then
    ok=1
    [[ "$(module_state "$DB" shopify_connector)" == "uninstalled" ]] || { fail "$STAGE: package itself not removed"; ok=0; }
    for name in $SIX_MODULES; do
        for n in ${name//,/ }; do
            [[ "$(module_state "$DB" "$n")" == "uninstalled" ]] || { fail "$STAGE: $n not removed by the package uninstall"; ok=0; }
        done
    done
    for std in product sale stock account; do
        [[ "$(module_state "$DB" "$std")" == "installed" ]] || { fail "$STAGE: standard app $std was wrongly removed"; ok=0; }
    done
    [[ $ok -eq 1 ]] && pass "$STAGE"
else
    fail "$STAGE: odoo shell exited non-zero, see ${ARTIFACT_DIR}/6_full_uninstall.log"
fi
drop_db "$DB"

# ---------------------------------------------------------------------------
STAGE="7. Wider transitive cascade (product)"
echo "=== ${STAGE} ==="
DB2="lc_wide_$$"
drop_db "$DB2"
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$DB2"
run_odoo "$DB2" "${ARTIFACT_DIR}/7a_fresh_install.log" -i shopify_connector
cat > "${ARTIFACT_DIR}/uninstall_product.py" <<'EOF'
env['ir.module.module'].search([('name', '=', 'product')]).button_immediate_uninstall()
env.cr.commit()
EOF
if run_shell "$DB2" "${ARTIFACT_DIR}/uninstall_product.py" "${ARTIFACT_DIR}/7b_uninstall_product.log"; then
    ok=1
    [[ "$(module_state "$DB2" shopify_connector)" == "installed" ]] || { fail "$STAGE: shopify_connector did not survive"; ok=0; }
    [[ "$(module_state "$DB2" shopify_connector_core)" == "installed" ]] || { fail "$STAGE: shopify_connector_core did not survive"; ok=0; }
    for name in $SIX_MODULES; do
        for n in ${name//,/ }; do
            [[ "$n" == "shopify_connector_core" ]] && continue
            [[ "$(module_state "$DB2" "$n")" == "uninstalled" ]] || { fail "$STAGE: $n should have cascaded with product"; ok=0; }
        done
    done
    [[ $ok -eq 1 ]] && pass "$STAGE"
else
    fail "$STAGE: odoo shell exited non-zero, see ${ARTIFACT_DIR}/7b_uninstall_product.log"
fi
drop_db "$DB2"

echo
if [[ $FAILED -eq 0 ]]; then
    echo "ALL LIFECYCLE STAGES PASSED"
    exit 0
else
    echo "ONE OR MORE LIFECYCLE STAGES FAILED -- see ${ARTIFACT_DIR}"
    exit 1
fi
