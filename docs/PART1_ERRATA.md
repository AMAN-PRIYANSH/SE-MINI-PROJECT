# Part-1 errata: problems found in the submitted documents and how they were fixed

While building the system, the Part-1 documents (SRS v1.2, SADS v1.1, STP v1.1) were checked against
each other and against what can actually be built. The submitted PDFs are kept unchanged in
`docs/part-1/` because they are the graded Part-1 deliverable. This file records what was wrong or
missing and where it is fixed. Differences in what was *built* are in [DEVIATIONS.md](DEVIATIONS.md).

## 1. Things that were missing or left open

| # | Where | Problem | Fixed in |
|---|---|---|---|
| E-01 | SRS REQ-FD-03, 2.6, A4 | The dataset schema was referred to ("the feature columns expected by the trained models … listed in the user manual") but **never defined anywhere**, and no user manual existed. A tester could not build `valid_1000.csv` from the documents | Schema defined: `V1`-`V28`, `Amount` (numeric), `Class` (0/1), other columns ignored. It lives in `shared/schema.py` and in user manual section 3 |
| E-02 | SRS TBD-03 | The QML simulator was still "Open", although REQ-FD-09 is a **High**-priority requirement | Resolved: PennyLane 0.45.1 `default.qubit` (DEVIATIONS D-06) |
| E-03 | SRS A4, STP 4 | No document said what data the models are trained on. STP 4 says test data is synthetic only, which leaves the training data unexplained | Training uses the public, anonymised Kaggle *Credit Card Fraud Detection* dataset, downloaded by `training/prepare_data.py` and never shipped. Test files are synthetic (DEVIATIONS T-07) |
| E-04 | SRS REQ-FD-15 | It requires ROC-AUC for every run, but ROC-AUC is **undefined** when a dataset has only one class (for example a small file with no fraud) | ROC-AUC is `null` / "n/a" in that case (DEVIATIONS D-08) |
| E-05 | SRS 2.4, STP 11 | "Python 3.10+" cannot be met together with the current pinned library versions | Python 3.12+ (DEVIATIONS D-01) |
| E-06 | SADS 3.3 | The lifecycle did not cover a server restart in the middle of a job, so a job could stay "running" forever | Jobs left behind are failed on startup (DEVIATIONS D-10) |

## 2. Things that were over-promised (the "too heavy" part)

| # | Where | Problem | What was done |
|---|---|---|---|
| E-07 | STP 5, 6, 7 | The brief asked for **7-10 test cases**. The STP has **57**, with minute-level effort sums and a three-day manual schedule for four people. Executed by hand, that is 31.5 person-hours | The plan was kept, and 56 of the 57 cases were **automated** so they run in CI on every PR. This made the over-scoped plan an asset instead of a burden |
| E-08 | STP TC-SAFE-04 (NFR-Q01) | It needs an outside first-time user with a timer, so it can never be automated | Kept as a manual task (issue #33) with a ready protocol in `docs/USABILITY_WALKTHROUGH.md` |
| E-09 | STP TC-JOB-04 | "GET both jobs again 30 minutes later" adds half an hour of waiting and checks nothing that other cases do not already check | Re-read immediately (DEVIATIONS T-04) |
| E-10 | SADS 2.4 item 4 | It promises an "equivalent ACL on Windows" without saying how | POSIX permissions are implemented. The Windows ACL is recorded as not done (DEVIATIONS D-07) |
| E-11 | SRS NFR-05/NFR-Q03, STP TC-PERF-05 | 10 concurrent sessions, including the QML model, were promised before any QML model existed. That was risky, because a slow simulator could break the timing targets | The QML model was kept small (4 qubits), so 10 mixed sessions complete with poll p95 well under 500 ms (TEST_REPORT) |

## 3. Small inconsistencies

| # | Where | Problem | Resolution |
|---|---|---|---|
| E-12 | SADS 3.2 vs SRS REQ-FD-13 | The SADS example rounds probabilities to 4 decimals. The SRS gives no precision. With 4 decimals the class and the probability can disagree near 0.5 | The API returns 6 decimals and the class is derived from the returned value (DEVIATIONS D-09) |
| E-13 | SRS REQ-FD-04 | Only three example messages, while the validator must explain many more cases | All messages are listed in user manual section 6 (DEVIATIONS D-12) |
| E-14 | STP 4 vs SRS 2.4 | The portability smoke test needs a Windows **and** a Linux machine, but the team had only one reference machine | Both are covered by the GitHub Actions runners on every PR (DEVIATIONS T-06) |

## 4. Should the Part-1 documents be rewritten?

No. The brief asks for deviations to be *documented and explained at the final demo*, not for the
SRS/SADS/STP to be re-submitted. Rewriting the graded documents after the fact would hide the
history. If the faculty asks for updated versions, the changes needed are exactly the rows above:
E-01 to E-06 for the SRS and SADS, and E-07 to E-09 for the STP.
