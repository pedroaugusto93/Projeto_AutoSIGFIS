# page_itens.py

import config
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from helpers import wait_for_page_complete, js_select_value, fill_input, safe_click, swal_click_confirm


def formatar_valor_quatro_decimais(valor_raw: str) -> str:
    """
    Converte um valor tipo '125,90' ou '125.90' para formato com quatro decimais '125,9000'.
    Remove separadores de milhar e garante separador decimal vírgula.
    """
    if not valor_raw:
        return ""
    s = str(valor_raw).strip().replace(".", ",")
    # Divide parte inteira e decimal
    if "," in s:
        inteiro, decimal = s.split(",", 1)
    else:
        inteiro, decimal = s, ""
    # Garante 4 casas decimais
    decimal = (decimal + "0000")[:4]
    return f"{inteiro},{decimal}"


def preencher_itens(driver, wait, cfg):
    # 1) Abre modal de novo item
    safe_click(driver, wait, (By.XPATH, "//button[contains(.,'Incluir Novo Item')]"))

    # 2) Posição (campo padrão funciona para o wrapper)
    wait.until(EC.visibility_of_element_located((By.NAME, "posicao"))).send_keys(cfg.get('NUM_ITEM'))

    # 3) Descrição (usa <textarea> interno)
    fill_input(driver, wait, 'input-textarea[name="Descricao"] textarea', cfg.get('OBJETO'))

    # 4) Quantidade (input interno)
    qtd_el = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input-number[name="quantidade"] input')))
    driver.execute_script("arguments[0].scrollIntoView(true);", qtd_el)
    qtd_el.clear()
    qtd_el.send_keys(cfg.get('QTD_ITEM'))
    wait.until(lambda d: qtd_el.get_attribute('value') == cfg.get('QTD_ITEM'))

    # 5) Unidade de medida (select Angular)
    wrap = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input-select[name="unidadeMedida"]')))
    sel = wrap.find_element(By.TAG_NAME, "select")
    driver.execute_script("arguments[0].scrollIntoView(true);", wrap)
    js_select_value(driver, sel, config.UNID_MEDIDA)
    wait.until(lambda d: sel.get_attribute("value") == config.UNID_MEDIDA)

    # 6) Valor unitário (input interno do currency)
    vu_el = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR, 'input-currency[name="ValorUnitario"] input'
    )))
    driver.execute_script("arguments[0].scrollIntoView(true);", vu_el)
    vu_el.clear()

    # Corrige escala decimal (divide por 100 para alinhar com comportamento do SIGFIS)
    try:
        raw_valor = cfg['VALOR_UNIT']
        # Remove tudo que não for número nem vírgula/ponto
        val = str(raw_valor).strip().replace(".", "").replace(",", ".")
        num = float(val)
        num_scaled = num / 100  # desloca vírgula duas casas à esquerda
        valor_formatado = f"{num_scaled:.4f}".replace(".", ",")  # 4 casas decimais
    except Exception:
        valor_formatado = "0,0000"

    vu_el.send_keys(valor_formatado)


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
