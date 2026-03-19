from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_hunt_script_bootstraps_local_package_import() -> None:
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "scripts" / "run_hunt.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Run Odisseo Signal Atlas locally." in result.stdout
