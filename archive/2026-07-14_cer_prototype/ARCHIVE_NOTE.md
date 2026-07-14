# Archived CER Prototype

Archived on 2026-07-14.

This snapshot preserves the initial Contextual Execution Runtime experiment and static website.

It includes:

- Original requirements in `requirements.md`
- CER requirements in `requirements_2.md`
- Fixed CER runtime context in `experiment_context.md`
- Python harness and tests
- Static simulated web demo in `index.html`, `styles.css`, and `app.js`

Reason for archive:

The project direction shifted from a fixed CER prototype to a product/builder split:

- First screen: user defines the state machine and per-state prompt context.
- Runtime screen: app inserts that generated state machine into prompt context and shows state changes during execution.

