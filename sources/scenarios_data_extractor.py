import pandas as pd
import os
import re
import networkx as nx
from collections import OrderedDict
import traceback
import time

base_path = r"C:\Users\wpcal\Dropbox\Arquivos Pacheco 02_05_2022\Programacao\Ambiente_VirtualCS\Marcella\cenarios"
cenarios = [f"cenario_{i:02d}" for i in range(1, 12)]

# Dicionário com os totais de precipitação por série temporal (mm)
PRECIPITACOES = {
    'TS1': 13.9,  # cenario_01 (5 min)
    'TS2': 31.9,  # cenario_02 (20 min)
    'TS3': 48.8,  # cenario_03,09 (50 min)
    'TS4': 48.6,  # cenario_04 (60 min)
    'TS5': 57.9,  # cenario_05,10 (90 min)
    'TS6': 54.3,  # cenario_06,11 (90 min)
    'TS7': 65.5  # cenario_07,08 (180 min)
}

# Mapeamento de cenários para séries temporais
CENARIO_TS_MAP = {
    'cenario_01': 'TS1',
    'cenario_02': 'TS2',
    'cenario_03': 'TS3',
    'cenario_04': 'TS4',
    'cenario_05': 'TS5',
    'cenario_06': 'TS6',
    'cenario_07': 'TS7',
    'cenario_08': 'TS7',
    'cenario_09': 'TS3',
    'cenario_10': 'TS5',
    'cenario_11': 'TS6'
}

# Dicionário de unidades (atualizado com NOME em maiúsculo)
unidades = {
    'NOME': '-',
    'AREA': 'm²',
    'DECL': '%',
    'DURC': 'min',
    'VCHU': 'mm',
    'IMPV': '%',
    'TIPO': '-',
    'DIAM': 'm',
    'LESC': 'm',
    'PMAX': 'm',
    'VAZT': 'm³/s',
    'VTOT': '10^6 L',
    'RAZA': '-',
    'KSAT': 'mm/h',
    'ALTC': 'm',
    'CLBO': '-',
    'VSUP': 'm³',
    'VINF': 'm³',
    'VGER': 'm³',
    'PSUP': '-',
    'PINF': '-',
    'VINI': 'mm',
    'VEVA': 'mm',
    'VRET': 'mm',
    'VSTO': 'mm',
    'ERRO': '%',
}


def parse_duration(conteudo):
    """Extrai END_TIME do conteúdo do .inp e converte para minutos"""
    if not isinstance(conteudo, str):
        return 0

    match = re.search(r'END_TIME\s+(\d{1,2}:\d{2}:\d{2})', conteudo, re.IGNORECASE)
    if match:
        time_str = match.group(1)
        try:
            h, m, s = map(int, time_str.split(':'))
            return h * 60 + m + (1 if s >= 30 else 0)
        except:
            return 0
    return 0


def ler_secao_arquivo_com_ordem(caminho, secao):
    """Lê uma seção mantendo a ordem original dos IDs"""
    dados = OrderedDict()
    try:
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
            leitura = False
            for linha in f:
                linha = linha.strip()

                # Início da seção
                if f"[{secao.upper()}]" in linha.upper():
                    leitura = True
                    continue

                # Fim da seção
                if leitura and (linha.startswith("[") or not linha):
                    break

                # Linha de dados
                if leitura and not linha.startswith(";"):
                    partes = linha.split()
                    if partes:
                        id = partes[0]
                        dados[id] = partes  # Armazena todos os campos
    except Exception as e:
        print(f"Erro ao ler {secao}: {str(e)}")
    return dados


