#!/usr/bin/env python3
"""
Valida SLOs definidos em SDD §8 contra o CSV de stats do Locust.
Exit code 0 = todos os SLOs atingidos.
Exit code 1 = uma ou mais violações.

Uso:
  python load-tests/check_slos.py load-tests/results/ingest_stats.csv
"""

import csv
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SloRule:
    p95_ms: float
    failure_pct: float


# SLOs formais por endpoint (SDD §8.1)
SLO_RULES: dict[str, SloRule] = {
    "POST /logs": SloRule(p95_ms=100.0, failure_pct=1.0),
    "GET /metrics/overview": SloRule(p95_ms=200.0, failure_pct=1.0),
    "GET /metrics/response-times": SloRule(p95_ms=200.0, failure_pct=1.0),
    "GET /health": SloRule(p95_ms=50.0, failure_pct=0.1),
    "POST /analyze": SloRule(p95_ms=30_000.0, failure_pct=5.0),
}

MIN_REQUESTS = 10  # ignora endpoints com amostra mínima insuficiente


def _float(value: str) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def check_csv(path: str) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    passing: list[str] = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            if name == "Aggregated" or name not in SLO_RULES:
                continue

            rule = SLO_RULES[name]
            request_count = int(_float(row.get("Request Count", "0")))
            if request_count < MIN_REQUESTS:
                continue

            failure_count = int(_float(row.get("Failure Count", "0")))
            failure_pct = (failure_count / request_count * 100) if request_count else 0.0
            p95 = _float(row.get("95%", "0"))

            if p95 > rule.p95_ms:
                violations.append(
                    f"  FAIL [{name}] P95={p95:.0f}ms > SLO {rule.p95_ms:.0f}ms"
                    f" ({request_count} reqs)"
                )
            else:
                passing.append(
                    f"  PASS [{name}] P95={p95:.0f}ms <= SLO {rule.p95_ms:.0f}ms"
                )

            if failure_pct > rule.failure_pct:
                violations.append(
                    f"  FAIL [{name}] failure={failure_pct:.1f}% > SLO {rule.failure_pct:.1f}%"
                    f" ({failure_count}/{request_count} reqs)"
                )
            else:
                passing.append(
                    f"  PASS [{name}] failure={failure_pct:.1f}% <= SLO {rule.failure_pct:.1f}%"
                )

    return violations, passing


def main() -> int:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "results/ingest_stats.csv"

    if not Path(csv_path).exists():
        print(f"ERROR: arquivo não encontrado: {csv_path}", file=sys.stderr)
        return 2

    violations, passing = check_csv(csv_path)

    for line in passing:
        print(line)

    if violations:
        print(f"\n[FAIL] {len(violations)} violacao(es) de SLO detectada(s):")
        for line in violations:
            print(line)
        return 1

    print(f"\n[PASS] Todos os SLOs atingidos ({len(passing)} verificacoes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
