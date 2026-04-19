"""watchdog-based file watcher that runs the pipeline on new photos in BOX_WATCH_DIR."""
from __future__ import annotations

import hashlib
import json
import queue
import threading
import time
from pathlib import Path

from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import Config
from .gemini_client import GeminiClient
from .pipeline import process

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


class Watcher:
    def __init__(self, cfg: Config, client: GeminiClient) -> None:
        self.cfg = cfg
        self.client = client
        self._queue: queue.Queue[Path] = queue.Queue()
        self._state_path = cfg.log_dir / "state.json"
        self._state = _load_state(self._state_path)
        self._stop = threading.Event()

    def run(self) -> None:
        self.cfg.ensure_dirs()
        handler = _Handler(self._enqueue)
        observer = Observer()
        observer.schedule(handler, str(self.cfg.box_watch_dir), recursive=False)
        observer.start()
        logger.info("Watching {}", self.cfg.box_watch_dir)

        worker = threading.Thread(target=self._worker, daemon=True)
        worker.start()

        for f in sorted(self.cfg.box_watch_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXT:
                self._enqueue(f)

        try:
            while not self._stop.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            observer.stop()
            observer.join()

    def _enqueue(self, path: Path) -> None:
        if path.suffix.lower() not in SUPPORTED_EXT:
            return
        self._queue.put(path)

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                path = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                self._process_one(path)
            except Exception as exc:
                logger.exception("Pipeline error for {}: {}", path, exc)

    def _process_one(self, path: Path) -> None:
        if not _wait_stable_size(path, self.cfg.stable_size_seconds):
            logger.debug("File never stabilized, skipping: {}", path)
            return
        if not path.exists():
            return
        digest = _sha256(path)
        if digest in self._state.get("hashes", {}):
            logger.debug("Already processed (hash match): {}", path)
            return
        logger.info("New photo: {}", path)
        draft = process(path, self.cfg, self.client)
        self._state.setdefault("hashes", {})[digest] = {
            "source": str(path),
            "draft": str(draft),
            "ts": time.time(),
        }
        _save_state(self._state_path, self._state)


class _Handler(FileSystemEventHandler):
    def __init__(self, on_new: callable) -> None:  # type: ignore[valid-type]
        super().__init__()
        self._on_new = on_new

    def on_created(self, event) -> None:  # noqa: ANN001
        if not event.is_directory:
            self._on_new(Path(event.src_path))

    def on_moved(self, event) -> None:  # noqa: ANN001
        if not event.is_directory:
            self._on_new(Path(event.dest_path))


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {"hashes": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"hashes": {}}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _wait_stable_size(path: Path, seconds: int, poll: float = 0.5, timeout: float = 120.0) -> bool:
    deadline = time.time() + timeout
    last_size = -1
    stable_since = 0.0
    while time.time() < deadline:
        if not path.exists():
            time.sleep(poll)
            continue
        size = path.stat().st_size
        if size == last_size and size > 0:
            if stable_since and (time.time() - stable_since) >= seconds:
                return True
            if not stable_since:
                stable_since = time.time()
        else:
            last_size = size
            stable_since = 0.0
        time.sleep(poll)
    return False
