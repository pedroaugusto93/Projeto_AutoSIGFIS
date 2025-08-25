# # page_documentos.py
# import time
# import config
# import os
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.action_chains import ActionChains
# from helpers import wait_for_page_complete

# def preencher_documentos(driver, wait, cfg):
#     # (1) Clicar na aba Documentos (você já confirmou que isso está funcionando)
#     # Portanto, se já estiver na aba, não precisa repetir.

#     # (2) Aguardar botão 'Incluir Documento' estar presente no DOM
#     incluir_btn = wait.until(EC.presence_of_element_located((
#         By.XPATH, "//div[contains(@class,'tab-footer')]//button[contains(.,'Incluir Documento')]"
#     )))

#     # (3) Scroll até o botão e dar foco
#     driver.execute_script("arguments[0].scrollIntoView(true);", incluir_btn)
#     time.sleep(0.3)  # Pequena pausa para renderização final da aba

#     # (4) Clique com ActionChains + JS para garantir disparo dos eventos Angular
#     actions = ActionChains(driver)
#     actions.move_to_element(incluir_btn).pause(0.2).click().perform()

#     # (5) Espera o modal visível (confirma que carregou)
#     wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "modal-container[role='dialog']")))

#     # (6) Campo Ato (dentro de input-select[name='tipo'])
#     ato_wrapper = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='tipo']")))
#     ato_select = ato_wrapper.find_element(By.TAG_NAME, "select")

#     driver.execute_script("arguments[0].scrollIntoView(true);", ato_select)
#     driver.execute_script("""
#         arguments[0].value = arguments[1];
#         arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
#         arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
#     """, ato_select, cfg.get('ATO_DOCUMENTO'))  # Ex: "1" para Principal

#     # (7) Tipo Documento (usando a mesma lógica Angular-safe)
#     tipo_wrapper = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='TipoDocumento']")))
#     tipo_select = tipo_wrapper.find_element(By.TAG_NAME, "select")

#     driver.execute_script("arguments[0].scrollIntoView(true);", tipo_select)
#     driver.execute_script("""
#         arguments[0].value = arguments[1];
#         arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
#         arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
#     """, tipo_select, cfg.get('TIPO_DOCUMENTO'))  # Ex: "1" para PDF



#    # (8) Upload do arquivo
#     file_path = cfg.get('FILE_PATH')

#     # Verifica se o arquivo existe
#     if not os.path.isfile(file_path):
#         raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

#     # Encontra o campo real do tipo file dentro do modal (mais flexível que usar ID fixo)
#     upload = wait.until(EC.presence_of_element_located((
#         By.XPATH, "//modal-container//input[@type='file']"
#     )))
#     upload.send_keys(file_path)

#     # Verifica se o nome do arquivo aparece no campo visual (readonly)
#     campo_visual = wait.until(EC.presence_of_element_located((
#         By.CSS_SELECTOR, "input[id^='input-upload-0-']"
#     )))
#     wait.until(lambda d: os.path.basename(file_path) in campo_visual.get_attribute('value'))

#     print(f"[✔] Upload do arquivo '{file_path}' realizado com sucesso.")



#     # (9) Salvar
#     salvar_btn = wait.until(EC.element_to_be_clickable((
#         By.XPATH,
#         "//div[contains(@class,'modal-footer')]//button[@type='submit' and contains(@class,'btn-outline-primary')]"
#     )))
#     driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", salvar_btn)

#     # (10) Espera carregar após salvar
#     wait_for_page_complete(driver, wait)

import time
import os
import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from helpers import wait_for_page_complete

def preencher_documentos(driver, wait, cfg):
    # (1) Botão "Incluir Documento"
    incluir_btn = wait.until(EC.presence_of_element_located((
        By.XPATH, "//div[contains(@class,'tab-footer')]//button[contains(.,'Incluir Documento')]"
    )))
    driver.execute_script("arguments[0].scrollIntoView(true);", incluir_btn)
    time.sleep(0.3)
    actions = ActionChains(driver)
    actions.move_to_element(incluir_btn).pause(0.2).click().perform()

    # (2) Espera o modal visível
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "modal-container[role='dialog']")))

    # (3) Campo Ato
    ato_wrapper = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='tipo']")))
    ato_select = ato_wrapper.find_element(By.TAG_NAME, "select")
    driver.execute_script("arguments[0].scrollIntoView(true);", ato_select)
    driver.execute_script("""
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, ato_select, cfg.get('ATO_DOCUMENTO'))

    # (4) Tipo Documento
    tipo_wrapper = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input-select[name='TipoDocumento']")))
    tipo_select = tipo_wrapper.find_element(By.TAG_NAME, "select")
    driver.execute_script("arguments[0].scrollIntoView(true);", tipo_select)
    driver.execute_script("""
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, tipo_select, cfg.get('TIPO_DOCUMENTO'))

    # (5) Upload do arquivo
    file_path = cfg.get('FILE_PATH')
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    upload = wait.until(EC.presence_of_element_located((By.XPATH, "//modal-container//input[@type='file']")))
    upload.send_keys(file_path)

    campo_visual = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[id^='input-upload-0-']")))
    wait.until(lambda d: os.path.basename(file_path) in campo_visual.get_attribute('value'))

    print(f"[✔] Upload do arquivo '{file_path}' realizado com sucesso.")

    # (6) Salvar
    salvar_btn = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "//div[contains(@class,'modal-footer')]//button[@type='submit' and contains(@class,'btn-outline-primary')]"
    )))
    driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", salvar_btn)

    # (7) Espera carregar após salvar
    wait_for_page_complete(driver, wait)

    # (8) Clicar no botão OK do SweetAlert2, se aparecer
    try:
        ok_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm') and contains(.,'OK')]")))
        driver.execute_script("arguments[0].click();", ok_btn)
    except Exception:
        print("[!] Nenhum botão OK encontrado após salvar (pode estar tudo certo).")