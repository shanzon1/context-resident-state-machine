import unittest

from experiment_harness import load_context, parse_state_machine, validate_transition


class ExperimentHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context()

    def test_parses_cer_state_machine_from_context(self):
        machine = parse_state_machine(self.context)

        self.assertEqual(machine.states, frozenset({"EXPLORE", "EVALUATE", "REFINE"}))
        self.assertEqual(machine.current_state, "EXPLORE")
        self.assertEqual(machine.turn, 1)

    def test_accepts_explicit_transition(self):
        self.assertEqual(validate_transition(self.context, "EVALUATE"), "EXPLORE -> EVALUATE valid: YES")

    def test_rejects_missing_transition(self):
        self.assertEqual(validate_transition(self.context, "REFINE"), "EXPLORE -> REFINE valid: NO")


if __name__ == "__main__":
    unittest.main()
