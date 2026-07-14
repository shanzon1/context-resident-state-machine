const programDefinition = `==============================================================================
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
7. Only the active state's owned fields may be modified.`;

const transitions = {
  EXPLORE: "EVALUATE",
  EVALUATE: "REFINE",
  REFINE: "EXPLORE",
};

const initialRuntime = {
  state: "EXPLORE",
  turn: 1,
  proposal: "None",
  critique: "None",
  revision: "None",
  history: [],
};

let runtime = { ...initialRuntime, history: [] };

const contextView = document.querySelector("#contextView");
const responseView = document.querySelector("#responseView");
const form = document.querySelector("#runtimeForm");
const userInput = document.querySelector("#userInput");
const resetButton = document.querySelector("#resetButton");
const currentStateValue = document.querySelector("#currentStateValue");
const transitionValue = document.querySelector("#transitionValue");
const turnValue = document.querySelector("#turnValue");
const proposalValue = document.querySelector("#proposalValue");
const critiqueValue = document.querySelector("#critiqueValue");
const revisionValue = document.querySelector("#revisionValue");
const historyList = document.querySelector("#historyList");

function normalizeInput(value) {
  const trimmed = value.trim();
  return trimmed || "Test whether context alone can control one LLM state transition.";
}

function renderContext() {
  const historyText = runtime.history.length
    ? runtime.history
        .map(
          (entry) => `Turn: ${entry.turn}
Executed State: ${entry.executedState}
Modified Fields: ${entry.modifiedFields.join(", ")}
Transition: ${entry.transition}`
        )
        .join("\n\n")
    : "(empty)";

  return `# Contextual Execution Runtime (CER)
Version: 0.1

${programDefinition}

==============================================================================
EXECUTION CONTEXT (MUTABLE)
==============================================================================

Current State

${runtime.state}

Turn

${runtime.turn}

==============================================================================
WORKING OBJECT (MUTABLE)
==============================================================================

Proposal

${runtime.proposal}

Critique

${runtime.critique}

Revision

${runtime.revision}

==============================================================================
EXECUTION HISTORY
==============================================================================

${historyText}

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
==============================================================================`;
}

function simulateOpenAIResponse(input) {
  const executedState = runtime.state;
  const nextState = transitions[executedState];
  const modifiedFields = [];
  let proposal = runtime.proposal;
  let critique = runtime.critique;
  let revision = runtime.revision;

  if (executedState === "EXPLORE") {
    proposal = `Use "${input}" as the seed for a one-turn CER experiment where the LLM updates only the active state's owned field.`;
    modifiedFields.push("Proposal");
  }

  if (executedState === "EVALUATE") {
    critique = "The experiment still relies on the model faithfully preserving immutable sections while changing mutable sections.";
    modifiedFields.push("Critique");
  }

  if (executedState === "REFINE") {
    revision = "Added an explicit visible state trace so each accepted transition can be inspected after every simulated API call.";
    proposal = `${runtime.proposal} The page now displays the current state, transition, working object, and execution history after each turn.`;
    modifiedFields.push("Proposal", "Revision");
  }

  const transition = `${executedState} -> ${nextState}`;

  return {
    executedState,
    modifiedFields,
    proposal,
    critique,
    revision,
    transition,
    transitionValid: "YES",
    updatedCurrentState: nextState,
    historyEntry: {
      turn: runtime.turn,
      executedState,
      modifiedFields,
      transition,
    },
  };
}

function formatResponse(response) {
  return `Executed State

${response.executedState}

Modified Fields

${response.modifiedFields.join(", ")}

Working Object

Proposal:
${response.proposal}

Critique:
${response.critique}

Revision:
${response.revision}

Transition

${response.transition}

Transition Valid

${response.transitionValid}

Updated Current State

${response.updatedCurrentState}

Execution History Entry

Turn: ${response.historyEntry.turn}
Executed State: ${response.historyEntry.executedState}
Modified Fields: ${response.historyEntry.modifiedFields.join(", ")}
Transition: ${response.historyEntry.transition}`;
}

function applyResponse(response) {
  runtime = {
    state: response.updatedCurrentState,
    turn: runtime.turn + 1,
    proposal: response.proposal,
    critique: response.critique,
    revision: response.revision,
    history: [...runtime.history, response.historyEntry],
  };
}

function render() {
  contextView.textContent = renderContext();
  currentStateValue.textContent = runtime.state;
  transitionValue.textContent = `${runtime.state} -> ${transitions[runtime.state]}`;
  turnValue.textContent = runtime.turn;
  proposalValue.textContent = runtime.proposal;
  critiqueValue.textContent = runtime.critique;
  revisionValue.textContent = runtime.revision;

  document.querySelectorAll("[data-state-node]").forEach((node) => {
    node.classList.toggle("active", node.dataset.stateNode === runtime.state);
  });

  historyList.innerHTML = "";
  runtime.history.forEach((entry) => {
    const item = document.createElement("li");
    item.innerHTML = `<strong>${entry.transition}</strong><span>Turn ${entry.turn}; modified ${entry.modifiedFields.join(", ")}</span>`;
    historyList.appendChild(item);
  });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const input = normalizeInput(userInput.value);
  const response = simulateOpenAIResponse(input);
  responseView.textContent = formatResponse(response);
  applyResponse(response);
  render();
});

resetButton.addEventListener("click", () => {
  runtime = { ...initialRuntime, history: [] };
  userInput.value = "";
  responseView.textContent = "No response yet.";
  render();
});

render();
