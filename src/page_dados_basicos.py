# page_dados_basicos.py

import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from helpers import fill_input, js_select_value, wait_for_page_complete, safe_click, swal_click_confirm

def _valor_duas_casas(valor_raw: str) -> str:
    """
    Normaliza para DUAS casas decimais com vírgula.
    Exemplos:
      '125,90' -> '125,90'
      '125.90' -> '125,90'
      '12590'  -> '125,90'
      '12'     -> '12,00'
    """
    if not valor_raw:
        return ""
    s = str(valor_raw).strip()

    # se veio com separador decimal, normaliza para vírgula
    if "," in s or "." in s:
        s = s.replace(".", ",")
        inteiro, _, frac = s.partition(",")
        frac = (frac + "00")[:2]
        return f"{inteiro},{frac}"

    # só dígitos: insere vírgula 2 casas à esquerda
    dig = "".join(ch for ch in s if ch.isdigit())
    if not dig:
        return ""
    if len(dig) == 1:
        return f"0,0{dig}"
    if len(dig) == 2:
        return f"0,{dig}"
    return f"{dig[:-2]},{dig[-2:]}"

def preencher_dados_basicos(driver, wait, cfg):
    """
    Preenche todos os campos da aba 'Dados Básicos' usando somente CSS selectors
    e, ao final, avança para a aba 'Itens'.
    """

    # ===== Helpers locais rápidos =====
    short_wait = WebDriverWait(driver, 3, poll_frequency=0.2)

    def get_visible(locator):
        return wait.until(EC.visibility_of_element_located(locator))

    # 1) Processo Administrativo
    fill_input(
        driver, wait,
        'input-text[name="ProcessoAdministrativo"] input',
        cfg['PROCESSO']
    )

    # 2) Tipologia
    wrap = get_visible((By.CSS_SELECTOR, 'input-select[name="TipologiaObjetoContratacao"]'))
    sel  = wrap.find_element(By.TAG_NAME, 'select')
    js_select_value(driver, sel, config.TIPOLOGIA_VALUE)
    short_wait.until(lambda d: sel.get_attribute('value') == config.TIPOLOGIA_VALUE)

    # 3) Valor (DUAS casas decimais)
    valor_norm = _valor_duas_casas(cfg['VALOR'])
    fill_input(driver, wait, 'input-currency[name="Valor"] input', valor_norm)

    # 4) Item/Lote
    wrap = get_visible((By.CSS_SELECTOR, 'input-select[name="TipoLicitacao"]'))
    sel  = wrap.find_element(By.TAG_NAME, 'select')
    js_select_value(driver, sel, config.ITEM_LOTE_VALUE)
    short_wait.until(lambda d: sel.get_attribute('value') == config.ITEM_LOTE_VALUE)

    # 5) Fundamentação Legal
    wrap = get_visible((By.CSS_SELECTOR, 'input-select[name="FundamentoLegal"]'))
    sel  = wrap.find_element(By.TAG_NAME, 'select')
    js_select_value(driver, sel, config.FUNDAMENTO_VALUE)
    short_wait.until(lambda d: sel.get_attribute('value') == config.FUNDAMENTO_VALUE)

    # 6) Ordenador (CPF)
    ord_selector = 'app-pessoa-pesquisa-cadastro[name="cpfCnpjOrdenador"] input[name="cpfCnpj"]'
    fill_input(driver, wait, ord_selector, cfg['CPF_ORDENADOR'])
    short_wait.until(lambda d: d.find_element(By.CSS_SELECTOR, ord_selector)
                     .get_attribute('value').strip() != "")

    # 7) Data do Ato
    data_selector = 'input-date[name="DataAto"] input'
    fill_input(driver, wait, data_selector, cfg['DATA_ATO'])
    short_wait.until(lambda d: d.find_element(By.CSS_SELECTOR, data_selector)
                     .get_attribute('value').strip() != "")

    # 8) Fornecedor (CNPJ + nome/autofill com fallback rápido)
    forn_cnpj_selector = (
        'app-pessoa-pesquisa-cadastro[name="fornecedor"] input[name="cpfCnpj"]'
    )
    fill_input(driver, wait, forn_cnpj_selector, cfg['CNPJ_FORNECEDOR'])

    nome_sel = (
        'app-pessoa-pesquisa-cadastro[name="fornecedor"] '
        'input-text[name="nomeRazaoSocial"] input'
    )

    try:
        short_wait.until(
            lambda d: d.find_element(By.CSS_SELECTOR, nome_sel)
                      .get_attribute('value').strip() == cfg['NOME_FORNECEDOR'].strip()
        )
    except TimeoutException:
        print("[⚠] Timeout ao aguardar nome do fornecedor. Digitando manualmente.")
        campo_nome = get_visible((By.CSS_SELECTOR, nome_sel))
        driver.execute_script("arguments[0].focus();", campo_nome)
        try:
            campo_nome.clear()
        except Exception:
            pass
        campo_nome.send_keys(cfg['NOME_FORNECEDOR'])
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));",
            campo_nome
        )
        print(f"[✔] Fornecedor preenchido manualmente: {cfg['NOME_FORNECEDOR']}")

    # 9) Prazo de Execução
    fill_input(
        driver, wait,
        'input-number[name="prazoExecucao"] input',
        cfg['PRAZO_EXECUCAO']
    )

    # 10) Objeto
    fill_input(
        driver, wait,
        'input-textarea[name="Objeto"] textarea',
        cfg['OBJETO']
    )

    # 11) Salvar
    save_btn = get_visible((By.CSS_SELECTOR, 'button[form="frm"][type="submit"]'))
    safe_click(driver, wait, save_btn)
    wait_for_page_complete(driver, wait)

    # 12) SweetAlert OK (Swal API → instantâneo; fallback: botão)
        # SweetAlert OK (centralizado em helper)
    if not swal_click_confirm(driver, wait, 'OK', 'Confirmar'):
        pass
    wait_for_page_complete(driver, wait)

    # 13) Selecionar aba Itens
    # (localiza a 2ª aba por XPATH, como no seu original, mas clica via JS)
    itens_link = WebDriverWait(driver, 5, poll_frequency=0.2).until(
        EC.presence_of_element_located((By.XPATH, "(//ul[contains(@class,'nav-tabs')]/li)[2]/a"))
    )
    safe_click(driver, wait, itens_link)
    wait_for_page_complete(driver, wait)
