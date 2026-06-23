# page_empenhos.py
# -*- coding: utf-8 -*-
import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from helpers import wait_for_page_complete, aguardar_carregamento_final, safe_click, swal_click_confirm
from logger import get_logger

log = get_logger("empenhos")


def normaliza_data_empenho(valor):
    try:
        if not valor:
            return ""
        valor = str(valor).strip()
        if " " in valor:
            valor = valor.split(" ")[0]
        if "-" in valor:
            data = datetime.strptime(valor, "%Y-%m-%d")
            return data.strftime("%d/%m/%Y")
        if "/" in valor and len(valor) == 10:
            return valor
    except Exception:
        pass
    return valor


def _resolver_input(driver, modal, substrings, fallback_id):
    """
    Localiza o input do empenho de forma resiliente:
      1) pelo TEXTO do <label> (estavel) -> atributo 'for' -> id atual do input;
      2) se o label nao tiver 'for', pega o <input> dentro do mesmo form-group;
      3) por ultimo, cai no id posicional antigo (comportamento que ja funcionava).
    Retorna (elemento, origem) onde 'origem' descreve como foi achado (para log).
    """
    try:
        for lb in modal.find_elements(By.TAG_NAME, "label"):
            txt = (lb.text or "").strip().lower()
            if txt and any(s in txt for s in substrings):
                fid = lb.get_attribute("for")
                if fid:
                    els = modal.find_elements(By.ID, fid)
                    if els:
                        return els[0], f"label '{txt}' -> #{fid}"
                try:
                    grp = lb.find_element(By.XPATH, "./ancestor::div[contains(@class,'form-group')][1]")
                    inp = grp.find_elements(By.CSS_SELECTOR, "input")
                    if inp:
                        return inp[0], f"label '{txt}' -> form-group"
                except Exception:
                    pass
    except Exception as e:
        log.debug("Erro na resolucao por label %s: %s", substrings, e)

    els = driver.find_elements(By.ID, fallback_id)
    if els:
        return els[0], f"fallback #{fallback_id}"
    return None, "NAO ENCONTRADO"


def preencher_empenhos(driver, wait, cfg, *args):
    log.info("Preenchendo Empenhos | NE=%s | Ano=%s", cfg.get('NUM_EMPENHO'), cfg.get('ANO_EMPENHO'))

    incluir_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//div[contains(@class,'tab-footer')]//button[contains(normalize-space(.),'Incluir Empenho')]"
    )))
    safe_click(driver, wait, incluir_btn)
    modal = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal.show")))

    # (substrings do label em minusculo, id de fallback, valor)
    plano = [
        (["ano"],                        "input-number-2",     cfg.get("ANO_EMPENHO", "")),
        (["data"],                       "input-date-4",       normaliza_data_empenho(cfg.get("DATA_EMPENHO", ""))),
        (["ug", "siafe", "cód", "cod"],  "input-text-mask-0",  cfg.get("COD_UG_SIAFE", "")),
        (["número", "numero"],           "input-text-mask-1",  cfg.get("NUM_EMPENHO", "")),
        (["valor"],                      "input-currency-3",   cfg.get("VALOR_EMPENHO", "")),
    ]

    for substrings, fallback_id, valor in plano:
        campo, origem = _resolver_input(driver, modal, substrings, fallback_id)
        if campo is None:
            log.error("Campo de empenho nao encontrado (%s) - pulando.", substrings[0])
            continue
        if origem.startswith("fallback"):
            log.warning("Empenho '%s' resolvido por id posicional (%s) - confira o layout.",
                        substrings[0], fallback_id)
        try:
            campo.clear()
            campo.click()
            for c in str(valor):
                campo.send_keys(c)
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('blur', {bubbles:true}));",
                campo
            )
            log.debug("Empenho [%s] = %r (via %s)", substrings[0], valor, origem)
        except Exception as e:
            log.error("Falha ao preencher empenho '%s': %s", substrings[0], e)

    salvar_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//div[contains(@class,'modal-footer')]//button[@type='submit' and contains(@class,'btn-outline-primary')]"
    )))
    safe_click(driver, wait, salvar_btn)

    if swal_click_confirm(driver, wait, 'OK', 'Confirmar'):
        log.debug("SweetAlert2 OK clicado.")
    else:
        time.sleep(1)

    wait_for_page_complete(driver, wait)
    aguardar_carregamento_final(driver, wait)
    log.info("Empenho incluido.")
