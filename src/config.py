import os   # inserido para desabilitar verificação de certificado
import re
import socket
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
URL_CONSULTA = (
    "https://www.tcerj.tc.br/"
    "sigfis-atosjuridicos/site/admin/dispensas-inexigibilidades/dispensas/consulta"
)
def _primeiro_caminho_existente(candidatos):
    """Retorna o primeiro caminho que existe (trabalho ou home office)."""
    for c in candidatos:
        if c and os.path.isfile(c):
            return c
    # nenhum existe ainda: devolve o primeiro como padrao (a leitura avisara o erro)
    return candidatos[0]


# Caminhos possiveis do cadastro.xlsx (ora no trabalho, ora em home office).
# A variavel de ambiente SIGFIS_EXCEL_PATH, se definida, tem prioridade sobre todos.
EXCEL_PATHS = [
    os.path.join(os.path.dirname(__file__), "cadastro.xlsx"),
    r"C:\Users\pedro\OneDrive\Documentos\Projeto_AutoSIGFIS\src\cadastro.xlsx",
]                                        # PC pessoal (home office)

EXCEL_PATH = os.environ.get("SIGFIS_EXCEL_PATH") or _primeiro_caminho_existente(EXCEL_PATHS)
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
# Se True, registro sem documento (FILE_PATH vazio/ausente) NAO conta como 100%/completo.
DOCUMENTO_OBRIGATORIO = True
# IRREVERSIVEL: se True, apos preencher tudo o robo clica em "Enviar ao TCE".
# So envia registros 100% OK (conferidos e com documento).
ENVIAR_AO_TCE = True
# Pasta onde salvar os recibos em PDF (apos enviar ao TCE). Varia por maquina:
# edite o caminho abaixo OU defina a variavel de ambiente SIGFIS_RECIBO_DIR.
RECIBO_DIR = os.environ.get(
    "SIGFIS_RECIBO_DIR",
    r"C:\Users\pedro\OneDrive\Documentos\Projeto_AutoSIGFIS\recibos"
)
# Pasta onde salvar os recibos baixados (pesquisa) e o PDF unico do lote.
RECIBOS_LOTE_DIR = os.environ.get(
    "SIGFIS_RECIBOS_LOTE_DIR",
    os.path.join(os.path.dirname(RECIBO_DIR) or ".", "recibos_lote")
)

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


def _norm_data_br(valor):
    """Converte datas variadas para dd/mm/aaaa.
    O Excel as vezes entrega a celula de data como '2026-06-15 00:00:00' (ISO + hora),
    e o bsdatepicker do SIGFIS so aceita dd/mm/aaaa -> sem isso aparece 'Invalid date'."""
    s = str(valor or "").strip()
    if not s:
        return ""
    s = s.split(" ")[0]  # descarta parte de hora, se houver
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)        # ISO: aaaa-mm-dd
    if m:
        return f"{int(m.group(3)):02d}/{int(m.group(2)):02d}/{m.group(1)}"
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)  # dd/mm/aaaa ou dd-mm-aaaa
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    return s


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
        cfg.setdefault('NUM_ITEM', str(NUM_ITEM))  # default "1" se a coluna for removida

        # Datas -> dd/mm/aaaa (evita "Invalid date" quando o Excel entrega data com hora)
        cfg['DATA_ATO'] = _norm_data_br(cfg.get('DATA_ATO'))
        cfg['DATA_EMPENHO'] = _norm_data_br(cfg.get('DATA_EMPENHO'))

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


def _porta_aberta(host, porta, timeout=1.5):
    try:
        with socket.create_connection((host, int(porta)), timeout=timeout):
            return True
    except OSError:
        return False


def create_driver_and_wait():
    host, _, porta = DEBUGGER_ADDRESS.partition(":")
    if not _porta_aberta(host, porta):
        log.error(
            "Nao consegui conectar ao Chrome em %s.\n"
            "  >> O Chrome precisa estar ABERTO em modo debug ANTES de rodar o script.\n"
            "  >> Feche TODAS as janelas do Chrome e, num PowerShell, rode:\n"
            "     & \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" "
            "--remote-debugging-port=9222 --user-data-dir=\"C:\\ChromeDebugProfile\"\n"
            "  >> Faca login no SIGFIS nessa janela e rode o script de novo.",
            DEBUGGER_ADDRESS,
        )
        raise RuntimeError(f"Chrome em modo debug nao encontrado em {DEBUGGER_ADDRESS}")

    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    # timeout menor e polling mais rápido
    wait = WebDriverWait(driver, 8, poll_frequency=0.2)
    log.debug("Driver conectado ao Chrome em %s", DEBUGGER_ADDRESS)
    return driver, wait
