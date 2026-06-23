# page_documentos.py
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from helpers import wait_for_page_complete, js_select_value, safe_click, swal_click_confirm
from logger import get_logger

log = get_logger("documentos")


def preencher_documentos(driver, wait, cfg):
    short_wait = WebDriverWait(driver, 4, poll_frequency=0.2)
    file_path = cfg.get("FILE_PATH")
    log.info("Preenchendo Documentos | arquivo=%s", file_path or "(vazio)")

    # Validação antecipada e clara do arquivo (antes de abrir o modal)
    if not file_path or not str(file_path).strip():
        log.warning("FILE_PATH vazio na planilha; pulando inclusao de documento.")
        return
    if not os.path.isfile(file_path):
        log.error("Arquivo de documento nao encontrado: %s", file_path)
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    # (1) Incluir Documento
    incluir_btn = wait.until(EC.presence_of_element_located((
        By.XPATH, "//div[contains(@class,'tab-footer')]//button[contains(.,'Incluir Documento')]"
    )))
    safe_click(driver, wait, incluir_btn)

    # (2) Modal aberto
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "modal-container[role='dialog']")))

    # (3) Ato
    ato_wrap = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='tipo']")))
    ato_select = ato_wrap.find_element(By.TAG_NAME, "select")
    js_select_value(driver, ato_select, cfg.get("ATO_DOCUMENTO"))

    # (4) Tipo de Documento
    tipo_wrap = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='TipoDocumento']")))
    tipo_select = tipo_wrap.find_element(By.TAG_NAME, "select")
    js_select_value(driver, tipo_select, cfg.get("TIPO_DOCUMENTO"))

    # (5) Upload do arquivo
    upload = wait.until(EC.presence_of_element_located((
        By.XPATH, "//modal-container//input[@type='file']"
    )))
    upload.send_keys(file_path)

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
        log.warning("Nome do arquivo nao confirmado no preview do modal; seguindo.")
    log.info("Upload do arquivo realizado: %s", os.path.basename(file_path))

    # (6) Salvar no modal
    salvar_btn = wait.until(EC.presence_of_element_located((
        By.XPATH, "//div[contains(@class,'modal-footer')]//button[@type='submit' and contains(@class,'btn-outline-primary')]"
    )))
    safe_click(driver, wait, salvar_btn)

    # (7) Espera pós-salvar
    wait_for_page_complete(driver, wait)

    # (8) SweetAlert OK
    if not swal_click_confirm(driver, wait, 'OK', 'Confirmar'):
        try:
            WebDriverWait(driver, 3, poll_frequency=0.2).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.swal2-container.swal2-shown, div.swal2-popup.swal2-modal'))
            )
        except TimeoutException:
            pass

    wait_for_page_complete(driver, wait)
    log.info("Documento incluido.")
