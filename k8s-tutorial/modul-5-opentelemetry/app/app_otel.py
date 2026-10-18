"""app-otel: dua servis kecil untuk demo tracing OpenTelemetry (Modul 5).

Satu fail, dua peranan (env ROLE):
  ROLE=kedai      -> /beli?item=buku : panggil servis inventori, kemudian "kira harga"
  ROLE=inventori  -> /stok?item=buku : "semak pangkalan data" (kadang-kadang lambat)
Kedua-dua peranan: /healthz

Trace dihasilkan dengan SDK OpenTelemetry secara manual (tiada auto-instrumentation) supaya
peserta nampak apa yang berlaku: span SERVER, span CLIENT, span dalaman, dan propagasi
konteks melalui header HTTP `traceparent` (W3C Trace Context).

Env:
  OTEL_SERVICE_NAME            -> nama servis dalam Tempo (dibaca terus oleh SDK)
  OTEL_EXPORTER_OTLP_ENDPOINT  -> cth http://otel-collector.monitoring.svc:4318 (dibaca terus oleh SDK)
  OTEL_RESOURCE_ATTRIBUTES     -> atribut tambahan, cth k8s.pod.name=... (dibaca terus oleh SDK)
  INVENTORI_URL                -> (kedai) alamat servis inventori, default http://inventori:8080
  DB_MS                        -> (inventori) masa biasa pangkalan data, ms (default 20)
  LAMBAT_RATE                  -> (inventori) 0.0-1.0, peratus request yang pangkalan datanya lambat
  LAMBAT_MS                    -> (inventori) masa bila lambat, ms (default 800)
  GAGAL_RATE                   -> (inventori) 0.0-1.0, peratus request yang gagal (HTTP 500)
"""
import json
import os
import random
import signal
import socket
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

ROLE = os.environ.get("ROLE", "kedai")
INVENTORI_URL = os.environ.get("INVENTORI_URL", "http://inventori:8080")
DB_MS = float(os.environ.get("DB_MS", "20"))
LAMBAT_RATE = float(os.environ.get("LAMBAT_RATE", "0"))
LAMBAT_MS = float(os.environ.get("LAMBAT_MS", "800"))
GAGAL_RATE = float(os.environ.get("GAGAL_RATE", "0"))
HOSTNAME = socket.gethostname()

# Resource = "siapa" yang menghasilkan span. Resource.create() membaca OTEL_SERVICE_NAME dan
# OTEL_RESOURCE_ATTRIBUTES. Exporter OTLP/HTTP membaca OTEL_EXPORTER_OTLP_ENDPOINT dan
# menambah /v1/traces sendiri. BatchSpanProcessor menghantar span secara berkumpulan di latar.
provider = TracerProvider(resource=Resource.create({"service.namespace": "bengkel"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("app-otel")


def log(msg, **kw):
    # Log JSON dengan trace_id supaya log (Loki, Modul 4) boleh dikaitkan dengan trace (Tempo)
    ctx = trace.get_current_span().get_span_context()
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "pod": HOSTNAME, "role": ROLE, "msg": msg, **kw}
    if ctx.is_valid:
        rec["trace_id"] = format(ctx.trace_id, "032x")
    print(json.dumps(rec), flush=True)


def burn_cpu(ms):
    end = time.perf_counter() + ms / 1000.0
    while time.perf_counter() < end:
        pass


def panggil_inventori(item):
    url = f"{INVENTORI_URL}/stok?item={item}"
    with tracer.start_as_current_span("GET /stok", kind=SpanKind.CLIENT) as span:
        span.set_attribute("http.request.method", "GET")
        span.set_attribute("url.full", url)
        headers = {}
        inject(headers)  # tambah header traceparent: inventori akan menyambung trace yang sama
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as r:
                span.set_attribute("http.response.status_code", r.status)
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            span.set_attribute("http.response.status_code", e.code)
            span.set_status(Status(StatusCode.ERROR, f"inventori pulangkan {e.code}"))
            return e.code, {"error": "inventori gagal"}
        except OSError as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            return 503, {"error": str(e)}


class Handler(BaseHTTPRequestHandler):
    server_version = "app-otel/" + ROLE

    def log_message(self, fmt, *args):
        pass  # log akses ditulis oleh log() di dalam span

    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/healthz":
            return self.send(200, {"status": "ok"})
        item = parse_qs(url.query).get("item", ["buku"])[0]
        route = {"kedai": "/beli", "inventori": "/stok"}[ROLE]
        if url.path != route:
            return self.send(404, {"error": "not found"})
        # Span SERVER: sambung trace daripada header traceparent (jika ada), atau mula trace baharu
        with tracer.start_as_current_span(f"GET {route}", context=extract(self.headers), kind=SpanKind.SERVER) as span:
            span.set_attribute("http.request.method", "GET")
            span.set_attribute("http.route", route)
            span.set_attribute("bengkel.item", item)
            code, body = self.kedai(item) if ROLE == "kedai" else self.inventori(item)
            span.set_attribute("http.response.status_code", code)
            if code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            log(f"GET {route} {code}", item=item, code=code)
            return self.send(code, body)

    def kedai(self, item):
        code, stok = panggil_inventori(item)
        if code != 200:
            return 502, {"error": "tidak dapat semak stok", "item": item}
        with tracer.start_as_current_span("kira-harga") as span:
            burn_cpu(5)
            harga = round(10 + random.random() * 40, 2)
            span.set_attribute("bengkel.harga", harga)
        return 200, {"item": item, "stok": stok["stok"], "harga": harga, "pod": HOSTNAME}

    def inventori(self, item):
        with tracer.start_as_current_span("semak-pangkalan-data") as span:
            lambat = random.random() < LAMBAT_RATE
            span.set_attribute("db.system.name", "simulasi")
            span.set_attribute("bengkel.lambat", lambat)
            time.sleep((LAMBAT_MS if lambat else DB_MS) / 1000.0)
            if random.random() < GAGAL_RATE:
                span.set_status(Status(StatusCode.ERROR, "sambungan pangkalan data terputus"))
                return 500, {"error": "pangkalan data gagal"}
        return 200, {"item": item, "stok": random.randint(0, 100), "pod": HOSTNAME}


def main():
    port = int(os.environ.get("PORT", "8080"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    httpd.daemon_threads = True
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # supaya finally di bawah dijalankan
    log(f"listening on :{port}")
    try:
        httpd.serve_forever()
    finally:
        provider.shutdown()  # hantar span yang masih dalam penimbal


if __name__ == "__main__":
    main()
