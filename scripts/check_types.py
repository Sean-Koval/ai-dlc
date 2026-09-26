"""Type-check against the prepared interpreter on every supported platform."""

import subprocess
import sys

if __name__ == "__main__":
    raise SystemExit(
        subprocess.run(
            [sys.executable, "-m", "pyright", "--pythonpath", sys.executable], check=False
        ).returncode
    )
