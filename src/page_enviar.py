

# import os
# import time
# import pyautogui
# from pywinauto.application import Application
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from helpers import wait_for_page_complete

# # Dicionário global para controlar contadores por PROCESSO
# processo_contador = {}

# def gerar_nome_arquivo(processo):
#     base_nome = processo.strip().replace("/", "-")
#     contador = processo_contador.get(base_nome, 0)
#     if contador == 0:
#         nome_final = f"{base_nome}.pdf"
#     else:
#         nome_final = f"{base_nome} - {contador}.pdf"
#     processo_contador[base_nome] = contador + 1
#     return nome_final

# def enviar_e_imprimir(driver, wait, cfg):
#     from helpers import aguardar_carregamento_final

#     print("[1] Tentando clicar na aba 'Enviar'")
#     try:
#         aba_envio = wait.until(EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class,'nav-tabs')]//a[contains(., 'Enviar')]")))
#         driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", aba_envio)
#         wait_for_page_complete(driver, wait)
#         print("[✔] Aba 'Enviar' acessada")
#     except:
#         print("[⚠] Aba 'Enviar' não localizada")

#     # (1) Botão "Enviar ao TCE"
#     print("[2] Procurando botão 'Enviar ao TCE'")
#     enviar_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Enviar ao TCE')]")))
#     driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", enviar_btn)

#     # (2) Confirmar "Sim"
#     print("[3] Confirmando SweetAlert (Sim)")
#     sim_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm') and contains(.,'Sim')]")))
#     driver.execute_script("arguments[0].click();", sim_btn)

#     # (3) "Emitir Recibo"
#     print("[4] Clicando em 'Emitir Recibo'")
#     emitir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm') and contains(.,'Emitir Recibo')]")))
#     driver.execute_script("arguments[0].click();", emitir_btn)

#     # (4) "Imprimir"
#     print("[5] Clicando no botão 'Imprimir'")
#     imprimir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Imprimir') and contains(@class,'btn-outline-primary')]")))
#     driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", imprimir_btn)

#     # (5) Aguarda janela de impressão abrir
#     time.sleep(2)
#     print("[6] Pressionando Ctrl+P para abrir janela de impressão")
#     pyautogui.hotkey("ctrl", "p")
#     time.sleep(2.5)

#     # (6.1) Garante que destino seja "Salvar como PDF"
#     print("[6.1] Selecionando destino 'Salvar como PDF'")
#     pyautogui.press("tab", presses=2, interval=0.2)
#     pyautogui.press("down", presses=2, interval=0.2)
#     pyautogui.press("enter")
#     time.sleep(1)

#     # (6.2) Pressiona Ctrl+S para abrir janela de salvar
#     print("[6.2] Pressionando Ctrl+S para salvar como PDF")
#     pyautogui.hotkey("ctrl", "s")
#     time.sleep(2)

#     # (7) Nome e caminho do arquivo
#     processo = cfg.get('PROCESSO', 'recibo')
#     nome_arquivo = gerar_nome_arquivo(processo)
#     caminho_completo = os.path.join("C:\\Users\\pedro\\Documents\\Sigfis", nome_arquivo)
#     print(f"[7] Aguardando janela 'Salvar como' para salvar em: {caminho_completo}")

#     # (8) Usa pywinauto para interagir com a janela do Chrome
#     try:
#         app = Application(backend="uia").connect(title_re="Salvar.*")
#         salvar_janela = app.window(title_re="Salvar.*")
#         salvar_janela.wait("ready", timeout=10)

#         salvar_janela.type_keys(caminho_completo, with_spaces=True)
#         time.sleep(1)

#         salvar_btn = salvar_janela.child_window(title="Salvar", control_type="Button")
#         salvar_btn.click_input()

#         print(f"[✔] PDF salvo com sucesso: {caminho_completo}")
#     except Exception as e:
#         print(f"[❌] Erro ao salvar o PDF: {e}")

#     time.sleep(2)
#     aguardar_carregamento_final(driver, wait)


import os
import time
import pyautogui
from pywinauto import Desktop
import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from helpers import wait_for_page_complete, aguardar_carregamento_final

# Dicionário global para controlar contadores por PROCESSO
processo_contador = {}

def gerar_nome_arquivo(processo):
    base_nome = processo.strip().replace("/", "-")
    contador = processo_contador.get(base_nome, 0)
    if contador == 0:
        nome_final = f"{base_nome}.pdf"
    else:
        nome_final = f"{base_nome} - {contador}.pdf"
    processo_contador[base_nome] = contador + 1
    return nome_final

def enviar_e_imprimir(driver, wait, cfg):
    print("[1] Tentando clicar na aba 'Enviar'")
    try:
        aba_envio = wait.until(EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class,'nav-tabs')]//a[contains(., 'Enviar')]")))
        driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", aba_envio)
        wait_for_page_complete(driver, wait)
        print("[✔] Aba 'Enviar' acessada")
    except:
        print("[⚠] Aba 'Enviar' não localizada")

    print("[2] Procurando botão 'Enviar ao TCE'")
    enviar_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Enviar ao TCE')]")))
    driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", enviar_btn)

    print("[3] Confirmando SweetAlert (Sim)")
    sim_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm') and contains(.,'Sim')]")))
    driver.execute_script("arguments[0].click();", sim_btn)
    
    
    print("[4] Clicando em 'Fechar' para fechar o modal")
    emitir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm') and contains(.,'Fechar')]")))
    driver.execute_script("arguments[0].click();", emitir_btn)


    # print("[4] Clicando em 'Emitir Recibo'")
    # emitir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm') and contains(.,'Emitir Recibo')]")))
    # driver.execute_script("arguments[0].click();", emitir_btn)

    # print("[5] Clicando no botão 'Imprimir'")
    # imprimir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Imprimir') and contains(@class,'btn-outline-primary')]")))
    # driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", imprimir_btn)

    # print("[6] Pressionando Ctrl+P para abrir janela de impressão")
    # time.sleep(2)
    # pyautogui.hotkey("ctrl", "p")
    # time.sleep(2)

    # print("[6.1] Selecionando destino 'Salvar como PDF'")
    # pyautogui.press('tab', presses=5, interval=0.2)
    # pyautogui.press('down')
    # time.sleep(1)

    # print("[6.2] Pressionando Ctrl+S para salvar como PDF")
    # pyautogui.hotkey("ctrl", "s")
    # time.sleep(2)

    # processo = cfg.get('PROCESSO', 'recibo')
    # nome_arquivo = gerar_nome_arquivo(processo)
    # caminho_completo = os.path.join("C:\\Users\\pedro\\Documents\\Sigfis", nome_arquivo)
    # print(f"[7] Aguardando janela 'Salvar como' para salvar em: {caminho_completo}")

    # try:
    #     janela = Desktop(backend="uia").window(title_re="Salvar.*", visible_only=False)
    #     edit = janela.child_window(auto_id="1001", control_type="Edit")
    #     edit.set_edit_text(caminho_completo)

    #     salvar_btn = janela.child_window(control_type="Button", title="Salvar")
    #     salvar_btn.invoke()

    #     print(f"[✔] Recibo salvo como PDF: {caminho_completo}")
    # except Exception as e:
    #     print(f"[❌] Erro ao salvar o PDF: {e}")

    # print("[DEBUG] Aguardando carregamento completo final antes de enviar...")
    # aguardar_carregamento_final(driver, wait)
    # print("[✔] Página carregada e pronta.")
