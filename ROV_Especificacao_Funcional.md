
# ESPECIFICAÇÃO FUNCIONAL COMPLETA
# Sistema Orçamentário — Rota Oeste Veículos (ROV)
# Versão 1.0 | Documento para desenvolvimento

---

## CONTEXTO DO NEGÓCIO

Grupo: Rota Oeste Veículos (ROV) — concessionária Scania
Filiais: CBA (Cuiabá), ROO (Rondonópolis), SNP (Sinop), SPZ (Sapezal), AGB (Água Boa), REF (Reformadora), MTP (Matuá), CWS (Lucas do Rio Verde)
Objetivo: substituir planilhas Excel dispersas por sistema web integrado

---

## STACK TÉCNICA

Backend: Python + FastAPI
Templates: Jinja2
Banco de dados: Excel (.xlsx) via openpyxl — arquivo data/ROV_Base_Dados.xlsx
Frontend: HTML + CSS puro (sem framework) + Chart.js para gráficos
Cores: Azul #1D3557 (sidebar/header), Verde #1D9E75 (ações/destaque), Fundo #F8F9FA
Fonte: Arial, system-ui

---

## ESTRUTURA DE PASTAS

Sistema-Or-amentario/
├── main.py                    ← FastAPI app principal
├── db.py                      ← camada de acesso ao Excel
├── requirements.txt
├── data/
│   └── ROV_Base_Dados.xlsx    ← banco de dados Excel
├── routers/
│   ├── cadastros.py
│   ├── budget.py
│   ├── receitas.py
│   ├── headcount.py
│   ├── opex.py
│   └── analise.py
└── templates/
    ├── base.html              ← layout com sidebar
    ├── dashboard.html
    ├── cadastros/
    │   ├── empresas.html
    │   ├── plano_contas.html
    │   ├── centros_custo.html
    │   └── usuarios.html
    ├── budget/
    │   ├── ciclo.html
    │   ├── entrada.html       ← TELA MAIS IMPORTANTE
    │   ├── aprovacao.html
    │   └── versoes.html
    ├── receitas/
    │   ├── posVenda.html
    │   ├── comissoes.html
    │   └── conectividade.html
    ├── headcount/
    │   ├── colaboradores.html
    │   ├── folha.html
    │   └── cargos.html
    ├── opex/
    │   ├── despesas.html
    │   └── capex.html
    └── analise/
        ├── bvsr.html
        ├── dre.html
        └── forecast.html

---

## MÓDULO 1 — CADASTROS

### 1.1 Empresas e Filiais

Tabela no Excel: aba "Filiais"
Campos: id, empresa_id, codigo, nome, cidade, uf, ativo

Filiais cadastradas:
- CBA | Rota Oeste Veículos · Cuiabá | Cuiabá | MT
- ROO | Rota Oeste Veículos · Rondonópolis | Rondonópolis | MT
- SNP | Rota Oeste Veículos · Sinop | Sinop | MT
- SPZ | Rota Oeste Veículos · Sapezal | Sapezal | MT
- AGB | Rota Oeste Veículos · Água Boa | Água Boa | MT
- REF | Rota Oeste Veículos · Reformadora | Guarantã do Norte | MT
- MTP | Rota Oeste Veículos · Matuá | Matupá | MT
- CWS | Rota Oeste Veículos · Lucas Rio Verde | Lucas do Rio Verde | MT

Tela: tabela listagem + botão Novo (modal com campos)

### 1.2 Plano de Contas

Tabela no Excel: aba "PlanoContas"
Campos: id, codigo, nome, categoria (receita/custo/despesa), tipo

