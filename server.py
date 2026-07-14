from __future__ import annotations

import json
import mimetypes
import os
import sqlite3
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "context_machines.db"
ENV_PATH = ROOT / ".env"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def load_env() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def extract_response_text(result: dict) -> str:
    if result.get("output_text"):
        return result["output_text"]

    chunks: list[str] = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])

    return "\n".join(chunks).strip()


def parse_machine_test_output(
    text: str,
    states: list[dict],
    fallback_state_id: int | None,
    valid_next_ids: set,
) -> dict:
    state_by_id = {state["id"]: state for state in states}
    fallback_state = state_by_id.get(fallback_state_id) or (states[0] if states else None)
    cleaned_text = text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        if cleaned_text.lower().startswith("json"):
            cleaned_text = cleaned_text[4:].strip()

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError:
        return {
            "assistantMessage": text,
            "nextStateId": fallback_state["id"] if fallback_state else None,
            "nextStateName": fallback_state["name"] if fallback_state else "none",
            "stateReason": "The model did not return a structured state decision.",
        }

    state_by_name = {state["name"].lower(): state for state in states}
    requested_state = parsed.get("nextStateId")
    if isinstance(requested_state, str) and requested_state.isdigit():
        requested_state = int(requested_state)
    next_state = state_by_id.get(requested_state)

    if not next_state and parsed.get("nextStateName"):
        next_state = state_by_name.get(str(parsed["nextStateName"]).lower())

    if next_state and next_state["id"] not in valid_next_ids:
        next_state = fallback_state

    if not next_state:
        next_state = fallback_state

    return {
        "assistantMessage": str(parsed.get("assistantMessage", "")).strip() or text,
        "nextStateId": next_state["id"] if next_state else None,
        "nextStateName": next_state["name"] if next_state else "none",
        "stateReason": str(parsed.get("stateReason", "")).strip(),
    }


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                selected_state_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                context TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                from_state_id INTEGER NOT NULL,
                to_state_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(machine_id, from_state_id, to_state_id),
                FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
                FOREIGN KEY (from_state_id) REFERENCES states(id) ON DELETE CASCADE,
                FOREIGN KEY (to_state_id) REFERENCES states(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.execute(
            """
            INSERT OR IGNORE INTO documents (title, body)
            VALUES (?, ?)
            """,
            (
                "Context-resident state machine overview",
                """# Context-resident state machine

This application helps users create state machines whose control structure can live directly inside an LLM context window.

The app is organized into three working areas:

1. Machine Library
Users create and select durable state machines. Machines are stored in SQLite.

2. Builder
Users define states, bind context to each state, and define valid associations between states. Each association includes reasoning that tells the LLM why that transition should be selected.

3. Machine Testing
Users inspect the generated LLM context in a scrollable window and provide a user prompt below it. This page is where the OpenAI API call can be attached later.

                The key product idea is that the LLM can read a textual machine definition, load only the selected state's context, and use transition reasoning to determine a valid next state.""",
            ),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO documents (title, body)
            VALUES (?, ?)
            """,
            (
                "Theory of context-resident state machines",
                """# Theory of context-resident state machines

This project explores whether an LLM can be controlled by a state machine that lives in its context instead of by hidden application logic.

The central hypothesis is:

Can a structured, human-readable state machine embedded in prompt context act as a lightweight execution controller for an LLM?

Core ideas:

1. State machine as text
The machine definition is rendered into the LLM context, not only stored in application code.

2. States have bound context
Each state owns a context fragment or instruction set.

3. Only one state context is loaded
At any moment, the LLM sees the machine plus the currently active state's context.

4. Transitions are explicit
The LLM is only allowed to move along defined associations.

5. Transitions have reasoning
When more than one transition is valid, the context includes reasons for choosing one next state over another.

6. Testing separates execution from design
The builder defines the machine. The testing page shows what the LLM would receive, plus a user prompt.

7. Durability matters
SQLite stores machines, states, associations, documents, and eventually test runs.

The product goal is to let users design these machines without requiring implementation language like nodes, edges, orchestration frameworks, or hidden workflow code.""",
            ),
        )
        db.commit()


def machine_payload(db: sqlite3.Connection) -> list[dict]:
    machines = [
        {
            "id": row["id"],
            "name": row["name"],
            "selectedStateId": row["selected_state_id"],
            "states": [],
            "associations": [],
        }
        for row in db.execute("SELECT id, name, selected_state_id FROM machines ORDER BY id")
    ]
    by_id = {machine["id"]: machine for machine in machines}

    for row in db.execute(
        "SELECT id, machine_id, name, context FROM states ORDER BY machine_id, position, id"
    ):
        by_id[row["machine_id"]]["states"].append(
            {
                "id": row["id"],
                "name": row["name"],
                "context": row["context"],
            }
        )

    for row in db.execute(
        """
        SELECT id, machine_id, from_state_id, to_state_id, reason
        FROM associations
        ORDER BY machine_id, id
        """
    ):
        by_id[row["machine_id"]]["associations"].append(
            {
                "id": row["id"],
                "from": row["from_state_id"],
                "to": row["to_state_id"],
                "reason": row["reason"],
            }
        )

    for machine in machines:
        state_ids = {state["id"] for state in machine["states"]}
        if machine["selectedStateId"] not in state_ids:
            machine["selectedStateId"] = machine["states"][0]["id"] if machine["states"] else None

    return machines


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/machines":
            with connect() as db:
                self.send_json(machine_payload(db))
            return

        if self.path == "/api/documents":
            with connect() as db:
                documents = [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "body": row["body"],
                        "updatedAt": row["updated_at"],
                    }
                    for row in db.execute(
                        "SELECT id, title, body, updated_at FROM documents ORDER BY id"
                    )
                ]
                self.send_json(documents)
            return

        self.serve_static()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self.read_json()

        if path == "/api/machines":
            name = body.get("name", "").strip()
            if not name:
                self.send_error_json(400, "Machine name is required")
                return
            with connect() as db:
                cursor = db.execute("INSERT INTO machines (name) VALUES (?)", (name,))
                db.commit()
                self.send_json({"id": cursor.lastrowid}, 201)
            return

        if path == "/api/machine-test":
            self.run_machine_test(body)
            return

        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "machines"] and parts[3] == "states":
            self.create_state(int(parts[2]), body)
            return

        if len(parts) == 4 and parts[:2] == ["api", "machines"] and parts[3] == "associations":
            self.create_association(int(parts[2]), body)
            return

        self.send_error_json(404, "Not found")

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "machines"] and parts[3] == "selected-state":
            body = self.read_json()
            with connect() as db:
                db.execute(
                    "UPDATE machines SET selected_state_id = ? WHERE id = ?",
                    (body.get("selectedStateId"), int(parts[2])),
                )
                db.commit()
            self.send_json({"ok": True})
            return

        self.send_error_json(404, "Not found")

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/machines":
            with connect() as db:
                db.execute("DELETE FROM machines")
                db.commit()
            self.send_json({"ok": True})
            return

        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "states"]:
            with connect() as db:
                db.execute("DELETE FROM states WHERE id = ?", (int(parts[2]),))
                db.execute(
                    """
                    UPDATE machines
                    SET selected_state_id = (
                        SELECT id FROM states
                        WHERE machine_id = machines.id
                        ORDER BY position, id
                        LIMIT 1
                    )
                    WHERE selected_state_id NOT IN (SELECT id FROM states)
                    """
                )
                db.commit()
            self.send_json({"ok": True})
            return

        if len(parts) == 3 and parts[:2] == ["api", "associations"]:
            with connect() as db:
                db.execute("DELETE FROM associations WHERE id = ?", (int(parts[2]),))
                db.commit()
            self.send_json({"ok": True})
            return

        self.send_error_json(404, "Not found")

    def create_state(self, machine_id: int, body: dict) -> None:
        name = body.get("name", "").strip()
        context = body.get("context", "").strip()
        if not name or not context:
            self.send_error_json(400, "State name and context are required")
            return

        with connect() as db:
            position = db.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM states WHERE machine_id = ?",
                (machine_id,),
            ).fetchone()[0]
            cursor = db.execute(
                "INSERT INTO states (machine_id, name, context, position) VALUES (?, ?, ?, ?)",
                (machine_id, name, context, position),
            )
            db.execute(
                "UPDATE machines SET selected_state_id = ? WHERE id = ?",
                (cursor.lastrowid, machine_id),
            )
            db.commit()
            self.send_json({"id": cursor.lastrowid}, 201)

    def create_association(self, machine_id: int, body: dict) -> None:
        from_state_id = body.get("from")
        to_state_id = body.get("to")
        reason = body.get("reason", "").strip() or "Use this transition when its destination is the best next state."
        if not from_state_id or not to_state_id or from_state_id == to_state_id:
            self.send_error_json(400, "A valid from-state and to-state are required")
            return

        with connect() as db:
            db.execute(
                """
                INSERT OR IGNORE INTO associations (machine_id, from_state_id, to_state_id, reason)
                VALUES (?, ?, ?, ?)
                """,
                (machine_id, from_state_id, to_state_id, reason),
            )
            db.commit()
            self.send_json({"ok": True}, 201)

    def run_machine_test(self, body: dict) -> None:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            self.send_error_json(400, "OPENAI_API_KEY is missing. Add it to .env and restart the server.")
            return

        context = body.get("context", "").strip()
        user_prompt = body.get("userPrompt", "").strip()
        states = body.get("states", [])
        associations = body.get("associations", [])
        current_state_id = body.get("currentStateId")
        conversation = body.get("conversation", [])
        model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini").strip()

        if not context or not user_prompt:
            self.send_error_json(400, "Context and user prompt are required")
            return

        valid_state_ids = {state.get("id") for state in states}
        current_state = next((state for state in states if state.get("id") == current_state_id), None)
        valid_next_ids = {
            association.get("to")
            for association in associations
            if association.get("from") == current_state_id
        }
        if current_state_id in valid_state_ids:
            valid_next_ids.add(current_state_id)

        valid_next_states = [
            {"id": state.get("id"), "name": state.get("name")}
            for state in states
            if state.get("id") in valid_next_ids
        ]
        transition_options = [
            {
                "from": association.get("from"),
                "to": association.get("to"),
                "reason": association.get("reason"),
            }
            for association in associations
            if association.get("from") == current_state_id
        ]
        transcript = "\n".join(
            f"{turn.get('role', 'unknown')}: {turn.get('content', '')}"
            for turn in conversation[-12:]
        )
        decision_prompt = f"""Conversation transcript:
{transcript or "(no prior conversation)"}

Most recent user message:
{user_prompt}

Current state:
{json.dumps(current_state or {}, indent=2)}

Valid next states. You may stay in the current state if the conversation does not justify a transition:
{json.dumps(valid_next_states, indent=2)}

Transition reasons from the current state:
{json.dumps(transition_options, indent=2)}

Return JSON only with this shape:
{{
  "assistantMessage": "your response to the user",
  "nextStateId": number,
  "nextStateName": "state name",
  "stateReason": "why the most recent user message should keep or change the state"
}}"""

        payload = {
            "model": model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"{context}\n\n"
                                "Use the context-resident state machine above as the controlling frame. "
                                "Decide the next state from only the valid next states provided by the user message."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": decision_prompt,
                        }
                    ],
                },
            ],
        }

        request = urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            message = error.read().decode("utf-8")
            self.send_error_json(error.code, message)
            return
        except urllib.error.URLError as error:
            self.send_error_json(502, f"OpenAI request failed: {error.reason}")
            return

        text = extract_response_text(result)
        parsed = parse_machine_test_output(text, states, current_state_id, valid_next_ids)
        self.send_json({"model": model, "text": text, "raw": result, **parsed})

    def serve_static(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            path = "/index.html"
        target = (ROOT / path.lstrip("/")).resolve()

        if not str(target).startswith(str(ROOT)) or not target.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, payload: dict | list, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    load_env()
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Serving http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
