import json
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


SIMULATIONS = {
    "Product Return Authorization": [
        "I want to return headphones I bought recently. The right side stopped working and I need a refund.",
        "Order RMA-77821, purchased 12 days ago. They are wireless headphones, no visible damage, and I still have the box and receipt.",
        "A replacement is fine if it ships quickly. I can print a label today.",
    ],
    "Event Incident Response": [
        "There is a problem near the east entrance. People are backing up and someone said a guest fell.",
        "East entrance gate 3. One attendee tripped on a loose floor mat, is sitting up, and says their ankle hurts. The line is blocking the doorway.",
        "Medical staff are on the way and security is moving the line. Venue ops needs the loose mat location and incident notes.",
        "Medical took over, security cleared the doorway, and venue ops removed the mat. Please document it for follow-up.",
    ],
}


def api(path: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def selected_state(machine: dict) -> dict | None:
    return next(
        (state for state in machine["states"] if state["id"] == machine["selectedStateId"]),
        machine["states"][0] if machine["states"] else None,
    )


def render_context(machine: dict) -> str:
    state = selected_state(machine)
    states = ", ".join(item["name"] for item in machine["states"]) or "(none)"
    associations = ", ".join(
        f"{state_name(machine, item['from'])} -> {state_name(machine, item['to'])}"
        for item in machine["associations"]
    ) or "(none)"
    transition_reasoning = "\n".join(
        f"{state_name(machine, item['from'])} -> {state_name(machine, item['to'])}: {item['reason']}"
        for item in machine["associations"]
    ) or "(none)"
    bindings = "\n".join(f"{item['name']}: context bound" for item in machine["states"]) or "(none)"

    return f"""context_resident_state_machine {{
  machine: {machine['name']}
  states: {states}
  associations: {associations}
  current_state: {state['name'] if state else 'none'}
}}

transition_reasoning {{
{transition_reasoning}
}}

state_context_bindings {{
{bindings}
}}

loaded_state_context {{
  state: {state['name'] if state else 'none'}
  context:
{state['context'] if state else '(none)'}
}}"""


def state_name(machine: dict, state_id: int) -> str:
    return next((state["name"] for state in machine["states"] if state["id"] == state_id), str(state_id))


def machine_by_name(name: str) -> dict:
    machines = api("/api/machines")
    return next(machine for machine in machines if machine["name"] == name)


def reset_to_first_state(machine: dict) -> None:
    if not machine["states"]:
        return
    api(
        f"/api/machines/{machine['id']}/selected-state",
        method="PATCH",
        payload={"selectedStateId": machine["states"][0]["id"]},
    )


def run_simulation(machine_name: str, prompts: list[str]) -> dict:
    machine = machine_by_name(machine_name)
    reset_to_first_state(machine)
    conversation = []
    session_id = None
    transitions = []

    for prompt in prompts:
        machine = machine_by_name(machine_name)
        before_state = selected_state(machine)
        conversation.append({"role": "user", "content": prompt})
        result = api(
            "/api/machine-test",
            method="POST",
            payload={
                "machineId": machine["id"],
                "sessionId": session_id,
                "context": render_context(machine),
                "userPrompt": prompt,
                "conversation": conversation,
                "currentStateId": machine["selectedStateId"],
                "states": machine["states"],
                "associations": machine["associations"],
            },
        )
        session_id = result["sessionId"]
        conversation.append(
            {
                "role": "assistant",
                "content": result.get("assistantMessage") or result.get("text") or "",
            }
        )

        transitions.append(
            {
                "from": before_state["name"] if before_state else "none",
                "to": result.get("nextStateName"),
                "reason": result.get("stateReason"),
            }
        )

        if result.get("nextStateId") and result["nextStateId"] != machine["selectedStateId"]:
            api(
                f"/api/machines/{machine['id']}/selected-state",
                method="PATCH",
                payload={"selectedStateId": result["nextStateId"]},
            )

    return {"machine": machine_name, "sessionId": session_id, "transitions": transitions}


def main() -> None:
    summaries = [run_simulation(name, prompts) for name, prompts in SIMULATIONS.items()]
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
