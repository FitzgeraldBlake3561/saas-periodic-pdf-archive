from pathlib import Path

from report_service import Tenant, choose_tenants, render_and_archive


def main() -> None:
    tenants = [Tenant("acme", "Acme Systems", 42), Tenant("quiet", "Quiet Labs", 0)]
    period = "2026-09"
    for tenant in choose_tenants(tenants):
        result = render_and_archive(tenant, period, Path("archive"))
        print(f"archived {result.archive_path}")


if __name__ == "__main__":
    main()
