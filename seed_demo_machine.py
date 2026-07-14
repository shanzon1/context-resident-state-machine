import sqlite3
from pathlib import Path

import server


DB_PATH = Path(__file__).resolve().parent / "context_machines.db"


MACHINE_NAME = "Customer Support Triage"


STATES = [
    (
        "Intake",
        "Capture the customer's issue in plain language. Identify the product area, urgency, affected account, and the outcome the customer wants. Do not diagnose yet.",
    ),
    (
        "Clarify",
        "Ask for the smallest missing detail needed to continue. Prefer one precise question over a long checklist.",
    ),
    (
        "Diagnose",
        "Reason about likely causes using the available details. Produce one most likely cause and one alternative cause.",
    ),
    (
        "Resolve",
        "Give the customer a clear next action or fix. Keep it actionable and avoid internal jargon.",
    ),
    (
        "Escalate",
        "Prepare an escalation summary for a human specialist. Include customer impact, evidence gathered, attempted resolution, and why escalation is needed.",
    ),
    (
        "Close",
        "Summarize the outcome, confirm the customer has a path forward, and state what was learned for future support.",
    ),
]


ASSOCIATIONS = [
    ("Intake", "Clarify", "the issue lacks required details such as product area, error message, account, or urgency"),
    ("Intake", "Diagnose", "the issue has enough detail to infer likely causes"),
    ("Clarify", "Diagnose", "the missing detail has been supplied and the issue can now be reasoned about"),
    ("Diagnose", "Resolve", "the likely cause has a known customer-facing fix or workaround"),
    ("Diagnose", "Escalate", "the cause is unclear, risky, account-specific, or requires privileged access"),
    ("Resolve", "Close", "the customer has a concrete answer or next step"),
    ("Resolve", "Escalate", "the proposed fix fails or reveals a deeper system/account problem"),
    ("Escalate", "Close", "the escalation package is complete and ready for handoff"),
]


def main() -> None:
    server.init_db()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("DELETE FROM machines WHERE name = ?", (MACHINE_NAME,))
        cursor = db.execute("INSERT INTO machines (name) VALUES (?)", (MACHINE_NAME,))
        machine_id = cursor.lastrowid

        state_ids = {}
        for position, (name, context) in enumerate(STATES):
            cursor = db.execute(
                """
                INSERT INTO states (machine_id, name, context, position)
                VALUES (?, ?, ?, ?)
                """,
                (machine_id, name, context, position),
            )
            state_ids[name] = cursor.lastrowid

        db.execute(
            "UPDATE machines SET selected_state_id = ? WHERE id = ?",
            (state_ids["Intake"], machine_id),
        )

        for from_name, to_name, reason in ASSOCIATIONS:
            db.execute(
                """
                INSERT INTO associations (machine_id, from_state_id, to_state_id, reason)
                VALUES (?, ?, ?, ?)
                """,
                (machine_id, state_ids[from_name], state_ids[to_name], reason),
            )

        db.commit()

    print(f"Seeded {MACHINE_NAME}")


if __name__ == "__main__":
    main()
