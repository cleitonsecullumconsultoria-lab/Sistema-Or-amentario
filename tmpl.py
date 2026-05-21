"""Instância compartilhada de Jinja2Templates com filtros ROV."""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def _fmt_moeda(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "-"


def _fmt_pct(v) -> str:
    try:
        return f"{float(v):.1f}%"
    except (TypeError, ValueError):
        return "-"


def _var_cls(v) -> str:
    """Classe CSS para variação: positivo=verde, negativo=vermelho."""
    try:
        return "var-pos" if float(v) >= 0 else "var-neg"
    except (TypeError, ValueError):
        return ""


templates.env.filters["fmt_moeda"] = _fmt_moeda
templates.env.filters["fmt_pct"] = _fmt_pct
templates.env.filters["var_cls"] = _var_cls
