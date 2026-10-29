# User manual: Credit Card Fraud Detection and Model Performance Evaluation System

Release 1.0 · Team Error 404 · This manual is SRS section 2.6, item 1. You can also open it from
the **Help & user manual** link at the top of every screen.

## 1. What the system does

You give the system a CSV file of credit-card transactions in which every row is already labelled
as legitimate or fraud. You choose one of three model types. The model predicts, for every row,
whether it is fraud and how likely that is. The system then compares those predictions with your
labels and reports how good the model was.

| Model type | Model used | Kind |
|---|---|---|
| **ML** | Random Forest (`random_forest`) | classical machine learning |
| **DL** | Multilayer perceptron (`mlp`) | neural network |
| **QML** | 4-qubit variational quantum classifier (`vqc_4qubit`) | quantum machine learning on a simulator |

> **Analytical result only. Not a financial authorization decision.** The system never approves,
> blocks or changes a real transaction.

## 2. Before you start

- Ask the person who runs the system for the **API key**. Every action needs it.
- Open the address you were given (by default <http://127.0.0.1:5000/>) in Chrome, Firefox or Edge.
  The page works at 1280 × 720 and larger.
- The key is kept only while the page is open. After a reload you must enter it again. This is
  deliberate, so the key is never stored in your browser.

## 3. Preparing the dataset

Your file must follow all of these rules. A file that breaks one is rejected, and the message says
which rule failed.

| Rule | Detail |
|---|---|
| Format | `.csv`, UTF-8 text, **comma**-separated, first row is the header |
| Size | at most **500 MB** and **1,000,000** data rows; at least 1 data row |
| Label column | `Class`, with value `0` (legitimate) or `1` (fraud) in every row |
| Feature columns | `V1`, `V2`, … `V28` and `Amount`, all numbers (no empty cells, no text) |
| Other columns | allowed and ignored (for example `Time`, or your own reference column) |

The 30 required columns are the same as in the public Kaggle *Credit Card Fraud Detection* dataset.
There, `V1`–`V28` are anonymised components of the original transaction fields, so any file in that
format works as is.

A ready-made synthetic example ships with the system: `data/samples/sample_transactions.csv`
(2,000 rows, about 2 % fraud). Do not upload real cardholder data. Release 1.0 is meant for
synthetic or anonymised data only.

## 4. Step by step

1. **API key.** Paste the key into the *API key* field.
2. **Upload.** Under *Transaction file*, choose one `.csv` file and press **Upload**. If it is
   accepted you see *Dataset accepted: N rows.* If not, the reason appears in red under the button
   (see section 6).
3. **Model.** Select exactly one of **ML**, **DL** or **QML**.
4. **Run.** Press **Run fraud detection**. The badge next to the button changes from
   `queued` to `running` to `completed`. You do not need to reload the page, because it checks the
   status every 2 seconds. A run is stopped and marked failed if it takes longer than 10 minutes.
5. **Results.** When the run completes, the results appear automatically (section 5).
6. **Compare.** Select another model and press **Run** again on the same dataset. Each result is
   labelled with the name of the model that produced it.
7. **Download.** Press **Download predictions (CSV)** to save `row_index, predicted_class,
   fraud_probability` for every row.

Your dataset and its results are deleted automatically **24 hours** after the upload.

## 5. Reading the results

**Metrics.** These are computed by comparing the predictions with your `Class` column. Each is shown
to 4 decimal places.

| Metric | Question it answers |
|---|---|
| Accuracy | What share of all rows was classified correctly? |
| Precision | Of the rows flagged as fraud, what share really were fraud? |
| Recall | Of the real frauds, what share were caught? |
| F1-score | The balance of precision and recall (their harmonic mean) |
| ROC-AUC | How well the fraud probabilities rank frauds above legitimate rows (0.5 = random, 1 = perfect). Shown as *n/a* if the file contains only one class |

Fraud is rare: about 0.17 % of transactions in the Kaggle data. A model that never flags anything
would still score about 99.8 % accuracy, so compare models on **precision, recall and F1**.

**Confusion matrix.** This shows four counts:

- **true positives**: frauds that were flagged
- **false negatives**: frauds that were missed
- **false positives**: legitimate rows that were flagged
- **true negatives**: legitimate rows that were correctly passed

The four counts add up to the number of rows.

**Predictions table.** For each row it shows the row index (0 is the first data row), the predicted
class (`1 fraud` / `0 legit`) and the fraud probability. It shows 50 rows per page; use **Previous**
and **Next** to move between pages. A row is predicted as fraud when its probability is 0.5 or more.

## 6. Messages and what to do

| Message | Meaning and fix |
|---|---|
| Enter the API key first. | Paste the key before uploading |
| The API key was rejected. | The key is wrong or has spaces; ask for the correct key |
| unsupported file type … | The file is not a text `.csv` file (for example an Excel file renamed). Export it as CSV, UTF-8 |
| the file is empty / the file has no data rows | Add data rows under the header |
| file exceeds the 500 MB limit / the 1,000,000 row limit | Split the file into smaller files |
| wrong delimiter: the file must be comma-delimited | Your file uses `;` or tabs. Re-export it with commas |
| missing required column: X | Add column X (the names are case-sensitive) |
| invalid value in column Class at row N | Row N has a label that is not 0 or 1 (or is empty) |
| non-numeric or missing value in column X at row N | Row N has text or an empty cell in feature X |
| malformed CSV: the rows do not match the header | Some row has more fields than the header |
| Select a model (ML, DL or QML) before running. | Choose a model type |
| Upload a dataset before running. | Upload an accepted file first |
| The requested dataset/job was not found. | The data is older than 24 hours and was deleted; upload again |
| Run failed: The model service is unavailable … | That model's service is not running. Try another model, or ask the operator to restart it |
| Run failed: The analysis timed out … | The run took more than 10 minutes. Use a smaller file |

Row numbers count data rows from 1, not counting the header. Messages never repeat the values
in your file.

## 7. For the operator

Start everything with `python run_all.py`. It prints the API key to give to users. Configuration,
the API and troubleshooting for developers are covered in the project
[README](https://github.com/AMAN-PRIYANSH/SE-MINI-PROJECT#readme).
