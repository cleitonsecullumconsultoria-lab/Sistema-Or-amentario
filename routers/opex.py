from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB
from tmpl import templates

router = APIRouter(prefix="/opex", tags=["opex"])


def _fmt(v) -> str:
    try:
        return f"{float(v)/1000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


@router.get("/despesas")
async def despesas(request: Request, ano: int = 2024, filial_id: int | None = None):
    db = DB()
    real_df = db.tabela("Realizado")
    filiais_df = db.tabela("Filiais")
    contas_df = db.tabela("PlanoContas")

    filial_nome = "Grupo consolidado"
    if filial_id:
        f = filiais_df[filiais_df["id"] == filial_id]
        filial_nome = f.iloc[0]["nome"] if not f.empty else "Grupo"

    real = real_df[real_df["ano"] == ano]
    if filial_id:
        real = real[real["filial_id"] == filial_id]

    desp_contas = contas_df[contas_df["categoria"] == "despesa"]
    real_desp = real[real["conta_id"].isin(desp_contas["id"].tolist())]

    contas_map = {r["id"]: r for _, r in desp_contas.iterrows()}

    grupos_dict = {}
    for _, r in real_desp.iterrows():
        cid = r["conta_id"]
        c = contas_map.get(cid, {})
        tipo = c.get("tipo", "outros") if c else "outros"
        if tipo not in grupos_dict:
            grupos_dict[tipo] = {}
        key = (cid, c.get("nome", "?") if c else "?", c.get("codigo", "") if c else "")
        grupos_dict[tipo][key] = grupos_dict[tipo].get(key, 0) + float(r["valor"])

    grupos = []
    total_opex = 0
    for tipo, linhas in sorted(grupos_dict.items()):
        grupo_linhas = []
        for (cid, nome, cod), total in sorted(linhas.items(), key=lambda x: -x[1]):
            r_jan = float(real_desp[(real_desp["conta_id"] == cid) & (real_desp["mes"] == 1)]["valor"].sum()) / 1000
            r_fev = float(real_desp[(real_desp["conta_id"] == cid) & (real_desp["mes"] == 2)]["valor"].sum()) / 1000
            r_mar = float(real_desp[(real_desp["conta_id"] == cid) & (real_desp["mes"] == 3)]["valor"].sum()) / 1000
            grupo_linhas.append({
                "nome": nome, "codigo": cod,
                "jan": f"{r_jan:.1f}".replace(".", ","),
                "fev": f"{r_fev:.1f}".replace(".", ","),
                "mar": f"{r_mar:.1f}".replace(".", ","),
                "q1": f"{r_jan+r_fev+r_mar:.1f}".replace(".", ","),
                "total_fmt": _fmt(total),
                "pct_opex": 0,
            })
            total_opex += total
        grupos.append({"label": tipo.capitalize(), "linhas": grupo_linhas})

    # Calcula % OPEX
    for g in grupos:
        for l in g["linhas"]:
            raw = float(str(l["total_fmt"]).replace(".", "").replace(",", ".") or 0) * 1000
            l["pct_opex"] = round(raw / total_opex * 100, 1) if total_opex else 0

    real_rec = real_df[(real_df["ano"] == ano)]
    if filial_id:
        real_rec = real_rec[real_rec["filial_id"] == filial_id]
    rec_contas = contas_df[contas_df["categoria"] == "receita"]["id"].tolist()
    total_rec = float(real_rec[real_rec["conta_id"].isin(rec_contas)]["valor"].sum())

    kpis = {
        "total_fmt": _fmt(total_opex),
        "receitas_fmt": _fmt(total_rec),
        "pct_receita_fmt": f"{round(total_opex/total_rec*100,1)}%" if total_rec else "—",
    }

    return templates.TemplateResponse(request, "opex/despesas.html", {
        "grupos": grupos,
        "kpis": kpis,
        "filiais": filiais_df[filiais_df["ativo"] == 1].to_dict("records"),
        "filial_id": filial_id,
        "filial_nome": filial_nome,
        "ano": ano,
        "anos_disponiveis": [2024, 2023],
        "active_page": "opex",
    })


@router.get("/capex")
async def capex(request: Request, ano: int = 2026):
    db = DB()
    filiais_df = db.tabela("Filiais")
    return templates.TemplateResponse(request, "opex/capex.html", {
        "ano": ano,
        "filiais": filiais_df.to_dict("records"),
        "active_page": "capex",
    })
