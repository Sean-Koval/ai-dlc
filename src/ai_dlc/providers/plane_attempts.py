"""Immutable private Plane intents: one local sender, no reset or deletion API."""

import fcntl
import hashlib
import json
import os
import stat
from contextlib import contextmanager
from pathlib import Path


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def unsafe():
    return ValueError(
        "Plane intent storage is unsafe or corrupt; retain it and inspect the operation"
    )


class PlaneAttemptStore:
    def __init__(self, root, state_home):
        self.root = Path(root).resolve()
        base = Path(state_home)
        if not base.is_absolute() or not self.root.is_dir():
            raise unsafe()
        self.base = base
        self.path = base / "ai-dlc" / "provider-attempts" / "plane" / digest(str(self.root))
        self.snapshot = None

    @contextmanager
    def directory(self):
        descriptors = []
        links = []
        try:
            parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
            descriptors.append(parent)
            current = Path("/")
            for part in self.path.parts[1:]:
                current /= part
                try:
                    child = os.open(
                        part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
                    )
                except FileNotFoundError:
                    try:
                        os.mkdir(part, 0o700, dir_fd=parent)
                        os.fsync(parent)
                    except FileExistsError:
                        pass
                    child = os.open(
                        part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
                    )
                descriptors.append(child)
                metadata = os.fstat(child)
                if (current == self.base or self.base in current.parents) and (
                    metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o022
                ):
                    raise unsafe()
                links.append((parent, part, metadata.st_dev, metadata.st_ino))
                parent = child
            fcntl.flock(parent, fcntl.LOCK_EX)
            self._check_links(links)
            snapshot = [(part, dev, ino) for _, part, dev, ino in links]
            if self.snapshot is not None and snapshot != self.snapshot:
                raise unsafe()
            self.snapshot = snapshot
            yield parent
            self._check_links(links)
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise unsafe() from None
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    @staticmethod
    def _check_links(links):
        for parent, part, dev, ino in links:
            item = os.stat(part, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(item.st_mode) or (item.st_dev, item.st_ino) != (dev, ino):
                raise unsafe()

    @staticmethod
    def _check_file(directory, name, fd):
        opened = os.fstat(fd)
        linked = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or stat.S_IMODE(opened.st_mode) & 0o077
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (linked.st_dev, linked.st_ino)
        ):
            raise unsafe()
        return opened

    def begin(self, operation_id, fingerprint):
        if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 1000:
            raise ValueError("Plane requires a bounded stable operation_id")
        expected = {
            "schema": 1,
            "root": str(self.root),
            "operation_id": operation_id,
            "fingerprint": digest(fingerprint),
        }
        expected_bytes = (json.dumps(expected, sort_keys=True) + "\n").encode()
        name = digest(operation_id) + ".json"
        with self.directory() as directory:
            created = False
            try:
                fd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=directory,
                )
                created = True
            except FileExistsError:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                self._check_file(directory, name, fd)
                if created:
                    encoded = expected_bytes
                    while encoded:
                        encoded = encoded[os.write(fd, encoded) :]
                    os.fsync(fd)
                    os.fsync(directory)
                else:
                    data = os.read(fd, 8193)
                    if len(data) > 8192 or data != expected_bytes:
                        raise unsafe()
                metadata = self._check_file(directory, name, fd)
                self.intent = (name, metadata.st_dev, metadata.st_ino, expected_bytes)
            finally:
                os.close(fd)
        return created

    def verify(self):
        name, dev, ino, expected = self.intent
        with self.directory() as directory:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                metadata = self._check_file(directory, name, fd)
                if (metadata.st_dev, metadata.st_ino) != (dev, ino) or os.read(
                    fd, 8193
                ) != expected:
                    raise unsafe()
            finally:
                os.close(fd)
