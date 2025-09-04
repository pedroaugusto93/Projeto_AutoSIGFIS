
import config
from helpers import wait_for_page_complete
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.common.exceptions import TimeoutException
import time

# Função para aguardar carregamento Angular
def aguardar_carregamento_final(driver, wait):
    try:
        wait.until_not(EC.presence_of_element_located((
            By.CSS_SELECTOR, ".throbber, .ngx-loading, .loading"
        )))
        print("[✔] Página carregada e pronta.")
    except TimeoutException:
        print("[⚠] Timeout: carregamento demorou demais.")

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

def preencher_empenhos(driver, wait, cfg, *args):
    incluir_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//div[contains(@class,'tab-footer')]//button[contains(normalize-space(.),'Incluir Empenho')]"
    )))
    driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", incluir_btn)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal.show")))

    campos = [
        ("input-number-2", cfg.get("ANO_EMPENHO", "")),
        ("input-date-4", normaliza_data_empenho(cfg.get("DATA_EMPENHO", ""))),
        ("input-text-mask-0", cfg.get("COD_UG_SIAFE", "")),
        ("input-text-mask-1", cfg.get("NUM_EMPENHO", "")),
        ("input-currency-3", cfg.get("VALOR_EMPENHO", "")),
    ]

    for seletor, valor in campos:
        try:
            campo = wait.until(EC.element_to_be_clickable((By.ID, seletor)))
            campo.clear()
            campo.click()
            for c in str(valor):
                campo.send_keys(c)
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));"
                "arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));",
                campo
            )
            print(f"[Empenho] Preenchido: {seletor} = {valor}")
        except Exception as e:
            print(f"ERRO: Não foi possível preencher o campo '{seletor}': {e}")

    # Clique no botão Salvar do modal
    salvar_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//div[contains(@class,'modal-footer')]//button[@type='submit' and contains(@class,'btn-outline-primary')]"
    )))
    driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", salvar_btn)

    # Espera e clica no OK do SweetAlert2, se aparecer
    try:
        ok_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "button.swal2-confirm.swal2-styled"
        )))
        driver.execute_script("arguments[0].click();", ok_btn)
        print("SweetAlert2 OK clicado!")
    except Exception:
        print("SweetAlert2 OK não apareceu ou já foi fechado.")
        time.sleep(1)

    wait_for_page_complete(driver, wait)

    # Espera adicional de estabilidade do Angular
    print("[DEBUG] Aguardando carregamento completo final antes de enviar...")
    aguardar_carregamento_final(driver, wait)
