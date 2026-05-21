"""
Popula ROV_Base_Dados.xlsx com dados fictícios mas coerentes.

Gera:
  - CentrosCusto para todas as 8 filiais (completa as 6 que faltam)
  - BudgetLinhas para versões 2024, 2025 e 2026 (todas aprovadas)
  - Realizado para 2023 e 2024
  - ReceitasPosVenda para 2023 e 2024

Uso:
    python scripts/gerar_dados_ficticios.py
    python scripts/gerar_dados_ficticios.py --seed 99
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB

# ─────────────────────────────────────────────────────────────────────────────
# Configuração
# ─────────────────────────────────────────────────────────────────────────────

FILIAIS: dict[int, dict] = {
    1: dict(codigo="CBA", pecas_min=3_000_000, pecas_max=6_000_000),
    2: dict(codigo="ROO", pecas_min=2_500_000, pecas_max=4_500_000),
    3: dict(codigo="SNP", pecas_min=3_000_000, pecas_max=6_000_000),
    4: dict(codigo="SPZ", pecas_min=  800_000, pecas_max=1_500_000),
    5: dict(codigo="AGB", pecas_min=  800_000, pecas_max=1_500_000),
    6: dict(codigo="REF", pecas_min=  800_000, pecas_max=1_200_000),
    7: dict(codigo="MTP", pecas_min=  300_000, pecas_max=  700_000),
    8: dict(codigo="CWS", pecas_min=  300_000, pecas_max=  700_000),
}

# Prefixo de 2 dígitos para código CCU por filial (mantém padrão existente)
FILIAL_PREFIXO = {1: "21", 2: "31", 3: "41", 4: "51",
                  5: "61", 6: "71", 7: "81", 8: "91"}

CCU_TIPOS = [
    ("211", "Peças Balcão",       "pecas_balcao"),
    ("212", "Peças Oficina",      "pecas_oficina"),
    ("213", "Peças Garantia",     "pecas_garantia"),
    ("214", "Peças PMS",          "pecas_pms"),
    ("223", "Serviços Oficina",   "serv_oficina"),
    ("224", "Serviços Garantia",  "serv_garantia"),
    ("225", "Serviços PMS",       "serv_pms"),
]

# IDs do PlanoContas (conferidos na base real)
CONTA_PECAS     = [1, 2, 3]   # 311201 Scania, 311202 Similar, 311204 Combustíveis
CONTA_SERVICOS  = [4, 5, 6]   # 311302 Terceiros, 311303 Outros, 311305 Garantia
CONTA_CONECT    = 7            # 311401 Conectividade
CONTA_CUSTO_PEC = 11           # 411001 Custo Peças
CONTA_CUSTO_SRV = 12           # 411002 Custo Serviços

# Pesos de distribuição (somam 1 dentro de cada grupo)
W_CCU_PECAS = dict(pecas_balcao=0.40, pecas_oficina=0.32,
                   pecas_garantia=0.15, pecas_pms=0.13)
W_CCU_SERV  = dict(serv_oficina=0.50, serv_garantia=0.30, serv_pms=0.20)

W_CONTA_PECAS = {1: 0.83, 2: 0.05, 3: 0.12}   # Scania / Similar / Combustíveis
W_CONTA_SERV = {
    "serv_oficina":  {4: 0.20, 5: 0.55, 6: 0.25},
    "serv_garantia": {4: 0.10, 5: 0.25, 6: 0.65},
    "serv_pms":      {4: 0.45, 5: 0.45, 6: 0.10},
}

# Serviços = fração das peças; margens
SERV_FATOR   = 0.30          # ~30% do volume de peças
MARG_PECAS   = (0.27, 0.30)
MARG_SERV    = (0.55, 0.68)

# Sazonalidade mensal (índices, média ≈ 1.0)
SAZON = np.array([0.88, 0.92, 1.08, 1.15, 1.05,
                  0.95, 1.10, 1.12, 1.02, 0.93, 0.90, 0.90])

# Versão → ano para BudgetLinhas
VERSAO_ANO = {1: 2024, 2: 2025, 3: 2026}
# Crescimento budget sobre realizado anterior
CRESCIMENTO_BUD = {1: 1.12, 2: 1.12, 3: 1.15}


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────────────────────────────────────

def _ruido(rng: np.random.Generator, base: float, pct: float = 0.07) -> float:
    return max(0.0, base * (1 + rng.normal(0, pct)))


def _distribuir(rng: np.random.Generator,
                total: float,
                pesos: dict,
                ruido_pct: float = 0.08) -> dict:
    """Distribui total entre chaves com ruído proporcional."""
    raw = {k: pesos[k] * _ruido(rng, 1.0, ruido_pct) for k in pesos}
    soma = sum(raw.values())
    return {k: total * v / soma for k, v in raw.items()}


def _arred(v: float) -> float:
    return round(v, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 1. CentrosCusto — completa as 6 filiais que faltam
# ─────────────────────────────────────────────────────────────────────────────

def gerar_centros_custo(db: DB) -> pd.DataFrame:
    """Retorna DataFrame completo de CCUs para as 8 filiais."""
    existentes = db.tabela("CentrosCusto")
    # filiais já presentes na base
    filiais_ok = set(existentes["filial_id"].unique())
    filiais_novas = [fid for fid in FILIAIS if fid not in filiais_ok]

    if not filiais_novas:
        print("  CentrosCusto: todas as filiais já possuem CCUs.")
        return existentes

    max_id = int(existentes["id"].max())
    novos: list[dict] = []
    for fid in filiais_novas:
        cod = db.tabela("Filiais").set_index("id").loc[fid, "codigo"]
        prefixo = FILIAL_PREFIXO[fid]
        for sufixo, nome_base, tipo in CCU_TIPOS:
            max_id += 1
            novos.append({
                "id":        max_id,
                "filial_id": fid,
                "codigo":    f"{prefixo}{sufixo}",
                "nome":      f"{nome_base} - {cod}",
                "tipo":      tipo,
                "ativo":     True,
            })

    resultado = pd.concat([existentes, pd.DataFrame(novos)], ignore_index=True)
    print(f"  CentrosCusto: adicionadas {len(novos)} linhas "
          f"para {len(filiais_novas)} filiais → total {len(resultado)} CCUs")
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# 2. Geração de valores mensais por filial
# ─────────────────────────────────────────────────────────────────────────────

def _base_mensal_pecas(rng: np.random.Generator,
                       filial_id: int) -> np.ndarray:
    """12 valores mensais de receita bruta de peças com sazonalidade."""
    cfg = FILIAIS[filial_id]
    base = rng.uniform(cfg["pecas_min"], cfg["pecas_max"])
    valores = base * SAZON
    # adiciona ruído único por mês
    valores = np.array([_ruido(rng, v, 0.06) for v in valores])
    return valores


def _gerar_linhas_filial_ano(
    rng: np.random.Generator,
    filial_id: int,
    ano: int,
    ccu_map: dict,           # (filial_id, tipo) → ccu_id
    pecas_base: np.ndarray | None = None,
    crescimento: float = 1.0,
) -> tuple[list[dict], np.ndarray]:
    """
    Retorna (linhas, pecas_mensal).
    linhas: lista de dicts com campos comuns entre BudgetLinhas e Realizado.
    """
    if pecas_base is None:
        pecas_base = _base_mensal_pecas(rng, filial_id)
    pecas_mes = pecas_base * crescimento

    linhas: list[dict] = []

    for mes_idx, pecas_total in enumerate(pecas_mes, start=1):
        servicos_total = _ruido(rng, pecas_total * SERV_FATOR, 0.10)

        # ── peças por CCU e conta ──────────────────────────────────────────
        dist_ccu_pec = _distribuir(rng, pecas_total, W_CCU_PECAS)
        for tipo_ccu, valor_ccu in dist_ccu_pec.items():
            ccu_id = ccu_map[(filial_id, tipo_ccu)]
            dist_conta = _distribuir(rng, valor_ccu, W_CONTA_PECAS)
            for conta_id, valor_conta in dist_conta.items():
                linhas.append(dict(filial_id=filial_id, ccu_id=ccu_id,
                                   conta_id=conta_id, ano=ano, mes=mes_idx,
                                   valor=_arred(valor_conta)))
            # custo das peças (negativo / despesa)
            margem = rng.uniform(*MARG_PECAS)
            custo  = _arred(valor_ccu * (1 - margem))
            linhas.append(dict(filial_id=filial_id, ccu_id=ccu_id,
                               conta_id=CONTA_CUSTO_PEC, ano=ano, mes=mes_idx,
                               valor=custo))

        # ── serviços por CCU e conta ───────────────────────────────────────
        dist_ccu_srv = _distribuir(rng, servicos_total, W_CCU_SERV)
        for tipo_ccu, valor_ccu in dist_ccu_srv.items():
            ccu_id = ccu_map[(filial_id, tipo_ccu)]
            dist_conta = _distribuir(rng, valor_ccu, W_CONTA_SERV[tipo_ccu])
            for conta_id, valor_conta in dist_conta.items():
                linhas.append(dict(filial_id=filial_id, ccu_id=ccu_id,
                                   conta_id=conta_id, ano=ano, mes=mes_idx,
                                   valor=_arred(valor_conta)))
            # custo dos serviços
            margem = rng.uniform(*MARG_SERV)
            custo  = _arred(valor_ccu * (1 - margem))
            linhas.append(dict(filial_id=filial_id, ccu_id=ccu_id,
                               conta_id=CONTA_CUSTO_SRV, ano=ano, mes=mes_idx,
                               valor=custo))

        # ── conectividade (usa CCU serv_oficina) ──────────────────────────
        cfg = FILIAIS[filial_id]
        escala = (cfg["pecas_max"] + cfg["pecas_min"]) / 2 / 3_000_000
        conect = _arred(_ruido(rng, 25_000 * escala, 0.15))
        ccu_id_of = ccu_map[(filial_id, "serv_oficina")]
        linhas.append(dict(filial_id=filial_id, ccu_id=ccu_id_of,
                           conta_id=CONTA_CONECT, ano=ano, mes=mes_idx,
                           valor=conect))

    return linhas, pecas_mes


# ─────────────────────────────────────────────────────────────────────────────
# 3. Realizado
# ─────────────────────────────────────────────────────────────────────────────

def gerar_realizado(rng: np.random.Generator,
                    ccu_map: dict) -> tuple[pd.DataFrame, dict]:
    """Gera Realizado 2023 e 2024; retorna DataFrame e dict pecas_2024[filial_id]."""
    rows: list[dict] = []
    pecas_2024: dict[int, np.ndarray] = {}

    for fid in sorted(FILIAIS):
        # 2023
        linhas_2023, base_2023 = _gerar_linhas_filial_ano(rng, fid, 2023, ccu_map)
        rows.extend(linhas_2023)

        # 2024 = 2023 × crescimento, com variação de execução
        crescimento = rng.uniform(1.08, 1.16)
        linhas_2024, base_2024 = _gerar_linhas_filial_ano(
            rng, fid, 2024, ccu_map, base_2023, crescimento)
        rows.extend(linhas_2024)
        pecas_2024[fid] = base_2024

    df = pd.DataFrame(rows)
    df.insert(0, "id", range(1, len(df) + 1))
    df["origem"]       = "dados_ficticios"
    df["importado_em"] = str(date.today())
    df["created_by"]   = "sistema"
    print(f"  Realizado: {len(df)} linhas (2023 + 2024, 8 filiais)")
    return df, pecas_2024


# ─────────────────────────────────────────────────────────────────────────────
# 4. BudgetLinhas
# ─────────────────────────────────────────────────────────────────────────────

def gerar_budget(rng: np.random.Generator,
                 ccu_map: dict,
                 pecas_2024: dict) -> pd.DataFrame:
    """Gera BudgetLinhas para versões 2024, 2025 e 2026."""
    rows: list[dict] = []

    for versao_id, ano in VERSAO_ANO.items():
        cresc = CRESCIMENTO_BUD[versao_id]
        for fid in sorted(FILIAIS):
            base = pecas_2024[fid] / cresc   # ajusta base por versão
            linhas, _ = _gerar_linhas_filial_ano(
                rng, fid, ano, ccu_map, base, cresc)
            for ln in linhas:
                ln["versao_id"]  = versao_id
                ln["obs"]        = None
                ln["created_by"] = "sistema"
                ln["created_at"] = f"{ano - 1}-12-01"
                ln.pop("ano", None)   # budget não tem coluna ano direta
            rows.extend(linhas)

    df = pd.DataFrame(rows)
    df.insert(0, "id", range(1, len(df) + 1))
    # reordenar colunas para corresponder ao schema
    df = df[["id", "versao_id", "filial_id", "ccu_id", "conta_id",
             "mes", "valor", "obs", "created_by", "created_at"]]
    print(f"  BudgetLinhas: {len(df)} linhas (versões 2024/2025/2026, 8 filiais)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 5. ReceitasPosVenda (consolidada por filial/mês, apenas receitas brutas)
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIAS_PV = [
    ("pecas_balcao",   "pecas_balcao",   MARG_PECAS),
    ("pecas_oficina",  "pecas_oficina",  MARG_PECAS),
    ("pecas_garantia", "pecas_garantia", MARG_PECAS),
    ("pecas_pms",      "pecas_pms",      MARG_PECAS),
    ("serv_oficina",   "serv_oficina",   MARG_SERV),
    ("serv_garantia",  "serv_garantia",  MARG_SERV),
    ("serv_pms",       "serv_pms",       MARG_SERV),
]


def gerar_receitas_posv(rng: np.random.Generator,
                        ccu_map: dict,
                        realizado_df: pd.DataFrame) -> pd.DataFrame:
    """Consolida valores do Realizado em ReceitasPosVenda por categoria/filial/mês."""
    ccu_inv = {v: k[1] for k, v in ccu_map.items()}   # ccu_id → tipo

    # apenas contas de receita (< 400000 = receita bruta)
    real_rec = realizado_df[realizado_df["conta_id"].isin(
        CONTA_PECAS + CONTA_SERVICOS + [CONTA_CONECT]
    )].copy()
    real_rec["categoria"] = real_rec["ccu_id"].map(ccu_inv)
    real_rec.loc[real_rec["conta_id"] == CONTA_CONECT, "categoria"] = "conectividade"

    grp = real_rec.groupby(
        ["filial_id", "categoria", "conta_id", "ano", "mes"], as_index=False
    )["valor"].sum()

    rows: list[dict] = []
    for _, row in grp.iterrows():
        cat = row["categoria"] if row["categoria"] else "outros"
        # Determina margem
        if "pec" in cat:
            margem = rng.uniform(*MARG_PECAS)
        elif cat == "conectividade":
            margem = 0.95
        else:
            margem = rng.uniform(*MARG_SERV)

        rb  = row["valor"]
        imp = _arred(rb * 0.03)     # impostos simplificados ~3%
        dev = _arred(rb * 0.005)    # devoluções ~0,5%
        rl  = _arred(rb - imp - dev)
        cst = _arred(rl * (1 - margem))
        lb  = _arred(rl - cst)
        rows.append(dict(
            filial_id       = int(row["filial_id"]),
            categoria       = cat,
            conta_id        = int(row["conta_id"]),
            ano             = int(row["ano"]),
            mes             = int(row["mes"]),
            receita_bruta   = _arred(rb),
            impostos        = imp,
            devolucoes      = dev,
            receita_liquida = rl,
            custo           = cst,
            lucro_bruto     = lb,
            margem_pct      = round(margem * 100, 2),
            origem          = "dados_ficticios",
            created_by      = "sistema",
            created_at      = str(date.today()),
        ))

    df = pd.DataFrame(rows)
    df.insert(0, "id", range(1, len(df) + 1))
    print(f"  ReceitasPosVenda: {len(df)} linhas")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Orquestrador
# ─────────────────────────────────────────────────────────────────────────────

def main(seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    db  = DB()
    print(f"Base: {db.caminho.name}  |  seed={seed}\n")

    # 1. CentrosCusto
    print("── CentrosCusto ──")
    df_ccu = gerar_centros_custo(db)
    ccu_map: dict[tuple[int, str], int] = {}
    for _, r in df_ccu.iterrows():
        ccu_map[(int(r["filial_id"]), r["tipo"])] = int(r["id"])

    # 2. Realizado
    print("\n── Realizado ──")
    df_real, pecas_2024 = gerar_realizado(rng, ccu_map)

    # 3. BudgetLinhas
    print("\n── BudgetLinhas ──")
    df_bud = gerar_budget(rng, ccu_map, pecas_2024)

    # 4. ReceitasPosVenda
    print("\n── ReceitasPosVenda ──")
    df_pv = gerar_receitas_posv(rng, ccu_map, df_real)

    # 5. Grava no Excel (sem registrar audit para não poluir o log)
    print("\n── Gravando no Excel ──")
    db.salvar("CentrosCusto",    df_ccu,  registrar_audit=False)
    db.salvar("BudgetLinhas",    df_bud,  registrar_audit=False)
    db.salvar("Realizado",       df_real, registrar_audit=False)
    db.salvar("ReceitasPosVenda",df_pv,   registrar_audit=False)
    print("Concluído.")

    # 6. Resumo rápido
    print("\n══ Resumo dos dados gerados ══")
    for fid, cod in [(f, FILIAIS[f]["codigo"]) for f in sorted(FILIAIS)]:
        media_pec = float(pecas_2024[fid].mean())
        print(f"  {cod}: receita média peças 2024 = R$ {media_pec:>12,.0f}/mês")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    main(args.seed)
