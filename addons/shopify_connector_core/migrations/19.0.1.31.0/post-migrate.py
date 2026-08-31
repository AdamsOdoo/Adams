"""P09 additive runtime indexes; restart-safe and data preserving."""


def migrate(cr, version):
    del version
    # Older releases could already have masked evidence without an explicit
    # progress marker.  Mark those rows from their terminal timestamp so the
    # bounded sweep advances instead of selecting the same oldest batch.
    cr.execute(
        "UPDATE shopify_connector_mutation_attempt "
        "SET evidence_masked_at = resolved_at "
        "WHERE evidence_masked_at IS NULL "
        "AND resolved_at IS NOT NULL "
        "AND remote_mutation_intent = '{\"masked\": true}'::jsonb "
        "AND preconditions_snapshot = '{\"masked\": true}'::jsonb "
        "AND remote_evidence_refs = '{\"masked\": true}'::jsonb"
    )
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_mutation_retention_pending_idx "
        "ON shopify_connector_mutation_attempt (resolved_at, id) "
        "WHERE resolved_at IS NOT NULL AND evidence_masked_at IS NULL"
    )
    # Historic jobs intentionally keep NULL run/lane/availability fields.
    # The old dispatcher therefore remains behaviorally unchanged after a
    # warm update.  Only V2 admission creates populated runtime rows.
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_connector_job_v2_due_idx "
        "ON shopify_connector_job "
        "(lane, available_at, lane_priority, id) "
        "WHERE state IN ('queued', 'retry_waiting') "
        "AND lane IS NOT NULL"
    )
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_connector_run_store_time_idx "
        "ON shopify_connector_run (store_id, requested_at DESC, id DESC)"
    )
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_connector_attempt_job_time_idx "
        "ON shopify_connector_job_attempt "
        "(job_id, claimed_at DESC, id DESC)"
    )
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_connector_attempt_stale_idx "
        "ON shopify_connector_job_attempt (outcome, heartbeat_at, id) "
        "WHERE outcome IN ('claimed', 'running')"
    )
