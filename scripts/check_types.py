"""Type-check all platform implementations using the prepared interpreter's imports.

The shared Pyright configuration checks both Unix and Windows code on every host.
Native runtime tests enforce dispatch and API availability; static success does
not extend platform qualification.
"""

import subprocess
import sys

if __name__ == "__main__":
    raise SystemExit(
        subprocess.run(
            [sys.executable, "-m", "pyright", "--pythonpath", sys.executable], check=False
        ).returncode
    )
