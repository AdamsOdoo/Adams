import unittest

from ..tools.redaction import REDACTED, SENSITIVE_KEYS, redact


class TestRedaction(unittest.TestCase):

    def test_key_based_redaction_all_sensitive_keys(self):
        for key in SENSITIVE_KEYS:
            self.assertEqual(
                redact({key: 'shpat_DUMMYDUMMYDUMMY0000000000000000'}),
                {key: REDACTED},
            )

    def test_key_based_redaction_header_casing_variants(self):
        self.assertEqual(
            redact({'Authorization': 'Bearer shpat_DUMMYDUMMYDUMMY0000'}),
            {'Authorization': REDACTED},
        )
        self.assertEqual(
            redact({'X-Shopify-Access-Token': 'shpat_DUMMYDUMMYDUMMY0000'}),
            {'X-Shopify-Access-Token': REDACTED},
        )

    def test_value_pattern_hits_inside_longer_strings(self):
        message = (
            'connected with token shpat_DUMMYDUMMYDUMMY0000000000000000 '
            'and refresh shprt_DUMMYDUMMYDUMMY0000000000000000'
        )
        redacted = redact(message)
        self.assertNotIn('shpat_DUMMYDUMMYDUMMY0000000000000000', redacted)
        self.assertNotIn('shprt_DUMMYDUMMYDUMMY0000000000000000', redacted)
        self.assertIn(REDACTED, redacted)

    def test_exact_match_scrub_of_arbitrary_format_dummy(self):
        arbitrary_dummy = 'ARBITRARY-DUMMY-FORMAT-000000000000'
        message = 'stored value %s in the record' % arbitrary_dummy
        redacted = redact(message, extra_secrets=[arbitrary_dummy])
        self.assertNotIn(arbitrary_dummy, redacted)
        self.assertIn(REDACTED, redacted)

    def test_nested_structures_shape_preserved(self):
        nested = {
            'outer': [
                {'access_token': 'shpat_DUMMYDUMMYDUMMY0000000000000000'},
                ('note', 'shpat_DUMMYDUMMYDUMMY0000000000000000'),
            ],
        }
        redacted = redact(nested)
        self.assertIsInstance(redacted, dict)
        self.assertIsInstance(redacted['outer'], list)
        self.assertIsInstance(redacted['outer'][0], dict)
        self.assertIsInstance(redacted['outer'][1], tuple)
        self.assertEqual(redacted['outer'][0]['access_token'], REDACTED)
        self.assertNotIn(
            'shpat_DUMMYDUMMYDUMMY0000000000000000', redacted['outer'][1][1]
        )

    def test_idempotence(self):
        message = 'token shpat_DUMMYDUMMYDUMMY0000000000000000'
        once = redact(message)
        twice = redact(once)
        self.assertEqual(once, twice)

    def test_non_string_passthrough(self):
        self.assertEqual(redact(42), 42)
        self.assertEqual(redact(4.2), 4.2)
        self.assertIsNone(redact(None))
        self.assertEqual(redact(True), True)
        self.assertEqual(redact(False), False)

    def test_input_not_mutated_in_place(self):
        original = {'access_token': 'shpat_DUMMYDUMMYDUMMY0000000000000000'}
        snapshot = dict(original)
        redact(original)
        self.assertEqual(original, snapshot)
