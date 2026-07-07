import json
import uuid

from odoo import api, fields, models


class ShopifyConnectorReadinessCheck(models.AbstractModel):
    """The readiness-check registry/service for `shopify_connector_core`.

    A stateless internal service (`AbstractModel` -- no table, no ACL row
    needed) that runs the fixed core-owned check set accepted by MBQ-06
    (DEC-018), aggregates the results fail-closed, and persists one
    `core_readiness_check` job per run.

    TD-001 fix (technical-debt-register.md): `core_readiness_check` job
    creation below uses its own fresh UUID4 `payload_hash` nonce, exactly
    mirroring the already-accepted `action_test_connection` pattern in
    `shopify_connector_store.py` for `core_test_connection` (Task 003).
    This is the whole fix -- scoped exclusively to this target-less job
    type, touching neither `shopify_connector_job.py` nor
    `shopify_connector_store.py`.

    Every check reads only already-stored core evidence (or, for
    `web.base.url`, `ir.config_parameter`) -- no Shopify API call, no
    domain-model read or write, and no secret is ever read, logged, or
    embedded in a check result.

    Domain-extension seam: `_get_checks()` is the one override point.
    A domain module extends the registry via classic Odoo inheritance
    (`_inherit = 'shopify.connector.readiness.check'`), overriding
    `_get_checks()` to call `super()._get_checks(store)` and append its
    own check dict(s) -- never removing or mutating a core-owned entry.
    """

    _name = 'shopify.connector.readiness.check'
    _description = 'Shopify Connector Readiness Check Service'

    ESSENTIAL = 'essential'
    WARNING = 'warning'

    RESULT_PASS = 'pass'
    RESULT_FAIL = 'fail'
    # Internal per-check state only -- never written to the store's
    # last_readiness_result mirror, whose selection is limited to
    # pass/fail/warning. An essential check in this state always makes
    # the overall summary 'fail' (fail-closed; never inferred as a pass).
    RESULT_NOT_PROVEN = 'not_proven'

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @api.model
    def run_for_store(self, store):
        """Run every registered readiness check for one store and persist it.

        Creates one `core_readiness_check` job (fresh UUID4 `payload_hash`
        nonce -- the TD-001 fix), runs the registered checks, aggregates
        fail-closed, appends the per-check JSON to
        `job.log.payload_snapshot` via the existing `_system_append` path,
        mirrors the summary onto `store.last_readiness_result`/`_at`, and
        marks the job succeeded -- the job's own state records that the
        readiness *evaluation* completed, independently of whether the
        readiness *result* itself is pass/fail/warning.

        Returns a dict: {'job': job, 'overall_result': str, 'checks': list}.
        """
        store.ensure_one()
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']

        job = Job.create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_readiness_check',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', 'Readiness check attempt started.',
        )

        checks = self._get_checks(store)
        overall_result = self._aggregate(checks)

        JobLog._system_append(
            job, 'verification_read',
            'Readiness check completed: overall %s.' % overall_result,
            payload_snapshot=json.dumps(checks),
            from_state='running', to_state='succeeded',
        )
        store.write({
            'last_readiness_result': overall_result,
            'last_readiness_at': fields.Datetime.now(),
        })
        job.write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        return {'job': job, 'overall_result': overall_result, 'checks': checks}

    # ------------------------------------------------------------------
    # Aggregation (fail-closed)
    # ------------------------------------------------------------------

    @api.model
    def _aggregate(self, checks):
        """Fail-closed aggregation over a list of check-result dicts.

        - Any essential check not RESULT_PASS (fail or not_proven) ->
          overall fail. An unknown/uncomputed essential state is never
          inferred as a pass.
        - All essential pass, but at least one warning-tier check is not
          RESULT_PASS -> overall warning. Warnings never block.
        - All essential pass and all warnings pass -> overall pass.
        """
        essential_all_pass = all(
            check['result'] == self.RESULT_PASS
            for check in checks
            if check['tier'] == self.ESSENTIAL
        )
        if not essential_all_pass:
            return self.RESULT_FAIL
        warnings_all_pass = all(
            check['result'] == self.RESULT_PASS
            for check in checks
            if check['tier'] == self.WARNING
        )
        if not warnings_all_pass:
            return self.WARNING
        return self.RESULT_PASS

    # ------------------------------------------------------------------
    # Registry / domain-extension seam
    # ------------------------------------------------------------------

    @api.model
    def _get_checks(self, store):
        """Return the ordered list of computed check-result dicts for `store`.

        The domain-extension registration seam: override this method via
        classic Odoo model inheritance, call
        `super()._get_checks(store)` first, then append additional check
        dict(s) (each built with `_check_result`) -- never remove or
        mutate an entry returned by the core implementation.
        """
        return [
            self._check_credential_test_connection(store),
            self._check_required_scopes(store),
            self._check_api_version_health(store),
            self._check_store_identity(store),
            self._check_web_base_url(store),
            self._check_webhook_hmac(store),
            self._check_mapped_location(store),
            self._check_cron_queue_health(store),
            self._check_domain_flag_enablement(store),
        ]

    @api.model
    def _check_result(self, code, tier, result, reason):
        return {'code': code, 'tier': tier, 'result': result, 'reason': reason}

    # ------------------------------------------------------------------
    # Core-owned checks (MBQ-06 / DEC-018 essential set)
    # ------------------------------------------------------------------

    @api.model
    def _check_credential_test_connection(self, store):
        """Stored-evidence only -- never a live Shopify call (DEC-021 §4).

        Reads only `store.last_test_connection_result`, the Task 003
        mirror. Reports `not_proven`, never `pass`, when that mirror has
        never recorded a pass -- a hard, non-negotiable rule while VAL-B2
        remains deferred.
        """
        code = 'credential_test_connection'
        if store.last_test_connection_result == 'pass':
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Stored test-connection evidence is a pass.',
            )
        if store.last_test_connection_result == 'fail':
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'Stored test-connection evidence is a fail: %s' % (
                    store.last_test_connection_reason or 'no reason recorded',
                ),
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
            'No stored test-connection evidence exists for this store yet.',
        )

    @api.model
    def _check_required_scopes(self, store):
        """Reads `store.granted_scopes` only -- no live Shopify call."""
        code = 'required_scopes'
        if not store.granted_scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'No granted-scopes snapshot recorded for this store yet.',
            )
        try:
            scopes = json.loads(store.granted_scopes)
        except (TypeError, ValueError):
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'Stored granted-scopes snapshot is not valid JSON.',
            )
        if not isinstance(scopes, list) or not scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'Stored granted-scopes snapshot is empty or malformed.',
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'Granted-scopes snapshot recorded: %d scope(s).' % len(scopes),
        )

    @api.model
    def _check_api_version_health(self, store):
        """Reads `store.api_health_state`/`_reason` only -- no live call."""
        code = 'api_version_health'
        if store.api_health_state == 'normal':
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'API health state is normal.',
            )
        if store.api_health_state in ('throttled', 'degraded'):
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'API health state is %s: %s' % (
                    store.api_health_state,
                    store.api_health_reason or 'no reason recorded',
                ),
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
            'No API health state recorded for this store yet.',
        )

    @api.model
    def _check_store_identity(self, store):
        """Reads local store fields only (`shop_domain`)."""
        code = 'store_identity'
        if store.shop_domain:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Store shop_domain is configured: %s.' % store.shop_domain,
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_FAIL,
            'Store shop_domain is not configured.',
        )

    @api.model
    def _check_web_base_url(self, store):
        """Reads `ir.config_parameter` only -- no external network call."""
        code = 'web_base_url'
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if not base_url:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'web.base.url is not configured.',
            )
        if base_url.startswith('https://'):
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'web.base.url is configured and uses HTTPS.',
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_FAIL,
            'web.base.url is configured but is not HTTPS.',
        )

    @api.model
    def _check_webhook_hmac(self, store):
        """Registered pending slot only -- no webhook implementation exists."""
        return self._check_result(
            'webhook_hmac', self.ESSENTIAL, self.RESULT_NOT_PROVEN,
            'Webhook HMAC verification is not implemented yet -- '
            'registered as a pending check slot only.',
        )

    @api.model
    def _check_mapped_location(self, store):
        """Registered pending slot only -- Location mapping is domain-owned.

        `shopify.connector.location` is a Shopify-side-only cache with no
        mapped-Odoo-location or domain-enablement concept (see its own
        docstring) -- that mapping is owned by a future inventory domain
        module. Reporting this as anything but not_proven here would
        require a domain-model dependency this task must not add.
        """
        return self._check_result(
            'mapped_location', self.ESSENTIAL, self.RESULT_NOT_PROVEN,
            'Mapped-Location verification requires a future domain '
            'module -- registered as a pending check slot only.',
        )

    @api.model
    def _check_cron_queue_health(self, store):
        """Registered pending slot only -- no cron/queue implementation exists."""
        return self._check_result(
            'cron_queue_health', self.ESSENTIAL, self.RESULT_NOT_PROVEN,
            'Cron/queue health verification is not implemented yet -- '
            'registered as a pending check slot only.',
        )

    @api.model
    def _check_domain_flag_enablement(self, store):
        """Reads `shopify.connector.store.settings` presence only.

        No per-flag "explicitly set" tracking exists on the settings
        model (every domain flag defaults to False), so the only safe,
        non-inferred signal available at core level is whether an
        explicit settings record exists for this store at all.
        """
        code = 'domain_flag_enablement'
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if settings:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Store-settings record exists; domain enablement is '
                'explicitly configured.',
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
            'No store-settings record exists yet -- domain enablement '
            'has not been configured.',
        )
