# Penjana diagram SVG untuk tutorial bengkel K8s.
# Setiap diagram guna kelas yang sama; warna datang daripada token --d-*.
from xml.sax.saxutils import escape as esc

SVG_RULES = """
.zone{fill:var(--d-zone);stroke:var(--d-line);stroke-width:1.2}
.zone2{fill:var(--d-zone2);stroke:var(--d-line);stroke-width:1.2;stroke-dasharray:6 4}
.box{fill:var(--d-box);stroke:var(--d-line);stroke-width:1.2}
.acc{fill:var(--d-accbg);stroke:var(--d-acc);stroke-width:1.4}
.warn{fill:var(--d-warnbg);stroke:var(--d-warn);stroke-width:1.4}
.okb{fill:var(--d-okbg);stroke:var(--d-ok);stroke-width:1.4}
.solid{fill:var(--d-acc)}
.t{fill:var(--d-fg);font-size:14px}
.th{fill:var(--d-fg);font-size:14px;font-weight:600}
.ts{fill:var(--d-muted);font-size:12px}
.tl{fill:var(--d-muted);font-size:11px;letter-spacing:.06em;text-transform:uppercase;font-weight:600}
.ta{fill:var(--d-acc);font-size:12px;font-weight:600}
.tw{fill:var(--d-warn);font-size:12px;font-weight:600}
.tn{fill:var(--d-box);font-size:11px;font-weight:700}
.m{font-family:var(--d-mono)}
.arr{fill:none;stroke:var(--d-arrow);stroke-width:1.6}
.arra{fill:none;stroke:var(--d-acc);stroke-width:1.8}
.dash{stroke-dasharray:5 4}
.grid{stroke:var(--d-grid);stroke-width:1}
.area{fill:var(--d-accbg);stroke:var(--d-acc);stroke-width:2}
.head{fill:var(--d-arrow)}
.heada{fill:var(--d-acc)}
text{font-family:var(--d-font)}
"""

LIGHT = dict(zone="#f3f5f8", zone2="#f8f6f1", box="#ffffff", line="#b9c2cf", fg="#18202c",
             muted="#5a6577", acc="#2457c5", accbg="#e6edfb", warn="#b4540b", warnbg="#fbeee2",
             ok="#1f7a4d", okbg="#e3f3ea", arrow="#6b7688", grid="#e1e5eb")
DARK = dict(zone="#1a212c", zone2="#211f1b", box="#121821", line="#3c4757", fg="#e6eaf0",
            muted="#9aa5b6", acc="#7ea4ff", accbg="#1d2a45", warn="#f0a35e", warnbg="#3a2717",
            ok="#5fcf93", okbg="#16301f", arrow="#8b96a8", grid="#2a3340")


def tokens(d):
    return ";".join(f"--d-{k}:{v}" for k, v in d.items())


def standalone_style():
    fonts = "--d-font:'IBM Plex Sans',system-ui,sans-serif;--d-mono:'IBM Plex Mono',ui-monospace,monospace"
    return (f"<style>svg{{{tokens(LIGHT)};{fonts}}}"
            f"@media (prefers-color-scheme:dark){{svg{{{tokens(DARK)}}}}}{SVG_RULES}</style>")


DEFS = ('<defs><marker id="{p}h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="head"/></marker>'
        '<marker id="{p}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="heada"/></marker></defs>')


