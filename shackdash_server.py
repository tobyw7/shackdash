#!/usr/bin/env python3
"""
ShackDash Local Server
Serves ~/shack/ on localhost:7373 and proxies SOTA/POTA spot APIs.
"""
import http.server
import socketserver
import os
import urllib.request
import json

PORT = 7373
DIRECTORY = os.path.expanduser("~/shack")

SOTA_URL = "https://api2.sota.org.uk/api/spots/10/all"
POTA_URL = "https://api.pota.app/spot/activator"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/spots':
            self._serve_spots()
        else:
            super().do_GET()

    def _serve_spots(self):
        spots = []
        # Fetch SOTA spots
        try:
            req = urllib.request.Request(
                SOTA_URL, headers={'User-Agent': 'ShackDash/1.0'})
            with urllib.request.urlopen(req, timeout=8) as r:
                sota = json.loads(r.read())
            for s in sota[:10]:
                spots.append({
                    'type':      'SOTA',
                    'callsign':  s.get('activatorCallsign', ''),
                    'reference': (s.get('associationCode', '') + '/' + s.get('summitCode', '')) if s.get('associationCode') else s.get('summitCode', ''),
                    'freq':      str(s.get('frequency', '')),
                    'mode':      s.get('mode', ''),
                    'comment':   s.get('comments', ''),
                    'time':      s.get('timeStamp', ''),
                })
        except Exception as e:
            print(f"SOTA fetch error: {e}")

        # Fetch POTA spots
        try:
            req = urllib.request.Request(
                POTA_URL, headers={'User-Agent': 'ShackDash/1.0'})
            with urllib.request.urlopen(req, timeout=8) as r:
                pota = json.loads(r.read())
            for s in (pota[:10] if isinstance(pota, list) else []):
                spots.append({
                    'type':      'POTA',
                    'callsign':  s.get('activator', ''),
                    'reference': s.get('reference', ''),
                    'freq':      str(s.get('frequency', '')),
                    'mode':      s.get('mode', ''),
                    'comment':   s.get('comments', ''),
                    'time':      s.get('spotTime', ''),
                })
        except Exception as e:
            print(f"POTA fetch error: {e}")

        body = json.dumps(spots).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"ShackDash server running on http://127.0.0.1:{PORT}")
        httpd.serve_forever()
