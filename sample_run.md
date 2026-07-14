# Sample CER Experiment Run

This sample shows the expected shape of three manual LLM turns. The exact proposal text may vary; the important behavior is that only the active state's owned fields are modified and each transition is explicit and valid.

## Turn 1

```text
Executed State

EXPLORE

Modified Fields

Proposal

Working Object

Proposal:
Embed the state machine, execution context, working object, and history in a single structured prompt, then require the model to execute exactly one state per turn.

Critique:
None

Revision:
None

Transition

EXPLORE -> EVALUATE

Transition Valid

YES

Updated Current State

EVALUATE

Execution History Entry

Turn: 1
Executed State: EXPLORE
Modified Fields: Proposal
Transition: EXPLORE -> EVALUATE
```

## Turn 2

```text
Executed State

EVALUATE

Modified Fields

Critique

Working Object

Proposal:
Embed the state machine, execution context, working object, and history in a single structured prompt, then require the model to execute exactly one state per turn.

Critique:
The proposal depends on the model preserving runtime boundaries without accidentally modifying immutable or inactive sections.

Revision:
None

Transition

EVALUATE -> REFINE

Transition Valid

YES

Updated Current State

REFINE

Execution History Entry

Turn: 2
Executed State: EVALUATE
Modified Fields: Critique
Transition: EVALUATE -> REFINE
```

## Turn 3

```text
Executed State

REFINE

Modified Fields

Proposal, Revision

Working Object

Proposal:
Embed the state machine, execution context, working object, and history in a single structured prompt, require the model to execute exactly one state per turn, and compare each turn against the invariants before accepting mutable updates.

Critique:
The proposal depends on the model preserving runtime boundaries without accidentally modifying immutable or inactive sections.

Revision:
Added an explicit invariant check before accepting mutable updates.

Transition

REFINE -> EXPLORE

Transition Valid

YES

Updated Current State

EXPLORE

Execution History Entry

Turn: 3
Executed State: REFINE
Modified Fields: Proposal, Revision
Transition: REFINE -> EXPLORE
```
