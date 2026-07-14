# context-resident state machine

This is a local research prototype for building state machines whose structure and active state context can be loaded into an LLM prompt.

The app explores whether an LLM can use a visible, context-resident state machine as a lightweight controller:

- The machine definition is rendered as prompt context.
- Each state has its own bound context.
- Only the selected state's context is loaded.
- Valid state changes are defined as associations with reasoning.
- The testing page keeps an ongoing conversation and lets the most recent user turn drive the next state decision.

The older contextual execution runtime experiment is still included in the archived/project files so the starting point is preserved.

## Web Demo

Run the local server, then open `http://127.0.0.1:8000`.

```powershell
python server.py
```

For real OpenAI-backed machine testing, create/edit `.env`:

```text
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4.1-mini
```

Restart `python server.py` after changing `.env`.

The first page lists created machines and lets the user create/select one. The builder page lets the user add named states, bind context to each state, and define associations with transition reasoning.

Machine testing is a separate page. It shows the generated LLM context in a scrollable window, then keeps an ongoing conversation below it. Each user message is sent to the backend OpenAI call with the conversation history, valid next states, and transition reasons. The model returns an assistant message plus a next-state decision; the UI reloads the context when the active state changes.

Durability is backed by SQLite in `context_machines.db`. The database has `machines`, `states`, `associations`, and `documents` tables, with state context stored on each state row.

## Seed A Demo Machine

```powershell
python seed_demo_machine.py
```

This creates a non-trivial customer support triage machine for testing state transitions.

## Documents

The app includes a documents page backed by SQLite. It stores the product overview and the theory behind context-resident state machines.

## Run The Local Checks

```powershell
python -m unittest
```

## Render The Current CER Prompt

```powershell
python experiment_harness.py render
```

## Validate A Transition

```powershell
python experiment_harness.py validate EVALUATE
python experiment_harness.py validate REFINE
```

From the initial `EXPLORE` state, `EVALUATE` is valid and `REFINE` is invalid.

## Manual LLM Experiment

1. Open `experiment_context.md`.
2. Paste the full CER context into an LLM.
3. Ask it to execute exactly one state.
4. Replace only the mutable sections with the model's updated output:
   - `EXECUTION CONTEXT (MUTABLE)`
   - `WORKING OBJECT (MUTABLE)`
   - `EXECUTION HISTORY`
5. Repeat.

The expected loop is:

```text
EXPLORE -> EVALUATE -> REFINE -> EXPLORE
```
