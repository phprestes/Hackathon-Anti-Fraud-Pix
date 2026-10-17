import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_worker_once() -> None:
    """Runs one worker cycle as an external process; tests never import from src/."""
    result = subprocess.run(
        ["docker", "compose", "run", "--rm", "worker", "python", "-m", "worker", "--once"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, f"worker --once failed:\n{result.stdout}\n{result.stderr}"
