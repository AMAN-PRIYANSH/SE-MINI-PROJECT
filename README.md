# Credit Card Fraud Detection and Model Performance Evaluation System

SE Mini-Project, Team **Error 404** (PES University, B.Tech AIML, Section A).

You upload a labelled credit-card transaction CSV, pick an **ML**, **DL** or **QML** model, and run
fraud detection as a background job. The system then shows a prediction for every row, along with
accuracy, precision, recall, F1-score, ROC-AUC and the confusion matrix.

This README is the **developer README** promised in SRS section 2.6, item 3. End users should read the
[user manual](docs/USER_MANUAL.md), which is also shown in the app through the *Help* link.

| Document | File |
|---|---|
| SRS v1.2 (Part 1) | [docs/part-1/SRS_Error-404_v1.2.pdf](docs/part-1/SRS_Error-404_v1.2.pdf) |
| Architecture & Design (SADS) v1.1 (Part 1) | [docs/part-1/SADS_Error-404_v1.1.pdf](docs/part-1/SADS_Error-404_v1.1.pdf) |
| Test Plan (STP) v1.1 (Part 1) | [docs/part-1/STP_Error-404_v1.1.pdf](docs/part-1/STP_Error-404_v1.1.pdf) |
| User manual | [docs/USER_MANUAL.md](docs/USER_MANUAL.md) |
| Deviations from the Part-1 documents | [docs/DEVIATIONS.md](docs/DEVIATIONS.md) |
| Part-1 errata (problems found and fixed) | [docs/PART1_ERRATA.md](docs/PART1_ERRATA.md) |
| Test execution report (STP section 10) | [docs/TEST_REPORT.md](docs/TEST_REPORT.md) |
| Sprint plan and backlog | [docs/SPRINT_PLAN.md](docs/SPRINT_PLAN.md) |
| Release notes and freeze | [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md) |
| Usability walkthrough protocol (TC-SAFE-04) | [docs/USABILITY_WALKTHROUGH.md](docs/USABILITY_WALKTHROUGH.md) |
| Demo videos (Sprint 1: 1 min, Sprint 2: 2 min) | [docs/videos/](docs/videos/) |

---

## 1. Architecture

The system has three tiers (SADS 2.2), and each component runs as its own process on one host
(SADS 2.5):

```
Browser (Web Client: HTML/CSS/JS)
      |  REST + JSON, Authorization: Bearer <API key>
      v
Flask Web Server :5000  -- auth, validation, async jobs, dataset store, retention purge
      |  POST /predict {dataset_id}   (loopback only)
      +--> ML  service :5001  Random Forest / Logistic Regression (scikit-learn)
      +--> DL  service :5002  multilayer perceptron (scikit-learn MLP)
      +--> QML service :5003  4-qubit variational quantum classifier (PennyLane simulator)
                 ^
                 | each service reads datasets/<dataset_id>.csv (read-only)
          dataset store (data_store/: datasets/, jobs/, results/)
```

| Folder | Contents (SADS 3.4) |
|---|---|
| `server/` | `app.py` (factory), `routes.py`, `auth.py`, `validator.py`, `jobs.py`, `store.py`, `retention.py`, `errors.py` |
| `services/common/` | the IPredict HTTP contract shared by all three services, plus the dataset reader and predictor base |
| `services/ml`, `services/dl`, `services/qml` | one `server.py` per service, with its trained model in `model/` |
| `client/` | `index.html`, `style.css`, `app.js`, `results.js`, `download.js`, `help.html` |
| `shared/` | configuration (environment variables), dataset schema, metrics |
| `training/` | the scripts that trained the models (training is outside the product, SRS A4) |
| `tests/` | pytest suite named after the STP test-case IDs; `tests/ui` (browser), `tests/perf` (performance) |

## 2. Requirements

- **Python 3.12 or newer** on Windows 10/11 or Ubuntu 20.04+, with 8 GB RAM (SRS 2.4).
  (SRS 2.4 says 3.10+. The pinned NumPy/SciPy need 3.12; see [DEVIATIONS](docs/DEVIATIONS.md) D-01.)
- A current Chrome, Firefox or Edge.

