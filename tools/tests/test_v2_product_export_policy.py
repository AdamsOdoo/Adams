"""Deterministic pure P13 product-export policy and application tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
from copy import copy, deepcopy
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _namespace(name: str, path: Path) -> None:
    package = sys.modules.get(name)
    if package is None:
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        package.__package__ = name
        sys.modules[name] = package


for _addon in ("shopify_connector_core", "shopify_connector_product_export"):
    _root = ROOT / "addons" / _addon
    _namespace(_addon, _root)
    _namespace(_addon + ".domain", _root / "domain")
    _namespace(_addon + ".integration", _root / "integration")
    _namespace(_addon + ".integration.shopify", _root / "integration" / "shopify")
    _namespace(_addon + ".application", _root / "application")


from shopify_connector_core.integration.shopify.mutation_contracts import (  # noqa: E402
    MutationTransportError,
)
from shopify_connector_product_export.application.product_export_commands import (  # noqa: E402
    DurableMediaProgress,
    FakeMutationLedger,
    ProductExportCommand,
    build_export_payload,
    build_export_sequence,
    build_gateway_requests,
    validate_command,
)
from shopify_connector_product_export.domain.product_export_authority import (  # noqa: E402
    FieldAuthority,
    desired_product_scalars,
    desired_variant_fields,
    field_authority_diff,
    validate_export_fields,
)
from shopify_connector_product_export.domain.product_export_binding import (  # noqa: E402
    ExportPath,
    VariantChange,
    VariantPlan,
    decide_create_or_update,
    plan_variant_operations,
)
from shopify_connector_product_export.domain.product_export_preview import (  # noqa: E402
    PreviewSnapshot,
    reject_stale_preview,
)
from shopify_connector_product_export.domain.product_export_readback import (  # noqa: E402
    BindingNamespaceReadEvidence,
    ReadbackVerdict,
    attest_binding_namespace_read,
    evaluate_remote_readback,
)
from shopify_connector_product_export.domain.product_export_sequence import (  # noqa: E402
    MediaCandidate,
    intent_fingerprint,
    plan_export_sequence,
    scope_key,
)
from shopify_connector_product_export.integration.shopify.product_export_mutation_gateway import (  # noqa: E402
    PRODUCT_EXPORT_MUTATION_REGISTRY,
    ProductExportMutationGateway,
)
from shopify_connector_product_export.integration.shopify.product_media_mutation_gateway import (  # noqa: E402
    MEDIA_FILE_CREATE_READ_QUERY,
    PRODUCT_MEDIA_MUTATION_REGISTRY,
    ProductMediaMutationGateway,
)


STORE = "store-1"
IDENTITY = "store-1.myshopify.com"
PRODUCT = "gid://shopify/Product/3"
VARIANT = "gid://shopify/ProductVariant/4"
VARIANT_2 = "gid://shopify/ProductVariant/5"
FILE = "gid://shopify/File/6"
NOW = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
COMMAND_ID = "00000000-0000-4000-8000-000000000001"
AUTHORITY = {"title": "odoo", "barcode": "odoo", "price_source_of_truth": "odoo_authoritative"}


class Delegate:
    def __init__(self, response=None):
        self.response = response or {"data": {}}
        self.calls = []

    def execute(self, operation, variables):
        self.calls.append((operation, variables))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


class ProgressLoader:
    def __init__(self, progress):
        self.progress = progress
        self.calls = []

    def load_verified(self, **kwargs):
        self.calls.append(kwargs)
        return self.progress


def _binding_evidence(generation=1, identity=IDENTITY):
    return attest_binding_namespace_read(
        {
            "metafieldDefinitions": {
                "nodes": [{
                    "id": "gid://shopify/MetafieldDefinition/7",
                    "key": "odoo_template_custom_id_v2",
                    "ownerType": "PRODUCT",
                    "type": {"name": "id"},
                }],
                "pageInfo": {"hasNextPage": False},
            },
            "shop": {"myshopifyDomain": identity},
        },
        expected_store_identity=identity,
        connection_generation=generation,
    )


class TestProductExportAuthority(unittest.TestCase):
    def test_v1_authority_omits_optional_values_and_only_managed_status(self):
        values = desired_product_scalars(
            {"name": "Hat", "description": "", "vendor": "Acme", "tags": "red, blue", "status": "DRAFT"},
            authority={"status": "odoo", "vendor": "shopify"},
        )
        self.assertEqual(values, {"title": "Hat", "vendor": "Acme", "tags": ["red", "blue"], "status": "DRAFT"})
        values = desired_product_scalars({"name": "Hat", "description": ""}, authority={"description": "odoo"})
        self.assertEqual(values["descriptionHtml"], "")

    def test_protected_and_unknown_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "merchant-owned"):
            validate_export_fields({"metafields": []})
        with self.assertRaisesRegex(ValueError, "protected"):
            validate_export_fields({"collectionsToJoin": []})
        with self.assertRaisesRegex(ValueError, "merchant-owned"):
            desired_variant_fields({"sku": "A", "tracked": True})

    def test_variant_price_authority_and_compare_at_zero_preserve_v1_omission(self):
        self.assertEqual(
            desired_variant_fields({"sku": "A", "price": "4", "compareAtPrice": "0.00"}, authority={"price_source_of_truth": "odoo_authoritative"}),
            {"inventoryItem": {"sku": "A"}, "price": "4.00"},
        )
        self.assertNotIn("price", desired_variant_fields({"sku": "A", "price": "4"}, authority={"price_source_of_truth": "shopify"}))

    def test_authority_diff_discloses_shopify_field_without_writing_it(self):
        diff = field_authority_diff(
            {"title": "New", "vendor": "Acme"},
            {"title": "Old", "vendor": "Merchant"},
            authority={"title": FieldAuthority.ODOO, "vendor": FieldAuthority.SHOPIFY},
        )
        self.assertEqual({row.field for row in diff if row.changed}, {"title"})
        self.assertEqual({row.field for row in diff if row.authority is FieldAuthority.SHOPIFY}, {"vendor"})


class TestProductExportIdentityAndSequence(unittest.TestCase):
    def test_scope_and_fingerprint_are_server_derived_and_stable(self):
        self.assertEqual(scope_key(STORE, PRODUCT), f"product:{STORE}:{PRODUCT}")
        first = intent_fingerprint(
            store_id=STORE,
            connection_generation=4,
            operation="product_export",
            target={"product_gid": PRODUCT},
            business_values={"title": "Hat", "display_label": "ignored", "correlation_id": "one"},
            preconditions={"version": 2},
            scope=scope_key(STORE, PRODUCT),
        )
        second = intent_fingerprint(
            store_id=STORE,
            connection_generation=4,
            operation="product_export",
            target={"product_gid": PRODUCT},
            business_values={"title": "Hat", "display_label": "changed", "correlation_id": "two"},
            preconditions={"version": 2},
            scope=scope_key(STORE, PRODUCT),
        )
        self.assertEqual(first, second)

    def test_binding_requires_update_and_blocks_duplicate_or_missing_identity(self):
        self.assertEqual(decide_create_or_update(store_id=STORE, template_id=9).path, ExportPath.CREATE)
        self.assertEqual(
            decide_create_or_update(store_id=STORE, template_id=9, binding={"product_gid": PRODUCT}, remote_product={"id": PRODUCT}).path,
            ExportPath.UPDATE,
        )
        missing = decide_create_or_update(store_id=STORE, template_id=9, binding={"product_gid": PRODUCT})
        self.assertEqual((missing.path, missing.reason_code), (ExportPath.BLOCKED, "bound_product_missing_remotely"))
        duplicate = decide_create_or_update(store_id=STORE, template_id=9, remote_by_custom_id=[{"id": PRODUCT}])
        self.assertEqual(duplicate.reason_code, "custom_id_duplicate_risk")

    def test_variant_identity_is_strict_and_unowned_remote_rows_are_disclosed(self):
        plan = plan_variant_operations(
            [{"id": VARIANT, "sku": "A", "price": "2"}, {"sku": "B"}],
            remote_variants=[{"id": VARIANT, "sku": "OLD"}, {"id": VARIANT_2, "sku": "MERCHANT"}],
            authority={"price_source_of_truth": "odoo_authoritative"},
        )
        self.assertFalse(plan.blocked)
        self.assertEqual(len(plan.updates), 1)
        self.assertEqual([row.sku for row in plan.creates], ["B"])
        self.assertEqual(plan.unowned_remote_variant_gids, (VARIANT_2,))
        blocked = plan_variant_operations([{"id": "gid://shopify/ProductVariant/99", "sku": "X"}], remote_variants=[])
        self.assertEqual(blocked.blocked_reason, "bound_variant_missing_remotely")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            plan_variant_operations([{"sku": "MERCHANT"}], remote_variants=[{"id": VARIANT_2, "sku": "MERCHANT"}])
        duplicate_remote = plan_variant_operations(
            [{"id": VARIANT, "sku": "A"}],
            remote_variants=[{"id": VARIANT, "sku": "A"}, {"id": VARIANT, "sku": "shadow"}],
        )
        self.assertEqual(duplicate_remote.blocked_reason, "duplicate_remote_variant_identity")
        self.assertEqual(duplicate_remote.updates, ())

    def test_sequence_has_one_ordered_send_per_step_and_defers_create_media(self):
        create = plan_export_sequence(
            path="create", store_id=STORE, template_id=9, connection_generation=1,
            product_scalars={"title": "Hat"}, binding_namespace_ready=False,
            authority={"title": "odoo"}, source_write_date=NOW,
        )
        self.assertEqual(
            [step.step for step in create.steps],
            [
                "product_export_binding_namespace_decision",
                "product_export_binding_namespace",
                "product_export_binding_namespace_readback",
            ],
        )
        self.assertEqual(create.blocked_reason, "binding_namespace_readback_required")
        update = plan_export_sequence(
            path="update", store_id=STORE, template_id=9, connection_generation=1, product_gid=PRODUCT,
            product_scalars={"title": "Hat"},
            variant_plan=VariantPlan((), ()),
            media=[MediaCandidate("hat.png", "sha-1")], media_source_of_truth="odoo",
            authority={"title": "odoo"}, source_write_date=NOW, remote_updated_at=NOW,
        )
        self.assertEqual(
            [step.step for step in update.steps],
            ["product_export_update", "product_export_media_stage", "product_export_media_upload", "product_export_media_file_create", "product_export_media_poll", "product_export_media_associate"],
        )
        self.assertEqual(update.remote_send_count, 4)
        create_media = plan_export_sequence(
            path="create", store_id=STORE, template_id=9, connection_generation=1,
            expected_store_identity=IDENTITY,
            media=[MediaCandidate("hat.png", "sha-1")], media_source_of_truth="odoo",
            binding_namespace_evidence=_binding_evidence(), source_write_date=NOW,
        )
        self.assertEqual([step.step for step in create_media.steps], ["product_export_binding_namespace_decision", "product_export_create"])


class TestProductExportPreviewReadback(unittest.TestCase):
    def _snapshot(self, **changes):
        values = {"store_id": STORE, "connection_generation": 3, "fingerprint": "a" * 64, "created_at": NOW, "state": "confirmed"}
        values.update(changes)
        return PreviewSnapshot.create(**values)

    def test_stale_preview_rejects_ttl_generation_fingerprint_source_and_remote_changes(self):
        snapshot = self._snapshot(source_write_date=NOW, remote_updated_at=NOW)
        self.assertIs(reject_stale_preview(snapshot, now=NOW + timedelta(hours=1), expected_fingerprint=snapshot.fingerprint, current_generation=3, current_source_write_date=NOW, current_remote_updated_at=NOW), snapshot)
        for kwargs in (
            {"now": NOW + timedelta(hours=25)},
            {"now": NOW, "current_generation": 4},
            {"now": NOW, "expected_fingerprint": "b" * 64},
            {"now": NOW, "current_source_write_date": NOW + timedelta(seconds=1)},
            {"now": NOW, "current_remote_updated_at": NOW + timedelta(seconds=1)},
        ):
            with self.assertRaisesRegex(ValueError, "reviewed"):
                reject_stale_preview(snapshot, **kwargs)

    def test_readback_matrix_distinguishes_applied_not_applied_and_inconclusive(self):
        applied = evaluate_remote_readback("product_create", {"template_id": "9"}, [{"id": PRODUCT, "custom_id": "9"}], complete=True)
        self.assertEqual(applied.verdict, ReadbackVerdict.APPLIED)
        duplicate = evaluate_remote_readback("product_create", {"template_id": "9"}, [{"id": PRODUCT, "custom_id": "9"}, {"id": VARIANT, "custom_id": "9"}], complete=True)
        self.assertEqual(duplicate.verdict, ReadbackVerdict.NOT_APPLIED)
        uncertain = evaluate_remote_readback("product_update", {"product_gid": PRODUCT, "title": "Hat"}, None, read_error="timeout", send_state="after_send")
        self.assertEqual(uncertain.verdict, ReadbackVerdict.INCONCLUSIVE)
        before = evaluate_remote_readback("product_update", {"product_gid": PRODUCT, "title": "Hat"}, None, read_error="timeout", send_state="before_send")
        self.assertEqual(before.reason_code, "send_not_attempted")
        partial = evaluate_remote_readback("product_update", {"product_gid": PRODUCT, "title": "Hat"}, {"product": {"id": PRODUCT, "title": "Hat"}, "userErrors": [{"field": ["title"], "message": "partial"}]})
        self.assertEqual(partial.reason_code, "partial_user_errors")

    def test_variant_and_media_readback_are_exact(self):
        variant = evaluate_remote_readback(
            "variants_update", {"product_gid": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]},
            {"product": {"id": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]}}, complete=True,
        )
        self.assertEqual(variant.verdict, ReadbackVerdict.APPLIED)
        created = evaluate_remote_readback(
            "variants_create", {"product_gid": PRODUCT, "variants": [{"sku": "A"}, {"sku": "B"}]},
            {"product": {"id": PRODUCT, "variants": [{"id": VARIANT, "sku": "A"}, {"id": VARIANT_2, "sku": "B"}]}}, complete=True,
        )
        self.assertEqual(created.verdict, ReadbackVerdict.APPLIED)
        media = evaluate_remote_readback("media_file_create", {"file_gid": FILE}, {"node": {"id": FILE}})
        self.assertEqual(media.verdict, ReadbackVerdict.APPLIED)
        associated = evaluate_remote_readback(
            "media_associate", {"product_gid": PRODUCT, "file_gid": FILE},
            {"product": {"id": PRODUCT, "media": {"nodes": [{"id": FILE}], "pageInfo": {"hasNextPage": False}}}},
        )
        self.assertEqual(associated.verdict, ReadbackVerdict.APPLIED)
        staged = evaluate_remote_readback("media_stage", {}, {"shop_identity": IDENTITY})
        self.assertEqual(staged.verdict, ReadbackVerdict.INCONCLUSIVE)


class TestProductExportApplicationGatewaySeam(unittest.TestCase):
    def test_payload_command_and_p08_gateway_requests_are_pure(self):
        payload = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="update", product_gid=PRODUCT, scalar_fields={"title": "Hat"},
            variant_updates=({"id": VARIANT, "barcode": "B"},),
            authority=AUTHORITY, source_write_date=NOW, remote_updated_at=NOW,
        )
        command = ProductExportCommand("apply", payload, COMMAND_ID, "admin", 1, payload.fingerprint)
        preview = PreviewSnapshot.create(
            store_id=STORE, connection_generation=1, fingerprint=payload.fingerprint,
            created_at=NOW, state="confirmed", source_write_date=NOW,
            remote_updated_at=NOW, product_gid=PRODUCT, scope=payload.scope,
        )
        self.assertIs(validate_command(command, current_generation=1, current_fingerprint=payload.fingerprint, preview=preview, now=NOW, current_source_write_date=NOW, current_remote_updated_at=NOW, current_store_id=STORE), command)
        sequence = build_export_sequence(payload)
        product_delegate = Delegate({"data": {}})
        product_gateway = ProductExportMutationGateway(product_delegate, PRODUCT_EXPORT_MUTATION_REGISTRY)
        requests = build_gateway_requests(payload, sequence, product_gateway)
        self.assertEqual(len(requests), 2)
        self.assertEqual([item.request.operation_key for item in requests], ["product_export.update", "product_export.variants_update"])
        self.assertEqual(product_delegate.calls, [])

    def test_payload_rejects_non_boolean_namespace_readiness(self):
        with self.assertRaisesRegex(ValueError, "strict boolean"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="create", binding_namespace_ready="false",
            )

    def test_media_gateway_materialization_and_one_send_ledger_do_not_shadow_mutate(self):
        payload = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="update", product_gid=PRODUCT, media=(MediaCandidate("hat.png", "sha-1"),), media_source_of_truth="odoo",
            source_write_date=NOW, remote_updated_at=NOW,
        )
        sequence = build_export_sequence(payload)
        product_gateway = ProductExportMutationGateway(Delegate(), PRODUCT_EXPORT_MUTATION_REGISTRY)
        media_delegate = Delegate()
        media_gateway = ProductMediaMutationGateway(media_delegate, PRODUCT_MEDIA_MUTATION_REGISTRY)
        materialized = {"hat.png": {"staged_resource_url": "https://upload.example/resource", "file_gid": FILE}}
        requests = build_gateway_requests(payload, sequence, product_gateway, media_gateway, materialized_media=materialized)
        remote = [row for row in requests if row.remote_send]
        self.assertEqual([row.step.operation for row in remote], ["product_export.media_stage", "product_export.media_file_create"])
        self.assertEqual(requests[-1].reason_code, "durable_media_progress_required")
        association = sequence.steps[-1]
        prerequisite_keys = tuple(step.idempotency_key for step in sequence.steps[-5:-1])
        file_readback = evaluate_remote_readback(
            "media_file_create", {"file_gid": FILE},
            {"node": {"id": FILE}, "shop": {"myshopifyDomain": IDENTITY}},
            expected_store_identity=IDENTITY,
        )
        progress = DurableMediaProgress(sequence.fingerprint, association.scope, prerequisite_keys, FILE, file_readback)
        loader = ProgressLoader(progress)
        verified_requests = build_gateway_requests(
            payload, sequence, product_gateway, media_gateway,
            materialized_media=materialized, durable_media_progress=loader,
        )
        verified_remote = [row for row in verified_requests if row.remote_send]
        self.assertEqual(
            [row.step.operation for row in verified_remote],
            ["product_export.media_stage", "product_export.media_file_create", "product_export.media_associate"],
        )
        self.assertEqual(verified_remote[-1].request.variables["files"][0]["id"], FILE)
        incomplete = DurableMediaProgress(
            sequence.fingerprint, association.scope, prerequisite_keys[:-1], FILE, file_readback,
        )
        incomplete_requests = build_gateway_requests(
            payload, sequence, product_gateway, media_gateway,
            materialized_media=materialized, durable_media_progress=ProgressLoader(incomplete),
        )
        self.assertEqual(incomplete_requests[-1].reason_code, "media_prerequisites_not_durable")
        ledger = FakeMutationLedger()
        calls = []
        for row in remote[:1]:
            ledger.send_once(row.step.send_once_key, lambda row=row: calls.append(row.step.operation) or "sent")
            ledger.send_once(row.step.send_once_key, lambda: calls.append("shadow") or "sent-again")
        self.assertEqual(calls, ["product_export.media_stage"])
        self.assertEqual(len(ledger.calls), 1)

    def test_p08_gateway_preserves_before_after_send_ambiguity(self):
        delegate = Delegate(MutationTransportError(after_send=False))
        gateway = ProductExportMutationGateway(delegate, PRODUCT_EXPORT_MUTATION_REGISTRY)
        request = gateway.build_update(PRODUCT, {"title": "Hat"}, idempotency_key="k-before")
        result = gateway.execute_once(request)
        self.assertEqual(result.outcome, "failed_clean")
        self.assertEqual(len(delegate.calls), 1)
        delegate = Delegate(MutationTransportError(after_send=True))
        gateway = ProductExportMutationGateway(delegate, PRODUCT_EXPORT_MUTATION_REGISTRY)
        request = gateway.build_update(PRODUCT, {"title": "Hat"}, idempotency_key="k-after")
        result = gateway.execute_once(request)
        self.assertEqual(result.outcome, "uncertain")

    def test_readiness_is_fail_closed_and_authority_is_explicit(self):
        payload = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="create", scalar_fields={"title": "Hat"}, authority={"title": "odoo"},
            source_write_date=NOW,
        )
        self.assertFalse(payload.binding_namespace_ready)
        bootstrap = build_export_sequence(payload)
        self.assertEqual(
            [step.operation for step in bootstrap.steps],
            [
                "product_export.binding_namespace.decision",
                "product_export.binding_namespace",
                "product_export.binding_definition.read",
            ],
        )
        self.assertNotIn("product_export.create", [step.operation for step in bootstrap.steps])
        with self.assertRaisesRegex(ValueError, "server-attested"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="create", binding_namespace_ready=True, source_write_date=NOW,
            )
        with self.assertRaisesRegex(ValueError, "typed server-attested"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="create", binding_namespace_evidence=_binding_evidence().as_dict(), source_write_date=NOW,
            )
        with self.assertRaisesRegex(ValueError, "applied exact definition readback"):
            attest_binding_namespace_read(
                {
                    "metafieldDefinitions": {"nodes": [{
                        "id": "gid://shopify/MetafieldDefinition/7",
                        "key": "odoo_template_custom_id_v2",
                        "ownerType": "PRODUCT",
                        "type": {"name": "id"},
                    }]},
                    "shop": {"myshopifyDomain": IDENTITY},
                },
                expected_store_identity=IDENTITY,
                connection_generation=1,
            )
        with self.assertRaisesRegex(ValueError, "another connection generation"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="create", binding_namespace_evidence=_binding_evidence(2), source_write_date=NOW,
            )
        with self.assertRaisesRegex(ValueError, "another Shopify store"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="create",
                binding_namespace_evidence=_binding_evidence(identity="other.myshopify.com"),
                source_write_date=NOW,
            )
        with self.assertRaisesRegex(ValueError, "another Shopify store"):
            plan_export_sequence(
                path="create", store_id=STORE, template_id=9, connection_generation=1,
                expected_store_identity=IDENTITY,
                binding_namespace_evidence=_binding_evidence(identity="other.myshopify.com"),
                source_write_date=NOW,
            )
        ready = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="create", binding_namespace_evidence=_binding_evidence(), source_write_date=NOW,
        )
        self.assertTrue(ready.binding_namespace_ready)
        self.assertEqual(
            [step.operation for step in build_export_sequence(ready).steps],
            ["product_export.binding_namespace.decision", "product_export.create"],
        )
        with self.assertRaisesRegex(ValueError, "explicitly Odoo-authoritative"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="update", product_gid=PRODUCT, scalar_fields={"title": "Hat"},
                source_write_date=NOW, remote_updated_at=NOW,
            )
        self.assertEqual(field_authority_diff({"title": "Hat"})[0].authority, FieldAuthority.SHOPIFY)

    def test_binding_evidence_is_constructor_closed_and_copy_safe(self):
        with self.assertRaisesRegex(ValueError, "only be produced"):
            BindingNamespaceReadEvidence()
        with self.assertRaisesRegex(ValueError, "sealed and cannot be subclassed"):
            class ForgedBindingEvidence(BindingNamespaceReadEvidence):
                def __new__(cls):
                    return object.__new__(cls)

                def _validate(self):
                    return None

        evidence = _binding_evidence()
        with self.assertRaises(TypeError):
            replace(evidence, store_identity="other.myshopify.com")
        with self.assertRaisesRegex(ValueError, "cannot be copied"):
            copy(evidence)
        with self.assertRaisesRegex(ValueError, "cannot be copied"):
            deepcopy(evidence)
        tampered = _binding_evidence()
        object.__setattr__(tampered, "_store_identity", "other.myshopify.com")
        with self.assertRaisesRegex(ValueError, "mutated after attestation"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="create", binding_namespace_evidence=tampered, source_write_date=NOW,
            )

    def test_preview_requires_exact_scope_freshness_and_current_fingerprint(self):
        payload = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="update", product_gid=PRODUCT, scalar_fields={"title": "Hat"},
            authority={"title": "odoo"}, source_write_date=NOW, remote_updated_at=NOW,
        )
        command = ProductExportCommand("apply", payload, COMMAND_ID, "admin")
        with self.assertRaisesRegex(ValueError, "confirmed preview"):
            validate_command(command, current_generation=1, current_fingerprint=payload.fingerprint)
        preview = PreviewSnapshot.create(
            store_id=STORE, connection_generation=1, fingerprint=payload.fingerprint,
            created_at=NOW, state="confirmed", source_write_date=NOW,
            remote_updated_at=NOW, product_gid=PRODUCT, scope=payload.scope,
        )
        self.assertIs(
            validate_command(
                command, current_generation=1, current_fingerprint=payload.fingerprint,
                preview=preview, now=NOW, current_source_write_date=NOW,
                current_remote_updated_at=NOW, current_store_id=STORE,
            ),
            command,
        )
        with self.assertRaisesRegex(ValueError, "no longer current"):
            validate_command(
                command, current_generation=1, current_fingerprint=payload.fingerprint,
                preview=preview, now=NOW, current_source_write_date=NOW + timedelta(seconds=1),
                current_remote_updated_at=NOW, current_store_id=STORE,
            )
        with self.assertRaisesRegex(ValueError, "reviewed_fingerprint"):
            plan_export_sequence(
                path="update", store_id=STORE, template_id=9, connection_generation=1,
                product_gid="gid://shopify/Product/99", product_scalars={"title": "Other"},
                authority={"title": "odoo"}, source_write_date=NOW, remote_updated_at=NOW,
                reviewed_fingerprint=payload.fingerprint,
            )

    def test_blocked_variant_evidence_survives_and_existing_creates_require_sku(self):
        blocked_plan = VariantPlan(
            (VariantChange(VARIANT, {"barcode": "B"}),), (), (), "bound_variant_missing_remotely"
        )
        payload = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="update", product_gid=PRODUCT, scalar_fields={"title": "Hat"},
            variant_plan=blocked_plan, authority=AUTHORITY,
            source_write_date=NOW, remote_updated_at=NOW,
        )
        sequence = build_export_sequence(payload)
        self.assertEqual(sequence.path, ExportPath.BLOCKED)
        self.assertEqual(sequence.blocked_reason, "bound_variant_missing_remotely")
        with self.assertRaisesRegex(ValueError, "requires a SKU"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="update", product_gid=PRODUCT, variant_creates=({"barcode": "B"},),
                authority={"barcode": "odoo"}, source_write_date=NOW, remote_updated_at=NOW,
            )

    def test_missing_media_materialization_is_typed_defer_not_silent_drop(self):
        payload = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="update", product_gid=PRODUCT, media=(MediaCandidate("hat.png", "sha-1"),),
            media_source_of_truth="odoo", source_write_date=NOW, remote_updated_at=NOW,
        )
        sequence = build_export_sequence(payload)
        product_gateway = ProductExportMutationGateway(Delegate(), PRODUCT_EXPORT_MUTATION_REGISTRY)
        media_gateway = ProductMediaMutationGateway(Delegate(), PRODUCT_MEDIA_MUTATION_REGISTRY)
        requests = build_gateway_requests(payload, sequence, product_gateway, media_gateway, materialized_media={})
        self.assertEqual([item.step.step for item in requests], [step.step for step in sequence.steps])
        deferred = {item.step.step: item.reason_code for item in requests if item.deferred}
        self.assertEqual(deferred["product_export_media_upload"], "media_upload_runtime_required")
        self.assertEqual(deferred["product_export_media_file_create"], "media_stage_materialization_required")
        self.assertEqual(deferred["product_export_media_poll"], "media_file_create_readback_required")
        self.assertEqual(deferred["product_export_media_associate"], "durable_media_progress_required")

    def test_readback_requires_exact_identity_and_pagination_evidence(self):
        missing_media = evaluate_remote_readback(
            "media_associate", {"product_gid": PRODUCT, "file_gid": FILE},
            {"product": {"id": PRODUCT, "media": {"nodes": []}}},
        )
        self.assertEqual(missing_media.verdict, ReadbackVerdict.INCONCLUSIVE)
        wrong_binding = evaluate_remote_readback(
            "binding_namespace", {"definition_key": "odoo_template_custom_id_v2", "type": "id", "owner": "PRODUCT"},
            {"metafieldDefinitions": {"nodes": [{"id": "gid://shopify/MetafieldDefinition/1", "key": "wrong", "ownerType": "PRODUCT", "type": {"name": "id"}}], "pageInfo": {"hasNextPage": False}}},
        )
        self.assertEqual(wrong_binding.verdict, ReadbackVerdict.NOT_APPLIED)
        missing_binding = evaluate_remote_readback(
            "product_create", {"template_id": "9"}, [{"id": PRODUCT}],
        )
        self.assertEqual(missing_binding.verdict, ReadbackVerdict.INCONCLUSIVE)

    def test_readback_defaults_incomplete_and_rejects_has_next_page(self):
        unproved = evaluate_remote_readback(
            "variants_update", {"product_gid": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]},
            {"product": {"id": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]}},
        )
        self.assertEqual((unproved.verdict, unproved.reason_code), (ReadbackVerdict.INCONCLUSIVE, "readback_incomplete"))
        paged = evaluate_remote_readback(
            "variants_update", {"product_gid": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]},
            {"product": {"id": PRODUCT, "variants": {"nodes": [{"id": VARIANT, "price": "2.00"}], "pageInfo": {"hasNextPage": True}}}},
            complete=True,
        )
        self.assertEqual((paged.verdict, paged.reason_code), (ReadbackVerdict.INCONCLUSIVE, "readback_has_next_page"))
        complete_page = evaluate_remote_readback(
            "variants_update", {"product_gid": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]},
            {"product": {"id": PRODUCT, "variants": {"nodes": [{"id": VARIANT, "price": "2.00"}], "pageInfo": {"hasNextPage": False}}}},
        )
        self.assertEqual(complete_page.verdict, ReadbackVerdict.APPLIED)
        unrelated_variant_page = evaluate_remote_readback(
            "variants_update", {"product_gid": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]},
            {
                "product": {"id": PRODUCT, "variants": {"nodes": [{"id": VARIANT, "price": "2.00"}]}},
                "unrelated": {"pageInfo": {"hasNextPage": False}},
            },
        )
        self.assertEqual(unrelated_variant_page.reason_code, "readback_incomplete")
        unrelated_media_page = evaluate_remote_readback(
            "media_associate", {"product_gid": PRODUCT, "file_gid": FILE},
            {
                "product": {"id": PRODUCT, "media": {"nodes": [{"id": FILE}]}},
                "files": {"pageInfo": {"hasNextPage": False}},
            },
        )
        self.assertEqual(unrelated_media_page.reason_code, "readback_incomplete")
        unrelated_file_page = evaluate_remote_readback(
            "media_file_create", {"filename": "hat.png"},
            {
                "files": {"nodes": [{"id": FILE, "filename": "hat.png"}]},
                "products": {"pageInfo": {"hasNextPage": False}},
            },
        )
        self.assertEqual(unrelated_file_page.reason_code, "readback_incomplete")

    def test_variant_and_media_readbacks_require_exact_product_identity(self):
        variant_expected = {"product_gid": PRODUCT, "variants": [{"id": VARIANT, "price": "2.00"}]}
        variant_observed = {
            "product": {
                "id": "gid://shopify/Product/99",
                "variants": {"nodes": [{"id": VARIANT, "price": "2.00"}], "pageInfo": {"hasNextPage": False}},
            },
        }
        mismatch = evaluate_remote_readback("variants_update", variant_expected, variant_observed)
        self.assertEqual((mismatch.verdict, mismatch.reason_code), (ReadbackVerdict.NOT_APPLIED, "product_identity_mismatch"))
        media_mismatch = evaluate_remote_readback(
            "media_associate", {"product_gid": PRODUCT, "file_gid": FILE},
            {"product": {"id": "gid://shopify/Product/99", "media": {"nodes": [{"id": FILE}], "pageInfo": {"hasNextPage": False}}}},
        )
        self.assertEqual((media_mismatch.verdict, media_mismatch.reason_code), (ReadbackVerdict.NOT_APPLIED, "product_identity_mismatch"))
        with self.assertRaisesRegex(ValueError, "expected product_gid"):
            evaluate_remote_readback(
                "variants_update", {"variants": [{"id": VARIANT, "price": "2.00"}]},
                {"product": {"id": PRODUCT, "variants": {"nodes": [], "pageInfo": {"hasNextPage": False}}}},
            )
        with self.assertRaisesRegex(ValueError, "expected product_gid"):
            evaluate_remote_readback(
                "media_associate", {"file_gid": FILE},
                {"product": {"id": PRODUCT, "media": {"nodes": [], "pageInfo": {"hasNextPage": False}}}},
            )

    def test_media_file_readback_requires_filename_or_immutable_gid(self):
        not_exact = evaluate_remote_readback(
            "media_file_create", {"filename": "hat.png"},
            {"files": {"nodes": [{"id": FILE}], "pageInfo": {"hasNextPage": False}}},
        )
        self.assertEqual((not_exact.verdict, not_exact.reason_code), (ReadbackVerdict.NOT_APPLIED, "file_not_found"))
        exact = evaluate_remote_readback(
            "media_file_create", {"file_gid": FILE},
            {"node": {"id": FILE}, "files": {"pageInfo": {"hasNextPage": True}}},
        )
        self.assertEqual((exact.verdict, exact.reason_code), (ReadbackVerdict.APPLIED, "verified_exact_file_identity"))
        self.assertIn("$query: String!", MEDIA_FILE_CREATE_READ_QUERY)
        self.assertIn("files(first: 5, query: $query)", MEDIA_FILE_CREATE_READ_QUERY)

    def test_strict_media_gid_uuid_and_exact_sequence_scope(self):
        with self.assertRaisesRegex(ValueError, "bounded"):
            build_export_payload(
                store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
                path="create", media=({"filename": 42, "checksum": "sha-1"},),
                source_write_date=NOW,
            )
        with self.assertRaisesRegex(ValueError, "canonical Shopify GID"):
            PreviewSnapshot.create(
                store_id=STORE, connection_generation=1, fingerprint="a" * 64,
                created_at=NOW, product_gid="Product/3",
            )
        payload = build_export_payload(
            store_id=STORE, store_identity=IDENTITY, connection_generation=1, template_id=9,
            path="update", product_gid=PRODUCT, scalar_fields={"title": "Hat"},
            authority={"title": "odoo"}, source_write_date=NOW, remote_updated_at=NOW,
        )
        with self.assertRaisesRegex(ValueError, "UUID"):
            ProductExportCommand("preview", payload, "cmd-1", "reviewer")
        product_gateway = ProductExportMutationGateway(Delegate(), PRODUCT_EXPORT_MUTATION_REGISTRY)
        bad_sequence = replace(build_export_sequence(payload), scope="product:other:gid://shopify/Product/3")
        with self.assertRaisesRegex(ValueError, "server-derived payload intent"):
            build_gateway_requests(payload, bad_sequence, product_gateway)


if __name__ == "__main__":
    unittest.main()
