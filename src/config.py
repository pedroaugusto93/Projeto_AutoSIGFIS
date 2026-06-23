import os   # inserido para desabilitar verificação de certificado
import unicodedata
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from helpers import norm_money_digits
from logger import get_logger

log = get_logger("config")

# ─── VARIÁVEIS DE AMBIENTE ──────────────────────────────────────────────────────
os.environ['WDM_SSL_VERIFY'] = '0'

DEBUGGER_ADDRESS = "127.0.0.1:9222"
URL_DISPENSA = (
    "https://www.tcerj.tc.br/"
    "sigfis-atosjuridicos/site/admin/dispensas-inexigibilidades/dispensas/criar"
)
EXCEL_PATH = os.environ.get("SIGFIS_EXCEL_PATH", r"C:\Users\pedro\OneDrive\Documentos\Projeto_AutoSIGFIS\src\cadastro.xlsx") # Caminho do Excel no MPRJ "
#EXCEL_PATH = os.environ.get("SIGFIS_EXCEL_PATH", r"C:\Users\pedro\Projeto_AutoSIGIFIS\Projeto_AutoSIGFIS\src\cadastro.xlsx") # Caminho do Excel no meu PC
SHEET_NAME = "Sheet1" # Nome da aba do Excel que contém as configurações

# ─── CONSTANTES FIXAS ───────────────────────────────────────────────────────────
TIPOLOGIA_VALUE = "30"
ITEM_LOTE_VALUE = "1"
FUNDAMENTO_VALUE = "61"
QTD_ITEM = "1"
UNID_MEDIDA = "37"
COD_UG_SIAFE = "100100"
ATO_DOCUMENTO = "1"
TIPO_DOCUMENTO = "5"
NUM_ITEM = 1
REGISTRO_PRECO_VALUE = "false"   # "Registro de Preço" = Não (campo obrigatório novo)

# ─── MAPEAMENTO DE COLUNAS (planilha -> chave usada no código) ──────────────────
# A planilha do MPRJ usa nomes que divergem do código (ex.: 'data_ato' vs 'DATA_ATO',
# 'CNPJ_CPF_FORNECEDOR' vs 'CNPJ_FORNECEDOR'). Sem esse de-para, o código lê "" e trava.
# A comparação é feita ignorando maiúsculas/minúsculas, acentos e espaços.
COLUMN_ALIASES = {
    "PROCESSO":        ["processo"],
    "VALOR":           ["valor"],
    "CNPJ_FORNECEDOR": ["cnpj_fornecedor", "cnpj_cpf_fornecedor", "cpf_cnpj_fornecedor", "cnpj"],
    "NOME_FORNECEDOR": ["nome_fornecedor"],
    "PRAZO_EXECUCAO":  ["prazo_execucao"],
    "OBJETO":          ["objeto"],
    "ANO_EMPENHO":     ["ano_empenho"],
    "DATA_EMPENHO":    ["data_empenho"],
    "NUM_EMPENHO":     ["num_empenho", "numero_empenho"],
    "CPF_ORDENADOR":   ["cpf_ordenador", "autoridade_cpf"],   # confirmado: CPF do ordenador (Dr. Leandro)
    "DATA_ATO":        ["data_ato"],
    "FILE_PATH":       ["file_path", "filepath", "arquivo", "caminho_arquivo"],
    "NUM_ITEM":        ["num_item", "item"],
    "QTD_ITEM":        ["qtd_item", "quantidade"],
}


def _canon(s: str) -> str:
    """Normaliza um nome de coluna para comparação (minúsculo, sem acento, sem espaço)."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower().replace(" ", "_")


def _remap_columns(row: dict) -> dict:
    """Copia os valores das colunas da planilha para as chaves canônicas do código."""
    out = dict(row)  # mantém as chaves originais também
    canon_lookup = {_canon(k): k for k in row.keys()}
    for canonical, aliases in COLUMN_ALIASES.items():
        # se já existe valor sob a chave canônica, não sobrescreve
        if str(out.get(canonical, "")).strip():
            continue
        for alias in aliases:
            origem = canon_lookup.get(_canon(alias))
            if origem is not None and str(row[origem]).strip():
                out[canonical] = row[origem]
                if _canon(origem) != _canon(canonical):
                    log.debug("Coluna mapeada: '%s' -> '%s'", origem, canonical)
                break
    return out


def load_all_cfgs(path=EXCEL_PATH, sheet=SHEET_NAME):
    """
    Lê a aba `sheet` do Excel em `path` e retorna uma lista de dicionários,
    um por linha, com as chaves já normalizadas para os nomes esperados pelo código.
    """
    log.info("Lendo planilha: %s (aba %s)", path, sheet)
    df = pd.read_excel(path, sheet_name=sheet, dtype=str).fillna("")
    log.debug("Colunas encontradas: %s", list(df.columns))
    cfg_list = [_remap_columns(row.to_dict()) for _, row in df.iterrows()]

    for i, cfg in enumerate(cfg_list, start=1):
        # Defaults para colunas da planilha
        for k in ('PROCESSO', 'VALOR', 'CPF_ORDENADOR', 'DATA_ATO', 'CNPJ_FORNECEDOR',
                  'NOME_FORNECEDOR', 'PRAZO_EXECUCAO', 'OBJETO', 'ANO_EMPENHO',
                  'DATA_EMPENHO', 'NUM_EMPENHO', 'FILE_PATH'):
            cfg.setdefault(k, "")
        cfg.setdefault('QTD_ITEM', QTD_ITEM)

        # Valores monetários: SEMPRE derivam de VALOR (ignora placeholders da planilha).
        # Antes, um "1" residual na coluna VALOR_EMPENHO virava R$ 0,01 no empenho.
        raw = cfg.get('VALOR') or ""
        cfg['VALOR_EMPENHO'] = norm_money_digits(raw)
        cfg['VALOR_UNIT']    = norm_money_digits(raw)

        # Constantes fixas (sobrepõem qualquer placeholder vindo da planilha)
        cfg['COD_UG_SIAFE'] = COD_UG_SIAFE
        cfg['TIPOLOGIA_VALUE'] = TIPOLOGIA_VALUE
        cfg['ITEM_LOTE_VALUE'] = NUM_ITEM
        cfg['FUNDAMENTO_VALUE'] = FUNDAMENTO_VALUE
        cfg['UNID_MEDIDA'] = UNID_MEDIDA
        cfg['ATO_DOCUMENTO'] = ATO_DOCUMENTO
        cfg['TIPO_DOCUMENTO'] = TIPO_DOCUMENTO

        # Aviso preventivo: campos obrigatórios vazios após o de-para
        faltando = [k for k in ('PROCESSO', 'CPF_ORDENADOR', 'DATA_ATO',
                                'CNPJ_FORNECEDOR', 'NOME_FORNECEDOR') if not str(cfg.get(k, "")).strip()]
        if faltando:
            log.warning("Registro %d: campos vazios na planilha -> %s", i, ", ".join(faltando))

    log.info("Registros carregados: %d", len(cfg_list))
    return cfg_list


def create_driver_and_wait():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    # timeout menor e polling mais rápido
    wait = WebDriverWait(driver, 8, poll_frequency=0.2)
    log.debug("Driver conectado ao Chrome em %s", DEBUGGER_ADDRESS)
    return driver, wait
