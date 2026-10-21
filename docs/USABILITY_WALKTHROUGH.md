# Usability walkthrough protocol (TC-SAFE-04, NFR-Q01)

This one STP case cannot be automated, because it needs a person who has never used the system.
It is tracked as issue #33 (planned owner: Raghav Balaji).

## Setup

1. Start the system: `python run_all.py`. Note the API key it prints.
2. Write the API key on a card.
3. Open <http://127.0.0.1:5000/> on a laptop at 1280×720 or larger.
4. Put `tests/data/valid_1000.csv` on the desktop.
5. Choose a participant from outside the team who has never seen the system.

## Task given to the participant (read it out, then do not help)

> "Using this page and the key on this card, upload the file valid_1000.csv on the desktop,
> run fraud detection with any model, and show me the results."

Start a timer when you finish reading. Stop it when the metrics and the predictions table are
on the screen.

## Record

| Field | Value |
|---|---|
| Date | |
| Participant (initials, programme) | |
| Model chosen | |
| Time to results (mm:ss) | |
| Asked for help? (yes/no, at which step) | |
| Errors made (e.g. wrong file, forgot model) | |
| Comments from the participant | |
| **Pass (<= 5:00 and no help)?** | |

After the walkthrough, put the result in `docs/TEST_REPORT.md` (TC-SAFE-04 row) and close issue #33.
