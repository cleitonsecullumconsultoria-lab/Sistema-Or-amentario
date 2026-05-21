from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB
from tmpl import templates

router = APIRouter(prefix="/cadastros", tags=["cadastros"])

# ---------------------------------------------------------------------------
# Filiais
# ---------------------------------------------------------------------------

@router.get("/filiais")
async def filiais_list(request: Request):
    db = DB()
    filiais = db.tabela("Filiais").to_dict("records")
    empresas = db.tabela("Empresas").to_dict("records")
    return templates.TemplateResponse(request, "cadastros/filiais.html", {
        "filiais": filiais,
        "empresas": empresas,
        "active_page": "cadastros",
    })


@router.post("/filiais/criar")
async def filiais_criar(
    request: Request,
    empresa_id: int = Form(...),
    codigo: str = Form(...),
    nome: str = Form(...),
    cidade: str = Form(...),
    uf: str = Form(...),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("Filiais")
    novo_id = int(df["id"].max()) + 1 if not df.empty else 1
    nova = pd.DataFrame([{
        "id": novo_id,
        "empresa_id": empresa_id,
        "codigo": codigo.upper().strip(),
        "nome": nome.strip(),
        "cidade": cidade.strip(),
        "uf": uf.upper().strip(),
        "ativo": 1 if ativo == "1" else 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }])
    df = pd.concat([df, nova], ignore_index=True)
    db.salvar("Filiais", df)
    return RedirectResponse("/cadastros/filiais", status_code=303)


@router.post("/filiais/editar/{filial_id}")
async def filiais_editar(
    request: Request,
    filial_id: int,
    empresa_id: int = Form(...),
    codigo: str = Form(...),
    nome: str = Form(...),
    cidade: str = Form(...),
    uf: str = Form(...),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("Filiais")
    mask = df["id"] == filial_id
    df.loc[mask, "empresa_id"] = empresa_id
    df.loc[mask, "codigo"] = codigo.upper().strip()
    df.loc[mask, "nome"] = nome.strip()
    df.loc[mask, "cidade"] = cidade.strip()
    df.loc[mask, "uf"] = uf.upper().strip()
    df.loc[mask, "ativo"] = 1 if ativo == "1" else 0
    db.salvar("Filiais", df)
    return RedirectResponse("/cadastros/filiais", status_code=303)


@router.post("/filiais/excluir/{filial_id}")
async def filiais_excluir(request: Request, filial_id: int):
    db = DB()
    df = db.tabela("Filiais")
    df = df[df["id"] != filial_id]
    db.salvar("Filiais", df)
    return RedirectResponse("/cadastros/filiais", status_code=303)


# ---------------------------------------------------------------------------
# Plano de Contas
# ---------------------------------------------------------------------------

@router.get("/plano-contas")
async def plano_contas_list(request: Request, categoria: str = ""):
    db = DB()
    df = db.tabela("PlanoContas")
    if categoria:
        df = df[df["categoria"] == categoria]
    contas = df.to_dict("records")
    return templates.TemplateResponse(request, "cadastros/plano_contas.html", {
        "contas": contas,
        "categoria_filtro": categoria,
        "active_page": "cadastros",
    })


@router.post("/plano-contas/criar")
async def plano_contas_criar(
    request: Request,
    codigo: str = Form(...),
    nome: str = Form(...),
    categoria: str = Form(...),
    tipo: str = Form(...),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("PlanoContas")
    novo_id = int(df["id"].max()) + 1 if not df.empty else 1
    nova = pd.DataFrame([{
        "id": novo_id,
        "empresa_id": 1,
        "codigo": codigo.strip(),
        "nome": nome.strip(),
        "categoria": categoria,
        "tipo": tipo,
        "ativo": 1 if ativo == "1" else 0,
    }])
    df = pd.concat([df, nova], ignore_index=True)
    db.salvar("PlanoContas", df)
    return RedirectResponse("/cadastros/plano-contas", status_code=303)


@router.post("/plano-contas/editar/{conta_id}")
async def plano_contas_editar(
    request: Request,
    conta_id: int,
    codigo: str = Form(...),
    nome: str = Form(...),
    categoria: str = Form(...),
    tipo: str = Form(...),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("PlanoContas")
    mask = df["id"] == conta_id
    df.loc[mask, "codigo"] = codigo.strip()
    df.loc[mask, "nome"] = nome.strip()
    df.loc[mask, "categoria"] = categoria
    df.loc[mask, "tipo"] = tipo
    df.loc[mask, "ativo"] = 1 if ativo == "1" else 0
    db.salvar("PlanoContas", df)
    return RedirectResponse("/cadastros/plano-contas", status_code=303)


@router.post("/plano-contas/excluir/{conta_id}")
async def plano_contas_excluir(request: Request, conta_id: int):
    db = DB()
    df = db.tabela("PlanoContas")
    df = df[df["id"] != conta_id]
    db.salvar("PlanoContas", df)
    return RedirectResponse("/cadastros/plano-contas", status_code=303)


# ---------------------------------------------------------------------------
# Centros de Custo
# ---------------------------------------------------------------------------

@router.get("/centros-custo")
async def centros_custo_list(request: Request, filial_id: str = ""):
    db = DB()
    df = db.tabela("CentrosCusto")
    filiais = db.tabela("Filiais").to_dict("records")
    if filial_id:
        df = df[df["filial_id"] == int(filial_id)]
    ccus = df.to_dict("records")
    filiais_map = {f["id"]: f["nome"] for f in filiais}
    for c in ccus:
        c["filial_nome"] = filiais_map.get(c["filial_id"], "-")
    return templates.TemplateResponse(request, "cadastros/centros_custo.html", {
        "ccus": ccus,
        "filiais": filiais,
        "filial_filtro": filial_id,
        "active_page": "cadastros",
    })


@router.post("/centros-custo/criar")
async def centros_custo_criar(
    request: Request,
    filial_id: int = Form(...),
    codigo: str = Form(...),
    nome: str = Form(...),
    tipo: str = Form(...),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("CentrosCusto")
    novo_id = int(df["id"].max()) + 1 if not df.empty else 1
    nova = pd.DataFrame([{
        "id": novo_id,
        "filial_id": filial_id,
        "codigo": codigo.strip(),
        "nome": nome.strip(),
        "tipo": tipo,
        "ativo": 1 if ativo == "1" else 0,
    }])
    df = pd.concat([df, nova], ignore_index=True)
    db.salvar("CentrosCusto", df)
    return RedirectResponse("/cadastros/centros-custo", status_code=303)


@router.post("/centros-custo/editar/{ccu_id}")
async def centros_custo_editar(
    request: Request,
    ccu_id: int,
    filial_id: int = Form(...),
    codigo: str = Form(...),
    nome: str = Form(...),
    tipo: str = Form(...),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("CentrosCusto")
    mask = df["id"] == ccu_id
    df.loc[mask, "filial_id"] = filial_id
    df.loc[mask, "codigo"] = codigo.strip()
    df.loc[mask, "nome"] = nome.strip()
    df.loc[mask, "tipo"] = tipo
    df.loc[mask, "ativo"] = 1 if ativo == "1" else 0
    db.salvar("CentrosCusto", df)
    return RedirectResponse("/cadastros/centros-custo", status_code=303)


@router.post("/centros-custo/excluir/{ccu_id}")
async def centros_custo_excluir(request: Request, ccu_id: int):
    db = DB()
    df = db.tabela("CentrosCusto")
    df = df[df["id"] != ccu_id]
    db.salvar("CentrosCusto", df)
    return RedirectResponse("/cadastros/centros-custo", status_code=303)


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------

@router.get("/usuarios")
async def usuarios_list(request: Request):
    db = DB()
    usuarios = db.tabela("Usuarios").to_dict("records")
    filiais = db.tabela("Filiais").to_dict("records")
    filiais_map = {f["id"]: f["nome"] for f in filiais}
    for u in usuarios:
        u["filial_nome"] = filiais_map.get(u.get("filial_id"), "—")
    return templates.TemplateResponse(request, "cadastros/usuarios.html", {
        "usuarios": usuarios,
        "filiais": filiais,
        "active_page": "cadastros",
    })


@router.post("/usuarios/criar")
async def usuarios_criar(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    perfil: str = Form(...),
    filial_id: str = Form(""),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("Usuarios")
    novo_id = int(df["id"].max()) + 1 if not df.empty else 1
    nova = pd.DataFrame([{
        "id": novo_id,
        "nome": nome.strip(),
        "email": email.strip().lower(),
        "perfil": perfil,
        "filial_id": int(filial_id) if filial_id else None,
        "ativo": 1 if ativo == "1" else 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }])
    df = pd.concat([df, nova], ignore_index=True)
    db.salvar("Usuarios", df)
    return RedirectResponse("/cadastros/usuarios", status_code=303)


@router.post("/usuarios/editar/{usuario_id}")
async def usuarios_editar(
    request: Request,
    usuario_id: int,
    nome: str = Form(...),
    email: str = Form(...),
    perfil: str = Form(...),
    filial_id: str = Form(""),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("Usuarios")
    mask = df["id"] == usuario_id
    df.loc[mask, "nome"] = nome.strip()
    df.loc[mask, "email"] = email.strip().lower()
    df.loc[mask, "perfil"] = perfil
    df.loc[mask, "filial_id"] = int(filial_id) if filial_id else None
    df.loc[mask, "ativo"] = 1 if ativo == "1" else 0
    db.salvar("Usuarios", df)
    return RedirectResponse("/cadastros/usuarios", status_code=303)


@router.post("/usuarios/excluir/{usuario_id}")
async def usuarios_excluir(request: Request, usuario_id: int):
    db = DB()
    df = db.tabela("Usuarios")
    df = df[df["id"] != usuario_id]
    db.salvar("Usuarios", df)
    return RedirectResponse("/cadastros/usuarios", status_code=303)
