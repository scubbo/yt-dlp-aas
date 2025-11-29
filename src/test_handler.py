import os
import pathlib
import tempfile
from unittest.mock import patch

from src.handler import download

def test_download():
    video_url = "https://www.youtube.com/watch?v=bTThnbwxN5g"
    expected_filename = "A Beginner's Guide to the EICAR Test File [bTThnbwxN5g].m4a"
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.environ['DOWNLOAD_DIR'] = tmpdirname
        with patch('src.handler.YoutubeDL') as mock_ydl:
            ydl_instance = mock_ydl.return_value.__enter__.return_value
            ydl_instance.download.side_effect = lambda url: pathlib.Path(tmpdirname, expected_filename).touch()
            download(video_url)
        download_dir = pathlib.Path(tmpdirname)
        passes = False
        for contents in download_dir.iterdir():
            print(f'DEBUG - {contents=}')
            if contents.name == expected_filename:
                passes = True
                break
        assert passes, "Could not find downloaded file"
