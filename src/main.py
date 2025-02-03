#!/usr/bin/python

import os
import socketserver

from functools import partial
from src.handler import Handler
from multiprocessing import Pool

PORT = int(os.environ.get('PORT', '8000'))

if __name__ == '__main__':
    with Pool(5) as p:
        # https://stackoverflow.com/a/52046062/1040915
        handler = partial(Handler, p)
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            print("serving at port", PORT)
            httpd.serve_forever()
