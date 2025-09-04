
import os   # inserido para desabilitar verificação de certificado
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait

# ─── VARIÁVEIS DE AMBIENTE ──────────────────────────────────────────────────────
os.environ['WDM_SSL_VERIFY'] = '0'

DEBUGGER_ADDRESS = "127.0.0.1:9222"
URL_DISPENSA = (
    "https://www.tcerj.tc.br/"
    "sigfis-atosjuridicos/site/admin/dispensas-inexigibilidades/dispensas/criar"
)
EXCEL_PATH = r"C:\Users\pedro.naia\OneDrive - MPRJ\Arquivo\Documentos\Projeto_AutoSIGIFIS\cadastro.xlsx" # Caminho do Excel no MPRJ
#EXCEL_PATH = r"C:\Users\pedro\Projeto_AutoSIGIFIS\virtual\cadastro.xlsx" # Caminho do Excel no meu PC
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


def load_all_cfgs(path=EXCEL_PATH, sheet=SHEET_NAME):
    """
    Lê a aba `sheet` do Excel em `path` e retorna uma lista de dicionários,
    um por linha, contendo as variáveis da planilha.
    """
    df = pd.read_excel(path, sheet_name=sheet, dtype=str).fillna("")
    cfg_list = [row.to_dict() for _, row in df.iterrows()]

    for cfg in cfg_list:
        # Defaults para colunas da planilha
        cfg.setdefault('PROCESSO', "")
        cfg.setdefault('VALOR', "")
        cfg.setdefault('CPF_ORDENADOR', "")
        cfg.setdefault('DATA_ATO', "")
        cfg.setdefault('CNPJ_FORNECEDOR', "")
        cfg.setdefault('NOME_FORNECEDOR', "")
        cfg.setdefault('PRAZO_EXECUCAO', "")
        cfg.setdefault('OBJETO', "")
        cfg.setdefault('ANO_EMPENHO', "")
        cfg.setdefault('DATA_EMPENHO', "")
        cfg.setdefault('NUM_EMPENHO', "")
        cfg.setdefault('FILE_PATH', "")
        # Defaults para itens
        cfg.setdefault('NUM_ITEM', ITEM_LOTE_VALUE)
        cfg.setdefault('QTD_ITEM', QTD_ITEM)

        # Ajuste de sufixos para valores monetários
        raw = cfg.get('VALOR') or ""
        cfg['VALOR_EMPENHO'] = cfg.get('VALOR_EMPENHO') or raw
        cfg['VALOR_UNIT'] = cfg.get('VALOR_UNIT') or (raw + "00")

        # ADICIONE ESTA PARTE ABAIXO:
        cfg['COD_UG_SIAFE'] = COD_UG_SIAFE
        cfg['TIPOLOGIA_VALUE'] = TIPOLOGIA_VALUE
        cfg['ITEM_LOTE_VALUE'] = ITEM_LOTE_VALUE
        cfg['FUNDAMENTO_VALUE'] = FUNDAMENTO_VALUE
        cfg['UNID_MEDIDA'] = UNID_MEDIDA
        cfg['ATO_DOCUMENTO'] = ATO_DOCUMENTO
        cfg['TIPO_DOCUMENTO'] = TIPO_DOCUMENTO

    return cfg_list





def create_driver_and_wait():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    # timeout menor e polling mais rápido
    wait = WebDriverWait(driver, 8, poll_frequency=0.2)
    return driver, wait
