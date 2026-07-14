# Context State Machine Prototype

## Objective

Build a minimal prototype that demonstrates whether an LLM can use a state machine embedded directly in its context as a lightweight execution controller.

This is a research prototype, not a production implementation.

---

# Goal

Represent a finite state machine entirely as text within the LLM context.

The context should contain:

- State definitions
- Valid transitions
- Current state
- State-specific instructions
- A working object

The LLM should execute behavior based solely on the current state.

---

# Scope

Keep the implementation extremely small.

Do NOT build:

- Agent framework
- Workflow engine
- Database
- Persistence layer
- Authentication
- Scheduling
- Tool execution
- UI beyond a simple demo

Only prove the concept.

---

# Functional Requirements

## 1. State Machine Definition

Represent a state machine in a simple human-readable format.

Example:

```text
States:
EXPLORE
EVALUATE
REFINE

Transitions:
EXPLORE -> EVALUATE
EVALUATE -> REFINE
REFINE -> EXPLORE

Current State:
EXPLORE
```

The format should be easy for both humans and the LLM to read.

---

## 2. State Metadata

Each state contains:

- name
- description
- execution instructions

Example:

```text
State: EXPLORE

Purpose:
Generate one new idea.

Instructions:
Generate exactly one candidate solution.
Do not critique it.
```

---

## 3. Working Object

Maintain a shared object that is modified over time.

Example:

```text
Working Object:

Current proposal:
...
```

The object should survive state transitions.

---

## 4. Execution

Given:

- current state
- state definition
- working object

the LLM should:

1. Read the current state.
2. Execute only that state's instructions.
3. Update the working object.
4. Determine the next valid state.
5. Output the updated state.

---

## 5. Transition Validation

Only transitions explicitly defined by the state machine are allowed.

If an invalid transition is attempted, it should be reported instead of executed.

---

## 6. Demonstration

Create a simple demonstration using three states.

EXPLORE

Generate one idea.

↓

EVALUATE

Identify the strongest weakness.

↓

REFINE

Improve the idea.

↓

Repeat.

---

# Non-Goals

Do not implement:

- AI planning
- Autonomous agents
- Memory systems
- Vector search
- RAG
- Multi-agent communication
- Parallel execution
- External APIs

These are intentionally excluded.

---

# Architecture

Keep the architecture simple.

Suggested components:

StateMachine
State
Transition
WorkingObject
Executor

No additional abstraction unless clearly necessary.

---

# Success Criteria

The prototype is successful if:

- A state machine can exist entirely inside prompt/context.
- The LLM consistently executes the correct state's behavior.
- The working object evolves correctly.
- State transitions remain valid.
- The current state can be updated and reused in subsequent prompts.

---

# Future Research (Out of Scope)

Potential future extensions include:

- Hierarchical state machines
- Nested workflows
- Dynamic state generation
- Context module loading
- Agent orchestration
- Tool routing
- Context compression
- Planning systems
- Graph-based execution
- Reflection loops

Do not implement these yet.

---

# Design Philosophy

The objective is to determine whether a simple textual state machine can act as a deterministic control layer over an LLM.

Prefer clarity over flexibility.

Prefer simplicity over completeness.

If a feature does not directly help answer the research question, it should not be included.