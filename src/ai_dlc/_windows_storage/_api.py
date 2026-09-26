"""Small typed Win32 boundary, loaded only for native storage operations."""

from __future__ import annotations

import ctypes as c
from ctypes import wintypes as w
from functools import cache


class FileInfo(c.Structure):
    _fields_ = [
        ("attributes", w.DWORD),
        ("created", w.FILETIME),
        ("accessed", w.FILETIME),
        ("written", w.FILETIME),
        ("volume", w.DWORD),
        ("size_high", w.DWORD),
        ("size_low", w.DWORD),
        ("links", w.DWORD),
        ("index_high", w.DWORD),
        ("index_low", w.DWORD),
    ]

    @property
    def identity(self) -> tuple[int, int, int]:
        return self.volume, self.index_high, self.index_low


class Overlapped(c.Structure):
    _fields_ = [
        ("internal", c.c_size_t),
        ("internal_high", c.c_size_t),
        ("offset", w.DWORD),
        ("offset_high", w.DWORD),
        ("event", w.HANDLE),
    ]


class SecurityAttributes(c.Structure):
    _fields_ = [("length", w.DWORD), ("descriptor", c.c_void_p), ("inherit", w.BOOL)]


class RenameInfo(c.Structure):
    _fields_ = [
        ("replace", w.BOOL),
        ("root", w.HANDLE),
        ("length", w.DWORD),
        ("name", w.WCHAR * 1),
    ]


class UnicodeString(c.Structure):
    _fields_ = [("length", w.USHORT), ("maximum", w.USHORT), ("buffer", w.LPWSTR)]


class ObjectAttributes(c.Structure):
    _fields_ = [
        ("length", w.ULONG),
        ("root", w.HANDLE),
        ("name", c.POINTER(UnicodeString)),
        ("attributes", w.ULONG),
        ("security", c.c_void_p),
        ("quality", c.c_void_p),
    ]


class IoStatus(c.Structure):
    _fields_ = [("status", c.c_void_p), ("information", c.c_size_t)]


def _windows_ctypes(name):
    # ctypes' Win32 attributes are deliberately absent on the Unix review host.
    return getattr(c, name)


def last_error() -> int:
    return _windows_ctypes("get_last_error")()


def winerror(code: int | None = None) -> OSError:
    return _windows_ctypes("WinError")(last_error() if code is None else code)


def _bind(library, name, result, *arguments):
    function = getattr(library, name)
    function.restype = result
    function.argtypes = list(arguments)
    return function


