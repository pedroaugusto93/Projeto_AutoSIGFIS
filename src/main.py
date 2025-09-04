# main.py
# -*- coding: utf-8 -*-

# Dica: se quiser abrir o Chrome em modo debug, rode manualmente no PowerShell:
# "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"

import sys
import config
from helpers import wait_for_page_complete
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from page_dados_basicos import preencher_dados_basicos
from page_itens import preencher_itens
from page_documentos import preencher_documentos
from page_empenhos import preencher_empenhos
from page_enviar import enviar_e_imprimir


def selecionar_aba(driver, wait, titulo: str):
    """
    Clica na aba cujo <fa-icon> tem atributo title igual a `titulo`.
    Para 'Enviar', tenta achar a aba; se não existir, apenas registra e segue,
    pois o botão 'Enviar ao TCE' fica em #BotoesComuns (fora das abas).
    """
    if "Enviar" in titulo:
        try:
            aba = wait.until(EC.element_to_be_clickable((By.XPATH,
                "//ul[contains(@class,'nav-tabs')]//a[.//fa-icon[@title='5 - Enviar'] or contains(normalize-space(.),'Enviar')]"
            )))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", aba)
            driver.execute_script("arguments[0].click();", aba)
            wait_for_page_complete(driver, wait)
            print("[✔] Aba 'Enviar' acessada")
        except Exception:
            print("[i] Aba 'Enviar' não existe nesta tela; seguindo direto para o botão.")
        return

    # Demais abas (com fa-icon e title esperado)
    aba = wait.until(EC.element_to_be_clickable((By.XPATH,
        f"//ul[contains(@class,'nav-tabs')]//fa-icon[@title='{titulo}']/ancestor::a"
    )))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", aba)
    driver.execute_script("arguments[0].click();", aba)
    wait_for_page_complete(driver, wait)
    print(f"[✔] Aba '{titulo}' acessada")


def main():
    print("[INIT] Carregando planilha…")
    cfgs = config.load_all_cfgs()
    if not cfgs:
        print(f"[ERRO] Nenhuma config encontrada em: {config.EXCEL_PATH}")
        return

    print(f"[INFO] Registros carregados: {len(cfgs)}")

    # Cria um ÚNICO driver para todos os registros (ganho de tempo)
    driver, wait = config.create_driver_and_wait()

    try:
        for idx, cfg in enumerate(cfgs, start=1):
            proc = cfg.get('PROCESSO')
            print(f"\n--- [Registro {idx}] PROCESSO: {proc} ---")
            try:
                driver.get(config.URL_DISPENSA)
                wait_for_page_complete(driver, wait)

                # === Aba 1: Dados Básicos ===
                selecionar_aba(driver, wait, "1 - Dados Básicos")
                preencher_dados_basicos(driver, wait, cfg)
                try:
                    valor_p1 = driver.find_element(By.NAME, 'Valor').get_attribute('value')
                except Exception:
                    valor_p1 = cfg.get('VALOR', '')
                print(f"[INFO] Valor (página 1): {valor_p1}")

                # === Aba 2: Itens ===
                selecionar_aba(driver, wait, "Itens")
                preencher_itens(driver, wait, cfg)

                # === Aba 3: Documentos ===
                selecionar_aba(driver, wait, "3 - Documentos")
                preencher_documentos(driver, wait, cfg)

                # === Aba 4: Empenhos ===
                selecionar_aba(driver, wait, "4 - Empenhos")
                preencher_empenhos(driver, wait, cfg, valor_p1)

                # === Enviar (aba pode não existir) ===
                selecionar_aba(driver, wait, "5 - Enviar")
                enviar_e_imprimir(driver, wait, cfg)

                print(f"[OK] Registro concluído: {proc}")

            except Exception as e:
                print(f"[ERRO] Processo {proc} falhou: {e}")

    finally:
        print("[END] Fechando driver…")
        driver.quit()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] Interrompido pelo usuário.")
        sys.exit(1)
