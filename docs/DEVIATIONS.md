# Deviations from the submitted Part-1 documents

Part-2 brief, item 2i: *"Deviations from the submitted document should be documented and explained
during the final demo."*

This file lists every place where the built system (Release 1.0) differs from **SRS v1.2**,
**SADS v1.1** or **STP v1.1**. For each one it gives what the document said, what was built, and why.
Problems found *inside* the Part-1 documents themselves are listed in
[PART1_ERRATA.md](PART1_ERRATA.md).

Summary: no functional requirement was dropped. All 22 REQ-FD, 6 REQ-UI and 5 REQ-API
requirements are implemented. The deviations are about versions, code layout, details the
documents left open, and the process.

## A. Product deviations

| ID | Document and section | Documented | Built | Why |
|---|---|---|---|---|
| D-01 | SRS 2.4, STP 11 | Python 3.10+ | **Python 3.12+** | The pinned NumPy 2.5.3 and SciPy 1.18.1 (and scikit-learn 1.9, pandas 3.0) no longer support 3.10/3.11. The pins are needed so that the saved models load identically on every machine (SRS D1) |
| D-02 | SADS 3.4 | Each service folder has its own `server.py`, `dataset_reader.py`, `model_loader.py`, `predictor.py`, `metrics.py` | One shared implementation in `services/common/` (HTTP contract, dataset reader, predictor base) and `shared/metrics.py`. Each service folder holds only its `server.py` (model loading and prediction) and its model files | Three copies of the same contract could drift apart. A single implementation guarantees the uniform IPredict contract of NFR-Q02 by construction. The training scripts also reuse `shared/metrics.py`, so offline and online metrics are computed identically |
| D-03 | SADS 3.4 | The purge task lives in `store.py`; error handling lives in `app.py` | Purge task in `server/retention.py`, error taxonomy in `server/errors.py` | Smaller modules. The behaviour is exactly SADS 2.4 item 4 and SADS 3.3 |
| D-04 | SADS 3.4 (client) | Web Client = `index.html`, `style.css`, `app.js` | Adds `results.js` (results view), `download.js` (CSV export) and `help.html` (user manual) | Keeps each file focused. There is still no build toolchain and still one stylesheet (REQ-UI-06) |
| D-05 | SRS REQ-FD-08 | DL baseline: multilayer perceptron | MLP (64 and 32 ReLU units, Adam, early stopping) implemented with **scikit-learn** `MLPClassifier` | It is the documented model. Using scikit-learn avoids a ~700 MB deep-learning framework that the CI runners and the reference machine would have to install |
| D-06 | SRS REQ-FD-09, TBD-03 | "At least one QML classifier on a circuit simulator"; simulator not chosen | 4-qubit variational quantum classifier on **PennyLane 0.45.1 `default.qubit`**. Features are reduced to 4 PCA components (one per qubit) and the model is trained on a balanced sample of 794 rows | Resolves TBD-03. Simulating more qubits, or training on all 227k rows, is too slow for a lab project. The cost: QML is clearly weaker (test F1 0.34 against 0.83 for Random Forest). It is a working quantum baseline, and that comparison is itself a result of the project |
| D-07 | SADS 2.4 item 4 | Owner-only permissions: 0700/0600 on Linux, "an equivalent ACL on Windows" | 0700/0600 on Linux and macOS. On Windows the store inherits the ACL of the user's profile folder, and no explicit ACL is set | Setting Windows ACLs needs `pywin32` or `icacls` calls that were out of scope for Release 1.0. Mitigation: keep `CCFD_STORE_DIR` under the service account's own profile. Planned for a later release together with TBD-02 |
| D-08 | SRS REQ-FD-15 | ROC-AUC always reported to 4 d.p. | ROC-AUC is `null` in the API and "n/a" in the UI **when the dataset contains only one class** | ROC-AUC is mathematically undefined without both classes. Returning a made-up number would break BR-04 |
| D-09 | SADS 3.2 example | Probabilities shown with 4 decimals, e.g. `0.0132` | The API returns probabilities rounded to **6** decimals; the UI shows 4 | Keeps enough precision for an independent recomputation of ROC-AUC from the returned values (TC-MET-01). The class is derived from the rounded value, so the prediction and the probability never disagree |
| D-10 | SADS 3.3 lifecycle | Only the transitions queued → running → completed/failed | Added: when the Web Server starts, jobs left queued/running by a previous process are marked **failed** with `MODEL_SERVICE_ERROR` | Without this, a server restart would leave jobs "running" forever and the client would poll them for ever. This is consistent with REQ-FD-14 and BR-04 |
| D-11 | SADS 3.3, REQ-FD-14 | Timeout = no response within 600 s | Implemented as a **hard overall deadline** around the whole HTTP call | A plain socket read timeout would never fire for a service that keeps sending bytes slowly |
| D-12 | SRS REQ-FD-04 | Three example messages | More named reasons: empty file, no header, duplicate column, row limit, malformed rows, invalid label at row N, non-numeric value at row N, no file part, more than one file | Each new message still names the reason and never echoes a cell value (SR-04). The user manual lists all of them |
| D-13 | SRS 2.5, SADS 2.5 | Production deployment not specified | The Flask/Werkzeug threaded server is used for all four processes | Single-host lab deployment. A production WSGI server and TLS belong to TBD-02 (out of scope) |
| D-14 | (new) | — | `run_all.py` generates a random API key and prints it if `CCFD_API_KEY` is not set | Convenience for the demo. The key still lives only in the environment of the processes (SADS 2.4), never in source code |

