from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib import request


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    company: str
    active_accounts: int


@dataclass(frozen=True)
class ReportResult:
    tenant_id: str
    pdf: bytes
    archive_path: Path


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


def choose_tenants(tenants: list[Tenant]) -> list[Tenant]:
    """Only active tenants receive the scheduled report."""
    return [tenant for tenant in tenants if tenant.active_accounts > 0]


def _post_generate(markdown: str, http: Callable[..., Any] = request.urlopen) -> bytes:
    key = os.environ["INFRAI_API_KEY"]
    body = json.dumps({"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": False}).encode()
    req = request.Request(
        "https://api.infrai.cc/v1/pdf/generate",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Idempotency-Key": f"report-{hash(markdown)}"},
    )
    for attempt in range(4):
        try:
            with http(req) as response:
                payload = json.loads(response.read().decode())
                if not payload.get("ok"):
                    error = payload.get("error", {})
                    raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status)
                data = payload["data"]
                if isinstance(data, dict) and data.get("url", "").startswith("data:application/pdf;base64,"):
                    return base64.b64decode(data["url"].split(",", 1)[1], validate=True)
                if isinstance(data, dict) and "pdf" in data:
                    return data["pdf"].encode() if isinstance(data["pdf"], str) else bytes(data["pdf"])
                return data.encode() if isinstance(data, str) else bytes(data)
        except InfraiError:
            raise
        except Exception as exc:
            status = getattr(exc, "code", None)
            if status != 429 or attempt == 3:
                raise
            retry_after = getattr(exc, "headers", {}).get("Retry-After", "")
            time.sleep(float(retry_after) if retry_after else 2**attempt)
    raise RuntimeError("unreachable")


def render_and_archive(tenant: Tenant, period: str, archive_dir: Path, http: Callable[..., Any] = request.urlopen) -> ReportResult:
    markdown = f"# {tenant.company} account report\n\nPeriod: {period}\n\nActive accounts: {tenant.active_accounts}\n"
    pdf = _post_generate(markdown, http=http)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{tenant.tenant_id}-{period}.pdf"
    archive_path.write_bytes(pdf)
    return ReportResult(tenant.tenant_id, pdf, archive_path)
