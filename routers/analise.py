from fastapi import APIRouter, Request
from tmpl import templates

router = APIRouter(prefix="/analise", tags=["analise"])


@router.get("/")
async def analise_index(request: Request):
    return templates.TemplateResponse(request, "em_construcao.html", {
        "modulo": "Análise & Relatórios",
        "active_page": "analise",
    })
