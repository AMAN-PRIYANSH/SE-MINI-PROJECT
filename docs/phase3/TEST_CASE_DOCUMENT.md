# Test Case Document v1.2 (STP-CCFD test cases, updated after the sprints)

This document updates the 57 test cases of STP-CCFD-1.1 (section 5) to match the system as built in Sprints 1 and 2. Each case keeps its ID, objective and traceability; where a sprint changed what a case checks, the case says what changed and why, with a reference to docs/DEVIATIONS.md. Two cases are new (TC-JOB-07, TC-MET-06), giving 59 in total.

Every case except TC-SAFE-04 is automated: the *Automated test(s)* row names the pytest test that executes it. Results are in the System Validation Report. Environment for all cases: Python 3.12+ (DEVIATIONS D-01).

## Change history

| Version | Date | Change |
|---|---|---|
| 1.1 | 12 Oct 2026 | STP-CCFD-1.1 (Part 1) |
| 1.2 | Nov 2026 | Updated after Sprints 1 and 2: exact error messages, test substitutions, resolved TBD-03, two new cases |

## Summary of changes per case

| Case | Change in this version |
|---|---|
| TC-SEC-05 | Expected now quotes the exact message: `unsupported file type: the file is not CSV text` for binary content with a .csv name (`only .csv files are accepted` for other extensions). (source: DEVIATIONS D-12) |
| TC-SEC-06 | Automated run uses a 100 KB size limit instead of 500 MB (STP 13 substitution). Expected message: `file exceeds the 500 MB limit` (100 KB in the test). (source: DEVIATIONS T-03) |
| TC-SEC-09 | Step 3: retention 2 s and purge interval 0.2 s in the automated run (was 5 minutes). Owner-only permissions are checked on Linux and macOS; on Windows the store inherits the profile ACL. (source: DEVIATIONS T-03, D-07) |
| TC-UPL-02 | Expected now quotes the exact message: `missing required column: Class`. (source: DEVIATIONS D-12) |
| TC-UPL-03 | Expected now quotes the exact message, which also names the data-row number: `invalid value in column Class at row N: Class must be 0 or 1`. (source: DEVIATIONS D-12) |
| TC-UPL-04 | Expected now quotes the exact message: `the file has no data rows`. (source: DEVIATIONS D-12) |
| TC-UPL-06 | Expected now quotes the exact message: `wrong delimiter: the file must be comma-delimited`. (source: DEVIATIONS D-12) |
| TC-UPL-07 | Expected now quotes the exact message, which names column and row: `non-numeric or missing value in column <col> at row N`. (source: DEVIATIONS D-12) |
| TC-MOD-03 | The DL model is a scikit-learn MLPClassifier (64 and 32 ReLU units); expected model_name is `mlp`. (source: DEVIATIONS D-05) |
| TC-MOD-04 | TBD-03 resolved: the QML model is a 4-qubit variational quantum classifier on PennyLane `default.qubit`; expected model_name is `vqc_4qubit`. (source: DEVIATIONS D-06) |
| TC-JOB-04 | Step 3: both jobs are read again immediately after completion instead of 30 minutes later; retention is tested by TC-SEC-09. (source: DEVIATIONS T-04) |
| TC-JOB-06 | Automated run uses a 1 s timeout instead of 600 s (STP 13 substitution). The timeout is a hard overall deadline on the whole call. (source: DEVIATIONS T-03, D-11) |
| TC-JOB-07 | New in v1.2: covers the restart behaviour added during Sprint 2 (source: DEVIATIONS D-10). |
| TC-MET-01 | The API returns probabilities with 6 decimals (the UI shows 4); the comparison stays at 4 d.p. (source: DEVIATIONS D-09) |
| TC-MET-06 | New in v1.2: ROC-AUC is undefined without both classes (source: DEVIATIONS D-08). |
| TC-PERF-03 | Measured on the client over HTTP to a server on the same host (an upper bound), not from the server log. (source: DEVIATIONS T-05) |
| TC-PERF-06 | Measured on the client over HTTP to a server on the same host (an upper bound), not from the server log. (source: DEVIATIONS T-05) |
| TC-SAFE-04 | Protocol and record sheet in docs/USABILITY_WALKTHROUGH.md; the result is recorded in docs/phase3/USABILITY_WALKTHROUGH_RESULT.md. (source: DEVIATIONS T-02) |

## Test cases

### TC-SEC-01 - Dataset upload without API key → 401, nothing stored

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 20 min |
| Objective | The upload endpoint rejects unauthenticated callers and stores nothing. |
| Traceability | SR-03, REQ-API-04 (objective SO-02) |
| Preconditions | Server healthy; Authorization header deliberately omitted. |
| Steps | 1. POST /api/datasets with valid_1000.csv and no Authorization header. 2. List the datasets/ directory of the dataset store. |
| Expected | HTTP 401 with a {code, message} JSON body; the store is unchanged. |
| Pass criterion | 401 received and no new file in the store. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_sec_01_upload_without_key_is_401_and_nothing_stored` |

### TC-SEC-02 - Invalid API key → 401

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 15 min |
| Objective | A wrong key is treated the same as a missing key. |
| Traceability | SR-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/datasets with valid_1000.csv and header Authorization: Bearer invalid- key-123. |
| Expected | HTTP 401; nothing stored. |
| Pass criterion | 401 received; store unchanged. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_sec_02_invalid_key_is_401` |

