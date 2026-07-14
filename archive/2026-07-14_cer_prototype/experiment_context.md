# Contextual Execution Runtime (CER)
Version: 0.1

==============================================================================
PURPOSE
==============================================================================

This context represents a runtime execution environment embedded entirely
within an LLM context window.

The LLM shall execute exactly one state per interaction.

The runtime consists of:

1. Immutable Program Definition
2. Mutable Execution Context
3. Mutable Working Object
4. Execution History

The goal is to determine whether an LLM can reliably execute against an
explicit runtime model represented solely as context.

==============================================================================
PROGRAM DEFINITION (IMMUTABLE)
==============================================================================

State Machine

States

- EXPLORE
- EVALUATE
- REFINE

Transitions

EXPLORE  -> EVALUATE
EVALUATE -> REFINE
REFINE   -> EXPLORE

------------------------------------------------------------------------------
State Definitions
------------------------------------------------------------------------------

EXPLORE

Purpose

Generate exactly one candidate solution.

Rules

- Produce one proposal.
- Do not critique.
- Do not refine.
- Update only the Proposal section.

--------------------------------

EVALUATE

Purpose

Identify the strongest weakness in the current proposal.

Rules

- Do not create a new proposal.
- Do not improve the proposal.
- Update only the Critique section.

--------------------------------

REFINE

Purpose

Improve the proposal using the existing critique.

Rules

- Modify only the Proposal.
- Preserve the original critique.
- Update only the Revision section.

==============================================================================
EXECUTION INVARIANTS
==============================================================================

The following conditions must always remain true.

1. Exactly one state executes per turn.
2. Exactly one transition occurs per turn.
3. Only valid transitions may occur.
4. The current state must always belong to the defined state set.
5. The Program Definition is immutable.
6. The Working Object persists across turns.
7. Only the active state's owned fields may be modified.

==============================================================================
EXECUTION CONTEXT (MUTABLE)
==============================================================================

Current State

EXPLORE

Turn

1

==============================================================================
WORKING OBJECT (MUTABLE)
==============================================================================

Proposal

None

Critique

None

Revision

None

==============================================================================
EXECUTION HISTORY
==============================================================================

(empty)

==============================================================================
EXECUTION PROCEDURE
==============================================================================

Perform the following steps exactly once.

Step 1

Read the Current State.

Step 2

Execute only the instructions for that state.

Step 3

Update only the fields owned by that state.

Step 4

Validate that the next transition is legal.

Step 5

Update the Current State.

Step 6

Append a record to the Execution History.

==============================================================================
OUTPUT FORMAT
==============================================================================

Executed State

<state>

Modified Fields

<list>

Working Object

Proposal:
...

Critique:
...

Revision:
...

Transition

<from> -> <to>

Transition Valid

YES or NO

Updated Current State

<state>

Execution History Entry

Turn:
Executed State:
Modified Fields:
Transition:

==============================================================================
TURN INSTRUCTION
==============================================================================

Execute exactly one state from the current runtime context.

==============================================================================
END RUNTIME
==============================================================================
