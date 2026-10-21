/* CSV download of the predictions (REQ-FD-21, SR-04).
 *
 * The file is built in the browser from the completed job (SADS 2.1) and contains
 * exactly three columns: row_index, predicted_class, fraud_probability. No other column
 * of the uploaded dataset is ever exported.
 */
(function () {
  "use strict";

  function toCsv(job) {
    const lines = ["row_index,predicted_class,fraud_probability"];
    job.predictions.forEach((p) => lines.push(`${p.row},${p.class},${p.probability}`));
    return lines.join("\n") + "\n";
  }

  function addButton(job) {
    const slot = document.getElementById("result-actions");
    if (!slot) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn";
    btn.setAttribute("data-testid", "download-btn");
    btn.textContent = "Download predictions (CSV)";
    btn.addEventListener("click", () => {
      const blob = new Blob([toCsv(job)], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `predictions_${job.model_name}_${job.job_id.slice(0, 8)}.csv`;
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    });
    slot.append(btn);
  }

  window.CCFDResultsHooks = window.CCFDResultsHooks || [];
  window.CCFDResultsHooks.push(addButton);
  window.CCFDDownload = { toCsv };
})();
