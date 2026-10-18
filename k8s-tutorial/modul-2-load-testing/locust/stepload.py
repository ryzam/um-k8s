"""Step load: naik 20 user setiap 60 saat sehingga 120 user, kemudian berhenti.

Locust guna LoadTestShape secara automatik jika ia wujud dalam fail, sebab itu ia
diasingkan daripada locustfile.py. Berguna untuk lihat respons HPA pada setiap "anak tangga".
  locust -f stepload.py -H http://localhost:30080 --headless --csv hasil
"""
from locust import LoadTestShape

from locustfile import DemoUser  # noqa: F401  (Locust kesan user class yang di-import)


class StepLoad(LoadTestShape):
    """Naik 20 user setiap 60 saat sehingga 120 user, kemudian berhenti.

    Berguna untuk lihat setiap "anak tangga" beban dan respons HPA padanya.
    """
    step_users = 20
    step_time = 60
    max_users = 120

    def tick(self):
        t = self.get_run_time()
        step = int(t // self.step_time) + 1
        users = step * self.step_users
        if users > self.max_users:
            return None
        return users, self.step_users
