"""WP-6 bounded retention query indexes; additive and repeat-safe."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_connector_job_finished_state_idx "
        "ON shopify_connector_job (finished_at, state, id) "
        "WHERE finished_at IS NOT NULL"
    )
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_connector_attempt_resolved_idx "
        "ON shopify_connector_mutation_attempt (resolved_at, id) "
        "WHERE resolved_at IS NOT NULL"
    )
