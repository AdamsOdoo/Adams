"""Dependency-free invariants for the P01 Shopify operation catalog.

The inventory is the generated source of truth for document identity.  The
catalog is deliberately checked without importing Odoo or the GraphQL parser,
so this gate can run in the small policy-test lane as well as in a full
environment.
"""

from copy import deepcopy
from collections import Counter
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "docs/v2/evidence/shopify-operation-inventory.json"
CATALOG_PATH = ROOT / "docs/v2/evidence/shopify-operation-contracts.json"

REQUIRED_ROW_FIELDS = frozenset({
    "inventory_key",
    "name",
    "kind",
    "anonymous",
    "declares_user_errors",
    "has_cursor_variable",
    "has_page_info",
    "line",
    "source_line",
    "addon",
    "source",
    "sha256",
    "document_sha256",
    "api_version",
    "variables",
    "domain",
    "required_scopes",
    "scope_status",
    "pagination_bound",
    "completeness_rule",
    "side_effect_class",
    "idempotency_posture",
    "connector_idempotency",
    "shopify_idempotency",
    "readback_plan",
    "readback_operation",
    "uncertainty_policy",
    "live_canary_family",
    "cost_throttle_policy",
    "served_version_policy",
})


class CatalogContractError(AssertionError):
    """Raised when a catalog violates an ownership or safety invariant."""


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _identity(row):
    return (row.get("name"), row.get("kind"))


def _document_identity(row):
    return (
        row.get("name"),
        row.get("kind"),
        row.get("addon"),
        row.get("source"),
        row.get("sha256"),
    )


def validate_catalog(inventory, catalog):
    """Validate catalog/inventory identity and P01 contract invariants."""
    inventory_rows = inventory.get("operations")
    catalog_rows = catalog.get("operations")
    if not isinstance(inventory_rows, list) or not isinstance(catalog_rows, list):
        raise CatalogContractError("inventory and catalog operations must be lists")

    expected_count = inventory.get("operation_count")
    if expected_count != len(inventory_rows):
        raise CatalogContractError("inventory operation count is not self-consistent")
    if catalog.get("operation_count") != expected_count:
        raise CatalogContractError("catalog operation count differs from inventory")
    if len(catalog_rows) != expected_count:
        raise CatalogContractError("catalog row count differs from inventory")
    if catalog.get("anonymous_operation_count") != 0:
        raise CatalogContractError("catalog contains anonymous operations")
    if inventory.get("anonymous_operation_count") != 0:
        raise CatalogContractError("authoritative inventory contains anonymous operations")
    if any(row.get("anonymous") is not False for row in inventory_rows):
        raise CatalogContractError("authoritative inventory contains an anonymous row")

    expected_ids = [_identity(row) for row in inventory_rows]
    actual_ids = [_identity(row) for row in catalog_rows]
    if len(set(expected_ids)) != len(expected_ids):
        raise CatalogContractError("inventory contains duplicate operation names/kinds")
    if len(set(row.get("name") for row in inventory_rows)) != len(inventory_rows):
        raise CatalogContractError("inventory contains duplicate operation names")
    if len(set(actual_ids)) != len(actual_ids):
        raise CatalogContractError("catalog contains duplicate operation names/kinds")
    if len(set(row.get("name") for row in catalog_rows)) != len(catalog_rows):
        raise CatalogContractError("catalog contains duplicate operation names")
    if Counter(actual_ids) != Counter(expected_ids):
        raise CatalogContractError("catalog operation set differs from inventory")

    expected_documents = Counter(_document_identity(row) for row in inventory_rows)
    actual_documents = Counter(_document_identity(row) for row in catalog_rows)
    if actual_documents != expected_documents:
        raise CatalogContractError(
            "catalog document hash/kind/source identity differs from inventory"
        )

    if catalog.get("inventory_source_ref") != inventory.get("source_ref"):
        raise CatalogContractError("catalog source ref differs from inventory")
    if catalog.get("inventory_source_sha") != inventory.get("source_sha"):
        raise CatalogContractError("catalog source sha differs from inventory")
    if catalog.get("api_version") != inventory.get("api_version_literal"):
        raise CatalogContractError("catalog API version differs from inventory")

    inventory_by_id = {_identity(row): row for row in inventory_rows}
    for row in catalog_rows:
        missing = REQUIRED_ROW_FIELDS - set(row)
        if missing:
            raise CatalogContractError(
                "row %s is missing required fields: %s" % (
                    row.get("name"), ", ".join(sorted(missing)),
                )
            )
        if row["anonymous"] is not False:
            raise CatalogContractError("catalog row is anonymous")
        source = inventory_by_id.get(_identity(row))
        if source is None:
            raise CatalogContractError("catalog row has no inventory owner")
        for field in (
            "inventory_key", "name", "kind", "addon", "source", "line",
            "variables", "declares_user_errors", "has_cursor_variable",
            "has_page_info",
        ):
            if row[field] != source[field]:
                raise CatalogContractError(
                    "%s differs for %s" % (field, row.get("name"))
                )
        if row["source_line"] != source["line"]:
            raise CatalogContractError("source_line differs for %s" % row["name"])
        if row["sha256"] != source["sha256"]:
            raise CatalogContractError("document hash differs for %s" % row["name"])
        if row["document_sha256"] != source["sha256"]:
            raise CatalogContractError(
                "document_sha256 differs for %s" % row["name"]
            )
        if row["api_version"] != inventory["api_version_literal"]:
            raise CatalogContractError("row API version differs for %s" % row["name"])

        scopes = row["required_scopes"]
        if not isinstance(scopes, list) or any(
            not isinstance(scope, str) or not scope.strip() for scope in scopes
        ):
            raise CatalogContractError("invalid required_scopes for %s" % row["name"])
        if not scopes and row["scope_status"] != "needs_live_confirmation":
            raise CatalogContractError(
                "unknown scope must be []/needs_live_confirmation for %s"
                % row["name"]
            )
        if scopes and row["scope_status"] != "repo_pinned":
            raise CatalogContractError(
                "non-empty scope list must be repo_pinned for %s" % row["name"]
            )
        if row["scope_status"] not in {
            "repo_pinned", "needs_live_confirmation",
        }:
            raise CatalogContractError("invalid scope_status for %s" % row["name"])

        bound = row["pagination_bound"]
        if not isinstance(bound, dict):
            raise CatalogContractError("pagination_bound must be an object")
        for field in ("mode", "page_size", "max_pages", "max_items", "detail"):
            if field not in bound:
                raise CatalogContractError(
                    "pagination_bound missing %s for %s" % (field, row["name"])
                )
        if not isinstance(bound["mode"], str) or not bound["mode"]:
            raise CatalogContractError("pagination mode is empty")
        if not isinstance(row["completeness_rule"], str) or not row[
            "completeness_rule"
        ].strip():
            raise CatalogContractError("completeness rule is empty")
        for field in (
            "domain", "side_effect_class", "idempotency_posture",
            "connector_idempotency", "shopify_idempotency", "readback_plan",
            "uncertainty_policy", "live_canary_family", "cost_throttle_policy",
            "served_version_policy",
        ):
            if not isinstance(row[field], str) or not row[field].strip():
                raise CatalogContractError(
                    "%s is empty for %s" % (field, row["name"])
                )
        if not isinstance(row["readback_operation"], list):
            raise CatalogContractError("readback_operation must be a list")

        if row["kind"] == "query":
            if row["idempotency_posture"] != "replay_safe":
                raise CatalogContractError(
                    "query is not marked replay_safe: %s" % row["name"]
                )
            if row["readback_plan"] != "not_applicable":
                raise CatalogContractError(
                    "query readback must be not_applicable: %s" % row["name"]
                )
            if row["readback_operation"]:
                raise CatalogContractError(
                    "query has a readback operation: %s" % row["name"]
                )
        elif row["kind"] == "mutation":
            if row["idempotency_posture"] == "replay_safe":
                raise CatalogContractError(
                    "mutation cannot be replay_safe: %s" % row["name"]
                )
            if row["readback_plan"] == "not_applicable":
                raise CatalogContractError(
                    "mutation lacks a readback plan: %s" % row["name"]
                )
            if not row["readback_operation"]:
                raise CatalogContractError(
                    "mutation lacks a readback operation: %s" % row["name"]
                )
            if row["side_effect_class"] == "read_only":
                raise CatalogContractError(
                    "mutation is marked read_only: %s" % row["name"]
                )
        else:
            raise CatalogContractError("unknown operation kind: %s" % row["kind"])


class TestShopifyOperationContractCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = _read(INVENTORY_PATH)
        cls.catalog = _read(CATALOG_PATH)

    def test_catalog_matches_inventory_identity_and_contracts(self):
        validate_catalog(self.inventory, self.catalog)
        self.assertEqual(self.catalog["operation_count"], 48)
        self.assertEqual(len(self.catalog["operations"]), 48)

    def test_rejects_anonymous_operation(self):
        broken = deepcopy(self.catalog)
        broken["operations"][0]["anonymous"] = True
        broken["anonymous_operation_count"] = 1
        with self.assertRaises(CatalogContractError):
            validate_catalog(self.inventory, broken)

    def test_rejects_duplicate_operation_name(self):
        broken = deepcopy(self.catalog)
        broken["operations"][1]["name"] = broken["operations"][0]["name"]
        broken["operations"][1]["inventory_key"] = broken["operations"][0][
            "inventory_key"
        ]
        with self.assertRaises(CatalogContractError):
            validate_catalog(self.inventory, broken)

    def test_rejects_missing_required_field(self):
        broken = deepcopy(self.catalog)
        del broken["operations"][0]["uncertainty_policy"]
        with self.assertRaises(CatalogContractError):
            validate_catalog(self.inventory, broken)

    def test_mutations_have_readback_and_uncertainty_contracts(self):
        validate_catalog(self.inventory, self.catalog)
        mutations = [
            row for row in self.catalog["operations"]
            if row["kind"] == "mutation"
        ]
        self.assertEqual(len(mutations), 14)
        for row in mutations:
            self.assertTrue(row["readback_operation"])
            self.assertNotEqual(row["readback_plan"], "not_applicable")
            self.assertTrue(row["uncertainty_policy"].strip())


if __name__ == "__main__":
    unittest.main()
