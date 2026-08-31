"""Exact P10 claim fencing for the existing business-read transport."""

from __future__ import annotations

from odoo import models

from ..runtime.p10_claim_fence import (
    AttemptClaimState,
    JobClaimState,
    ReadClaimSnapshot,
    RunClaimState,
    SettingsClaimState,
    StoreClaimState,
    read_claim_matches,
)
from ..runtime.p10_coordinator import ClaimedWork
from .shopify_connector_api_client import ShopifyQuiescedError


class ShopifyConnectorApiClientV2ReadClaim(models.AbstractModel):
    """Require the exact committed P10 owner before a claimed network read."""

    _inherit = "shopify.connector.api.client"

    @staticmethod
    def _one_locked_row(side_cr, query, params):
        side_cr.execute(query, params)
        row = side_cr.fetchone()
        if not row:
            raise ShopifyQuiescedError(
                "The V2 read claim is stale or no longer owns this work."
            )
        return row

    def _lock_v2_read_claim_snapshot(self, side_cr, claim):
        """Lock one claim in the global job→attempt→run→store→settings order."""

        job = JobClaimState(*self._one_locked_row(
            side_cr,
            """
                SELECT id, store_id, company_id, job_type, job_source, state,
                       current_attempt_token, owner_worker_ref,
                       expected_connection_generation,
                       expected_configuration_generation, run_id, lane,
                       operation_scope_key, mutation_attempt_id
                  FROM shopify_connector_job
                 WHERE id = %s
                 FOR SHARE
            """,
            (claim.job_id,),
        ))
        attempt = AttemptClaimState(*self._one_locked_row(
            side_cr,
            """
                SELECT attempt_no, claim_token, worker_ref, outcome, run_id
                  FROM shopify_connector_job_attempt
                 WHERE job_id = %s AND claim_token = %s
                 FOR SHARE
            """,
            (claim.job_id, claim.claim_token),
        ))
        run = RunClaimState(*self._one_locked_row(
            side_cr,
            """
                SELECT store_id, company_id, state, cancel_requested_at,
                       expected_connection_generation,
                       expected_configuration_generation
                  FROM shopify_connector_run
                 WHERE id = %s
                 FOR SHARE
            """,
            (job.run_id,),
        ))
        store = StoreClaimState(*self._one_locked_row(
            side_cr,
            """
                SELECT company_id, state, connection_generation,
                       shop_domain, api_version
                  FROM shopify_connector_store
                 WHERE id = %s
                 FOR SHARE
            """,
            (job.store_id,),
        ))
        side_cr.execute(
            """
                SELECT company_id, configuration_generation, v2_runtime_mode
                  FROM shopify_connector_store_settings
                 WHERE store_id = %s
                 ORDER BY id
                 LIMIT 2
                 FOR SHARE
            """,
            (job.store_id,),
        )
        settings_rows = side_cr.fetchall()
        if len(settings_rows) != 1:
            raise ShopifyQuiescedError(
                "The V2 read claim has no unique store settings owner."
            )
        return ReadClaimSnapshot(
            job=job,
            attempt=attempt,
            run=run,
            store=store,
            settings=SettingsClaimState(*settings_rows[0]),
        )

    def _assert_v2_read_claim(self, side_cr, job, store, claim):
        if not isinstance(claim, ClaimedWork):
            raise ShopifyQuiescedError(
                "A claimed V2 read requires immutable runtime identity."
            )
        if claim.job_id != job.id or claim.store_id != store.id:
            raise ShopifyQuiescedError(
                "The V2 read claim does not own this job and store."
            )
        snapshot = self._lock_v2_read_claim_snapshot(side_cr, claim)
        if not read_claim_matches(
            snapshot, claim, tuple(self.env.companies.ids),
        ):
            raise ShopifyQuiescedError(
                "The V2 read claim is stale or no longer owns this work."
            )
        return snapshot

    def _preflight_business_read_claim(self, job, store, claim):
        if claim is None:
            return None
        side_cr = self.env.registry.cursor()
        try:
            snapshot = self._assert_v2_read_claim(side_cr, job, store, claim)
            side_cr.commit()
            return snapshot
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()

    def _validate_business_read_claim_locked(
        self, side_cr, job, store, claim,
    ):
        if claim is None:
            return None
        return self._assert_v2_read_claim(side_cr, job, store, claim)

    def _claimed_business_read_values(
        self, side_cr, job, store, claim, preflight_snapshot,
    ):
        snapshot = self._validate_business_read_claim_locked(
            side_cr, job, store, claim,
        )
        if snapshot.endpoint != preflight_snapshot.endpoint:
            raise ShopifyQuiescedError(
                "The Shopify endpoint changed during read admission."
            )
        return (
            snapshot.job.store_id,
            snapshot.job.job_source,
            snapshot.job.job_type,
            snapshot.job.connection_generation,
            snapshot.store.company_id,
            snapshot.store.state,
            snapshot.store.connection_generation,
            snapshot.store.shop_domain,
            snapshot.store.api_version,
            claim.worker_ref,
        )


__all__ = ["ShopifyConnectorApiClientV2ReadClaim"]
