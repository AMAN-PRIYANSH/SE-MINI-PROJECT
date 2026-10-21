/* Results view (REQ-FD-17, REQ-FD-18, REQ-FD-19, REQ-FD-20, REQ-UI-05).
 *
 * Shows, for a completed job: the executed model's name, the five metrics and the
 * confusion matrix (all labelled with that model), and the per-row predictions in a
 * table of 50 rows per page. Only row index, predicted class and fraud probability are
 * ever displayed (SR-04).
 */
(function () {
  "use strict";

  const PAGE_SIZE = 50;
  const METRICS = [
    ["accuracy", "Accuracy"],
    ["precision", "Precision"],
    ["recall", "Recall"],
    ["f1", "F1-score"],
    ["roc_auc", "ROC-AUC"],
  ];

  let current = null;  // {job, page}
  window.__ccfdRenderMs = [];

  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === "text") e.textContent = v;
      else if (k === "class") e.className = v;
      else e.setAttribute(k, v);
    });
    (children || []).forEach((c) => e.append(c));
    return e;
  }

  const fmt = (v) => (v === null || v === undefined ? "n/a" : Number(v).toFixed(4));

  function metricTiles(job) {
    const grid = el("div", { class: "metric-grid", "data-testid": "metrics" });
    METRICS.forEach(([key, label]) => {
      const v = job.metrics[key];
      const tile = el("div", { class: "metric", "data-metric": key }, [
        el("div", { class: "label", text: label }),
        el("div", { class: "value", text: fmt(v), "data-testid": "metric-" + key }),
      ]);
      if (v === null) tile.title = "Undefined: the dataset contains only one class.";
      grid.append(tile);
    });
    return grid;
  }

  function confusionMatrix(job) {
    const cm = job.metrics.confusion_matrix;
    const cell = (cls, key, label) =>
      el("td", { class: cls, "data-testid": "cm-" + key, title: label }, [
        el("strong", { text: String(cm[key]) }), el("div", { class: "hint", text: label }),
      ]);
    return el("div", {}, [
      el("h3", { text: "Confusion matrix" }),
      el("table", { class: "cm", "data-testid": "confusion-matrix" }, [
        el("tr", {}, [el("th", { text: "" }), el("th", { text: "Predicted fraud (1)" }),
                      el("th", { text: "Predicted legitimate (0)" })]),
        el("tr", {}, [el("th", { text: "Actual fraud (1)" }), cell("hit", "tp", "true positives"),
                      cell("miss", "fn", "false negatives")]),
        el("tr", {}, [el("th", { text: "Actual legitimate (0)" }), cell("miss", "fp", "false positives"),
                      cell("hit", "tn", "true negatives")]),
      ]),
    ]);
  }

  function pageCount(job) {
    return Math.max(1, Math.ceil(job.predictions.length / PAGE_SIZE));
  }

  function predictionsTable() {
    const { job, page } = current;
    const start = (page - 1) * PAGE_SIZE;
    const rows = job.predictions.slice(start, start + PAGE_SIZE);
    const tbody = el("tbody");
    rows.forEach((p) => {
      tbody.append(el("tr", { class: p.class === 1 ? "fraud" : "" }, [
        el("td", { text: String(p.row) }),
        el("td", {}, [el("span", { class: "pill pill-" + p.class, text: p.class === 1 ? "1 fraud" : "0 legit" })]),
        el("td", { text: Number(p.probability).toFixed(4) }),
      ]));
    });
    const table = el("table", { class: "preds", "data-testid": "predictions-table" }, [
      el("thead", {}, [el("tr", {}, [el("th", { text: "Row index" }), el("th", { text: "Predicted class" }),
                                     el("th", { text: "Fraud probability" })])]),
      tbody,
    ]);
    const total = job.predictions.length;
    const pages = pageCount(job);
    const prev = el("button", { class: "btn", type: "button", "data-testid": "page-prev", text: "‹ Previous" });
    const next = el("button", { class: "btn", type: "button", "data-testid": "page-next", text: "Next ›" });
    prev.disabled = page <= 1;
    next.disabled = page >= pages;
    prev.addEventListener("click", () => goTo(page - 1));
    next.addEventListener("click", () => goTo(page + 1));
    const info = el("span", {
      "data-testid": "page-info",
      text: `Rows ${total ? start + 1 : 0}–${start + rows.length} of ${total} · Page ${page} of ${pages}`,
    });
    return el("div", { id: "predictions-block" }, [
      el("h3", { text: "Predictions" }),
      el("div", { class: "table-wrap" }, [table]),
      el("div", { class: "pager" }, [info, prev, next]),
    ]);
  }

  function goTo(page) {
    current.page = Math.min(Math.max(1, page), pageCount(current.job));
    document.getElementById("predictions-block").replaceWith(predictionsTable());
  }

  function showCompleted(job) {
    const t0 = performance.now();
    current = { job, page: 1 };
    const body = document.getElementById("results-body");
    body.textContent = "";
    const head = el("div", { class: "result-head" }, [
      el("p", { class: "model-name" }, [
        document.createTextNode("Metrics and predictions of model "),
        el("span", { "data-testid": "model-name", text: job.model_name }),
      ]),
      el("div", { id: "result-actions" }),
    ]);
    body.append(head, metricTiles(job),
                el("div", { class: "result-cols" }, [confusionMatrix(job), predictionsTable()]));
    if (window.CCFDResultsHooks) window.CCFDResultsHooks.forEach((fn) => fn(job, body));
    window.__ccfdRenderMs.push(performance.now() - t0);
  }

  window.CCFDResults = { showCompleted, PAGE_SIZE };
})();
