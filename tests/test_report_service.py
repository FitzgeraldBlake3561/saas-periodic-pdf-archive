import base64
import json
from pathlib import Path

from src.report_service import Tenant, choose_tenants, render_and_archive


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"ok": True, "data": {"pdf_id": "pdf_test", "url": "data:application/pdf;base64," + base64.b64encode(b"%PDF-test").decode(), "retention_days": 7}}).encode()


def test_only_active_tenants_are_rendered(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("INFRAI_API_KEY", "test-key")
    tenants = [Tenant("live", "Live Co", 1), Tenant("empty", "Empty Co", 0)]
    assert [t.tenant_id for t in choose_tenants(tenants)] == ["live"]
    result = render_and_archive(tenants[0], "2026-09", tmp_path, http=lambda req: FakeResponse())
    assert result.archive_path.read_bytes() == b"%PDF-test"
