"""Installed W3 inventory webhook contracts; no Shopify network calls."""

import hashlib
import importlib.util
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

from ..models.constants import (
    INVENTORY_OBSERVATION_JOB_TYPE,
    INVENTORY_WEBHOOK_INCLUDE_FIELDS,
    INVENTORY_WEBHOOK_HANDLER,
    INVENTORY_WEBHOOK_TOPIC,
    fair_rotation,
)
from ..models.shopify_connector_inventory_observation import (
    _CRON_CONTEXT_SENTINEL,
    _parse_inventory_level_gid,
    _parse_remote_datetime,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    RETRY_MAX_ATTEMPTS,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_inventory.models.shopify_connector_inventory_service import (
    ERROR_CLASS_DATA_SHAPE,
    ERROR_CLASS_TEMPORARY,
)
from odoo.addons.shopify_connector_core.tests.canonical_settings_classification import (
    INTERNAL_PROTECTED,
    assert_module_classification,
)

MODULE = 'shopify_connector_inventory_webhook'
WEBHOOK_SETTINGS_CLASSIFICATION = {
    'inventory_observation_scheduled_at': (
        INTERNAL_PROTECTED,
        'Bounded scheduler checkpoint; written by the observer cron, never a '
        'merchant configuration decision.',
    ),
}


@tagged('post_install', '-at_install')
class TestShopifyConnectorInventoryWebhookW3(TransactionCase):
    """Exercise W3 production seams without issuing a Shopify request."""

    def _store(self, suffix):
        store = self.env['shopify.connector.store'].create({
            'name': 'W3 inventory webhook %s' % suffix,
            'shop_domain': 'w3-inventory-%s.myshopify.com' % suffix,
            'api_version': SHOPIFY_API_VERSION,
            'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id,
            'inventory_domain_enabled': True,
            'inventory_scheduled_sync_enabled': True,
        })
        return store

    def test_webhook_settings_fields_have_canonical_classification(self):
        assert_module_classification(
            self, MODULE, WEBHOOK_SETTINGS_CLASSIFICATION,
        )

    def test_webhook_registry_contract_exports_handler_constant(self):
        """The registry's imported handler name must be an exported contract."""
        self.assertEqual(INVENTORY_WEBHOOK_HANDLER, INVENTORY_OBSERVATION_JOB_TYPE)

    def test_observation_fields_use_protected_binding_extension_seam(self):
        binding = self.env['shopify.connector.inventory.level.binding']
        observation_fields = frozenset((
            'last_observed_updated_at',
            'last_observed_available',
            'last_observation_delivery_id',
            'last_observation_event_id',
            'last_observation_state',
            'last_observed_at',
        ))
        self.assertTrue(
            observation_fields <= binding._additional_protected_binding_fields()
        )
        self.assertTrue(
            observation_fields <= binding._protected_binding_fields()
        )

    def _delivery(self, store, suffix, level_gid, source_updated_at):
        digest = hashlib.sha256(
            ('w3-inventory-body-%s' % suffix).encode('utf-8'),
        ).hexdigest()
        return self.env[
            'shopify.connector.webhook.delivery'
        ]._ingest(
            store,
            delivery_id='w3-inventory-delivery-%s' % suffix,
            event_id='w3-inventory-event-%s' % suffix,
            topic=INVENTORY_WEBHOOK_TOPIC,
            shop_domain=store.shop_domain,
            api_version=SHOPIFY_API_VERSION,
            triggered_at=fields.Datetime.now(),
            source_updated_at=source_updated_at,
            payload_digest=digest,
            payload_size=192,
            # This is the reduced payload shape admitted by the active
            # includeFields contract. The child later reads Shopify by GID.
            payload_identity={
                'admin_graphql_api_id': level_gid,
                'inventory_item_id': '123456789',
                'location_id': '987654321',
                'available': 7,
                'updated_at': fields.Datetime.to_string(source_updated_at),
            },
        )[0]

    def test_registry_activates_only_inventory_update_with_full_filter(self):
        registry = self.env['shopify.connector.webhook.registry']
        active = set(registry.allowed_topics())
        self.assertIn(INVENTORY_WEBHOOK_TOPIC, active)
        inventory_topics = {
            topic for topic in active if topic.startswith('inventory')
        }
        self.assertEqual(inventory_topics, {INVENTORY_WEBHOOK_TOPIC})
        self.assertEqual(
            registry.topic_spec(INVENTORY_WEBHOOK_TOPIC)['handler'],
            INVENTORY_OBSERVATION_JOB_TYPE,
        )
        self.assertEqual(
            registry.topic_spec(INVENTORY_WEBHOOK_TOPIC)['include_fields'],
            INVENTORY_WEBHOOK_INCLUDE_FIELDS,
        )

    def test_registry_extension_is_add_only_and_fails_closed_on_collision(self):
        registry = self.env['shopify.connector.webhook.registry']
        with self.assertRaises(ValidationError):
            registry._extend_inventory_topic_registry({
                INVENTORY_WEBHOOK_TOPIC: {'enum': 'OTHER_HANDLER'},
            })
        with self.assertRaises(ValidationError):
            registry._extend_inventory_topic_handlers({
                INVENTORY_WEBHOOK_TOPIC: object(),
            })

    def test_production_delivery_entry_coalesces_and_later_stamp_is_new_work(self):
        """Repeated filtered deliveries never hit a duplicate SQL insert."""
        store = self._store('admission')
        level_gid = 'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        first_at = fields.Datetime.to_datetime('2026-08-22 08:00:00')
        first = self._delivery(store, 'first', level_gid, first_at)
        with self.assertNoLogs('odoo.sql_db', level='ERROR'):
            first._process_queued()
            second = self._delivery(store, 'second', level_gid, first_at)
            second._process_queued()
        Job = self.env['shopify.connector.job'].sudo()
        children = Job.search([
            ('store_id', '=', store.id),
            ('job_type', '=', INVENTORY_OBSERVATION_JOB_TYPE),
            ('shopify_target_gid', '=', level_gid),
        ], order='id asc')
        self.assertEqual(len(children), 1)
        self.assertIn('coalesced', second.processing_note)

        # Once the first child is terminal, a later updated_at from the same
        # filtered webhook shape receives a distinct generation-scoped key.
        children._transition_failed_final(
            'data_shape_schema_mismatch',
            'W3 later-update admission fixture; child was not read.',
        )
        later_at = fields.Datetime.add(first_at, seconds=1)
        later = self._delivery(store, 'later', level_gid, later_at)
        with self.assertNoLogs('odoo.sql_db', level='ERROR'):
            later._process_queued()
        children = Job.search([
            ('store_id', '=', store.id),
            ('job_type', '=', INVENTORY_OBSERVATION_JOB_TYPE),
            ('shopify_target_gid', '=', level_gid),
        ], order='id asc')
        self.assertEqual(len(children), 2)
        self.assertNotEqual(children[0].payload_hash, children[1].payload_hash)

    def test_production_delivery_generation_fence_denies_stale_child_admission(self):
        store = self._store('stale-generation')
        level_gid = 'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        delivery = self._delivery(
            store, 'stale-generation', level_gid,
            fields.Datetime.to_datetime('2026-08-22 08:00:00'),
        )
        store.sudo().write({
            'connection_generation': int(store.connection_generation or 0) + 1,
        })
        delivery._process_queued()
        self.assertEqual(delivery.state, 'manual_review')
        self.assertFalse(self.env['shopify.connector.job'].sudo().search([
            ('job_type', '=', INVENTORY_OBSERVATION_JOB_TYPE),
            ('shopify_target_gid', '=', level_gid),
        ]))

    def test_exact_inventory_level_identity_and_read_dispatch(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        valid = 'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        self.assertEqual(service._valid_level_gid(valid), valid)
        self.assertFalse(service._valid_level_gid('7001'))
        self.assertFalse(
            service._valid_level_gid('gid://shopify/InventoryLevel/7001/child'),
        )
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertIn(INVENTORY_OBSERVATION_JOB_TYPE, dispatch._get_handlers())
        self.assertIn(
            INVENTORY_OBSERVATION_JOB_TYPE,
            dispatch._get_replay_policies(),
        )

    def test_remote_datetime_requires_rfc3339_timezone(self):
        self.assertEqual(
            _parse_remote_datetime('2026-08-22T08:00:00Z'),
            fields.Datetime.to_datetime('2026-08-22 08:00:00'),
        )
        self.assertEqual(
            _parse_remote_datetime('2026-08-22T12:00:00+04:00'),
            fields.Datetime.to_datetime('2026-08-22 08:00:00'),
        )
        self.assertEqual(
            _parse_remote_datetime('2026-08-22T08:00:00.123456789Z'),
            datetime(2026, 8, 22, 8, 0, 0, 123456),
        )
        for invalid in (
            '2026-08-22 08:00:00',
            '2026-08-22T08:00:00',
            '2026-08-22T08:00:00.1234567890Z',
            '2026-08-22T08:00:00+0000',
            ' 2026-08-22T08:00:00Z',
            '2026-08-22T08:00:00Zjunk',
        ):
            self.assertFalse(_parse_remote_datetime(invalid), invalid)

    def test_inventory_level_gid_is_exact_composite_and_cross_checked(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        level = 'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        self.assertEqual(
            _parse_inventory_level_gid(level),
            {'level_id': '7001', 'inventory_item_id': '8001'},
        )
        self.assertTrue(service._level_gid_matches_authoritative_identity(
            level,
            'gid://shopify/InventoryItem/8001',
            'gid://shopify/Location/7001',
        ))
        self.assertFalse(service._level_gid_matches_authoritative_identity(
            level,
            'gid://shopify/InventoryItem/8002',
            'gid://shopify/Location/7001',
        ))
        self.assertFalse(service._level_gid_matches_authoritative_identity(
            level,
            'gid://shopify/InventoryItem/8001',
            'gid://shopify/Location/9001',
        ))
        for invalid in (
            'gid://shopify/InventoryLevel/7001',
            'gid://shopify/InventoryLevel/7001?inventory_item_id=8001&junk=1',
            'gid://shopify/InventoryLevel/7001?inventory_item_id=8001#x',
            'gid://shopify/InventoryLevel/7001/child?inventory_item_id=8001',
            'gid://shopify/InventoryLevel/7001?inventory_item_id=8001/',
            '7001',
        ):
            self.assertFalse(service._valid_level_gid(invalid), invalid)

    def test_authoritative_graphql_read_uses_quantity_timestamp_only(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        store = SimpleNamespace(shop_domain='w3-read.myshopify.com')
        job = SimpleNamespace(id=991)
        level_gid = (
            'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        )
        result = {
            'data': {
                'shop': {'myshopifyDomain': store.shop_domain},
                'inventoryLevel': {
                    'id': level_gid,
                    # A level timestamp must never be used as a fallback.
                    'updatedAt': '2026-08-22T08:00:00Z',
                    'item': {
                        'id': 'gid://shopify/InventoryItem/8001',
                        'tracked': True,
                    },
                    'location': {'id': 'gid://shopify/Location/7001'},
                    'quantities': [{
                        'name': 'available',
                        'quantity': 7,
                        'updatedAt': '2026-08-22T08:00:01Z',
                    }],
                },
            },
        }

        class ReadContext:
            def __enter__(self):
                return result

            def __exit__(self, *_args):
                return False

        client = self.env['shopify.connector.api.client']
        with patch.object(
            type(client), 'execute_business_read',
            return_value=ReadContext(),
        ) as execute:
            snapshot = service._read_inventory_level(job, store, level_gid)
        self.assertEqual(snapshot['source_updated_at'],
                         fields.Datetime.to_datetime('2026-08-22 08:00:01'))
        execute.assert_called_once()
        self.assertIn('inventoryLevel(id: $levelId) { id',
                      execute.call_args.args[2])
        self.assertIn(
            'quantities(names: ["available"]) { name quantity updatedAt }',
            execute.call_args.args[2],
        )
        self.assertNotIn('inventoryLevel(id: $levelId) { id updatedAt',
                         execute.call_args.args[2])

    def test_missing_or_naive_quantity_timestamp_never_uses_level_timestamp(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        store = SimpleNamespace(shop_domain='w3-read.myshopify.com')
        job = SimpleNamespace(id=992)
        level_gid = (
            'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        )

        class ReadContext:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self.payload

            def __exit__(self, *_args):
                return False

        client = self.env['shopify.connector.api.client']
        for timestamp in (None, '2026-08-22T08:00:01'):
            payload = {
                'data': {
                    'shop': {'myshopifyDomain': store.shop_domain},
                    'inventoryLevel': {
                        'id': level_gid,
                        'updatedAt': '2026-08-22T08:00:00Z',
                        'item': {
                            'id': 'gid://shopify/InventoryItem/8001',
                            'tracked': True,
                        },
                        'location': {'id': 'gid://shopify/Location/7001'},
                        'quantities': [{
                            'name': 'available',
                            'quantity': 7,
                            'updatedAt': timestamp,
                        }],
                    },
                },
            }
            with patch.object(
                type(client), 'execute_business_read',
                return_value=ReadContext(payload),
            ):
                with self.assertRaises(JobHandlerError) as raised:
                    service._read_inventory_level(job, store, level_gid)
            self.assertIn('quantity.updatedAt', raised.exception.reason)
            self.assertIn('not a valid substitute', raised.exception.reason)

    def test_production_handler_freezes_missing_authoritative_timestamp(self):
        """The guarded child records review evidence instead of local time."""
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]

        class FakeStore:
            shop_domain = 'w3-read.myshopify.com'

            def sudo(self):
                return self

        class FakeBinding:
            status = 'active'

            def __init__(self):
                self.writes = []

            def __len__(self):
                # The production handler requires an exact singleton binding
                # recordset before it performs any read or freeze action.
                return 1

            def try_lock_for_update(self):
                return self

            def invalidate_recordset(self):
                return None

            def sudo(self):
                return self

            def write(self, values):
                self.writes.append(dict(values))
                self.status = values.get('status', self.status)
                return True

        class FakeJob:
            job_source = 'scheduled_sync'
            trigger_origin_event_ref = 'scheduled_observation:1:run'
            shopify_target_gid = (
                'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
            )

            def __init__(self):
                self.store_id = FakeStore()
                self.transition = None

            def _transition_blocked_manual_review(self, *args):
                self.transition = args

        job = FakeJob()
        binding = FakeBinding()
        failure = JobHandlerError(
            ERROR_CLASS_DATA_SHAPE,
            'missing/malformed quantity.updatedAt; '
            'InventoryLevel.updatedAt is not a valid substitute.',
        )
        with patch.object(
            type(service), '_find_binding_by_level_gid', return_value=binding,
        ), patch.object(
            type(service), '_outbound_lineage', return_value=False,
        ), patch.object(
            type(service), '_read_inventory_level', side_effect=failure,
        ):
            service._handle_inventory_observation_sync(job)

        self.assertEqual(binding.status, 'review')
        self.assertEqual(binding.writes, [{'status': 'review'}])
        self.assertIsNotNone(job.transition)
        self.assertEqual(job.transition[0], ERROR_CLASS_DATA_SHAPE)

    def test_outbound_lineage_deferral_is_core_bounded_and_freezes_persistent(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]

        class FakeBinding:
            def __init__(self):
                self.writes = []

            def sudo(self):
                return self

            def write(self, values):
                self.writes.append(dict(values))
                return True

        class FakeJob:
            retry_count = 0
            started_at = fields.Datetime.now()

            def __init__(self):
                self.transition = None

            def _transition_blocked_manual_review(self, *args):
                self.transition = args

        dispatch = self.env['shopify.connector.job.dispatch']
        active_job = FakeJob()
        active_lineage = SimpleNamespace(id=501, state='retry_waiting')
        with patch.object(
            type(dispatch), '_schedule_retry_or_fail',
        ) as schedule:
            self.assertTrue(
                service._defer_for_outbound_lineage(
                    active_job, active_lineage,
                )
            )
        schedule.assert_called_once()
        self.assertEqual(
            schedule.call_args.kwargs['max_attempts'], RETRY_MAX_ATTEMPTS,
        )

        persistent_job = FakeJob()
        persistent_job.retry_count = RETRY_MAX_ATTEMPTS
        binding = FakeBinding()
        blocked_lineage = SimpleNamespace(id=502, state='blocked_manual_review')
        self.assertFalse(
            service._defer_for_outbound_lineage(
                persistent_job, blocked_lineage, binding=binding,
            )
        )
        self.assertEqual(binding.writes, [{'status': 'review'}])
        self.assertIsNotNone(persistent_job.transition)

    def test_scheduled_fallback_reference_is_not_treated_as_delivery_id(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        delivery = service._delivery_for_job(SimpleNamespace(
            job_source='scheduled_sync',
            trigger_origin_event_ref='scheduled_observation:1:run',
        ))
        self.assertFalse(delivery)

    def test_fair_rotation_is_bounded_and_wraps(self):
        self.assertEqual(
            fair_rotation([10, 11, 12, 13], 11, 2),
            (12, 13),
        )
        self.assertEqual(
            fair_rotation([10, 11, 12, 13], 13, 3),
            (10, 11, 12),
        )
        self.assertEqual(fair_rotation([10, 11], 0, 99), (10, 11))

    def test_scheduled_pass_rotates_stores_and_commits_only_admitted_pairs(self):
        """Exercise the production scheduler with bounded fake DB seams."""
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ].sudo()

        class FakeStore:
            def __init__(self, store_id):
                self.id = store_id
                self.inventory_observation_cursor_id = 0
                self.inventory_observation_scheduled_at = False
                self.writes = []

            def sudo(self):
                return self

            def write(self, values):
                self.writes.append(dict(values))
                for key, value in values.items():
                    setattr(self, key, value)
                return True

        stores = [FakeStore(10), FakeStore(20)]
        bindings = {
            10: [SimpleNamespace(id=101, shopify_gid='level-101'),
                 SimpleNamespace(id=102, shopify_gid='level-102')],
            20: [SimpleNamespace(id=201, shopify_gid='level-201')],
        }
        candidate_calls = []

        def candidates(store, _limit, cursor=0):
            candidate_calls.append(store.id)
            rows = [row for row in bindings[store.id] if row.id > cursor]
            return rows[:1]

        with patch.object(
            type(service), '_scheduled_observation_stores',
            return_value=stores,
        ), patch.object(
            type(service), '_observation_candidates', side_effect=candidates,
        ), patch.object(
            type(service), '_admit_fallback_pair',
            return_value=(True, 'coalesced'),
        ), patch.object(
            type(service), '_cron_has_time', return_value=True,
        ):
            result = service.run_scheduled_observation_fallback(limit=3)

        self.assertEqual(result, 0)
        self.assertEqual(candidate_calls, [10, 20, 10])
        self.assertEqual(stores[0].inventory_observation_cursor_id, 102)
        self.assertEqual(stores[1].inventory_observation_cursor_id, 201)
        self.assertTrue(all(store.writes for store in stores))

    def test_scheduled_budget_expiry_leaves_unattempted_pair_cursor_unchanged(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ].sudo()

        class FakeStore:
            id = 10
            inventory_observation_cursor_id = 0
            inventory_observation_scheduled_at = False

            def __init__(self):
                self.writes = []

            def sudo(self):
                return self

            def write(self, values):
                self.writes.append(dict(values))
                return True

        store = FakeStore()
        with patch.object(
            type(service), '_scheduled_observation_stores',
            return_value=[store],
        ), patch.object(
            type(service), '_cron_has_time',
            side_effect=(True, True, False),
        ), patch.object(
            type(service), '_observation_candidates',
            side_effect=AssertionError('budget must stop before pair query'),
        ), patch.object(
            type(service), '_admit_fallback_pair',
            side_effect=AssertionError('unattempted pair must not be admitted'),
        ):
            result = service.run_scheduled_observation_fallback(limit=1)

        self.assertEqual(result, 0)
        self.assertEqual(store.inventory_observation_cursor_id, 0)
        self.assertEqual(store.writes, [])

    def test_apply_snapshot_records_stale_duplicate_conflict_and_drift(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        inventory_service = self.env[
            'shopify.connector.inventory.service'
        ]
        stamp = fields.Datetime.to_datetime('2026-08-22 08:00:00')
        snapshot = {
            'source_updated_at': stamp,
            'available': 7,
            'inventory_level_gid': (
                'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
            ),
            'inventory_item_gid': 'gid://shopify/InventoryItem/8001',
            'location_gid': 'gid://shopify/Location/7001',
            'store_domain': 'w3-snapshot.myshopify.com',
        }

        class FakeBinding:
            status = 'active'
            last_pushed_at = False
            last_pushed_available = 0

            def __init__(self):
                self.writes = []

            def try_lock_for_update(self):
                return self

            def invalidate_recordset(self):
                return None

            def sudo(self):
                return self

            def write(self, values):
                self.writes.append(dict(values))
                self.status = values.get('status', self.status)
                return True

        class FakeJob:
            store_id = SimpleNamespace(id=1)

            def __init__(self):
                self.transitions = []

            def _transition_blocked_manual_review(self, *args):
                self.transitions.append(args)

        mapping = SimpleNamespace(id=70)
        cases = (
            ('stale', SimpleNamespace(
                source_updated_at=fields.Datetime.add(stamp, seconds=1),
                available=3,
            ), 3, 7, False),
            ('duplicate', SimpleNamespace(
                source_updated_at=stamp, available=7,
            ), 7, 7, False),
            ('manual_review', SimpleNamespace(
                source_updated_at=stamp, available=8,
            ), 8, 7, True),
        )
        for state, latest, target, pushed, freezes in cases:
            with self.subTest(state=state):
                binding = FakeBinding()
                binding.last_pushed_at = stamp if freezes else False
                binding.last_pushed_available = pushed
                job = FakeJob()
                with patch.object(
                    type(service), '_outbound_lineage', return_value=False,
                ), patch.object(
                    type(service), '_latest_observation', return_value=latest,
                ), patch.object(
                    type(service), '_record_observation',
                ) as record, patch.object(
                    type(inventory_service), '_refresh_pending_target',
                    return_value=(target, 0),
                ) as refresh_target:
                    service._apply_snapshot(
                        job, binding, mapping, snapshot,
                    )
                self.assertTrue(record.called)
                self.assertEqual(record.call_args.args[4], state)
                refresh_target.assert_not_called()
                if freezes:
                    self.assertEqual(binding.status, 'review')
                    self.assertTrue(job.transitions)

        drift_binding = FakeBinding()
        drift_binding.last_pushed_at = stamp
        drift_binding.last_pushed_available = 5
        drift_job = FakeJob()
        with patch.object(
            type(service), '_outbound_lineage', return_value=False,
        ), patch.object(
            type(service), '_latest_observation', return_value=False,
        ), patch.object(
            type(service), '_record_observation',
        ) as record, patch.object(
            type(inventory_service), '_refresh_pending_target',
            return_value=(6, 0),
        ) as refresh_target:
            service._apply_snapshot(drift_job, drift_binding, mapping, snapshot)
        refresh_target.assert_called_once_with(drift_binding)
        self.assertEqual(record.call_args.args[4], 'manual_review')
        self.assertEqual(drift_binding.status, 'review')
        self.assertTrue(drift_job.transitions)

    def test_scheduler_uses_real_cron_commit_progress_for_cursor_admission(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ].sudo().with_context(
            _inventory_observation_cron=_CRON_CONTEXT_SENTINEL,
            cron_id=self.env.ref(
                'shopify_connector_inventory_webhook.ir_cron_shopify_connector_inventory_observation'
            ).id,
        )

        class FakeStore:
            id = 88
            inventory_observation_cursor_id = 0
            inventory_observation_scheduled_at = False

            def __init__(self):
                self.writes = []

            def sudo(self):
                return self

            def write(self, values):
                self.writes.append(dict(values))
                for key, value in values.items():
                    setattr(self, key, value)
                return True

        store = FakeStore()
        binding = SimpleNamespace(id=8801, shopify_gid='level-8801')
        progress = []

        def commit_progress(cron, processed=0, remaining=None, **kwargs):
            progress.append((processed, remaining, kwargs))
            return 1

        Cron = type(self.env['ir.cron'])
        with patch.object(Cron, '_commit_progress', new=commit_progress), \
             patch.object(type(service), '_scheduled_observation_stores',
                          return_value=[store]), \
             patch.object(type(service), '_observation_candidates',
                          return_value=[binding]), \
             patch.object(type(service), '_admit_fallback_pair',
                          return_value=(True, 'coalesced')):
            self.assertEqual(
                service.run_scheduled_observation_fallback(limit=1), 0,
            )
        self.assertEqual(store.inventory_observation_cursor_id, 8801)
        self.assertTrue(any(processed == 1 for processed, _r, _k in progress))

    def test_public_scheduler_acl_denies_non_administrator(self):
        user = self.env['res.users'].create({
            'name': 'W3 Inventory Observer Without Admin',
            'login': 'w3_inventory_observer_no_admin',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            self.env[
                'shopify.connector.inventory.observation.service'
            ].with_user(user).run_scheduled_observation_fallback(limit=1)

    def test_scheduler_company_isolation_uses_active_allowed_company(self):
        other_company = self.env['res.company'].sudo().create({
            'name': 'W3 Other Company',
        })
        other_store = self.env['shopify.connector.store'].sudo().create({
            'name': 'W3 Other Company Store',
            'shop_domain': 'w3-other-company.myshopify.com',
            'api_version': SHOPIFY_API_VERSION,
            'company_id': other_company.id,
            'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': other_store.id,
            'inventory_domain_enabled': True,
            'inventory_scheduled_sync_enabled': True,
        })
        own_store = self._store('allowed-company')
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ].sudo().with_context(allowed_company_ids=[self.env.company.id])
        stores = service._scheduled_observation_stores(10)
        self.assertIn(own_store, stores)
        self.assertNotIn(other_store, stores)
        spoofed = service.with_context(
            _inventory_observation_cron=True,
        )._scheduled_observation_stores(10)
        self.assertNotIn(other_store, spoofed)
        spoofed_string = service.with_context(
            _inventory_observation_cron='true',
        )._scheduled_observation_stores(10)
        self.assertNotIn(other_store, spoofed_string)
        cron_stores = service.with_context(
            _inventory_observation_cron=_CRON_CONTEXT_SENTINEL,
        )._scheduled_observation_stores(10)
        self.assertIn(other_store, cron_stores)

    def test_root_observation_cron_entry_sets_private_identity_sentinel(self):
        observation = self.env[
            'shopify.connector.inventory.observation'
        ].sudo()
        service_model = type(self.env[
            'shopify.connector.inventory.observation.service'
        ])

        def guarded_service_run(service, limit):
            self.assertIs(
                service.env.context.get('_inventory_observation_cron'),
                _CRON_CONTEXT_SENTINEL,
            )
            return limit

        with patch.object(
            service_model, 'run_scheduled_observation_fallback',
            new=guarded_service_run,
        ):
            self.assertEqual(
                observation._run_scheduled_observation_fallback(limit=7), 7,
            )

    def test_non_root_cannot_enter_either_cron_wrapper(self):
        user = self.env['res.users'].create({
            'name': 'W3 Non Root Cron User',
            'login': 'w3_non_root_cron_user',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        observation = self.env[
            'shopify.connector.inventory.observation'
        ].with_user(user)
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ].with_user(user)
        with self.assertRaises(AccessError):
            observation._run_scheduled_observation_fallback(limit=1)
        with self.assertRaises(AccessError):
            service._run_scheduled_observation_fallback(limit=1)

    def test_cron_migration_updates_existing_noupdate_row_idempotently(self):
        path = Path(__file__).resolve().parents[1] / 'migrations' / '19.0.0.3.0' / 'post-migrate.py'
        spec = importlib.util.spec_from_file_location('w3_cron_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        cron = self.env.ref(
            'shopify_connector_inventory_webhook.ir_cron_shopify_connector_inventory_observation',
        ).sudo()
        cron.write({'code': 'model.run_scheduled_observation_fallback(limit=20)'})
        cron.invalidate_recordset()
        self.assertEqual(
            cron.code, 'model.run_scheduled_observation_fallback(limit=20)',
        )
        before = (cron.active, cron.interval_number, cron.interval_type,
                  cron.user_id.id, cron.model_id.id)
        migration.migrate(self.env.cr, '19.0.0.2.0')
        cron.invalidate_recordset()
        self.assertEqual(
            cron.code, 'model._run_scheduled_observation_fallback(limit=20)',
        )
        action = cron.ir_actions_server_id.sudo()
        action_audit = (action.write_date, action.write_uid.id)
        migration.migrate(self.env.cr, '19.0.0.3.0')
        cron.invalidate_recordset()
        action.invalidate_recordset()
        self.assertEqual(
            before,
            (cron.active, cron.interval_number, cron.interval_type,
             cron.user_id.id, cron.model_id.id),
        )
        self.assertEqual(cron.code, migration.TARGET_CODE)
        self.assertEqual(action_audit, (action.write_date, action.write_uid.id))

    def test_cron_migration_missing_xmlid_is_a_bounded_noop(self):
        path = Path(__file__).resolve().parents[1] / 'migrations' / '19.0.0.3.0' / 'post-migrate.py'
        spec = importlib.util.spec_from_file_location('w3_missing_cron_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        class MissingXmlidEnv:
            def ref(self, xmlid, raise_if_not_found=False):
                self.request = (xmlid, raise_if_not_found)
                return None

        fake_env = MissingXmlidEnv()
        with patch.object(
            migration.api, 'Environment', return_value=fake_env,
        ):
            migration.migrate(object(), '19.0.0.2.0')
        self.assertEqual(
            fake_env.request,
            (
                'shopify_connector_inventory_webhook.'
                'ir_cron_shopify_connector_inventory_observation',
                False,
            ),
        )

    def test_scheduler_store_page_is_sql_bounded_and_null_oldest_fair(self):
        stores = [self._store('fair-%s' % index) for index in range(4)]
        stores[0].sudo().write({
            'inventory_observation_scheduled_at': '2026-08-22 10:00:00',
        })
        stores[1].sudo().write({
            'inventory_observation_scheduled_at': '2026-08-22 08:00:00',
        })
        settings = self.env['shopify.connector.store.settings']
        checkpoint = settings._fields['inventory_observation_scheduled_at']
        self.assertTrue(checkpoint.store)
        self.assertTrue(checkpoint.index)

        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        selected = service._scheduled_observation_stores(3)
        selected_ids = [store.id for store in selected]
        null_ids = sorted(store.id for store in stores[2:])
        self.assertEqual(selected_ids[:2], null_ids)
        self.assertEqual(selected_ids[2], stores[1].id)
        self.assertLessEqual(len(selected), 3)

    def test_dispatch_routes_missing_binding_to_manual_fix_retryable(self):
        store = self._store('handler-retry')
        level_gid = 'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'scheduled_sync',
            'job_type': INVENTORY_OBSERVATION_JOB_TYPE,
            'state': 'queued',
            'res_model': 'shopify.connector.store',
            'res_id': store.id,
            'shopify_target_gid': level_gid,
            'expected_connection_generation': store.connection_generation,
        })
        self.env['shopify.connector.job.dispatch']._dispatch_one(job)
        job.invalidate_recordset()
        # Missing binding is a manual-fix-then-retry classification.  It is
        # deliberately not an automatic replay: no retry timestamp is set and
        # the attempt budget remains untouched until an operator repairs the
        # pair and explicitly requeues the job.
        self.assertEqual(job.state, 'failed_retryable')
        self.assertEqual(job.error_class, 'shopify_user_errors_validation')
        self.assertEqual(job.retry_count, 0)
        self.assertFalse(job.next_retry_at)
        self.assertTrue(job.finished_at)

    def test_dispatch_retries_remote_read_then_replays_to_success(self):
        """A temporary remote read is retried through the real job entry point."""
        store = self._store('handler-replay')
        level_gid = 'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'scheduled_sync',
            'job_type': INVENTORY_OBSERVATION_JOB_TYPE,
            'state': 'queued',
            'res_model': 'shopify.connector.store',
            'res_id': store.id,
            'shopify_target_gid': level_gid,
            'expected_connection_generation': store.connection_generation,
        })
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        Service = type(service)
        client = self.env['shopify.connector.api.client']
        Client = type(client)

        class FakeBinding:
            status = 'active'

            def __len__(self):
                return 1

        binding = FakeBinding()
        mapping = SimpleNamespace(id=7001)
        read_calls = []
        result = {
            'data': {
                'shop': {'myshopifyDomain': store.shop_domain},
                'inventoryLevel': {
                    'id': level_gid,
                    'item': {
                        'id': 'gid://shopify/InventoryItem/8001',
                        'tracked': True,
                    },
                    'location': {'id': 'gid://shopify/Location/7001'},
                    'quantities': [{
                        'name': 'available',
                        'quantity': 4,
                        'updatedAt': '2026-08-22T08:00:00Z',
                    }],
                },
            },
        }

        @contextmanager
        def guarded_read(_client, read_job, read_store, query, variables,
                         purpose):
            read_calls.append((read_job.id, read_store.id, query, variables,
                               purpose))
            if len(read_calls) == 1:
                raise ShopifyClientError(
                    ERROR_CLASS_TEMPORARY, 'temporary observation read',
                )
            yield result

        with patch.object(
            Service, '_find_binding_by_level_gid', return_value=binding,
        ), patch.object(
            Service, '_outbound_lineage', return_value=False,
        ), patch.object(
            Service, '_resolve_exact_binding', return_value=(binding, mapping),
        ), patch.object(
            Service, '_apply_snapshot', return_value=None,
        ), patch.object(
            Client, 'execute_business_read', new=guarded_read,
        ):
            dispatch = self.env['shopify.connector.job.dispatch']
            dispatch._dispatch_one(job)
            job.invalidate_recordset()
            self.assertEqual(job.state, 'retry_waiting')
            self.assertEqual(job.retry_count, 1)
            self.assertEqual(job.error_class, ERROR_CLASS_TEMPORARY)
            self.assertEqual(len(read_calls), 1)

            # Re-enter through the dispatcher: this is the durable replay,
            # not a direct service/helper invocation.
            dispatch._dispatch_one(job)
            job.invalidate_recordset()

        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(len(read_calls), 2)
        self.assertIn(
            'quantities(names: ["available"]) { name quantity updatedAt }',
            read_calls[1][2],
        )
        self.assertEqual(read_calls[1][3], {'levelId': level_gid})
        self.assertEqual(read_calls[1][4], 'inventory')

    def test_apply_snapshot_handler_freezes_real_blocked_outbound_lineage(self):
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]

        class FakeBinding:
            status = 'active'

            def __init__(self):
                self.writes = []

            def try_lock_for_update(self):
                return self

            def invalidate_recordset(self):
                return None

            def sudo(self):
                return self

            def write(self, values):
                self.writes.append(dict(values))
                self.status = values.get('status', self.status)
                return True

        class FakeJob:
            retry_count = 0
            started_at = fields.Datetime.now()
            store_id = SimpleNamespace(id=1)

            def __init__(self):
                self.transitions = []

            def _transition_blocked_manual_review(self, *args):
                self.transitions.append(args)

        binding = FakeBinding()
        job = FakeJob()
        lineage = SimpleNamespace(id=991, state='blocked_manual_review')
        snapshot = {
            'source_updated_at': fields.Datetime.now(),
            'available': 1,
        }
        with patch.object(
            type(service), '_outbound_lineage', return_value=lineage,
        ):
            service._apply_snapshot(
                job, binding, SimpleNamespace(id=1), snapshot,
            )
        self.assertEqual(binding.status, 'review')
        self.assertTrue(job.transitions)

    def test_real_handler_applies_read_evidence_without_stock_or_mutation_work(self):
        """Run the registered child handler against real ORM pair records."""
        store = self._store('orm-handler')
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1,
        )
        location = self.env['stock.location'].create({
            'name': 'W3 ORM Observation Location',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })
        mapping = self.env[
            'shopify.connector.location.mapping'
        ].sudo().create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Location/7001',
            'odoo_location_id': location.id,
            'match_key': 'manual',
        })
        template = self.env['product.template'].create({
            'name': 'W3 ORM Observation Product',
            'type': 'consu',
            'is_storable': True,
        })
        template_binding = self.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Product/8001',
            'product_template_id': template.id,
        })
        variant_binding = self.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/8001',
            'product_variant_id': template.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        })
        level_gid = (
            'gid://shopify/InventoryLevel/7001?inventory_item_id=8001'
        )
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().create({
            'store_id': store.id,
            'shopify_gid': level_gid,
            'product_variant_binding_id': variant_binding.id,
            'location_mapping_id': mapping.id,
            'shopify_inventory_item_gid': (
                'gid://shopify/InventoryItem/8001'
            ),
            'first_push_state': 'confirmed',
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'scheduled_sync',
            'job_type': INVENTORY_OBSERVATION_JOB_TYPE,
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'running_since': fields.Datetime.now(),
            'res_model': 'shopify.connector.store',
            'res_id': store.id,
            'shopify_target_gid': level_gid,
            'expected_connection_generation': store.connection_generation,
        })
        result = {
            'data': {
                'shop': {'myshopifyDomain': store.shop_domain},
                'inventoryLevel': {
                    'id': level_gid,
                    'item': {
                        'id': 'gid://shopify/InventoryItem/8001',
                        'tracked': True,
                    },
                    'location': {'id': 'gid://shopify/Location/7001'},
                    'quantities': [{
                        'name': 'available',
                        'quantity': 4,
                        'updatedAt': '2026-08-22T08:00:00Z',
                    }],
                },
            },
        }
        Quant = self.env['stock.quant'].sudo()
        before_quants = Quant.search_read([], ['quantity', 'reserved_quantity'])
        Attempt = self.env['shopify.connector.mutation.attempt'].sudo()
        before_attempt_count = Attempt.search_count([
            ('store_id', '=', store.id),
        ])
        Client = type(self.env['shopify.connector.api.client'])

        @contextmanager
        def guarded_read(_client, read_job, read_store, query, variables, purpose):
            self.assertEqual(read_job, job)
            self.assertEqual(read_store, store)
            self.assertIn('quantities(names: ["available"])', query)
            self.assertEqual(variables, {'levelId': level_gid})
            self.assertEqual(purpose, 'inventory')
            yield result

        handler = self.env['shopify.connector.job.dispatch']._get_handlers()[
            INVENTORY_OBSERVATION_JOB_TYPE
        ]
        with patch.object(Client, 'execute_business_read', new=guarded_read):
            handler(job)

        evidence = self.env[
            'shopify.connector.inventory.observation'
        ].sudo().search([('job_id', '=', job.id)])
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence.state, 'accepted')
        self.assertEqual(evidence.binding_id, binding)
        self.assertEqual(evidence.location_gid, mapping.shopify_gid)
        self.assertEqual(
            Quant.search_read([], ['quantity', 'reserved_quantity']),
            before_quants,
        )
        self.assertFalse(self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', 'in', (
                'inventory_push_sync', 'inventory_first_push_preview',
                'inventory_set_quantities', 'inventory_activate',
                'inventory_mutation_reconcile',
            )),
        ]))
        outbound_jobs = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', 'in', (
                'inventory_push_sync', 'inventory_first_push_preview',
                'inventory_set_quantities', 'inventory_activate',
                'inventory_mutation_reconcile',
            )),
        ])
        self.assertFalse(self.env[
            'shopify.connector.mutation.attempt'
        ].sudo().search([('job_id', 'in', outbound_jobs.ids)]))
        self.assertEqual(
            Attempt.search_count([('store_id', '=', store.id)]),
            before_attempt_count,
        )
        self.assertFalse(Attempt.search([('job_id', '=', job.id)]))

    def test_w3_is_read_first_and_suite_is_fail_closed(self):
        root = Path(__file__).resolve().parents[1]
        service = (root / 'models' /
                   'shopify_connector_inventory_observation.py').read_text()
        handler = (root / 'models' /
                   'shopify_connector_inventory_webhook.py').read_text()
        constants = (root / 'models' / 'constants.py').read_text()
        runner = (root.parents[1] / 'tools' /
                  'run_connector_suite.sh').read_text()
        manifest = (root / '__manifest__.py').read_text()
        cron = (root / 'data' /
                'shopify_connector_inventory_webhook_cron.xml').read_text()
        acl = (root / 'security' / 'ir.model.access.csv').read_text()
        rule = (root / 'security' /
                'shopify_connector_inventory_webhook_company_rules.xml').read_text()
        child = service.split(
            'def _handle_inventory_observation_sync', 1,
        )[1].split('def _observation_candidates', 1)[0]
        self.assertIn('execute_business_read', service)
        self.assertIn('inventoryLevel(id: $levelId) { id', service)
        self.assertIn(
            'quantities(names: ["available"]) { name quantity updatedAt }',
            service,
        )
        self.assertNotIn('execute_business(', child)
        self.assertNotIn('job.enqueue', child)
        self.assertNotIn('inventory_set_quantities', child)
        self.assertIn("job_source='webhook'", handler)
        self.assertIn(INVENTORY_OBSERVATION_JOB_TYPE, handler)
        self.assertIn('INVENTORY_WEBHOOK_TOPIC', handler)
        self.assertIn(
            "INVENTORY_WEBHOOK_TOPIC = 'inventory_levels/update'",
            constants,
        )
        self.assertIn("'shopify_connector_webhook'", manifest)
        self.assertIn("'shopify_connector_inventory'", manifest)
        self.assertIn('shopify_connector_inventory_webhook', runner)
        self.assertIn('W3_INVENTORY_WEBHOOK_VERSION', runner)
        self.assertIn(
            'model_shopify_connector_inventory_observation', cron,
        )
        self.assertIn(
            'model._run_scheduled_observation_fallback(limit=20)', cron,
        )
        self.assertIn(',1,0,0,0', acl)
        self.assertIn("('company_id', 'in', company_ids)", rule)
        self.assertIn("('sec3_scope_quarantined', '=', False)", rule)
