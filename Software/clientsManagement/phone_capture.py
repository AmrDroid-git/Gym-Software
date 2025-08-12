# phone_capture.py
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QPushButton, QWidget, QHBoxLayout
)

ANDROID_DIR = "/sdcard/Gymphotos"       # folder on the phone
INBOX_DIR = Path("phone_inbox")         # local folder to store pulled photos

def _run_adb(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(["adb"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def adb_device_ok() -> bool:
    code, out, _ = _run_adb(["get-state"])
    return code == 0 and out == "device"

def adb_dir_exists(remote_dir: str) -> bool:
    code, out, _ = _run_adb(["shell", f"[ -d '{remote_dir}' ] && echo OK || echo NO"])
    return "OK" in out

def newest_jpg(remote_dir: str) -> Optional[str]:
    code, out, _ = _run_adb(["shell", f"ls -1t {remote_dir}/*.jpg 2>/dev/null"])
    if code != 0 or not out:
        return None
    return out.splitlines()[0].strip()

def pull_unique(remote_path: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    base = dest_dir / Path(remote_path).name
    target = base
    i = 1
    while target.exists():
        target = dest_dir / f"{base.stem}_{i}{base.suffix}"
        i += 1
    _run_adb(["pull", remote_path, str(target)])
    return target

class PhoneCaptureDialog(QDialog):
    """
    Shows 'waiting for a picture' -> when a new JPG appears in ANDROID_DIR,
    pulls it locally and shows a preview with Accept / Do it again / Close.
    On Accept, dialog is Accepted and 'selected_path' holds the local file path.
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Take picture from phone")
        self.resize(560, 640)

        self._baseline: Optional[str] = None
        self.selected_path: Optional[Path] = None

        # UI
        self.v = QVBoxLayout(self)
        self.info = QLabel("", self)
        self.info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview = QLabel(self)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(480, 480)
        self.preview.setStyleSheet("background:#222; color:#bbb;")

        self.btns = QDialogButtonBox(self)
        self.btn_accept = QPushButton("Accept")
        self.btn_again = QPushButton("Do it again")
        self.btn_close = QPushButton("Close")
        self.btns.addButton(self.btn_accept, QDialogButtonBox.ButtonRole.AcceptRole)
        self.btns.addButton(self.btn_again, QDialogButtonBox.ButtonRole.ResetRole)
        self.btns.addButton(self.btn_close, QDialogButtonBox.ButtonRole.RejectRole)

        self.v.addWidget(self.info)
        self.v.addWidget(self.preview, 1)
        self.v.addWidget(self.btns)

        self.btn_accept.clicked.connect(self._accept)
        self.btn_again.clicked.connect(self._reset_waiting)
        self.btn_close.clicked.connect(self.reject)

        # Timer for polling
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # 1 second
        self.timer.timeout.connect(self._tick)

        self._enter_waiting()

    # --- States ---
    def _enter_waiting(self):
        # pre-checks
        if not adb_device_ok():
            self._set_info("Waiting for device via ADB… (is USB debugging ON?)")
        elif not adb_dir_exists(ANDROID_DIR):
            self._set_info(f"Waiting for folder on phone: {ANDROID_DIR}")
        else:
            self._set_info("Waiting for a picture… open camera on phone, take a photo.")
        self.selected_path = None
        self.btn_accept.setEnabled(False)
        self.btn_again.setEnabled(False)
        self._baseline = newest_jpg(ANDROID_DIR)
        self.preview.setPixmap(QPixmap())  # clear
        self.preview.setText("Waiting…")
        self.timer.start()

    def _enter_showing(self, local_path: Path):
        self.timer.stop()
        self.selected_path = local_path
        self._set_info(f"New photo received: {local_path.name}")
        pm = QPixmap(str(local_path))
        if not pm.isNull():
            pm = pm.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(pm)
            self.preview.setText("")
        else:
            self.preview.setText("(cannot display image)")
        self.btn_accept.setEnabled(True)
        self.btn_again.setEnabled(True)

    # --- Helpers ---
    def _set_info(self, text: str):
        self.info.setText(text)

    def _tick(self):
        if not adb_device_ok() or not adb_dir_exists(ANDROID_DIR):
            # keep showing waiting messages; baseline stays as-is
            return
        current = newest_jpg(ANDROID_DIR)
        if (self._baseline is None and current) or (self._baseline and current and current != self._baseline):
            local = pull_unique(current, INBOX_DIR)
            self._enter_showing(local)

    def _reset_waiting(self):
        self._enter_waiting()

    def _accept(self):
        if self.selected_path and self.selected_path.exists():
            self.accept()
        else:
            self._enter_waiting()
