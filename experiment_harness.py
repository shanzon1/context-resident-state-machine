from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


CONTEXT_PATH = Path("experiment_context.md")
SECTION_LINE = "=" * 78


@dataclass(frozen=True)
class Transition:
    source: str
    target: str


@dataclass(frozen=True)
class StateMachine:
    states: frozenset[str]
    transitions: frozenset[Transition]
    current_state: str
    turn: int

    def is_valid_transition(self, target: str) -> bool:
        return Transition(self.current_state, target) in self.transitions


def _extract_section(text: str, heading: str) -> str:
    pattern = (
        rf"{re.escape(SECTION_LINE)}\n"
        rf"{re.escape(heading)}\n"
        rf"{re.escape(SECTION_LINE)}\n"
        rf"(.*?)(?=\n{re.escape(SECTION_LINE)}\n[A-Z][A-Z ()0-9.]*\n{re.escape(SECTION_LINE)}|\Z)"
    )
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Missing section: {heading}")
    return match.group(1).strip()


def _extract_value_after_label(section: str, label: str) -> str:
    pattern = rf"^{re.escape(label)}\n\n(.+?)(?=\n\n[A-Z][A-Za-z ]*\n\n|\Z)"
    match = re.search(pattern, section, flags=re.DOTALL | re.MULTILINE)
    if not match:
        raise ValueError(f"Missing value for label: {label}")
    return match.group(1).strip()


def parse_state_machine(context: str) -> StateMachine:
    program = _extract_section(context, "PROGRAM DEFINITION (IMMUTABLE)")
    execution_context = _extract_section(context, "EXECUTION CONTEXT (MUTABLE)")

    states_block = re.search(r"States\n\n(.*?)\n\nTransitions", program, flags=re.DOTALL)
    if not states_block:
        raise ValueError("Missing state list")

    states = frozenset(
        line.removeprefix("-").strip()
        for line in states_block.group(1).splitlines()
        if line.strip().startswith("-")
    )

    transitions_block = re.search(
        r"Transitions\n\n(.*?)(?:\n\n-+\nState Definitions|\Z)",
        program,
        flags=re.DOTALL,
    )
    if not transitions_block:
        raise ValueError("Missing transition list")

    transitions = frozenset(
        Transition(source.strip(), target.strip())
        for source, target in (
            line.split("->", 1)
            for line in transitions_block.group(1).splitlines()
            if "->" in line
        )
    )

    current_state = _extract_value_after_label(execution_context, "Current State")
    turn = int(_extract_value_after_label(execution_context, "Turn"))

    if current_state not in states:
        raise ValueError(f"Current state is not defined: {current_state}")

    undefined = {
        name
        for transition in transitions
        for name in (transition.source, transition.target)
        if name not in states
    }
    if undefined:
        names = ", ".join(sorted(undefined))
        raise ValueError(f"Transitions reference undefined states: {names}")

    return StateMachine(
        states=states,
        transitions=transitions,
        current_state=current_state,
        turn=turn,
    )


def render_turn_prompt(context: str) -> str:
    machine = parse_state_machine(context)
    return (
        context.rstrip()
        + "\n\n"
        + "Runtime Harness Note\n\n"
        + f"Current State: {machine.current_state}\n"
        + f"Turn: {machine.turn}\n"
        + "Execute exactly one state and produce the required output format."
    )


def validate_transition(context: str, target: str) -> str:
    machine = parse_state_machine(context)
    verdict = "YES" if machine.is_valid_transition(target) else "NO"
    return f"{machine.current_state} -> {target} valid: {verdict}"


def load_context(path: Path = CONTEXT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Contextual Execution Runtime experiment harness.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("render", help="Render the current one-turn LLM prompt.")

    validate_parser = subparsers.add_parser("validate", help="Validate a transition target.")
    validate_parser.add_argument("target", help="Attempted next state.")

    args = parser.parse_args()
    context = load_context()

    if args.command == "render":
        print(render_turn_prompt(context))
    elif args.command == "validate":
        print(validate_transition(context, args.target))


if __name__ == "__main__":
    main()