### TC-SEC-03 - Analysis start without API key → 401, no job created

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 20 min |
| Objective | Job creation is protected; no phantom jobs appear. |
| Traceability | SR-03, REQ-API-02 (objective SO-02) |
| Preconditions | A valid dataset_id from TC-UPL-01. |
| Steps | 1. POST /api/analyses with {"dataset_id":"<id>","model_type":"ml"} and no Authorization header. 2. List the jobs/ directory of the dataset store and the microservice access logs. |
| Expected | HTTP 401; no job record created; no microservice request. |
| Pass criterion | 401 received; no new job record; no new microservice request. |
| Execution | Automated |
| Automated test(s) | `test_analyses::test_tc_sec_03_no_key_no_job_no_service_call` |

### TC-SEC-04 - Malformed JSON rejected before model processing, never logged

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 25 min |
| Objective | Strict schema validation stops malformed input at the server; payload contents never reach logs or microservices. |
| Traceability | SR-02, REQ-API-04 (objective SO-03) |
| Preconditions | A valid dataset_id. |
| Steps | 1. POST /api/analyses with the truncated body {"dataset_id":. 2. POST /api/analyses with {"dataset_id":"<id>"} (model_type missing). 3. POST /api/analyses with {"dataset_id":"<id>","model_type":"ml","debug":true} (unknown field). 4. Inspect the application log and the microservice access logs. |
| Expected | HTTP 400 with a reason-naming body for all three requests; no job created; no payload fragment in any log; no microservice activity. |
| Pass criterion | 400 on all three; logs contain no payload fragments; microservices show no new requests. |
| Execution | Automated |
| Automated test(s) | `test_analyses::test_tc_sec_04_malformed_json_rejected_not_logged` |

### TC-SEC-05 - Executable disguised as CSV rejected

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 20 min |
| Objective | File-type validation blocks non-CSV content regardless of the extension. |
| Traceability | SR-01, REQ-FD-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/datasets with evil.csv (a binary executable renamed to .csv). |
| Expected | HTTP 400 naming "unsupported file type"; nothing stored; no microservice contacted. |
| Pass criterion | 400 with the specific reason; store unchanged. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_sec_05_executable_renamed_csv_rejected` |
| **Changed in v1.2** | Expected now quotes the exact message: `unsupported file type: the file is not CSV text` for binary content with a .csv name (`only .csv files are accepted` for other extensions). (source: DEVIATIONS D-12) |

### TC-SEC-06 - Oversize upload rejected with specific reason

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Security / 25 min |
| Objective | The 500 MB limit is enforced with a clear message. |
| Traceability | SR-01, REQ-FD-02, REQ-FD-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload a file larger than 500 MB. If this is impractical in lab time, temporarily lower the configured limit (for example to 5 MB), upload a larger file and record the substitution. |
| Expected | HTTP 400 with "file exceeds the 500 MB limit" (or the substituted limit); nothing stored. |
| Pass criterion | 400 with the size reason; store unchanged. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_sec_06_oversize_rejected_with_reason` |
| **Changed in v1.2** | Automated run uses a 100 KB size limit instead of 500 MB (STP 13 substitution). Expected message: `file exceeds the 500 MB limit` (100 KB in the test). (source: DEVIATIONS T-03) |

### TC-SEC-07 - Error responses disclose no internals

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 25 min |
| Objective | Client-facing errors and job failure reasons never leak stack traces, paths or configuration. |
| Traceability | SR-06 (objectives SO-01, SO-02) |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. GET /api/analyses/{random-uuid} → expect 404. 2. POST /api/analyses with malformed JSON → expect 400. 3. Make the dataset store directory read-only, upload valid_1000.csv → expect 500, then restore permissions. 4. Read the failure reason of a failed job from TC-JOB- 05. |
| Expected | Every body contains only {code, message} (or the job's reason object); no Traceback, file- system path, .py reference or configuration value. |
| Pass criterion | None of the forbidden strings appear in any response. |
| Execution | Automated |
| Automated test(s) | `test_stp_cases::test_tc_sec_07_errors_disclose_no_internals` |

### TC-SEC-08 - No transaction data in logs, UI or export

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 30 min |
| Objective | Transaction field values are never logged, displayed or exported (data display policy). |
| Traceability | SR-04 (objective SO-01) |
| Preconditions | A completed ML job on extra_cols.csv (it contains a synthetic card_ref column). |
| Steps | 1. Search the application and microservice logs for distinctive values from extra_cols.csv (feature values and card_ref strings). 2. Inspect the results table and the downloaded CSV. 3. Upload non_numeric.csv and read the error message. |
| Expected | No field value appears in any log; the table and CSV show only row index, predicted class and fraud probability (no card_ref or feature column); the error message names the column and row but not the cell value. |
| Pass criterion | All three checks hold. |
| Execution | Automated |
| Automated test(s) | `test_data_protection::test_tc_sec_08_no_field_values_in_logs_or_results`<br>`test_data_protection::test_tc_sec_08_error_names_column_and_row_but_not_the_value` |

### TC-SEC-09 - Dataset store permissions and 24-hour retention

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Security / 30 min |
| Objective | Stored data is isolated on disk and deleted when its retention period ends. |
| Traceability | SR-05 (objective SO-01) |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload valid_1000.csv and complete one job on it. 2. Check the permissions of the dataset store directory and its files. 3. With the retention period temporarily configured to 5 minutes (substitution recorded), wait until it has elapsed. 4. List datasets/, jobs/ and results/; GET the job. |
| Expected | Owner-only permissions for the service account; after the retention period the dataset file, job record and result file are deleted and GET returns 404. |
| Pass criterion | Permissions are owner-only and all three artefacts are removed after the period ends. |
| Execution | Automated |
| Automated test(s) | `test_retention::test_tc_sec_09_dataset_job_and_result_deleted_after_retention`<br>`test_store::test_tc_sec_09_owner_only_permissions` |
| **Changed in v1.2** | Step 3: retention 2 s and purge interval 0.2 s in the automated run (was 5 minutes). Owner-only permissions are checked on Linux and macOS; on Windows the store inherits the profile ACL. (source: DEVIATIONS T-03, D-07) |

### TC-SEC-10 - Results retrieval without API key → 401

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Security / 15 min |
| Objective | Results of a job cannot be read without a valid key, even when the job_id is known. |
| Traceability | SR-03, REQ-API-03 (objectives SO-01, SO-02) |
| Preconditions | A completed job from TC-JOB-02. |
| Steps | 1. GET /api/analyses/{job_id} with no Authorization header. 2. Repeat with Authorization: Bearer invalid-key-123. |
| Expected | HTTP 401 for both; no predictions or metrics in the body. |
| Pass criterion | 401 on both requests and no result data returned. |
| Execution | Automated |
| Automated test(s) | `test_job_status::test_tc_sec_10_results_need_the_key` |

### TC-UPL-01 - Valid dataset accepted and registered

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 15 min |
| Objective | A well-formed labeled CSV is accepted with a unique dataset identifier. |
| Traceability | REQ-FD-02, REQ-FD-03, REQ-FD-05, REQ-API-01, NFR-01 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/datasets with valid_1000.csv; record status, body and elapsed time. 2. Upload the same file again. |
| Expected | HTTP 201 with a non-empty dataset_id and rows = 1000, returned within 2 s; the second upload receives a different dataset_id. |
| Pass criterion | 201 with dataset_id; elapsed ≤ 2 s; the two identifiers differ. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_01_valid_upload_twice_gives_two_ids_within_2s` |

### TC-UPL-02 - Missing Class column → 400 naming the reason

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 15 min |
| Objective | Schema validation catches the missing label column with a specific message. |
| Traceability | REQ-FD-03, REQ-FD-04, BR-01 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload no_class_column.csv. |
| Expected | HTTP 400; message "missing required column: Class". |
| Pass criterion | 400 with the column named; nothing stored. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_02_missing_class_column` |
| **Changed in v1.2** | Expected now quotes the exact message: `missing required column: Class`. (source: DEVIATIONS D-12) |

### TC-UPL-03 - Non-binary Class values → 400

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 15 min |
| Objective | The label domain (0/1 only) is enforced. |
| Traceability | REQ-FD-03, REQ-FD-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload bad_labels.csv (Class values 2, −1 and empty). |
| Expected | HTTP 400 naming the label-domain violation. |
| Pass criterion | 400 with a specific reason. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_03_non_binary_class_values` |
| **Changed in v1.2** | Expected now quotes the exact message, which also names the data-row number: `invalid value in column Class at row N: Class must be 0 or 1`. (source: DEVIATIONS D-12) |

### TC-UPL-04 - Header-only file → 400

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 15 min |
| Objective | A file with no data rows is rejected. |
| Traceability | REQ-FD-03, REQ-FD-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload header_only.csv. |
| Expected | HTTP 400 stating that the file has no data rows. |
| Pass criterion | 400 with a specific reason. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_04_header_only` |
| **Changed in v1.2** | Expected now quotes the exact message: `the file has no data rows`. (source: DEVIATIONS D-12) |

### TC-UPL-05 - Empty file → 400

| Field | Value |
|---|---|
| Priority / Type / Est. | Low / Functional / 10 min |
| Objective | A zero-byte upload is rejected gracefully. |
| Traceability | REQ-FD-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload empty.csv (0 bytes). 2. Repeat TC-UPL-01 step 1. |
| Expected | HTTP 400; the server keeps working. |
| Pass criterion | 400; the subsequent valid upload still returns 201. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_05_empty_file_then_server_still_works` |

### TC-UPL-06 - Wrong delimiter → 400

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 15 min |
| Objective | Only comma-delimited CSV is accepted. |
| Traceability | REQ-FD-02, REQ-FD-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload semicolon.csv. |
| Expected | HTTP 400 naming the format problem as the reason. |
| Pass criterion | 400 with a specific reason. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_06_semicolon_delimiter` |
| **Changed in v1.2** | Expected now quotes the exact message: `wrong delimiter: the file must be comma-delimited`. (source: DEVIATIONS D-12) |

### TC-UPL-07 - Non-numeric feature value → 400

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 15 min |
| Objective | Required feature columns must be numeric. |
| Traceability | REQ-FD-03, REQ-FD-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload non_numeric.csv. |
| Expected | HTTP 400 naming the offending column. |
| Pass criterion | 400 with the column named. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_07_non_numeric_feature_names_column_not_value` |
| **Changed in v1.2** | Expected now quotes the exact message, which names column and row: `non-numeric or missing value in column <col> at row N`. (source: DEVIATIONS D-12) |

### TC-UPL-08 - Extra columns tolerated and ignored

| Field | Value |
|---|---|
| Priority / Type / Est. | Low / Functional / 15 min |
| Objective | Files with columns beyond the documented schema are accepted and the extra columns are ignored. |
| Traceability | REQ-FD-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload extra_cols.csv. 2. Run an ML job on it and poll to completion. |
| Expected | HTTP 201; the run completes; predictions cover all rows. |
| Pass criterion | 201 and a completed run with the correct row count. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_upl_08_extra_columns_accepted` |

### TC-MOD-01 - Run blocked with no model selected

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 15 min |
| Objective | The UI enforces model selection before execution. |
| Traceability | REQ-FD-06, BR-02 |
| Preconditions | Web Client open; API key entered; a dataset uploaded. |
| Steps | 1. Leave the model selector empty and activate the run control. |
| Expected | The run does not start; a message asks the user to select a model. |
| Pass criterion | No POST /api/analyses is sent (browser network panel); the guidance message is shown. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_mod_01_run_blocked_without_model` |

### TC-MOD-02 - ML selection routes to the ML microservice

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 20 min |
| Objective | Selecting ML executes the ML service and labels results accordingly. |
| Traceability | REQ-FD-06, REQ-FD-07, REQ-FD-10, REQ-FD-11, REQ-FD-17, BR-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/analyses with {"dataset_id":"<id>","model_type":"ml"}. 2. Poll to completion; check the ML service access log and the model_name. |
| Expected | 202 with job_id; the ML service received the request; the completed job's model_name is the classifier configured for the ML service. |
| Pass criterion | 202; ML service called; model_name matches the configuration. |
| Execution | Automated |
| Automated test(s) | `test_stp_cases::test_tc_mod_02_ml_selection_routes_to_ml` |

### TC-MOD-03 - DL selection routes to the DL microservice

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 20 min |
| Objective | As TC-MOD-02 for the DL option. |
| Traceability | REQ-FD-06, REQ-FD-08, REQ-FD-10, REQ-FD-11, REQ-FD-17, BR-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Run with model_type "dl"; poll to completion; check the DL access log and model_name. |
| Expected | 202; completed job; model_name identifies the DL (MLP) model. |
| Pass criterion | 202; DL service called; model_name correct. |
| Execution | Automated |
| Automated test(s) | `test_dl_service::test_tc_mod_03_dl_selection_routes_to_dl` |
| **Changed in v1.2** | The DL model is a scikit-learn MLPClassifier (64 and 32 ReLU units); expected model_name is `mlp`. (source: DEVIATIONS D-05) |

### TC-MOD-04 - QML selection routes to the QML microservice

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 25 min |
| Objective | As TC-MOD-02 for the simulator-backed QML option. |
| Traceability | REQ-FD-06, REQ-FD-09, REQ-FD-10, REQ-FD-11, REQ-FD-17, BR-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Run with model_type "qml" on valid_1000.csv; poll to completion. |
| Expected | 202; completed job (the simulator may be slower, which the asynchronous design absorbs); model_name identifies the QML model. |
| Pass criterion | 202; completed with the QML model name. |
| Execution | Automated |
| Automated test(s) | `test_qml_service::test_tc_mod_04_qml_routing` |
| **Changed in v1.2** | TBD-03 resolved: the QML model is a 4-qubit variational quantum classifier on PennyLane `default.qubit`; expected model_name is `vqc_4qubit`. (source: DEVIATIONS D-06) |

### TC-MOD-05 - Unknown model_type → 400

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 15 min |
| Objective | The model-type enumeration is enforced at the API boundary. |
| Traceability | REQ-FD-06, REQ-API-02, REQ-API-04, SR-02 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/analyses with model_type "quantum-xyz". |
| Expected | HTTP 400 naming the invalid model type; no job created. |
| Pass criterion | 400; no job record exists. |
| Execution | Automated |
| Automated test(s) | `test_analyses::test_tc_mod_05_unknown_model_type` |

### TC-MOD-06 - Microservice contract tested in isolation

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 20 min |
| Objective | Each microservice honours the uniform contract on its own, without the Web Server. |
| Traceability | REQ-FD-10, NFR-Q05 |
| Preconditions | valid_1000.csv placed in the dataset store under a known dataset_id by the test fixture. |
| Steps | 1. GET /health on ports 5001, 5002 and 5003. 2. POST /predict with the known dataset_id to each service. 3. POST /predict with an unknown dataset_id. |
| Expected | 200 {"status":"ok"} from each health check; 200 with model_name, predictions and metrics in the contract shape; 404 with {code, message} for the unknown identifier. |
| Pass criterion | All three services satisfy all three checks. |
| Execution | Automated |
| Automated test(s) | `test_dl_service::test_tc_mod_06_dl_contract_in_isolation`<br>`test_ml_service::test_configured_classifier_is_used_and_named`<br>`test_qml_service::test_tc_mod_06_qml_contract_in_isolation`<br>`test_service_contract::test_health_ok_and_not_ready`<br>`test_service_contract::test_predict_contract_shape`<br>`test_service_contract::test_unknown_dataset_is_404` |

### TC-JOB-01 - Valid run accepted within 2 s with job_id

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 15 min |
| Objective | Analysis runs are asynchronous: the server accepts and returns at once. |
| Traceability | REQ-FD-12, REQ-API-02 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/analyses with {"dataset_id":"<id>","model_type":"ml"}; measure the time to response. |
| Expected | HTTP 202 within 2 s with a non-empty job_id and status "queued". |
| Pass criterion | 202 within 2 s; status "queued". |
| Execution | Automated |
| Automated test(s) | `test_analyses::test_tc_job_01_and_tc_api_02_accepted_within_2s` |

### TC-JOB-02 - Poll observes queued → running → completed in order

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 30 min |
| Objective | The full job lifecycle is observable and ordered; the client needs no reload. |
| Traceability | REQ-FD-12, REQ-UI-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Start an ML run from the Web Client. 2. In the browser network panel, record each GET /api/analyses/{job_id} response and its time; watch the status badge. |
| Expected | Polls every 2 s; states progress queued → running → completed; the badge updates without a reload; polling stops at the terminal state. |
| Pass criterion | All three states seen in order, polling interval 2 s (± 0.5 s), no manual refresh, no polls after completion. |
| Execution | Automated |
| Automated test(s) | `test_analyses::test_job_reaches_completed_and_result_is_stored`<br>`test_web_client::test_tc_job_02_and_tc_res_04_states_in_order_polling_2s_no_reload` |

### TC-JOB-03 - Unknown job_id → 404

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 10 min |
| Objective | Polling a nonexistent job returns a clean 404. |
| Traceability | REQ-API-03, REQ-API-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. GET /api/analyses/{random-uuid}. |
| Expected | HTTP 404 with a {code, message} body. |
| Pass criterion | 404 with the standard error shape. |
| Execution | Automated |
| Automated test(s) | `test_job_status::test_tc_job_03_unknown_job_is_404` |

### TC-JOB-04 - Two concurrent jobs stay independent

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 30 min |
| Objective | Concurrent jobs do not interfere and each result set stays with its own dataset and model. |
| Traceability | REQ-FD-11, REQ-FD-12, REQ-FD-22 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload valid_1000.csv and valid_51.csv. 2. Start an ML run on the first and a DL run on the second back-to-back. 3. Poll both to completion; GET both jobs again 30 minutes later. |
| Expected | Two distinct job_ids; both complete; each job reports its own dataset_id, model_type and model_name, with 1,000 and 51 predictions respectively, and still does so later in the retention period. |
| Pass criterion | Both complete with correctly associated results; no cross-contamination. |
| Execution | Automated |
| Automated test(s) | `test_dl_service::test_tc_job_04_ml_and_dl_jobs_back_to_back`<br>`test_job_status::test_tc_job_04_concurrent_jobs_stay_independent` |
| **Changed in v1.2** | Step 3: both jobs are read again immediately after completion instead of 30 minutes later; retention is tested by TC-SEC-09. (source: DEVIATIONS T-04) |

### TC-JOB-05 - Microservice down → job failed; other services unaffected

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional (negative) / 35 min |
| Objective | An unavailable service yields a failed job with a reason — never fabricated results — and the other services keep working. |
| Traceability | REQ-FD-14, REQ-FD-20, BR-04, NFR-06 |
| Preconditions | QML microservice stopped. |
| Steps | 1. Start a run with model_type "qml" from the Web Client. 2. Poll until a terminal state. 3. Start an ML run on the same dataset. |
| Expected | The QML job becomes failed with reason MODEL_SERVICE_ERROR; the Web Client shows the reason and no predictions or metrics; the ML job completes normally. |
| Pass criterion | failed with reason and no results shown; ML run completes. |
| Execution | Automated |
| Automated test(s) | `test_failures::test_tc_job_05_service_down_job_fails_others_unaffected`<br>`test_web_client::test_tc_job_05_failure_reason_shown_without_results` |

### TC-JOB-06 - Job timeout → failed with reason

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional (negative) / 40 min |
| Objective | The 600 s limit fires; hung jobs cannot linger. |
| Traceability | REQ-FD-14 |
| Preconditions | A stub microservice that never responds, registered as the ML service. |
| Steps | 1. Start a run against the stub. 2. Poll past the configured timeout (a lower value, for example 30 s, may be configured; record the substitution). |
| Expected | The job transitions to failed with reason JOB_TIMEOUT. |
| Pass criterion | failed with JOB_TIMEOUT recorded. |
| Execution | Automated |
| Automated test(s) | `test_failures::test_tc_job_06_timeout` |
| **Changed in v1.2** | Automated run uses a 1 s timeout instead of 600 s (STP 13 substitution). The timeout is a hard overall deadline on the whole call. (source: DEVIATIONS T-03, D-11) |

### TC-JOB-07 - Jobs interrupted by a server restart are marked failed

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 15 min |
| Objective | No job stays queued or running for ever after the Web Server restarts. |
| Traceability | REQ-FD-14, BR-04 |
| Preconditions | A job record left in state running by a stopped Web Server process. |
| Steps | 1. Stop the Web Server while a job is running. 2. Start it again. 3. GET the job. |
| Expected | The job is failed with reason MODEL_SERVICE_ERROR; no results are shown. |
| Pass criterion | Job state failed with the reason; client polling stops. |
| Execution | Automated |
| Automated test(s) | `test_failures::test_jobs_interrupted_by_a_restart_are_failed_on_startup` |
| **Changed in v1.2** | New in v1.2: covers the restart behaviour added during Sprint 2 (source: DEVIATIONS D-10). |

### TC-MET-01 - Metrics correct to four decimals against an independent reference

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 30 min |
| Objective | The five metrics match an independently computed reference. |
| Traceability | REQ-FD-15 |
| Preconditions | Completed ML job on valid_1000.csv; reference_metrics.json computed by a separate script from the same predictions. |
| Steps | 1. Read the metrics from GET /api/analyses/{job_id}. 2. Compare each value with the reference. |
| Expected | accuracy, precision, recall, f1 and roc_auc present, each with four decimal places, matching the reference. |
| Pass criterion | All five match to 4 d.p. |
| Execution | Automated |
| Automated test(s) | `test_ml_service::test_configured_classifier_is_used_and_named`<br>`test_stp_cases::test_tc_met_01_metrics_match_independent_reference` |
| **Changed in v1.2** | The API returns probabilities with 6 decimals (the UI shows 4); the comparison stays at 4 d.p. (source: DEVIATIONS D-09) |

### TC-MET-02 - Confusion-matrix counts are consistent

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 15 min |
| Objective | The confusion matrix is complete and arithmetically consistent. |
| Traceability | REQ-FD-16 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Read confusion_matrix from a completed job. |
| Expected | Integer tp, tn, fp and fn whose sum equals the dataset row count. |
| Pass criterion | tp + tn + fp + fn equals the input row count. |
| Execution | Automated |
| Automated test(s) | `test_service_contract::test_tc_res_03_value_domains_and_tc_met_02_counts`<br>`test_stp_cases::test_tc_met_02_confusion_matrix_consistent` |

### TC-MET-03 - Metrics and confusion matrix displayed and labeled with the executed model

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional/UI / 20 min |
| Objective | The results screen shows the metrics and confusion matrix, always identified by their source model. |
| Traceability | REQ-FD-17, REQ-FD-19, BR-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Complete one run per model type from the Web Client. 2. Inspect each results screen and metrics payload. |
| Expected | Each screen shows the five metrics and the four confusion-matrix counts, matching the API payload, labeled with the model_name of that job. |
| Pass criterion | All three runs display complete, correctly labeled metrics. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_met_03_metrics_displayed_and_labelled` |

### TC-MET-04 - Same dataset across ML, DL and QML yields comparable metric sets

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 30 min |
| Objective | Comparing approaches on identical data works end to end. |
| Traceability | REQ-FD-15, REQ-FD-16 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Run all three model types on valid_1000.csv. 2. Collect the three metric sets. |
| Expected | Three complete metric sets with identical structure, computed over the same row count. |
| Pass criterion | All three complete; structures identical. |
| Execution | Automated |
| Automated test(s) | `test_qml_service::test_tc_met_04_same_dataset_three_models_comparable` |

### TC-MET-05 - Hand-computed tiny dataset matches exactly

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 25 min |
| Objective | End-to-end metric correctness on a dataset small enough to verify by hand. |
| Traceability | REQ-FD-15, REQ-FD-16 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload tiny_4row.csv, run ML, read the predictions, metrics and confusion matrix. 2. Compute the metrics by hand from the returned predictions and the labels. |
| Expected | Values match the hand computation (to 4 d.p.). |
| Pass criterion | Exact match on all five metrics and all four counts. |
| Execution | Automated |
| Automated test(s) | `test_stp_cases::test_tc_met_05_tiny_dataset_by_hand` |

### TC-MET-06 - Single-class dataset: ROC-AUC reported as not available

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 15 min |
| Objective | Metrics stay correct and honest when the dataset has only one class. |
| Traceability | REQ-FD-15, BR-04 |
| Preconditions | A dataset whose Class column contains only 0. |
| Steps | 1. Run the metric calculation on labels of one class only. 2. Read accuracy, precision, recall, F1 and ROC-AUC. |
| Expected | No division error; ROC-AUC is null in the API and shown as n/a in the UI; the other metrics are defined. |
| Pass criterion | ROC-AUC null and no exception. |
| Execution | Automated |
| Automated test(s) | `test_metrics_unit::test_single_class_has_null_roc_auc_and_no_division_error` |
| **Changed in v1.2** | New in v1.2: ROC-AUC is undefined without both classes (source: DEVIATIONS D-08). |

### TC-RES-01 - Predictions table: columns and 50-row pagination

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional/UI / 20 min |
| Objective | The results table shows the required columns, paginated. |
| Traceability | REQ-FD-18, REQ-UI-05 |
| Preconditions | Completed job on valid_1000.csv. |
| Steps | 1. Open the results view; inspect the columns and the pager. |
| Expected | Columns row index, predicted class and fraud probability; 50 rows per page; 20 pages for 1,000 rows. |
| Pass criterion | Columns correct; 50 rows per page; 20 pages. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_res_01_columns_and_20_pages` |

### TC-RES-02 - Pagination boundary: 51 rows → 2 pages

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional/UI / 20 min |
| Objective | The page boundary drops or duplicates no rows. |
| Traceability | REQ-FD-18, REQ-UI-05 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Run on valid_51.csv; open the results; count the rows on pages 1 and 2. |
| Expected | Page 1 has 50 rows and page 2 has 1 row; row indices are continuous. |
| Pass criterion | 50 + 1 rows with no gaps or duplicates. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_res_02_51_rows_give_50_plus_1` |

### TC-RES-03 - Prediction value domains

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 15 min |
| Objective | Every row receives a valid class and probability. |
| Traceability | REQ-FD-13 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Read the full predictions array of a completed job on valid_1000.csv. |
| Expected | One prediction per input row; class ∈ {0, 1}; probability ∈ [0, 1]. |
| Pass criterion | Count matches the input; all values in domain. |
| Execution | Automated |
| Automated test(s) | `test_service_contract::test_tc_res_03_value_domains_and_tc_met_02_counts`<br>`test_stp_cases::test_tc_res_03_prediction_domains` |

### TC-RES-04 - Results appear automatically when the job completes

| Field | Value |
|---|---|
| Priority / Type / Est. | High / UI / 20 min |
| Objective | The Web Client moves from status to results on its own. |
| Traceability | REQ-UI-03, REQ-FD-20 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Start a run in the browser; do not reload or click anything further. |
| Expected | The status badge moves through queued → running → completed, and the predictions table and metrics appear automatically on completion. |
| Pass criterion | Results shown with no reload or extra user action. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_job_02_and_tc_res_04_states_in_order_polling_2s_no_reload` |

### TC-RES-05 - Error message adjacent to control within 1 s

| Field | Value |
|---|---|
| Priority / Type / Est. | High / UI / 20 min |
| Objective | Errors are shown where they happened, promptly. |
| Traceability | REQ-UI-02 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. In the browser, upload no_class_column.csv; in the performance panel, measure from receipt of the 400 response to the message appearing; note its position. |
| Expected | The message appears next to the upload control within 1 s of the server response. |
| Pass criterion | Adjacent placement and ≤ 1 s. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_res_05_error_adjacent_within_1s` |

### TC-RES-06 - CSV download: columns and row count

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 20 min |
| Objective | Completed predictions are downloadable in the specified shape. |
| Traceability | REQ-FD-21 |
| Preconditions | Completed job on valid_1000.csv. |
| Steps | 1. Use the download control; open the CSV. |
| Expected | Columns row index, predicted class and fraud probability; one row per transaction. |
| Pass criterion | Exactly the three columns; 1,000 data rows. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_res_06_csv_download` |

### TC-RES-07 - Single-page layout, upload control, help link and 1280×720 viewport

| Field | Value |
|---|---|
| Priority / Type / Est. | High / UI / 25 min |
| Objective | All controls are on one page, the upload control takes one file, guidance is always reachable and the layout works at the minimum viewport. |
| Traceability | REQ-UI-01, REQ-UI-04, REQ-UI-06, REQ-FD-01 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Open the Web Client; confirm the API-key field, upload control, model selector, run control and results region are on one page. 2. Try to select two files in the file chooser. 3. Check the help link in every state of the page and open it. 4. Resize the viewport to 1280×720 and walk the upload → run → results flow. |
| Expected | All controls on one page; the chooser accepts a single file; the help link is visible in every state and opens the manual; all controls reachable with consistent styling at 1280×720. |
| Pass criterion | All four checks hold. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_res_07_single_page_single_file_help_and_viewport` |

### TC-API-01 - POST /api/datasets contract

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 10 min |
| Objective | The upload endpoint's success contract is exact. |
| Traceability | REQ-API-01, REQ-API-05 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/datasets with valid_1000.csv; inspect status, headers and body. |
| Expected | HTTP 201; Content-Type application/json; body {"dataset_id": "<non-empty>", "rows": 1000}. |
| Pass criterion | 201 with the exact body shape and JSON content type. |
| Execution | Automated |
| Automated test(s) | `test_upload::test_tc_api_01_upload_contract` |

### TC-API-02 - POST /api/analyses contract

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 10 min |
| Objective | The analysis endpoint's acceptance contract is exact. |
| Traceability | REQ-API-02, REQ-API-05 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. POST /api/analyses with a valid body. |
| Expected | HTTP 202; body {"job_id": "<non-empty>", "status": "queued"}. |
| Pass criterion | 202 with the exact body shape. |
| Execution | Automated |
| Automated test(s) | `test_analyses::test_tc_job_01_and_tc_api_02_accepted_within_2s` |

### TC-API-03 - GET /api/analyses/{job_id} contract

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Functional / 15 min |
| Objective | Status polling returns the documented job shape in every state. |
| Traceability | REQ-API-03, REQ-API-05 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. GET a running job, a completed job and a failed job (from TC-JOB-05); inspect the bodies. |
| Expected | 200 with job_id, dataset_id, model_type and status in every state; model_name, predictions and metrics only when completed; reason {code, message} only when failed. |
| Pass criterion | Shape correct in all three states. |
| Execution | Automated |
| Automated test(s) | `test_job_status::test_tc_api_03_completed_shape`<br>`test_job_status::test_tc_api_03_queued_or_running_shape_has_no_results`<br>`test_job_status::test_tc_api_03_failed_shape_has_reason_only` |

### TC-API-04 - Uniform error body

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Functional / 20 min |
| Objective | All errors share the uniform body shape. |
| Traceability | REQ-API-04 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Trigger 400 (bad upload), 401 (no key) and 404 (unknown job). 2. Inspect each body. |
| Expected | Each body is {"code": "<MACHINE_CODE>", "message": "<text>"} with JSON content type, using the codes listed in SADS Section 3.3. |
| Pass criterion | Uniform shape and documented codes on all three. |
| Execution | Automated |
| Automated test(s) | `test_stp_cases::test_tc_api_04_uniform_error_body` |

### TC-API-05 - Wrong HTTP method → 405

| Field | Value |
|---|---|
| Priority / Type / Est. | Low / Functional / 10 min |
| Objective | Method enforcement on the API surface. |
| Traceability | REQ-API-04, REQ-API-05 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. GET /api/datasets. 2. DELETE /api/analyses/{job_id}. |
| Expected | HTTP 405 with the uniform error body for both. |
| Pass criterion | 405 and error body on both. |
| Execution | Automated |
| Automated test(s) | `test_job_status::test_tc_api_05_delete_job_is_405`<br>`test_upload::test_tc_api_05_get_on_upload_endpoint_is_405` |

### TC-PERF-01 - Upload result within 2 s for up to 10,000 rows

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Performance / 30 min |
| Objective | Typical uploads are acknowledged promptly. |
| Traceability | NFR-01 |
| Preconditions | Single-host deployment on the reference machine; client on the same host so transfer time is negligible. |
| Steps | 1. Upload valid_1000.csv and perf_10k.csv with curl -w %{time_total}; repeat each 3 times. 2. Repeat with a 10,000-row file that has a missing Class column. |
| Expected | Each 201 or 400 response arrives within 2 s. |
| Pass criterion | Median ≤ 2 s for every file. |
| Execution | Automated |
| Automated test(s) | `test_performance::test_tc_perf_01_upload_within_2s`<br>`test_upload::test_tc_perf_01_and_03_upload_timing` |

### TC-PERF-02 - Status polling p95 ≤ 500 ms under 10 concurrent pollers

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Performance / 45 min |
| Objective | The status endpoint stays responsive under concurrent polling. |
| Traceability | NFR-02 |
| Preconditions | A running job; the 10-client polling script. |
| Steps | 1. Launch 10 concurrent pollers for 60 s against GET /api/analyses/{job_id}. 2. Compute the response-time distribution. |
| Expected | p95 response time ≤ 500 ms; no errors. |
| Pass criterion | p95 ≤ 500 ms and zero 5xx responses. |
| Execution | Automated |
| Automated test(s) | `test_performance::test_tc_perf_02_polling_p95_under_500ms` |

### TC-PERF-03 - 100,000-row validation and storage within 60 s

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Performance / 45 min |
| Objective | Large-dataset intake meets its bound on the reference machine. |
| Traceability | NFR-03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload perf_100k.csv; measure from upload completion (server log timestamp) to the 201 response; repeat 3 times on an idle machine. |
| Expected | Validation and storage complete within 60 s. |
| Pass criterion | Median ≤ 60 s. |
| Execution | Automated |
| Automated test(s) | `test_performance::test_tc_perf_03_100k_rows_within_60s`<br>`test_upload::test_tc_perf_01_and_03_upload_timing` |
| **Changed in v1.2** | Measured on the client over HTTP to a server on the same host (an upper bound), not from the server log. (source: DEVIATIONS T-05) |

### TC-PERF-04 - Results page renders within 3 s

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Performance / 20 min |
| Objective | Result rendering is prompt after the completed response arrives. |
| Traceability | NFR-04 |
| Preconditions | Completed job on valid_1000.csv; browser developer tools. |
| Steps | 1. Measure from receipt of the completed job response to the rendered table and metrics; repeat 3 times. |
| Expected | Full render within 3 s. |
| Pass criterion | Median ≤ 3 s. |
| Execution | Automated |
| Automated test(s) | `test_web_client::test_tc_perf_04_results_render_within_3s` |

### TC-PERF-05 - 10 concurrent analysis sessions

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Performance / 45 min |
| Objective | The system sustains 10 parallel sessions without breaking its other targets. |
| Traceability | NFR-05, NFR-Q03 |
| Preconditions | The 10-session script: each session uploads valid_1000.csv, starts a run (model types spread across ML, DL and QML) and polls every 2 s to completion. |
| Steps | 1. Run 10 sessions concurrently. 2. Record upload times, status-poll latencies, response codes and, for one session, the browser render time. |
| Expected | Upload times ≤ 2 s, poll p95 ≤ 500 ms, render ≤ 3 s; at least 99% of requests receive the correct status code; all jobs reach a terminal state. |
| Pass criterion | All targets met under the 10-session load. |
| Execution | Automated |
| Automated test(s) | `test_performance::test_tc_perf_05_ten_concurrent_sessions` |

### TC-PERF-06 - Fast rejection of a large structurally invalid file

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Performance / 25 min |
| Objective | File-level errors are reported quickly regardless of file size. |
| Traceability | NFR-07 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Upload large_noclass.csv (≈400 MB, no Class column); measure from upload completion (server log timestamp) to the 400 response; repeat 3 times. |
| Expected | HTTP 400 "missing required column: Class" within 5 s of upload completion. |
| Pass criterion | Median ≤ 5 s with the correct reason. |
| Execution | Automated |
| Automated test(s) | `test_performance::test_tc_perf_06_400mb_invalid_file_rejected_within_5s`<br>`test_upload::test_tc_perf_06_large_structurally_invalid_file_rejected_fast` |
| **Changed in v1.2** | Measured on the client over HTTP to a server on the same host (an upper bound), not from the server log. (source: DEVIATIONS T-05) |

### TC-SAFE-01 - Analytical-only notice on every results screen

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Safety / 15 min |
| Objective | Outputs are framed as analytical, never as authorization decisions. |
| Traceability | NFR-S02, BR-05 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Complete a job; inspect every results state (table pages, metrics, download area) for the notice. |
| Expected | "Analytical result only — not a financial authorization decision." is visible on all results screens. |
| Pass criterion | Notice present everywhere results appear. |
| Execution | Automated |
| Automated test(s) | `test_safety::test_tc_safe_01_notice_is_part_of_the_results_region` |

### TC-SAFE-02 - No transaction-initiating controls exist

| Field | Value |
|---|---|
| Priority / Type / Est. | High / Safety / 15 min |
| Objective | The system cannot initiate, authorize or block real financial transactions. |
| Traceability | NFR-S01, BR-05 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Walk the entire UI and the API route list (SADS Section 3.2) looking for any control or endpoint that triggers a transaction. |
| Expected | No such control or endpoint exists. |
| Pass criterion | None found. |
| Execution | Automated |
| Automated test(s) | `test_safety::test_tc_safe_02_no_transaction_initiating_endpoint`<br>`test_safety::test_tc_safe_02_no_transaction_controls_in_ui` |

### TC-SAFE-03 - Sample datasets contain no real cardholder data

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Safety / 20 min |
| Objective | Shipped demonstration data is synthetic or anonymized. |
| Traceability | NFR-S03 |
| Preconditions | Server healthy; requests carry the test API key. |
| Steps | 1. Inspect every sample dataset shipped with the system for card-number-like or real-looking cardholder values. |
| Expected | All values synthetic or anonymized and documented as such. |
| Pass criterion | No real cardholder data found. |
| Execution | Automated |
| Automated test(s) | `test_datasets::test_tc_safe_03_no_card_number_like_values_in_shipped_data` |

### TC-SAFE-04 - First-time user completes the workflow within 5 minutes unaided

| Field | Value |
|---|---|
| Priority / Type / Est. | Medium / Usability / 30 min |
| Objective | A first-time user completes the full flow without help. |
| Traceability | NFR-Q01 |
| Preconditions | A participant who has never operated the UI (for example a classmate outside the team); a timer; the API key written on a card. |
| Steps | 1. Without assistance, the participant enters the API key, uploads valid_1000.csv, selects a model, runs the analysis and views the results. |
| Expected | Completion within 5 minutes with no assistance. |
| Pass criterion | Completed within 5 minutes unaided. |
| Execution | Manual |
| Automated test(s) | - |
| **Changed in v1.2** | Protocol and record sheet in docs/USABILITY_WALKTHROUGH.md; the result is recorded in docs/phase3/USABILITY_WALKTHROUGH_RESULT.md. (source: DEVIATIONS T-02) |

