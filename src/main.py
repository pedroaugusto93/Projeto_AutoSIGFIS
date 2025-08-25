# virtual/main.py
import config # Assumindo que config.py está no mesmo diretório
from helpers import wait_for_page_complete # Função auxiliar para esperar o carregamento da página
from selenium.webdriver.common.by import By # Importa By do Selenium
from selenium.webdriver.support import expected_conditions as EC # Importa expected_conditions do Selenium

from page_dados_basicos import preencher_dados_basicos # Função para preencher dados básicos
from page_itens import preencher_itens # Função para preencher itens
from page_documentos import preencher_documentos # Função para preencher documentos
from page_empenhos import preencher_empenhos # Função para preencher empenhos
from page_enviar import enviar_e_imprimir # Função para enviar e imprimir


def selecionar_aba(driver, wait, titulo):   # Seleciona a aba pela descrição

    aba = wait.until(EC.element_to_be_clickable((By.XPATH,f"//ul[contains(@class,'nav-tabs')]//fa-icon[@title='{titulo}']/ancestor::a")))# Ajuste o seletor conforme necessário
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", aba) # Rola até a aba
    driver.execute_script("arguments[0].click();", aba) # Clica na aba via JavaScript
    wait_for_page_complete(driver, wait) # Espera a página carregar


def main():
    # Carrega todas as configurações do Excel
    cfgs = config.load_all_cfgs()
    # Verifica se há configurações
    #if not cfgs:
    #    print("Nenhuma config encontrada em", config.EXCEL_PATH)
    #    return

    for idx, cfg in enumerate(cfgs, start=1):
        print(f"\n--- [Registro {idx}] PROCESSO: {cfg.get('PROCESSO')} ---") # Inicia o processo para cada configuração 
        
       
        driver, wait = config.create_driver_and_wait()  # Cria o driver e o wait
        
        # Tenta executar o processo, captura erros e garante que o driver será fechado
        try:
            driver.get(config.URL_DISPENSA)
            wait_for_page_complete(driver, wait)

            # === Aba 1: Dados Básicos ===
            selecionar_aba(driver, wait, "1 - Dados Básicos")
            preencher_dados_basicos(driver, wait, cfg)
           # valor_p1 = driver.find_element(By.NAME, 'Valor').get_attribute('value')

            # === Aba 2: Itens ===
            selecionar_aba(driver, wait, "Itens")
            preencher_itens(driver, wait, cfg)

            # === Aba 3: Documentos ===
            selecionar_aba(driver, wait, "3 - Documentos")
            preencher_documentos(driver, wait, cfg)

            # === Aba 4: Empenhos ===
            selecionar_aba(driver, wait, "4 - Empenhos")
            #preencher_empenhos(driver, wait, cfg, valor_p1)

            # === Aba 5: Enviar ===
            selecionar_aba(driver, wait, "5 - Enviar")
            enviar_e_imprimir(driver, wait, cfg)

        except Exception as e:
            print(f"[ERRO] Processo {cfg.get('PROCESSO')} falhou: {e}")

        finally:
            driver.quit()


if __name__ == '__main__':
    main()
