# page_itens.py

import config
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from helpers import wait_for_page_complete, js_select_value, fill_input


def preencher_itens(driver, wait, cfg):
    # 1) Abre modal de novo item
    wait.until(EC.element_to_be_clickable((
        By.XPATH, "//button[contains(.,'Incluir Novo Item')]"
    ))).click()

    # 2) Posição (campo padrão funciona para o wrapper)
    wait.until(EC.visibility_of_element_located((
        By.NAME, "posicao"
    ))).send_keys(cfg.get('NUM_ITEM'))

    # 3) Descrição (usa <textarea> interno)
    fill_input(
        driver, wait,
        'input-textarea[name="Descricao"] textarea',
        cfg.get('OBJETO')
    )

    # 4) Quantidade (input interno)
    qtd_el = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR, 'input-number[name="quantidade"] input'
    )))
    driver.execute_script("arguments[0].scrollIntoView(true);", qtd_el)
    qtd_el.clear()
    qtd_el.send_keys(cfg.get('QTD_ITEM'))
    wait.until(lambda d: qtd_el.get_attribute('value') == cfg.get('QTD_ITEM'))

    # 5) Unidade de medida (select Angular)
    wrap = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, 'input-select[name="unidadeMedida"]'
    )))
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
    vu_el.send_keys(cfg['VALOR_UNIT'])
    # → NÃO ficamos esperando pelo atributo value formatado

    # 7) Salvar e avançar
    save_btn = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        ".modal-footer > .actions.ml-0 > button.btn-outline-primary[type='submit']"
    )))
    driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", save_btn)

    # 8) Confirmar SweetAlert
    ok_btn = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, "button.swal2-confirm"
    )))
    driver.execute_script("arguments[0].click();", ok_btn)

    # 9) Aguarda o modal desaparecer
    wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal.show")))
    wait_for_page_complete(driver, wait)

