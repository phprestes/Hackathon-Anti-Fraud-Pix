import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_LOGS = ("graph_sql scored", "graphsage scored", "hmm scored")


def run_worker_once() -> None:
    """Runs one worker cycle as an external process; tests never import from src/."""
    # --no-deps: compose must not converge the running db; -T: no TTY, same behavior with or without a terminal.
    result = subprocess.run(
        ["docker", "compose", "run", "--rm", "--no-deps", "-T", "worker", "python", "-m", "worker", "--once"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, f"worker --once failed:\n{output}"
    missing = [log for log in EXPECTED_LOGS if log not in output]
    assert not missing, f"worker --once ran but did not report {missing}; the cycle saw no data:\n{output}"
