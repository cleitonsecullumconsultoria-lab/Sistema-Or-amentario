"""ROV — Sistema Orçamentário (FastAPI)."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

sys.path.insert(0, str(Path(__file__).parent))
from db import DB
from tmpl import templates
from routers import cadastros, budget, receitas, headcount, opex, analise

app = FastAPI(title="ROV — Sistema Orçamentário")

app.include_router(cadastros.router)
app.include_router(budget.router)
app.include_router(receitas.router)
app.include_router(headcount.router)
app.include_router(opex.router)
app.include_router(analise.router)


@app.get("/")
async def dashboard(request: Request):
    db = DB()
    try:
        filiais_df = db.tabela("Filiais")
        contas_df = db.tabela("PlanoContas")
        ccus_df = db.tabela("CentrosCusto")
        versoes_df = db.tabela("BudgetVersoes")
        bud_df = db.tabela("BudgetLinhas")
        real_df = db.tabela("Realizado")

        stats = {
            "filiais_ativas": int((filiais_df["ativo"] == 1).sum()),
            "total_contas": len(contas_df),
            "total_ccus": len(ccus_df),
            "versoes_budget": len(versoes_df),
            "linhas_budget": len(bud_df),
            "linhas_realizado": len(real_df),
        }
        versoes = versoes_df.to_dict("records")
    except Exception:
        stats = {k: 0 for k in ["filiais_ativas", "total_contas", "total_ccus",
                                  "versoes_budget", "linhas_budget", "linhas_realizado"]}
        versoes = []

    return templates.TemplateResponse(request, "dashboard.html", {
        "stats": stats,
        "versoes": versoes,
        "active_page": "dashboard",
    })


@app.get("/cadastros")
async def cadastros_redirect():
    return RedirectResponse("/cadastros/filiais", status_code=302)
