from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import server


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "context_machines.db"
FIXTURE_PATH = ROOT / "fixtures" / "demo_state_machines.json"


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def export_fixture(path: Path = FIXTURE_PATH) -> None:
    server.init_db()
    path.parent.mkdir(parents=True, exist_ok=True)

    with connect() as db:
        machines = []
        for machine in db.execute(
            "SELECT id, name, selected_state_id FROM machines ORDER BY id"
        ):
            states = [
                {
                    "name": row["name"],
                    "context": row["context"],
                    "position": row["position"],
                    "selected": row["id"] == machine["selected_state_id"],
                }
                for row in db.execute(
                    """
                    SELECT id, name, context, position
                    FROM states
                    WHERE machine_id = ?
                    ORDER BY position, id
                    """,
                    (machine["id"],),
                )
            ]
            state_names = {
                row["id"]: row["name"]
                for row in db.execute(
                    "SELECT id, name FROM states WHERE machine_id = ?",
                    (machine["id"],),
                )
            }
            associations = [
                {
                    "from": state_names[row["from_state_id"]],
                    "to": state_names[row["to_state_id"]],
                    "reason": row["reason"],
                }
                for row in db.execute(
                    """
                    SELECT from_state_id, to_state_id, reason
                    FROM associations
                    WHERE machine_id = ?
                    ORDER BY id
                    """,
                    (machine["id"],),
                )
            ]
            sessions = export_sessions(db, machine["id"], state_names)
            machines.append(
                {
                    "name": machine["name"],
                    "states": states,
                    "associations": associations,
                    "testSessions": sessions,
                }
            )

    path.write_text(json.dumps({"version": 1, "machines": machines}, indent=2), encoding="utf-8")
    print(f"Exported {len(machines)} machines to {path}")


def export_sessions(
    db: sqlite3.Connection,
    machine_id: int,
    state_names: dict[int, str],
) -> list[dict]:
    sessions = []
    for session in db.execute(
        """
        SELECT id, title, initial_state_id, current_state_id, started_at, updated_at
        FROM test_sessions
        WHERE machine_id = ?
        ORDER BY id
        """,
        (machine_id,),
    ):
        messages = [
            {
                "role": row["role"],
                "content": row["content"],
                "stateBefore": state_names.get(row["state_before_id"]),
                "stateAfter": state_names.get(row["state_after_id"]),
                "stateReason": row["state_reason"],
                "model": row["model"],
                "rawResponse": row["raw_response"],
                "createdAt": row["created_at"],
            }
            for row in db.execute(
                """
                SELECT
                    role,
                    content,
                    state_before_id,
                    state_after_id,
                    state_reason,
                    model,
                    raw_response,
                    created_at
                FROM test_messages
                WHERE session_id = ?
                ORDER BY id
                """,
                (session["id"],),
            )
        ]
        sessions.append(
            {
                "title": session["title"],
                "initialState": state_names.get(session["initial_state_id"]),
                "currentState": state_names.get(session["current_state_id"]),
                "startedAt": session["started_at"],
                "updatedAt": session["updated_at"],
                "messages": messages,
            }
        )
    return sessions


