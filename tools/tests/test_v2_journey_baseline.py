import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "v2" / "evidence"


class TestV2JourneyBaseline(unittest.TestCase):
    def _load(self, name):
        return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))

    def test_u1_through_u14_are_complete_contracts(self):
        baseline = self._load("journey-baseline.json")
        journeys = baseline["journeys"]
        self.assertEqual(
            [journey["id"] for journey in journeys],
            [f"U{index}" for index in range(1, 15)],
        )
        self.assertEqual(len(set(baseline["required_assertion_axes"])), 8)

        required_nonempty = (
            "actors",
            "trigger_paths",
            "ui_contracts",
            "backend_assertions",
            "remote_assertions",
            "failure_branches",
            "proof_packets",
        )
        fixture_ids = set()
        for journey in journeys:
            self.assertRegex(journey["fixture_id"], r"^journey\.[a-z0-9_]+\.v1$")
            self.assertNotIn(journey["fixture_id"], fixture_ids)
            fixture_ids.add(journey["fixture_id"])
            for key in required_nonempty:
                self.assertIsInstance(journey[key], list, (journey["id"], key))
                self.assertTrue(journey[key], (journey["id"], key))
            for packet in journey["proof_packets"]:
                self.assertRegex(packet, r"^P(?:0[0-9]|1[0-9]|20)$")
            self.assertEqual(journey["current_status"], "pending_execution")

        by_id = {journey["id"]: journey for journey in journeys}
        self.assertIn("operation_launcher", by_id["U3"]["ui_contracts"])
        self.assertIn("external token revocation pending", by_id["U11"]["failure_branches"])
        self.assertIn(
            "admin_lifecycle_status_or_explicit_runbook",
            by_id["U13"]["ui_contracts"],
        )
        self.assertIn("after-send mutation uncertainty", by_id["U14"]["failure_branches"])

    def test_setup_semantic_keys_and_both_phase_projections_preserve_order(self):
        baseline = self._load("setup-compatibility-baseline.json")
        durable = baseline["durable_steps"]
        keys = [step["step_key"] for step in durable]
        self.assertEqual([step["ordinal"] for step in durable], list(range(1, 13)))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("step_key is authoritative", baseline["canonical_addressing_rule"])

        for phase_key in ("v1_presentation_phases", "v2_presentation_phases"):
            projected = [
                step_key
                for phase in baseline[phase_key]
                for step_key in phase["step_keys"]
            ]
            self.assertEqual(projected, keys, phase_key)
            self.assertEqual(
                len({phase["phase_key"] for phase in baseline[phase_key]}),
                len(baseline[phase_key]),
            )

        self.assertEqual(len(baseline["v1_presentation_phases"]), 5)
        self.assertEqual(len(baseline["v2_presentation_phases"]), 6)
        self.assertEqual(
            set(baseline["legacy_numeric_resume_map"].values()),
            set(baseline["legacy_numeric_resume_map"].values()) & set(keys),
        )
        self.assertEqual(baseline["status"], "contract_frozen_execution_pending")


if __name__ == "__main__":
    unittest.main()
