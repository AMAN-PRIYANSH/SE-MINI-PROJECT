"""Run the STP performance cases against a running deployment and print a JSON report.

    python run_all.py                     # in another terminal (CCFD_API_KEY=... set)
    python tests/perf/run_perf.py --url http://127.0.0.1:5000 --key <key> [--quick]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.fixtures.make_datasets import DATA, GENERATED, large_noclass, perf  # noqa: E402
from tests.perf import harness  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5000")
    ap.add_argument("--key", required=True)
    ap.add_argument("--quick", action="store_true", help="20 s polling instead of 60 s")
    ap.add_argument("--large-mb", type=int, default=400)
    a = ap.parse_args()
    if not (GENERATED / "perf_100k.csv").exists():
        perf()
    if not (GENERATED / "large_noclass.csv").exists():
        large_noclass(a.large_mb)

    report = {"TC-PERF-01": [harness.upload_timing(a.url, a.key, p) for p in
                             (DATA / "valid_1000.csv", GENERATED / "perf_10k.csv", GENERATED / "perf_10k_noclass.csv")],
              "TC-PERF-03": harness.upload_timing(a.url, a.key, GENERATED / "perf_100k.csv"),
              "TC-PERF-06": harness.upload_timing(a.url, a.key, GENERATED / "large_noclass.csv")}
    _, _, body = harness.upload(a.url, a.key, DATA / "valid_1000.csv")
    import requests
    job = requests.post(f"{a.url}/api/analyses", headers={"Authorization": f"Bearer {a.key}"},
                        json={"dataset_id": body["dataset_id"], "model_type": "ml"}).json()
    report["TC-PERF-02"] = harness.poll_load(a.url, a.key, job["job_id"], 10, 20 if a.quick else 60)
    report["TC-PERF-05"] = harness.session_load(a.url, a.key, DATA / "valid_1000.csv", 10)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
