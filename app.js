let machines = [];
let selectedMachineId = null;
const testConversations = new Map();
const testSessionIds = new Map();

const libraryPage = document.querySelector("#libraryPage");
const builderPage = document.querySelector("#builderPage");
const testPage = document.querySelector("#testPage");
const documentsPage = document.querySelector("#documentsPage");
const machineForm = document.querySelector("#machineForm");
const machineName = document.querySelector("#machineName");
const machineList = document.querySelector("#machineList");
const machineCount = document.querySelector("#machineCount");
const activeMachineName = document.querySelector("#activeMachineName");
const backButton = document.querySelector("#backButton");
const testButton = document.querySelector("#testButton");
const documentsButton = document.querySelector("#documentsButton");
const resetButton = document.querySelector("#resetButton");
const testBackButton = document.querySelector("#testBackButton");
const testMachinesButton = document.querySelector("#testMachinesButton");
const documentsBackButton = document.querySelector("#documentsBackButton");
const documentList = document.querySelector("#documentList");
const documentCount = document.querySelector("#documentCount");
const testMachineName = document.querySelector("#testMachineName");
const testContextWindow = document.querySelector("#testContextWindow");
const testCurrentState = document.querySelector("#testCurrentState");
const testPromptForm = document.querySelector("#testPromptForm");
const userPrompt = document.querySelector("#userPrompt");
const openaiResponse = document.querySelector("#openaiResponse");
const openaiModelLabel = document.querySelector("#openaiModelLabel");
const conversationLog = document.querySelector("#conversationLog");
const activeSessionLabel = document.querySelector("#activeSessionLabel");
const newTranscriptButton = document.querySelector("#newTranscriptButton");
const transcriptSessionList = document.querySelector("#transcriptSessionList");
const rawDialog = document.querySelector("#rawDialog");
const rawDialogTitle = document.querySelector("#rawDialogTitle");
const rawDialogBody = document.querySelector("#rawDialogBody");

const stateList = document.querySelector("#stateList");
const stateForm = document.querySelector("#stateForm");
const stateName = document.querySelector("#stateName");
const newStateContext = document.querySelector("#newStateContext");
const stateCount = document.querySelector("#stateCount");
const contextPreview = document.querySelector("#contextPreview");
const loadedStateSelect = document.querySelector("#loadedStateSelect");

