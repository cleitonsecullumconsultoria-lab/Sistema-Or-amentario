from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB
from tmpl import templates

router = APIRouter(prefix="/receitas", tags=["receitas"])

MESES = [{"num": i, "nome": n} for i, n in enumerate(
    ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"], 1)]


def _fmt(v) -> str:
    try:
        return f"{float(v)/1000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


@router.get("/pos-venda")
async def pos_venda(request: Request, ano: int = 2024):
    db = DB()
    real_df = db.tabela("Realizado")
    filiais_df = db.tabela("Filiais")
    contas_df = db.tabela("PlanoContas")

    real = real_df[real_df["ano"] == ano]
    receita_contas = contas_df[contas_df["categoria"] == "receita"]["id"].tolist()
    custo_contas = contas_df[contas_df["categoria"] == "custo"]["id"].tolist()

    filiais_map = {r["id"]: r.to_dict() for _, r in filiais_df.iterrows()}
    receitas = []

    for fid, grupo in real.groupby("filial_id"):
        f = filiais_map.get(fid, {})
        rec = float(grupo[grupo["conta_id"].isin(receita_contas)]["valor"].sum())
        cus = float(grupo[grupo["conta_id"].isin(custo_contas)]["valor"].sum())
        lucro = rec - cus
        margem = round(lucro / rec * 100, 1) if rec != 0 else 0
        receitas.append({
            "filial_codigo": f.get("codigo", "?") if f else "?",
            "grupo": "Peças e Serviços",
            "rec_bruta_fmt": _fmt(rec),
            "rec_liq_fmt": _fmt(rec),
            "custos_fmt": _fmt(-cus),
            "lucro": lucro,
            "lucro_fmt": _fmt(lucro),
            "margem": margem,
        })
    receitas.sort(key=lambda x: x["filial_codigo"])

    return templates.TemplateResponse(request, "receitas/pos_venda.html", {
        "receitas": receitas,
        "ano": ano,
        "anos_disponiveis": [2024, 2023],
        "active_page": "pos_venda",
    })


@router.get("/comissoes")
async def comissoes(request: Request, ano: int = 2024):
    db = DB()
    real_df = db.tabela("Realizado")
    filiais_df = db.tabela("Filiais")
    contas_df = db.tabela("PlanoContas")

    comissao_contas = contas_df[contas_df["tipo"].str.lower().str.contains("comiss", na=False)]["id"].tolist()
    real = real_df[(real_df["ano"] == ano) & (real_df["conta_id"].isin(comissao_contas))]

    filiais_map = {r["id"]: r.to_dict() for _, r in filiais_df.iterrows()}
    contas_map = {r["id"]: r for _, r in contas_df.iterrows()}

    rows = []
    for (fid, cid), grp in real.groupby(["filial_id", "conta_id"]):
        f = filiais_map.get(fid, {})
        c = contas_map.get(cid, {})
        valores = {int(r["mes"]): f"{float(r['valor'])/1000:.1f}".replace(".", ",")
                   for _, r in grp.iterrows()}
        total = float(grp["valor"].sum())
        rows.append({
            "filial_codigo": f.get("codigo", "?") if f else "?",
            "tipo": c.get("nome", "?") if c else "?",
            "conta_codigo": c.get("codigo", "?") if c else "?",
            "valores": valores,
            "total_fmt": f"{total/1000:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."),
        })

    return templates.TemplateResponse(request, "receitas/comissoes.html", {
        "comissoes": rows,
        "meses": MESES,
        "ano": ano,
        "active_page": "comissoes",
    })
