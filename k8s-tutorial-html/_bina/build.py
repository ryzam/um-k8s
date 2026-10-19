# Bina laman HTML interaktif daripada ../../k8s-tutorial (relatif kepada skrip ini; sumber tidak diubah).
import html, os, re, sys, textwrap
INDENTED = []
import markdown
sys.path.insert(0, os.path.dirname(__file__))
import svgs

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # folder yang mengandungi k8s-tutorial/ dan k8s-tutorial-html/
SRC = os.environ.get("BENGKEL_SRC", os.path.join(ROOT, "k8s-tutorial"))  # BENGKEL_SRC: bina daripada salinan lain (cth: versi peserta)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "k8s-tutorial-html")
HERE = os.path.dirname(__file__)

MODULES = [  # (id, dir, nav label, eyebrow)
    ("gambaran", "", "Gambaran bengkel", "Mula di sini"),
    ("persediaan", "00-persediaan", "Persediaan · Pasang alat", "Sebelum Hari 1 · semua peserta"),
    ("opsyen-a", "00-persediaan/opsyen-a", "Persediaan · Opsyen A: k3d", "Sebelum Hari 1 · pilih satu opsyen"),
    ("rancher", "00-persediaan/rancher", "Persediaan · Opsyen B: Rancher", "Sebelum Hari 1 · pilih satu opsyen"),
    ("m1", "modul-1-hpa", "Modul 1 · HPA", "Hari 1 · 9:00 pagi – 1:00 petang"),
    ("m2", "modul-2-load-testing", "Modul 2 · Load testing", "Hari 1 · 2:00 – 5:00 petang"),
    ("m3", "modul-3-monitoring", "Modul 3 · Monitoring", "Hari 2 · 9:00 pagi – 1:00 petang"),
    ("m4", "modul-4-operations", "Modul 4 · Day-2 Ops", "Hari 2 · 2:00 – 5:00 petang"),
    ("m5", "modul-5-opentelemetry", "Modul 5 · OpenTelemetry (pilihan)", "Pilihan · di luar jadual 2 hari"),
    ("m6", "modul-6-keda", "Modul 6 · KEDA (pilihan)", "Pilihan · di luar jadual 2 hari"),
]
DIR2ID = {d: i for i, d, _, _ in MODULES}

CAPTIONS = {
    "seni-bina-makmal": "Kluster k3d berjalan dalam Docker pada laptop; stack monitoring dan storan log berjalan di luar kluster.",
    "seni-bina-rancher": "Opsyen B cara 1 (berasingan): Rancher tidak perlu mencapai kluster lab; agent membuka tunnel keluar ke Rancher.",
    "seni-bina-rancher-sekali": "Opsyen B cara 2 (sekali): Rancher dalam kluster lab sendiri, berkongsi worker dengan app demo.",
    "aliran-hpa": "HPA membaca metrik daripada Metrics Server setiap 15 saat dan mengira bilangan replicas.",
    "kelewatan-hpa": "Nilai tipikal; pull image tanpa cache boleh memanjangkan langkah ketiga hingga 30 saat.",
    "bentuk-ujian-beban": "Bentuk beban sebenar daripada stages dalam skrip k6 (Smoke, Load dan Stress dalam VU; Spike dalam RPS).",
    "monitoring-luar-kluster": "Pilihan A: Prometheus luar scrape terus. Akses ke cAdvisor dan pod melalui proxy API server, dikawal RBAC.",
    "pilihan-b-remote-write": "Pilihan B: bila kluster hanya boleh membuat sambungan keluar.",
    "penghalaan-alert": "Laluan Alertmanager dalam alertmanager.yml. Uji dengan amtool config routes test.",
    "strategi-deployment": "Tiga strategi yang dipraktikkan dalam Modul 4. Biru = v2.",
    "penamatan-pod": "Tanpa preStop, app boleh berhenti sebelum kube-proxy berhenti menghantar trafik kepadanya.",
    "log-shipping": "Fluent Bit menghantar ke dua destinasi: Loki untuk carian, S3 untuk arkib jangka panjang.",
    "aliran-diagnosis": "Mulakan dengan STATUS pod, kemudian ikut cabang ke bukti yang betul.",
    "aliran-data-grafana": "Grafana tidak scrape apa-apa: Prometheus simpan data, Grafana tahu alamatnya daripada fail provisioning dan hanya menghantar PromQL.",
    "keda-di-atas-hpa": "KEDA tidak menggantikan HPA: operator mencipta HPA dan melakukan 0 ↔ 1, HPA biasa melakukan 1 ↔ N.",
}

