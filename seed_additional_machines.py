import sqlite3
from pathlib import Path

import server


DB_PATH = Path(__file__).resolve().parent / "context_machines.db"


MACHINES = [
    {
        "name": "Product Return Authorization",
        "states": [
            (
                "Receive",
                "Capture the customer's return request. Identify the order, product, reason, timing, condition, and requested outcome. Do not decide eligibility yet.",
            ),
            (
                "Validate",
                "Check whether the request has enough information to evaluate policy eligibility. Ask only for missing facts needed to continue.",
            ),
            (
                "Assess",
                "Evaluate the request against return policy signals: purchase date, item category, condition, defect claims, and proof of purchase.",
            ),
            (
                "Approve",
                "Approve the return and provide clear next steps for shipping, refund timing, replacement, or store credit.",
            ),
            (
                "Deny",
                "Decline the return respectfully. Explain the policy reason and offer alternatives when appropriate.",
            ),
            (
                "Escalate",
                "Prepare a human review package for edge cases, high-value orders, fraud concerns, or policy exceptions.",
            ),
            (
                "Close",
                "Summarize the decision, next step, and any follow-up the customer should expect.",
            ),
        ],
        "associations": [
            ("Receive", "Validate", "the request lacks order, product, timing, condition, or requested outcome details"),
            ("Receive", "Assess", "the request includes enough order and product details to evaluate eligibility"),
            ("Validate", "Assess", "missing facts have been supplied and policy eligibility can now be evaluated"),
            ("Assess", "Approve", "the request appears eligible under the return policy"),
            ("Assess", "Deny", "the request clearly violates return policy and no exception is indicated"),
            ("Assess", "Escalate", "the request involves an exception, high-value item, fraud signal, or unclear policy edge"),
            ("Approve", "Close", "the customer has return authorization and concrete next steps"),
            ("Deny", "Close", "the customer has a clear policy explanation and alternatives"),
            ("Escalate", "Close", "the human review package is complete and ready for handoff"),
        ],
    },
    {
        "name": "Event Incident Response",
        "states": [
            (
                "Report",
                "Capture the incident report in plain language. Identify what happened, where, who is affected, urgency, and immediate safety concerns.",
            ),
            (
                "Clarify",
                "Ask for the smallest missing detail needed to classify severity and choose a response path.",
            ),
            (
                "Classify",
                "Classify severity and incident type using available details. Distinguish safety, facilities, attendee conduct, technical, and logistics issues.",
            ),
            (
                "Respond",
                "Provide immediate response actions appropriate for the incident type. Keep actions concrete and time-sensitive.",
            ),
            (
                "Escalate",
                "Prepare an escalation summary for security, medical, venue operations, or event leadership.",
            ),
            (
                "Document",
                "Record the incident facts, response taken, unresolved risks, and required follow-up.",
            ),
            (
                "Close",
                "Confirm the incident has a resolution path and summarize what should be monitored next.",
            ),
        ],
        "associations": [
            ("Report", "Clarify", "the incident lacks location, affected people, severity, or immediate risk details"),
            ("Report", "Classify", "the incident report includes enough facts to classify severity and type"),
            ("Clarify", "Classify", "missing incident facts have been supplied"),
            ("Classify", "Respond", "the incident can be handled with standard immediate response actions"),
            ("Classify", "Escalate", "the incident involves safety risk, medical need, security concern, or leadership decision"),
            ("Respond", "Document", "initial response actions have been provided and the event record should be updated"),
            ("Respond", "Escalate", "the response reveals continuing risk or requires authority beyond the operator"),
            ("Escalate", "Document", "the escalation package has enough detail for handoff and recordkeeping"),
            ("Document", "Close", "the incident facts and follow-up have been captured"),
        ],
    },
]


def seed_machine(db: sqlite3.Connection, machine: dict) -> None:
    db.execute("DELETE FROM machines WHERE name = ?", (machine["name"],))
    cursor = db.execute("INSERT INTO machines (name) VALUES (?)", (machine["name"],))
    machine_id = cursor.lastrowid

    state_ids = {}
    for position, (name, context) in enumerate(machine["states"]):
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
        (state_ids[machine["states"][0][0]], machine_id),
    )

    for from_name, to_name, reason in machine["associations"]:
        db.execute(
            """
            INSERT INTO associations (machine_id, from_state_id, to_state_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (machine_id, state_ids[from_name], state_ids[to_name], reason),
        )


def main() -> None:
    server.init_db()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("PRAGMA foreign_keys = ON")
        for machine in MACHINES:
            seed_machine(db, machine)
        db.commit()

    for machine in MACHINES:
        print(f"Seeded {machine['name']}")


if __name__ == "__main__":
    main()
