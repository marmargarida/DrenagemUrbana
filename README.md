# Drenagem Urbana – Simulações e Extração de Dados com SWMM

## 1. Contexto
Este repositório reúne os arquivos, scripts e relatórios gerados a partir de simulações hidrológicas e hidráulicas no **Storm Water Management Model (SWMM)**.  
O objetivo é analisar o comportamento do sistema de drenagem urbana em diferentes cenários de chuva, impermeabilização e parâmetros do solo, além de consolidar bases de dados para uso em **modelos supervisionados de aprendizado de máquina**.

---

## 2. Plano de execução

### (i) Simulação de cenários urbanos no SWMM
Foram rodados **8 cenários distintos**, variando:
- **Duração da chuva**: 5, 20, 60 minutos  
- **Nível de impermeabilização**: 75%, 87,5%  
- **Curve Number (CN)**: 85 (lotes), 98 (ruas)  

Para cada cenário, foram gerados:
- Arquivos `.rpt` e `.out` (resultados brutos do SWMM)  
- Gráficos individuais das curvas de profundidade em nós selecionados  
- Arquivos `.csv` com estatísticas hidrológicas por sub-bacia  
- Classificação hidráulica das bocas de lobo: **Normal, Sobrecarga ou Transbordamento**

---

### (ii) Construção da base de dados consolidada
A partir das simulações, foi criada uma tabela onde cada linha representa uma **sub-bacia**, contendo:

**Variáveis geométricas e hidrológicas (X):**
- Área da sub-bacia (m²)  
- Percentual de impermeabilização (%)  
- Curve Number (CN)  
- Tipo da sub-bacia (lote ou rua)  
- Comprimento do escoamento superficial (m)  
- Declividade média do terreno (%)  
- Duração da chuva (min)  
- Volume total de precipitação (mm)  
- Profundidade máxima (m)  
- Tempo até o pico (min)  
- Razão profundidade/altura da caixa de inspeção (adimensional)  

**Variáveis edáficas (quando simuladas via Green-Ampt):**
- Condutividade hidráulica do solo saturado (Ksat, mm/h)  
- Sucção na frente de infiltração (Ψ, mm)  
- Umidade inicial do solo (θinit, fração)  
- Profundidade efetiva da camada de solo (m)  
- Textura do solo (arenoso, franco, argiloso etc.)  

**Variável-alvo (y):**
- Classe operacional da boca de lobo: **Normal / Sobrecarga / Transbordamento**

O resultado final é o arquivo **`df_final.csv`**, consolidando todas as colunas explicativas e a classificação alvo.

---

## 3. Estrutura dos scripts e saídas

### Scripts principais
- **`scenarios_peak_depth_analysis.py`** → analisa profundidade em um único cenário  
- **`scenarios_global_peak_analysis.py`** → consolida estatísticas e curvas entre cenários  
- **`scenarios_input_audit.py`** → audita arquivos de entrada (.csv)  
- **`scenarios_data_extractor.py`** → extrai e organiza variáveis hidrológicas, hidráulicas e edáficas  

### Saídas geradas
- Estatísticas em `.csv` (máximo, mínimo, média, desvio padrão)  
- Séries temporais em `.png` ou `.pdf`  
- Relatórios de auditoria em `.txt`  
- Bases estruturadas em `.csv` e `.parquet`  

---

## 4. Estrutura de pastas

/scenarios
├── scenarioXX.rpt # Arquivos originais do SWMM
├── scenarioXX_peak_statistics.csv
├── scenarioXX_depth_timeseries.png / .pdf
├── scenarioXX.csv # Dados estruturados
├── scenarioXX.parquet
├── scenarioXX_audit_report.txt
...
/outputs
├── all_scenarios_peak_statistics.csv
├── all_scenarios_max_curves.pdf
scenarios_peak_depth_analysis.py
scenarios_global_peak_analysis.py
scenarios_input_audit.py
scenarios_data_extractor.py
