"""Isolated Python-provider worker: executed with -I -S, no site or bytecode caches."""

import contextlib
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


class VerifiedSource(importlib.abc.Loader):
    def __init__(self, entry):
        self.entry = entry

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        path = Path(self.entry["path"])
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != self.entry["sha256"]:
            raise ValueError("Python provider source digest changed")
        module.__file__ = str(path)
        if self.entry["package"]:
            module.__path__ = [str(path.parent)]
        exec(compile(content, str(path), "exec"), module.__dict__)  # noqa: S102 -- verified source loader bypasses unverified bytecode


class VerifiedFinder(importlib.abc.MetaPathFinder):
    def __init__(self, modules):
        self.modules = modules
        self.roots = {name.split(".", 1)[0] for name in modules}

    def find_spec(self, fullname, path=None, target=None):
        entry = self.modules.get(fullname)
        if entry:
            if hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError("Python provider dependency digest changed")
            loader = (
                importlib.machinery.ExtensionFileLoader(fullname, entry["path"])
                if entry.get("native")
                else VerifiedSource(entry)
            )
            return importlib.util.spec_from_file_location(
                fullname,
                entry["path"],
                loader=loader,
                submodule_search_locations=[str(Path(entry["path"]).parent)]
                if entry["package"]
                else None,
            )
        if any(name.startswith(fullname + ".") for name in self.modules):
            spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = []
            return spec
        if fullname.split(".", 1)[0] in self.roots:
            raise ModuleNotFoundError(
                "Import outside verified provider dependency closure: " + fullname
            )
        return None  # -I -S leaves only the interpreter's standard library available.


def main():
    message = json.load(sys.stdin)
    modules = message["modules"]
    if set(sys.modules) & set(modules):
        raise ValueError("Provider attempts to replace a loaded standard-library module")
    sys.meta_path.insert(0, VerifiedFinder(modules))
    with contextlib.redirect_stdout(sys.stderr):
        module_name, symbol = message["entry_point"].split(":", 1)
        value: Any = importlib.import_module(module_name)
        for part in symbol.split("."):
            value = getattr(value, part)
        provider = value(message["config"])
        request = message["request"]
        operation, payload = request["operation"], request["payload"]
        result = (
            getattr(provider, operation)(**payload)
            if operation in {"current", "merged", "ci", "deployment", "append"}
            else provider.invoke(operation, payload)
        )
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
