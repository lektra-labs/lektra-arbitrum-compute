from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class ExecutionUnitSnapshot:
    task_id: str
    execution_unit_id: str
    status: str
    artifact_urls: tuple[str, ...]


class BackendApiClient:
    """Tiny backend API client using stdlib only."""

    def __init__(self, *, base_url: str, bearer_token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/tasks", payload)

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/tasks/{task_id}")

    def get_execution_unit_snapshot(
        self, task_id: str, execution_unit_id: str
    ) -> ExecutionUnitSnapshot | None:
        task = self.get_task(task_id)
        units = task.get("execution_units") or []
        for unit in units:
            if str(unit.get("id")) != execution_unit_id:
                continue
            resources = unit.get("resources") or []
            urls = tuple(
                r.get("url")
                for r in resources
                if isinstance(r, dict) and isinstance(r.get("url"), str)
            )
            return ExecutionUnitSnapshot(
                task_id=task_id,
                execution_unit_id=execution_unit_id,
                status=str(unit.get("status") or ""),
                artifact_urls=urls,
            )
        return None

    def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = None
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except error.HTTPError as exc:
            msg = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"backend API error {exc.code} for {method} {path}: {msg}"
            ) from exc
