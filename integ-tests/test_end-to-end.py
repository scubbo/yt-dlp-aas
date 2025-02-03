import pathlib
import requests
import time

def test_download():
    target_file_name = "A Beginner's Guide to the EICAR Test File [bTThnbwxN5g].m4a"
    download_path = pathlib.Path('/download')
    url = 'https://www.youtube.com/watch?v=bTThnbwxN5g'

    try:
        # `app` is injected as a DNS name by the Docker Compose harness
        response = requests.post('http://app:8000/download', json={
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
