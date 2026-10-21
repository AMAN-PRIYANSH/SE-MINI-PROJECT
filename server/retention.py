"""Retention purge task (SRS SR-05; SADS 2.4 item 4).

Every purge_interval_s (10 minutes by default) the task deletes each dataset whose
retention period (24 hours after upload) has ended, together with its sidecar, its job
records and its results. Expired items are already invisible to the API before the purge
runs, because the store checks expires_at on every read.
"""
import logging
import threading

log = logging.getLogger("ccfd.retention")


class PurgeTask:
    def __init__(self, store, interval_s):
        self.store = store
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="retention-purge")

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()

    def run_once(self):
        removed = self.store.purge_expired()
        if removed:
            log.info("retention purge removed %d dataset(s)", len(removed))
        return removed

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as e:  # keep the task alive
                log.error("retention purge error %s", type(e).__name__)
            self._stop.wait(self.interval_s)