# Blok ASCII yang digantikan oleh SVG: penanda teks -> nama diagram
ASCII = [("Laptop peserta", "seni-bina-makmal"), ("HPA controller", "aliran-hpa"),
         ("metric-resolution", "kelewatan-hpa"), ("API server :6443", "monitoring-luar-kluster"),
         ("severity=\"critical\"  ─▶", "penghalaan-alert"), ("kubectl / rollout memadam pod", "penamatan-pod"),
         ("/var/log/containers/*.log", "log-shipping"), ('Kluster k3d "rancher"', "seni-bina-rancher"), ("Rancher di dalam", "seni-bina-rancher-sekali"), ("kubectl get pods            ─▶", "aliran-diagnosis"), ("cipta/urus", "keda-di-atas-hpa"), ("GET /api/v1/query_range", "aliran-data-grafana")]
# Diagram tambahan disuntik sebelum tajuk tertentu: (modul, tajuk, sisipan)
INJECT = [("m2", "### Model beban", '<div data-fig="bentuk-ujian-beban"></div>'),
          ("m3", "| | Pilihan A: scrape dari luar", '<div data-fig="pilihan-b-remote-write"></div>'),
          ("m4", "### Kitaran hayat", '<div data-fig="strategi-deployment"></div>'),
          ("m1", "---\n\n## Makmal 1.1", '<div data-widget="hpa"></div>'),
          ("m2", "---\n\n## Persediaan terminal", '<div data-widget="kapasiti"></div>')]