class D:
    def __init__(self, pid, w, h, title, desc):
        self.p, self.w, self.h, self.title, self.desc = pid, w, h, title, desc
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, cls="box", r=8):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" class="{cls}"/>')

    def text(self, x, y, s, cls="t", anchor="start"):
        self.add(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{esc(s)}</text>')

    def node(self, x, y, w, h, title, sub=None, cls="box", tcls="th", mono_sub=False):
        self.rect(x, y, w, h, cls)
        cx = x + w / 2
        if sub:
            self.text(cx, y + h / 2 - 3, title, tcls, "middle")
            self.text(cx, y + h / 2 + 15, sub, "ts m" if mono_sub else "ts", "middle")
        else:
            self.text(cx, y + h / 2 + 5, title, tcls, "middle")

    def path(self, d, acc=False, dash=False, head=True):
        cls = ("arra" if acc else "arr") + (" dash" if dash else "")
        m = f' marker-end="url(#{self.p}{"a" if acc else "h"})"' if head else ""
        self.add(f'<path d="{d}" class="{cls}"{m}/>')

    def svg(self, standalone):
        style = standalone_style() if standalone else ""
        ns = ' xmlns="http://www.w3.org/2000/svg"' if standalone else ""
        return (f'<svg{ns} viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="{self.p}t {self.p}d">'
                f'<title id="{self.p}t">{esc(self.title)}</title><desc id="{self.p}d">{esc(self.desc)}</desc>'
                f'{style}{DEFS.format(p=self.p)}{"".join(self.parts)}</svg>')


def seni_bina():
    d = D("sb", 900, 460, "Seni bina makmal",
          "Laptop peserta menjalankan kluster k3d lab (k3s dalam Docker) dengan namespace demo, kube-system, monitoring dan logging, "
          "serta stack luar kluster: Prometheus, Grafana, Alertmanager, Loki dan S3.")
    d.rect(8, 8, 884, 444, "zone2", 14)
    d.text(26, 34, "Laptop peserta", "tl")
    d.node(24, 150, 116, 58, "k6 / Locust", "penjana beban", "warn")
    d.path("M140,179 H174")
    d.rect(160, 50, 430, 390, "zone", 12)
    d.text(176, 76, "Kluster k3d “lab” (Docker)", "th")
    for i, n in enumerate(["server-0", "agent-0", "agent-1"]):
        d.node(176 + i * 140, 88, 128, 32, n, cls="box", tcls="ts m")
    rows = [("ns demo", "demo-app · HPA · PDB", "acc"), ("ns kube-system", "Metrics Server", "box"),
            ("ns monitoring", "kube-state-metrics · node-exporter", "box"), ("ns logging", "Fluent Bit (DaemonSet)", "box")]
    for i, (ns, txt, cls) in enumerate(rows):
        y = 140 + i * 72
        d.rect(176, y, 398, 58, cls)
        d.text(192, y + 22, ns, "ts m")
        d.text(192, y + 44, txt, "th")
    d.rect(620, 50, 256, 390, "zone", 12)
    d.text(636, 76, "Luar kluster", "th")
    d.text(860, 76, "docker compose", "ts m", "end")
    d.node(636, 110, 104, 42, "Prometheus")
    d.node(756, 110, 104, 42, "Grafana")
    d.path("M756,131 H742")
    d.node(636, 190, 224, 42, "Alertmanager")
    d.path("M688,152 V188")
    d.node(636, 262, 224, 42, "Email · Slack · Teams", cls="okb")
    d.path("M748,232 V260")
    d.node(636, 352, 104, 42, "Loki")
    d.node(756, 352, 104, 42, "S3", "SeaweedFS")
    d.path("M636,124 H605 V313 H576", acc=True)
    d.add('<text x="598" y="226" class="ta" transform="rotate(-90 598 226)" text-anchor="middle">scrape metrik</text>')
    d.path("M574,380 H612 V373 H634", acc=True)
    d.path("M574,400 H600 V424 H808 V396", acc=True)
    d.text(700, 418, "log", "ta", "middle")
    return d


def aliran_hpa():
    d = D("hp", 900, 300, "Aliran keputusan HPA",
          "kubelet menghantar metrik ke Metrics Server, HPA controller membaca metrics.k8s.io dan menskala Deployment setiap 15 saat.")
    boxes = [(20, 160, "kubelet", "cAdvisor"), (250, 170, "Metrics Server", "kube-system"),
             (490, 170, "HPA controller", "kube-controller-manager"), (730, 150, "Deployment", "demo-app")]
    for x, w, t, s in boxes:
        d.node(x, 40, w, 64, t, s, "acc" if t == "HPA controller" else "box")
    labels = ["/metrics/resource", "metrics.k8s.io", "scale"]
    for i, lab in enumerate(labels):
        x1 = boxes[i][0] + boxes[i][1]
        x2 = boxes[i + 1][0]
        d.path(f"M{x1},72 H{x2 - 2}", acc=(i == 2))
        d.text((x1 + x2) / 2, 28, lab, "ts m", "middle")
    d.path("M805,104 V146 H100 V106", dash=True)
    d.text(452, 140, "pod baharu → lebih banyak metrik; kitaran berulang setiap 15 s", "ts", "middle")
    d.rect(20, 172, 860, 112, "zone", 10)
    d.text(40, 200, "Formula", "tl")
    d.text(40, 230, "desiredReplicas = ceil( currentReplicas × currentUtilization / targetUtilization )", "th m")
    d.text(40, 256, "Contoh: 2 pod, sasaran 50%, purata 150%  →  ceil(2 × 150 / 50) = 6 pod", "t")
    d.text(40, 276, "Toleransi 10% (nisbah 0.9–1.1 diabaikan) · scale-down ambil nilai tertinggi dalam stabilizationWindowSeconds", "ts")
    return d


def kelewatan_hpa():
    d = D("kl", 900, 230, "Kelewatan reaksi HPA",
          "Garis masa 0 hingga 70 saat: resolusi Metrics Server 15 s, sync HPA 15 s, penjadualan dan pull image 1 hingga 30 s, "
          "start container dan readiness 3 hingga 10 s.")
    x0, k = 60, 11
    X = lambda s: x0 + s * k
    for s in range(0, 71, 10):
        d.add(f'<line x1="{X(s)}" y1="70" x2="{X(s)}" y2="170" class="grid"/>')
        d.text(X(s), 190, f"{s} s", "ts m", "middle")
    segs = [(0, 15, "Metrics Server", "~15 s", "box"), (15, 30, "Sync HPA", "~15 s", "box"),
            (30, 40, "Jadual + image", "1–30 s", "warn"), (40, 48, "Start + ready", "3–10 s", "acc")]
    for a, b, t, s, cls in segs:
        d.rect(X(a) + 1, 90, (b - a) * k - 2, 44, cls, 6)
        d.text((X(a) + X(b)) / 2, 82, t, "ts", "middle")
        d.text((X(a) + X(b)) / 2, 117, s, "th m" if b - a > 9 else "ts m", "middle")
    d.rect(X(30) + 1, 142, (60 - 30) * k, 10, "warn", 3)
    d.text(X(61), 151, "jadual + image tanpa cache", "tw")
    d.path(f"M{X(48)},60 V88", acc=True)
    d.text(X(48) + 8, 58, "pod baharu mula terima trafik (≈ 30–70 s)", "ta")
    d.text(x0, 28, "Kenapa HPA tidak serta-merta: jumlah kelewatan sebelum pod baharu melayan request", "th")
    d.text(x0, 214, "Implikasi: minReplicas mesti cukup untuk menampung lonjakan pertama.", "ts")
    return d


def load_tests():
    d = D("lt", 900, 420, "Bentuk beban ujian k6",
          "Empat graf: smoke 2 VU selama 1 minit, load naik ke 10 VU dan tahan, stress naik berperingkat hingga 150 VU, "
          "spike melonjak dari 5 ke 60 RPS dalam 10 saat.")
    panels = [
        ("Smoke", "smoke.js", "VU", [(0, 2), (1, 2)], 2, 1, "2 VU tetap, sahkan skrip"),
        ("Load", "load.js", "VU", [(0, 0), (1, 3), (4, 10), (9, 10), (10, 0)], 10, 10, "naik, tahan 5 min, turun"),
        ("Stress", "stress.js", "VU", [(0, 0), (2, 20), (4, 50), (6, 100), (8, 150), (11, 0)], 150, 11, "melebihi kapasiti, kemudian pulih"),
        ("Spike", "spike.js", "RPS", [(0, 5), (1, 5), (1 + 1/6, 60), (4 + 1/6, 60), (4 + 2/6, 5), (7 + 2/6, 5)], 60, 7 + 2/6, "open model: 5 → 60 RPS dalam 10 s"),
    ]
    W, H = 360, 130
    for i, (name, f, unit, pts, ymax, xmax, note) in enumerate(panels):
        ox = 60 + (i % 2) * 460
        oy = 50 + (i // 2) * 190
        d.text(ox - 40, oy - 18, name, "th")
        d.text(ox - 40 + len(name) * 9 + 10, oy - 18, f, "ts m")
        d.text(ox + W, oy - 18, note, "ts", "end")
        for frac in (0, .5, 1):
            y = oy + H - frac * H
            d.add(f'<line x1="{ox}" y1="{y}" x2="{ox + W}" y2="{y}" class="grid"/>')
            v = ymax * frac
            d.text(ox - 8, y + 4, f"{v:g}", "ts m", "end")
        X = lambda m: ox + m / xmax * W
        Y = lambda v: oy + H - v / ymax * H
        for m in sorted({0, xmax} | ({round(xmax / 2)} if xmax > 2 else set())):
            d.text(X(m), oy + H + 18, f"{m:g} min" if m == int(m) else f"{m:.1f} min", "ts m", "middle")
        line = " ".join(f"{X(m):.1f},{Y(v):.1f}" for m, v in pts)
        poly = f"{X(pts[0][0]):.1f},{oy + H} {line} {X(pts[-1][0]):.1f},{oy + H}"
        d.add(f'<polygon points="{poly}" class="area" style="stroke:none"/>')
        d.add(f'<polyline points="{line}" class="arra" />')
        d.text(ox + 4, oy + 12, unit, "tl")
    return d


def monitoring_luar():
    d = D("mo", 900, 420, "Monitoring luar kluster (Pilihan A)",
          "Prometheus di luar kluster scrape kube-state-metrics melalui NodePort, node-exporter pada port 9100, "
          "dan cAdvisor serta pod melalui proxy API server dengan token ServiceAccount. Alert ke Alertmanager lalu Email, Slack, Teams.")
    d.rect(20, 40, 290, 360, "zone2", 12)
    d.text(36, 66, "Luar kluster", "th")
    d.text(294, 66, "docker compose", "ts m", "end")
    d.node(44, 92, 242, 52, "Prometheus", "scrape + alert rules", "acc")
    d.node(44, 196, 242, 44, "Alertmanager")
    d.path("M165,144 V194")
    for i, n in enumerate(["Email", "Slack", "Teams"]):
        d.node(44 + i * 84, 272, 74, 36, n, cls="okb", tcls="ts")
        d.path(f"M{81 + i * 84},240 V270")
    d.node(44, 334, 242, 46, "Grafana", "dashboard + alert Grafana")
    d.path("M44,357 H32 V118 H42")
    d.rect(370, 40, 510, 360, "zone", 12)
    d.text(386, 66, "Kluster k3d “lab”", "th")
    d.node(392, 92, 200, 52, "API server :6443", "token SA prometheus-external")
    d.node(652, 84, 208, 42, "kubelet / cAdvisor", "setiap node")
    d.node(652, 140, 208, 42, "pod demo-app", ":8080/metrics", mono_sub=True)
    d.path("M592,110 H650")
    d.path("M592,126 H620 V161 H650")
    d.text(621, 102, "proxy", "ts", "middle")
    d.node(392, 210, 200, 52, "kube-state-metrics", "NodePort 30081")
    d.node(392, 300, 200, 52, "node-exporter", "DaemonSet · hostNetwork :9100")
    d.path("M286,112 H390", acc=True)
    d.path("M286,124 H340 V236 H390", acc=True)
    d.path("M286,132 H328 V326 H390", acc=True)
    d.text(338, 104, "scrape", "ta", "middle")
    d.rect(652, 210, 208, 142, "box")
    d.text(668, 234, "RBAC least privilege", "th")
    for j, s in enumerate(["✓ get nodes/proxy", "✓ get pods/proxy", "✗ delete pods", "✗ get secrets"]):
        d.text(668, 260 + j * 22, s, "ts m")
    return d


def pilihan_b():
    d = D("pb", 900, 220, "Pilihan B: Prometheus Agent dan remote_write",
          "Prometheus Agent dalam kluster scrape exporter, simpan WAL, dan remote_write keluar ke Prometheus luar melalui firewall yang hanya membenarkan trafik keluar.")
    d.rect(560, 30, 320, 170, "zone2", 12)
    d.rect(20, 30, 420, 170, "zone", 12)
    d.text(36, 56, "Kluster", "th")
    d.node(40, 76, 170, 44, "Exporter", "ksm · node · cAdvisor")
    d.node(250, 76, 170, 100, "Prometheus Agent", "WAL bila rangkaian putus", "acc")
    d.path("M210,98 H248")
    d.add('<line x1="490" y1="20" x2="490" y2="210" class="arr dash"/>')
    d.text(484, 214, "firewall: keluar sahaja", "tw", "end")
    d.path("M420,126 H600", acc=True)
    d.text(510, 116, "remote_write", "ta m", "middle")
    d.text(576, 56, "Luar kluster", "th")
    d.node(602, 100, 120, 52, "Prometheus", "terima tulis")
    d.node(744, 100, 120, 52, "Grafana")
    d.path("M744,126 H724")
    return d


def penghalaan_alert():
    d = D("ra", 900, 190, "Penghalaan Alertmanager",
          "Semua alert ke email-pasukan; alert severity critical ke slack-oncall, teams-oncall dan email-pasukan.")
    d.node(20, 66, 160, 56, "Alert firing", "dari Prometheus")
    d.node(230, 66, 170, 56, "Alertmanager", "route tree", "acc")
    d.path("M180,94 H228")
    d.path("M400,84 H460 V44 H498")
    d.path("M400,104 H460 V140 H498", acc=True)
    d.text(452, 38, "semua alert", "ts m", "end")
    d.text(452, 150, 'severity="critical"', "ta m", "end")
    d.node(500, 22, 170, 44, "email-pasukan", cls="okb", tcls="t m")
    for i, n in enumerate(["slack-oncall", "teams-oncall", "email-pasukan"]):
        d.node(500 + i * 130, 118, 120, 44, n, cls="okb", tcls="ts m")
    return d


def pod(d, x, y, v, faded=False):
    cls = "acc" if v == "v2" else "box"
    d.add(f'<rect x="{x}" y="{y}" width="44" height="28" rx="6" class="{cls}"{" opacity=\".45\"" if faded else ""}/>')
    d.text(x + 22, y + 19, v, "ts m", "middle")


def strategi():
    d = D("st", 900, 350, "Strategi deployment",
          "Rolling update menggantikan pod v1 dengan v2 sedikit demi sedikit; blue-green menukar selector Service dari blue ke green sekali gus; "
          "canary menghantar kira-kira 20 peratus trafik ke satu pod v2.")
    cols = [(20, "Rolling update", "ganti sedikit demi sedikit"), (320, "Blue-green", "tukar selector sekali gus"),
            (620, "Canary", "sebahagian kecil trafik ke v2")]
    for x, t, s in cols:
        d.rect(x, 20, 260, 310, "zone", 12)
        d.text(x + 16, 46, t, "th")
        d.text(x + 16, 64, s, "ts")
    # rolling
    for r, row in enumerate([["v1"] * 4, ["v2", "v2", "v1", "v1"], ["v2"] * 4]):
        y = 100 + r * 62
        d.text(36, y - 8, f"langkah {r + 1}", "tl")
        for i, v in enumerate(row):
            pod(d, 36 + i * 54, y, v)
    d.text(36, 300, "maxSurge / maxUnavailable: 0", "ts m")
    d.text(36, 318, "rollback: kubectl rollout undo", "ts m")
    # blue-green
    d.node(400, 84, 100, 36, "Service", cls="box", tcls="ts")
    d.text(336, 172, "blue (live)", "tl")
    for i in range(4):
        pod(d, 336 + i * 54, 180, "v1")
    d.text(336, 248, "green (preview)", "tl")
    for i in range(4):
        pod(d, 336 + i * 54, 256, "v2")
    d.path("M430,120 V176", acc=True)
    d.path("M470,120 V140 H560 V240 H500 V254", dash=True)
    d.text(566, 136, "switch.sh", "ts m", "end")
    d.text(336, 318, "2× sumber · rollback dalam saat", "ts")
    # canary
    d.node(700, 84, 100, 36, "Service", cls="box", tcls="ts")
    d.text(636, 172, "stable · 4 pod", "tl")
    for i in range(4):
        pod(d, 636 + i * 54, 180, "v1")
    d.text(636, 248, "canary · 1 pod", "tl")
    pod(d, 636, 256, "v2")
    d.path("M730,120 V176")
    d.path("M770,120 V140 H860 V270 H682", acc=True)
    d.text(724, 146, "~80%", "ts m", "end")
    d.text(852, 210, "~20%", "ta m", "end")
    d.text(636, 318, "promosi: scale canary 1 → 2 → 4", "ts m")
    return d


def penamatan_pod():
    d = D("pt", 900, 290, "Kitaran hayat penamatan pod",
          "Bila pod dipadam, dua perkara berlaku serentak: pod dibuang dari EndpointSlice sementara preStop sleep 5 saat berjalan. "
          "Selepas itu SIGTERM dihantar, app menghabiskan request, dan SIGKILL hanya jika melebihi terminationGracePeriodSeconds.")
    x0 = 170
    d.add(f'<line x1="{x0}" y1="40" x2="{x0}" y2="250" class="arr"/>')
    d.text(x0, 30, "pod dipadam", "th", "middle")
    d.text(20, 104, "Rangkaian", "tl")
    d.text(20, 192, "Container", "tl")
    d.rect(x0 + 6, 80, 250, 40, "warn", 6)
    d.text(x0 + 18, 98, "Buang dari EndpointSlice", "ts")
    d.text(x0 + 18, 113, "kube-proxy kemas kini iptables", "ts")
    d.text(x0 + 262, 104, "ambil masa!", "tw")
    d.rect(x0 + 6, 168, 250, 40, "acc", 6)
    d.text(x0 + 18, 186, "preStop: sleep 5s", "ts m")
    d.text(x0 + 18, 201, "trafik lama masih mungkin tiba", "ts")
    d.rect(x0 + 262, 168, 250, 40, "box", 6)
    d.text(x0 + 274, 186, "SIGTERM → /readyz gagal", "ts m")
    d.text(x0 + 274, 201, "habiskan request (SHUTDOWN_DELAY)", "ts")
    gx = 830
    d.add(f'<line x1="{gx}" y1="150" x2="{gx}" y2="268" class="arr dash"/>')
    d.text(gx, 126, "SIGKILL", "th m", "middle")
    d.text(gx, 142, "jika masih hidup", "ts", "middle")
    d.path(f"M{x0 + 516},188 H{gx - 4}", dash=True)
    d.add(f'<path d="M{x0 + 4},262 H{gx - 4}" class="arr" marker-start="url(#pth)" marker-end="url(#pth)"/>')
    d.text((x0 + gx) / 2, 254, "terminationGracePeriodSeconds (dikira dari saat pod dipadam)", "ts m", "middle")
    d.text(x0 + 6, 152, "preStop memberi masa langkah rangkaian selesai sebelum app berhenti", "ta")
    return d


def log_shipping():
    d = D("lg", 900, 250, "Log shipping ke storan luar",
          "Fail log di setiap node dibaca oleh Fluent Bit DaemonSet, yang menambah metadata, membuang log /healthz, menimbal di disk, "
          "dan menghantar ke Loki untuk carian di Grafana serta ke S3 sebagai arkib .gz.")
    d.rect(20, 30, 470, 200, "zone", 12)
    d.text(36, 56, "Setiap node", "th")
    d.node(40, 92, 180, 60, "/var/log/containers", "*.log", tcls="ts m")
    d.rect(260, 72, 210, 120, "acc")
    d.text(276, 98, "Fluent Bit", "th")
    d.text(276, 116, "DaemonSet", "ts m")
    for j, s in enumerate(["+ metadata K8s", "− log /healthz", "penimbal disk"]):
        d.text(276, 140 + j * 18, s, "ts")
    d.path("M220,122 H258")
    d.rect(540, 30, 340, 200, "zone2", 12)
    d.text(556, 56, "Luar kluster", "th")
    d.node(570, 74, 140, 52, "Loki", "cari di Grafana")
    d.node(730, 74, 130, 52, "Grafana", "LogQL")
    d.path("M730,100 H712")
    d.node(570, 154, 290, 52, "S3 (SeaweedFS)", "arkib .gz: cluster=lab/YYYY/MM/DD/HH/…", mono_sub=False)
    d.path("M470,110 H568", acc=True)
    d.path("M470,170 H568", acc=True)
    return d


def diagnosis():
    d = D("dg", 900, 440, "Aliran diagnosis kegagalan pod",
          "Mulakan dengan kubectl get pods, kemudian ikut status: Pending, ImagePullBackOff, CreateContainerConfigError, "
          "CrashLoopBackOff, Running 0/1, atau Running 1/1 tetapi Service gagal.")
    rows = [("Pending", "describe pod → Events: FailedScheduling", "resource, nodeSelector, taint, PVC", "warn"),
            ("ImagePullBackOff", "describe pod → Events", "nama image/tag, registry, imagePullSecrets", "warn"),
            ("CreateContainerConfigError", "describe pod", "ConfigMap / Secret / key yang hilang", "warn"),
            ("CrashLoopBackOff", "logs --previous · describe → Last State", "exit 1 app · 137 SIGKILL (OOM/liveness) · 143 SIGTERM", "warn"),
            ("Running 0/1", "readinessProbe gagal", "describe → Events: Readiness probe failed", "box"),
            ("Running 1/1, Service gagal", "get endpointslices", "semak selector dan targetPort", "box")]
    d.node(20, 186, 200, 66, "kubectl get pods", "STATUS dan RESTARTS?", "acc", tcls="th m")
    d.add('<line x1="240" y1="54" x2="240" y2="384" class="arr"/>')
    d.path("M220,219 H240", head=False)
    for i, (st, a1, a2, cls) in enumerate(rows):
        y = 30 + i * 68
        d.path(f"M240,{y + 24} H268")
        d.node(270, y, 230, 48, st, cls=cls, tcls="ts m")
        d.path(f"M500,{y + 24} H518")
        d.rect(520, y, 370, 48, "box")
        d.text(534, y + 20, a1, "ts m")
        d.text(534, y + 38, a2, "ts")
    return d


def seni_bina_rancher():
    d = D("sr", 900, 400, "Seni bina Opsyen B cara 1: Rancher dalam kluster berasingan",
          "Dua kluster k3d pada laptop. Kluster rancher menjalankan Rancher di belakang Traefik pada port 443. "
          "Agent dalam kluster lab membuka tunnel keluar ke Rancher. Browser dan kubectl context lab melalui Rancher; "
          "context k3d-lab terus ke API server.")
    d.rect(8, 8, 884, 384, "zone2", 14)
    d.text(26, 34, "Laptop · Docker", "tl")
    d.rect(28, 50, 300, 240, "zone", 12)
    d.text(44, 76, "Kluster k3d “rancher”", "th")
    d.node(48, 92, 260, 48, "Traefik (ingress) :443", "rancher.<IP>.sslip.io", mono_sub=True)
    d.node(48, 160, 260, 52, "Rancher", "ns cattle-system", "acc")
    d.path("M178,140 V158")
    d.node(48, 232, 260, 40, "cert-manager", cls="box", tcls="t")
    d.rect(540, 50, 332, 240, "zone", 12)
    d.text(556, 76, "Kluster k3d “lab”", "th")
    d.node(560, 92, 292, 48, "API server :6443", "127.0.0.1:6550 dari laptop")
    d.node(560, 160, 292, 52, "cattle-cluster-agent", "ns cattle-system · fleet-agent", "acc")
    d.path("M706,160 V142")
    d.node(560, 232, 292, 40, "ns demo · monitoring · logging", cls="box", tcls="t")
    d.path("M558,186 H310", acc=True)
    d.text(434, 176, "tunnel wss (sambungan keluar)", "ta", "middle")
    d.node(48, 318, 260, 52, "Browser · kubectl --context lab", "melalui Rancher (RBAC, audit)", "warn")
    d.path("M48,344 H38 V116 H46")
    d.node(560, 318, 292, 52, "kubectl --context k3d-lab", "terus ke API server (admin)", "warn")
    d.path("M852,344 H864 V116 H854")
    return d


def seni_bina_rancher_sekali():
    d = D("ss", 900, 400, "Seni bina Opsyen B cara 2: Rancher sekali dengan kluster lab",
          "Satu kluster k3d lab. Rancher dipasang terus di dalamnya di belakang Traefik pada port 443, dan muncul dalam Rancher "
          "sebagai kluster local. Tiada tunnel: Rancher bercakap terus dengan API server kluster yang sama. Pod Rancher berkongsi "
          "worker dengan app demo. Browser dan kubectl context local melalui Rancher; context k3d-lab terus ke API server.")
    d.rect(8, 8, 884, 384, "zone2", 14)
    d.text(26, 34, "Laptop · Docker", "tl")
    d.rect(28, 50, 844, 240, "zone", 12)
    d.text(44, 76, "Kluster k3d “lab” (dalam Rancher: “local”)", "th")
    d.node(48, 92, 260, 48, "Traefik (ingress) :443", "rancher.<IP>.sslip.io", mono_sub=True)
    d.node(48, 160, 260, 52, "Rancher", "ns cattle-system", "acc")
    d.path("M178,140 V158")
    d.node(48, 232, 260, 40, "cert-manager · fleet", cls="box", tcls="t")
    d.node(560, 92, 292, 48, "API server :6443", "127.0.0.1:6550 dari laptop")
    d.node(560, 160, 292, 52, "ns demo · monitoring · logging", "semua modul", "box")
    d.node(560, 232, 292, 40, "worker agent-0 · agent-1 dikongsi", cls="warn", tcls="t")
    d.path("M308,186 H524 V116 H558", acc=True)
    d.text(416, 176, "terus (tiada tunnel)", "ta", "middle")
    d.path("M308,252 H558", dash=True, head=False)
    d.text(434, 244, "pod pada node yang sama", "ts", "middle")
    d.node(48, 318, 260, 52, "Browser · kubectl --context local", "melalui Rancher (RBAC, audit)", "warn")
    d.path("M48,344 H38 V116 H46")
    d.node(560, 318, 292, 52, "kubectl --context k3d-lab", "terus ke API server (admin)", "warn")
    d.path("M852,344 H864 V116 H854")
    return d


def keda_hpa():
    d = D("kd", 900, 400, "KEDA dibina di atas HPA",
          "keda-operator bertanya kepada Prometheus luar, mencipta HPA keda-hpa-demo-app dan melakukan langkah 0 ke 1. "
          "HPA membaca metrik External daripada keda-operator-metrics-apiserver dan menskala demo-app dari 1 ke N.")
    d.rect(20, 30, 190, 260, "zone2", 12)
    d.text(36, 56, "Luar kluster", "th")
    d.node(36, 82, 158, 56, "Prometheus", "Modul 3")
    d.rect(230, 30, 650, 260, "zone", 12)
    d.text(246, 56, "Kluster k3d “lab”", "th")
    d.node(250, 82, 200, 56, "keda-operator", "ns keda", "acc")
    d.node(250, 222, 200, 56, "metrics-apiserver", "ns keda · external.metrics", "box")
    d.node(520, 160, 140, 56, "HPA", "keda-hpa-demo-app", "box", mono_sub=True)
    d.node(720, 160, 140, 56, "Deployment", "demo-app", "okb")
    d.path("M250,110 H196", acc=True)
    d.text(223, 102, "PromQL", "ta", "middle")
    d.path("M450,120 H560 V158")
    d.text(505, 112, "cipta", "ts", "middle")
    d.path("M450,92 H790 V158", dash=True)
    d.text(620, 84, "scale 0 ↔ 1 (operator, setiap pollingInterval)", "ts", "middle")
    d.path("M660,188 H718", acc=True)
    d.text(689, 180, "1 ↔ N", "ta", "middle")
    d.path("M590,216 V250 H452")
    d.text(560, 268, "nilai s0-prometheus, setiap 15 s", "ts", "middle")
    d.path("M350,222 V140")
    d.rect(20, 306, 860, 80, "zone", 10)
    d.text(40, 332, "HPA biasa, metrik External, metricType AverageValue", "tl")
    d.text(40, 360, "desiredReplicas = ceil( nilai query / threshold )", "th m")
    d.text(860, 360, "19 RPS / 5 → 4 pod", "t", "end")
    return d


def aliran_data_grafana():
    d = D("ag", 900, 540, "Aliran data dari exporter ke panel Grafana",
          "Prometheus tarik /metrics daripada kube-state-metrics, node-exporter, cAdvisor dan demo-app setiap 15 saat dan simpan dalam TSDB. "
          "Grafana tahu alamat Prometheus daripada fail provisioning datasources/prometheus.yml (url http://prometheus:9090) "
          "dan memuat dashboard JSON melalui provisioning/dashboards/provider.yml. Panel menghantar PromQL ke /api/v1/query_range, "
          "Prometheus menjawab JSON, dan Grafana melukis graf dalam pelayar.")

    def badge(x, y, n):
        d.add(f'<circle cx="{x}" cy="{y}" r="9" class="solid"/>')
        d.text(x, y + 4, str(n), "tn", "middle")

    # Kluster: sumber metrik
    d.rect(16, 30, 170, 290, "zone", 12)
    d.text(30, 56, "Kluster k3d “lab”", "th")
    srcs = [("kube-state-metrics", "NodePort :30081"), ("node-exporter", ":9100"),
            ("cAdvisor", "melalui API server"), ("demo-app", "melalui API server")]
    for i, (n, sub) in enumerate(srcs):
        y = 72 + i * 60
        d.node(26, y, 150, 48, n, sub, mono_sub=sub.startswith(":") or sub.startswith("Node"))
        d.path(f"M176,{y + 24} H194 V151 H226", acc=True)
    badge(194, 186, 1)

    # docker compose: Prometheus dan Grafana
    d.rect(202, 30, 438, 290, "zone2", 12)
    d.text(218, 56, "docker compose", "th")
    d.text(626, 56, "rangkaian monitoring", "ts m", "end")
    d.rect(218, 72, 168, 240, "acc")
    d.text(302, 94, "Prometheus", "th", "middle")
    d.text(302, 112, "prometheus:9090", "ts m", "middle")
    d.node(228, 126, 148, 50, "Scrape (pull)", "ikut prometheus.yml")
    d.node(228, 188, 148, 50, "TSDB", "siri masa, 7 hari")
    d.node(228, 250, 148, 50, "HTTP API", "/api/v1/query_range", mono_sub=True)
    d.path("M302,176 V186")
    d.path("M302,238 V248")
    badge(376, 188, 2)

    d.rect(462, 72, 164, 240, "box")
    d.text(544, 94, "Grafana", "th", "middle")
    d.text(544, 112, "localhost:3000", "ts m", "middle")
    d.node(472, 126, 144, 50, "Data source", "uid: prometheus", "okb", mono_sub=True)
    d.node(472, 188, 144, 50, "Dashboard", "dari fail JSON", "okb")
    d.node(472, 250, 144, 50, "Panel", "query + paparan")
    d.path("M544,238 V248")

    # Grafana -> Prometheus (PromQL) dan jawapan (JSON)
    d.path("M472,151 H424 V275 H378", acc=True)
    d.text(448, 140, "PromQL", "ta", "middle")
    badge(448, 151, 4)
    d.path("M378,290 H470")
    d.text(424, 310, "JSON", "ts", "middle")
    badge(424, 290, 5)

    # Fail provisioning
    d.rect(652, 30, 232, 290, "zone", 12)
    d.text(666, 56, "Fail provisioning", "th")
    badge(866, 51, 3)
    d.rect(660, 72, 216, 118, "okb")
    for j, (s, c) in enumerate([("datasources/prometheus.yml", "ts m"), ("name: Prometheus", "ts m"),
                                ("uid: prometheus", "ts m"), ("url: http://prometheus:9090", "ta m"),
                                ("(nama servis compose)", "ts")]):
        d.text(670, 94 + j * 20, s, c)
    d.path("M660,151 H618")
    d.rect(660, 204, 216, 104, "okb")
    for j, (s, c) in enumerate([("dashboards/provider.yml", "ts m"), ("muat setiap *.json dari", "ts"),
                                ("grafana/dashboards/", "ts m"), ("bengkel-k8s-hpa.json", "ta m")]):
        d.text(670, 226 + j * 20, s, c)
    d.path("M660,226 H646 V213 H618")

    # Langkah
    d.rect(16, 354, 410, 170, "zone", 12)
    d.text(32, 378, "Langkah", "tl")
    steps = ["Prometheus tarik (pull) /metrics setiap 15 s",
             "Sampel disimpan sebagai siri masa dalam TSDB",
             "Semasa mula, Grafana baca fail provisioning",
             "Panel hantar PromQL ke /api/v1/query_range",
             "Prometheus jawab JSON: senarai [masa, nilai]",
             "Grafana lukis graf dalam pelayar"]
    for i, s in enumerate(steps):
        y = 402 + i * 20
        badge(38, y - 4, i + 1)
        d.text(56, y, s, "ts")

    # Pelayar
    d.path("M544,300 V352", acc=True)
    badge(544, 334, 6)
    d.rect(440, 354, 444, 170, "zone2", 12)
    d.text(456, 380, "Pelayar anda", "th")
    d.text(456, 400, "localhost:3000", "ts m")
    d.text(456, 432, "Refresh dashboard", "ts")
    d.text(456, 450, "setiap 10 s = ulang", "ts")
    d.text(456, 468, "langkah 4 hingga 6", "ts")
    d.rect(604, 368, 266, 142, "box")
    d.text(616, 388, "CPU pod vs requests & limits", "ts")
    for gy in (420, 450, 480):
        d.add(f'<line x1="616" y1="{gy}" x2="858" y2="{gy}" class="grid"/>')
    d.add('<line x1="616" y1="412" x2="858" y2="412" class="arr dash"/>')
    d.text(620, 406, "limits", "ts")
    d.add('<line x1="616" y1="466" x2="858" y2="466" class="arr dash"/>')
    d.text(620, 460, "requests", "ts")
    d.add('<polyline points="616,494 646,492 676,486 706,470 736,446 766,430 796,438 826,452 858,458" class="arra"/>')
    return d


ALL = {
    "seni-bina-makmal": seni_bina, "aliran-hpa": aliran_hpa, "kelewatan-hpa": kelewatan_hpa,
    "bentuk-ujian-beban": load_tests, "monitoring-luar-kluster": monitoring_luar, "pilihan-b-remote-write": pilihan_b,
    "penghalaan-alert": penghalaan_alert, "strategi-deployment": strategi, "penamatan-pod": penamatan_pod,
    "log-shipping": log_shipping, "aliran-diagnosis": diagnosis, "seni-bina-rancher": seni_bina_rancher,
    "seni-bina-rancher-sekali": seni_bina_rancher_sekali, "keda-di-atas-hpa": keda_hpa,
    "aliran-data-grafana": aliran_data_grafana,
}
