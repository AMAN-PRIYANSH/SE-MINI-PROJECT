# Sprint plan and backlog

The backlog was built from the functional and nonfunctional requirements of SRS v1.2. Each item is a GitHub
issue with story points (Fibonacci scale: 1, 2, 3, 5, 8), a sprint milestone and a planned owner. Items are
tracked on the GitHub Project *Error 404 - Credit Card Fraud Detection (SE Mini-Project)*, which has
*Story Points* and *Sprint* fields.

| Sprint | Dates | Goal | Items | Story points |
|---|---|---|---|---|
| Sprint 1 | 19-23 Oct 2026 | A thin working slice: upload and validation, API key, asynchronous ML run, results view, CI | 18 | 59 |
| Sprint 2 | 26-30 Oct 2026 | DL and QML models, failure handling, retention, performance, browser tests, documentation, freeze | 16 | 54 |

## Planned owners

| Member | Area (from STP section 12) | Story points |
|---|---|---|
| Akshat Agarwal (PES1UG24AM024) | Security, CI/CD, retention, test lead | 25 |
| Aman Priyansh (PES1UG24AM030) | Upload and validation, API, store, docs, videos | 30 |
| Aditya Kalloli (PES1UG24AM015) | Models (ML, DL, QML), job manager | 33 |
| Raghav Balaji (PES1UG23AM224) | Web Client, results, safety, usability | 25 |

See [DEVIATIONS.md](DEVIATIONS.md) P-01 and P-02 for how the plan was actually executed.

## Sprint 1 backlog

| Issue | Key | Story | SP | Planned owner | Requirements |
|---|---|---|---|---|---|
| #1 | S1-01 | Project scaffolding, pinned dependencies and one-command start | 2 | Aman Priyansh | SRS 2.4, 2.5; SADS 2.5, 3.4 |
| #2 | S1-02 | GitHub Actions: lint and test on every push and pull request | 3 | Akshat Agarwal | Part-2 brief 2b; NFR-Q05 |
| #3 | S1-03 | PR automation: template, auto-labels and linked-issue check | 2 | Akshat Agarwal | Part-2 brief 2b-2d |
| #4 | S1-04 | Synthetic test datasets for the Test Plan (STP Section 4) | 3 | Aman Priyansh | NFR-S03; STP 4 (test data) |
| #5 | S1-05 | Dataset store with owner-only permissions | 3 | Aman Priyansh | REQ-FD-05, REQ-FD-22, SR-05 (permissions), SADS 2.6 |
| #6 | S1-06 | Flask app factory, uniform JSON errors, 404/405 handling | 3 | Aman Priyansh | REQ-API-04, REQ-API-05, SR-06 |
| #7 | S1-07 | API-key authentication on every REST endpoint | 2 | Akshat Agarwal | SR-03, SO-02 |
| #8 | S1-08 | Dataset upload endpoint with file-level validation | 5 | Aman Priyansh | REQ-FD-01, REQ-FD-02, REQ-FD-04, REQ-API-01, SR-01, NFR-07 |
| #9 | S1-09 | Row-level schema validation (Class label and numeric features) | 5 | Aman Priyansh | REQ-FD-03, REQ-FD-04, BR-01, NFR-01, NFR-03 |
| #10 | S1-10 | Train the ML baseline models (Logistic Regression, Random Forest) | 3 | Aditya Kalloli | REQ-FD-07; SRS A4 (models trained before deployment) |
| #11 | S1-11 | Shared microservice contract: POST /predict, GET /health, metrics | 5 | Aditya Kalloli | REQ-FD-10, REQ-FD-13, REQ-FD-15, REQ-FD-16, NFR-Q02, NFR-Q05, SADS 3.2 |
| #12 | S1-12 | ML microservice on port 5001 | 2 | Aditya Kalloli | REQ-FD-07, REQ-FD-10 |
| #13 | S1-13 | Start analysis: POST /api/analyses with asynchronous Job Manager | 5 | Aditya Kalloli | REQ-FD-11, REQ-FD-12, REQ-API-02, SR-02, BR-02 |
| #14 | S1-14 | Job status endpoint GET /api/analyses/{job_id} | 3 | Aman Priyansh | REQ-API-03, REQ-FD-22, SR-03 |
| #15 | S1-15 | Web Client: API key, upload, model selection, run control with live status | 5 | Raghav Balaji | REQ-UI-01, REQ-UI-02, REQ-UI-03, REQ-FD-01, REQ-FD-06, BR-02, SR-03 (key kept in memory only) |
| #16 | S1-16 | Web Client results view: metrics, confusion matrix, paginated predictions | 5 | Raghav Balaji | REQ-FD-17, REQ-FD-18, REQ-FD-19, REQ-FD-20, REQ-UI-05, NFR-04, BR-03 |
| #17 | S1-17 | Analytical-only notice; no transaction-initiating feature | 1 | Raghav Balaji | NFR-S01, NFR-S02, BR-05 |
| #18 | S1-18 | Sprint 1 demo video (1 minute) uploaded to the repo | 2 | Aman Priyansh | Part-2 brief 2g, 2h |

