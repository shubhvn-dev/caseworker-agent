const API_URL = window.location.hostname === "localhost" 
  ? "http://localhost:8000" 
  : "https://caseworker-agent.onrender.com";


const inputJson = document.getElementById("inputJson");
const loadSampleBtn = document.getElementById("loadSample");
const loadSavedBtn = document.getElementById("loadSaved");
const runAgentBtn = document.getElementById("runAgent");
const resultsSection = document.getElementById("resultsSection");
const resultsBody = document.querySelector("#resultsTable tbody");
const modal = document.getElementById("modal");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");
const closeModalBtn = document.getElementById("closeModal");
const singleSubject = document.getElementById("singleSubject");
const singleBody = document.getElementById("singleBody");
const runSingleAgentBtn = document.getElementById("runSingleAgent");


let currentResults = [];


loadSampleBtn.addEventListener("click", async () => {
  const res = await fetch(`${API_URL}/sample-cases`);
  const data = await res.json();
  inputJson.value = JSON.stringify(data.cases, null, 2);
});


loadSavedBtn.addEventListener("click", async () => {
  const res = await fetch(`${API_URL}/cases`);
  const data = await res.json();

  if (data.cases.length === 0) {
    alert("No saved cases yet. Run the agent first.");
    return;
  }

  currentResults = data.cases;
  renderResults();
  renderHotTopics();
});


runAgentBtn.addEventListener("click", async () => {
  let cases;
  try {
    cases = JSON.parse(inputJson.value);
  } catch (e) {
    alert("Invalid JSON. Please check your input.");
    return;
  }

  runAgentBtn.disabled = true;
  runAgentBtn.textContent = "Processing...";

  try {
    const res = await fetch(`${API_URL}/run-agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cases),
    });

    if (res.status === 429) {
      const err = await res.json();
      alert(err.detail || "Rate limit exceeded. Try again tomorrow.");
      return;
    }

    const data = await res.json();
    currentResults = data.results;
    renderResults();
    renderHotTopics();
  } catch (e) {
    alert("Error calling API: " + e.message);
  } finally {
    runAgentBtn.disabled = false;
    runAgentBtn.textContent = "Run Agent on Batch";
  }
});


runSingleAgentBtn.addEventListener("click", async () => {
  const subject = singleSubject.value.trim();
  const body = singleBody.value.trim();

  if (!subject || !body) {
    alert("Please enter both subject and message.");
    return;
  }

  const id = "single-" + Date.now();

  runSingleAgentBtn.disabled = true;
  runSingleAgentBtn.textContent = "Processing...";

  try {
    const res = await fetch(`${API_URL}/run-agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify([{ id, subject, body }]),
    });

    if (res.status === 429) {
      const err = await res.json();
      alert(err.detail || "Rate limit exceeded. Try again tomorrow.");
      return;
    }

    const data = await res.json();

    currentResults = [...data.results, ...currentResults];
    renderResults();
    renderHotTopics();

    singleSubject.value = "";
    singleBody.value = "";
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    runSingleAgentBtn.disabled = false;
    runSingleAgentBtn.textContent = "Run Agent";
  }
});


