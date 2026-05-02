const state = {
  connectors: [],
  loadedEnvKeys: [],
  learningRuns: [],
  missions: [],
  projects: [],
  runs: [],
  outcomes: [],
  pendingApprovals: [],
  currentMissionId: null,
  preview: null,
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatLabel(value) {
  return String(value || "")
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function renderStatusPill(status) {
  const safeStatus = escapeHtml(status || "unknown");
  return `<span class="status-pill status-${safeStatus.toLowerCase()}">${safeStatus}</span>`;
}

function debounce(fn, delayMs) {
  let timeoutId = null;
  return (...args) => {
    window.clearTimeout(timeoutId);
    timeoutId = window.setTimeout(() => fn(...args), delayMs);
  };
}

function collectExplorationFormData() {
  return {
    goal: document.getElementById("goal").value.trim(),
    domain: document.getElementById("domain").value,
    project_name: document.getElementById("project-name").value.trim(),
    project_kind: document.getElementById("project-kind").value,
    mission_name: document.getElementById("mission-name").value.trim(),
    owner: document.getElementById("owner").value.trim(),
    priority: document.getElementById("priority").value,
    hard_constraints: document.getElementById("hard-constraints").value.trim(),
    available_environment: document.getElementById("available-environment").value.trim(),
    evidence_requirements: document.getElementById("evidence-requirements").value.trim(),
    operator_hunches: document.getElementById("operator-hunches").value.trim(),
    disallowed_assumptions: document.getElementById("disallowed-assumptions").value.trim(),
    requested_connectors: Array.from(document.querySelectorAll('input[name="connector"]:checked')).map((input) => input.value),
  };
}

function composeMissionConstraints(formData) {
  const sections = [
    ["Hard Constraints", formData.hard_constraints],
    ["Available Environment", formData.available_environment],
    ["Evidence Requirements", formData.evidence_requirements],
    [
      "Operator Hunches",
      formData.operator_hunches
        ? `Treat these as operator hypotheses for exploration, not as the scoring rule unless later approved.\n${formData.operator_hunches}`
        : "",
    ],
    ["Disallowed Assumptions", formData.disallowed_assumptions],
  ];

  return sections
    .filter(([, content]) => content)
    .map(([title, content]) => `${title}:\n${content}`)
    .join("\n\n");
}

async function fetchState() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  state.connectors = payload.connectors || [];
  state.loadedEnvKeys = payload.loaded_env_keys || [];
  state.learningRuns = payload.learning_runs || [];
  state.missions = payload.missions || [];
  state.projects = payload.projects || [];
  state.runs = payload.runs || [];
  state.outcomes = payload.outcomes || [];
  state.pendingApprovals = payload.pending_approvals || [];

  renderProject(payload.project || {});
  renderOverview(
    payload.project || {},
    state.missions,
    state.pendingApprovals,
    state.projects,
    state.runs,
    state.outcomes
  );
  renderConnectorChoices(state.connectors);
  renderConnectors(state.connectors, state.loadedEnvKeys);
  renderApprovalQueue(state.pendingApprovals);
  renderMissionList(state.missions);

  if (state.currentMissionId) {
    const exists = state.missions.some((mission) => mission.id === state.currentMissionId);
    if (exists) {
      await loadMission(state.currentMissionId, false);
      return;
    }
  }

  if (state.missions.length) {
    await loadMission(state.missions[0].id, false);
  } else {
    renderMissionDetail(null);
  }
}

function renderProject(project) {
  document.getElementById("launcher-name").textContent = "GovernedAgentLab.command";
  document.getElementById("launcher-path").textContent = project.launcher || "";
  document.getElementById("scope-badge").textContent = project.autonomy_level || "A2";
}

function renderOverview(project, missions, approvals, projects, runs, outcomes) {
  const container = document.getElementById("overview-grid");
  const cards = [
    ["Projects", projects.length],
    ["Missions", missions.length],
    ["Runs", runs.length],
    ["Outcomes", outcomes.length],
    ["Approvals", approvals.length],
    ["Risk", project.risk_tier || "high"],
  ];
  container.innerHTML = cards
    .map(
      ([label, value]) =>
        `<div class="overview-card"><span class="muted">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`
    )
    .join("");
  document.getElementById("mission-count").textContent = String(missions.length);
  document.getElementById("approval-count").textContent = String(approvals.length);
}

function renderConnectorChoices(connectors) {
  const container = document.getElementById("connector-options");
  container.innerHTML = connectors
    .map((connector) => {
      const envVars = (connector.env_vars || []).join(", ");
      return `
        <label class="connector-choice">
          <div class="connector-choice-head">
            <input type="checkbox" name="connector" value="${escapeHtml(connector.key)}" />
            <strong>${escapeHtml(connector.label)}</strong>
          </div>
          <small class="connector-meta">${escapeHtml(connector.scope || "")}</small>
          <small class="connector-meta">Env: ${escapeHtml(envVars || "None")}</small>
        </label>
      `;
    })
    .join("");
}

function connectorState(connector) {
  if (connector.configured && connector.profile_enabled) return "ready";
  if (connector.profile_enabled) return "missing-env";
  return "disabled";
}

function renderConnectors(connectors, loadedEnvKeys) {
  document.getElementById("env-status").textContent = loadedEnvKeys.length
    ? `Loaded local env keys: ${loadedEnvKeys.join(", ")}`
    : "No local env secrets loaded yet.";

  const container = document.getElementById("connector-list");
  container.innerHTML = connectors
    .map((connector) => {
      const status = connectorState(connector);
      return `
        <article class="connector-card fade-in">
          <div class="connector-title-row">
            <strong>${escapeHtml(connector.label)}</strong>
            <span class="connector-status ${status}">${formatLabel(status)}</span>
          </div>
          <small class="connector-meta">${escapeHtml(connector.scope || "")}</small>
          <small class="connector-meta">${escapeHtml(connector.notes || "")}</small>
        </article>
      `;
    })
    .join("");
}

function renderApprovalQueue(approvals) {
  const container = document.getElementById("approval-queue");
  if (!approvals.length) {
    container.innerHTML = `<div class="approval-card"><strong>No approvals waiting</strong><small>New missions will surface any connector or tool-scope reviews here.</small></div>`;
    return;
  }

  container.innerHTML = approvals
    .map(
      (approval) => `
        <article class="approval-card fade-in">
          <div class="approval-title-row">
            <h3>${escapeHtml(approval.title)}</h3>
            ${renderStatusPill(approval.status)}
          </div>
          <small>${escapeHtml(approval.mission_name)}</small>
          <small>${escapeHtml(approval.rationale)}</small>
          <div class="approval-actions">
            <button type="button" class="approval-button" data-approval-id="${approval.id}" data-status="approved">Approve</button>
            <button type="button" class="approval-button" data-approval-id="${approval.id}" data-status="pending">Hold</button>
            <button type="button" class="approval-button reject" data-approval-id="${approval.id}" data-status="rejected">Reject</button>
          </div>
        </article>
      `
    )
    .join("");

  container.querySelectorAll("[data-approval-id]").forEach((button) => {
    button.addEventListener("click", () => updateApproval(Number(button.dataset.approvalId), button.dataset.status));
  });
}

function renderMissionList(missions) {
  const container = document.getElementById("mission-list");
  container.innerHTML = "";
  if (!missions.length) {
    container.innerHTML = `<div class="detail-card"><strong>No missions yet</strong><small>Use the exploratory intake above to open the first governed mission.</small></div>`;
    return;
  }

  const template = document.getElementById("mission-item-template");
  missions.forEach((mission) => {
    const fragment = template.content.cloneNode(true);
    const button = fragment.querySelector(".mission-card");
    if (state.currentMissionId === mission.id) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <div class="mission-title-row">
        <h3>${escapeHtml(mission.name)}</h3>
        ${renderStatusPill(mission.status)}
      </div>
      <div class="mission-meta">${escapeHtml(mission.domain)} · ${escapeHtml(mission.priority)}</div>
      <div class="mission-meta">${escapeHtml(mission.project_name || "Unlinked Project")} · ${escapeHtml(mission.run_key || "Run pending")}</div>
      <div class="mission-meta">${escapeHtml(mission.summary)}</div>
      <div class="mission-meta">${escapeHtml(mission.child_name)} · ${escapeHtml(mission.child_path)}</div>
    `;
    button.addEventListener("click", () => loadMission(mission.id, true));
    container.appendChild(fragment);
  });
}

function detailCard(title, body) {
  return `<article class="detail-card fade-in"><h3>${escapeHtml(title)}</h3>${body}</article>`;
}

function renderMissionDetail(mission) {
  const container = document.getElementById("mission-detail");
  const badge = document.getElementById("detail-status");
  if (!mission) {
    badge.textContent = "Idle";
    container.className = "detail-view empty-state";
    container.textContent = "Select or create a mission to see the child workspace, approval gates, artifacts, and role plan.";
    return;
  }

  badge.textContent = formatLabel(mission.status);
  const result = mission.result || {};
  const brief = result.brief || {};
  const child = mission.spec?.child || result.child || {};
  const project = mission.project || mission.spec?.project || result.project || {};
  const run = mission.run || mission.spec?.run || result.run || {};
  const approvals = mission.approvals || [];
  const phases = result.phases || [];
  const artifacts = mission.artifacts || [];
  const roles = result.orchestration?.roles || [];

  const summaryCard = detailCard(
    "Mission Summary",
    `
      <div class="detail-row"><span>${renderStatusPill(mission.status)}</span><span class="mission-meta">${escapeHtml(mission.domain)} · ${escapeHtml(mission.priority)}</span></div>
      <p>${escapeHtml(mission.summary)}</p>
      <p><strong>Goal</strong><br />${escapeHtml(mission.goal)}</p>
      <p><strong>Constraints</strong><br />${escapeHtml(mission.constraints || "None provided.")}</p>
      <p><strong>Success Definition</strong><br />${escapeHtml(brief.success_definition || "Keep the mission governed and outcome-focused.")}</p>
    `
  );

  const projectCard = detailCard(
    "Project Container",
    `
      <p><strong>${escapeHtml(project.name || "Not linked")}</strong></p>
      <p><strong>Kind</strong><br />${escapeHtml(project.kind || "project")}</p>
      <p class="path-block">${escapeHtml(project.root_path || project.path || "")}</p>
      <p><strong>Current Outcome</strong><br />${escapeHtml(project.current_outcome?.name || "None promoted yet")}</p>
    `
  );

  const runCard = detailCard(
    "Run Workspace",
    `
      <p><strong>${escapeHtml(run.run_key || run.key || child.slug || mission.child_slug)}</strong></p>
      <p class="path-block">${escapeHtml(run.root_path || run.path || child.path || mission.child_path)}</p>
      <p><strong>Requested Connectors</strong><br />${escapeHtml((child.requested_connectors || []).join(", ") || "None")}</p>
      <p><strong>Goal Brief</strong><br />${escapeHtml(run.spec?.goal_path || run.goal_path || child.goal_path || "workspace/goal.md")}</p>
    `
  );

  const approvalsCard = detailCard(
    "Approval Gates",
    approvals.length
      ? approvals
          .map(
            (approval) => `
              <div class="approval-card">
                <div class="approval-title-row">
                  <strong>${escapeHtml(approval.title)}</strong>
                  ${renderStatusPill(approval.status)}
                </div>
                <small>${escapeHtml(approval.required_for)}</small>
                <small>${escapeHtml(approval.rationale)}</small>
                <div class="approval-actions">
                  <button type="button" class="approval-button" data-approval-id="${approval.id}" data-status="approved">Approve</button>
                  <button type="button" class="approval-button" data-approval-id="${approval.id}" data-status="pending">Hold</button>
                  <button type="button" class="approval-button reject" data-approval-id="${approval.id}" data-status="rejected">Reject</button>
                </div>
              </div>
            `
          )
          .join("")
      : "<p>No approvals required.</p>"
  );

  const phasesCard = detailCard(
    "Mission Phases",
    `
      <div class="mission-phases">
        ${phases
          .map(
            (phase) => `
              <div class="phase-card">
                <div class="approval-title-row">
                  <strong>${escapeHtml(phase.title)}</strong>
                  ${renderStatusPill(phase.status)}
                </div>
                <small>${escapeHtml(phase.summary)}</small>
              </div>
            `
          )
          .join("")}
      </div>
    `
  );

  const artifactsCard = detailCard(
    "Artifact Timeline",
    artifacts.length
      ? artifacts
          .map(
            (artifact) => `
              <div class="artifact-card">
                <div class="approval-title-row">
                  <strong>${escapeHtml(artifact.title)}</strong>
                  <small>${escapeHtml(artifact.artifact_type)}</small>
                </div>
                <small>${escapeHtml(artifact.summary)}</small>
                <small class="path-block">${escapeHtml(artifact.path)}</small>
              </div>
            `
          )
          .join("")
      : "<p>No artifacts have been recorded yet.</p>"
  );

  const rolesCard = detailCard(
    "Role Plan",
    roles.length
      ? roles
          .map(
            (role) => `
              <div class="artifact-card">
                <div class="approval-title-row">
                  <strong>${escapeHtml(formatLabel(role.role))}</strong>
                  ${renderStatusPill(role.status)}
                </div>
                <small>${escapeHtml(role.purpose || "")}</small>
                <small>${escapeHtml(role.workspace_focus || "")}</small>
                <small>Artifact: ${escapeHtml(role.artifact || "n/a")}</small>
              </div>
            `
          )
          .join("")
      : "<p>No role plan available.</p>"
  );

  container.className = "detail-view";
  container.innerHTML = `
    <div class="detail-grid">
      ${summaryCard}
      ${projectCard}
    </div>
    ${runCard}
    ${approvalsCard}
    ${phasesCard}
    ${artifactsCard}
    ${rolesCard}
  `;

  container.querySelectorAll("[data-approval-id]").forEach((button) => {
    button.addEventListener("click", () => updateApproval(Number(button.dataset.approvalId), button.dataset.status));
  });
}

function renderPreview(preview) {
  const modeBadge = document.getElementById("preview-mode");
  const container = document.getElementById("preview-content");

  if (!preview) {
    modeBadge.textContent = "Waiting";
    container.className = "preview-content empty-state";
    container.textContent = "Fill in the exploration brief to preview how the agent will frame the mission before any mission is created.";
    return;
  }

  const objective = preview.objective_profile || {};
  const gainTarget = objective.gain_target || {};
  const costTarget = objective.cost_target || {};
  const uniqueMetrics = Array.from(
    new Set([...(gainTarget.derived_metrics || []), ...(costTarget.derived_metrics || [])])
  );
  const unresolved = preview.unresolved_questions || [];
  const biasControls = preview.bias_controls || [];
  const missionPacket = preview.mission_packet || {};

  modeBadge.textContent = formatLabel(objective.mode || "preview");
  container.className = "preview-content";
  container.innerHTML = `
    <article class="preview-block fade-in">
      <strong>Derived Objective</strong>
      <p>${escapeHtml(missionPacket.goal || "")}</p>
      <div class="preview-tags">
        <span class="preview-tag">Mode: ${escapeHtml(formatLabel(objective.mode || "unknown"))}</span>
        <span class="preview-tag">Domain: ${escapeHtml(formatLabel(preview.domain || "unknown"))}</span>
        <span class="preview-tag">Host: ${escapeHtml(objective.first_evaluation_environment || "unknown")}</span>
      </div>
    </article>

    <article class="preview-block fade-in">
      <strong>Candidate Dimensions</strong>
      <ul class="preview-list">
        <li><strong>Improve:</strong> ${escapeHtml(gainTarget.phrase || missionPacket.goal || "Not derived yet")}</li>
        <li><strong>Reduce:</strong> ${escapeHtml(costTarget.phrase || "No explicit cost phrase detected yet")}</li>
      </ul>
      <div class="preview-tags">
        ${uniqueMetrics.length
          ? uniqueMetrics.map((metric) => `<span class="preview-tag">${escapeHtml(formatLabel(metric))}</span>`).join("")
          : `<span class="preview-tag">Metrics still ambiguous</span>`}
      </div>
    </article>

    <article class="preview-block fade-in">
      <strong>Bias Controls</strong>
      <ul class="preview-list">
        ${biasControls.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </article>

    <article class="preview-block fade-in">
      <strong>Unresolved Questions</strong>
      <ul class="preview-list">
        ${
          unresolved.length
            ? unresolved.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
            : "<li>The intake is specific enough for a governed mission packet.</li>"
        }
      </ul>
    </article>

    <article class="preview-block fade-in">
      <strong>Mission Packet Sent To The Agent</strong>
      <pre class="preview-packet">${escapeHtml(
        JSON.stringify(
          {
            project_name: missionPacket.project_name || "",
            project_kind: missionPacket.project_kind || "",
            goal: missionPacket.goal || "",
            domain: missionPacket.domain || "",
            constraints: missionPacket.constraints || "",
          },
          null,
          2
        )
      )}</pre>
    </article>
  `;
}

async function loadMission(missionId, shouldScroll) {
  state.currentMissionId = missionId;
  const response = await fetch(`/api/missions/${missionId}`);
  const payload = await response.json();
  renderMissionList(state.missions);
  renderMissionDetail(payload.mission || null);
  if (shouldScroll) {
    document.getElementById("mission-detail").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function requestPreview(showStatus = true) {
  const status = document.getElementById("preview-status");
  const formData = collectExplorationFormData();

  if (!formData.goal) {
    state.preview = null;
    renderPreview(null);
    status.textContent = "Add a mission to generate a framing preview.";
    return;
  }

  if (showStatus) {
    status.textContent = "Deriving objective framing...";
  }

  const response = await fetch("/api/exploration/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formData),
  });
  const payload = await response.json();
  if (!response.ok) {
    status.textContent = payload.error || "Unable to derive a preview.";
    return;
  }

  state.preview = payload.preview;
  renderPreview(payload.preview);
  status.textContent = "Preview updated.";
}

async function submitMission(event) {
  event.preventDefault();
  const status = document.getElementById("mission-status");
  const formData = collectExplorationFormData();
  if (!formData.goal) {
    status.textContent = "Mission is required.";
    return;
  }

  status.textContent = "Opening governed mission...";
  const body = {
    mission_name: formData.mission_name,
    project_name: formData.project_name,
    project_kind: formData.project_kind,
    goal: formData.goal,
    domain: formData.domain,
    owner: formData.owner,
    priority: formData.priority,
    constraints: composeMissionConstraints(formData),
    requested_connectors: formData.requested_connectors,
  };
  const response = await fetch("/api/missions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    status.textContent = payload.error || "Unable to create mission.";
    return;
  }
  status.textContent = "Mission created.";
  state.currentMissionId = payload.mission.id;
  await fetchState();
}

async function updateApproval(approvalId, status) {
  const response = await fetch(`/api/approvals/${approvalId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  const payload = await response.json();
  if (!response.ok) {
    return;
  }
  state.currentMissionId = payload.mission?.id || state.currentMissionId;
  await fetchState();
}

async function reloadEnv() {
  await fetch("/api/connectors/reload", { method: "POST" });
  await fetchState();
}

const schedulePreview = debounce(() => {
  requestPreview(false);
}, 360);

document.getElementById("mission-form").addEventListener("submit", submitMission);
document.getElementById("reload-env").addEventListener("click", reloadEnv);
document.getElementById("preview-button").addEventListener("click", () => requestPreview(true));
document.querySelectorAll("#mission-form textarea, #mission-form input, #mission-form select").forEach((element) => {
  const eventName = element.tagName === "SELECT" ? "change" : "input";
  element.addEventListener(eventName, schedulePreview);
});

fetchState().then(() => requestPreview(false));
