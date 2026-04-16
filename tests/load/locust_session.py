from __future__ import annotations

from locust import HttpUser, between, task


class EnelSession(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def aggregation(self) -> None:
        self.client.get("/v1/aggregations/overview")
        self.client.get("/v1/aggregations/mis")

    @task(1)
    def version(self) -> None:
        self.client.get("/v1/dataset/version")
