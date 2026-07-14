# Contextual Execution Runtime Experiment

This is a minimal research prototype based on `requirements_2.md`.

It tests whether an LLM can reliably execute against an explicit runtime model represented solely as context. The runtime is stored in `experiment_context.md` and contains:

- Immutable Program Definition
- Mutable Execution Context
- Mutable Working Object
- Execution History

The harness stays deliberately small. It parses the state machine, validates transitions, and renders the current turn prompt. It does not execute the state logic for the LLM.

## Web Demo

Open `index.html` in a browser to try a simulated OpenAI API flow. The page shows the full CER context, accepts user input, executes one simulated state per submit, and displays the updated state, working object, and execution history.

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