The exact library versions are pinned in [requirements.txt](requirements.txt): Flask 3.1.3,
requests 2.34.2, NumPy 2.5.3, pandas 3.0.5, SciPy 1.18.1, scikit-learn 1.9.1, joblib 1.6.0 and
PennyLane 0.45.1. Test tools are in `requirements-dev.txt` (pytest, flake8, Playwright).

## 3. Install and run

```bash
git clone https://github.com/AMAN-PRIYANSH/SE-MINI-PROJECT.git
cd SE-MINI-PROJECT
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python run_all.py
```

`run_all.py` starts the Web Server and the three model services as separate processes and prints an
API key. Open <http://127.0.0.1:5000/>, paste the key, and upload
`data/samples/sample_transactions.csv`, a synthetic dataset with 2,000 rows.

To start one component on its own:

```bash
python -m services.ml.server     # :5001
python -m services.dl.server     # :5002
python -m services.qml.server    # :5003
CCFD_API_KEY=secret python -m server.app   # :5000
```

## 4. Configuration (environment variables)

Every setting comes from the environment, so no secret is ever written in source code (SADS 2.4).

| Variable | Default | Meaning |
|---|---|---|
| `CCFD_API_KEY` | *(required)* | The API key every REST call must send as `Authorization: Bearer <key>`. `run_all.py` generates one if it is unset |
| `CCFD_HOST` / `CCFD_PORT` | `127.0.0.1` / `5000` | Web Server address. Use `0.0.0.0` to serve a trusted LAN |
| `CCFD_STORE_DIR` | `./data_store` | Dataset store, shared by all four processes |
| `CCFD_MAX_UPLOAD_MB` | `500` | Upload size limit (REQ-FD-02) |
| `CCFD_MAX_ROWS` | `1000000` | Row limit (REQ-FD-02) |
| `CCFD_JOB_TIMEOUT_S` | `600` | Analysis time limit (REQ-FD-14) |
| `CCFD_WORKERS` | `8` | Background job workers |
| `CCFD_RETENTION_S` | `86400` | Retention period, 24 h (SR-05) |
| `CCFD_PURGE_INTERVAL_S` | `600` | How often the purge task runs |
| `CCFD_ML_URL`, `CCFD_DL_URL`, `CCFD_QML_URL` | `http://127.0.0.1:5001`, `:5002`, `:5003` | Service addresses used by the Web Server |
| `CCFD_ML_PORT`, `CCFD_DL_PORT`, `CCFD_QML_PORT` | `5001`, `5002`, `5003` | Port each service listens on |
| `CCFD_ML_MODEL` | `random_forest` | Classifier the ML service runs: `random_forest` or `logistic_regression` |

## 5. REST API (SADS 3.2)

Every endpoint requires `Authorization: Bearer <key>` and returns JSON.

| Method and path | Success | Errors |
|---|---|---|
| `POST /api/datasets` (multipart, one part named `file`) | `201 {"dataset_id", "rows"}` | 400 `E400_VALIDATION`, 401 `E401_AUTH`, 405 |
| `POST /api/analyses` `{"dataset_id", "model_type": "ml"\|"dl"\|"qml"}` | `202 {"job_id", "status": "queued"}` | 400, 401, 404 `E404_NOT_FOUND` |
| `GET /api/analyses/{job_id}` | `200` job: `job_id, dataset_id, model_type, status`, plus `model_name, predictions, metrics` when completed or `reason {code, message}` when failed | 401, 404 |

Every error body is `{"code": "...", "message": "..."}`. The codes are `E400_VALIDATION`,
`E401_AUTH`, `E404_NOT_FOUND`, `E405_METHOD` and `E500_INTERNAL`. A job fails with the reason
`MODEL_SERVICE_ERROR` or `JOB_TIMEOUT`.

```bash
KEY=...; URL=http://127.0.0.1:5000
curl -s -H "Authorization: Bearer $KEY" -F file=@data/samples/sample_transactions.csv $URL/api/datasets
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
     -d '{"dataset_id":"<id>","model_type":"qml"}' $URL/api/analyses
curl -s -H "Authorization: Bearer $KEY" $URL/api/analyses/<job_id>
```