def slug(s):
    s = re.sub(r"<[^>]+>", "", html.unescape(s)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def file_id(path):
    return "f-" + slug(path)


def prep_md(mid, text):
    def fence(m):
        body = m.group(2)
        for mark, name in ASCII:
            if mark in body and ("─" in body or "│" in body or "+" in body):
                return f'\n<div data-fig="{name}"></div>\n'
        return m.group(0)
    text = re.sub(r"^```(\w*)\n(.*?)^```", fence, text, flags=re.S | re.M)
    for m, head, ins in INJECT:
        if m == mid:
            assert head in text, (mid, head)
            text = text.replace(head, ins + "\n\n" + head, 1)
    text = text.replace("<details>", '<details markdown="1">')

    # fence berinden dalam senarai: Python-Markdown tidak menyokongnya, jadi simpan dan sisip semula
    def indented(m):
        INDENTED.append((m.group(2), textwrap.dedent(m.group(3))))
        return f"{m.group(1)}CODEBLOCK{len(INDENTED) - 1}X"
    text = re.sub(r"^( +)```(\w*)\n(.*?)^ +```", indented, text, flags=re.S | re.M)
    return text


def fig_html(name):
    d = svgs.ALL[name]()
    return (f'<figure class="fig" id="fig-{name}"><div class="fig-scroll">{d.svg(False)}</div>'
            f'<figcaption><span>{html.escape(CAPTIONS[name])}</span>'
            f'<a class="svg-link" href="svg/{name}.svg">SVG</a></figcaption></figure>')


WIDGETS = {
    "hpa": """<section class="widget" aria-labelledby="w-hpa-t"><h4 id="w-hpa-t">Kalkulator HPA</h4>
<p class="wnote">Cuba formula <code>desiredReplicas</code> dengan nilai anda sendiri. Termasuk toleransi 10% dan had min/max.</p>
<div class="wgrid">
<label>currentReplicas<input id="h-cur" type="number" min="1" value="2"></label>
<label>Purata utilization (%)<input id="h-util" type="number" min="0" value="150"></label>
<label>Sasaran (%)<input id="h-tgt" type="number" min="1" value="50"></label>
<label>minReplicas<input id="h-min" type="number" min="1" value="1"></label>
<label>maxReplicas<input id="h-max" type="number" min="1" value="10"></label>
</div><output id="h-out" class="wout" for="h-cur h-util h-tgt h-min h-max"></output></section>""",
    "kapasiti": """<section class="widget" aria-labelledby="w-cap-t"><h4 id="w-cap-t">Anggaran kapasiti</h4>
<p class="wnote">Kapasiti satu pod ≈ <code>limits.cpu</code> ÷ masa CPU setiap request. Laraskan untuk laptop anda.</p>
<div class="wgrid">
<label>CPU setiap request, ms (<code>/cpu?ms=N</code>)<input id="c-ms" type="number" min="1" value="100"></label>
<label>limits.cpu (millicore)<input id="c-lim" type="number" min="1" value="500"></label>
<label>maxReplicas<input id="c-max" type="number" min="1" value="10"></label>
</div><output id="c-out" class="wout" for="c-ms c-lim c-max"></output></section>""",
}


def rewrite_links(mid, mdir, h):
    def fix(m):
        href = m.group(1)
        if re.match(r"https?://", href):
            return f'href="{href}" target="_blank" rel="noopener"'
        if href.startswith("#"):
            return f'href="#{mid}-{href[1:]}"'
        href, _, frag = href.partition("#")
        p = os.path.normpath(os.path.join(mdir, href)) if mdir else os.path.normpath(href)
        if p.endswith("README.md"):
            tid = DIR2ID.get(os.path.dirname(p), "gambaran")
            return f'href="#{tid}-{frag}"' if frag else f'href="#{tid}"'
        return f'href="#{file_id(p)}"'
    return re.sub(r'href="([^"]+)"', fix, h)


def code_block(lang, body, escaped=False):
    if not escaped:
        body = html.escape(body.rstrip("\n") + "\n", quote=False)
    label = {"bash": "terminal", "": "teks"}.get(lang, lang)
    cls = f' class="language-{lang}"' if lang in ("bash", "yaml", "python", "javascript", "json") else ' class="nohighlight"'
    return (f'<div class="code"><div class="code-bar"><span>{label}</span>'
            f'<button type="button" class="copy">Salin</button></div><pre><code{cls}>{body}</code></pre></div>')


def post(mid, mdir, h, sec):
    h = rewrite_links(mid, mdir, h)
    # tajuk: id unik + toggle selesai pada makmal
    def head(m):
        lvl, inner = m.group(1), m.group(2)
        hid = f"{mid}-{slug(inner)}"
        if lvl in ("2", "3"):
            sec.append((hid, re.sub(r"<[^>]+>", "", inner), lvl))
        extra = ""
        if lvl == "2" and inner.startswith("Makmal"):
            extra = (f'<label class="done-toggle"><input type="checkbox" data-k="{hid}" data-m="{mid}">'
                     f'<span>Selesai</span></label>')
        return f'<h{lvl} id="{hid}"><a class="hl" href="#{hid}">{inner}</a>{extra}</h{lvl}>'
    h = re.sub(r"<h([1-4])>(.*?)</h\1>", head, h)
    # senarai semak
    n = [0]

    def chk(m):
        n[0] += 1
        return (f'<li class="task"><label><input type="checkbox" data-k="{mid}-semak-{n[0]}" data-m="{mid}">'
                f'<span>{m.group(1)}</span></label></li>')
    h = re.sub(r"<li>\[ \] (.*?)</li>", chk, h, flags=re.S)

    # blok kod
    def code(m):
        return code_block(m.group(1) or "", m.group(2), escaped=True)
    h = re.sub(r'<pre><code(?: class="language-(\w+)")?>(.*?)</code></pre>', code, h, flags=re.S)
    h = re.sub(r"(?:<p>)?CODEBLOCK(\d+)X(?:</p>)?", lambda m: code_block(*INDENTED[int(m.group(1))]), h)
    h = re.sub(r"<table>", '<div class="tbl"><table>', h).replace("</table>", "</table></div>")
    h = re.sub(r'<div data-fig="([\w-]+)"></div>', lambda m: fig_html(m.group(1)), h)
    h = re.sub(r'<div data-widget="(\w+)"></div>', lambda m: WIDGETS[m.group(1)], h)
    return h


LANG = {".yaml": "yaml", ".yml": "yaml", ".py": "python", ".js": "javascript", ".json": "json", ".sh": "bash"}


def files_html(mid, mdir):
    root = os.path.join(SRC, mdir)
    items = []
    for dp, dn, fn in os.walk(root):
        dn.sort()
        if dp != root and (os.path.basename(dp).startswith("modul-") or os.path.relpath(dp, SRC) in DIR2ID):
            dn[:] = []
            continue
        for f in sorted(fn):
            rel = os.path.relpath(os.path.join(dp, f), SRC)
            if f == "README.md" or (mdir == "" ):
                continue
            items.append(rel)
    if not items:
        return ""
    out = [f'<section class="files" id="{mid}-fail"><h2><a class="hl" href="#{mid}-fail">Fail modul</a></h2>'
           f'<p class="wnote">Semua manifest dan skrip untuk modul ini. Klik untuk buka, kemudian salin.</p>']
    for rel in items:
        txt = open(os.path.join(SRC, rel), encoding="utf-8").read()
        ext = os.path.splitext(rel)[1]
        lang = LANG.get(ext, "")
        cls = f"language-{lang}" if lang else "nohighlight"
        size = len(txt.encode())
        sz = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"
        short = os.path.relpath(rel, mdir)
        out.append(f'<details class="file" id="{file_id(rel)}"><summary><span class="fname">{html.escape(short)}</span>'
                   f'<span class="fsize">{sz}</span></summary><div class="code"><div class="code-bar"><span>{lang or "teks"}</span>'
                   f'<button type="button" class="copy">Salin</button></div><pre><code class="{cls}">{html.escape(txt)}</code></pre></div></details>')
    out.append("</section>")
    return "\n".join(out)


def build():
    os.makedirs(os.path.join(OUT, "svg"), exist_ok=True)
    for name, fn in svgs.ALL.items():
        with open(os.path.join(OUT, "svg", f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(fn().svg(True))
    sections, nav = [], []
    for mid, mdir, label, eyebrow in MODULES:
        text = open(os.path.join(SRC, mdir, "README.md"), encoding="utf-8").read()
        md = markdown.Markdown(extensions=["fenced_code", "tables", "md_in_html"])
        h = md.convert(prep_md(mid, text))
        sec = []
        h = post(mid, mdir, h, sec)
        # h1 menjadi tajuk bahagian
        h = re.sub(r'<h1 id="[^"]+"><a class="hl" href="#[^"]+">(.*?)</a></h1>',
                   lambda m: f'<header class="mod-head"><p class="eyebrow">{eyebrow}</p><h1>{m.group(1)}</h1>'
                             f'<div class="mod-prog" data-m="{mid}"><span class="bar"><i></i></span><span class="lbl"></span></div></header>',
                   h, count=1)
        fh = files_html(mid, mdir) if mdir else ""
        if fh:
            sec.append((f"{mid}-fail", "Fail modul", "2"))
        sections.append(f'<section class="module" id="{mid}" data-m="{mid}">{h}{fh}</section>')
        # teks tajuk sudah di-escape oleh markdown; unescape dahulu supaya tidak jadi &amp;amp;
        sub = "".join(f'<li class="l{lv}"><a href="#{i}">{html.escape(html.unescape(t))}</a></li>' for i, t, lv in sec)
        nav.append(f'<li class="nav-mod" data-m="{mid}"><div class="nav-row"><a class="nav-top" href="#{mid}"><span>{label}</span>'
                   f'<span class="nav-count" data-m="{mid}"></span></a>'
                   f'<button type="button" class="nav-exp" aria-expanded="false" aria-label="Tunjuk sub-bahagian {html.escape(label)}">'
                   f'<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>'
                   f'</button></div><ul>{sub}</ul></li>')
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    page = (tpl.replace("{{SVG_RULES}}", svgs.SVG_RULES)
               .replace("{{LIGHT}}", svgs.tokens(svgs.LIGHT)).replace("{{DARK}}", svgs.tokens(svgs.DARK))
               .replace("{{NAV}}", "\n".join(nav)).replace("{{CONTENT}}", "\n".join(sections)))
    full = ('<!doctype html>\n<html lang="ms">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + page.replace("<div class=\"layout\">", "</head>\n<body>\n<div class=\"layout\">", 1) + "\n</body>\n</html>\n")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(full)
    with open(os.path.join(HERE, "artifact.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("ok", len(page))


build()
