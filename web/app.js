const state = {
  connectors: [],
  loadedEnvKeys: [],
  missions: [],
  pendingApprovals: [],
  currentMissionId: null,
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

async function fetchState() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  state.connectors = payload.connectors || [];
  state.loadedEnvKeys = payload.loaded_env_keys || [];
  state.missions = payload.missions || [];
  state.pendingApprovals = payload.pending_approvals || [];

  renderProject(payload.project || {});
  renderOverview(payload.project || {}, state.missions, state.pendingApprovals, payload.children || []);
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

function renderOverview(project, missions, approvals, children) {
  const container = document.getElementById("overview-grid");
  const cards = [
    ["Missions", missions.length],
    ["Approvals", approvals.length],
    ["Children", children.length],
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
    container.innerHTML = `<div class="detail-card"><strong>No missions yet</strong><small>Create a mission to have the boss agent open a governed child workspace.</small></div>`;
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

  const childCard = detailCard(
    "Child Workspace",
    `
      <p><strong>${escapeHtml(child.name || mission.child_name)}</strong></p>
      <p class="path-block">${escapeHtml(child.path || mission.child_path)}</p>
      <p><strong>Requested Connectors</strong><br />${escapeHtml((child.requested_connectors || []).join(", ") || "None")}</p>
      <p><strong>Goal Brief</strong><br />${escapeHtml(child.goal_path || "workspace/goal.md")}</p>
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
      ${childCard}
    </div>
    ${approvalsCard}
    ${phasesCard}
    ${artifactsCard}
    ${rolesCard}
  `;

  container.querySelectorAll("[data-approval-id]").forEach((button) => {
    button.addEventListener("click", () => updateApproval(Number(button.dataset.approvalId), button.dataset.status));
  });
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

async function submitMission(event) {
  event.preventDefault();
  const status = document.getElementById("mission-status");
  status.textContent = "Opening governed mission...";
  const requestedConnectors = Array.from(document.querySelectorAll('input[name="connector"]:checked')).map((input) => input.value);
  const body = {
    mission_name: document.getElementById("mission-name").value.trim(),
    goal: document.getElementById("goal").value.trim(),
    domain: document.getElementById("domain").value,
    owner: document.getElementById("owner").value.trim(),
    priority: document.getElementById("priority").value,
    constraints: document.getElementById("constraints").value.trim(),
    requested_connectors: requestedConnectors,
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
  document.getElementById("mission-form").reset();
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

document.getElementById("mission-form").addEventListener("submit", submitMission);
document.getElementById("reload-env").addEventListener("click", reloadEnv);
fetchState();
