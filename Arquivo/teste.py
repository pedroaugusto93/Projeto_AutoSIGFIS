from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time

# ——— Configurações ———
DEBUGGER_ADDRESS   = "127.0.0.1:9222"
URL_DISPENSA       = (
    "https://www.tcerj.tc.br/"
    "sigfis-atosjuridicos/site/admin/dispensas-inexigibilidades/dispensas/criar"
)

# ——— Dados de exemplo ———
PROCESSO           = "20.22.0001.0004203.2025-19"
TIPOLOGIA_VALUE    = "30"
VALOR              = "24000,00"
ITEM_LOTE_VALUE    = "1"    # 1 = Item, 2 = Lote
FUNDAMENTO_VALUE   = "61"

CPF_ORDENADOR      = "010.902.667-58"
DATA_ATO           = "06/07/2025"

CNPJ_FORNECEDOR    = "48855116000139"
NOME_FORNECEDOR    = "ANDRADE SOLUCOES EM BENS E SERVICOS LTDA"
PRAZO_EXECUCAO     = "30"
OBJETO             = "Contratação de serviços de apoio técnico-administrativo."

# … demais constantes (itens, documentos, empenhos) …

def wait_for_page_complete(driver, wait, extra_delay=0.5):
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    try:
        spinner = (By.CSS_SELECTOR, ".loading-overlay, .spinner, .ng-star-inserted")
        wait.until(EC.invisibility_of_element_located(spinner))
    except:
        pass
    time.sleep(extra_delay)

# ——— Setup Selenium em modo “attach” ———
opts    = Options()
opts.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)
service = Service(ChromeDriverManager().install())
driver  = webdriver.Chrome(service=service, options=opts)
wait    = WebDriverWait(driver, 15)

try:
    # Acessa o formulário
    driver.get(URL_DISPENSA)
    wait_for_page_complete(driver, wait)

    # Página 1 — Dados Básicos —

    # 1) Processo Administrativo
    proc_inp = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, 'input-text[name="ProcessoAdministrativo"] input'
    )))
    driver.execute_script("arguments[0].scrollIntoView(true);", proc_inp)
    proc_inp.clear()
    proc_inp.send_keys(PROCESSO)

    # 2) Tipologia
    tpl_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'input-select[name="TipologiaObjetoContratacao"]'
    )))
    tpl_sel = tpl_wrap.find_element(By.TAG_NAME, "select")
    driver.execute_script("arguments[0].scrollIntoView(true);", tpl_wrap)
    driver.execute_script(
        "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
        tpl_sel, TIPOLOGIA_VALUE
    )

    # 3) Valor
    val_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'input-currency[name="Valor"]'
    )))
    val_inp = val_wrap.find_element(By.TAG_NAME, "input")
    driver.execute_script("arguments[0].scrollIntoView(true);", val_inp)
    val_inp.send_keys(Keys.CONTROL, "a")
    val_inp.send_keys(VALOR)

    # 4) Dispensa por item ou lote
    lote_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'input-select[name="TipoLicitacao"]'
    )))
    lote_sel = lote_wrap.find_element(By.TAG_NAME, "select")
    driver.execute_script("arguments[0].scrollIntoView(true);", lote_wrap)
    driver.execute_script(
        "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
        lote_sel, ITEM_LOTE_VALUE
    )

    # 5) Fundamentação Legal
    fund_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'input-select[name="FundamentoLegal"]'
    )))
    fund_sel = fund_wrap.find_element(By.TAG_NAME, "select")
    driver.execute_script("arguments[0].scrollIntoView(true);", fund_wrap)
    driver.execute_script(
        "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
        fund_sel, FUNDAMENTO_VALUE
    )

    # 6) Ordenador Responsável — só CPF (nome virá automático)
    ord_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        'app-pessoa-pesquisa-cadastro[name="cpfCnpjOrdenador"]'
    )))
    ord_inp = ord_wrap.find_element(By.CSS_SELECTOR, 'input[name="cpfCnpj"]')
    driver.execute_script("arguments[0].scrollIntoView(true);", ord_inp)
    ord_inp.clear()
    ord_inp.send_keys(CPF_ORDENADOR)

    # 7) Data do Ato
    date_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        'input-date[name="DataAto"]'
    )))
    date_inp = date_wrap.find_element(By.TAG_NAME, "input")
    driver.execute_script("arguments[0].scrollIntoView(true);", date_inp)
    date_inp.clear()
    date_inp.send_keys(DATA_ATO)

    # 8) Fornecedor/Executante — CNPJ + Razão Social
    forn_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        'app-pessoa-pesquisa-cadastro[name="fornecedor"]'
    )))
    # 8.1) CNPJ do fornecedor
    forn_cnpj = forn_wrap.find_element(By.CSS_SELECTOR, 'input[name="cpfCnpj"]')
    driver.execute_script("arguments[0].scrollIntoView(true);", forn_cnpj)
    forn_cnpj.clear()
    forn_cnpj.send_keys(CNPJ_FORNECEDOR, Keys.TAB)

    # 8.2) Nome/Razão Social do fornecedor
    forn_nome = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        'input-text[name="nomeRazaoSocial"] input'
    )))
    driver.execute_script("arguments[0].scrollIntoView(true);", forn_nome)
    forn_nome.clear()
    forn_nome.send_keys(NOME_FORNECEDOR)


    # 9) Prazo de Execução
    prazo_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'input-number[name="prazoExecucao"]'
    )))
    prazo_inp = prazo_wrap.find_element(By.TAG_NAME, "input")
    driver.execute_script("arguments[0].scrollIntoView(true);", prazo_inp)
    prazo_inp.clear()
    prazo_inp.send_keys(PRAZO_EXECUCAO)

    # 10) Objeto
    obj_wrap = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'input-textarea[name="Objeto"]'
    )))
    obj_inp = obj_wrap.find_element(By.TAG_NAME, "textarea")
    driver.execute_script("arguments[0].scrollIntoView(true);", obj_inp)
    obj_inp.clear()
    obj_inp.send_keys(OBJETO)

    # 11) Salvar e avançar
    next_btn = wait.until(EC.element_to_be_clickable((
        By.XPATH, "//button[contains(.,'Salvar') and contains(.,'Próximo')]"
    )))
    next_btn.click()
    wait_for_page_complete(driver, wait)

    # … página 2, 3, 4 conforme já refatorado …

finally:
    driver.quit()
