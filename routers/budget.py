from fastapi import APIRouter, Request
from tmpl import templates

router = APIRouter(prefix="/budget", tags=["budget"])


@router.get("/")
async def budget_index(request: Request):
    return templates.TemplateResponse(request, "em_construcao.html", {
        "modulo": "Budget",
        "active_page": "budget",
    })
