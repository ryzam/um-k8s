# Alternatif kepada initContainer pip (untuk Wi-Fi bengkel yang perlahan): bina sekali, import ke k3d.
#   docker build -t app-otel:1.0 .
#   k3d image import app-otel:1.0 -c lab
# Kemudian dalam ../k8s/02-app-otel.yaml: buang initContainers, tukar image kepada app-otel:1.0
# dan command kepada ["python", "-u", "/srv/app_otel.py"] (volume code dan deps boleh dibuang).
FROM python:3.12-slim
RUN pip install --no-cache-dir opentelemetry-sdk==1.45.1 opentelemetry-exporter-otlp-proto-http==1.45.1
COPY app_otel.py /srv/app_otel.py
CMD ["python", "-u", "/srv/app_otel.py"]
