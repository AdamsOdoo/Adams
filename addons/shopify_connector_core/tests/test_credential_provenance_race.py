"""The obsolete-token race, proved ACROSS transactions instead of within one.

WHY THIS FILE EXISTS
--------------------

`test_client_credentials.py` covers the refresh path's decisions -- the margin
arithmetic, the taxonomy, the invalidation on rotation -- and all of it runs
inside a single `TransactionCase` cursor under `registry_enter_test_mode()`. That
is real coverage of the *logic* and no coverage at all of the *mechanism*. Two
things are unprovable there, by construction:

* **A concurrent commit.** Under test mode every `registry.cursor()` is a
  `TestCursor` layered on the one test connection, so the refresh's side
  transaction and the "other operator's" rotation are the same PostgreSQL
  session. A transaction cannot be overtaken by itself, and the whole defect is
  about being overtaken.
* **The losing side of the advisory lock.** `pg_try_advisory_xact_lock` is
  re-grantable within one session, so the leader branch was taken on every call
  and the waiter branch -- the one that must never exchange competitively -- was
  never executed. The previous cycle's records nevertheless described that
  coverage as refresh coalescing. It was a sequential-call test.

This file is the proof. Genuine independent `db_connect` connections, distinct
backend PIDs, real commit boundaries, and the race STEPPED from inside the
patched token exchange so it runs identically every time -- no threads, no
sleeps, no barriers.

THE DEFECT, EXACTLY
-------------------

At `0a15b176e60b77bf2f40195a9961591c788e14f8` the whole refresh ran in ONE side
transaction: read the client pair, POST to Shopify, write the cache. Odoo cursors
run REPEATABLE READ, so a rotation that committed during the POST was invisible
to it -- and when the cache row was absent (the ordinary first-refresh case) the
write was a plain INSERT that conflicted with nothing. A token minted from secret
pair A was therefore committed and served for up to 24 hours after the merchant
had rotated to pair B. `credential_id` did not catch it: a rotation updates that
row in place, so the relation still pointed at it.

`TestCredentialProvenanceRaceAtAnyHead` is deliberately written to run unchanged
on the vulnerable head and on the corrected one -- it drives only public routes
and passes no argument that head lacks -- so it is a genuine before/after
reproducer rather than an assertion about code that already exists. It FAILS at
`0a15b17` and passes after the correction.

Zero Shopify contact: `_send_token_exchange` and `_send_lifecycle` are replaced,
so the real client, the real admission and the real taxonomy all run and only the
socket is absent. Every credential in this file is a synthetic marker string.
"""

import uuid

from odoo import SUPERUSER_ID, api
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase, tagged

from ..models import shopify_connector_store_credential as credential_module
from ..models.shopify_connector_api_client import (
    ERROR_AUTH,
    ERROR_TEMPORARY,
    ShopifyClientError,
)
from .test_api_client import FakeResponse, _success_body

PAIR_A_ID = 'race-client-id-AAAA0000000000000000'
PAIR_A_SECRET = 'race-secret-AAAA-LEAKCANARY-000000000'
PAIR_B_ID = 'race-client-id-BBBB0000000000000000'
PAIR_B_SECRET = 'race-secret-BBBB-LEAKCANARY-000000000'
TOKEN_FROM_A = 'shpat_MINTEDFROMPAIRA0000000000000000'
TOKEN_FROM_B = 'shpat_MINTEDFROMPAIRB0000000000000000'


def _token_response(token, expires_in=86399, scope='read_products'):
    return FakeResponse(200, json_body={
        'access_token': token,
        'scope': scope,
        'expires_in': expires_in,
    }, headers={})


