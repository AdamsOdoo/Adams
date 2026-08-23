import importlib.util
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged


REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = REPO_ROOT / 'tools' / 'validate_shopify_graphql.py'


def _validator_module():
    spec = importlib.util.spec_from_file_location(
        'shopify_graphql_schema_conformance', VALIDATOR_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged('post_install', '-at_install')
class TestGraphqlSchemaConformance(TransactionCase):

    def test_all_production_documents_validate_against_2026_07(self):
        validator = _validator_module()
        documents = validator.discover_documents(REPO_ROOT)
        self.assertGreaterEqual(
            len(documents), 47,
            'Document discovery unexpectedly shrank; no GraphQL operation '
            'may disappear from the schema gate silently.',
        )
        self.assertEqual(
            validator.validate_documents(validator.load_schema(), documents),
            [],
        )

    def test_undefined_field_fails_the_conformance_gate(self):
        validator = _validator_module()
        failures = validator.validate_documents(
            validator.load_schema(),
            [(Path('negative.graphql'), 1,
              'query NegativeSchemaCanary { shop { definitelyUndefined } }')],
        )
        self.assertEqual(len(failures), 1)
        self.assertIn('Cannot query field', failures[0][2])
