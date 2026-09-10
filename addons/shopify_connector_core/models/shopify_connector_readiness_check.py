import json
import uuid
from datetime import timedelta

from odoo import _, api, fields, models


SUPPORTED_STORES_PER_DATABASE = 10
SUPPORTED_JOBS_PER_MINUTE = 1000
SUPPORTED_STORE_POPULATIONS = (
    ('shopify.connector.product.template.binding', 100000, 'products'),
    ('shopify.connector.order.binding', 100000, 'orders'),
    ('shopify.connector.inventory.level.binding', 100000, 'inventory pairs'),
    ('shopify.connector.fulfillment.binding', 100000, 'fulfillments'),
)


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

    # The accepted Phase 1 MVP scope set (DEC-003/DEC-007 domain scope --
    # product, customer, order, inventory, location, fulfillment reads).
    # Extra granted scopes beyond this set are allowed; every one of
    # these must be present for the required-scopes check to pass.
    REQUIRED_MVP_SCOPES = (
        'read_products',
        'read_customers',
        'read_orders',
        'read_inventory',
        'read_locations',
        # TD-002 / D-014-2: the FulfillmentOrder-based mutation flow requires
        # read_merchant_managed_fulfillment_orders (read_fulfillments governs
        # FulfillmentService apps, not this merchant-managed connector). The
        # matching write scope is checked by the fulfillment domain's own
        # readiness seam when the fulfillment domain is enabled.
        'read_merchant_managed_fulfillment_orders',
    )

    # The four DEC-008 domain-module flags core itself owns, on
    # `shopify.connector.store.settings`. `notification_default_enabled`
    # and any other settings field is not a sync-domain flag and must
    # never cause a pass by itself. This is the CORE-owned base only --
    # `_accepted_domain_flags()` below is the recognized set a domain
    # module extends; nothing outside this file reads this tuple directly.
    ACCEPTED_DOMAIN_FLAGS = (
        'product_domain_enabled',
        'sale_domain_enabled',
        'inventory_domain_enabled',
        'fulfillment_domain_enabled',
    )

    # D-R1-1 (Task CORE-R1): a queued job for this store that has never
    # started (`started_at` unset) and is older than this threshold is a
    # stalled-queue signal `_check_cron_queue_health` fails on. Named,
    # tunable module constant -- never an inlined magic number.
    READINESS_QUEUE_STALL_MINUTES = 60

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

        job = Job.sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_readiness_check',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        job = Job.browse(job.id)
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
        store._store_service_write('_readiness', {
            'last_readiness_result': overall_result,
            'last_readiness_at': fields.Datetime.now(),
        })
        job.sudo().write({
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
            self._check_supported_scale(store),
        ]

    @api.model
    def _check_result(self, code, tier, result, reason, not_applicable=False):
        """One check result.

        `not_applicable` (Wave 5) is a PRESENTATION fact, not a new verdict:
        several checks legitimately return `pass` because the thing they
        verify does not apply to this store -- the inventory domain is off,
        webhook intake is not installed. Aggregation is unchanged (a
        not-applicable check still counts as a pass and still cannot block),
        but a surface that renders "Passed" in green for a domain the
        operator deliberately disabled is telling them something was proven
        when nothing was checked. The setup wizard's readiness projection
        renders these as `Not required`, which is the true statement.

        Written as a key on the dict rather than inferred from the reason
        text: a check's copy is translatable and editable, and a
        presentation rule that depends on a phrase inside it breaks the
        first time somebody rewords it.
        """
        return {
            'code': code, 'tier': tier, 'result': result, 'reason': reason,
            'not_applicable': bool(not_applicable),
        }

    @api.model
    def _supported_scale_counts(self, store):
        """Bounded local counts; no Shopify request and no credential read."""
        counts = [(
            'stores',
            self.env['shopify.connector.store'].sudo().search_count(
                [], limit=SUPPORTED_STORES_PER_DATABASE + 1,
            ),
            SUPPORTED_STORES_PER_DATABASE,
        )]
        counts.append((
            'jobs in the latest minute',
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', store.id),
                (
                    'create_date', '>=',
                    fields.Datetime.now() - timedelta(minutes=1),
                ),
            ], limit=SUPPORTED_JOBS_PER_MINUTE + 1),
            SUPPORTED_JOBS_PER_MINUTE,
        ))
        for model_name, limit, label in SUPPORTED_STORE_POPULATIONS:
            if model_name not in self.env.registry.models:
                continue
            count = self.env[model_name].sudo().search_count([
                ('store_id', '=', store.id),
            ], limit=limit + 1)
            counts.append((label, count, limit))
        return counts

    @api.model
    def _check_supported_scale(self, store):
        exceeded = [
            (label, count, limit)
            for label, count, limit in self._supported_scale_counts(store)
            if count > limit
        ]
        if exceeded:
            return self._check_result(
                'supported_scale', self.ESSENTIAL, self.RESULT_FAIL,
                'Supported boundary exceeded: %s.' % '; '.join(
                    '%s %d > %d' % item for item in exceeded
                ),
            )
        return self._check_result(
            'supported_scale', self.ESSENTIAL, self.RESULT_PASS,
            'Connector populations are within the enforced public limits.',
        )

    @api.model
    def _accepted_domain_flags(self):
        """The recognized sync-domain flag names, extensible per module.

        Correction B (independent review, Defect #3). The SAME
        domain-extension shape `_get_checks` already uses: a domain module
        overrides this, calls `super()._accepted_domain_flags()`, and
        returns the union with its own flag name(s) -- never removing a
        core-owned entry. `_check_domain_flag_enablement` reads this rather
        than the fixed `ACCEPTED_DOMAIN_FLAGS` tuple directly, so an
        installed domain's own sync-domain flag (e.g. Product Export's
        `product_export_domain_enabled`) is recognized as enabled without
        editing this file.
        """
        return self.ACCEPTED_DOMAIN_FLAGS

    @api.model
    def _governed_scope_catalog(self):
        """The scopes this install may request, with a business reason each.

        The same extension shape again, this time for the S1 wizard's step
        4 "Permissions" DISPLAY list (`ShopifyConnectorSetupWizard.
        _setup_required_scopes`). Step 4 runs before step 7's domain choice
        exists, so it necessarily shows the full installed superset an
        operator might need to grant, not a set narrowed by a decision they
        have not made yet -- exactly why this is a catalog of "may be
        needed", read here, rather than `REQUIRED_MVP_SCOPES` (the
        unconditional baseline `_check_required_scopes` enforces for every
        store regardless of which domains end up enabled). A domain module
        extends this to add its own entries; it must not touch
        `REQUIRED_MVP_SCOPES`, which stays core's own always-required set.
        """
        return [
            {'scope': scope, 'reason': reason}
            for scope, reason in (
                ('read_products', _(
                    'so your Shopify catalog can be read into Odoo',
                )),
                ('read_customers', _(
                    'so order customers can be matched to Odoo contacts',
                )),
                ('read_orders', _(
                    'so Shopify orders can become Odoo sales orders',
                )),
                ('read_inventory', _(
                    'so stock levels can be read as a baseline',
                )),
                ('read_locations', _(
                    'so Shopify locations can be mapped to your Odoo '
                    'warehouses',
                )),
                ('read_merchant_managed_fulfillment_orders', _(
                    'so deliveries can be matched to the right Shopify '
                    'fulfillment order',
                )),
            )
        ]

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
        """Reads `store.granted_scopes` only -- no live Shopify call.

        Passes only when every scope in `self.REQUIRED_MVP_SCOPES` is
        present in the stored snapshot -- extra granted scopes are
        allowed, but a non-empty snapshot missing even one required
        scope must not pass.
        """
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
        granted = set(scopes)
        missing = [
            scope for scope in self.REQUIRED_MVP_SCOPES
            if scope not in granted
        ]
        if missing:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'Missing required scope(s): %s.' % ', '.join(missing),
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'All required scopes are granted (%d scope(s) recorded).' % (
                len(scopes),
            ),
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
    def _web_base_url(self):
        """Read `web.base.url`, elevated, for exactly the reason the cron read
        below is elevated.

        System-parameter reads are `base.group_system` in Odoo 19
        (`ir_config_parameter.get_param` calls `check_access('read')`, and
        base grants that model to system administrators only). Readiness runs
        as the INVOKING connector administrator, who is not necessarily an
        Odoo system administrator -- so without this the check raised
        `AccessError` and took the whole readiness run down with it.

        That was reachable in production before S1 existed:
        `action_reconnect` runs `run_for_store` as the connector administrator
        who clicked it. The guided setup's readiness step reaches it too, and
        found it.

        Narrow, read-only, one named parameter, and isolated in its own helper
        rather than inlined -- the same shape and the same reason as
        `_drain_cron_active_state`, whose AST guard forbids `.sudo()` inside
        any `_check_*` method.
        """
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')

    @api.model
    def _check_web_base_url(self, store):
        """Reads `ir.config_parameter` only -- no external network call."""
        code = 'web_base_url'
        base_url = self._web_base_url()
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
        """Capability-aware webhook-HMAC readiness (D-R1-1..5, D-R1-3).

        The accepted MVP trigger architecture is manual/scheduled pull
        synchronization; webhook intake is a later (W1) module. Until it
        installs, HMAC verification is not applicable and passes -- the
        W1 packet owns replacing this check via an `_inherit` override
        with the real HMAC-configuration + subscription-state
        verification. No webhook model, subscription, secret, or
        configuration is implemented or read here (read-only, no Shopify
        call, no secret).
        """
        return self._check_result(
            'webhook_hmac', self.ESSENTIAL, self.RESULT_PASS,
            'Not applicable — webhook intake is not installed; '
            'scheduled/manual sync is the active trigger mechanism.',
            not_applicable=True,
        )

    @api.model
    def _check_mapped_location(self, store):
        """Capability-aware mapped-Location readiness (D-R1-2).

        Reads only the same core settings flag
        `_check_domain_flag_enablement` already reads -- no
        inventory-domain model dependency, no inventory-model access.
        When the store's inventory domain is not enabled, mapped-Location
        verification is not applicable and passes. When it IS enabled but
        no inventory module has overridden this check with the real
        verification, it stays fail-closed (`not_proven`): an
        inventory-enabled store without the inventory module must not
        activate. Task 013's inventory module replaces the evaluation via
        an `_inherit` override.
        """
        code = 'mapped_location'
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.inventory_domain_enabled:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Not applicable — the inventory domain is not enabled for '
                'this store.',
                not_applicable=True,
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
            'Mapped-Location verification requires the inventory module, '
            'which is not installed -- registered as a pending check slot '
            'until the inventory domain provides it.',
        )

    @api.model
    def _check_cron_queue_health(self, store):
        """Real, capability-aware scheduler/queue health (D-R1-1).

        Passes only when the merged drain cron
        (`ir_cron_shopify_connector_job_dispatch_drain`) exists and is
        active, and no queued job for this store has stalled. Reads local
        state only: the cron record through the one narrow, named
        read-only `sudo()` elevation (`_drain_cron_active_state` --
        connector groups hold no `ir.cron` ACL, so a non-elevated read
        raises AccessError) and this store's own jobs. No Shopify call,
        no secret. It does NOT require the Area-6 domain scan crons --
        they do not exist yet; a future Area-6 `_inherit` may extend this
        check to also verify enabled domains' scan crons.

        Stall discriminator (exact): `state='queued' AND NOT started_at`
        older than `READINESS_QUEUE_STALL_MINUTES`. `retry_count` counts
        scheduled retries, not attempts, and is deliberately not used. A
        job re-queued with a historical `started_at` is deliberately NOT
        flagged here (its `started_at` is set) -- such stalls surface
        through the Sync Center age columns, not readiness.
        """
        code = 'cron_queue_health'
        cron_active = self._drain_cron_active_state()
        if cron_active is None:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'The job-dispatch drain cron is missing.',
            )
        if not cron_active:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'The job-dispatch drain cron is inactive.',
            )
        stall_cutoff = fields.Datetime.subtract(
            fields.Datetime.now(), minutes=self.READINESS_QUEUE_STALL_MINUTES,
        )
        stalled_count = self.env['shopify.connector.job'].search_count([
            ('store_id', '=', store.id),
            ('state', '=', 'queued'),
            ('started_at', '=', False),
            ('create_date', '<', stall_cutoff),
        ])
        if stalled_count:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                '%d queued job(s) have stalled longer than %d minutes '
                'without starting.' % (
                    stalled_count, self.READINESS_QUEUE_STALL_MINUTES,
                ),
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'The drain cron is active and no queued job has stalled.',
        )

    @api.model
    def _drain_cron_active_state(self):
        """The single new sanctioned read-only `sudo()` site of Task
        CORE-R1 (D-R1-1) -- read the merged drain cron's `active` flag.

        Connector groups hold no `ir.cron` ACL (base grants it to
        `base.group_erp_manager` only), and readiness runs as the
        invoking (connector-admin) user, so this record read raises
        `AccessError` without elevation. The elevation is narrow (one
        record, one field, read-only) and is deliberately isolated in
        this own named helper rather than inlined into
        `_check_cron_queue_health`, so the pre-existing
        `test_readiness_check.py::test_source_level_no_check_method_
        mutates_state` AST guard -- which forbids `.sudo()` inside any
        `_check_*` method -- stays green. This is the third sanctioned
        `.sudo()` site in `shopify_connector_core/models`; the two source
        guards in `test_job_log_system_append.py` /
        `test_credential_service.py` enforce the exact three-site
        inventory (`shopify_connector_job_log.py`,
        `shopify_connector_readiness_check.py`,
        `shopify_connector_store_credential.py`), updated under CORE-R1
        gate amendment `4948368039`; any fourth site still fails both
        guards.

        Returns None when the drain cron record does not exist; otherwise
        the boolean value of its `active` field.
        """
        cron = self.env.ref(
            'shopify_connector_core.'
            'ir_cron_shopify_connector_job_dispatch_drain',
            raise_if_not_found=False,
        )
        if not cron:
            return None
        return bool(cron.sudo().active)

    @api.model
    def _check_domain_flag_enablement(self, store):
        """Reads `shopify.connector.store.settings` only -- no write, no
        domain-module dependency.

        Reports `pass` only when at least one of `self._accepted_domain_
        flags()` is True on the store's settings record; any other settings
        field (e.g. `notification_default_enabled`) is not a sync-domain
        flag and never contributes to this check. An unrecognized flag name
        -- one not actually present on `settings` -- fails closed to "not
        enabled" rather than raising, so a stale or misconfigured
        registration can never silently enable anything.

        Correction B (independent review, Defects #2/#3). WARNING tier, not
        ESSENTIAL. A deliberate zero-domain "connect-only" configuration is
        an explicitly accepted setup outcome (`docs/02-product/ui-ux-final-
        design-spec.md`, S1 step 7's own on-screen copy) -- the operator has
        already been shown, on the step-11 review screen, exactly which
        domains (zero or more) are about to be activated, so this check
        exists to surface an informational signal, not to gate activation a
        second time on a choice the operator already reviewed. Downgrading
        it to WARNING is what lets `activate()` complete for a genuine
        connect-only store and for a store enabling only a
        module-registered domain such as Product Export's
        `product_export_domain_enabled` -- both previously an
        unconditional essential failure ("No sync domain is enabled") no
        operator could ever clear. The PASS/NOT_PROVEN/FAIL result
        computation itself is unchanged; only the tier, and the flag set
        it is computed over, are corrected.
        """
        code = 'domain_flag_enablement'
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings:
            return self._check_result(
                code, self.WARNING, self.RESULT_NOT_PROVEN,
                'No store-settings record exists yet -- domain enablement '
                'has not been configured.',
            )
        if any(
            getattr(settings, flag, False)
            for flag in self._accepted_domain_flags()
        ):
            return self._check_result(
                code, self.WARNING, self.RESULT_PASS,
                'At least one sync domain is enabled.',
            )
        return self._check_result(
            code, self.WARNING, self.RESULT_FAIL,
            'No sync features are enabled. This store will connect without '
            'syncing. You can enable features later from Sync Rules.',
        )
