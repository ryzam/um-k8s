"""demo-app: aplikasi kecil untuk makmal autoscaling & operasi Kubernetes.

Endpoint:
  /                 -> info pod (hostname, versi)
  /cpu?ms=100       -> bakar CPU selama N milisaat (untuk HPA CPU)
  /mem?mb=20&hold=60 -> peruntuk N MB memori dan simpan selama `hold` saat (untuk HPA memory / OOMKilled)
  /healthz          -> liveness probe
  /readyz           -> readiness probe (503 semasa start-up dan semasa shutdown)
  /metrics          -> metrik format Prometheus
  /crash            -> tamatkan proses dengan exit code 1 (untuk makmal troubleshooting)

Env:
  VERSION           -> label versi (cth: v1, v2) untuk rolling update / canary
  STARTUP_DELAY     -> saat sebelum pod jadi Ready (default 3)
  SHUTDOWN_DELAY    -> saat menunggu selepas SIGTERM sebelum berhenti (default 5)
  FAIL_RATE         -> 0.0-1.0, peratus request / yang pulangkan HTTP 500 (simulasi versi rosak)
"""
import json
import os
import random
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = os.environ.get("VERSION", "v1")
STARTUP_DELAY = float(os.environ.get("STARTUP_DELAY", "3"))
SHUTDOWN_DELAY = float(os.environ.get("SHUTDOWN_DELAY", "5"))
FAIL_RATE = float(os.environ.get("FAIL_RATE", "0"))
HOSTNAME = socket.gethostname()
STARTED = time.time()

state = {"ready": False, "shutting_down": False}
lock = threading.Lock()
counters = {}  # (path, code) -> count
held_memory = []


def count(path, code):
    with lock:
        counters[(path, code)] = counters.get((path, code), 0) + 1


def burn_cpu(ms):
    end = time.perf_counter() + ms / 1000.0
    x = 0
    while time.perf_counter() < end:
        x += 1
    return x


def hold_memory(mb, hold):
    block = bytearray(mb * 1024 * 1024)
    for i in range(0, len(block), 4096):  # sentuh setiap page supaya betul-betul RSS
        block[i] = 1
    with lock:
        held_memory.append(block)
    time.sleep(hold)
    with lock:
        held_memory.remove(block)


class Handler(BaseHTTPRequestHandler):
    server_version = "demo-app/" + VERSION

    def log_message(self, fmt, *args):
        # Log satu baris JSON ke stdout supaya mudah di-parse oleh Fluent Bit
        print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "pod": HOSTNAME,
                          "version": VERSION, "msg": fmt % args}), flush=True)

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        count(urlparse(self.path).path, code)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path == "/":
            if FAIL_RATE and random.random() < FAIL_RATE:
                return self.send(500, {"error": "simulated failure", "version": VERSION, "pod": HOSTNAME})
            return self.send(200, {"pod": HOSTNAME, "version": VERSION, "uptime_s": round(time.time() - STARTED)})
        if url.path == "/cpu":
            ms = min(int(q.get("ms", ["100"])[0]), 5000)
            burn_cpu(ms)
            return self.send(200, {"pod": HOSTNAME, "version": VERSION, "cpu_ms": ms})
        if url.path == "/mem":
            mb = min(int(q.get("mb", ["20"])[0]), 2048)
            hold = min(int(q.get("hold", ["60"])[0]), 3600)
            threading.Thread(target=hold_memory, args=(mb, hold), daemon=True).start()
            return self.send(200, {"pod": HOSTNAME, "allocated_mb": mb, "hold_s": hold})
        if url.path == "/healthz":
            return self.send(200, {"status": "ok"})
        if url.path == "/readyz":
            ok = state["ready"] and not state["shutting_down"]
            return self.send(200 if ok else 503, {"ready": ok})
        if url.path == "/metrics":
            lines = ["# HELP demo_http_requests_total Jumlah request HTTP.",
                     "# TYPE demo_http_requests_total counter"]
            with lock:
                for (path, code), n in sorted(counters.items()):
                    lines.append(f'demo_http_requests_total{{path="{path}",code="{code}",version="{VERSION}"}} {n}')
                mb_held = sum(len(b) for b in held_memory) / 1024 / 1024
            lines += ["# HELP demo_memory_held_mb Memori yang sedang dipegang oleh /mem.",
                      "# TYPE demo_memory_held_mb gauge", f"demo_memory_held_mb {mb_held}"]
            return self.send(200, ("\n".join(lines) + "\n").encode(), "text/plain; version=0.0.4")
        if url.path == "/crash":
            self.send(200, {"crashing": True})
            print(json.dumps({"level": "fatal", "pod": HOSTNAME, "msg": "crash requested"}), flush=True)
            os._exit(1)
        return self.send(404, {"error": "not found"})


def main():
    port = int(os.environ.get("PORT", "8080"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    httpd.daemon_threads = True

    def become_ready():
        time.sleep(STARTUP_DELAY)
        state["ready"] = True
        print(json.dumps({"level": "info", "pod": HOSTNAME, "version": VERSION, "msg": "ready"}), flush=True)

    def on_sigterm(signum, frame):
        # Graceful shutdown: gagal readiness dahulu, tunggu endpoint dibuang, kemudian tutup.
        state["shutting_down"] = True
        print(json.dumps({"level": "info", "pod": HOSTNAME, "msg": f"SIGTERM, draining {SHUTDOWN_DELAY}s"}), flush=True)

        def stop():
            time.sleep(SHUTDOWN_DELAY)
            httpd.shutdown()
        threading.Thread(target=stop, daemon=True).start()

    signal.signal(signal.SIGTERM, on_sigterm)
    threading.Thread(target=become_ready, daemon=True).start()
    print(json.dumps({"level": "info", "pod": HOSTNAME, "version": VERSION, "msg": f"listening on :{port}"}), flush=True)
    httpd.serve_forever()
    sys.exit(0)


if __name__ == "__main__":
    main()
