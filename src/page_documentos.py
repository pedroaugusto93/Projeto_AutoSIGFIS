# page_documentos.py
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from helpers import wait_for_page_complete, js_select_value, safe_click, swal_click_confirm

def preencher_documentos(driver, wait, cfg):
    short_wait = WebDriverWait(driver, 4, poll_frequency=0.2)

    def js_click(el):
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)

    # (1) Incluir Documento
    incluir_btn = wait.until(EC.presence_of_element_located((
        By.XPATH, "//div[contains(@class,'tab-footer')]//button[contains(.,'Incluir Documento')]"
    )))
    safe_click(driver, wait, incluir_btn)

    # (2) Modal aberto
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "modal-container[role='dialog']")))

    # (3) Ato (input-select[name='tipo'])
    ato_wrap = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='tipo']")))
    ato_select = ato_wrap.find_element(By.TAG_NAME, "select")
    js_select_value(driver, ato_select, cfg.get("ATO_DOCUMENTO"))

    # (4) Tipo de Documento (input-select[name='TipoDocumento'])
    tipo_wrap = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='TipoDocumento']")))
    tipo_select = tipo_wrap.find_element(By.TAG_NAME, "select")
    js_select_value(driver, tipo_select, cfg.get("TIPO_DOCUMENTO"))

    # (5) Upload do arquivo
    file_path = cfg.get("FILE_PATH")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    upload = wait.until(EC.presence_of_element_located((
        By.XPATH, "//modal-container//input[@type='file']"
    )))
    upload.send_keys(file_path)

    # Aguarda o nome aparecer em algum input de preview dentro do modal
    base = os.path.basename(file_path).lower()
    try:
        short_wait.until(lambda d: d.execute_script("""
            const b = arguments[0];
            const scope = document.querySelector('modal-container');
            if (!scope) return false;
            const inputs = Array.from(scope.querySelectorAll("input[type='text'], input[readonly], input[id^='input-upload-']"));
            return inputs.some(i => (i.value || '').toLowerCase().includes(b));
        """, base))
    except TimeoutException:
        pass
    print(f"[✔] Upload do arquivo '{file_path}' realizado com sucesso.")

    # (6) Salvar no modal
    salvar_btn = wait.until(EC.presence_of_element_located((
        By.XPATH, "//div[contains(@class,'modal-footer')]//button[@type='submit' and contains(@class,'btn-outline-primary')]"
    )))
    safe_click(driver, wait, salvar_btn)

    # (7) Espera pós-salvar
    wait_for_page_complete(driver, wait)

    # (8) SweetAlert OK (instantâneo via API; fallback no botão)

    if not swal_click_confirm(driver, wait, 'OK', 'Confirmar'):

        try:
            WebDriverWait(driver, 3, poll_frequency=0.2).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.swal2-container.swal2-shown, div.swal2-popup.swal2-modal'))
            )
        except TimeoutException:
            pass

    wait_for_page_complete(driver, wait)
 