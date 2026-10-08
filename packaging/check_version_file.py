"""Fails (in CI, on Windows) if the Windows file-properties file cannot be read by PyInstaller, before a release depends on it."""

from pathlib import Path

from PyInstaller.utils.win32.versioninfo import load_version_info_from_text_file

info = load_version_info_from_text_file(str(Path(__file__).with_name("windows_version_info.txt")))
print("version resource ok,", len(info.toRaw()), "bytes")