class _GenuineCredentialHelpers:
    """Bounded real connections, committed fixtures, provable teardown.

    Copied in shape from `TestExportReconnectSettlementRace` in
    `shopify_connector_product_export` -- the repository's accepted
    genuine-connection harness -- so a reader compares like with like.
    """

    STATEMENT_TIMEOUT_MS = 15000
    LOCK_TIMEOUT_MS = 8000

    def _open_bounded(self):
        """A real pooled cursor carrying both transaction-local PG limits.

        Bounded so this file fails closed. A proof about lock conflicts that is
        one deadlock away from hanging the suite reports as neither pass nor
        fail, which is the worst available outcome.
        """
        cr = db_connect(self.env.cr.dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _backend_pid(self, cr):
        cr.execute('SELECT pg_backend_pid()')
        return cr.fetchone()[0]

    def _real_registry_cursor(self):
        """`registry.cursor()` handing out bounded REAL pooled cursors.

        Production opens the refresh's lock/write transactions on
        `registry.cursor()`. In test mode that is a `TestCursor` sharing the one
        test connection, which would quietly re-join the two sides this file
        exists to keep apart -- and would make the advisory lock re-grantable,
        so the waiter branch could never run.
        """
        return lambda *args, **kwargs: self._open_bounded()

    # -- fixtures ------------------------------------------------------

    def _commit_store(self, state='connected', pair=(PAIR_A_ID, PAIR_A_SECRET),
                      suffix=None):
        """A committed store on the client-credentials mode, pair A.

        Committed on its own connection, because both sides below must see it
        from transactions this one does not own.
        """
        suffix = suffix or uuid.uuid4().hex[:8]
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Credential race store %s' % suffix,
                'shop_domain': 'cred-race-%s.myshopify.com' % suffix,
                'api_version': self._api_version(env),
            })
            env['shopify.connector.store.credential'
                ].action_set_client_credentials(store, pair[0], pair[1])
            # Set the lifecycle state AFTER the credential, because setting a
            # credential on a `connected` store deliberately demotes it. The
            # fixture wants a store that is connected WITH pair A configured.
            store.write({'state': state})
            env.flush_all()
            fixture = {
                'store_id': store.id,
                'shop_domain': store.shop_domain,
                'generation': store.connection_generation,
            }
            cr.commit()
            self.addCleanup(self._cleanup_and_assert_no_residue, fixture)
        finally:
            cr.close()
        return fixture

    def _api_version(self, env):
        from ..models.shopify_connector_api_client import SHOPIFY_API_VERSION
        return SHOPIFY_API_VERSION

    def _cleanup_and_assert_no_residue(self, fixture):
        """Remove this test's COMMITTED rows, then prove they are gone.

        `TransactionCase` rolls back its own cursor; it cannot roll back what
        these connections committed. Raw SQL, scoped to this one store id, in
        foreign-key order -- and the credential row cannot be unlinked through
        the ORM at all now (history is retained), which is another reason this is
        SQL rather than a recordset call.
        """
        store_id = fixture['store_id']
        cr = self._open_bounded()
        try:
            for table in (
                'shopify_connector_store_access_token',
                'shopify_connector_call_lease',
                'shopify_connector_job_log',
                'shopify_connector_job',
                'shopify_connector_store_credential',
                'shopify_connector_store_settings',
                'shopify_connector_store',
            ):
                if table == 'shopify_connector_job_log':
                    cr.execute(
                        'DELETE FROM shopify_connector_job_log WHERE job_id IN '
                        '(SELECT id FROM shopify_connector_job '
                        ' WHERE store_id = %s)', (store_id,),
                    )
                    continue
                column = 'id' if table == 'shopify_connector_store' \
                    else 'store_id'
                cr.execute(
                    'DELETE FROM %s WHERE %s = %%s' % (table, column),
                    (store_id,),
                )
            cr.commit()
            cr.execute(
                'SELECT count(*) FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            self.assertEqual(
                cr.fetchone()[0], 0,
                'the genuine-connection fixture left committed residue',
            )
            cr.rollback()
        finally:
            cr.close()

    # -- observation ---------------------------------------------------

    def _column_exists(self, cr, table, column):
        """Whether `table.column` exists in this database.

        `credential_epoch` is added BY the correction, so a run of this file
        against the vulnerable head must not fail on a missing column before it
        reaches the assertion it exists to make. This keeps the observation
        head-agnostic, which is what lets the reproducer class below be the same
        code on both sides of the fix rather than a description of one side.
        """
        cr.execute(
            'SELECT 1 FROM information_schema.columns '
            'WHERE table_name = %s AND column_name = %s',
            (table, column),
        )
        return bool(cr.fetchone())

    def _observe(self, fixture):
        """COMMITTED authentication state, read on an independent connection."""
        cr = self._open_bounded()
        try:
            cr.execute(
                'SELECT state, connection_generation FROM '
                'shopify_connector_store WHERE id = %s', (fixture['store_id'],),
            )
            store_row = cr.fetchone()
            has_epoch = self._column_exists(
                cr, 'shopify_connector_store_credential', 'credential_epoch',
            )
            cr.execute(
                'SELECT client_id, credential_state, auth_mode%s '
                'FROM shopify_connector_store_credential WHERE store_id = %%s'
                % (', credential_epoch' if has_epoch else ', NULL'),
                (fixture['store_id'],),
            )
            credential_row = cr.fetchone()
            cr.execute(
                'SELECT access_token FROM '
                'shopify_connector_store_access_token WHERE store_id = %s',
                (fixture['store_id'],),
            )
            cache_row = cr.fetchone()
            cr.rollback()
        finally:
            cr.close()
        return {
            'state': store_row[0] if store_row else None,
            'generation': store_row[1] if store_row else None,
            'client_id': credential_row[0] if credential_row else None,
            'credential_state': credential_row[1] if credential_row else None,
            'auth_mode': credential_row[2] if credential_row else None,
            'credential_epoch': credential_row[3] if credential_row else None,
            'cached_token': cache_row[0] if cache_row else None,
        }

    def _served_token(self, fixture):
        """What `_get_access_token` would hand a caller, on a fresh connection.

        The question that matters is not "what is in the table" but "what does
        the connector authenticate with", so this drives the production accessor
        rather than reading the column.
        """
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            token = env['shopify.connector.store.credential']._get_access_token(
                store,
            )
            cr.rollback()
        finally:
            cr.close()
        return token

    # -- the concurrent mutations, each on its own real connection ------

    def _rotate_to_pair_b(self, fixture):
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            env['shopify.connector.store.credential'
                ].action_set_client_credentials(store, PAIR_B_ID, PAIR_B_SECRET)
            env.flush_all()
            cr.commit()
        finally:
            cr.close()

    def _clear_credential(self, fixture):
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            # `setup_incomplete`/`disconnected` clear directly; a live store
            # routes through the two-phase disconnect. Either is a genuine
            # operator clear; this drives whichever the state calls for.
            env['shopify.connector.store.credential'].action_clear_token(store)
            env.flush_all()
            cr.commit()
        finally:
            cr.close()

    def _switch_to_offline(self, fixture):
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            env['shopify.connector.store.credential'].action_set_token(
                store, 'shpat_SWITCHEDTOOFFLINE00000000000000',
            )
            env.flush_all()
            cr.commit()
        finally:
            cr.close()

    def _begin_disconnect(self, fixture):
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            store.action_disconnect()
            env.flush_all()
            cr.commit()
        finally:
            cr.close()

    # -- the worker under test -----------------------------------------

    def _refresh_with_interleaved(self, fixture, interleave, token=TOKEN_FROM_A,
                                  ensure_kwargs=None):
        """Run the production refresh, stepping `interleave` inside the exchange.

        The interleaving is deterministic without a thread or a sleep: the
        concurrent mutation is launched from INSIDE the patched
        `_send_token_exchange`, which is the one moment the worker is provably
        mid-exchange and provably has not written a cache row.

        Returns `(result, error)` -- exactly one of them is meaningful.
        """
        from unittest.mock import patch
        Client = self.env['shopify.connector.api.client']
        trace = {'exchanges': 0}

        def stepped_exchange(client_self, store, client_id, client_secret):
            trace['exchanges'] += 1
            trace['exchanged_client_id'] = client_id
            interleave(fixture)
            return _token_response(token)

        cr = self._open_bounded()
        try:
            trace['worker_pid'] = self._backend_pid(cr)
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor()), \
                 patch.object(type(Client), '_send_token_exchange',
                              stepped_exchange):
                try:
                    result = env[
                        'shopify.connector.store.credential'
                    ]._ensure_access_token(store, **(ensure_kwargs or {}))
                    error = None
                except ShopifyClientError as exc:
                    result, error = None, exc
            cr.rollback()
        finally:
            cr.close()
        return result, error, trace