function renderResults() {
  resultsBody.innerHTML = "";
  resultsSection.style.display = "block";

  currentResults.forEach((r, idx) => {
    const row = document.createElement("tr");

    const path = `${r.tags.tier1} → ${r.tags.tier2} → ${r.tags.tier3} → ${r.tags.tier4}`;

    const issueAreaClass = r.issue_area.toLowerCase().replace(" ", "-");

    const stepCount = r.action_plan ? r.action_plan.length : 0;
    let currentStep = stepCount;

    if (r.action_plan) {
      for (let i = 0; i < r.action_plan.length; i++) {
        if (r.action_plan[i].status === "pending" || r.action_plan[i].status === "waiting") {
          currentStep = i + 1;
          break;
        }
      }
    }

    const currentAction =
      r.action_plan && r.action_plan[currentStep - 1]
        ? r.action_plan[currentStep - 1].action
        : "N/A";

    row.innerHTML = `
      <td>${r.id}</td>
      <td><span class="issue-badge ${issueAreaClass}">${r.issue_area}</span></td>
      <td><span class="sentiment-badge ${r.sentiment}">${r.sentiment}</span></td>
      <td class="path-cell">${path}</td>
      <td>
        <button class="action-progress-btn" data-idx="${idx}">
          <span class="progress-label">Step ${currentStep}/${stepCount}</span>
          <span class="progress-action">${currentAction}</span>
        </button>
      </td>
      <td><button class="view-btn" data-idx="${idx}">View Details</button></td>
    `;

    resultsBody.appendChild(row);
  });

  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const idx = e.target.dataset.idx;
      showCaseDetails(currentResults[idx]);
    });
  });

  document.querySelectorAll(".action-progress-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const idx = e.target.closest(".action-progress-btn").dataset.idx;
      showCaseDetails(currentResults[idx], "timeline");
    });
  });
}


function showCaseDetails(result, defaultTab = "timeline") {
  modalTitle.textContent = `Case #${result.id}`;

  let firstPendingFound = false;

  const timelineHtml =
    result.action_plan && result.action_plan.length > 0
      ? `<div class="timeline">
          ${result.action_plan
            .map((step, i) => {
              let showButton = false;
              if ((step.status === "pending" || step.status === "waiting") && !firstPendingFound) {
                showButton = true;
                firstPendingFound = true;
              }
              return `
                <div class="timeline-step ${step.status}">
                  <div class="timeline-dot"></div>
                  <div class="timeline-header">
                    <span class="timeline-action">${i + 1}. ${step.action}</span>
                    <span class="timeline-days">${
                      step.days_from_now === 0 ? "Today" : `Day ${step.days_from_now}`
                    }</span>
                  </div>
                  <div class="timeline-desc">${step.description}</div>
                  <div class="timeline-footer">
                    <span class="timeline-status ${step.status}">${step.status}</span>
                    ${
                      showButton
                        ? `<button class="mark-complete-btn" data-case-id="${result.id}">Mark Complete</button>`
                        : ""
                    }
                  </div>
                </div>
              `;
            })
            .join("")}
        </div>`
      : `<p>No action plan available.</p>`;

  document.getElementById("timelineTab").innerHTML = timelineHtml;

  document.querySelectorAll(".mark-complete-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const caseId = e.target.dataset.caseId;
      e.target.disabled = true;
      e.target.textContent = "Updating...";

      try {
        const res = await fetch(`${API_URL}/cases/${caseId}/advance`, {
          method: "POST",
        });

        if (res.status === 429) {
          const err = await res.json();
          alert(err.detail || "Rate limit exceeded. Try again later.");
          e.target.disabled = false;
          e.target.textContent = "Mark Complete";
          return;
        }

        const data = await res.json();

        if (data.success) {
          const idx = currentResults.findIndex((r) => r.id === caseId);
          if (idx >= 0) {
            currentResults[idx] = data.case;
          }
          renderResults();
          renderHotTopics();
          showCaseDetails(data.case, "timeline");
        } else {
          alert("Failed to update case");
        }
      } catch (err) {
        alert("Error: " + err.message);
        e.target.disabled = false;
        e.target.textContent = "Mark Complete";
      }
    });
  });

  const draftsContainer = document.getElementById("draftsTab");
  draftsContainer.innerHTML = '<p class="loading">Loading drafts for current stage...</p>';

  fetchStageDrafts(result).then(({ drafts, current_stage }) => {
    if (!drafts || drafts.length === 0) {
      draftsContainer.innerHTML = '<p>No drafts available.</p>';
      return;
    }

    const draftsHtml = `
      <div class="stage-indicator">📍 Current Stage: Step ${current_stage}</div>
      ${drafts.map((d, i) => {
        const recipientClass = d.recipient.toLowerCase().includes('agency') 
          ? 'agency' 
          : d.recipient.toLowerCase().includes('supervisor') 
            ? 'supervisor' 
            : 'constituent';
        return `
          <div class="draft-card">
            <div class="draft-header">
              <span class="draft-type">${formatLetterType(d.type)}</span>
              <span class="draft-recipient-tag ${recipientClass}">To: ${d.recipient}</span>
            </div>
            <div class="draft-body">${d.content}</div>
            <button class="copy-btn" data-draft="${i}">📋 Copy to Clipboard</button>
          </div>
        `;
      }).join('')}
    `;

    draftsContainer.innerHTML = draftsHtml;
    draftsContainer.draftsData = drafts;

    draftsContainer.querySelectorAll(".copy-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const idx = e.target.dataset.draft;
        const draft = draftsContainer.draftsData[idx];
        navigator.clipboard.writeText(draft.content).then(() => {
          e.target.textContent = "✓ Copied!";
          setTimeout(() => (e.target.textContent = "📋 Copy to Clipboard"), 1500);
        });
      });
    });
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => btn.classList.remove("active"));
  document.querySelector(`.tab-btn[data-tab="${defaultTab}"]`).classList.add("active");
  document.getElementById("timelineTab").style.display = defaultTab === "timeline" ? "block" : "none";
  document.getElementById("draftsTab").style.display = defaultTab === "drafts" ? "block" : "none";

  modal.style.display = "flex";
}


