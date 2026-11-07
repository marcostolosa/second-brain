"""Secret retrieval. The Jev token comes from the environment or the Windows
Credential Manager — never from Git, Markdown, logs, or prompts.

Set it once (PowerShell), stored as a generic credential:
    cmdkey /generic:SecondBrain/TypeSafe /user:token /pass:<YOUR_TOKEN>
Read here via the Win32 CredRead API (ctypes, no third-party dep).
"""

from __future__ import annotations

import os

__all__ = ["get_typesafe_token", "CRED_TARGET"]

CRED_TARGET = "SecondBrain/TypeSafe"


def _cred_read_windows(target: str) -> str | None:
    import ctypes
    from ctypes import wintypes

    CRED_TYPE_GENERIC = 1

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    CredReadW = advapi32.CredReadW
    CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                          ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    CredReadW.restype = wintypes.BOOL
    CredFree = advapi32.CredFree
    CredFree.argtypes = [ctypes.c_void_p]

    pcred = ctypes.POINTER(CREDENTIAL)()
    if not CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
        return None
    try:
        cred = pcred.contents
        size = cred.CredentialBlobSize
        if not size:
            return None
        blob = ctypes.string_at(cred.CredentialBlob, size)
        # cmdkey stores the password as UTF-16LE; fall back to UTF-8.
        try:
            return blob.decode("utf-16-le").rstrip("\x00") or None
        except UnicodeDecodeError:
            return blob.decode("utf-8", "replace") or None
    finally:
        CredFree(pcred)


def get_typesafe_token() -> str | None:
    """Return the Jev/TypeSafe bearer token, or None if not configured."""
    env = os.environ.get("TYPESAFE_API_TOKEN")
    if env and env.strip():
        return env.strip()
    if os.name == "nt":
        try:
            return _cred_read_windows(CRED_TARGET)
        except OSError:
            return None
    return None