const associationForm = document.querySelector("#associationForm");
const fromState = document.querySelector("#fromState");
const toState = document.querySelector("#toState");
const transitionReason = document.querySelector("#transitionReason");
const associationList = document.querySelector("#associationList");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${response.status}`);
  }

  return response.json();
}

async function loadMachines() {
  machines = await api("/api/machines");
  if (selectedMachineId && !machines.some((machine) => machine.id === selectedMachineId)) {
    selectedMachineId = null;
  }
}

async function loadDocuments() {
  return api("/api/documents");
}

async function loadTestSessions(machineId) {
  return api(`/api/machines/${machineId}/test-sessions`);
}

async function loadTestSession(sessionId) {
  return api(`/api/test-sessions/${sessionId}`);
}

function getMachine() {
  return machines.find((item) => item.id === selectedMachineId) || null;
}

function getSelectedState() {
  const machine = getMachine();
  if (!machine) return null;
  return machine.states.find((state) => state.id === machine.selectedStateId) || machine.states[0] || null;
}

function getStateName(id) {
  const machine = getMachine();
  if (!machine) return id;
  return machine.states.find((state) => state.id === id)?.name || id;
}

function associationsFrom(id) {
  const machine = getMachine();
  if (!machine) return [];
  return machine.associations.filter((association) => association.from === id);
}

async function createMachine(name) {
  const cleaned = name.trim();
  if (!cleaned) return;

  const result = await api("/api/machines", {
    method: "POST",
    body: JSON.stringify({ name: cleaned }),
  });
  selectedMachineId = result.id;
  await loadMachines();
  showBuilder();
}

async function addState(name, context) {
  const machine = getMachine();
  const cleaned = name.trim();
  const cleanedContext = context.trim();
  if (!machine || !cleaned || !cleanedContext) return;

  await api(`/api/machines/${machine.id}/states`, {
    method: "POST",
    body: JSON.stringify({ name: cleaned, context: cleanedContext }),
  });
  await loadMachines();
}

async function deleteState(id) {
  await api(`/api/states/${id}`, { method: "DELETE" });
  await loadMachines();
}

async function addAssociation(from, to, reason) {
  const machine = getMachine();
  if (!machine || !from || !to || from === to) return;

  await api(`/api/machines/${machine.id}/associations`, {
    method: "POST",
    body: JSON.stringify({ from: Number(from), to: Number(to), reason }),
  });
  await loadMachines();
}

async function deleteAssociation(id) {
  await api(`/api/associations/${id}`, { method: "DELETE" });
  await loadMachines();
}

async function setSelectedState(id) {
  const machine = getMachine();
  if (!machine) return;
  machine.selectedStateId = Number(id);
  await api(`/api/machines/${machine.id}/selected-state`, {
    method: "PATCH",
    body: JSON.stringify({ selectedStateId: machine.selectedStateId }),
  });
  await loadMachines();
}

async function runMachineTest(context, prompt, conversation) {
  const machine = getMachine();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 75000);

  return api("/api/machine-test", {
    method: "POST",
    signal: controller.signal,
    body: JSON.stringify({
      machineId: machine?.id || null,
      sessionId: getSessionId(),
      context,
      userPrompt: prompt,
      conversation,
      currentStateId: machine?.selectedStateId || null,
      states: machine?.states || [],
      associations: machine?.associations || [],
    }),
  }).finally(() => clearTimeout(timeout));
}

function getConversation(machineId = selectedMachineId) {
  if (!machineId) return [];
  if (!testConversations.has(machineId)) {
    testConversations.set(machineId, []);
  }
  return testConversations.get(machineId);
}

function getSessionId(machineId = selectedMachineId) {
  return testSessionIds.get(machineId) || null;
}

function setSessionId(sessionId, machineId = selectedMachineId) {
  if (!machineId) return;
  if (sessionId) {
    testSessionIds.set(machineId, sessionId);
  } else {
    testSessionIds.delete(machineId);
  }
}

function renderConversation() {
  const conversation = getConversation();
  conversationLog.innerHTML = "";

  if (!conversation.length) {
    conversationLog.innerHTML = `<div class="empty-state compact">No conversation yet.</div>`;
    return;
  }

  conversation.forEach((turn) => {
    const item = document.createElement("article");
    item.className = `conversation-turn ${turn.role}`;
    const role =
      turn.role === "assistant" && turn.state
        ? `Assistant - State: ${turn.state}`
        : turn.role === "user"
          ? "User"
          : "Assistant";
    item.innerHTML = `<div class="conversation-turn-meta"><strong></strong></div><p></p>`;
    item.querySelector("strong").textContent = role;
    if (turn.role === "assistant" && turn.raw) {
      const rawButton = document.createElement("button");
      rawButton.type = "button";
      rawButton.className = "raw-link";
      rawButton.textContent = "See raw";
      rawButton.addEventListener("click", () => {
        showRawDialog(role, turn.raw);
      });

      const stateButton = document.createElement("button");
      stateButton.type = "button";
      stateButton.className = "raw-link";
      stateButton.textContent = "See state";
      stateButton.addEventListener("click", () => {
        showStateDialog(role, turn.raw);
      });

      item.querySelector(".conversation-turn-meta").append(rawButton, stateButton);
    }
    item.querySelector("p").textContent = turn.content;
    conversationLog.appendChild(item);
  });

  conversationLog.scrollTop = conversationLog.scrollHeight;
}

function showRawDialog(title, rawText) {
  rawDialogTitle.textContent = title;
  rawDialogBody.textContent = rawText || "(no raw output saved)";
  if (typeof rawDialog.showModal === "function") {
    rawDialog.showModal();
  } else {
    alert(rawDialogBody.textContent);
  }
}

function showStateDialog(title, rawText) {
  rawDialogTitle.textContent = `${title} - State`;
  rawDialogBody.textContent = formatStateDecision(rawText);
  if (typeof rawDialog.showModal === "function") {
    rawDialog.showModal();
  } else {
    alert(rawDialogBody.textContent);
  }
}

function formatStateDecision(rawText) {
  if (!rawText) return "(no raw output saved)";

  const cleanedText = rawText.trim().replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```$/i, "").trim();

  try {
    const parsed = JSON.parse(cleanedText);
    const decisionOnly = {
      assistantMessage: "[text removed]",
      nextStateId: parsed.nextStateId ?? null,
      nextStateName: parsed.nextStateName ?? null,
      stateReason: parsed.stateReason ?? null,
    };
    return JSON.stringify(decisionOnly, null, 2);
  } catch {
    return rawText;
  }
}

