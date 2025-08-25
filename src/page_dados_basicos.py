# Preenche a aba "Dados Básicos" do formulário de Dispensa/Inexigibilidade
import config # Importa as constantes e funções de configuração
from selenium.webdriver.common.by import By # Importa By do Selenium
from selenium.webdriver.support import expected_conditions as EC # Importa expected_conditions do Selenium
from selenium.webdriver.common.keys import Keys # Importa Keys do Selenium
from selenium.common.exceptions import TimeoutException # Importa TimeoutException do Selenium
from helpers import fill_input, js_select_value, wait_for_page_complete # Funções auxiliares

#Preenche todos os campos da aba 'Dados Básicos' usando somente CSS selectors e, ao final, seleciona a aba 'Itens'. Retorna cfg['VALOR'].
def preencher_dados_basicos(driver, wait, cfg):  

    # 1) Processo Administrativo
    fill_input( driver, wait,'input-text[name="ProcessoAdministrativo"] input', cfg['PROCESSO']) 

    # # 2) Tipologia
    wrap = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'input-select[name="TipologiaObjetoContratacao"]')))
    sel = wrap.find_element(By.TAG_NAME, 'select')
    driver.execute_script("arguments[0].scrollIntoView(true);", wrap)
    js_select_value(driver, sel, config.TIPOLOGIA_VALUE)
    wait.until(lambda d: sel.get_attribute('value') == config.TIPOLOGIA_VALUE)
    
    # 3) Valor
    fill_input(
        driver, wait,
        'input-currency[name="Valor"] input',
        cfg['VALOR']
    )

    # 4) Item/Lote
    wrap = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        'input-select[name="TipoLicitacao"]'
    )))
    sel = wrap.find_element(By.TAG_NAME, 'select')
    driver.execute_script("arguments[0].scrollIntoView(true);", wrap)
    js_select_value(driver, sel, config.ITEM_LOTE_VALUE)
    wait.until(lambda d: sel.get_attribute('value') == config.ITEM_LOTE_VALUE)

    # 5) Fundamentação Legal
    wrap = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        'input-select[name="FundamentoLegal"]'
    )))
    sel = wrap.find_element(By.TAG_NAME, 'select')
    driver.execute_script("arguments[0].scrollIntoView(true);", wrap)
    js_select_value(driver, sel, config.FUNDAMENTO_VALUE)
    wait.until(lambda d: sel.get_attribute('value') == config.FUNDAMENTO_VALUE)

    # 6) Ordenador (CPF)
    ord_selector = 'app-pessoa-pesquisa-cadastro[name="cpfCnpjOrdenador"] input[name="cpfCnpj"]'
    fill_input(driver, wait, ord_selector, cfg['CPF_ORDENADOR'])
    wait.until(lambda d: d.find_element(By.CSS_SELECTOR, ord_selector)
               .get_attribute('value').strip() != "")

    # 7) Data do Ato
    data_selector = 'input-date[name="DataAto"] input'
    fill_input(driver, wait, data_selector, cfg['DATA_ATO'])
    wait.until(lambda d: d.find_element(By.CSS_SELECTOR, data_selector)
               .get_attribute('value').strip() != "")

    # 8) Fornecedor (CNPJ + Razão Social)
    forn_cnpj_selector = (
        'app-pessoa-pesquisa-cadastro[name="fornecedor"] '
        'input[name="cpfCnpj"]'
    )
    fill_input(driver, wait, forn_cnpj_selector, cfg['CNPJ_FORNECEDOR'])

    nome_sel = (
        'app-pessoa-pesquisa-cadastro[name="fornecedor"] '
        'input-text[name="nomeRazaoSocial"] input'
    )

    try:
        fill_input(driver, wait, nome_sel, cfg['NOME_FORNECEDOR'])
        wait.until(lambda d: d.find_element(By.CSS_SELECTOR, nome_sel)
                   .get_attribute('value').strip() == cfg['NOME_FORNECEDOR'].strip())
    except TimeoutException:
        print("[⚠] Timeout ao aguardar nome do fornecedor. Tentando digitação manual.")
        campo_nome = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, nome_sel)))
        campo_nome.clear()
        campo_nome.send_keys(cfg['NOME_FORNECEDOR'])
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));",
            campo_nome
        )
        print(f"[✔] Fornecedor preenchido manualmente: {cfg['NOME_FORNECEDOR']}")

    # 9) Prazo de Execução
    fill_input(
        driver, wait,
        'input-number[name="prazoExecucao"] input',
        cfg['PRAZO_EXECUCAO']
    )

    # 10) Objeto
    fill_input(
        driver, wait,
        'input-textarea[name="Objeto"] textarea',
        cfg['OBJETO']
    )

    # 11) Salvar e avançar
    save_btn_selector = 'button[form="frm"][type="submit"]'
    btn = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        save_btn_selector
    )))
    driver.execute_script("arguments[0].click();", btn)
    wait_for_page_complete(driver, wait)

    # 12) Clicar em “OK” no SweetAlert
    ok_btn_selector = 'button.swal2-confirm.swal2-styled'
    ok_btn = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        ok_btn_selector
    )))
    driver.execute_script("arguments[0].click();", ok_btn)
    wait_for_page_complete(driver, wait)

    # 13) Selecionar aba Itens
    itens_link = wait.until(EC.presence_of_element_located((
        By.XPATH,
        "(//ul[contains(@class,'nav-tabs')]/li)[2]/a"
    )))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", itens_link)
    driver.execute_script("arguments[0].click();", itens_link)
    wait_for_page_complete(driver, wait)

# Preenche a aba "Dados Básicos" do formulário de Dispensa/Inexigibilidade
# import config
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
# from helpers import set_field_value, click_js
# from helpers import wait_for_page_complete  # você já tem

# def preencher_dados_basicos(driver, wait, cfg):
#     # 1) Processo Administrativo
#     set_field_value(driver, wait,
#         'input-text[name="ProcessoAdministrativo"] input',
#         cfg['PROCESSO']
#     )

#     # 2) Tipologia (wrapper com <select> interno)
#     set_field_value(driver, wait,
#         'input-select[name="TipologiaObjetoContratacao"]',
#         config.TIPOLOGIA_VALUE
#     )

#     # 3) Valor (se precisar apenas dígitos, trate o valor antes de passar)
#     set_field_value(driver, wait,
#         'input-currency[name="Valor"] input',
#         cfg['VALOR']
#     )

#     # 4) Item/Lote
#     set_field_value(driver, wait,
#         'input-select[name="TipoLicitacao"]',
#         config.ITEM_LOTE_VALUE
#     )

#     # 5) Fundamentação Legal
#     set_field_value(driver, wait,
#         'input-select[name="FundamentoLegal"]',
#         config.FUNDAMENTO_VALUE
#     )

#     # 6) Ordenador (CPF)
#     set_field_value(driver, wait,
#         'app-pessoa-pesquisa-cadastro[name="cpfCnpjOrdenador"] input[name="cpfCnpj"]',
#         cfg['CPF_ORDENADOR']
#     )

#     # 7) Data do Ato
#     set_field_value(driver, wait,
#         'input-date[name="DataAto"] input',
#         cfg['DATA_ATO']
#     )

#     # 8) Fornecedor (CNPJ + Razão Social)
#     set_field_value(driver, wait,
#         'app-pessoa-pesquisa-cadastro[name="fornecedor"] input[name="cpfCnpj"]',
#         cfg['CNPJ_FORNECEDOR']
#     )