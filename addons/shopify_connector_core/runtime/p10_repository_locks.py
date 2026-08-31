"""Deterministic lock helpers for the Odoo P10 repository adapter."""


def lock_claim_batch_scopes(side_env, job_ids):
    """Lock attempts and shared parents by table, then ascending identity."""
    ordered_job_ids = tuple(sorted(set(job_ids)))
    if not ordered_job_ids:
        return ()
    side_env.cr.execute(
        """SELECT id, run_id, store_id FROM shopify_connector_job
             WHERE id IN %s ORDER BY id""",
        [ordered_job_ids],
    )
    identities = {
        job_id: (run_id, store_id)
        for job_id, run_id, store_id in side_env.cr.fetchall()
        if run_id and store_id
    }
    valid_job_ids = []
    for job_id in ordered_job_ids:
        if job_id not in identities:
            continue
        side_env.cr.execute(
            """SELECT id FROM shopify_connector_job_attempt
                 WHERE job_id = %s AND outcome IN ('claimed', 'running')
                 ORDER BY id FOR UPDATE""",
            [job_id],
        )
        if not side_env.cr.fetchall():
            valid_job_ids.append(job_id)
    if not valid_job_ids:
        return ()
    run_ids = tuple(sorted({identities[job_id][0] for job_id in valid_job_ids}))
    store_ids = tuple(sorted({identities[job_id][1] for job_id in valid_job_ids}))
    side_env.cr.execute(
        """SELECT id FROM shopify_connector_run
             WHERE id IN %s ORDER BY id FOR UPDATE""",
        [run_ids],
    )
    locked_runs = {row[0] for row in side_env.cr.fetchall()}
    side_env.cr.execute(
        """SELECT id FROM shopify_connector_store
             WHERE id IN %s ORDER BY id FOR UPDATE""",
        [store_ids],
    )
    locked_stores = {row[0] for row in side_env.cr.fetchall()}
    side_env.cr.execute(
        """SELECT id, store_id FROM shopify_connector_store_settings
             WHERE store_id IN %s ORDER BY store_id, id FOR UPDATE""",
        [store_ids],
    )
    locked_settings = {row[1] for row in side_env.cr.fetchall()}
    return tuple(
        job_id for job_id in valid_job_ids
        if identities[job_id][0] in locked_runs
        and identities[job_id][1] in locked_stores
        and identities[job_id][1] in locked_settings
    )
