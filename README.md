# Credit Card Fraud Detection and Model Performance Evaluation System

SE Mini-Project - Team **Error 404** (PES University, AIML, Sec-A).

A web system where a user uploads a labelled credit-card transaction CSV, picks an
ML, DL or QML model, runs fraud detection as a background job and sees per-row
predictions plus performance metrics.

| Part-1 documents | |
|---|---|
| SRS v1.2 | [docs/part-1/SRS_Error-404_v1.2.pdf](docs/part-1/SRS_Error-404_v1.2.pdf) |
| Architecture & Design (SADS) v1.1 | [docs/part-1/SADS_Error-404_v1.1.pdf](docs/part-1/SADS_Error-404_v1.1.pdf) |
| Test Plan (STP) v1.1 | [docs/part-1/STP_Error-404_v1.1.pdf](docs/part-1/STP_Error-404_v1.1.pdf) |

## Quick start

```bash
python -m pip install -r requirements.txt     # Python 3.12+
python run_all.py                              # starts the Web Server and the model services
```

Then open http://127.0.0.1:5000/ and paste the API key printed by `run_all.py`.

## Layout (SADS 3.4)

```
server/      Flask Web Server (REST API, auth, validation, jobs, dataset store)
services/    ML / DL / QML model microservices (POST /predict, GET /health)
client/      Web Client (HTML, CSS, JavaScript - no build step)
shared/      configuration and dataset schema shared by all processes
training/    scripts that train the models served by the microservices
tests/       automated tests, named after the STP test-case IDs
docs/        Part-1 documents, Part-2 documents, demo videos
```
