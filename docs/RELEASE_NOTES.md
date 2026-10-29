# Release 1.0: release notes and development freeze

**Release:** 1.0 (git tag `v1.0`, created on `main` once the last Sprint 2 pull request is merged)
**Freeze:** development is frozen at the end of Sprint 2 (30 Oct 2026). After the freeze, `main` only
takes fixes for defects found at the final demo.

## What is in Release 1.0

| Area | Delivered | Requirements |
|---|---|---|
| Dataset upload and validation | CSV up to 500 MB / 1,000,000 rows, file-level and row-level checks, named reasons | REQ-FD-01 to REQ-FD-05, SR-01, NFR-01, NFR-03, NFR-07 |
| Model selection | ML (Random Forest; Logistic Regression configurable), DL (MLP), QML (4-qubit VQC on PennyLane) | REQ-FD-06 to REQ-FD-10 |
| Asynchronous execution | Job queue with queued -> running -> completed/failed, 600 s deadline, failure reasons | REQ-FD-11 to REQ-FD-14 |
| Performance evaluation | Accuracy, precision, recall, F1, ROC-AUC (4 d.p.), confusion matrix | REQ-FD-15 to REQ-FD-17 |
| Results | Live status, automatic results, 50-row pagination, CSV download, analytical-only notice | REQ-FD-18 to REQ-FD-22, REQ-UI-01 to REQ-UI-06, NFR-S01 to NFR-S03 |
| REST API | 3 endpoints, uniform JSON errors | REQ-API-01 to REQ-API-05 |
| Security | API key, strict JSON, no data in logs, owner-only store, 24 h retention, safe errors | SR-01 to SR-06 |
| Quality | Independent microservices, Windows + Ubuntu CI, browser tests, performance harness | NFR-05, NFR-06, NFR-Q02 to NFR-Q05 |
| Documentation | Developer README, user manual (also in the app), deviations, Part-1 errata, test report, sprint plan | SRS 2.6 |

## Verification

See [TEST_REPORT.md](TEST_REPORT.md): 141 automated tests; 56 of 57 STP cases pass (all 32
High-priority cases). TC-SAFE-04 (usability walkthrough) is done by hand by the team.

## Known limitations

- QML is a 4-qubit baseline and is clearly weaker than ML and DL (README section 7).
- Single-host deployment with the Flask development server. No TLS, so it is not for the public internet (SRS TBD-01, TBD-02).
- There is no explicit Windows ACL on the dataset store (DEVIATIONS D-07).
- The data must be synthetic or anonymised (SRS section 6).

## How to cut the release (repo owner)

1. Merge the Sprint 2 pull requests in issue order (S2-01 first), each with a merge commit.
2. Wait for CI on `main` to pass.
3. Tag the release: `git tag -a v1.0 -m "Release 1.0" && git push origin v1.0`.
4. Close the Sprint 2 milestone.
