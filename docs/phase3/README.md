# Phase 3 - Testing (2-6 Nov 2026)

Part-3 brief: update the test cases after the sprints, complete the testing according to the Test Plan, and put
the Unit Test Report, System Validation Report, Code Coverage Report and Branch Coverage Report in `docs/`.

## Reports and owners

| Issue | Report | File | Owner | Command |
|---|---|---|---|---|
| T3-02 | Updated Test Case Document (v1.2) | [TEST_CASE_DOCUMENT.md](TEST_CASE_DOCUMENT.md) | Aman Priyansh | `python tests/report/phase3.py cases` |
| T3-03 | Unit Test Report | [UNIT_TEST_REPORT.md](UNIT_TEST_REPORT.md) | Akshat Agarwal | `python tests/report/phase3.py unit` |
| T3-04 | Code Coverage Report (statements) | [CODE_COVERAGE_REPORT.md](CODE_COVERAGE_REPORT.md) | Akshat Agarwal | `python tests/report/phase3.py coverage` |
| T3-05 | System Validation Report | [SYSTEM_VALIDATION_REPORT.md](SYSTEM_VALIDATION_REPORT.md) | Aditya Kalloli | `python tests/report/phase3.py system` |
| T3-06 | Branch Coverage Report | [BRANCH_COVERAGE_REPORT.md](BRANCH_COVERAGE_REPORT.md) | Aditya Kalloli | `python tests/report/phase3.py branch` |
| T3-07 | Test Summary Report | [TEST_SUMMARY_REPORT.md](TEST_SUMMARY_REPORT.md) | Akshat Agarwal | `python tests/report/phase3.py summary` |
| #33 (S2-15, Sprint 3) | Usability walkthrough (TC-SAFE-04, manual) | [USABILITY_WALKTHROUGH_RESULT.md](USABILITY_WALKTHROUGH_RESULT.md) | Aman Priyansh | by hand, see docs/USABILITY_WALKTHROUGH.md |

Each command runs the tests on the machine where it is started and writes the report, with the commit, date,
machine and the name of the person who ran it, plus raw evidence (JUnit XML, coverage XML/JSON) in `raw/`.

## How to run

```bash
python -m pip install -r requirements-dev.txt     # Python 3.12+
python -m playwright install chromium             # only for the system report (browser tests)
python tests/report/phase3.py <report>
```

The same reports can be produced on a clean GitHub runner: Actions > **Test reports** > Run workflow; the files are
attached to the run as the `phase3-reports` artifact.

## Sprint 3

The only item that did not finish in Sprint 2 is S2-15 (issue #33), the manual usability walkthrough. It spills over
into Sprint 3, which runs in parallel with the testing week (Part-3 brief, item 3). No new development is planned:
the code stays frozen at Release 1.0.
