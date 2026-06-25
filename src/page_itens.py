# page_itens.py

import re
import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from helpers import wait_for_page_complete, js_select_value, fill_input, safe_click, swal_click_confirm, confirm_or_warn
from logger import get_logger

log = get_logger("itens")


def valor_quatro_casas(valor_raw: str) -> str:
    """
    Converte o VALOR humano para o formato com 4 casas decimais e virgula que o
    campo de Valor Unitario do SIGFIS espera. Le o valor direto (sem depender de
    forma 'so digitos' nem de divisao por 100).
      '462.14'   -> '462,1400'
      '1109.1'   -> '1109,1000'
      '1.234,56' -> '1234,5600'  (separador de milhar e ignorado)
      '100'      -> '100,0000'
    """
    if not valor_raw:
        return ""
    s = str(valor_raw).strip()
    sep = max(s.rfind(","), s.rfind("."))   # ultimo separador = decimal
    if sep >= 0:
        inteiro = re.sub(r"\D", "", s[:sep])
        frac = re.sub(r"\D", "", s[sep + 1:])
    else:
        inteiro, frac = re.sub(r"\D", "", s), ""
    inteiro = inteiro.lstrip("0") or "0"
    frac = (frac + "0000")[:4]
    return f"{inteiro},{frac}"


def preencher_itens(driver, wait, cfg):
    log.info("Preenchendo Itens | Item=%s | Qtd=%s", cfg.get('NUM_ITEM'), cfg.get('QTD_ITEM'))

    # 1) Abre modal de novo item (botao so habilita apos salvar os Dados Basicos)
    safe_click(driver, wait, (By.XPATH, "//button[contains(.,'Incluir Novo Item')]"))

    # 2) Posição (campo com name/id 'posicao', estavel)
    pos_el = wait.until(EC.visibility_of_element_located((By.NAME, "posicao")))
    pos_el.send_keys(cfg.get('NUM_ITEM'))

    # 3) Descrição (textarea interno do wrapper Angular, ancorado por name)
    fill_input(driver, wait, 'input-textarea[name="Descricao"] textarea', cfg.get('OBJETO'))

    # 4) Quantidade
    qtd_el = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input-number[name="quantidade"] input')))
    driver.execute_script("arguments[0].scrollIntoView(true);", qtd_el)
    qtd_el.clear()
    qtd_el.send_keys(cfg.get('QTD_ITEM'))
    confirm_or_warn(driver, lambda d: qtd_el.get_attribute('value') == cfg.get('QTD_ITEM'),
                    "Quantidade nao assumiu o valor esperado")

    # 5) Unidade de medida (select Angular)
    wrap = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input-select[name="unidadeMedida"]')))
    sel = wrap.find_element(By.TAG_NAME, "select")
    driver.execute_script("arguments[0].scrollIntoView(true);", wrap)
    js_select_value(driver, sel, config.UNID_MEDIDA)
    confirm_or_warn(driver, lambda d: sel.get_attribute("value") == config.UNID_MEDIDA,
                    "Unidade de medida nao assumiu o valor esperado")

    # 6) Valor unitário (4 casas decimais) — assume quantidade = 1 (unitario = total)
    vu_el = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR, 'input-currency[name="ValorUnitario"] input'
    )))
    driver.execute_script("arguments[0].scrollIntoView(true);", vu_el)
    vu_el.clear()
    valor_formatado = valor_quatro_casas(cfg.get('VALOR')) or "0,0000"
    log.debug("Valor unitario formatado: %s", valor_formatado)
    vu_el.send_keys(valor_formatado)
    # garante que o Angular/currencymask registre o valor (recalcula o Preço Total)
    driver.execute_script(
        "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('blur', {bubbles:true}));",
        vu_el
    )
    confirm_or_warn(driver, lambda d: (vu_el.get_attribute('value') or '').strip() != "",
                    "Valor unitario ficou vazio apos digitar")

    # 7) Salvar e avançar
    save_btn = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        ".modal-footer > .actions.ml-0 > button.btn-outline-primary[type='submit']"
    )))
    safe_click(driver, wait, save_btn)

    # 8) Confirmar SweetAlert
    swal_click_confirm(driver, wait, 'OK', 'Confirmar')

    # 9) Aguarda o modal desaparecer
    wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal.show")))
    wait_for_page_complete(driver, wait)
    log.info("Item incluido.")
