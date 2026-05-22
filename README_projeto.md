# Sistema Orçamentário — Rota Oeste Veículos (ROV)

Sistema de controle de **Budget** e **Pós-venda** das 8 filiais da ROV.  
Dados armazenados em `ROV_Base_Dados.xlsx`; scripts Python lêem e gravam via `db.py`.

## Estrutura de pastas

```
Sistema-Or-amentario/
├── data/                    # ROV_Base_Dados.xlsx (não versionado)
├── scripts/                 # Utilitários de carga e manutenção
├── relatorios/              # Scripts de relatórios
├── exports/                 # Saídas geradas (CSV, XLSX, PDF)
├── logs/                    # Log de execução
├── db.py                    # Camada de acesso ao Excel
└── requirements.txt         # Dependências Python
```

## Abas do Excel (17)

| Aba | Descrição |
|-----|-----------|
| Empresas | Grupo e CNPJs |
| Filiais | 8 filiais ROV |
| PlanoContas | Plano de contas gerencial |
| CentrosCusto | Centros de custo |
| BudgetVersoes | Versões de orçamento (Original, Rev1…) |
| BudgetLinhas | Linhas de budget por conta/CC/mês |
| Realizado | Lançamentos realizados |
| PesosRateio | Pesos para rateio entre filiais |
| ReceitasPosVenda | Receitas de pós-venda |
| Colaboradores | Cadastro de colaboradores |
| FolhaMensal | Folha de pagamento mensal |
| AuditLog | Rastro de alterações |

## Pré-requisitos

```bash
pip install -r requirements.txt
```

## Uso rápido

```python
from db import DB

db = DB()                              # abre ROV_Base_Dados.xlsx
df = db.tabela("BudgetLinhas")         # retorna DataFrame
db.salvar("BudgetLinhas", df)          # grava de volta
```

## Relatórios disponíveis

| Script | Descrição |
|--------|-----------|
| `relatorios/relatorio_budget_vs_real.py` | Budget × Realizado por filial/conta/mês |

## Executando um relatório

```bash
python relatorios/relatorio_budget_vs_real.py
# Saída em exports/budget_vs_real_<data>.xlsx
```
