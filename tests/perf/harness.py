"""Performance and load harnesses for STP 5.3 (TC-PERF-01 - TC-PERF-06).

Each function works against any running deployment (base_url + API key), so the same
code is used by the pytest perf tests (in-process servers) and by run_perf.py (the real
system started with run_all.py on the reference machine).
"""
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests


def _h(key):
    return {"Authorization": f"Bearer {key}"}


def p95(values):
    values = sorted(values)
    return values[max(0, int(round(0.95 * len(values))) - 1)] if values else None


def upload(base_url, key, path):
    """Upload a file; return (status, seconds from upload completion to response).

    The client sends the body from memory, so on the same host the transfer time is
    negligible; the measured time is dominated by server-side validation and storage.
    """
    data = Path(path).read_bytes()
    t0 = time.perf_counter()
    r = requests.post(f"{base_url}/api/datasets", headers=_h(key), files={"file": (Path(path).name, data)})
    return r.status_code, time.perf_counter() - t0, (r.json() if r.content else {})


def upload_timing(base_url, key, path, repeats=3):
    runs = [upload(base_url, key, path) for _ in range(repeats)]
    return {"file": Path(path).name, "status": [r[0] for r in runs],
            "seconds": [round(r[1], 3) for r in runs], "median_s": round(statistics.median(r[1] for r in runs), 3)}


def poll_load(base_url, key, job_id, clients=10, seconds=60):
    """TC-PERF-02: `clients` concurrent pollers for `seconds` against one job."""
    stop = time.time() + seconds

    def poller():
        lat, codes = [], []
        s = requests.Session()
        while time.time() < stop:
            t0 = time.perf_counter()
            r = s.get(f"{base_url}/api/analyses/{job_id}", headers=_h(key))
            lat.append(time.perf_counter() - t0)
            codes.append(r.status_code)
        return lat, codes

    with ThreadPoolExecutor(clients) as ex:
        results = list(ex.map(lambda _: poller(), range(clients)))
    lat = [x for r in results for x in r[0]]
    codes = [c for r in results for c in r[1]]
    return {"requests": len(lat), "p95_ms": round(p95(lat) * 1000, 1),
            "median_ms": round(statistics.median(lat) * 1000, 1), "max_ms": round(max(lat) * 1000, 1),
            "errors_5xx": sum(c >= 500 for c in codes), "non_200": sum(c != 200 for c in codes)}


def session(base_url, key, path, model_type, poll_s=2.0, timeout_s=600):
    """One analysis session: upload, start a run, poll every poll_s until terminal."""
    s = requests.Session()
    out = {"model_type": model_type, "codes": [], "poll_ms": []}
    data = Path(path).read_bytes()
    t0 = time.perf_counter()
    r = s.post(f"{base_url}/api/datasets", headers=_h(key), files={"file": (Path(path).name, data)})
    out["upload_s"] = time.perf_counter() - t0
    out["codes"].append((r.status_code, 201))
    if r.status_code != 201:
        return out
    r = s.post(f"{base_url}/api/analyses", headers=_h(key),
               json={"dataset_id": r.json()["dataset_id"], "model_type": model_type})
    out["codes"].append((r.status_code, 202))
    job_id = r.json()["job_id"]
    end = time.time() + timeout_s
    while time.time() < end:
        time.sleep(poll_s)
        t0 = time.perf_counter()
        r = s.get(f"{base_url}/api/analyses/{job_id}", headers=_h(key))
        out["poll_ms"].append((time.perf_counter() - t0) * 1000)
        out["codes"].append((r.status_code, 200))
        if r.json().get("status") in ("completed", "failed"):
            out["final"] = r.json()["status"]
            break
    return out


def session_load(base_url, key, path, sessions=10):
    """TC-PERF-05: `sessions` concurrent sessions spread across ML, DL and QML."""
    kinds = ["ml", "dl", "qml"]
    with ThreadPoolExecutor(sessions) as ex:
        results = list(ex.map(lambda i: session(base_url, key, path, kinds[i % 3]), range(sessions)))
    polls = [p for r in results for p in r["poll_ms"]]
    codes = [c for r in results for c in r["codes"]]
    correct = sum(got == want for got, want in codes)
    return {"sessions": sessions,
            "upload_max_s": round(max(r["upload_s"] for r in results), 3),
            "poll_p95_ms": round(p95(polls), 1),
            "correct_status_pct": round(100 * correct / len(codes), 2),
            "all_terminal": all(r.get("final") in ("completed", "failed") for r in results),
            "finals": [r.get("final") for r in results]}
