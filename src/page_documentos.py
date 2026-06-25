# page_documentos.py
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from helpers import wait_for_page_complete, js_select_value, safe_click, swal_click_confirm, confirm_or_warn
from logger import get_logger

log = get_logger("documentos")

# Modal pode aparecer como .modal.show (itens/empenho) ou modal-container[role=dialog]
_MODAL_CSS = ".modal.show, modal-container[role='dialog']"


def _select_por_valor(modal, valor):
    """
    Retorna o <select> do modal que possui uma <option> com value == `valor`.
    Ancora estavel: o id do select muda (input-select-80/81...), mas o conjunto
    de opcoes nao. 'Ato' tem a opcao 1 (Principal); 'Tipo' tem a 5 (Documento do Ato).
    """
    if not valor:
        return None
    for sel in modal.find_elements(By.TAG_NAME, "select"):
        if sel.find_elements(By.CSS_SELECTOR, f"option[value='{valor}']"):
            return sel
    return None


def preencher_documentos(driver, wait, cfg):
    short_wait = WebDriverWait(driver, 4, poll_frequency=0.2)
    # Limpa aspas/espacos: "Copiar como caminho" do Windows cola o path entre aspas,
    # o que faz o os.path.isfile falhar. Remove aspas simples/duplas das pontas.
    file_path = str(cfg.get("FILE_PATH") or "").strip().strip('"').strip("'").strip()
    log.info("Preenchendo Documentos | arquivo=%s", file_path or "(vazio)")

    # Validação do arquivo (antes de abrir o modal)
    if not file_path:
        log.warning("FILE_PATH vazio na planilha; pulando inclusao de documento.")
        return False
    if not os.path.isfile(file_path):
        log.error("Arquivo de documento nao encontrado (%s); registro ficara SEM documento.", file_path)
        return False

    # (1) Incluir Documento (botao por texto, sem depender de tab-footer)
    incluir_btn = wait.until(EC.element_to_be_clickable((
        By.XPATH, "//button[contains(normalize-space(.),'Incluir Documento')]"
    )))
    safe_click(driver, wait, incluir_btn)

    # (2) Modal aberto
    modal = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, _MODAL_CSS)))

    # (3) Ato (localiza o select que contem o valor desejado, ex.: 1=Principal)
    ato_val = cfg.get("ATO_DOCUMENTO")
    ato_sel = _select_por_valor(modal, ato_val)
    if ato_sel is None:
        log.error("Select 'Ato' (valor=%s) nao encontrado no modal.", ato_val)
    else:
        js_select_value(driver, ato_sel, ato_val)
        confirm_or_warn(driver, lambda d: ato_sel.get_attribute("value") == ato_val,
                        "Ato nao assumiu o valor esperado")

    # (4) Tipo de Documento (ex.: 5=Documento do Ato(PDF))
    tipo_val = cfg.get("TIPO_DOCUMENTO")
    tipo_sel = _select_por_valor(modal, tipo_val)
    if tipo_sel is None:
        log.error("Select 'Tipo de Documento' (valor=%s) nao encontrado no modal.", tipo_val)
    else:
        js_select_value(driver, tipo_sel, tipo_val)
        confirm_or_warn(driver, lambda d: tipo_sel.get_attribute("value") == tipo_val,
                        "Tipo de Documento nao assumiu o valor esperado")

    # (5) Upload do arquivo via <input type='file'> (oculto). O Selenium injeta o
    #     caminho direto, sem abrir a janela nativa do Windows.
    uploads = modal.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if not uploads:
        uploads = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")  # fallback global
    if not uploads:
        log.error("Nenhum <input type='file'> encontrado. Se o SIGFIS usa SOMENTE a janela "
                  "nativa do Windows (sem input file oculto), o Selenium nao consegue anexar "
                  "por aqui. Mande o outerHTML completo do modal para avaliar.")
        return False

    uploads[0].send_keys(file_path)

    # Confirma que o nome do arquivo apareceu no preview do modal
    base = os.path.basename(file_path).lower()
    try:
        short_wait.until(lambda d: d.execute_script("""
            const b = arguments[0];
            const scope = document.querySelector('.modal.show, modal-container');
            if (!scope) return false;
            const inputs = Array.from(scope.querySelectorAll("input[type='text'], input[readonly], input[id^='input-upload-']"));
            return inputs.some(i => (i.value || '').toLowerCase().includes(b));
        """, base))
        log.info("Arquivo anexado: %s", os.path.basename(file_path))
    except TimeoutException:
        log.warning("Nome do arquivo nao confirmado no preview; seguindo (confira o resultado).")

    # (6) Salvar no modal
    salvar_btn = wait.until(EC.presence_of_element_located((
        By.XPATH, "//div[contains(@class,'modal-footer')]//button[@type='submit' and contains(@class,'btn-outline-primary')]"
    )))
    safe_click(driver, wait, salvar_btn)

    # (7) Pós-salvar + SweetAlert
    wait_for_page_complete(driver, wait)
    if not swal_click_confirm(driver, wait, 'OK', 'Confirmar'):
        try:
            WebDriverWait(driver, 3, poll_frequency=0.2).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.swal2-container.swal2-shown, div.swal2-popup.swal2-modal'))
            )
        except TimeoutException:
            pass

    wait_for_page_complete(driver, wait)
    log.info("Documento incluido.")
    return True