async function renderTranscriptSessions() {
  const machine = getMachine();
  if (!machine) return;

  activeSessionLabel.textContent = getSessionId() ? `session ${getSessionId()}` : "new session";
  transcriptSessionList.innerHTML = `<div class="empty-state compact">Loading transcripts...</div>`;

  try {
    const sessions = await loadTestSessions(machine.id);
    transcriptSessionList.innerHTML = "";

    if (!sessions.length) {
      transcriptSessionList.innerHTML = `<div class="empty-state compact">No saved transcripts yet.</div>`;
      return;
    }

    sessions.forEach((session) => {
      const row = document.createElement("article");
      row.className = "transcript-row";
      row.classList.toggle("active", session.id === getSessionId());

      const summary = document.createElement("div");
      summary.className = "transcript-summary";
      const title = document.createElement("strong");
      title.textContent = session.title;
      const detail = document.createElement("span");
      detail.textContent = `${session.messageCount} messages / ${session.initialState || "none"} -> ${
        session.currentState || "none"
      } / ${session.updatedAt}`;
      summary.append(title, detail);

      const loadButton = document.createElement("button");
      loadButton.type = "button";
      loadButton.className = "secondary-button";
      loadButton.textContent = "Load";
      loadButton.addEventListener("click", async () => {
        const transcript = await loadTestSession(session.id);
        setSessionId(transcript.id);
        testConversations.set(
          machine.id,
          transcript.messages.map((message) => ({
            role: message.role,
            content: message.content,
            state: message.role === "assistant" ? message.stateBefore : null,
            raw: message.role === "assistant" ? message.rawResponse : null,
          }))
        );
        let loadedModel = "loaded";
        for (let index = transcript.messages.length - 1; index >= 0; index -= 1) {
          if (transcript.messages[index].model) {
            loadedModel = transcript.messages[index].model;
            break;
          }
        }
        openaiModelLabel.textContent = loadedModel;
        openaiResponse.textContent = `loaded transcript\nstate: ${transcript.currentState || "none"}`;
        renderConversation();
        renderTestContext();
        await renderTranscriptSessions();
      });

      row.append(summary, loadButton);
      transcriptSessionList.appendChild(row);
    });
  } catch (error) {
    transcriptSessionList.innerHTML = `<div class="empty-state compact">${error.message}</div>`;
  }
}

function showLibrary() {
  selectedMachineId = null;
  libraryPage.classList.remove("hidden");
  builderPage.classList.add("hidden");
  testPage.classList.add("hidden");
  documentsPage.classList.add("hidden");
  renderLibrary();
}

function showBuilder() {
  libraryPage.classList.add("hidden");
  builderPage.classList.remove("hidden");
  testPage.classList.add("hidden");
  documentsPage.classList.add("hidden");
  renderBuilder();
}

function showTest() {
  if (!getMachine()) {
    showLibrary();
    return;
  }

  libraryPage.classList.add("hidden");
  builderPage.classList.add("hidden");
  testPage.classList.remove("hidden");
  documentsPage.classList.add("hidden");
  renderTest();
}

async function showDocuments() {
  libraryPage.classList.add("hidden");
  builderPage.classList.add("hidden");
  testPage.classList.add("hidden");
  documentsPage.classList.remove("hidden");
  await renderDocuments();
}

function renderLibrary() {
  machineList.innerHTML = "";
  machineCount.textContent = `${machines.length} ${machines.length === 1 ? "machine" : "machines"}`;

  if (!machines.length) {
    machineList.innerHTML = `<div class="empty-state">Create a machine to begin.</div>`;
    return;
  }

  machines.forEach((machine) => {
    const card = document.createElement("article");
    card.className = "machine-card";
    card.innerHTML = `
      <strong>${machine.name}</strong>
      <span>${machine.states.length} ${machine.states.length === 1 ? "state" : "states"} / ${machine.associations.length} ${machine.associations.length === 1 ? "association" : "associations"}</span>
      <div class="machine-card-actions">
        <button class="primary-button" type="button" data-machine-action="edit">Edit</button>
        <button class="secondary-button" type="button" data-machine-action="test">Test</button>
      </div>
    `;

    card.querySelector('[data-machine-action="edit"]').addEventListener("click", () => {
      selectedMachineId = machine.id;
      showBuilder();
    });

    card.querySelector('[data-machine-action="test"]').addEventListener("click", () => {
      selectedMachineId = machine.id;
      showTest();
    });

    machineList.appendChild(card);
  });
}