Contas obrigatórias (extraídas das planilhas):
RECEITAS:
- 311201 | VENDA PEÇAS SCANIA | receita | pecas
- 311202 | VENDA PEÇAS SIMILAR | receita | pecas
- 311204 | VENDA COMBUSTÍVEIS E LUBRIFICANTES | receita | pecas
- 311302 | VENDA SERVIÇOS DE TERCEIROS | receita | servico
- 311305 | VENDA SERVIÇOS GARANTIA | receita | servico
- 311401 | VENDA CONECTIVIDADE | receita | comissao
- 311501 | COMISSÃO PMV | receita | comissao
- 311502 | COMISSÃO PMS | receita | comissao
- 311503 | COMISSÃO TOP DEALERS | receita | comissao
- 3.1.3.10 | VENDA PEÇAS SCANIA PMS | receita | pecas
- 3.1.4.03 | VENDA COMBUST./LUBRIF. EM PMS | receita | pecas
- 3.1.4.02 | VENDA COMBUST./LUBRIF. EM GARANTIA | receita | pecas
- 3.1.7.04 | VENDA SERVIÇOS DE TERCEIROS (REFORMADORA) | receita | servico

CUSTOS:
- 411001 | CUSTO DAS PEÇAS VENDIDAS (CPV) | custo | cpmv
- 411002 | CUSTO DOS SERVIÇOS PRESTADOS | custo | cpmv

DESPESAS:
- 511001 | FOLHA DE PAGAMENTO | despesa | pessoal
- 511002 | ENCARGOS SOCIAIS | despesa | pessoal
- 511003 | BENEFÍCIOS | despesa | pessoal
- 512001 | ALUGUEL | despesa | administrativo
- 512002 | ENERGIA ELÉTRICA | despesa | administrativo
- 512010 | SERVIÇOS TERCEIROS | despesa | administrativo

### 1.3 Centros de Custo (CCUs)

Tabela no Excel: aba "CentrosCusto"
Estrutura: código numérico + descrição + filial + tipo

CCUs por filial (padrão):
Para CBA (Cuiabá) — prefixo 21:
- 21211 | Peças Balcão - CBA
- 21212 | Peças Oficina - CBA
- 21213 | Peças Garantia Scania - CBA
- 21214 | Peças PMS - CBA
- 21223 | Serviços Oficina - CBA
- 21224 | Serviços Garantia - CBA
- 21225 | Serviços PMS - CBA
- 21232 | Funilaria/Reformadora - CBA

Para AGB (Água Boa) — prefixo 61:
- 61211 | Peças Balcão - AGB
- 61212 | Peças Oficina - AGB
- 61213 | Peças Garantia Scania - AGB
- 61214 | Peças PMS - AGB
- 61223 | Serviços Oficina - AGB
- 61224 | Serviços Garantia - AGB
- 61225 | Serviços PMS - AGB

(demais filiais seguem o mesmo padrão com prefixo da filial)

### 1.4 Usuários e Permissões

Tabela no Excel: aba "Usuarios"
Perfis:
- admin: acesso total, configura sistema
- controller: vê todas as filiais, abre/fecha ciclo, aprova budgets
- gerente: vê e edita APENAS sua filial vinculada
- diretoria: vê consolidado, aprova versão final

Regra crítica de segurança:
- Gerente logado só vê dados de sua filial
- Budget aprovado fica BLOQUEADO para edição — só controller pode reabrir
- Toda alteração grava em AuditLog: usuário + campo + valor anterior + valor novo + timestamp

---

## MÓDULO 2 — BUDGET

### 2.1 Ciclo Orçamentário

Tabela no Excel: aba "BudgetVersoes"
Campos: id, empresa_id, ano, cenario, status, descricao, aprovado_por, aprovado_em

Cenários possíveis: conservador | realista | agressivo
Status do ciclo: rascunho → em_revisao → aprovado | devolvido

Fluxo obrigatório:
1. Controller abre ciclo (define ano e prazo)
2. Gerentes de cada filial preenchem (status: em_edição)
3. Gerente clica "Enviar para aprovação" (status: em_revisao — trava edição)
4. Controller revisa, pode devolver com comentário ou encaminhar
5. Diretoria aprova (status: aprovado — trava permanente)

### 2.2 TELA DE ENTRADA DE BUDGET — REGRAS COMPLETAS

Esta é a tela central do sistema. É aqui que o gerente orça sua filial.

