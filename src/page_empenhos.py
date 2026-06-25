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


def _resolver_input(driver, modal, labels, css_list):
    """
    Resolve o input do empenho de forma resiliente, SEM depender de id (que o
    Angular renumera: ano ja foi input-number-2 e hoje e input-number-9, etc.).

    Ordem de tentativa:
      1) pelo TEXTO do <label> -> atributo 'for' -> id atual; ou input no mesmo form-group;
      2) por ATRIBUTO estavel do proprio input (type=number, bsdatepicker,
         currencymask, placeholder=000000...), exigindo casar com UM unico elemento.
    Retorna (elemento, origem) ou (None, motivo).
    """
    # 1) por label
    try:
        for lb in modal.find_elements(By.TAG_NAME, "label"):
            txt = (lb.text or "").strip().lower()
            if txt and any(s in txt for s in labels):
                fid = lb.get_attribute("for")
                if fid:
                    els = modal.find_elements(By.ID, fid)
                    if els:
                        return els[0], f"label '{txt}'"
                try:
                    grp = lb.find_element(By.XPATH, "./ancestor::div[contains(@class,'form-group')][1]")
                    inp = grp.find_elements(By.CSS_SELECTOR, "input")
                    if inp:
                        return inp[0], f"label-grupo '{txt}'"
                except Exception:
                    pass
    except Exception as e:
        log.debug("Resolver por label falhou (%s): %s", labels, e)

    # 2) por atributo estavel (exige match unico dentro do modal)
    for css in css_list:
        try:
            els = modal.find_elements(By.CSS_SELECTOR, css)
            if len(els) == 1:
                return els[0], f"atributo '{css}'"
            if len(els) > 1:
                log.debug("CSS '%s' casou %d elementos; ignorando por ambiguidade.", css, len(els))
        except Exception as e:
            log.debug("CSS '%s' falhou: %s", css, e)

    return None, "NAO ENCONTRADO"


def preencher_empenhos(driver, wait, cfg, *args):
    log.info("Preenchendo Empenhos | NE=%s | Ano=%s", cfg.get('NUM_EMPENHO'), cfg.get('ANO_EMPENHO'))

    incluir_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//div[contains(@class,'tab-footer')]//button[contains(normalize-space(.),'Incluir Empenho')]"
    )))
    safe_click(driver, wait, incluir_btn)
    modal = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal.show")))

    # (labels para casar, seletores CSS por atributo estavel, valor)
    plano = [
        (["ano"],
         ["input[type='number']"],
         cfg.get("ANO_EMPENHO", "")),
        (["data"],
         ["input[bsdatepicker]"],
         normaliza_data_empenho(cfg.get("DATA_EMPENHO", ""))),
        (["ug", "siafe", "cód", "cod"],
         ["input[placeholder='000000']"],
         cfg.get("COD_UG_SIAFE", "")),
        (["número", "numero"],
         ["input[autoselectonfocus][type='text']:not([currencymask]):not([placeholder='000000'])"],
         cfg.get("NUM_EMPENHO", "")),
        (["valor"],
         ["input[currencymask]"],
         cfg.get("VALOR_EMPENHO", "")),
    ]

    for labels, css_list, valor in plano:
        campo, origem = _resolver_input(driver, modal, labels, css_list)
        if campo is None:
            log.error("Campo de empenho nao encontrado (%s) - pulando.", labels[0])
            continue
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
            log.debug("Empenho [%s] = %r (via %s)", labels[0], valor, origem)
        except Exception as e:
            log.error("Falha ao preencher empenho '%s': %s", labels[0], e)

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