async function renderDocuments() {
  const documents = await loadDocuments();
  documentCount.textContent = `${documents.length} ${documents.length === 1 ? "document" : "documents"}`;
  documentList.innerHTML = "";

  if (!documents.length) {
    documentList.innerHTML = `<div class="empty-state">No documents yet.</div>`;
    return;
  }

  documents.forEach((doc) => {
    const article = document.createElement("article");
    article.className = "document-card";
    article.innerHTML = `
      <h2>${doc.title}</h2>
      <pre>${doc.body}</pre>
    `;
    documentList.appendChild(article);
  });
}

function renderStateList() {
  const machine = getMachine();
  stateList.innerHTML = "";

  if (!machine?.states.length) {
    stateList.innerHTML = `<div class="empty-state">No states yet.</div>`;
    return;
  }

  machine.states.forEach((state) => {
    const row = document.createElement("div");
    row.className = "state-row";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "state-button";
    button.classList.toggle("active", state.id === machine.selectedStateId);
    button.innerHTML = `<span>${state.name}</span><small>${associationsFrom(state.id).length} out</small>`;
    button.addEventListener("click", async () => {
      await setSelectedState(state.id);
      renderBuilder();
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "icon-button";
    deleteButton.textContent = "x";
    deleteButton.setAttribute("aria-label", `Delete ${state.name}`);
    deleteButton.addEventListener("click", async () => {
      await deleteState(state.id);
      renderBuilder();
    });

    row.append(button, deleteButton);
    stateList.appendChild(row);
  });
}

function renderSelectors() {
  const machine = getMachine();
  const states = machine?.states || [];
  const options = states.map((state) => `<option value="${state.id}">${state.name}</option>`).join("");

  fromState.innerHTML = options;
  toState.innerHTML = options;
  fromState.disabled = states.length < 2;
  toState.disabled = states.length < 2;
  transitionReason.disabled = states.length < 2;
  associationForm.querySelector("button").disabled = states.length < 2;

  if (!states.length) return;

  fromState.value = machine.selectedStateId || states[0].id;
  const defaultTarget = states.find((state) => state.id !== Number(fromState.value));
  toState.value = defaultTarget?.id || fromState.value;
}

function renderAssociations() {
  const machine = getMachine();
  associationList.innerHTML = "";

  if (!machine?.associations.length) {
    associationList.innerHTML = `<div class="empty-state">No associations yet.</div>`;
    return;
  }

  machine.associations.forEach((association) => {
    const row = document.createElement("div");
    row.className = "association-row";

    const name = document.createElement("div");
    name.className = "association-name";
    name.innerHTML = `<strong>${getStateName(association.from)} -> ${getStateName(association.to)}</strong><span>${association.reason}</span>`;

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "icon-button";
    deleteButton.textContent = "x";
    deleteButton.setAttribute("aria-label", `Delete ${name.textContent}`);
    deleteButton.addEventListener("click", async () => {
      await deleteAssociation(association.id);
      renderBuilder();
    });

    row.append(name, deleteButton);
    associationList.appendChild(row);
  });
}

function renderLoadedStateSelector() {
  const machine = getMachine();
  const states = machine?.states || [];

  loadedStateSelect.innerHTML = states
    .map((state) => `<option value="${state.id}">${state.name}</option>`)
    .join("");
  loadedStateSelect.disabled = !states.length;

  if (states.length) {
    loadedStateSelect.value = getSelectedState()?.id || states[0].id;
  }
}

function renderLlmContext() {
  const machine = getMachine();
  if (!machine) return "";

  const selected = getSelectedState();
  const states = machine.states.map((state) => state.name).join(", ") || "(none)";
  const associations = machine.associations.length
    ? machine.associations
        .map((association) => `${getStateName(association.from)} -> ${getStateName(association.to)}`)
        .join(", ")
    : "(none)";
  const transitionReasoning = machine.associations.length
    ? machine.associations
        .map(
          (association) =>
            `${getStateName(association.from)} -> ${getStateName(association.to)}: ${association.reason}`
        )
        .join("\n")
    : "(none)";
  const bindings = machine.states.length
    ? machine.states.map((state) => `${state.name}: context bound`).join("\n")
    : "(none)";

  return `context_resident_state_machine {
  machine: ${machine.name}
  states: ${states}
  associations: ${associations}
  current_state: ${selected?.name || "none"}
}

transition_reasoning {
${transitionReasoning}
}

state_context_bindings {
${bindings}
}

loaded_state_context {
  state: ${selected?.name || "none"}
  context:
${selected?.context || "(none)"}
}`;
}

function renderBuilder() {
  const machine = getMachine();
  if (!machine) {
    showLibrary();
    return;
  }

  activeMachineName.textContent = machine.name;
  stateCount.textContent = `${machine.states.length} ${machine.states.length === 1 ? "state" : "states"}`;

  renderStateList();
  renderSelectors();
  renderAssociations();
  renderLoadedStateSelector();
  contextPreview.textContent = renderLlmContext();
}

function renderTest() {
  const machine = getMachine();
  if (!machine) {
    showLibrary();
    return;
  }

  renderTestContext();
  openaiModelLabel.textContent = "not run";
  openaiResponse.textContent = "Waiting for the next user message.";
  renderConversation();
  renderTranscriptSessions();
}

function renderTestContext() {
  const machine = getMachine();
  const selected = getSelectedState();
  testMachineName.textContent = machine?.name || "No machine selected";
  testCurrentState.textContent = `state: ${selected?.name || "none"}`;
  testContextWindow.textContent = renderLlmContext();
}

machineForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await createMachine(machineName.value);
  machineName.value = "";
});

stateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await addState(stateName.value, newStateContext.value);
  stateName.value = "";
  newStateContext.value = "";
  renderBuilder();
});

associationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await addAssociation(fromState.value, toState.value, transitionReason.value);
  transitionReason.value = "";
  renderBuilder();
});

backButton.addEventListener("click", showLibrary);
testButton.addEventListener("click", showTest);
testBackButton.addEventListener("click", showBuilder);
testMachinesButton.addEventListener("click", showLibrary);
documentsButton.addEventListener("click", showDocuments);
documentsBackButton.addEventListener("click", showLibrary);

testPromptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = userPrompt.value.trim();
  if (!prompt) return;

  const conversation = getConversation();
  conversation.push({ role: "user", content: prompt });
  userPrompt.value = "";
  renderConversation();
  openaiModelLabel.textContent = "running";
  openaiResponse.textContent = "Calling OpenAI and evaluating state...";

  try {
    const respondingState = getSelectedState()?.name || null;
    const result = await runMachineTest(testContextWindow.textContent, prompt, conversation);
    const assistantMessage = result.assistantMessage || result.text || "(no text returned)";
    setSessionId(result.sessionId);
    conversation.push({
      role: "assistant",
      content: assistantMessage,
      state: respondingState,
      raw: result.text,
    });
    openaiModelLabel.textContent = result.model;
    openaiResponse.textContent = `state: ${result.nextStateName || "none"}\nreason: ${
      result.stateReason || "No state reason returned."
    }`;

    if (result.nextStateId && result.nextStateId !== getMachine()?.selectedStateId) {
      await setSelectedState(result.nextStateId);
    }

    renderConversation();
    renderTestContext();
    renderTranscriptSessions();
  } catch (error) {
    openaiModelLabel.textContent = "error";
    openaiResponse.textContent =
      error.name === "AbortError"
        ? "OpenAI did not return within 75 seconds."
        : error.message;
    renderConversation();
  }
});

newTranscriptButton.addEventListener("click", () => {
  const machine = getMachine();
  if (!machine) return;
  setSessionId(null);
  testConversations.set(machine.id, []);
  openaiModelLabel.textContent = "not run";
  openaiResponse.textContent = "Waiting for the next user message.";
  renderConversation();
  renderTranscriptSessions();
});

loadedStateSelect.addEventListener("change", async () => {
  await setSelectedState(loadedStateSelect.value);
  renderBuilder();
});

resetButton.addEventListener("click", async () => {
  await api("/api/machines", { method: "DELETE" });
  await loadMachines();
  selectedMachineId = null;
  renderLibrary();
});

loadMachines().then(renderLibrary).catch((error) => {
  machineList.innerHTML = `<div class="empty-state">${error.message}</div>`;
});