Layout da tela:
- Header: "Orçamento [ANO] — [FILIAL]" + status badge + usuário
- Abas horizontais: Peças | Serviços | Comissões | Headcount | OPEX
- Área principal: grade de entrada (ver abaixo)
- Rodapé: botão Salvar Rascunho + botão Enviar para Aprovação + info último salvamento

ESTRUTURA DA GRADE DE ENTRADA (aba Peças):

Linha de referência acima (cinza claro, não editável):
Conta Contábil | Real 2023 Jan | Real 2023 Fev | ... | Real 2024 Jan | ... | Real 2024 Dez | Total 2024

Linha de entrada (editável):
Conta Contábil | Jan | Fev | Mar | Abr | Mai | Jun | Jul | Ago | Set | Out | Nov | Dez | Total

Contas que aparecem na aba Peças (por CCU):
BALCÃO (CCU Peças Balcão):
- 311201 VENDA PEÇAS SCANIA
- 311202 VENDA PEÇAS SIMILAR
- 311204 VENDA COMBUSTÍVEIS E LUBRIFICANTES
Subtotal Balcão (calculado)

OFICINA (CCU Peças Oficina):
- 311201 VENDA PEÇAS SCANIA
- 311202 VENDA PEÇAS SIMILAR
- 311204 VENDA COMBUSTÍVEIS E LUBRIFICANTES
Subtotal Oficina (calculado)

GARANTIA (CCU Peças Garantia):
- 311201 VENDA PEÇAS SCANIA
- 311204 VENDA COMBUSTÍVEIS E LUBRIFICANTES
Subtotal Garantia (calculado)

PMS (CCU Peças PMS):
- 3.1.3.10 VENDA PEÇAS SCANIA PMS
- 3.1.4.03 VENDA COMBUST./LUBRIF. EM PMS
Subtotal PMS (calculado)

TOTAL GERAL PEÇAS (soma todos os subtotais — calculado)

Contas que aparecem na aba Serviços (por CCU):
OFICINA (CCU Serviços Oficina):
- 311302 VENDA SERVIÇOS DE TERCEIROS
- 311305 VENDA SERVIÇOS GARANTIA
Subtotal Oficina (calculado)

GARANTIA (CCU Serviços Garantia):
- 311302 VENDA SERVIÇOS DE TERCEIROS
- 311305 VENDA SERVIÇOS GARANTIA
Subtotal Garantia (calculado)

PMS (CCU Serviços PMS):
- 311302 VENDA SERVIÇOS DE TERCEIROS
Subtotal PMS (calculado)

REFORMADORA (apenas filiais que possuem):
- 311302 VENDA SERVIÇOS TERCEIROS (REFORMADORA)
Subtotal Reformadora (calculado)

TOTAL GERAL SERVIÇOS (soma todos — calculado)

Contas na aba Comissões:
- 311501 COMISSÃO PMV
- 311502 COMISSÃO PMS
- 311503 COMISSÃO TOP DEALERS
- 311401 CONECTIVIDADE
TOTAL COMISSÕES (calculado)

Regras de cálculo automático na grade:
- Total coluna = soma dos 12 meses de cada linha
- Subtotal grupo = soma das contas do grupo no mês
- Total geral = soma de todos os grupos
- Campos de total são READONLY — calculados automaticamente em JS ao digitar
- Valores em R$ mil (ex: digitar 2.106 = R$ 2.106.000)

Regras de salvamento:
- Salvar Rascunho: grava na aba BudgetLinhas do Excel sem mudar status
- Enviar para Aprovação: muda status para "em_revisao" e bloqueia edição
- Gravar em AuditLog cada salvamento: usuario, filial, conta, ccu, mes, valor_anterior, valor_novo, timestamp

### 2.3 Sistema de Rateio por Pesos (CRÍTICO)

Esta lógica já existia nas planilhas Pesos_AGB e Pesos_CBA e deve ser preservada.

Conceito:
O valor que o gerente digita é o TOTAL da receita por conta contábil.
O sistema distribui automaticamente esse total entre os CCUs usando PESOS históricos.

