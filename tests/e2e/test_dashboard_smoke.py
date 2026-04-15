from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from importlib.util import find_spec
from urllib.request import urlopen

import pytest


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.skipif(
    shutil.which("streamlit") is None and find_spec("streamlit") is None,
    reason="streamlit is not installed",
)
def test_dashboard_streamlit_entrypoint_smoke() -> None:
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "apps/streamlit/erro_leitura_dashboard.py",
            "--server.headless=true",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.time() + 30
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                    assert response.status == 200
                    return
            except Exception as exc:  # noqa: BLE001 - retry loop must tolerate startup errors.
                last_error = exc
                time.sleep(0.5)
        output = process.stdout.read() if process.stdout else ""
        raise AssertionError(f"Streamlit dashboard did not become healthy: {last_error}\n{output}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
