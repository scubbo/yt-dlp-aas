import os
import pathlib
import socket
import time

import pytest
import requests


def _can_reach_app_host(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
    except socket.gaierror:
        return False
    return True

def test_download():
    app_host = os.environ.get('APP_HOST', 'app')
    download_path = pathlib.Path(os.environ.get('DOWNLOAD_DIR', '/download'))
    if not _can_reach_app_host(app_host):
        pytest.skip("App host is not reachable outside the compose harness")
    if not download_path.exists():
        pytest.skip("Download directory is not available")

    target_file_name = "A Beginner's Guide to the EICAR Test File [bTThnbwxN5g].m4a"
    url = 'https://www.youtube.com/watch?v=bTThnbwxN5g'

    try:
        # `app` is injected as a DNS name by the Docker Compose harness
        response = requests.post(f'http://{app_host}:8000/download', json={
            'url': url
        })
        assert response.status_code == 202, f"Non-202 response: {response.status_code}. Body: {response.json()}"
        time.sleep(2)
        for _ in range(5):
            if _does_target_file_exist(target_file_name, download_path):
                break
            else:
                time.sleep(3)
        else:
            assert False, "File not found after 15 seconds"
    finally:
        for f in download_path.iterdir():
            if f.name != 'README.md':
                f.unlink()

def _does_target_file_exist(file_name: str, dir: pathlib.Path) -> bool:
    for f in dir.iterdir():
        if f.name == file_name:
            return True
        else:
            print(f"Found file: {f.name} which does not match")
    return False
