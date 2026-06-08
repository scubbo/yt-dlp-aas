import os
import pathlib
import tempfile
import json
from unittest.mock import patch, MagicMock

from src.handler import download, is_valid_youtube_url, Handler


def test_download():
    video_url = "https://www.youtube.com/watch?v=bTThnbwxN5g"
    expected_filename = "A Beginner's Guide to the EICAR Test File [bTThnbwxN5g].m4a"
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.environ["DOWNLOAD_DIR"] = tmpdirname
        with patch("src.handler.YoutubeDL") as mock_ydl:
            ydl_instance = mock_ydl.return_value.__enter__.return_value
            ydl_instance.download.side_effect = lambda url: pathlib.Path(
                tmpdirname, expected_filename
            ).touch()
            download(video_url)
        download_dir = pathlib.Path(tmpdirname)
        passes = False
        for contents in download_dir.iterdir():
            print(f"DEBUG - {contents=}")
            if contents.name == expected_filename:
                passes = True
                break
        assert passes, "Could not find downloaded file"


def test_download_with_filename_override():
    video_url = "https://www.youtube.com/watch?v=bTThnbwxN5g"
    expected_filename = "my-custom-file.m4a"
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.environ["DOWNLOAD_DIR"] = tmpdirname
        with patch("src.handler.YoutubeDL") as mock_ydl:
            ydl_instance = mock_ydl.return_value.__enter__.return_value
            ydl_instance.download.side_effect = lambda url: pathlib.Path(
                tmpdirname, expected_filename
            ).touch()
            download(video_url, filename=expected_filename)

        # Ensure we passed the custom filename into yt_dlp
        ydl_opts = mock_ydl.call_args[0][0]
        assert ydl_opts["outtmpl"]["default"] == expected_filename

        # Ensure the file exists with the requested name
        download_dir = pathlib.Path(tmpdirname)
        assert any(p.name == expected_filename for p in download_dir.iterdir())


def test_is_valid_youtube_url():
    assert is_valid_youtube_url("https://www.youtube.com/watch?v=abc")
    assert is_valid_youtube_url("http://youtube.com/watch?v=abc")
    assert is_valid_youtube_url("https://youtu.be/abc")
    assert not is_valid_youtube_url("https://www.example.com/watch?v=abc")
    assert not is_valid_youtube_url("ftp://www.youtube.com/watch?v=abc")


def test_openapi_spec_is_valid_json():
    spec_path = pathlib.Path(__file__).parent / "static" / "openapi.json"
    with spec_path.open() as f:
        data = json.load(f)
    assert data["openapi"].startswith("3.")
    assert "/download" in data["paths"]


def test_openapi_spec_matches_handler_contract():
    spec_path = pathlib.Path(__file__).parent / "static" / "openapi.json"
    with spec_path.open() as f:
        data = json.load(f)

    download_op = data["paths"]["/download"]["post"]
    req = download_op["requestBody"]["content"]["application/json"]["schema"]
    # Resolve the ref for the schema we use in the handler
    schema = data["components"]["schemas"]["DownloadRequest"] if "$ref" in req else req

    assert download_op["responses"].keys() >= {"202", "400", "500"}
    assert schema["required"] == ["url"]
    assert "filename" in schema["properties"]
    assert schema["properties"]["url"]["description"].startswith("YouTube URL")


def test_download_with_cookies():
    video_url = "https://www.youtube.com/watch?v=bTThnbwxN5g"
    cookies = "session_token=abc123; auth_token=def456"
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.environ["DOWNLOAD_DIR"] = tmpdirname
        with patch("src.handler.YoutubeDL") as mock_ydl:
            ydl_instance = mock_ydl.return_value.__enter__.return_value
            ydl_instance.download.side_effect = lambda url: None
            download(video_url, cookies=cookies)
            ydl_opts = mock_ydl.call_args[0][0]
            assert "http_headers" in ydl_opts
            assert ydl_opts["http_headers"]["Cookie"] == cookies


def test_download_without_cookies_no_headers():
    video_url = "https://www.youtube.com/watch?v=bTThnbwxN5g"
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.environ["DOWNLOAD_DIR"] = tmpdirname
        with patch("src.handler.YoutubeDL") as mock_ydl:
            ydl_instance = mock_ydl.return_value.__enter__.return_value
            ydl_instance.download.side_effect = lambda url: None
            download(video_url)

        # Ensure no http_headers are set when no cookies provided
        ydl_opts = mock_ydl.call_args[0][0]
        assert "http_headers" not in ydl_opts


def test_options_method_cors_headers():
    handler = object.__new__(Handler)
    handler.pool = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_OPTIONS()

    handler.send_response.assert_called_once()
    handler.send_header.assert_any_call(
        "Access-Control-Allow-Origin", "https://www.youtube.com"
    )
    handler.send_header.assert_any_call(
        "Access-Control-Allow-Methods", "POST, OPTIONS"
    )
    handler.send_header.assert_any_call(
        "Access-Control-Allow-Headers", "Content-Type"
    )


def test_post_with_cookies():
    handler = object.__new__(Handler)
    handler.pool = MagicMock()

    # Mock the request body with cookies
    request_data = json.dumps(
        {
            "url": "https://www.youtube.com/watch?v=bTThnbwxN5g",
            "filename": "test-video.m4a",
            "cookies": "session_token=abc123; auth_token=def456",
        }
    )

    # Mock handler methods
    handler.headers = MagicMock()
    handler.headers.__getitem__.return_value = str(len(request_data))
    handler.rfile = MagicMock()
    handler.rfile.read.return_value = request_data.encode("utf-8")
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()

    # Call POST method
    handler.do_POST()

    # Verify CORS headers are present on the response
    handler.send_header.assert_any_call("Access-Control-Allow-Origin", "https://www.youtube.com")

    # Verify download was called with cookies
    handler.pool.apply_async.assert_called_once()
    args, kwargs = handler.pool.apply_async.call_args
    assert args[0] == download
    assert args[1] == ("https://www.youtube.com/watch?v=bTThnbwxN5g",)
    assert args[2]["filename"] == "test-video.m4a"
    assert args[2]["cookies"] == "session_token=abc123; auth_token=def456"
