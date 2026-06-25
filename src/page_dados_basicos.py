# page_dados_basicos.py

import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from helpers import (
    fill_input, js_select_value, wait_for_page_complete,
    safe_click, swal_click_confirm, confirm_or_warn,
)
from logger import get_logger
from verify import ler_id_dispensa

log = get_logger("dados_basicos")


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

    if "," in s or "." in s:
        s = s.replace(".", ",")
        inteiro, _, frac = s.partition(",")
        frac = (frac + "00")[:2]
        return f"{inteiro},{frac}"

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

    Campos vazios na planilha NÃO derrubam mais o registro: geram WARNING e o
    fluxo continua, registrando exatamente onde houve problema.
    """
    log.info("Preenchendo Dados Basicos | Processo=%s | Fornecedor=%s",
             cfg.get('PROCESSO'), cfg.get('NOME_FORNECEDOR'))

    def get_visible(locator):
        return wait.until(EC.visibility_of_element_located(locator))

    def aviso_se_vazio(chave):
        if not str(cfg.get(chave, "")).strip():
            log.warning("Campo '%s' vazio na planilha para este registro.", chave)
            return True
        return False

    # 1) Processo Administrativo
    fill_input(driver, wait, 'input-text[name="ProcessoAdministrativo"] input', cfg['PROCESSO'])

    # 2) Tipologia
    wrap = get_visible((By.CSS_SELECTOR, 'input-select[name="TipologiaObjetoContratacao"]'))
    sel = wrap.find_element(By.TAG_NAME, 'select')
    js_select_value(driver, sel, config.TIPOLOGIA_VALUE)
    confirm_or_warn(driver, lambda d: sel.get_attribute('value') == config.TIPOLOGIA_VALUE,
                    "Tipologia nao assumiu o valor esperado")

    # 2b) Registro de Preço (campo obrigatório novo) -> "Não"
    wrap = get_visible((By.CSS_SELECTOR, 'input-select[name="registroPreco"]'))
    sel = wrap.find_element(By.TAG_NAME, 'select')
    js_select_value(driver, sel, config.REGISTRO_PRECO_VALUE)
    confirm_or_warn(driver, lambda d: sel.get_attribute('value') == config.REGISTRO_PRECO_VALUE,
                    "Registro de Preco nao assumiu o valor esperado")

    # 3) Valor (DUAS casas decimais)
    valor_norm = _valor_duas_casas(cfg['VALOR'])
    fill_input(driver, wait, 'input-currency[name="Valor"] input', valor_norm)

    # 4) Item/Lote
    wrap = get_visible((By.CSS_SELECTOR, 'input-select[name="TipoLicitacao"]'))
    sel = wrap.find_element(By.TAG_NAME, 'select')
    js_select_value(driver, sel, config.ITEM_LOTE_VALUE)
    confirm_or_warn(driver, lambda d: sel.get_attribute('value') == config.ITEM_LOTE_VALUE,
                    "Item/Lote nao assumiu o valor esperado")

    # 5) Fundamentação Legal
    wrap = get_visible((By.CSS_SELECTOR, 'input-select[name="FundamentoLegal"]'))
    sel = wrap.find_element(By.TAG_NAME, 'select')
    js_select_value(driver, sel, config.FUNDAMENTO_VALUE)
    confirm_or_warn(driver, lambda d: sel.get_attribute('value') == config.FUNDAMENTO_VALUE,
                    "Fundamento Legal nao assumiu o valor esperado")

    # 6) Ordenador (CPF)
    ord_selector = 'app-pessoa-pesquisa-cadastro[name="cpfCnpjOrdenador"] input[name="cpfCnpj"]'
    aviso_se_vazio('CPF_ORDENADOR')
    fill_input(driver, wait, ord_selector, cfg['CPF_ORDENADOR'])
    if str(cfg.get('CPF_ORDENADOR', "")).strip():
        confirm_or_warn(driver, lambda d: d.find_element(By.CSS_SELECTOR, ord_selector)
                        .get_attribute('value').strip() != "", "CPF do ordenador nao foi gravado")

    # 7) Data do Ato
    data_selector = 'input-date[name="DataAto"] input'
    aviso_se_vazio('DATA_ATO')
    fill_input(driver, wait, data_selector, cfg['DATA_ATO'])
    if str(cfg.get('DATA_ATO', "")).strip():
        confirm_or_warn(
            driver,
            lambda d: ('invalid' not in (d.find_element(By.CSS_SELECTOR, data_selector).get_attribute('class') or '').lower())
                      and d.find_element(By.CSS_SELECTOR, data_selector).get_attribute('value').strip() != "",
            "Data do Ato ficou invalida ou vazia (esperado dd/mm/aaaa)")

    # 8) Fornecedor (CNPJ + nome/autofill com fallback)
    forn_cnpj_selector = 'app-pessoa-pesquisa-cadastro[name="fornecedor"] input[name="cpfCnpj"]'
    aviso_se_vazio('CNPJ_FORNECEDOR')
    fill_input(driver, wait, forn_cnpj_selector, cfg['CNPJ_FORNECEDOR'])

    nome_sel = ('app-pessoa-pesquisa-cadastro[name="fornecedor"] '
                'input-text[name="nomeRazaoSocial"] input')

    autofill_ok = confirm_or_warn(
        driver,
        lambda d: d.find_element(By.CSS_SELECTOR, nome_sel).get_attribute('value').strip()
        == cfg['NOME_FORNECEDOR'].strip(),
        "Autofill do nome do fornecedor nao casou; preenchendo manualmente",
        timeout=1.2,  # CPF de pessoa fisica raramente tem autofill; cai rapido para o preenchimento manual
    )
    if not autofill_ok:
        try:
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
            log.info("Fornecedor preenchido manualmente: %s", cfg['NOME_FORNECEDOR'])
        except Exception as e:
            log.warning("Nao foi possivel preencher o nome do fornecedor manualmente: %s", e)

    # 9) Prazo de Execução
    fill_input(driver, wait, 'input-number[name="prazoExecucao"] input', cfg['PRAZO_EXECUCAO'])

    # 10) Objeto
    fill_input(driver, wait, 'input-textarea[name="Objeto"] textarea', cfg['OBJETO'])

    # 11) Salvar
    save_btn = get_visible((By.CSS_SELECTOR, 'button[form="frm"][type="submit"]'))
    safe_click(driver, wait, save_btn)
    wait_for_page_complete(driver, wait)
    log.info("Dados Basicos salvos.")

    # 12) SweetAlert OK
    swal_click_confirm(driver, wait, 'OK', 'Confirmar')
    wait_for_page_complete(driver, wait)

    # 12b) Le o Nº da Dispensa gerado (prova de que salvou de fato)
    dispensa_id = ler_id_dispensa(driver)
    if dispensa_id:
        log.info("Nº Dispensa SIGFIS gerado: %s", dispensa_id)

    # 13) Selecionar aba Itens
    try:
        itens_link = WebDriverWait(driver, 5, poll_frequency=0.2).until(
            EC.presence_of_element_located((By.XPATH, "(//ul[contains(@class,'nav-tabs')]/li)[2]/a"))
        )
        safe_click(driver, wait, itens_link)
        wait_for_page_complete(driver, wait)
    except TimeoutException:
        log.warning("Nao encontrei a aba Itens a partir de Dados Basicos; main.py tentara navegar.")

    return dispensa_id
