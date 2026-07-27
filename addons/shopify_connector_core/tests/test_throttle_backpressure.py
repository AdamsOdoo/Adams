"""TD-014: PERF-1 backpressure driven by Shopify's real throttle signal.

The defect
----------
PERF-1 shipped a complete backpressure lever and no way to pull it.

`_backpressured_store_ids` drops any store whose `api_health_state` is
`throttled` or `degraded` from the drain's claim candidate search, and
that machinery works. But **no production code path had ever written
`'throttled'`** — in any commit. The one place that could have known,
`_parse_throttle_status`, extracted `currentlyAvailable`,
`maximumAvailable` and `restoreRate` from every single Shopify response
and handed them to callers that dropped them on the floor.

So the connector measured its own rate head-room continuously, published
it in its return values, and never once acted on it. Under sustained load
it would push straight into Shopify's 429s exactly as if PERF-1 had never
been written.

The correction
--------------
The signal is folded into durable store state at the client's single
response choke point, and head-room drives the existing lever. No new
mechanism was invented to sit beside `api_health_state`: the accepted
D-PERF1-4 design is used as specified, and what was missing was its
input.

Two properties do the real work and both have tests here:

**Hysteresis.** Deferring below 20% and recovering only above 50% stops
the state flapping across a single line and rewriting the store row on
every call.

**Projection.** A deferred store issues no calls, so it receives no new
`throttleStatus` — an observation-only design would defer it forever on
the strength of one bad moment. Shopify's bucket refills continuously at
`restoreRate` points per second
(https://shopify.dev/docs/api/usage/limits, read 2026-07-27), so
head-room is recomputed from the last observation and the clock. No
Shopify call is involved, which is what makes it both starvation-proof
and testable.

Nothing here contacts Shopify. `_record_throttle_status` takes a plain
dict; the numbers are the same three the parser already returned.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models import (
    shopify_connector_job_dispatch as dispatch_module,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_store import (
    THROTTLE_DEFER_RATIO,
    THROTTLE_RECOVER_RATIO,
)


class FakeThrottleResponse:
    """A `requests.Response` stand-in for `_normalize_response`.

    Deliberately minimal: `_normalize_response` reads `json()` and, on the
    error paths only, the status/text. A richer fake would let a test pass
    for reasons the production path does not have.
    """

    status_code = 200

    def __init__(self, body):
        self._body = body
        self.headers = {}
        self.text = ''

    def json(self):
        return self._body


@tagged('post_install', '-at_install')
class TestThrottleBackpressure(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env['shopify.connector.job']
        cls.Store = cls.env['shopify.connector.store']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Param = cls.env['ir.config_parameter']
        cls.store = cls.Store.create({
            'name': 'TD-014 primary store',
            'shop_domain': 'td014-primary.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.other_store = cls.Store.create({
            'name': 'TD-014 second store',
            'shop_domain': 'td014-second.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
        })

    def _throttle(self, available, maximum=2000.0, restore_rate=100.0):
        """A `throttleStatus` payload in Shopify's own field names."""
        return {
            'currentlyAvailable': available,
            'maximumAvailable': maximum,
            'restoreRate': restore_rate,
        }

    def _queue(self, count, store=None):
        store = store or self.store
        return self.Job.create([{
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
        } for _index in range(count)])

    # ------------------------------------------------------------------
    # 1. The signal becomes durable state
    # ------------------------------------------------------------------

    def test_a_response_records_the_three_official_values(self):
        """Requirements 1 and 2: consume the real signal, store the minimum."""
        self.store._record_throttle_status(self._throttle(1800.0))
        self.store.invalidate_recordset()
        self.assertEqual(self.store.api_throttle_available, 1800.0)
        self.assertEqual(self.store.api_throttle_maximum, 2000.0)
        self.assertEqual(self.store.api_throttle_restore_rate, 100.0)
        self.assertTrue(self.store.api_throttle_observed_at)

    def test_nothing_but_numbers_is_persisted(self):
        """Requirement 11: no payload, credential or header may leak.

        The recorder is handed the parsed status only, and the fields it
        writes are three floats and a timestamp. This asserts the field
        set rather than trusting the call site, so a future addition of a
        richer field is a test failure rather than a quiet disclosure.
        """
        throttle_fields = {
            name for name in self.Store._fields
            if name.startswith('api_throttle_')
        }
        self.assertEqual(
            throttle_fields,
            {'api_throttle_available', 'api_throttle_maximum',
             'api_throttle_restore_rate', 'api_throttle_observed_at'},
        )
        for name in throttle_fields - {'api_throttle_observed_at'}:
            self.assertEqual(self.Store._fields[name].type, 'float')

    # ------------------------------------------------------------------
    # 2. Head-room drives the accepted lever
    # ------------------------------------------------------------------

    def test_low_headroom_defers_the_store(self):
        """Requirements 3, 4 and 10."""
        self.store._record_throttle_status(self._throttle(100.0))
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.api_health_state, 'throttled',
            'Head-room of 5%% is below the %.0f%% defer threshold.'
            % (THROTTLE_DEFER_RATIO * 100),
        )
        self.assertIn('head-room', self.store.api_health_reason)

    def test_healthy_headroom_leaves_the_store_alone(self):
        """Requirement 12: normal throughput is preserved."""
        self.store._record_throttle_status(self._throttle(1900.0))
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.api_health_state, 'throttled')

    def test_a_deferred_store_is_dropped_from_the_drain(self):
        """Requirement 4, end to end through the production lever.

        This is the assertion that proves the correction reaches
        production admission rather than merely writing a field.
        """
        self._queue(3)
        self._queue(2, store=self.other_store)
        self.store._record_throttle_status(self._throttle(50.0))
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '50',
        )
        self.assertEqual(
            self.Dispatch.run_drain(), 2,
            'Only the healthy store\'s jobs may run while the other has no '
            'rate head-room left.',
        )

    def test_one_stores_exhaustion_never_defers_another(self):
        """Requirement 9: state is isolated per store."""
        self.store._record_throttle_status(self._throttle(10.0))
        self.other_store._record_throttle_status(self._throttle(1900.0))
        self.store.invalidate_recordset()
        self.other_store.invalidate_recordset()
        self.assertEqual(self.store.api_health_state, 'throttled')
        self.assertNotEqual(self.other_store.api_health_state, 'throttled')
        self.assertEqual(
            self.Dispatch._backpressured_store_ids(), (self.store.id,),
        )

    # ------------------------------------------------------------------
    # 2b. Same-pass backpressure: pressure THIS pass observed binds THIS
    #     pass. The correction to the first TD-014 implementation.
    # ------------------------------------------------------------------

    def _low_headroom_body(self, available):
        """A real-shaped GraphQL body carrying `extensions.cost`.

        The three field names are Shopify's own
        (https://shopify.dev/docs/api/usage/limits, read 2026-07-27) and
        this goes through `_normalize_response` -- the production choke
        point -- not through `_record_throttle_status` directly. That is
        the whole point of these two tests: the previous TD-014 regressions
        proved the *lever* worked by pulling it themselves.
        """
        return {
            'data': {'shop': {'myshopifyDomain': 'irrelevant'}},
            'extensions': {'cost': {'throttleStatus': {
                'maximumAvailable': 2000.0,
                'currentlyAvailable': available,
                'restoreRate': 100.0,
            }}},
        }

    def _drain_with_throttle_on(self, throttled_store, available=40.0):
        """Run ONE `run_drain()` in which the first job for `throttled_store`
        comes back reporting near-exhausted head-room.

        The handler is replaced -- not the transport -- because
        `core_dispatch_selftest` deliberately issues no Shopify call at all,
        so there is no request for a patched `_send` to answer. What is
        under test is not the transport: it is whether state written
        DURING a pass changes the claims still to come in that pass. So the
        handler feeds a real-shaped response through the real
        `_normalize_response`, which is the only production route from a
        response to `api_health_state`.
        """
        Dispatch = type(self.Dispatch)
        Client = type(self.env['shopify.connector.api.client'])
        original = Dispatch._handle_core_dispatch_selftest
        seen = []

        def handler(dispatch_self, job):
            seen.append(job.store_id.id)
            if job.store_id.id == throttled_store.id and len(seen) == 1:
                response = FakeThrottleResponse(
                    self._low_headroom_body(available)
                )
                dispatch_self.env[
                    'shopify.connector.api.client'
                ]._normalize_response(job.store_id, response)
            return original(dispatch_self, job)

        with patch.object(Client, '_assert_served_api_version',
                          lambda _self, _response: '2026-07'), \
                patch.object(Dispatch, '_handle_core_dispatch_selftest',
                             handler):
            processed = self.Dispatch.run_drain()
        return processed, seen

    def test_pressure_observed_mid_pass_defers_that_store_in_the_same_pass(self):
        """The TD-014 correction, at the production seam.

        The first implementation computed the deferred set ONCE, before the
        claim loop. So a store could report 2% head-room on the first job
        of a pass and have four more of its jobs claimed by the same pass
        -- the exact burst backpressure exists to prevent, and a defect no
        amount of testing the lever in isolation would surface.

        No forced 429 anywhere: the deferral comes from proactive
        `throttleStatus` head-room, which is what the official
        documentation says applications should use.
        """
        self._queue(4)
        self._queue(1, store=self.other_store)
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '50',
        )
        processed, seen = self._drain_with_throttle_on(self.store)

        self.assertEqual(
            seen[0], self.store.id,
            'The pressure-reporting store must go first, or this proves '
            'nothing about what follows it.',
        )
        self.assertEqual(
            seen.count(self.store.id), 1,
            'Store A reported near-zero head-room on its FIRST job of this '
            'pass. No further job for store A may be claimed by the SAME '
            'pass -- this is the assertion the original TD-014 '
            'implementation could not pass.',
        )
        self.assertIn(
            self.other_store.id, seen,
            'Per-store isolation: one store losing head-room must not stop '
            'an unrelated store\'s work in the same pass.',
        )
        self.assertEqual(processed, 2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.api_health_state, 'throttled')

    def test_the_deferred_set_can_only_grow_during_a_pass(self):
        """Once deferred, deferred for the rest of the pass.

        The union is not an implementation detail. Re-reading the set
        without accumulating would let the mid-pass recovery projection
        lift a deferral the same pass had just applied, and the pass would
        oscillate against a bucket it is supposed to be leaving alone.
        Recovery is a NEXT-pass event, and the read the loop uses is the
        one that does not project.
        """
        self.store._record_throttle_status(self._throttle(100.0))
        self.store.invalidate_recordset()
        # Aged far enough that the projection WOULD clear the deferral.
        self.store.sudo().write({
            'api_throttle_observed_at': fields.Datetime.subtract(
                fields.Datetime.now(), seconds=60,
            ),
        })
        self.store.invalidate_recordset()
        self.assertIn(
            self.store.id, self.Dispatch._backpressured_store_ids_now(),
            'The mid-pass read must report the store\'s CURRENT durable '
            'state without projecting recovery onto it.',
        )
        self.assertNotIn(
            self.store.id, self.Dispatch._backpressured_store_ids(),
            'The pass-boundary read still applies the documented restore-'
            'rate projection, so recovery keeps working across passes.',
        )

    def test_a_later_pass_admits_the_recovered_store_again(self):
        """Requirement: deferral is temporary, and recovery needs no 429."""
        self._queue(2)
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '50',
        )
        processed, seen = self._drain_with_throttle_on(self.store)
        self.assertEqual(processed, 1, 'The pass self-limited to one job.')

        # Time passes. `restoreRate` refills the bucket; nothing is asked
        # of Shopify to find that out.
        self.store.sudo().write({
            'api_throttle_observed_at': fields.Datetime.subtract(
                fields.Datetime.now(), seconds=60,
            ),
        })
        self.store.invalidate_recordset()
        self.assertEqual(
            self.Dispatch.run_drain(), 1,
            'The remaining job must run on a later pass once the projected '
            'refill clears the accepted recovery threshold.',
        )

    # ------------------------------------------------------------------
    # 3. Recovery, and the starvation it prevents
    # ------------------------------------------------------------------

    def test_headroom_is_projected_forward_from_the_restore_rate(self):
        """Requirement 6, and the arithmetic it rests on.

        100 points/second for 10 seconds is 1000 more points. Asserted
        exactly, because an approximate refill model would make the
        recovery threshold unpredictable.
        """
        self.store._record_throttle_status(
            self._throttle(200.0, maximum=2000.0, restore_rate=100.0),
        )
        self.store.invalidate_recordset()
        later = self.store.api_throttle_observed_at + timedelta(seconds=10)
        self.assertEqual(
            self.store._projected_throttle_available(now=later), 1200.0,
        )
        self.assertEqual(
            self.store._throttle_headroom_ratio(now=later), 0.6,
        )

    def test_the_projection_never_exceeds_the_bucket(self):
        self.store._record_throttle_status(self._throttle(1000.0))
        self.store.invalidate_recordset()
        far_later = (
            self.store.api_throttle_observed_at + timedelta(hours=5)
        )
        self.assertEqual(
            self.store._projected_throttle_available(now=far_later), 2000.0,
        )

    def test_a_deferred_store_recovers_without_any_shopify_call(self):
        """Requirement 7: no starvation. The core anti-deadlock property.

        A deferred store issues no calls, so it can never report fresh
        head-room. If recovery required an observation, the first
        deferral would be permanent — a worse outage than the throttling
        it was avoiding.
        """
        self.store._record_throttle_status(self._throttle(100.0))
        self.store.invalidate_recordset()
        self.assertEqual(self.store.api_health_state, 'throttled')

        recovered_at = (
            self.store.api_throttle_observed_at + timedelta(seconds=15)
        )
        self.store._apply_throttle_backpressure(now=recovered_at)
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.api_health_state, 'normal',
            'The bucket refilled past the recovery threshold; the store '
            'must be admitted again with no Shopify contact.',
        )
        self.assertFalse(self.store.api_health_reason)

    def test_the_drain_pass_itself_lifts_an_expired_deferral(self):
        """Recovery is reached from production, not only from a helper."""
        self.store._record_throttle_status(self._throttle(100.0))
        self.store.invalidate_recordset()
        self.assertIn(self.store.id, self.Dispatch._backpressured_store_ids())

        # Age the observation so the projected refill clears the threshold.
        self.store.sudo().write({
            'api_throttle_observed_at': fields.Datetime.subtract(
                fields.Datetime.now(), seconds=60,
            ),
        })
        self.store.invalidate_recordset()
        self.assertNotIn(
            self.store.id, self.Dispatch._backpressured_store_ids(),
            'The drain pass must re-evaluate rate deferrals against the '
            'clock, or a deferred store never runs again.',
        )

    def test_recovery_needs_more_than_the_defer_threshold(self):
        """Hysteresis: the two thresholds are not the same line."""
        self.assertGreater(THROTTLE_RECOVER_RATIO, THROTTLE_DEFER_RATIO)
        self.store._record_throttle_status(self._throttle(100.0))
        self.store.invalidate_recordset()
        # Just above the DEFER line but below the RECOVER line: still held.
        between = (THROTTLE_DEFER_RATIO + THROTTLE_RECOVER_RATIO) / 2
        self.store.sudo().write({
            'api_throttle_available': 2000.0 * between,
            'api_throttle_restore_rate': 0.0,
            'api_throttle_observed_at': fields.Datetime.now(),
        })
        self.store.invalidate_recordset()
        self.store._apply_throttle_backpressure()
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.api_health_state, 'throttled',
            'Recovering at the defer threshold would flap the state and '
            'resume work before the bucket had actually refilled.',
        )

    # ------------------------------------------------------------------
    # 4. Fail-safe on missing or malformed data
    # ------------------------------------------------------------------

    def test_absent_or_malformed_data_changes_nothing(self):
        """Requirement 12: no evidence means no backpressure.

        Shopify omits `extensions.cost` on some responses. Reading that
        as zero head-room would defer a perfectly healthy store.
        """
        cases = [
            None,
            {},
            'not-a-dict',
            {'currentlyAvailable': None, 'maximumAvailable': 2000.0,
             'restoreRate': 100.0},
            {'currentlyAvailable': 'lots', 'maximumAvailable': 2000.0,
             'restoreRate': 100.0},
            {'currentlyAvailable': 100.0, 'maximumAvailable': 0.0,
             'restoreRate': 100.0},
            {'currentlyAvailable': -5.0, 'maximumAvailable': 2000.0,
             'restoreRate': 100.0},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                store = self.Store.create({
                    'name': 'TD-014 malformed %s' % uuid.uuid4().hex[:6],
                    'shop_domain': '%s.myshopify.com' % uuid.uuid4().hex[:10],
                    'api_version': '2026-07',
                    'state': 'connected',
                })
                self.assertFalse(store._record_throttle_status(payload))
                store.invalidate_recordset()
                self.assertNotEqual(store.api_health_state, 'throttled')
                self.assertFalse(store.api_throttle_observed_at)

    def test_a_store_with_no_observation_has_no_headroom_opinion(self):
        self.assertIsNone(self.store._projected_throttle_available())
        self.assertIsNone(self.store._throttle_headroom_ratio())
        self.assertFalse(self.store._apply_throttle_backpressure())

    def test_a_degraded_store_is_never_silently_cleared(self):
        """`degraded` means something else and is not this lever's to reset."""
        self.store.sudo().write({
            'api_health_state': 'degraded',
            'api_health_reason': 'Set by the store lifecycle.',
        })
        self.store._record_throttle_status(self._throttle(1900.0))
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.api_health_state, 'degraded',
            'Healthy rate head-room says nothing about a degradation this '
            'lever did not cause.',
        )

    # ------------------------------------------------------------------
    # 5. Structural
    # ------------------------------------------------------------------

    def test_the_client_records_every_response_it_normalizes(self):
        """The signal must reach state from the one shared choke point.

        `_normalize_response` is where both `execute` and
        `execute_business` land, for every domain. Parsing the status
        anywhere else and forgetting to record it is the original defect.
        """
        import inspect

        from odoo.addons.shopify_connector_core.models import (
            shopify_connector_api_client as client_module,
        )

        source = inspect.getsource(
            client_module.ShopifyConnectorApiClient._normalize_response
        )
        self.assertIn('_record_throttle_status', source)

    def test_backpressure_can_only_ever_defer(self):
        """No path here raises a rate, shortens a delay or admits work."""
        import inspect

        from odoo.addons.shopify_connector_core.models import (
            shopify_connector_store as store_module,
        )

        source = inspect.getsource(
            store_module.ShopifyConnectorStore._apply_throttle_backpressure
        )
        written_states = {
            value for value in ('throttled', 'normal', 'degraded')
            if "'%s'" % value in source
        }
        self.assertEqual(
            written_states, {'throttled', 'normal'},
            'This lever may only defer a store or release it again; it '
            'must never touch any other health state.',
        )
