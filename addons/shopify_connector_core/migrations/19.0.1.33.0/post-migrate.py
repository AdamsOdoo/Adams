"""Backfill additive V2 mutation-attempt identity and its query index."""


def migrate(cr, version):
    if not version:
        return
    # The ORM creates these nullable/defaulted columns before post-migrate.
    # Copy only the server-owned run/configuration snapshot from each locked
    # job; never invent a run for a legacy attempt.
    cr.execute(
        """
        UPDATE shopify_connector_mutation_attempt AS attempt
           SET run_id = job.run_id,
               expected_configuration_generation =
                   COALESCE(job.expected_configuration_generation, 0)
          FROM shopify_connector_job AS job
         WHERE attempt.job_id = job.id
           AND job.run_id IS NOT NULL
           AND (
               attempt.run_id IS DISTINCT FROM job.run_id
               OR attempt.expected_configuration_generation IS DISTINCT FROM
                  COALESCE(job.expected_configuration_generation, 0)
           )
        """
    )
    cr.execute(
        """
        CREATE INDEX IF NOT EXISTS
            shopify_connector_mutation_attempt_v2_scope_idx
            ON shopify_connector_mutation_attempt
               (run_id, expected_configuration_generation, id)
            WHERE run_id IS NOT NULL
        """
    )