document.addEventListener("click", (e) => {
  if (e.target.classList.contains("tab-btn")) {
    const tab = e.target.dataset.tab;

    document.querySelectorAll(".tab-btn").forEach((btn) => btn.classList.remove("active"));
    e.target.classList.add("active");

    document.getElementById("timelineTab").style.display = tab === "timeline" ? "block" : "none";
    document.getElementById("draftsTab").style.display = tab === "drafts" ? "block" : "none";
  }
});


function renderHotTopics() {
  const hotTopicsSection = document.getElementById("hotTopicsSection");
  hotTopicsSection.style.display = "block";

  const issueAreaCounts = {};
  const problemCounts = {};
  const sentimentCounts = {};

  currentResults.forEach((r) => {
    issueAreaCounts[r.issue_area] = (issueAreaCounts[r.issue_area] || 0) + 1;
    const problem = r.tags.tier4;
    problemCounts[problem] = (problemCounts[problem] || 0) + 1;
    sentimentCounts[r.sentiment] = (sentimentCounts[r.sentiment] || 0) + 1;
  });

  const total = currentResults.length;

  document.getElementById("issueAreaStats").innerHTML = renderStatBars(issueAreaCounts, total);
  document.getElementById("problemStats").innerHTML = renderStatBars(problemCounts, total);
  document.getElementById("sentimentStats").innerHTML = renderStatBars(sentimentCounts, total);
}


function renderStatBars(counts, total) {
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);

  return sorted
    .map(([label, count]) => {
      const percent = Math.round((count / total) * 100);
      return `
        <div class="stat-row">
          <span class="stat-label">${label}</span>
          <span class="stat-count">${count}</span>
        </div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: ${percent}%"></div>
        </div>
      `;
    })
    .join("");
}


async function fetchStageDrafts(caseData) {
  try {
    const res = await fetch(`${API_URL}/generate-drafts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ caseData })
    });
    return await res.json();
  } catch (e) {
    console.error("Error fetching drafts:", e);
    return { drafts: [], current_stage: 1 };
  }
}


function formatLetterType(type) {
  const labels = {
    acknowledgment: "📨 Acknowledgment Letter",
    agency_inquiry: "🏛️ Agency Inquiry",
    followup: "📝 Follow-up Letter",
    escalation: "⚠️ Escalation Letter",
    resolution: "✅ Resolution Notice"
  };
  return labels[type] || type;
}


closeModalBtn.addEventListener("click", () => {
  modal.style.display = "none";
});


modal.addEventListener("click", (e) => {
  if (e.target === modal) modal.style.display = "none";
});