Exemplo real (extraído de Pesos_AGB):
Gerente digita: 311201 Balcão = R$ 404.924
Sistema distribui:
- 61211 Peças Balcão: 85,07% = R$ 344.481
- 61212 Peças Oficina: 41,74% = (só para conta oficina)
(pesos calculados com base no histórico real 2024)

Tabela no Excel: aba "PesosRateio"
Campos: filial_id, conta_id, ccu_id, peso, ano_referencia

Pesos extraídos das planilhas (AGB — ano 2024):
311201 → 61211 (Balcão): peso 0.85067
311202 → 61211 (Balcão): peso 0.04027
311204 → 61211 (Balcão): peso 0.10906
311201 → 61212 (Oficina): peso 0.41740
311202 → 61212 (Oficina): peso 0.00635
311204 → 61212 (Oficina): peso 0.15103
311201 → 61213 (Garantia): peso 0.21681
311201 → 61214 (PMS): peso 0.10793
(pesos somam 1.0 por conta dentro da filial)

Quando o budget é salvo:
1. Python pega valor digitado pelo gerente (ex: 311201 total = 500.000)
2. Busca pesos na aba PesosRateio para aquela filial + conta
3. Calcula valor por CCU = valor_total × peso
4. Salva na BudgetLinhas com ccu_id já distribuído

---

## MÓDULO 3 — RECEITAS PÓS-VENDA

### 3.1 Mapa de Vendas (estrutura real das planilhas)

Estrutura do "Mapa de Vendas" das planilhas Template_CBA, Template_AGB etc:

GRUPOS DE RECEITA (por ordem na DRE):

GRUPO 1 — PEÇAS BALCÃO E OFICINA
Linhas:
- RECEITA BRUTA (valor digitado)
- (-) Impostos Sobre Venda (conforme cadastro de impostos por filial)
- (-) Devoluções e Descontos
- = RECEITA LÍQUIDA (calculado: Bruta - Impostos - Devoluções)
- (-) CUSTOS (CPV — custo das peças)
- = LUCRO BRUTO (calculado: Líquida - Custos)
- % Margem Bruta = Lucro Bruto / Receita Líquida

GRUPO 2 — PEÇAS REFORMADORA (apenas filiais com reformadora)
Mesma estrutura do grupo 1

GRUPO 3 — SERVIÇOS OFICINA
- RECEITA BRUTA
- (-) Impostos
- (-) Devoluções
- = RECEITA LÍQUIDA
- (-) CUSTOS (custo dos serviços)
- = LUCRO BRUTO
- % Margem Bruta

GRUPO 4 — SERVIÇOS REFORMADORA (apenas filiais com reformadora)
Mesma estrutura

GRUPO 5 — COMISSÕES
- Comissão PMV (311501)
- Comissão PMS (311502)
- Comissão Top Dealers (311503)
- Total Comissões

TOTAL GERAL:
- Receita Bruta Total = soma de todos os grupos
- Receita Líquida Total
- Lucro Bruto Total
- Margem Bruta Total % = Lucro Bruto Total / Receita Líquida Total

Cálculos obrigatórios (em Python no backend):
receita_liquida = receita_bruta - impostos - devolucoes
lucro_bruto = receita_liquida - custos
margem_pct = (lucro_bruto / receita_liquida) * 100 if receita_liquida > 0 else 0

### 3.2 Conectividade Scania

Receita mensal de conectividade por filial.
Conta: 311401
Entrada: valor mensal por filial (jan a dez)
Sem rateio por CCU — conta direta

---

## MÓDULO 4 — HEADCOUNT

### 4.1 Colaboradores

Tabela no Excel: aba "Colaboradores"
Campos: id, filial_id, ccu_id, nome, cargo, salario_base, admissao, ativo

Cargos identificados nas planilhas:
- Lubrificador I (faixa R$ 4.200 a R$ 4.800)
- Lubrificador II (faixa R$ 4.800 a R$ 5.400)
- Lubrificador III (faixa R$ 5.400 a R$ 6.200)