# Issue #193 / #157 -- Odoo 19 test-phase contract (fixtures create business rows).
@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_credential_provenance_race')
class TestCredentialProvenanceRaceAtAnyHead(
    _GenuineCredentialHelpers, TransactionCase,
):
    """The before/after reproducer. Written to run on the vulnerable head too.

    Nothing in this class passes an argument, or calls a method, that
    `0a15b176e60b77bf2f40195a9961591c788e14f8` does not have -- the store is
    `connected` and `_ensure_access_token(store)` is called with no keyword, so
    the corrected head's default `business` purpose admits it as well. Run this
    file against that commit and these tests fail; run it after the correction
    and they pass. That is the whole point of writing it this way.
    """

    def test_a_rotation_during_the_exchange_never_caches_the_obsolete_token(self):
        """THE REPRODUCED P0.

        A refresh reads pair A, is overtaken by a rotation to pair B, and must
        not cache -- let alone serve -- a token minted from A.
        """
        fixture = self._commit_store(state='connected')
        _result, error, trace = self._refresh_with_interleaved(
            fixture, self._rotate_to_pair_b, token=TOKEN_FROM_A,
        )
        self.assertEqual(trace['exchanges'], 1)
        self.assertEqual(
            trace['exchanged_client_id'], PAIR_A_ID,
            'the exchange must have genuinely used pair A, or this test is '
            'not the race it claims to be',
        )
        observed = self._observe(fixture)
        self.assertEqual(
            observed['client_id'], PAIR_B_ID,
            'the concurrent rotation must have committed',
        )
        self.assertNotEqual(
            observed['cached_token'], TOKEN_FROM_A,
            'a token minted from the SUPERSEDED credential pair was cached; '
            'this is the reproduced obsolete-token defect',
        )
        self.assertNotEqual(
            self._served_token(fixture), TOKEN_FROM_A,
            'the connector would authenticate with a token minted from a '
            'credential the merchant has already replaced',
        )
        # And the caller is told, in the accepted taxonomy, rather than being
        # handed a silent success.
        self.assertIsNotNone(error)
        self.assertEqual(error.error_class, ERROR_TEMPORARY)
        self.assertNotIn(PAIR_A_SECRET, str(error))
        self.assertNotIn(PAIR_A_SECRET, str(error.technical_detail or ''))
        self.assertNotIn(TOKEN_FROM_A, str(error.technical_detail or ''))

    def test_a_clear_during_the_exchange_never_caches_the_obsolete_token(self):
        """The `cache absent + clear` half of the same defect."""
        fixture = self._commit_store(state='connected')
        _result, error, trace = self._refresh_with_interleaved(
            fixture, self._clear_credential, token=TOKEN_FROM_A,
        )
        self.assertEqual(trace['exchanges'], 1)
        observed = self._observe(fixture)
        self.assertNotEqual(
            observed['cached_token'], TOKEN_FROM_A,
            'a token was cached for a credential the operator had cleared',
        )
        self.assertNotEqual(self._served_token(fixture), TOKEN_FROM_A)
        self.assertIsNotNone(error)

    def test_a_mode_switch_during_the_exchange_never_caches(self):
        """A switch to the offline mode supersedes the identity just as hard."""
        fixture = self._commit_store(state='connected')
        _result, error, trace = self._refresh_with_interleaved(
            fixture, self._switch_to_offline, token=TOKEN_FROM_A,
        )
        self.assertEqual(trace['exchanges'], 1)
        observed = self._observe(fixture)
        self.assertEqual(
            observed['auth_mode'], credential_module.AUTH_MODE_OFFLINE,
            'the concurrent mode switch must have committed',
        )
        self.assertNotEqual(
            observed['cached_token'], TOKEN_FROM_A,
            'a client-credentials token was cached for a store that had '
            'switched to the offline mode',
        )
        self.assertNotEqual(self._served_token(fixture), TOKEN_FROM_A)
        self.assertIsNotNone(error)

    def test_a_rotation_over_an_existing_cache_never_serves_the_old_token(self):
        """Cache PRESENT and inside its margin, then rotated mid-exchange."""
        fixture = self._commit_store(state='connected')
        # First, a clean refresh so a cache row exists at all.
        self._refresh_with_interleaved(
            fixture, lambda _f: None, token=TOKEN_FROM_B,
        )
        self.assertEqual(self._served_token(fixture), TOKEN_FROM_B)
        # Age it into the refresh margin, keeping a genuine 24-hour lifetime.
        cr = self._open_bounded()
        try:
            cr.execute(
                'UPDATE shopify_connector_store_access_token '
                "SET obtained_at = now() - interval '23 hours 55 minutes', "
                "    expires_at = now() + interval '5 minutes' "
                'WHERE store_id = %s', (fixture['store_id'],),
            )
            cr.commit()
        finally:
            cr.close()
        _result, _error, trace = self._refresh_with_interleaved(
            fixture, self._rotate_to_pair_b, token=TOKEN_FROM_A,
        )
        self.assertEqual(trace['exchanges'], 1)
        self.assertNotEqual(
            self._served_token(fixture), TOKEN_FROM_A,
            'the obsolete token replaced a valid cache row and is now served',
        )

    def test_disconnect_beginning_during_the_exchange_discards_the_token(self):
        """A disconnect that starts mid-exchange wins; the token is discarded."""
        fixture = self._commit_store(state='connected')
        _result, error, trace = self._refresh_with_interleaved(
            fixture, self._begin_disconnect, token=TOKEN_FROM_A,
        )
        self.assertEqual(trace['exchanges'], 1)
        observed = self._observe(fixture)
        self.assertEqual(
            observed['state'], 'disconnecting',
            'the concurrent disconnect must have committed',
        )
        self.assertNotEqual(
            observed['cached_token'], TOKEN_FROM_A,
            'a token was cached for a store whose disconnect had already '
            'begun',
        )
        self.assertIsNotNone(error)


