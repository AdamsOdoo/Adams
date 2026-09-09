"""Odoo adapter for the bounded P06 read gateways.

This model is an adapter, not a second Shopify client.  It resolves the
store-scoped migration mode, delegates through the existing authorized API
client/credential boundary, and exposes only the exact query documents owned
by the core/product/sale addons.  It has no table and never performs a write
or job transition.  In ``compare_reads`` mode the legacy result remains the
source of business truth; a deterministic, bounded typed sample produces only
digest evidence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Callable

from odoo import SUPERUSER_ID, api, models
from odoo.exceptions import AccessError, MissingError, UserError

from ..integration.shopify.read_comparison import (
    ReadComparisonEvidence,
    REPLAY_SAFE_READ_OPERATIONS,
    compare_values,
    safe_digest,
    should_compare,
)
from ..integration.shopify.read_contracts import (
    CursorProgress,
    ReadCompatibilityAdapter,
    ReadGatewayError,
    ReadGatewayMode,
    ReadOperation,
    ReadResult,
)
from ..integration.shopify.read_gateway import (
    LocationReadGateway,
    StoreCapabilityReadGateway,
)


_STORE_MODES = frozenset(("legacy", "compare_reads", "v2"))
_CONNECTOR_GROUP_PREFIX = "shopify_connector_core.group_shopify_connector_"
_READ_ROLES = ("admin", "reviewer", "operator", "auditor")
_COMPARE_SAMPLE_MODULUS = 100

# The normal read surface remains role-gated.  The root cron reaches it only
# after the dispatcher has acquired a real job row and bound execution to that
# job's company.  Object identity makes the capability impossible to construct
# through an RPC context; the owner tuple additionally binds it to this exact
# cursor/claim path and job/store/company identity.  A copied context on a side
# cursor therefore cannot inherit worker authority.
READ_WORKER_CAPABILITY_CONTEXT = "shopify_read_worker_capability"
READ_WORKER_OWNER_CONTEXT = "shopify_read_worker_owner"
_READ_WORKER_CAPABILITY = object()


class _AuthorizedReadDelegate:
    """Bridge one pure adapter call to the existing Odoo API client.

    The delegate deliberately has no URL, token, requests, or retry logic.  A
    job-owned read enters the current ``execute_business`` admission lease;
    the two lifecycle identity methods may use the existing ``execute`` path
    when no job is supplied.  Both paths issue exactly one authorized request.
    """

    def __init__(
        self,
        client: Any,
        documents: Mapping[str, str],
        *,
        job: Any = None,
        purpose: str | None = None,
        claim: Any = None,
        allow_lifecycle: bool = False,
    ) -> None:
        self.client = client
        self.documents = documents
        self.job = job
        self.purpose = purpose
        self.claim = claim
        self.allow_lifecycle = allow_lifecycle

    def execute(self, store: Any, document: str, variables: Mapping[str, Any]) -> Any:
        if self.job is None:
            if not self.allow_lifecycle:
                raise ReadGatewayError(
                    "job_required",
                    "A Shopify domain read requires an admitted connector job.",
                )
            # Core setup/identity reads retain the exact public client path.
            return self.client.execute(store, document, variables)
        if not self.purpose:
            raise ReadGatewayError(
                "purpose_required",
                "A Shopify domain read requires a fixed admission purpose.",
            )
        with self.client.execute_business_read(
            self.job,
            store,
            document,
            variables,
            purpose=self.purpose,
            claim=self.claim,
        ) as result:
            return result

    def execute_read(
        self,
        store: Any,
        operation: ReadOperation,
        variables: Mapping[str, Any],
    ) -> Any:
        document = self.documents.get(operation.operation_name)
        if not isinstance(document, str):
            raise ReadGatewayError(
                "operation_unconfigured",
                "The checked-in Shopify read operation is not configured.",
                operation.operation_name,
            )
        return self.execute(store, document, variables)


class ShopifyConnectorReadGateway(models.AbstractModel):
    """Store-scoped Odoo adapter over the P06 pure read gateways."""

    _name = "shopify.connector.read.gateway"
    _description = "Shopify Connector P06 Read Gateway"

    # ------------------------------------------------------------------
    # Scope, mode and document resolution
    # ------------------------------------------------------------------

    @api.model
    def _claimed_dispatch_scope(self, dispatcher: Any, job: Any) -> tuple:
        """Bind an already-claimed job worker to its exact owning company.

        This private method is called only by ``_drain_one`` immediately after
        its row-lock claim.  Root receives the unforgeable read capability;
        an Administrator-run manual drain receives only the company binding
        and continues through the ordinary connector-role check.
        """
        job.ensure_one()
        company = job.company_id
        worker = dispatcher.with_company(company)
        context = {}
        if worker.env.su and worker.env.uid == SUPERUSER_ID:
            context = {
                READ_WORKER_CAPABILITY_CONTEXT: _READ_WORKER_CAPABILITY,
                READ_WORKER_OWNER_CONTEXT: (
                    worker.env.cr, job.id, job.store_id.id, company.id,
                ),
            }
        worker = worker.with_context(**context)
        scoped_job = worker.env["shopify.connector.job"].browse(job.id)
        return worker, scoped_job, job.id, job.store_id.id

    @api.model
    def _is_owned_root_worker_read(self, job: Any, store: Any) -> bool:
        """Recognize only the claimed root worker scope minted by dispatch."""
        context = self.env.context
        if not (
            self.env.su
            and self.env.uid == SUPERUSER_ID
            and context.get(READ_WORKER_CAPABILITY_CONTEXT)
            is _READ_WORKER_CAPABILITY
        ):
            return False
        owner = context.get(READ_WORKER_OWNER_CONTEXT)
        if not (
            isinstance(owner, tuple)
            and len(owner) == 4
            and owner[0] is self.env.cr
        ):
            return False
        try:
            job.ensure_one()
            store.ensure_one()
        except Exception:
            return False
        if (
            getattr(job, "_name", None) != "shopify.connector.job"
            or getattr(store, "_name", None) != "shopify.connector.store"
            or job.env.cr is not self.env.cr
            or store.env.cr is not self.env.cr
            or not job.exists()
            or not store.exists()
        ):
            return False
        cursor, job_id, store_id, company_id = owner
        del cursor
        return bool(
            job.id == job_id
            and store.id == store_id
            and job.state == "running"
            and job.store_id.id == store.id
            and job.company_id.id == company_id
            and store.company_id.id == company_id
            and self.env.company.id == company_id
        )

    @api.model
    def _assert_connector_role(self, job: Any = None, store: Any = None) -> None:
        for suffix in _READ_ROLES:
            if self.env.user.has_group(_CONNECTOR_GROUP_PREFIX + suffix):
                return
        if self._is_owned_root_worker_read(job, store):
            return
        raise AccessError("This Shopify read surface is limited to connector users.")

    @api.model
    def _assert_store(self, store: Any, *, job: Any = None) -> Any:
        self._assert_connector_role(job=job, store=store)
        if not store or not hasattr(store, "ensure_one"):
            raise UserError("Choose one valid Shopify store.")
        try:
            store.ensure_one()
        except Exception as exc:
            raise UserError("Choose one valid Shopify store.") from exc
        # Odoo 19's combined record access API must run before ``exists()`` or
        # a company comparison.  This collapses missing and foreign records
        # into one refusal and avoids an existence side channel.  There is no
        # sudo() here: a gateway read must never cross tenant scope.
        try:
            if not store.has_access("read"):
                raise AccessError("store read denied")
            store.check_access("read")
        except (AccessError, MissingError) as exc:
            raise AccessError("The requested Shopify store is not readable.") from exc
        if not store.exists() or store.company_id.id != self.env.company.id:
            raise AccessError("The requested Shopify store is not in the active company.")
        return store

    @api.model
    def _store_mode(self, store: Any) -> str:
        settings = self.env["shopify.connector.store.settings"].search(
            [
                ("store_id", "=", store.id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        mode = settings.v2_gateway_mode if settings else "legacy"
        if mode not in _STORE_MODES:
            raise UserError("The store has an unsupported read gateway mode.")
        return mode

    @api.model
    def _extend_documents(
        self, names: set[str] | frozenset[str], documents: dict[str, str],
    ) -> dict[str, str]:
        """Domain addons append their own checked-in query documents."""
        del names
        return documents

    @api.model
    def _documents(self, names: set[str] | frozenset[str]) -> dict[str, str]:
        """Load exact core documents, then invoke domain-owned extensions."""

        documents: dict[str, str] = {}
        if "ConnectorTestConnection" in names:
            from .shopify_connector_store import TEST_CONNECTION_QUERY

            documents["ConnectorTestConnection"] = TEST_CONNECTION_QUERY
        documents = self._extend_documents(names, documents)
        if not isinstance(documents, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in documents.items()
        ):
            raise UserError("A Shopify read document provider is malformed.")
        missing = set(names) - set(documents)
        if missing:
            raise UserError(
                "The requested Shopify read operation is not installed: %s."
                % ", ".join(sorted(missing))
            )
        return documents

    @api.model
    def _adapter(
        self,
        store: Any,
        job: Any,
        names: set[str] | frozenset[str],
        *,
        purpose: str | None = None,
        claim: Any = None,
        allow_lifecycle: bool = False,
    ) -> tuple[ReadCompatibilityAdapter, str, dict[str, str]]:
        documents = self._documents(names)
        client = self.env["shopify.connector.api.client"]
        delegate = _AuthorizedReadDelegate(
            client,
            documents,
            job=job,
            purpose=purpose,
            claim=claim,
            allow_lifecycle=allow_lifecycle,
        )
        return (
            ReadCompatibilityAdapter(
                delegate,
                documents,
                typed_delegate=delegate,
                mode=ReadGatewayMode.LEGACY,
            ),
            self._store_mode(store),
            documents,
        )

    # ------------------------------------------------------------------
    # One bounded call with optional compare sampling
    # ------------------------------------------------------------------

    @api.model
    def _record_comparison(
        self,
        job: Any,
        evidence: ReadComparisonEvidence,
        *,
        claim: Any = None,
    ) -> None:
        if not job:
            return
        # The sanctioned append-only log path redacts again.  The payload is
        # already digest-only; no response, variables, PII or credentials are
        # persisted.
        def append(env, target):
            env["shopify.connector.job.log"]._system_append(
                target,
                "verification_read",
                "P06 %s read comparison %s."
                % (
                    evidence.operation_name,
                    "matched" if evidence.equal else "differed",
                ),
                technical_detail=json.dumps(
                    evidence.as_dict(), sort_keys=True, separators=(",", ":")
                ),
            )

        if claim is None:
            append(self.env, job)
            return
        cursor = self.env.registry.cursor()
        side_env = api.Environment(
            cursor,
            SUPERUSER_ID,
            dict(self.env.context, allowed_company_ids=[claim.company_id]),
        )
        try:
            side_job = side_env["shopify.connector.job"].browse(
                claim.job_id,
            ).exists()
            if (
                not side_job
                or side_job.id != job.id
                or side_job.store_id.id != claim.store_id
                or side_job.company_id.id != claim.company_id
                or side_job.run_id.id != claim.run_id
            ):
                cursor.rollback()
                return
            append(side_env, side_job)
            side_env.flush_all()
            cursor.commit()
        except Exception:
            cursor.rollback()
            raise
        finally:
            cursor.close()

    @api.model
    def _run(
        self,
        store: Any,
        job: Any,
        operation: ReadOperation,
        names: set[str] | frozenset[str],
        reader: Callable[[ReadCompatibilityAdapter], ReadResult[Any]],
        variables: Mapping[str, Any],
        *,
        purpose: str | None = None,
        claim: Any = None,
        allow_lifecycle: bool = False,
    ) -> ReadResult[Any]:
        store = self._assert_store(store, job=job)
        adapter, mode, _documents = self._adapter(
            store,
            job,
            names,
            purpose=purpose,
            claim=claim,
            allow_lifecycle=allow_lifecycle,
        )
        if mode == "legacy":
            return reader(adapter)
        typed_adapter = adapter.for_mode(ReadGatewayMode.TYPED)
        if mode == "v2":
            return reader(typed_adapter)
        if operation.operation_name not in REPLAY_SAFE_READ_OPERATIONS:
            raise ReadGatewayError(
                "comparison_not_allowed",
                "Only replay-safe Shopify reads may be compared.",
                operation.operation_name,
            )
        legacy_result = reader(adapter)
        if not should_compare(
            store.id,
            operation.operation_name,
            variables,
            modulus=_COMPARE_SAMPLE_MODULUS,
        ):
            return legacy_result
        try:
            typed_result = reader(typed_adapter)
        except Exception:
            # Compare mode is explicitly rollback-safe: a typed shape defect
            # is evidence, while the already successful legacy result remains
            # the business answer.  Never persist exception text.
            evidence = ReadComparisonEvidence(
                operation.operation_name,
                True,
                False,
                safe_digest(legacy_result),
                None,
                typed_error=True,
            )
        else:
            evidence = compare_values(operation.operation_name, legacy_result, typed_result)
        self._record_comparison(job, evidence, claim=claim)
        return legacy_result

    @staticmethod
    def _rpc(result: ReadResult[Any]) -> dict[str, Any]:
        if not isinstance(result, ReadResult):
            raise ReadGatewayError("invalid_result", "The Shopify read did not return a typed result.")
        return result.as_dict()

    # ------------------------------------------------------------------
    # Explicit core/product/sale methods.  There is no generic dispatcher.
    # ------------------------------------------------------------------

    @api.model
    def read_store_capability(self, store: Any) -> dict[str, Any]:
        operation = self._core_capability_operation()
        result = self._run(
            store,
            None,
            operation,
            {"ConnectorTestConnection"},
            lambda adapter: StoreCapabilityReadGateway(adapter).read(store),
            {},
            allow_lifecycle=True,
        )
        return self._rpc(result)

    @staticmethod
    def _core_capability_operation() -> ReadOperation:
        from ..integration.shopify.read_gateway import STORE_CAPABILITY_OPERATION

        return STORE_CAPABILITY_OPERATION

    @api.model
    def read_location_page(
        self,
        job: Any,
        store: Any,
        *,
        cursor: str | None = None,
        progress: CursorProgress | None = None,
    ) -> dict[str, Any]:
        from ..integration.shopify.read_gateway import LOCATION_PAGE_OPERATION

        result = self._run(
            store,
            job,
            LOCATION_PAGE_OPERATION,
            {"ConnectorFulfillmentLocations"},
            lambda adapter: LocationReadGateway(adapter).read_page(
                store, cursor=cursor, progress=progress
            ),
            {"cursor": cursor},
            purpose="fulfillment",
        )
        return self._rpc(result)

__all__ = ["ShopifyConnectorReadGateway"]