### 4.2 Folha Orçada

Tabela no Excel: aba "FolhaMensal"
Campos: colaborador_id, versao_budget_id, ano, mes, salario, encargos, beneficios, bonus, hora_extra, total

Cálculo obrigatório (Python):
encargos = salario_base * 0.50  (INSS + FGTS + outros — aproximação 50%)
total_mes = salario + encargos + beneficios + bonus + hora_extra

Impacto automático na DRE:
- total_folha_mes → conta 511001 (Folha de Pagamento)
- encargos → conta 511002 (Encargos Sociais)
- beneficios → conta 511003 (Benefícios)
- Esses valores alimentam automaticamente o OPEX e a DRE — NÃO precisam ser digitados de novo

### 4.3 Hora Extra (extraído da aba "ROV - Momoria Hora Extra")

Memória de cálculo de horas extras por período:
- Registro de horas por colaborador
- Valor calculado com base no salário hora + adicional legal (50% ou 100%)

---

## MÓDULO 5 — OPEX

### 5.1 Despesas Operacionais

Tabela no Excel: aba "BudgetLinhas" (filtrado por contas de despesa 5xxxxx)

Categorias e contas:
PESSOAL (já vem do Headcount automaticamente):
- 511001 Folha de Pagamento
- 511002 Encargos Sociais
- 511003 Benefícios

ADMINISTRATIVO (digitado pelo gerente):
- 512001 Aluguel
- 512002 Energia Elétrica
- 512003 Água e Esgoto
- 512004 Telefone e Internet
- 512010 Serviços de Terceiros
- 512011 Material de Escritório
- 512020 Manutenção e Conservação
- 512030 Seguros
- 512040 Viagens e Representação
- 512050 Treinamentos

TOTAL OPEX = PESSOAL (automático) + ADMINISTRATIVO (digitado)

Regra importante: campo de Pessoal é READONLY no OPEX — vem do Headcount.

### 5.2 CAPEX

Tabela no Excel: aba separada "CAPEX" (criar se não existir)
Campos: descricao, filial_id, valor, mes_previsto, tipo_ativo, depreciacao_anos, status

Status: proposto → aprovado | rejeitado
Somente controller e diretoria aprovam CAPEX

---

## MÓDULO 6 — ANÁLISE

### 6.1 Budget vs Real

Comparativo mensal: valor orçado (BudgetLinhas) vs valor realizado (Realizado)

Cálculos obrigatórios (Python):
variacao_rs = real - budget
variacao_pct = ((real - budget) / budget) * 100 if budget > 0 else 0
atingimento_pct = (real / budget) * 100 if budget > 0 else 0