## B. Test deviations (STP v1.1)

| ID | STP section | Documented | Done | Why |
|---|---|---|---|---|
| T-01 | 7 (schedule), 6 (effort) | 57 manual cases executed by four people over three days (31.5 person-hours) | **56 of 57 cases automated** with pytest (API, integration and browser tests). They run on every pull request in GitHub Actions on Ubuntu and Windows | Repeatable on every change. The STP's estimates were for manual execution, so the actual effort is reported separately in TEST_REPORT.md |
| T-02 | TC-SAFE-04 | Usability walkthrough with a classmate outside the team | **Not executed yet.** Kept open as issue #33, with the protocol in `docs/USABILITY_WALKTHROUGH.md` | It needs a real first-time user and cannot be automated. Planned for Sprint 2 (Raghav) |
| T-03 | TC-JOB-06, TC-SEC-06, TC-SEC-09 | Substitutions allowed by STP section 13 | Timeout 600 s → 1 s, size limit 500 MB → 100 KB, retention 24 h → 2 s (purge interval 10 min → 0.2 s) | As allowed by the STP. The assertion logic is unchanged |
| T-04 | TC-JOB-04 | Read both jobs again 30 minutes later | Read again immediately after completion | Waiting 30 minutes in CI adds nothing. Results are read from files that only the purge task deletes, and TC-SEC-09 tests that separately |
| T-05 | TC-PERF-03, TC-PERF-06 | Measured from upload completion using the server log timestamp | Measured on the client, over HTTP to a server on the same host | It is an upper bound (it includes the local transfer). The target is met even so |
| T-06 | NFR-Q04 smoke test | Run once on Windows 10/11 and once on Ubuntu 20.04+ | The whole automated suite runs on GitHub's `windows-latest` and `ubuntu-latest` runners on every PR | Stronger than a one-off smoke test. The runners are Windows Server, not desktop Windows 11 |
| T-07 | 4 (test data) | Synthetic CSVs only | All test files are synthetic: sampled from per-class Gaussian statistics of the public, anonymised Kaggle data. The **models** are trained on the Kaggle data itself, which is downloaded and not shipped | The models need real (anonymised) data to learn anything. No real or anonymised transaction is shipped with the system (NFR-S03) |

## C. Process deviations (Part-2 brief)

| ID | Brief | Planned | What happened |
|---|---|---|---|
| P-01 | 1 (ETA 12 Oct) | Backlog, story points and assignment by 12 Oct; dry-run week 12-16 Oct | The backlog (34 issues), milestones and the Project board were created on **22 Oct**, during Sprint 1. There was no dry-run sprint |
| P-02 | 1d, 2c | Each story assigned to, and its PR raised by, its member | Two team members were away during Sprint 1, so **Aman Priyansh implemented and raised every PR**. The planned owner of each story is kept as a label (`owner:akshat`, `owner:aman`, `owner:aditya`, `owner:raghav`). On GitHub every issue is assigned to the only account available (AMAN-PRIYANSH) |
| P-03 | 2d | Repo owners review and merge | The owner merged each PR after the CI checks passed. Self-review only, because no second reviewer was available |
| P-04 | 2e | GPTs may be used to implement | An AI assistant was used to write code, tests and documentation. Every change went through tests and CI |
