"""Locust: alternatif k6 dengan UI web dan skrip Python.

UI:        locust -f locustfile.py -H http://localhost:30080      (buka http://localhost:8089)
Headless:  locust -f locustfile.py -H http://localhost:30080 --headless -u 50 -r 5 -t 5m --csv hasil

Step load automatik (shape dalam fail berasingan):
           locust -f stepload.py -H http://localhost:30080 --headless --csv hasil
"""
from locust import HttpUser, between, task


class DemoUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(8)
    def cpu(self):
        # name= kumpulkan statistik bawah satu label walaupun query string berbeza
        with self.client.get("/cpu?ms=50", name="/cpu", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"status {r.status_code}")

    @task(2)
    def home(self):
        self.client.get("/")