def load_fixture(path: Path = FIXTURE_PATH) -> None:
    server.init_db()
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture_data(data)

    with connect() as db:
        for machine in data["machines"]:
            db.execute("DELETE FROM machines WHERE name = ?", (machine["name"],))
            cursor = db.execute("INSERT INTO machines (name) VALUES (?)", (machine["name"],))
            machine_id = cursor.lastrowid

            state_ids = {}
            selected_state_id = None
            for state in machine["states"]:
                cursor = db.execute(
                    """
                    INSERT INTO states (machine_id, name, context, position)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        machine_id,
                        state["name"],
                        state["context"],
                        state.get("position", len(state_ids)),
                    ),
                )
                state_ids[state["name"]] = cursor.lastrowid
                if state.get("selected"):
                    selected_state_id = cursor.lastrowid

            db.execute(
                "UPDATE machines SET selected_state_id = ? WHERE id = ?",
                (selected_state_id or next(iter(state_ids.values()), None), machine_id),
            )

            for association in machine["associations"]:
                db.execute(
                    """
                    INSERT INTO associations (machine_id, from_state_id, to_state_id, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        machine_id,
                        state_ids[association["from"]],
                        state_ids[association["to"]],
                        association["reason"],
                    ),
                )

            for session in machine.get("testSessions", []):
                cursor = db.execute(
                    """
                    INSERT INTO test_sessions
                        (machine_id, title, initial_state_id, current_state_id, started_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        machine_id,
                        session["title"],
                        state_ids.get(session.get("initialState")),
                        state_ids.get(session.get("currentState")),
                        session.get("startedAt"),
                        session.get("updatedAt"),
                    ),
                )
                session_id = cursor.lastrowid
                for message in session.get("messages", []):
                    db.execute(
                        """
                        INSERT INTO test_messages
                            (
                                session_id,
                                role,
                                content,
                                state_before_id,
                                state_after_id,
                                state_reason,
                                model,
                                raw_response,
                                created_at
                            )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            message["role"],
                            message["content"],
                            state_ids.get(message.get("stateBefore")),
                            state_ids.get(message.get("stateAfter")),
                            message.get("stateReason"),
                            message.get("model"),
                            message.get("rawResponse"),
                            message.get("createdAt"),
                        ),
                    )

        db.commit()

    print(f"Loaded {len(data['machines'])} machines from {path}")


def validate_fixture(path: Path = FIXTURE_PATH) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_fixture_data(data)
    machine_count = len(data["machines"])
    session_count = sum(len(machine.get("testSessions", [])) for machine in data["machines"])
    message_count = sum(
        len(session.get("messages", []))
        for machine in data["machines"]
        for session in machine.get("testSessions", [])
    )
    print(
        f"Fixture valid: {machine_count} machines, {session_count} sessions, {message_count} messages"
    )


def validate_fixture_data(data: dict) -> None:
    if data.get("version") != 1:
        raise ValueError("Unsupported fixture version")

    machine_names = set()
    for machine in data.get("machines", []):
        name = machine.get("name")
        if not name:
            raise ValueError("Machine is missing a name")
        if name in machine_names:
            raise ValueError(f"Duplicate machine: {name}")
        machine_names.add(name)

        state_names = [state.get("name") for state in machine.get("states", [])]
        if not state_names or any(not state for state in state_names):
            raise ValueError(f"{name}: every machine needs named states")
        if len(state_names) != len(set(state_names)):
            raise ValueError(f"{name}: duplicate state names")
        state_set = set(state_names)

        for association in machine.get("associations", []):
            if association.get("from") not in state_set:
                raise ValueError(f"{name}: association has unknown from-state")
            if association.get("to") not in state_set:
                raise ValueError(f"{name}: association has unknown to-state")
            if not association.get("reason"):
                raise ValueError(f"{name}: association is missing a reason")

        for session in machine.get("testSessions", []):
            for key in ("initialState", "currentState"):
                if session.get(key) and session[key] not in state_set:
                    raise ValueError(f"{name}: session references unknown {key}")
            messages = session.get("messages", [])
            if len(messages) % 2 != 0:
                raise ValueError(f"{name}: transcript should have user/assistant message pairs")
            for message in messages:
                if message.get("role") not in {"user", "assistant"}:
                    raise ValueError(f"{name}: invalid message role")
                for key in ("stateBefore", "stateAfter"):
                    if message.get(key) and message[key] not in state_set:
                        raise ValueError(f"{name}: message references unknown {key}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export, load, or validate demo data.")
    parser.add_argument("command", choices=["export", "load", "validate"])
    parser.add_argument("--path", type=Path, default=FIXTURE_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "export":
        export_fixture(args.path)
    elif args.command == "load":
        load_fixture(args.path)
    elif args.command == "validate":
        validate_fixture(args.path)


if __name__ == "__main__":
    main()