@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_credential_provenance_race')
class TestCredentialProvenanceCorrectedHead(
    _GenuineCredentialHelpers, TransactionCase,
):
    """Behaviour that only exists after the correction, proved genuinely.

    Split from the reproducer class deliberately: these use `purpose=` and the
    epoch column, neither of which the vulnerable head has, so they could not be
    part of a file that must run on it.
    """

    def test_an_epoch_only_rotation_is_still_caught(self):
        """The sharpest test of the epoch: nothing else changes.

        A rotation on a `reconnect_needed` store bumps the identity epoch and
        NOTHING else the revalidation reads -- the state does not move and the
        connection generation does not move (only a `connected` store's does).
        So the epoch is the sole thing standing between the merchant and an
        obsolete token here, which is exactly why the row id and `write_date`
        were insufficient.
        """
        fixture = self._commit_store(state='reconnect_needed')
        before = self._observe(fixture)
        _result, error, trace = self._refresh_with_interleaved(
            fixture, self._rotate_to_pair_b, token=TOKEN_FROM_A,
            ensure_kwargs={'purpose': 'setup'},
        )
        after = self._observe(fixture)
        self.assertEqual(trace['exchanges'], 1)
        self.assertEqual(
            after['state'], 'reconnect_needed',
            'the state must NOT have moved, or this test proves the state '
            'check rather than the epoch check',
        )
        self.assertEqual(
            after['generation'], before['generation'],
            'the generation must NOT have moved, for the same reason',
        )
        self.assertGreater(
            after['credential_epoch'], before['credential_epoch'],
            'the rotation must have advanced the identity epoch',
        )
        self.assertNotEqual(after['cached_token'], TOKEN_FROM_A)
        self.assertIsNotNone(error)
        self.assertEqual(error.error_class, ERROR_TEMPORARY)

    def test_a_disconnected_store_never_reaches_the_token_endpoint(self):
        """§7: lifecycle eligibility, on the business path.

        The exchange is a Shopify call and obeys the state matrix. Previously it
        ran BEFORE admission -- correctly, for the lock reason -- and therefore
        before the gate that would have refused it, so a store nobody may call
        still contacted Shopify.
        """
        fixture = self._commit_store(state='connected')
        cr = self._open_bounded()
        try:
            cr.execute(
                "UPDATE shopify_connector_store SET state = 'disconnected' "
                'WHERE id = %s', (fixture['store_id'],),
            )
            cr.commit()
        finally:
            cr.close()
        _result, error, trace = self._refresh_with_interleaved(
            fixture, lambda _f: None, token=TOKEN_FROM_A,
        )
        self.assertEqual(
            trace['exchanges'], 0,
            'a disconnected store contacted the Shopify token endpoint',
        )
        self.assertIsNotNone(error)
        self.assertEqual(error.error_class, ERROR_TEMPORARY)

    def test_a_disconnecting_store_never_reaches_the_token_endpoint(self):
        """`disconnecting` is in NO exchange matrix, by any purpose."""
        fixture = self._commit_store(state='connected')
        self._begin_disconnect(fixture)
        for purpose in ('business', 'setup', 'reconnect'):
            _result, error, trace = self._refresh_with_interleaved(
                fixture, lambda _f: None, token=TOKEN_FROM_A,
                ensure_kwargs={'purpose': purpose},
            )
            self.assertEqual(
                trace['exchanges'], 0,
                'purpose %r reached the token endpoint while the store was '
                'disconnecting' % (purpose,),
            )
            self.assertIsNotNone(error)

    def test_disconnect_quiescence_sees_an_in_flight_exchange(self):
        """§7.4/§7.5: the controller must not finalize during an exchange.

        Proved with two genuine sessions: one holds the store's refresh advisory
        lock (which is what an in-flight exchange holds, for its whole duration),
        the other runs the production quiescence pass. The pass must decline to
        complete, and must say so.
        """
        fixture = self._commit_store(state='connected')
        self._begin_disconnect(fixture)
        holder = self._open_bounded()
        try:
            holder.execute(
                'SELECT pg_try_advisory_xact_lock(%s, %s)',
                (credential_module.TOKEN_REFRESH_ADVISORY_CLASSID,
                 fixture['store_id']),
            )
            self.assertTrue(
                holder.fetchone()[0],
                'the holder connection must own the refresh lock, or the '
                'controller below is not being tested against anything',
            )
            controller = self._open_bounded()
            try:
                self.assertNotEqual(
                    self._backend_pid(holder), self._backend_pid(controller),
                    'both sides are on one PostgreSQL session, so no lock '
                    'conflict is possible and this proves nothing',
                )
                env = api.Environment(controller, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(
                    fixture['store_id'],
                )
                self.assertTrue(
                    env['shopify.connector.store.credential']
                    ._token_exchange_in_flight(store),
                    'a held refresh lock must read as an in-flight exchange',
                )
                controller.rollback()
                env = api.Environment(controller, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(
                    fixture['store_id'],
                )
                store._process_disconnect_quiesce()
                env.flush_all()
                self.assertEqual(
                    store.state, 'disconnecting',
                    'the disconnect completed while a token exchange was in '
                    'flight',
                )
                self.assertEqual(store.disconnect_status, 'quiescing')
                self.assertIn(
                    'access-token exchange', store.disconnect_status_reason,
                    'the operator-visible reason must name the blocker',
                )
                controller.rollback()
            finally:
                controller.close()
        finally:
            holder.rollback()
            holder.close()

    def test_two_genuine_workers_perform_exactly_one_exchange(self):
        """§8: real coalescing, and the waiter branch genuinely executed.

        Worker B is launched from inside worker A's exchange, on its own
        PostgreSQL session, while A provably holds the advisory lock. B must not
        exchange; it must take the non-acquired path, wait, and end in the
        accepted retryable taxonomy because A's result is discarded by design in
        this arrangement -- what is being proved is that B never mints a second
        token, not that B succeeds.
        """
        fixture = self._commit_store(state='connected')
        from unittest.mock import patch
        Client = self.env['shopify.connector.api.client']
        trace = {'a': 0, 'b': 0, 'b_error': None, 'pids': set()}
        # Keep the waiter's bound short: this test asserts the BRANCH, and a
        # ten-second poll adds nothing to that.
        original_attempts = credential_module.TOKEN_REFRESH_WAIT_ATTEMPTS
        original_delay = credential_module.TOKEN_REFRESH_WAIT_SECONDS
        credential_module.TOKEN_REFRESH_WAIT_ATTEMPTS = 2
        credential_module.TOKEN_REFRESH_WAIT_SECONDS = 0.01
        self.addCleanup(
            setattr, credential_module, 'TOKEN_REFRESH_WAIT_ATTEMPTS',
            original_attempts,
        )
        self.addCleanup(
            setattr, credential_module, 'TOKEN_REFRESH_WAIT_SECONDS',
            original_delay,
        )

        def worker_b(_fixture):
            cr = self._open_bounded()
            try:
                trace['pids'].add(self._backend_pid(cr))
                env = api.Environment(cr, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(
                    fixture['store_id'],
                )
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor()):
                    try:
                        env['shopify.connector.store.credential'
                            ]._ensure_access_token(store)
                    except ShopifyClientError as exc:
                        trace['b_error'] = exc
                cr.rollback()
            finally:
                cr.close()

        def a_exchange(client_self, store, client_id, client_secret):
            trace['a'] += 1
            # A holds the advisory lock right now. B must find it taken.
            worker_b(fixture)
            return _token_response(TOKEN_FROM_A)

        def b_exchange(client_self, store, client_id, client_secret):
            trace['b'] += 1
            return _token_response(TOKEN_FROM_B)

        def counting_exchange(client_self, store, client_id, client_secret):
            # One seam, two callers: whoever is inside `a_exchange` already is A.
            if trace['a'] == 0:
                return a_exchange(client_self, store, client_id, client_secret)
            return b_exchange(client_self, store, client_id, client_secret)

        cr = self._open_bounded()
        try:
            trace['pids'].add(self._backend_pid(cr))
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor()), \
                 patch.object(type(Client), '_send_token_exchange',
                              counting_exchange):
                env['shopify.connector.store.credential'
                    ]._ensure_access_token(store)
            cr.rollback()
        finally:
            cr.close()
        self.assertEqual(trace['a'], 1, 'the leader must exchange exactly once')
        self.assertEqual(
            trace['b'], 0,
            'the losing worker exchanged competitively; coalescing is not '
            'happening at all',
        )
        self.assertGreaterEqual(
            len(trace['pids']), 2,
            'both workers ran on one PostgreSQL session, so the advisory lock '
            'was re-grantable and the waiter branch was never exercised',
        )
        self.assertIsInstance(
            trace['b_error'], ShopifyClientError,
            'the waiter must end in the accepted taxonomy rather than '
            'silently succeeding or raising something raw',
        )
        self.assertEqual(trace['b_error'].error_class, ERROR_TEMPORARY)

    def test_different_stores_do_not_block_one_another(self):
        """The advisory lock is per store, so a second store is never queued."""
        fixture_one = self._commit_store(state='connected')
        fixture_two = self._commit_store(state='connected')
        from unittest.mock import patch
        Client = self.env['shopify.connector.api.client']
        trace = {'two_exchanged': 0}

        def other_store_refresh(_fixture):
            cr = self._open_bounded()
            try:
                env = api.Environment(cr, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(
                    fixture_two['store_id'],
                )
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor()):
                    env['shopify.connector.store.credential'
                        ]._ensure_access_token(store)
                cr.rollback()
            finally:
                cr.close()

        def exchange(client_self, store, client_id, client_secret):
            if store.id == fixture_two['store_id']:
                trace['two_exchanged'] += 1
                return _token_response(TOKEN_FROM_B)
            other_store_refresh(None)
            return _token_response(TOKEN_FROM_A)

        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(
                fixture_one['store_id'],
            )
            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor()), \
                 patch.object(type(Client), '_send_token_exchange', exchange):
                env['shopify.connector.store.credential'
                    ]._ensure_access_token(store)
            cr.rollback()
        finally:
            cr.close()
        self.assertEqual(
            trace['two_exchanged'], 1,
            "store two's refresh was blocked by store one's advisory lock",
        )
        self.assertEqual(self._served_token(fixture_two), TOKEN_FROM_B)

    def test_a_failed_leader_does_not_strand_the_next_worker(self):
        """A leader that raises releases the lock; the next worker leads."""
        fixture = self._commit_store(state='connected')
        from unittest.mock import patch
        Client = self.env['shopify.connector.api.client']
        attempts = {'n': 0}

        def failing_then_working(client_self, store, client_id, client_secret):
            attempts['n'] += 1
            if attempts['n'] == 1:
                raise ShopifyClientError(
                    error_class=ERROR_TEMPORARY,
                    reason='synthetic transport failure',
                )
            return _token_response(TOKEN_FROM_B)

        for expected_error in (True, False):
            cr = self._open_bounded()
            try:
                env = api.Environment(cr, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(
                    fixture['store_id'],
                )
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor()), \
                     patch.object(type(Client), '_send_token_exchange',
                                  failing_then_working):
                    try:
                        env['shopify.connector.store.credential'
                            ]._ensure_access_token(store)
                        raised = False
                    except ShopifyClientError:
                        raised = True
                cr.rollback()
            finally:
                cr.close()
            self.assertEqual(raised, expected_error)
        self.assertEqual(attempts['n'], 2)
        self.assertEqual(
            self._served_token(fixture), TOKEN_FROM_B,
            'the second worker must have led its own exchange rather than '
            'waiting forever on the crashed leader',
        )

    def test_test_connection_cannot_validate_with_an_obsolete_token(self):
        """The operator-visible consequence, driven through the real button.

        A rotation lands during Test Connection's own token exchange. The probe
        must not go on to validate the store and record scope evidence using a
        token minted from the credential that was just replaced.
        """
        fixture = self._commit_store(state='connected')
        from unittest.mock import patch
        Client = self.env['shopify.connector.api.client']
        trace = {'sent': 0}

        def exchange(client_self, store, client_id, client_secret):
            self._rotate_to_pair_b(fixture)
            return _token_response(TOKEN_FROM_A)

        def lifecycle(client_self, store, query, token):
            trace['sent'] += 1
            trace['token'] = token
            return {
                'data': _success_body(domain=fixture['shop_domain'])['data'],
                'throttle_status': None,
                'served_version': self._api_version(self.env),
            }

        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor()), \
                 patch.object(type(Client), '_send_token_exchange', exchange), \
                 patch.object(type(Client), '_send_lifecycle', lifecycle):
                try:
                    store.action_test_connection()
                    env.flush_all()
                    cr.commit()
                    trace['aborted'] = False
                except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
                    # An ACCEPTED outcome, and production's own. The rotation
                    # committed an update to the store row that this request's
                    # snapshot predates, so the probe's mirror write is a genuine
                    # SQLSTATE 40001 -- which `odoo.service.model.retrying`
                    # catches and re-drives the whole RPC for. What must never
                    # happen is the OTHER outcome: a probe that quietly succeeds
                    # using a token minted from the replaced credential.
                    cr.rollback()
                    trace['aborted'] = True
        finally:
            cr.close()
        self.assertEqual(
            trace['sent'], 0,
            'Test Connection sent a Shopify request after its credential was '
            'replaced mid-exchange; the obsolete token reached the transport',
        )
        self.assertIsNone(
            trace.get('token'),
            'Test Connection authenticated with a token minted from the '
            'superseded credential pair',
        )
        observed = self._observe(fixture)
        self.assertNotEqual(observed['cached_token'], TOKEN_FROM_A)
        self.assertEqual(
            observed['client_id'], PAIR_B_ID,
            'the concurrent rotation must have committed',
        )
        cr = self._open_bounded()
        try:
            cr.execute(
                'SELECT last_test_connection_result FROM '
                'shopify_connector_store WHERE id = %s',
                (fixture['store_id'],),
            )
            recorded = cr.fetchone()[0]
            cr.rollback()
        finally:
            cr.close()
        self.assertNotEqual(
            recorded, 'pass',
            'a probe whose credential was replaced underneath it must not '
            'record a passing connection (recorded: %r, request aborted: %r)'
            % (recorded, trace.get('aborted')),
        )

    def test_a_serialization_failure_is_normalized_not_raw(self):
        """§9.3: a genuine 40001 becomes the connector's taxonomy, fail-closed.

        A second genuine session updates the credential row and holds it
        uncommitted; the refresh's write transaction then blocks on it and hits
        its `lock_timeout`, which PostgreSQL reports as SQLSTATE 55P03 -- a
        member of the same concurrency family as 40001 and one that must not
        escape as a raw psycopg2 error through a Shopify-facing path.
        """
        fixture = self._commit_store(state='connected')
        from unittest.mock import patch
        Client = self.env['shopify.connector.api.client']
        blocker = self._open_bounded()

        def exchange(client_self, store, client_id, client_secret):
            # Take and HOLD the credential row lock, uncommitted, so the
            # refresh's post-network revalidation cannot acquire it.
            blocker.execute(
                'SELECT id FROM shopify_connector_store_credential '
                'WHERE store_id = %s FOR NO KEY UPDATE',
                (fixture['store_id'],),
            )
            blocker.fetchone()
            return _token_response(TOKEN_FROM_A)

        try:
            cr = self._open_bounded()
            try:
                env = api.Environment(cr, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(
                    fixture['store_id'],
                )
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor()), \
                     patch.object(type(Client), '_send_token_exchange',
                                  exchange):
                    with self.assertRaises(ShopifyClientError) as ctx:
                        env['shopify.connector.store.credential'
                            ]._ensure_access_token(store)
                cr.rollback()
            finally:
                cr.close()
        finally:
            blocker.rollback()
            blocker.close()
        self.assertEqual(ctx.exception.error_class, ERROR_TEMPORARY)
        self.assertNotIn(PAIR_A_SECRET, str(ctx.exception.technical_detail or ''))
        self.assertNotIn(TOKEN_FROM_A, str(ctx.exception.technical_detail or ''))
        observed = self._observe(fixture)
        self.assertNotEqual(
            observed['cached_token'], TOKEN_FROM_A,
            'a concurrency failure must fail CLOSED -- nothing cached',
        )
