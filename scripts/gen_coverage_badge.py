#!/usr/bin/env python3
"""
gen_coverage_badge.py — gera docs/coverage.svg a partir do coverage.py.

Sem dependência de serviços externos (Codecov etc.): lê a porcentagem total de
cobertura do arquivo .coverage (via API do coverage) e escreve um badge SVG
estático no estilo shields.io. Regenere com `make coverage`.

Uso:
    coverage run -m pytest && python scripts/gen_coverage_badge.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "docs" / "coverage.svg"


def _cor(pct: float) -> str:
    """Cor no padrão shields.io conforme a faixa de cobertura."""
    if pct >= 90:
        return "#4c1"      # brightgreen
    if pct >= 80:
        return "#97ca00"   # green
    if pct >= 70:
        return "#a4a61d"   # yellowgreen
    if pct >= 60:
        return "#dfb317"   # yellow
    if pct >= 50:
        return "#fe7d37"   # orange
    return "#e05d44"       # red


def _svg(pct: int, cor: str) -> str:
    """Monta um badge SVG simples (rótulo 'coverage' + valor)."""
    valor = f"{pct}%"
    # Larguras aproximadas para o texto caber (em pixels).
    w_label, w_val = 62, 38
    largura = w_label + w_val
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="20" role="img" aria-label="coverage: {valor}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{largura}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{w_label}" height="20" fill="#555"/>
    <rect x="{w_label}" width="{w_val}" height="20" fill="{cor}"/>
    <rect width="{largura}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{w_label/2:.0f}" y="15" fill="#010101" fill-opacity=".3">coverage</text>
    <text x="{w_label/2:.0f}" y="14">coverage</text>
    <text x="{w_label + w_val/2:.0f}" y="15" fill="#010101" fill-opacity=".3">{valor}</text>
    <text x="{w_label + w_val/2:.0f}" y="14">{valor}</text>
  </g>
</svg>
"""


def main() -> int:
    try:
        from coverage import Coverage

        cov = Coverage(data_file=str(RAIZ / ".coverage"))
        cov.load()
        pct = round(cov.report(file=open("/dev/null", "w")))
    except Exception as exc:  # noqa: BLE001
        print(f"[erro] não foi possível ler a cobertura: {exc}", file=sys.stderr)
        return 1

    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(_svg(int(pct), _cor(pct)), encoding="utf-8")
    print(f"Badge gerado: {SAIDA} ({pct}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
