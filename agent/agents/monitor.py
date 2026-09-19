from __future__ import annotations

import hashlib
import os
import threading
import time
from typing import Callable, Iterable

from ..db import claim_invoice, log_file_event, mark_error


def _hash_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _is_supported(name: str) -> bool:
    return name.lower().endswith((".pdf", ".docx", ".png"))


def _is_ignored(name: str) -> bool:
    lowered = name.lower()
    ignored_suffixes = (
        ".part",
        ".tmp",
        ".crdownload",
    )
    if name.startswith(".") or name.startswith("~$"):
        return True
    if lowered.endswith(ignored_suffixes):
        return True
    return False


class InvoiceMonitor(threading.Thread):
    def __init__(self, incoming_dir: str, poll_seconds: int = 3, callback: Callable | None = None) -> None:
        super().__init__(daemon=True)
        self.incoming_dir = incoming_dir
        self.poll_seconds = poll_seconds
        self.callback = callback
        self.stop_event = threading.Event()
        self.stability_state: dict[str, tuple[int, float, int]] = {}

    def _scan(self) -> Iterable[str]:
        if not os.path.isdir(self.incoming_dir):
            return []
        files: list[str] = []
        for entry in os.scandir(self.incoming_dir):
            if entry.is_dir():
                continue
            name = entry.name
            if _is_ignored(name):
                continue
            files.append(entry.path)
        return sorted(files)

    def _check_stability(self, path: str) -> bool:
        stat = os.stat(path)
        current = (stat.st_size, float(stat.st_mtime))
        prior = self.stability_state.get(path)
        if prior is None:
            self.stability_state[path] = (*current, 1)
            return False
        if prior[:2] == current:
            new_count = prior[2] + 1
            self.stability_state[path] = (*current, new_count)
            return new_count >= 2
        self.stability_state[path] = (*current, 1)
        return False

    def _handle_file(self, path: str) -> None:
        name = os.path.basename(path)
        if not _is_supported(name):
            checksum = _hash_file(path) if os.path.exists(path) else "unreadable"
            log_file_event(None, path, checksum, "unsupported", f"Unsupported extension for {name}")
            return

        try:
            file_size = os.path.getsize(path)
            if file_size == 0:
                synthetic = hashlib.sha256(f"{path}unreadable".encode("utf-8")).hexdigest()
                mark_error(None, f"{path} is empty or unreadable", "0-byte file rejected")
                log_file_event(None, path, synthetic, "error", "0-byte file observed")
                return
            checksum = _hash_file(path)
            invoice_id = claim_invoice(path, name, name.rsplit(".", 1)[-1].lower(), checksum)
            if invoice_id is None:
                log_file_event(None, path, checksum, "duplicate", "File already claimed")
                return
            log_file_event(invoice_id, path, checksum, "detected", "File detected and claimed")
            if self.callback is not None:
                self.callback({
                    "file_path": path,
                    "file_name": name,
                    "file_type": name.rsplit(".", 1)[-1].lower(),
                    "file_checksum": checksum,
                    "invoice_id": invoice_id,
                })
        except Exception as exc:
            synthetic = hashlib.sha256(f"{path}unreadable".encode("utf-8")).hexdigest()
            log_file_event(None, path, synthetic, "error", str(exc))
            mark_error(None, str(exc), "file could not be processed")

    def run(self) -> None:
        while not self.stop_event.is_set():
            for path in self._scan():
                if self._check_stability(path):
                    self._handle_file(path)
            time.sleep(self.poll_seconds)

    def stop(self) -> None:
        self.stop_event.set()