## 6. Model microservice contract (IPredict)

The three services implement one contract (in `services/common/app_factory.py`). Each service listens
on 127.0.0.1 only and needs no key.

- `POST /predict {"dataset_id": "<id>"}` returns `200 {"model_name", "predictions": [{"row", "class", "probability"}], "metrics": {"accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix": {"tp","tn","fp","fn"}}}`.
  It returns 400 `E400_VALIDATION` for a bad body, 404 `E404_NOT_FOUND` for an unknown dataset and 500 `E500_MODEL` if the model fails.
- `GET /health` returns `200 {"status": "ok"}`, or `503 {"status": "not_ready"}` while the service is not ready.

The probability is rounded to 6 decimal places. The predicted class is `probability >= 0.5`.
Metrics are computed from the returned values and rounded to 4 decimal places. ROC-AUC is
`null` when the dataset contains only one class.

To add a new model, write a `Predictor` subclass, serve it with `run_service()`, and add its URL
to the configuration. The Web Client does not change (SRS section 6, reuse objective).

## 7. Models

All four models are trained on the same stratified 80 % split of the public, anonymised Kaggle dataset
*Credit Card Fraud Detection* (284,807 transactions, 492 fraud; seed 404). The table below shows their
results on the remaining 20 % (56,962 rows, 98 fraud):

| Service | model_name | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|---|
| ML (default) | `random_forest` | 0.9995 | 0.9359 | 0.7449 | 0.8295 | 0.9690 |
| ML (option) | `logistic_regression` | 0.9991 | 0.8615 | 0.5714 | 0.6871 | 0.9737 |
| DL | `mlp` | 0.9994 | 0.9125 | 0.7449 | 0.8202 | 0.9625 |
| QML | `vqc_4qubit` | 0.9957 | 0.2310 | 0.6531 | 0.3413 | 0.8536 |

The QML model compresses the 29 features to 4 PCA components, one per qubit, and is trained on a
balanced sample of 794 rows (394 fraud, 400 legitimate). That is why it is weaker: it is a working quantum baseline, not a
competitive one. Accuracy is close to 1 for every model only because 99.83 % of transactions are
legitimate, so compare the models on precision, recall and F1.

To retrain (this downloads the dataset to `training/raw/`, which is git-ignored):

```bash
python training/prepare_data.py && python training/train_ml.py && python training/train_dl.py && python training/train_qml.py
```

## 8. Tests

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium            # once, for the browser tests
python -m pytest -m "not perf and not ui"         # unit, integration and API tests (CI, Ubuntu + Windows)
python -m pytest -m ui                            # browser tests of the Web Client (CI)
python -m pytest -m perf                          # performance tests, which generate 100k-row and 400 MB files
python tests/perf/run_perf.py --key $KEY          # performance cases against a running deployment
python tests/fixtures/make_datasets.py            # regenerate the synthetic STP test files
```

Test names carry the STP IDs. For example, `test_tc_sec_09_...` implements TC-SEC-09. The latest
results are in [docs/TEST_REPORT.md](docs/TEST_REPORT.md).

## 9. Development workflow

- Backlog: GitHub issues #1 to #34, built from the SRS FRs/NFRs, with story points, sprint milestones
  and planned owners. They are tracked on the GitHub Project *Error 404 - Credit Card Fraud Detection*.
- Each backlog item is built on its own branch `feature/<key>-...` and merged through a pull request
  that says `Closes #n`.
- GitHub Actions: **CI** runs flake8 and pytest on Ubuntu, the same suite on Windows, and the browser
  tests. **PR automation** labels each PR by the area it changes, assigns the author, and fails any
  PR that does not link an issue.

## 10. Team

| SRN | Name |
|---|---|
| PES1UG24AM024 | Akshat Agarwal |
| PES1UG24AM030 | Aman Priyansh (repo owner) |
| PES1UG24AM015 | Aditya Kalloli |

Raghav Balaji (PES1UG23AM224) was a member for Part 1 and left the college before Part 2; his stories were reassigned (see docs/SPRINT_PLAN.md).
