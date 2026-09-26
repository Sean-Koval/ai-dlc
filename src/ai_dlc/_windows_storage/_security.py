"""Current-account private Windows objects; never trust environment account paths."""

from __future__ import annotations

import ctypes as c
import uuid
from contextlib import contextmanager
from ctypes import wintypes as w
from functools import cache
from pathlib import Path

from ._api import SecurityAttributes, api, checked, winerror


class Acl(c.Structure):
    _fields_ = [
        ("revision", c.c_ubyte),
        ("reserved", c.c_ubyte),
        ("size", w.WORD),
        ("count", w.WORD),
        ("reserved2", w.WORD),
    ]


class Ace(c.Structure):
    _fields_ = [
        ("kind", c.c_ubyte),
        ("flags", c.c_ubyte),
        ("size", w.WORD),
        ("mask", w.DWORD),
        ("sid", w.DWORD),
    ]


def sid_text(sid) -> str:
    value = w.LPWSTR()
    checked(api().sid_string(sid, c.byref(value)))
    try:
        return value.value or ""
    finally:
        api().free(c.cast(value, c.c_void_p))


@cache
def current_sid() -> str:
    handle = w.HANDLE()
    checked(api().token(api().process(), 0x0008, c.byref(handle)))
    try:
        size = w.DWORD()
        api().token_info(handle, 1, None, 0, c.byref(size))
        buffer = c.create_string_buffer(size.value)
        checked(api().token_info(handle, 1, buffer, size, c.byref(size)))
        return sid_text(c.cast(buffer, c.POINTER(c.c_void_p))[0])
    finally:
        api().close(handle)


def local_app_data() -> Path:
    identifier = c.create_string_buffer(uuid.UUID("f1b32785-6fba-4fcf-9d55-7b8e7f157091").bytes_le)
    value = w.LPWSTR()
    result = api().folder(identifier, 0, None, c.byref(value))
    if result < 0:
        raise OSError(f"Cannot resolve current-account local application data: {result}")
    try:
        if not value.value:
            raise ValueError("Current-account local application data is unavailable")
        return Path(value.value)
    finally:
        api().task_free(c.cast(value, c.c_void_p))


@contextmanager
def private_attributes():
    descriptor = c.c_void_p()
    sid = current_sid()
    checked(
        api().sddl(f"O:{sid}D:P(A;OICI;FA;;;{sid})(A;OICI;FA;;;SY)", 1, c.byref(descriptor), None)
    )
    attributes = SecurityAttributes(c.sizeof(SecurityAttributes), descriptor, False)
    try:
        yield c.byref(attributes)
    finally:
        api().free(descriptor)


def validate_private(handle, *, account_directory: bool = False) -> None:
    owner, dacl, descriptor = c.c_void_p(), c.c_void_p(), c.c_void_p()
    result = api().security_info(
        handle, 1, 0x1 | 0x4, c.byref(owner), None, c.byref(dacl), None, c.byref(descriptor)
    )
    if result:
        raise winerror(result)
    try:
        sid = current_sid()
        allowed = {sid, "S-1-5-18", "S-1-5-32-544"}
        owners = allowed if account_directory else {sid}
        if sid_text(owner) not in owners or not dacl.value:
            raise ValueError("Windows private object owner or DACL is unsafe")
        for index in range(c.cast(dacl, c.POINTER(Acl)).contents.count):
            pointer = c.c_void_p()
            checked(api().ace(dacl, index, c.byref(pointer)))
            if pointer.value is None:
                raise ValueError("Windows private object DACL contains an invalid ACE")
            entry = c.cast(pointer, c.POINTER(Ace)).contents
            if entry.flags & 0x8:  # INHERIT_ONLY_ACE does not grant access to this object.
                continue
            if entry.kind == 1:  # A deny ACE cannot grant another principal access.
                continue
            if entry.kind != 0 or sid_text(pointer.value + Ace.sid.offset) not in allowed:
                raise ValueError(
                    "Windows private object DACL grants access outside the current account"
                )
    finally:
        api().free(descriptor)


@contextmanager
def copied_attributes(handle):
    owner, dacl, descriptor = c.c_void_p(), c.c_void_p(), c.c_void_p()
    result = api().security_info(
        handle, 1, 0x1 | 0x4, c.byref(owner), None, c.byref(dacl), None, c.byref(descriptor)
    )
    if result:
        raise winerror(result)
    try:
        if not owner.value or not dacl.value:
            raise ValueError("Existing Windows file has an unsafe security descriptor")
        yield c.byref(SecurityAttributes(c.sizeof(SecurityAttributes), descriptor, False))
    finally:
        api().free(descriptor)
