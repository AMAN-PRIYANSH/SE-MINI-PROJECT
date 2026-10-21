/* Web Client controller: API key, upload, model selection, run control, status polling.
 *
 * SR-03: the API key is held only in this script's memory for the open page. It is never
 * written to cookies, localStorage or sessionStorage, so it must be re-entered after a reload.
 */
(function () {
  "use strict";

  const POLL_MS = 2000;          // SRS 3.4: poll every 2 seconds while queued or running
  const TERMINAL = ["completed", "failed"];

  const state = {
    apiKey: "",                  // memory only (SR-03)
    datasetId: null,
    datasetRows: null,
    jobId: null,
    pollTimer: null,
  };
  // Poll timestamps, readable by the browser tests (TC-JOB-02 interval check)
  window.__ccfdPolls = [];

  const $ = (id) => document.getElementById(id);

  function setMsg(id, text, kind) {
    const el = $(id);
    el.textContent = text || "";
    el.className = "field-msg" + (kind ? " " + kind : "");
  }

  function setBadge(status) {
    const b = $("status-badge");
    b.textContent = status;
    b.className = "badge badge-" + status;
  }

  function setFacts(pairs) {
    const dl = $("run-facts");
    dl.textContent = "";
    pairs.forEach(([k, v]) => {
      if (v === null || v === undefined) return;
      const dt = document.createElement("dt");
      dt.textContent = k;
      const dd = document.createElement("dd");
      dd.textContent = v;
      dl.append(dt, dd);
    });
  }

  function readKey() {
    state.apiKey = $("api-key").value.trim();
    if (!state.apiKey) {
      setMsg("api-key-msg", "Enter the API key first.", "error");
      return false;
    }
    setMsg("api-key-msg", "");
    return true;
  }

  async function api(method, path, body) {
    const headers = { Authorization: "Bearer " + state.apiKey };
    let payload;
    if (body instanceof FormData) {
      payload = body;
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
    let resp;
    try {
      resp = await fetch(path, { method, headers, body: payload });
    } catch (e) {
      return { status: 0, body: { code: "NETWORK", message: "The server cannot be reached." } };
    }
    let data = null;
    try { data = await resp.json(); } catch (e) { data = null; }
    if (resp.status === 401) {
      setMsg("api-key-msg", "The API key was rejected. Check it and try again.", "error");
    }
    return { status: resp.status, body: data || { message: "Unexpected response from the server." } };
  }

  // ------------------------------------------------------------------ upload (REQ-FD-01)
  async function upload() {
    setMsg("upload-msg", "");
    if (!readKey()) return;
    const input = $("file-input");
    if (!input.files || input.files.length !== 1) {
      setMsg("upload-msg", "Choose one .csv file to upload.", "error");
      return;
    }
    const form = new FormData();
    form.append("file", input.files[0]);
    $("upload-btn").disabled = true;
    setMsg("upload-msg", "Uploading and validating…");
    const r = await api("POST", "/api/datasets", form);
    $("upload-btn").disabled = false;
    if (r.status === 201) {
      state.datasetId = r.body.dataset_id;
      state.datasetRows = r.body.rows;
      setMsg("upload-msg", `Dataset accepted: ${r.body.rows.toLocaleString()} rows.`, "ok");
      setFacts([["dataset_id", state.datasetId], ["rows", state.datasetRows]]);
    } else {
      state.datasetId = null;
      // REQ-UI-02: the error is shown next to the control that caused it
      setMsg("upload-msg", r.body.message || "Upload failed.", "error");
    }
  }

  // ------------------------------------------------------------------ run (REQ-FD-06, BR-02)
  function selectedModel() {
    const el = document.querySelector('input[name="model"]:checked');
    return el ? el.value : null;
  }

  async function run() {
    setMsg("run-msg", "");
    setMsg("model-msg", "");
    const model = selectedModel();
    if (!model) {
      setMsg("model-msg", "Select a model (ML, DL or QML) before running.", "error");
      return;  // no request is sent (TC-MOD-01)
    }
    if (!state.datasetId) {
      setMsg("run-msg", "Upload a dataset before running.", "error");
      return;
    }
    if (!readKey()) return;
    stopPolling();
    $("run-btn").disabled = true;
    const r = await api("POST", "/api/analyses", { dataset_id: state.datasetId, model_type: model });
    if (r.status !== 202) {
      $("run-btn").disabled = false;
      setMsg("run-msg", r.body.message || "The run could not be started.", "error");
      return;
    }
    state.jobId = r.body.job_id;
    setBadge(r.body.status);
    setFacts([["dataset_id", state.datasetId], ["rows", state.datasetRows],
              ["job_id", state.jobId], ["model_type", model]]);
    showPending(model);
    schedulePoll();
  }

  // ------------------------------------------------------------------ polling (REQ-UI-03, REQ-FD-20)
  function schedulePoll() {
    state.pollTimer = setTimeout(poll, POLL_MS);
  }

  function stopPolling() {
    if (state.pollTimer) clearTimeout(state.pollTimer);
    state.pollTimer = null;
  }

  async function poll() {
    const jobId = state.jobId;
    window.__ccfdPolls.push(Date.now());
    const r = await api("GET", "/api/analyses/" + encodeURIComponent(jobId));
    if (jobId !== state.jobId) return;  // a newer run replaced this one
    if (r.status !== 200) {
      $("run-btn").disabled = false;
      setMsg("run-msg", r.body.message || "Status could not be read.", "error");
      return;
    }
    setBadge(r.body.status);
    if (TERMINAL.includes(r.body.status)) {
      stopPolling();
      $("run-btn").disabled = false;
      if (r.body.status === "completed") {
        if (window.CCFDResults) window.CCFDResults.showCompleted(r.body);
        else showSimpleCompleted(r.body);
      } else {
        showFailed(r.body);
      }
      return;
    }
    schedulePoll();
  }

  // ------------------------------------------------------------------ result placeholders
  function resultsBody() {
    const body = $("results-body");
    body.textContent = "";
    return body;
  }

  function showPending(model) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = `Running the ${model.toUpperCase()} model… results appear here automatically.`;
    resultsBody().append(p);
  }

  function showSimpleCompleted(job) {
    const p = document.createElement("p");
    p.textContent = `${job.model_name}: ${job.predictions.length} predictions.`;
    resultsBody().append(p);
  }

  function showFailed(job) {
    const box = document.createElement("div");
    box.className = "failure";
    box.setAttribute("data-testid", "failure-reason");
    const strong = document.createElement("strong");
    strong.textContent = "Run failed: ";
    box.append(strong, document.createTextNode(job.reason ? job.reason.message : "unknown reason"));
    const hint = document.createElement("p");
    hint.className = "hint";
    hint.textContent = "No predictions or metrics are shown for a failed run. You can start a new run.";
    resultsBody().append(box, hint);
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("upload-btn").addEventListener("click", upload);
    $("run-btn").addEventListener("click", run);
  });
})();
