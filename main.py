"""ROV Sistema Orçamentário — FastAPI web app."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import sys
sys.path.insert(0, str(Path(__file__).parent))
from db import DB

app = FastAPI(title="ROV Sistema Orçamentário")
templates = Jinja2Templates(directory="templates")
def _today() -> str:
    return date.today().strftime("%d/%m/%Y")

MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

# ── Jinja2 filters ────────────────────────────────────────────────────────────

def _fmt_real(v: float) -> str:
    try:
        v = float(v)
        s = "−" if v < 0 else ""
        return s + "R$ " + f"{abs(v):,.0f}".replace(",", ".")
    except Exception:
        return "—"


def _fmt_m(v: float) -> str:
    try:
        v = float(v)
        s = "−" if v < 0 else ""
        a = abs(v)
        if a >= 1e9: return f"{s}R$ {a/1e9:.2f}B"
        if a >= 1e6: return f"{s}R$ {a/1e6:.1f}M"
        if a >= 1e3: return f"{s}R$ {a/1e3:.0f}k"
        return f"{s}R$ {a:.0f}"
    except Exception:
        return "—"


def _fmt_pct(v: float) -> str:
    try:
        v = float(v)
        arrow = "▲" if v > 0.05 else "▼" if v < -0.05 else "≈"
        return f"{arrow} {abs(v):.2f}%".replace(".", ",")
    except Exception:
        return "—"


def _var_cls(v: float) -> str:
    try:
        v = float(v)
        return "pos" if v > 0.1 else "neg" if v < -0.5 else "neu"
    except Exception:
        return ""


templates.env.filters.update({
    "fmt_real": _fmt_real,
    "fmt_m":    _fmt_m,
    "fmt_pct":  _fmt_pct,
    "var_cls":  _var_cls,
})

# ── Data helpers ─────────────────────────────────────────────────────────────

def _db() -> DB:
    return DB()


def _lookup(db: DB) -> tuple:
    filiais = db.tabela("Filiais").set_index("id")
    contas  = db.tabela("PlanoContas").set_index("id")
    versoes = db.tabela("BudgetVersoes").set_index("id")
    ccus    = db.tabela("CentrosCusto").set_index("id")
    return filiais, contas, versoes, ccus


def _receita_ids(contas: pd.DataFrame) -> set:
    return set(contas[contas["categoria"] == "receita"].index.tolist())


def _custo_ids(contas: pd.DataFrame) -> set:
    return set(contas[contas["categoria"] == "custo"].index.tolist())


def _latest_approved(versoes: pd.DataFrame, ano: int | None = None) -> int:
    df = versoes[versoes["status"] == "aprovado"]
    if ano:
        match = df[df["ano"] == ano]
        if not match.empty:
            return int(match.index.min())
    return int(df.index.max()) if not df.empty else int(versoes.index.max())


def _versoes_lista(versoes: pd.DataFrame) -> list[dict]:
    return [
        {"id": int(i), "label": f"{row['ano']} — {row['cenario']} ({row['status']})"}
        for i, row in versoes.sort_values("id").iterrows()
    ]


def _bvr_por_filial(
    bud: pd.DataFrame,
    real: pd.DataFrame,
    filiais: pd.DataFrame,
    contas: pd.DataFrame,
) -> list[dict]:
    """Budget vs Realizado agregado por filial (receita + custo)."""
    rec = _receita_ids(contas)
    cst = _custo_ids(contas)

    bud_r  = bud[bud["conta_id"].isin(rec)].groupby("filial_id")["valor"].sum()
    bud_c  = bud[bud["conta_id"].isin(cst)].groupby("filial_id")["valor"].sum()
    real_r = real[real["conta_id"].isin(rec)].groupby("filial_id")["valor"].sum()
    real_c = real[real["conta_id"].isin(cst)].groupby("filial_id")["valor"].sum()

    rows = []
    for fid in sorted(filiais.index):
        b  = float(bud_r.get(int(fid), 0))
        r  = float(real_r.get(int(fid), 0))
        bc = float(bud_c.get(int(fid), 0))
        rc = float(real_c.get(int(fid), 0))
        var    = r - b
        var_pct = (var / b * 100) if b else 0.0
        mg      = ((r - rc) / r * 100) if r else 0.0
        rows.append({
            "filial_id":     int(fid),
            "filial_codigo": filiais.loc[fid, "codigo"],
            "filial_nome":   filiais.loc[fid, "nome"],
            "budget":        b,
            "real":          r,
            "var_rs":        var,
            "var_pct":       round(var_pct, 2),
            "margem":        round(mg, 2),
        })
    return rows


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = _db()
    filiais, contas, versoes, ccus = _lookup(db)

    bud  = db.tabela("BudgetLinhas")
    bud  = bud[bud["versao_id"] == _latest_approved(versoes, ano=2024)]
    real = db.tabela("Realizado")
    real = real[real["ano"] == 2024]

    tabela = _bvr_por_filial(bud, real, filiais, contas)

    tot_b   = sum(r["budget"] for r in tabela)
    tot_r   = sum(r["real"]   for r in tabela)
    tot_var = (tot_r - tot_b) / tot_b * 100 if tot_b else 0.0
    tot_mg  = sum(r["margem"] for r in tabela) / len(tabela) if tabela else 0.0
    best    = max(tabela, key=lambda x: x["var_pct"]) if tabela else {}
    worst   = min(tabela, key=lambda x: x["var_pct"]) if tabela else {}

    rec_ids  = _receita_ids(contas)
    bud_mes  = bud[bud["conta_id"].isin(rec_ids)].groupby("mes")["valor"].sum()
    real_mes = real[real["conta_id"].isin(rec_ids)].groupby("mes")["valor"].sum()

    return templates.TemplateResponse(request, "index.html", {
        "today":           _today(),
        "periodo":        "Budget 2024 · Jan – Dez",
        "kpis": {
            "tot_budget":   tot_b,
            "tot_real":     tot_r,
            "tot_var_pct":  round(tot_var, 2),
            "margem":       round(tot_mg, 2),
            "best_filial":  best.get("filial_codigo", "—"),
            "best_var":     best.get("var_pct", 0),
            "worst_filial": worst.get("filial_codigo", "—"),
            "worst_var":    worst.get("var_pct", 0),
        },
        "tabela":          tabela,
        "chart_labels":    json.dumps([r["filial_codigo"] for r in tabela]),
        "chart_budget":    json.dumps([round(r["budget"]) for r in tabela]),
        "chart_real":      json.dumps([round(r["real"])   for r in tabela]),
        "chart_meses":     json.dumps(MESES),
        "chart_bud_mes":   json.dumps([round(float(bud_mes.get(m, 0)))  for m in range(1, 13)]),
        "chart_real_mes":  json.dumps([round(float(real_mes.get(m, 0))) for m in range(1, 13)]),
    })


@app.get("/budget", response_class=HTMLResponse)
async def budget_view(
    request: Request,
    versao_id: Optional[int] = Query(default=None),
):
    db = _db()
    filiais, contas, versoes, ccus = _lookup(db)

    if versao_id is None:
        versao_id = _latest_approved(versoes)

    versao_info = versoes.loc[versao_id] if versao_id in versoes.index else versoes.iloc[-1]

    bud     = db.tabela("BudgetLinhas")
    bud     = bud[bud["versao_id"] == versao_id]
    rec_ids = _receita_ids(contas)
    bud_rec = bud[bud["conta_id"].isin(rec_ids)]

    grp = bud_rec.groupby(["filial_id", "mes"])["valor"].sum()

    pivot: dict[int, dict] = {}
    for fid in sorted(filiais.index):
        meses_vals = {int(m): float(v) for (f, m), v in grp.items() if f == fid}
        pivot[int(fid)] = {
            "codigo": filiais.loc[fid, "codigo"],
            "nome":   filiais.loc[fid, "nome"],
            "meses":  [meses_vals.get(m, 0.0) for m in range(1, 13)],
            "total":  sum(meses_vals.values()),
        }

    totais_mes  = [sum(pivot[f]["meses"][i] for f in pivot) for i in range(12)]
    grand_total = sum(totais_mes)

    return templates.TemplateResponse(request, "budget.html", {
        "today":        _today(),
        "versoes":      _versoes_lista(versoes),
        "versao_id":    versao_id,
        "versao_info":  versao_info,
        "meses":        MESES,
        "pivot":        pivot,
        "filiais_ord":  [int(f) for f in sorted(filiais.index)],
        "totais_mes":   totais_mes,
        "grand_total":  grand_total,
    })


@app.get("/realizado", response_class=HTMLResponse)
async def realizado_view(
    request: Request,
    ano: int         = Query(default=2024),
    filial_id: Optional[int] = Query(default=None),
    msg: Optional[str]       = Query(default=None),
):
    db = _db()
    filiais, contas, versoes, ccus = _lookup(db)
    real     = db.tabela("Realizado")
    anos_disp = sorted(real["ano"].unique().tolist(), reverse=True) if not real.empty else [2024]

    real_f   = real[real["ano"] == ano]
    if filial_id:
        real_f = real_f[real_f["filial_id"] == filial_id]

    rec_ids  = _receita_ids(contas)
    real_rec = real_f[real_f["conta_id"].isin(rec_ids)]

    tabela = []
    for fid in sorted(filiais.index):
        sub = real_rec[real_rec["filial_id"] == fid]
        if sub.empty and filial_id and int(fid) != filial_id:
            continue
        mv = sub.groupby("mes")["valor"].sum()
        tabela.append({
            "filial_codigo": filiais.loc[fid, "codigo"],
            "filial_nome":   filiais.loc[fid, "nome"],
            "filial_id":     int(fid),
            "meses":         [float(mv.get(m, 0)) for m in range(1, 13)],
            "total":         float(mv.sum()),
        })

    return templates.TemplateResponse(request, "realizado.html", {
        "today":        _today(),
        "anos":         anos_disp,
        "ano":          ano,
        "filial_id":    filial_id,
        "filiais":      [{"id": int(i), "codigo": r["codigo"], "nome": r["nome"]}
                         for i, r in filiais.iterrows()],
        "meses":        MESES,
        "tabela":       tabela,
        "ccus_lista":   [{"id": int(i), "label": f"{r['codigo']} — {r['nome']}"}
                         for i, r in ccus.sort_values("filial_id").iterrows()],
        "contas_lista": [{"id": int(i), "label": f"{r['codigo']} — {r['nome']}"}
                         for i, r in contas.iterrows()
                         if r["categoria"] in ("receita", "custo")],
        "msg":          msg,
    })


@app.post("/realizado", response_class=HTMLResponse)
async def add_realizado(
    filial_id: int   = Form(...),
    ccu_id:    int   = Form(...),
    conta_id:  int   = Form(...),
    ano:       int   = Form(...),
    mes:       int   = Form(...),
    valor:     float = Form(...),
    origem:    str   = Form(default="manual"),
):
    db   = _db()
    real = db.tabela("Realizado")
    nid  = int(real["id"].max()) + 1 if not real.empty else 1
    nova = pd.DataFrame([{
        "id":          nid,
        "filial_id":   filial_id,
        "ccu_id":      ccu_id,
        "conta_id":    conta_id,
        "ano":         ano,
        "mes":         mes,
        "valor":       valor,
        "origem":      origem,
        "importado_em": str(date.today()),
        "created_by":  "web",
    }])
    db.salvar("Realizado", pd.concat([real, nova], ignore_index=True),
              registrar_audit=False)
    return RedirectResponse(
        url=f"/realizado?ano={ano}&msg=Lançamento+adicionado+com+sucesso",
        status_code=303,
    )


@app.get("/relatorio", response_class=HTMLResponse)
async def relatorio_view(
    request:   Request,
    versao_id: Optional[int] = Query(default=None),
    ano:       int            = Query(default=2024),
):
    db = _db()
    filiais, contas, versoes, ccus = _lookup(db)

    if versao_id is None:
        versao_id = _latest_approved(versoes, ano=ano)

    bud  = db.tabela("BudgetLinhas")
    bud  = bud[bud["versao_id"] == versao_id]
    real = db.tabela("Realizado")
    real = real[real["ano"] == ano]

    tabela  = _bvr_por_filial(bud, real, filiais, contas)
    tot_b   = sum(r["budget"] for r in tabela)
    tot_r   = sum(r["real"]   for r in tabela)
    tot_var = (tot_r - tot_b) / tot_b * 100 if tot_b else 0.0
    tot_mg  = sum(r["margem"] for r in tabela) / len(tabela) if tabela else 0.0

    rec_ids = _receita_ids(contas)
    bud_d   = bud[bud["conta_id"].isin(rec_ids)].groupby(["filial_id","conta_id","mes"])["valor"].sum().reset_index()
    real_d  = real[real["conta_id"].isin(rec_ids)].groupby(["filial_id","conta_id","mes"])["valor"].sum().reset_index()

    merged = pd.merge(
        bud_d.rename(columns={"valor": "budget"}),
        real_d.rename(columns={"valor": "real"}),
        on=["filial_id","conta_id","mes"], how="outer",
    ).fillna(0)
    merged["var_rs"]  = merged["real"] - merged["budget"]
    merged["var_pct"] = (
        merged["var_rs"] / merged["budget"].replace(0, float("nan")) * 100
    ).fillna(0)
    merged["filial_codigo"] = merged["filial_id"].map(filiais["codigo"])
    merged["conta_nome"]    = merged["conta_id"].map(contas["nome"])
    detalhe = merged.sort_values(["filial_codigo","mes","conta_nome"]).to_dict("records")

    anos_disp = sorted(db.tabela("Realizado")["ano"].unique().tolist(), reverse=True)

    return templates.TemplateResponse(request, "relatorio.html", {
        "today":        _today(),
        "versoes":      _versoes_lista(versoes),
        "versao_id":    versao_id,
        "anos":         anos_disp,
        "ano":          ano,
        "kpis": {
            "tot_budget":  tot_b,
            "tot_real":    tot_r,
            "tot_var_pct": round(tot_var, 2),
            "margem":      round(tot_mg, 2),
        },
        "tabela":       tabela,
        "detalhe":      detalhe,
        "chart_labels": json.dumps([r["filial_codigo"] for r in tabela]),
        "chart_budget": json.dumps([round(r["budget"]) for r in tabela]),
        "chart_real":   json.dumps([round(r["real"])   for r in tabela]),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