Cores na tela:
- Verde (#1D9E75): atingimento >= 100% (receita) ou <= 100% (despesa)
- Vermelho (#E24B4A): atingimento < 95% (receita) ou > 105% (despesa)
- Âmbar (#EF9F27): entre 95% e 100%

Visões disponíveis:
- Por filial (linha por filial, colunas jan a dez + total)
- Por conta contábil dentro da filial
- Por CCU dentro da filial
- Consolidado grupo (soma de todas as filiais)

Filtros: ano | mês | filial | conta | CCU

### 6.2 DRE Gerencial

Estrutura obrigatória (baseada no Mapa de Vendas das planilhas):

(+) RECEITA BRUTA
  (-) Impostos sobre vendas
  (-) Devoluções e descontos
= RECEITA LÍQUIDA
  (-) CPV (Custo das Peças e Serviços Vendidos)
= LUCRO BRUTO
  % Margem Bruta = Lucro Bruto / Receita Líquida

  (-) DESPESAS OPERACIONAIS
      (-) Pessoal (folha + encargos + benefícios)
      (-) Administrativo (aluguel, energia, etc.)
= EBITDA
  % Margem EBITDA = EBITDA / Receita Líquida

  (-) Depreciação e Amortização
= EBIT

Visão: Budget | Real | Variação R$ | Variação %
Período: mês selecionado | acumulado ano | projeção

### 6.3 Forecast Dinâmico

Lógica de cálculo:
meses_realizados = número de meses com dado real lançado
media_mensal_real = soma_real_acumulado / meses_realizados
projecao_anual = soma_real_acumulado + (media_mensal_real * (12 - meses_realizados))
desvio_vs_budget = projecao_anual - budget_anual
desvio_pct = (desvio_vs_budget / budget_anual) * 100

---

## REGRAS GERAIS DE INTERFACE

### Formatação de valores
- Todos os valores monetários em R$ mil (ex: 2.106 = R$ 2.106.000)
- Separador decimal: vírgula (padrão BR)
- Separador milhar: ponto (padrão BR)
- Percentuais: uma casa decimal (ex: 34,5%)

### Validações obrigatórias
- Valores negativos não permitidos nas receitas
- Campo obrigatório: filial + conta + mês ao salvar
- Budget não pode ser enviado se alguma aba estiver vazia
- Confirmar antes de enviar para aprovação (modal de confirmação)

### Auditoria (AuditLog)
Gravar SEMPRE que:
- Budget é salvo (rascunho ou envio)
- Status é alterado
- Valor real é lançado
- Usuário é criado ou alterado

Campos: id, usuario, aba_alterada, acao, id_registro, valor_anterior, valor_novo, data_hora

---

## DADOS DE EXEMPLO PARA TESTES

Filial CBA — Budget 2026 — Peças Balcão — 311201:
Jan: 2.106.552 | Fev: 2.062.908 | Mar: 1.881.664 | Abr: 2.044.142
Mai: 2.141.384 | Jun: 2.042.109 | Jul: 2.011.233 | Ago: 2.031.442
Set: 1.978.301 | Out: 1.981.203 | Nov: 1.875.442 | Dez: 1.814.219
Total: 23.970.599

Filial AGB — Budget 2026 — Peças Balcão — 311201:
Jan: 404.924 | Fev: 632.277 | Mar: 769.322 | Abr: 814.123
Mai: 1.098.117 | Jun: 848.610 | Jul: 1.139.637 | Ago: 1.310.061

Folha Orçada — Colaboradores selecionados:
Pedro Rikelmy Lima Ribeiro | Lubrificador III | SPZ | Sal: 5.684,71
Elizangela Pereira da Costa Gomes | Lubrificador I | SNP | Sal: 4.730,38
Carlos Davi Silva Barbosa | Lubrificador I | AGB | Sal: 5.143,64
Giovane Goncalves de Souza | Lubrificador I | CBA | Sal: 4.367,48
Leandro Gabriel Machado | Lubrificador III | SNP | Sal: 4.538,21

---

## INSTRUÇÃO PARA O CLAUDE CODE

Com esta especificação, construa o sistema completo na seguinte ordem:

SPRINT 1 — Fundação (base.html + cadastros):
1. base.html com sidebar completa conforme módulos definidos
2. Rotas de cadastros funcionando com leitura do Excel
3. Telas: empresas, plano de contas, centros de custo, usuários

SPRINT 2 — Budget (tela central):
1. Ciclo orçamentário (abrir/fechar ciclo)
2. Tela de entrada de budget com grade 12 meses × contas × CCUs
3. Histórico de referência (Real 2024) ao lado das células de input
4. Salvamento com AuditLog
5. Fluxo de aprovação (enviar → revisar → aprovar/devolver)

SPRINT 3 — Receitas e Headcount:
1. Mapa de vendas pós-venda (grupos: Peças, Serviços, Comissões)
2. Cálculos automáticos (margem, líquida, lucro bruto)
3. Módulo headcount com cálculo automático de encargos
4. Integração folha → OPEX automático

SPRINT 4 — Análise:
1. Budget vs Real com variações coloridas
2. DRE gerencial dinâmica
3. Forecast automático com projeção anual

Certifique-se de que:
- Gerente só acessa sua filial (passar filial_codigo na sessão)
- Budget aprovado é somente leitura
- Todos os cálculos são feitos em Python no backend (não em JS)
- Interface responsiva e profissional conforme identidade ROV