class Api:
    def __init__(self):
        dll = _windows_ctypes("WinDLL")
        kernel = dll("kernel32", use_last_error=True)
        security = dll("advapi32", use_last_error=True)
        shell = dll("shell32", use_last_error=True)
        native = dll("ntdll")
        self.nt_open = _bind(
            native,
            "NtCreateFile",
            c.c_long,
            c.POINTER(w.HANDLE),
            w.DWORD,
            c.POINTER(ObjectAttributes),
            c.POINTER(IoStatus),
            c.c_void_p,
            w.DWORD,
            w.DWORD,
            w.DWORD,
            w.DWORD,
            c.c_void_p,
            w.DWORD,
        )
        self.nt_error = _bind(native, "RtlNtStatusToDosError", w.ULONG, c.c_long)
        self.close = _bind(kernel, "CloseHandle", w.BOOL, w.HANDLE)
        self.open = _bind(
            kernel,
            "CreateFileW",
            w.HANDLE,
            w.LPCWSTR,
            w.DWORD,
            w.DWORD,
            c.c_void_p,
            w.DWORD,
            w.DWORD,
            w.HANDLE,
        )
        self.info = _bind(
            kernel, "GetFileInformationByHandle", w.BOOL, w.HANDLE, c.POINTER(FileInfo)
        )
        self.mkdir = _bind(kernel, "CreateDirectoryW", w.BOOL, w.LPCWSTR, c.c_void_p)
        self.volume = _bind(
            kernel,
            "GetVolumeInformationByHandleW",
            w.BOOL,
            w.HANDLE,
            w.LPWSTR,
            w.DWORD,
            c.c_void_p,
            c.c_void_p,
            c.c_void_p,
            w.LPWSTR,
            w.DWORD,
        )
        self.drive = _bind(kernel, "GetDriveTypeW", w.UINT, w.LPCWSTR)
        self.set_info = _bind(
            kernel, "SetFileInformationByHandle", w.BOOL, w.HANDLE, c.c_int, c.c_void_p, w.DWORD
        )
        self.read = _bind(
            kernel,
            "ReadFile",
            w.BOOL,
            w.HANDLE,
            c.c_void_p,
            w.DWORD,
            c.POINTER(w.DWORD),
            c.c_void_p,
        )
        self.write = _bind(
            kernel,
            "WriteFile",
            w.BOOL,
            w.HANDLE,
            c.c_void_p,
            w.DWORD,
            c.POINTER(w.DWORD),
            c.c_void_p,
        )
        self.flush = _bind(kernel, "FlushFileBuffers", w.BOOL, w.HANDLE)
        self.lock = _bind(
            kernel,
            "LockFileEx",
            w.BOOL,
            w.HANDLE,
            w.DWORD,
            w.DWORD,
            w.DWORD,
            w.DWORD,
            c.POINTER(Overlapped),
        )
        self.unlock = _bind(
            kernel,
            "UnlockFileEx",
            w.BOOL,
            w.HANDLE,
            w.DWORD,
            w.DWORD,
            w.DWORD,
            c.POINTER(Overlapped),
        )
        self.process = _bind(kernel, "GetCurrentProcess", w.HANDLE)
        self.token = _bind(
            security, "OpenProcessToken", w.BOOL, w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)
        )
        self.token_info = _bind(
            security,
            "GetTokenInformation",
            w.BOOL,
            w.HANDLE,
            c.c_int,
            c.c_void_p,
            w.DWORD,
            c.POINTER(w.DWORD),
        )
        self.sid_string = _bind(
            security, "ConvertSidToStringSidW", w.BOOL, c.c_void_p, c.POINTER(w.LPWSTR)
        )
        self.security_info = _bind(
            security,
            "GetSecurityInfo",
            w.DWORD,
            w.HANDLE,
            c.c_int,
            w.DWORD,
            c.POINTER(c.c_void_p),
            c.c_void_p,
            c.POINTER(c.c_void_p),
            c.c_void_p,
            c.POINTER(c.c_void_p),
        )
        self.ace = _bind(security, "GetAce", w.BOOL, c.c_void_p, w.DWORD, c.POINTER(c.c_void_p))
        self.sddl = _bind(
            security,
            "ConvertStringSecurityDescriptorToSecurityDescriptorW",
            w.BOOL,
            w.LPCWSTR,
            w.DWORD,
            c.POINTER(c.c_void_p),
            c.c_void_p,
        )
        self.free = _bind(kernel, "LocalFree", c.c_void_p, c.c_void_p)
        self.folder = _bind(
            shell,
            "SHGetKnownFolderPath",
            c.c_long,
            c.c_void_p,
            w.DWORD,
            w.HANDLE,
            c.POINTER(w.LPWSTR),
        )
        self.task_free = _bind(dll("ole32"), "CoTaskMemFree", None, c.c_void_p)


@cache
def api() -> Api:
    import os

    if os.name != "nt":
        raise OSError("Native Windows storage requires Windows and local NTFS")
    return Api()


def checked(result):
    if not result:
        raise winerror()
    return result


def info(handle) -> FileInfo:
    value = FileInfo()
    checked(api().info(handle, c.byref(value)))
    return value


def open_relative(
    parent, name: str, access: int, share: int, creation: int, attributes, directory: bool
):
    text = c.create_unicode_buffer(name)
    byte_length = len(name.encode("utf-16-le"))
    unicode = UnicodeString(byte_length, byte_length + 2, c.cast(text, w.LPWSTR))
    security = (
        c.cast(attributes, c.POINTER(SecurityAttributes)).contents.descriptor
        if attributes
        else None
    )
    objects = ObjectAttributes(
        c.sizeof(ObjectAttributes), parent, c.pointer(unicode), 0x40 | 0x1000, security, None
    )
    handle, status = w.HANDLE(), IoStatus()
    disposition = {1: 2, 3: 1, 4: 3}[creation]  # CREATE_NEW/OPEN_EXISTING/OPEN_ALWAYS
    options = 0x20 | 0x00200000 | (1 if directory else 0x40)
    result = api().nt_open(
        c.byref(handle),
        access | 0x100000,
        c.byref(objects),
        c.byref(status),
        None,
        0,
        share,
        disposition,
        options,
        None,
        0,
    )
    if result < 0:
        if result & 0xFFFFFFFF == 0xC000050B:
            raise ValueError("Native managed path encountered a reparse point")
        raise winerror(api().nt_error(result))
    if handle.value is None:
        raise OSError("Native open returned no handle")
    return handle.value
