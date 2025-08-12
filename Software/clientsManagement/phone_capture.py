# phone_capture.py
from __future__ import annotations
import os, sys, shutil, subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QPushButton, QWidget, QHBoxLayout
)

# ---------------- Paths (your logic kept) ----------------
ANDROID_DIR = "/sdcard/Gymphotos"

def _documents_dir() -> Path:
    # Use Windows Known Folder when available; fallback otherwise
    try:
        if os.name == "nt":
            from ctypes import windll, wintypes, byref
            FOLDERID_Documents = (0xFDD39AD0, 0x238F, 0x46AF, 0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7)
            SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [wintypes.GUID, wintypes.DWORD, wintypes.HANDLE, wintypes.LPWSTR]
            p = wintypes.LPWSTR()
            SHGetKnownFolderPath(wintypes.GUID(*FOLDERID_Documents), 0, 0, byref(p))
            return Path(p.value)
    except Exception:
        pass
    return Path.home() / "Documents"

APP_DATA_DIR = _documents_dir() / "GymSoftware"
INBOX_DIR = APP_DATA_DIR / "phone_inbox"

# ---------------- ADB helpers (hardened) ----------------
def _adb_path() -> str:
    # 1) env override
    p = os.getenv("ADB_PATH")
    if p and Path(p).exists():
        return p
    # 2) bundled with PyInstaller (next to the exe) or a local ./adb folder
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    for cand in (base / "adb.exe", base / "adb", base / "adb" / "adb.exe"):
        if cand.exists():
            return str(cand)
    # 3) system PATH
    return shutil.which("adb") or "adb"

# Hide spawned consoles on Windows and avoid UI stalls
_STARTUPINFO = None
_CREATE_NO_WINDOW = 0
if os.name == "nt":
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _CREATE_NO_WINDOW = 0x08000000

def _run_adb(args: list[str], timeout: float = 2.0) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            [_adb_path()] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            startupinfo=_STARTUPINFO,
            creationflags=_CREATE_NO_WINDOW,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError:
        return 127, "", "adb not found"

def adb_device_ok() -> bool:
    code, out, _ = _run_adb(["get-state"])
    return code == 0 and out == "device"

def adb_dir_exists(remote_dir: str) -> bool:
    code, out, _ = _run_adb(["shell", f"[ -d '{remote_dir}' ] && echo OK || echo NO"])
    return code == 0 and "OK" in out

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

# ---------------- Dialog ----------------
class PhoneCaptureDialog(QDialog):
    """
    Waits for a new JPG in ANDROID_DIR, pulls it to INBOX_DIR,
    shows a preview, Accept exposes 'selected_path'.
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Take picture from phone")
        self.resize(560, 640)

        self._baseline: Optional[str] = None
        self.selected_path: Optional[Path] = None

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

        self.timer = QTimer(self)
        self.timer.setInterval(1000)   # 1s polling
        self.timer.timeout.connect(self._tick)

        self._enter_waiting()

    def _enter_waiting(self):
        INBOX_DIR.mkdir(parents=True, exist_ok=True)

        code, _, _ = _run_adb(["version"])
        if code == 127:
            self._set_info("ADB not found. Bundle adb.exe or set ADB_PATH.")
        elif not adb_device_ok():
            self._set_info("Waiting for device via ADB… (USB debugging ON? Authorized?)")
        elif not adb_dir_exists(ANDROID_DIR):
            self._set_info(f"Waiting for folder on phone: {ANDROID_DIR}")
        else:
            self._set_info("Waiting for a picture… open camera and take a photo.")

        self.selected_path = None
        self.btn_accept.setEnabled(False)
        self.btn_again.setEnabled(False)
        self._baseline = newest_jpg(ANDROID_DIR)
        self.preview.setPixmap(QPixmap())
        self.preview.setText("Waiting…")
        self.timer.start()

    def _enter_showing(self, local_path: Path):
        self.timer.stop()
        self.selected_path = local_path
        self._set_info(f"New photo received: {local_path.name}")

        pm = QPixmap(str(local_path))
        if not pm.isNull():
            pm = pm.scaled(self.preview.size(),
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(pm)
            self.preview.setText("")
        else:
            self.preview.setText("(cannot display image)")

        self.btn_accept.setEnabled(True)
        self.btn_again.setEnabled(True)

    def _tick(self):
        # fast exits avoid blocking the UI
        if not adb_device_ok() or not adb_dir_exists(ANDROID_DIR):
            return
        current = newest_jpg(ANDROID_DIR)
        if not current:
            return
        if (self._baseline is None) or (current != self._baseline):
            local = pull_unique(current, INBOX_DIR)
            self._enter_showing(local)

    def _set_info(self, text: str):
        self.info.setText(text)

    def _reset_waiting(self):
        self._enter_waiting()

    def _accept(self):
        if self.selected_path and self.selected_path.exists():
            self.accept()
        else:
            self._enter_waiting()