def ler_duracao_chuva(caminho_inp):
    """Lê o arquivo .inp e extrai a duração total"""
    try:
        with open(caminho_inp, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            return parse_duration(conteudo)
    except Exception as e:
        print(f"Erro ao ler duração: {str(e)}")
        return 0

def determinar_tipo_sub_bacia(nome):
    """Determina o tipo de sub-bacia com base no código"""
    if not isinstance(nome, str):
        return 'rua'
    codigo = nome.split('_')[0].upper() if '_' in nome else nome.upper()
    return 'lote' if codigo in ['B', 'P', 'E', 'G', 'S', 'BL', 'TS'] else 'rua'


def construir_mapeamento_b_p_g(caminho_inp):
    """Constrói o mapeamento completo entre B, P e G mantendo a ordem"""
    # Dicionários ordenados para armazenar relações
    b_para_p = OrderedDict()
    p_para_b = {}  # Mapeamento reverso P → B
    p_para_g = OrderedDict()
    g_para_diam = OrderedDict()

    # 1. Ler seção [SUBCATCHMENTS] mantendo ordem
    subcatchments = ler_secao_arquivo_com_ordem(caminho_inp, 'SUBCATCHMENTS')
    for b_id, valores in subcatchments.items():
        if len(valores) >= 3:
            p_outlet = valores[2]
            b_para_p[b_id] = p_outlet
            # Criar mapeamento reverso (um P pode ter várias bacias)
            if p_outlet not in p_para_b:
                p_para_b[p_outlet] = []
            p_para_b[p_outlet].append(b_id)

    # 2. Ler seção [CONDUITS] mantendo ordem
    conduits = ler_secao_arquivo_com_ordem(caminho_inp, 'CONDUITS')
    grafo = nx.DiGraph()
    for g_id, valores in conduits.items():
        if len(valores) >= 3:
            p_from = valores[1]
            p_to = valores[2]
            grafo.add_edge(p_from, p_to, conduit=g_id)

    # 3. Ler seção [XSECTIONS] mantendo ordem
    xsections = ler_secao_arquivo_com_ordem(caminho_inp, 'XSECTIONS')
    for g_id, valores in xsections.items():
        if len(valores) >= 3:
            diam = valores[2]
            try:
                g_para_diam[g_id] = float(diam)
            except ValueError:
                g_para_diam[g_id] = None

    # 4. Construir mapeamento P->G
    for p_node in grafo.nodes:
        successors = list(grafo.successors(p_node))
        if successors:
            next_node = successors[0]
            p_para_g[p_node] = grafo.edges[(p_node, next_node)]['conduit']

    # 5. Construir mapeamento final B->G
    b_para_g = OrderedDict()
    for b_id in b_para_p:  # Mantém a ordem original
        p_outlet = b_para_p[b_id]
        if p_outlet in p_para_g:
            b_para_g[b_id] = p_para_g[p_outlet]

    return b_para_g, g_para_diam, b_para_p, p_para_b

def ler_altura_caixa_junctions(caminho_inp):
    """Lê a altura da caixa de inspeção (3ª coluna) da seção JUNCTIONS"""
    alturas = {}
    try:
        with open(caminho_inp, 'r', encoding='utf-8', errors='ignore') as f:
            leitura = False
            for linha in f:
                linha = linha.strip()

                if len(partes) >= 3:
                    node_id = partes[0]
                    altura = float(partes[2])  # certo!

                if "[JUNCTIONS]" in linha.upper():
                    leitura = True
                    continue

                if leitura:
                    if linha.startswith("[") or not linha or linha.startswith(";"):
                        break

                    partes = linha.split()
                    if len(partes) >= 3:
                        node_id = partes[0]
                        try:
                            altura = float(partes[2])
                            alturas[node_id] = altura
                        except ValueError:
                            pass
    except Exception as e:
        print(f"Erro ao ler altura da caixa: {str(e)}")
    return alturas

def ler_storage_volumes(caminho_rpt):
    vsup_dict = OrderedDict()
    vinf_dict = OrderedDict()
    try:
        with open(caminho_rpt, 'r', encoding='utf-8', errors='ignore') as f:
            leitura = False
            for linha in f:
                linha = linha.strip()

                if "Storage Volume Summary" in linha:
                    leitura = True
                    continue
                if leitura and linha.startswith('['):
                    break
                if leitura and (not linha or '-' in linha or linha.startswith(';')):
                    continue

                partes = linha.split()
                if len(partes) >= 6:
                    node = partes[0]
                    vsup = partes[3].replace('*', '')
                    vinf = partes[4].replace('*', '')
                    vsup_dict[node] = float(vsup)
                    vinf_dict[node] = float(vinf)
    except Exception as e:
        print(f"Erro ao ler Storage Volume Summary: {str(e)}")
    return vsup_dict, vinf_dict

def calcular_variaveis_volume_simples(vsup_dict, vinf_dict):
    dados = []
    for node in vsup_dict:
        vsup = vsup_dict.get(node, 0.0)
        vinf = vinf_dict.get(node, 0.0)
        vger = vsup

def ler_storage_volume_summary(caminho_rpt):
    """
    Lê a seção [Subcatchment Runoff Summary] do .rpt e calcula:
    VSUP, VINF, VGER, PSUP, PINF, VINI, VEVA, VRET, VSTO, ERRO por sub-bacia.
    """
    dados = OrderedDict()
    try:
        with open(caminho_rpt, 'r', encoding='utf-8', errors='ignore') as f:
            leitura = False
            for linha in f:
                linha = linha.strip()

                if "Subcatchment Runoff Summary" in linha:
                    leitura = True
                    continue
                if leitura and linha.startswith('['):
                    break
                if leitura and (not linha or '-' in linha or linha.startswith(";")):
                    continue

                partes = linha.split()
                if len(partes) >= 9:
                    try:
                        id_ = partes[0]
                        vini = float(partes[1])  # Volume inicial
                        veva = float(partes[2])  # Evaporação
                        vret = float(partes[3])  # Retenção
                        vinf = float(partes[4])  # Infiltração
                        vsup = float(partes[5])  # Escoamento
                        vsto = float(partes[6])  # Volume final
                        vger = float(partes[7])  # Total gerado
                        erro = float(partes[8])  # % de erro
                        psup = vsup / vger * 100 if vger > 0 else 0
                        pinf = vinf / vger * 100 if vger > 0 else 0

                        dados[id_] = {
                            'VINI': vini,
                            'VEVA': veva,
                            'VRET': vret,
                            'VINF': vinf,
                            'VSUP': vsup,
                            'VSTO': vsto,
                            'VGER': vger,
                            'ERRO': erro,
                            'PSUP': psup,
                            'PINF': pinf
                        }
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Erro ao ler Subcatchment Runoff Summary: {str(e)}")
    return dados


def ler_rpt_ordenado(caminho_rpt, secao, coluna):
    """Lê seções de relatório mantendo a ordem e tratando espaçamentos e cabeçalhos irregulares"""
    dados = OrderedDict()
    try:
        with open(caminho_rpt, 'r', encoding='utf-8', errors='ignore') as f:
            leitura = False
            cabecalho_processado = False
            for linha in f:
                linha = linha.strip()

                # Iniciar leitura ao encontrar a seção
                if secao.upper() in linha.upper():
                    leitura = True
                    cabecalho_processado = False
                    continue

                # Parar ao encontrar próxima seção
                if leitura and linha.startswith('['):
                    break

                if leitura and not cabecalho_processado:
                    if "Node" in linha and "Type" in linha:
                        cabecalho_processado = True
                    continue

                if leitura and cabecalho_processado:
                    if not linha or '-' in linha or linha.startswith(';'):
                        continue

                    partes = linha.split()
                    if len(partes) > coluna:
                        id_ = partes[0]
                        valor = partes[coluna].replace('*', '')
                        dados[id_] = valor
    except Exception as e:
        print(f"Erro ao ler {secao}: {str(e)}")
    return dados

def ler_valor_rpt(caminho_rpt, secao, coluna_desejada, id_alvo):
    try:
        with open(caminho_rpt, 'r', encoding='utf-8', errors='ignore') as f:
            leitura = False
            cabecalho_processado = False
            for linha in f:
                linha = linha.strip()

                if secao.upper() in linha.upper():
                    leitura = True
                    cabecalho_processado = False
                    continue

                if leitura and linha.startswith('['):
                    break

                if leitura and not cabecalho_processado:
                    if "Node" in linha and "Type" in linha:
                        cabecalho_processado = True
                    continue

                if leitura and cabecalho_processado:
                    if not linha or '-' in linha or linha.startswith(';'):
                        continue
                    partes = linha.split()
                    if len(partes) > coluna_desejada and partes[0] == id_alvo:
                        return partes[coluna_desejada].replace('*', '')
    except Exception as e:
        print(f"Erro ao ler {secao} para {id_alvo}: {str(e)}")
    return None


def criar_registro(id, valores, b_para_g, g_para_diam, junctions, infiltration, durc, vchu):
    """Cria um registro mantendo a ordem original"""
    # Obter diâmetro através do mapeamento
    diam = None
    if id in b_para_g:
        g_id = b_para_g[id]
        diam = g_para_diam.get(g_id)

    # Determinar tipo de sub-bacia
    tipo = determinar_tipo_sub_bacia(id)

    # Obter valores específicos da seção
    area = impv = decl = lesc = altc = ksat = None

    # Se for uma sub-bacia (começa com 'B')
    if id.startswith('B') and len(valores) >= 8:
        try:
            area = float(valores[3])  # 4ª coluna (Area)
            impv = float(valores[4])  # 5ª coluna (%Imperv)
            lesc = float(valores[5])  # 6ª coluna (Width - LESC)
            decl = float(valores[6])  # 7ª coluna (%Slope)
        except (ValueError, IndexError):
            pass

    # Altura da caixa (ALTC) vem da 3ª coluna da seção [JUNCTIONS]
    if id in junctions and len(junctions[id]) >= 3:
        try:
            altc = float(junctions[id][2])  # 3ª coluna: altura da caixa
        except (ValueError, IndexError):
            pass

    # KSAT vem da infiltração
    if id in infiltration and len(infiltration[id]) >= 2:
        try:
            ksat = float(infiltration[id][1])  # KSAT é o 2º parâmetro
        except (ValueError, IndexError):
            pass

    return {
        'NOME': id,
        'AREA': area,
        'DECL': decl,
        'DURC': durc,
        'VCHU': vchu,
        'IMPV': impv,
        'TIPO': tipo,
        'DIAM': diam,
        'LESC': lesc,
        'PMAX': None,
        'VAZT': None,
        'VTOT': None,
        'KSAT': ksat,
        'ALTC': altc,
        'RAZA': None,
        'CLBO': None,
        'VSUP': None,  # ← Volume superficial
        'VINF': None,  # ← Volume infiltrado
        'VGER': None,  # ← Volume geral
        'PSUP': None,  # ← Percentual superficial
        'PINF': None  # ← Percentual infiltrado
    }


def calcular_raza_clbo_para_df(df, b_para_p, node_depth, junctions):
    """Preenche as colunas ALTC, RAZA e CLBO no DataFrame"""
    for index, row in df.iterrows():
        b_id = row['NOME']
        p_node = b_para_p.get(b_id.upper())

        if not p_node:
            continue

        try:
            # 1. ALTC diretamente da seção JUNCTIONS
            altc = None
            if p_node in junctions:
                partes = junctions[p_node]
                if len(partes) >= 3:
                    altc = float(partes[2])

            # 2. PMAX já carregado do RPT
            pmax_str = node_depth.get(p_node)
            pmax = float(pmax_str) if pmax_str else None

            # 3. Cálculo da razão
            raza = clbo = None
            if altc and altc > 0 and pmax is not None:
                raza = pmax / altc
                clbo = (
                    "Normal" if raza < 0.7 else
                    "Sobrecarga" if raza < 1.0 else
                    "Transbordamento"
                )

            df.at[index, 'ALTC'] = altc
            df.at[index, 'RAZA'] = raza
            df.at[index, 'CLBO'] = clbo
        except:
            pass  # Silencia erro para não travar todo o loop

    # Preencher VSUP, VINF, VGER, PSUP, PINF
    for index, row in df.iterrows():
        try:
            vsup = row.get('VTOT')
            vger = row.get('VCHU')
            if vsup is not None and pd.notna(vsup):
                vsup_m3 = float(vsup) * 1000  # VTOT está em 10⁶ L → m³
                vger_m3 = float(vger) * float(row.get('AREA', 0)) / 1000  # mm·m² → L → m³
                vinf = vger_m3 - vsup_m3

                psup = vsup_m3 / vger_m3 if vger_m3 > 0 else None
                pinf = vinf / vger_m3 if vger_m3 > 0 else None

                df.at[index, 'VSUP'] = vsup_m3
                df.at[index, 'VINF'] = vinf
                df.at[index, 'VGER'] = vger_m3
                df.at[index, 'PSUP'] = psup
                df.at[index, 'PINF'] = pinf
        except Exception:
            continue
    return df  # ← Fora do for e do try



def processar_cenario(cenario):
    try:
        print(f"\nIniciando processamento: {cenario}")
        caminho_inp = os.path.join(base_path, f"{cenario}.inp")
        caminho_rpt = os.path.join(base_path, f"{cenario}.rpt")

        # 1. Obter valores globais
        ts_id = CENARIO_TS_MAP.get(cenario)
        vchu = round(PRECIPITACOES.get(ts_id, 0.0), 2)
        durc = ler_duracao_chuva(caminho_inp)
        alturas_caixa = ler_altura_caixa_junctions(caminho_inp)

        # 2. Construir mapeamento B->G->DIAM mantendo ordem
        b_para_g, g_para_diam, b_para_p, p_para_b = construir_mapeamento_b_p_g(caminho_inp)
        print(f"  Mapeamento construído: {len(b_para_p)} bacias para nós P")

        # 3. Processar seções principais mantendo ordem
        subcatchments = ler_secao_arquivo_com_ordem(caminho_inp, 'SUBCATCHMENTS')
        junctions = ler_secao_arquivo_com_ordem(caminho_inp, 'JUNCTIONS')
        infiltration = ler_secao_arquivo_com_ordem(caminho_inp, 'INFILTRATION')
        print(f"  Seções lidas: {len(subcatchments)} subcatchments, {len(junctions)} junctions")

        # 4. Processar relatórios (.rpt) se existirem
        node_depth = OrderedDict()
        node_inflow = OrderedDict()
        node_volume = OrderedDict()

        if os.path.exists(caminho_rpt):
            print(f"  Processando relatório: {caminho_rpt}")
            # CORREÇÃO: Colunas ajustadas conforme especificado
            node_depth = ler_rpt_ordenado(caminho_rpt, 'Node Depth Summary', 3)  # 4ª coluna: Maximum Depth (PMAX)
            node_inflow = ler_rpt_ordenado(caminho_rpt, 'Node Inflow Summary', 3)  # 4ª coluna: Maximum Total Inflow (VAZT)
            node_volume = ler_rpt_ordenado(caminho_rpt, 'Node Inflow Summary', 6)  # 7ª coluna: Total Inflow Volume (VTOT)
            print(f"  Dados extraídos: {len(node_depth)} nós de profundidade, {len(node_inflow)} nós de vazão")
        else:
            print(f"  Aviso: Arquivo .rpt não encontrado para {cenario}")

        # 5. Construir registros na ordem do .inp
        registros = []

        # Processar bacias (SUBCATCHMENTS)
        for b_id, valores in subcatchments.items():
            registro = criar_registro(b_id, valores, b_para_g, g_para_diam, junctions, infiltration, durc, vchu)

            p_node = b_para_p.get(b_id)
            if p_node:
                pmax = ler_valor_rpt(caminho_rpt, "Node Depth Summary", 3, p_node)
                vzt = ler_valor_rpt(caminho_rpt, "Node Inflow Summary", 3, p_node)
                vtot = ler_valor_rpt(caminho_rpt, "Node Inflow Summary", 6, p_node)

                registro['PMAX'] = pmax
                registro['VAZT'] = vzt
                registro['VTOT'] = vtot

            registros.append(registro)

        # Processar junções (JUNCTIONS) não processadas
        for j_id, valores in junctions.items():
            if j_id not in subcatchments:
                registro = criar_registro(j_id, valores, b_para_g, g_para_diam, junctions, infiltration, durc, vchu)

                # Se é um nó outlet, atribuir valores do relatório
                if j_id in p_para_b:
                    registro['PMAX'] = node_depth.get(j_id)
                    registro['VAZT'] = node_inflow.get(j_id)
                    registro['VTOT'] = node_volume.get(j_id)

                registros.append(registro)

        # 6. Criar DataFrame
        df = pd.DataFrame(registros)
        print(f"  DataFrame criado com {len(df)} registros")
        calcular_raza_clbo_para_df(df, b_para_p, node_depth, junctions)

        # 7. Inserir variáveis de volume de armazenamento (VSUP, VINF, VGER, PSUP, PINF)
        storage_data = ler_storage_volume_summary(caminho_rpt)
        for index, row in df.iterrows():
            node_id = row['NOME']
            if node_id in storage_data:
                for var in ['VSUP', 'VINF', 'VGER', 'PSUP', 'PINF']:
                    df.at[index, var] = storage_data[node_id][var]

        # Cálculo de RAZA e CLBO
        calcular_raza_clbo_para_df(df, b_para_p, node_depth, junctions)

        # Leitura do resumo hidrológico por sub-bacia
        summary_data = ler_storage_volume_summary(caminho_rpt)

        # Inserção das variáveis adicionais no DataFrame
        for index, row in df.iterrows():
            nome = row['NOME']
            if nome in summary_data:
                valores = summary_data[nome]
                for var in ['VSUP', 'VINF', 'VGER', 'PSUP', 'PINF', 'VINI', 'VEVA', 'VRET', 'VSTO', 'ERRO']:
                    df.at[index, var] = valores.get(var, None)

        # 8. Garantir todas as colunas necessárias
        colunas_necessarias = [
            'NOME', 'AREA', 'DECL', 'DURC', 'VCHU', 'IMPV', 'TIPO',
            'DIAM', 'LESC', 'PMAX', 'VAZT', 'VTOT', 'RAZA', 'KSAT',
            'ALTC', 'CLBO', 'VSUP', 'VINF', 'VGER', 'PSUP', 'PINF',
            'VINI', 'VEVA', 'VRET', 'VSTO', 'ERRO'
        ]

        # Adicionar colunas faltantes
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = None

        # Ordenar colunas
        df = df[colunas_necessarias]

        # 9. Salvar resultados
        csv_path = os.path.join(base_path, f"{cenario}.csv")
        parquet_path = os.path.join(base_path, f"{cenario}.parquet")

        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        df.to_csv(csv_path, index=False, encoding='utf-8')
        df.to_parquet(parquet_path, index=False)

        # 10. Gerar relatório de conferência
        relatorio = f"Relatório de Conferência - {cenario}\n"
        relatorio += "-" * 70 + "\n"
        relatorio += "| Código Variável | 1º valor          | Quantidade de valores | Unidade   | Nº colunas vazias |\n"
        relatorio += "-" * 70 + "\n"

        for coluna in df.columns:
            
            valor_bruto = df[coluna].iloc[0]
            if pd.isna(valor_bruto):
                primeiro_valor = "VAZIO"
            elif isinstance(valor_bruto, float):
                primeiro_valor = f"{valor_bruto:.4f}"
            else:
                primeiro_valor = str(valor_bruto)

            qtd_valores = df[coluna].count()
            qtd_vazias = len(df) - qtd_valores
            unidade = unidades.get(coluna, 'desconhecida')

            linha = f"| {coluna:<15} | {primeiro_valor:<18} | {qtd_valores:<21} | {unidade:<8} | {qtd_vazias:<17} |\n"
            relatorio += linha

        relatorio_path = os.path.join(base_path, f"{cenario}_relatorio_conferencia.txt")
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        print(f"📄 Relatório gerado: {relatorio_path}")

        print(f"✅ {cenario} processado com sucesso!")
        return df

    except Exception as e:
        print(f"❌ Erro em {cenario}: {str(e)}")
        traceback.print_exc()
        return None


# Execução principal
if __name__ == "__main__":
    for cenario in cenarios:
        try:
            print(f"\n{'=' * 50}")
            print(f"Processando cenário: {cenario}")
            print(f"{'=' * 50}")

            # Processar cenário
            df = processar_cenario(cenario)

            if df is not None:
                # Pequena pausa para garantir que o arquivo foi fechado
                time.sleep(1)

        except Exception as e:
            print(f"Falha crítica no cenário {cenario}: {str(e)}")
            continue