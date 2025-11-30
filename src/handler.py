import os
import json
from http import HTTPStatus
import http.server
from urllib.parse import urlparse

from yt_dlp import YoutubeDL

ALLOWED_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "youtu.be"}


def is_valid_youtube_url(url: str) -> bool:
    """Check for http(s) scheme and YouTube host."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.split(":")[0]
    return host in ALLOWED_YOUTUBE_HOSTS


# https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#extract-audio
def download(url, filename=None):
    if not is_valid_youtube_url(url):
        raise ValueError("URL must be a YouTube http(s) URL")
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'paths': {
            'home': os.environ.get('DOWNLOAD_DIR', '.')
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a'
        }]
    }
    if filename:
        ydl_opts['outtmpl'] = {'default': filename}
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(url)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, pool, *args, **kwargs):
        self.pool = pool
        # https://stackoverflow.com/a/52046062/1040915
        super().__init__(*args, **kwargs)

    def do_POST(self):
        try:
            content_length = self.headers['Content-Length']
            if not content_length:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                content = "Looks like you forgot to send a body".encode('utf-8')
                self.send_header("Content-type", 'application/json')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                return

            data_string = self.rfile.read(int(content_length))
            body = json.loads(data_string) # TODO - better error-handling here
            url = body.get('url')
            filename = body.get('filename')
            if not url:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                content = "Looks like you forgot to send a `url` parameter".encode('utf-8')
                self.send_header("Content-type", 'application/json')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                return
            if not is_valid_youtube_url(url):
                self.send_response(HTTPStatus.BAD_REQUEST)
                content = "Invalid URL - only YouTube URLs with http(s) scheme are allowed".encode('utf-8')
                self.send_header("Content-type", 'application/json')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                return

            self.send_response(HTTPStatus.ACCEPTED)
            content = f'Accepted download request for {url}\n'.encode('utf-8')
            self.send_header("Content-type", 'application/json')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            # TODO - check for success of kicking-off the thread
            self.pool.apply_async(download, (url,), {'filename': filename})
            self.wfile.write(content)
        except Exception as e:
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            content = str(e).encode('utf-8')
            print(e) # TODO - better logging!
            self.send_header("Content-type", 'application/json')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)

    def do_GET(self):
        # No need for a full webserver here!
        if self.path in ("/", "/index.html"):
            static_dir = os.path.join(os.path.dirname(__file__), "static")
            index_path = os.path.join(static_dir, "index.html")
            try:
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-type", "text/html")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                content = "UI is missing".encode("utf-8")
                self.send_header("Content-type", "text/plain")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            content = "Not found".encode('utf-8')
            self.send_header("Content-type", 'text/plain')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
