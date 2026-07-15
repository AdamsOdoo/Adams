"""LC-1: preserve the original domain job type on upgrade."""


def migrate(cr, version):
    # Additive and idempotent. The column is created by the ORM before this
    # post-migration runs; pre-existing jobs receive their then-current type.
    cr.execute(
        """
        UPDATE shopify_connector_job
           SET original_job_type = job_type
         WHERE original_job_type IS NULL
        """
    )