## Sprint 2 backlog

| Issue | Key | Story | SP | Planned owner | Requirements |
|---|---|---|---|---|---|
| #19 | S2-01 | DL microservice (multilayer perceptron) on port 5002 | 5 | Aditya Kalloli | REQ-FD-08, REQ-FD-10 |
| #20 | S2-02 | QML microservice (variational quantum classifier on a simulator) on port 5003 | 8 | Aditya Kalloli | REQ-FD-09, REQ-FD-10, TBD-03 |
| #21 | S2-03 | Job failure handling: service down, invalid response, timeout | 5 | Aditya Kalloli | REQ-FD-14, REQ-FD-20, BR-04, NFR-06 |
| #22 | S2-04 | Download predictions as CSV (row, class, probability only) | 2 | Raghav Balaji | REQ-FD-21, SR-04 |
| #23 | S2-05 | Help link, user manual page, single stylesheet, 1280x720 layout | 3 | Raghav Balaji | REQ-UI-04, REQ-UI-06, SRS 2.6 |
| #24 | S2-06 | No transaction data in logs, messages or exports | 3 | Akshat Agarwal | SR-04, SR-02 (payloads not logged), SO-01 |
| #25 | S2-07 | 24-hour retention purge of datasets, jobs and results | 3 | Akshat Agarwal | SR-05 |
| #26 | S2-08 | Performance and load test harnesses | 5 | Akshat Agarwal | NFR-01, NFR-02, NFR-03, NFR-04, NFR-05, NFR-07, NFR-Q03 |
| #27 | S2-09 | Browser end-to-end tests of the Web Client (Playwright) | 5 | Raghav Balaji | REQ-UI-01 - REQ-UI-06, REQ-FD-18 - REQ-FD-21 |
| #28 | S2-10 | Portability: run the smoke test on Windows and Ubuntu in CI | 2 | Akshat Agarwal | NFR-Q04 |
| #29 | S2-11 | Developer README (contracts, configuration, how to run) | 2 | Aman Priyansh | SRS 2.6 item 3 |
| #30 | S2-12 | User manual (dataset schema, workflow, troubleshooting) | 3 | Raghav Balaji | SRS 2.6 item 1, REQ-UI-04 |
| #31 | S2-13 | Deviations document and Part-1 errata | 2 | Akshat Agarwal | Part-2 brief 2i |
| #32 | S2-14 | Test execution report against the STP (57 cases) | 3 | Akshat Agarwal | STP Section 10 (deliverables 2, 5) |
| #33 | S2-15 | Usability walkthrough with a first-time user (manual) | 1 | Raghav Balaji | NFR-Q01 |
| #34 | S2-16 | Sprint 2 demo video (2 minutes), final docs and development freeze | 2 | Aman Priyansh | Part-2 brief 3b-3d |
