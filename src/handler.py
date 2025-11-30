import os
import json
from http import HTTPStatus
import http.server

from yt_dlp import YoutubeDL

# https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#extract-audio
def download(url, filename=None):
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
        self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
        content = 'ERROR: Only POST requests are permitted\n'.encode('utf-8')
        self.send_header("Content-type", 'application/json')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)
