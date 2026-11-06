"""Backup receiver: a small web server that takes backup zips from a Plant record on another computer and keeps the newest
twenty. Run it on the second PC with Docker (docker compose up -d) or plain Python (python3 receiver.py). It answers:
  PUT /backup/<name>    with the X-Backup-Token header: stores the file in ./received
  GET /health           {ok, kept}
Set BACKUP_TOKEN (a long random text, the same one typed into the Plant record) in .env or the environment."""
import json, os, re, socket, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
TOKEN = os.environ.get('BACKUP_TOKEN', '')
DIR = os.environ.get('RECEIVE_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'received'))
KEEP = int(os.environ.get('KEEP', '20'))
NAME = re.compile(r'^plantdb-backup-\d{8}-\d{6}-(manual|auto|update)(-photos)?\.zip$')

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == '/health':
            os.makedirs(DIR, exist_ok=True)
            return self._send(200, {'ok': True, 'kept': len([f for f in os.listdir(DIR) if NAME.match(f)]), 'host': socket.gethostname()})
        self._send(404, {'error': 'not found'})
    def do_PUT(self):
        if not TOKEN or self.headers.get('X-Backup-Token', '') != TOKEN: return self._send(403, {'error': 'wrong or missing token'})
        name = self.path.split('/backup/', 1)[-1] if self.path.startswith('/backup/') else ''
        from urllib.parse import unquote
        name = unquote(name)
        if not NAME.match(name): return self._send(400, {'error': 'that is not a backup file name'})
        n = int(self.headers.get('Content-Length', '0'))
        if n <= 0 or n > 2_000_000_000: return self._send(400, {'error': 'empty or too large'})
        os.makedirs(DIR, exist_ok=True)
        tmp = os.path.join(DIR, '.' + name + '.part')
        with open(tmp, 'wb') as f:
            left = n
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk: break
                f.write(chunk); left -= len(chunk)
        if left: os.remove(tmp); return self._send(400, {'error': 'the file arrived short'})
        os.replace(tmp, os.path.join(DIR, name))
        for f in sorted((f for f in os.listdir(DIR) if NAME.match(f)), reverse=True)[KEEP:]:
            try: os.remove(os.path.join(DIR, f))
            except OSError: pass
        self._send(201, {'ok': True, 'kept': len([f for f in os.listdir(DIR) if NAME.match(f)]), 'host': socket.gethostname()})
    def log_message(self, fmt, *a): sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % a))

if __name__ == '__main__':
    if not TOKEN: print('Set BACKUP_TOKEN first (a long random text).'); raise SystemExit(1)
    port = int(os.environ.get('PORT', '8089'))
    print(f'Backup receiver on port {port}, keeping the newest {KEEP} in {DIR}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()
