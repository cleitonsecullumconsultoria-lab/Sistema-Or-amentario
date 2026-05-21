"""
Camada de acesso ao ROV_Base_Dados.xlsx.

Uso:
    from db import DB
    db = DB()
    df = db.tabela("BudgetLinhas")
    db.salvar("BudgetLinhas", df)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

_BASE_DIR = Path(__file__).parent
_DATA_DIR = _BASE_DIR / "data"
_LOG_DIR = _BASE_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=_LOG_DIR / "db.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Abas conhecidas — usadas para validação e type hints de documentação
ABAS = [
    "Empresas",
    "Filiais",
    "PlanoContas",
    "CentrosCusto",
    "BudgetVersoes",
    "BudgetLinhas",
    "Realizado",
    "PesosRateio",
    "ReceitasPosVenda",
    "Colaboradores",
    "FolhaMensal",
    "AuditLog",
]


def _localizar_excel() -> Path:
    """Encontra o arquivo Excel na pasta data/, independente do nome exato."""
    candidatos = sorted(_DATA_DIR.glob("*.xlsx"))
    if not candidatos:
        raise FileNotFoundError(
            f"Nenhum arquivo .xlsx encontrado em '{_DATA_DIR}'. "
            "Coloque o ROV_Base_Dados.xlsx nessa pasta."
        )
    if len(candidatos) > 1:
        logger.warning("Múltiplos .xlsx em data/; usando '%s'", candidatos[0].name)
    return candidatos[0]


class DB:
    """Interface simples para ler e gravar abas do Excel ROV."""

    def __init__(self, caminho: str | Path | None = None) -> None:
        self.caminho = Path(caminho) if caminho else _localizar_excel()
        logger.info("DB iniciado: %s", self.caminho)

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def tabela(self, aba: str, **kwargs: Any) -> pd.DataFrame:
        """Retorna o conteúdo de uma aba como DataFrame."""
        df = pd.read_excel(self.caminho, sheet_name=aba, **kwargs)
        logger.info("Lida aba '%s' (%d linhas)", aba, len(df))
        return df

    def todas_abas(self) -> dict[str, pd.DataFrame]:
        """Lê todas as abas de uma vez; retorna dict {nome_aba: DataFrame}."""
        dfs = pd.read_excel(self.caminho, sheet_name=None)
        logger.info("Lidas %d abas", len(dfs))
        return dfs

    def nomes_abas(self) -> list[str]:
        """Lista os nomes das abas disponíveis no arquivo."""
        import openpyxl  # importação tardia para não exigir durante testes

        wb = openpyxl.load_workbook(self.caminho, read_only=True, data_only=True)
        nomes = wb.sheetnames
        wb.close()
        return nomes

    # ------------------------------------------------------------------
    # Gravação
    # ------------------------------------------------------------------

    def salvar(self, aba: str, df: pd.DataFrame, registrar_audit: bool = True) -> None:
        """
        Grava df de volta na aba especificada, preservando todas as demais abas.
        Usa openpyxl para escrita incremental (não recria o arquivo do zero).
        """
        with pd.ExcelWriter(
            self.caminho,
            engine="openpyxl",
            mode="a",
            if_sheet_exists="replace",
        ) as writer:
            df.to_excel(writer, sheet_name=aba, index=False)

        logger.info("Gravada aba '%s' (%d linhas)", aba, len(df))

        if registrar_audit:
            self._audit(aba, len(df))

    def _audit(self, aba: str, n_linhas: int) -> None:
        """Acrescenta uma linha na aba AuditLog."""
        try:
            audit = self.tabela("AuditLog")
        except Exception:
            audit = pd.DataFrame(columns=["DataHora", "Aba", "Linhas", "Usuario"])

        nova = pd.DataFrame(
            [
                {
                    "DataHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Aba": aba,
                    "Linhas": n_linhas,
                    "Usuario": os.getenv("USER", "sistema"),
                }
            ]
        )
        audit = pd.concat([audit, nova], ignore_index=True)
        # grava sem recursão (registrar_audit=False)
        self.salvar("AuditLog", audit, registrar_audit=False)

    # ------------------------------------------------------------------
    # Helpers de domínio
    # ------------------------------------------------------------------

    def filiais(self) -> pd.DataFrame:
        return self.tabela("Filiais")

    def plano_contas(self) -> pd.DataFrame:
        return self.tabela("PlanoContas")

    def budget(self, versao: str | None = None) -> pd.DataFrame:
        """Retorna BudgetLinhas, opcionalmente filtrado por versão."""
        df = self.tabela("BudgetLinhas")
        if versao:
            df = df[df["Versao"] == versao]
        return df

    def realizado(
        self,
        ano: int | None = None,
        mes: int | None = None,
    ) -> pd.DataFrame:
        """Retorna Realizado, opcionalmente filtrado por ano e/ou mês."""
        df = self.tabela("Realizado")
        if ano:
            df = df[df["Ano"] == ano]
        if mes:
            df = df[df["Mes"] == mes]
        return df
