from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

# ————— Navegação até “Cadastro de Dispensa” —————
driver.get("URL_BASE_DO_SIGFIS")
wait.until(EC.element_to_be_clickable((By.XPATH, "//a[.='Atos Jurídicos']"))).click()
wait.until(EC.element_to_be_clickable((By.XPATH, "//a[.='Dispensa Eletrônica']"))).click()

# ————— Página 1 – Dados Básicos —————
campo_processo = wait.until(EC.visibility_of_element_located((
    By.XPATH, "//input[@type='text' and @maxlength='36' and @autocomplete='on']"
)))
campo_processo.send_keys("12345/2025")

Select(wait.until(EC.element_to_be_clickable((
    By.XPATH, "//input-select[@name='TipologiaObjetoContratacao']//select"
)))).select_by_value("30")  # Outros Serviços

campo_valor = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//input-currency[@name='Valor']//input[@currencymask]"
)))
campo_valor.send_keys("10000,00")

Select(wait.until(EC.element_to_be_clickable((
    By.XPATH, "//input-select[@name='TipoLicitacao']//select"
)))).select_by_value("1")  # Item

Select(wait.until(EC.element_to_be_clickable((
    By.XPATH, "//input-select[@name='FundamentoLegal']//select"
)))).select_by_value("61")  # Art. 75 II

campo_ordenador_cpf = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-pessoa-pesquisa-cadastro[@name='cpfCnpjOrdenador']//input[@name='cpfCnpj']"
)))
campo_ordenador_cpf.send_keys("12345678901")

campo_ordenador_nome = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-pessoa-pesquisa-cadastro[@name='cpfCnpjOrdenador']//input[@maxlength='255']"
)))
campo_ordenador_nome.send_keys("NOME DO ORDENADOR")

campo_data_ato = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//input-date[@name='DataAto']//input"
)))
campo_data_ato.send_keys("06/07/2025")

campo_fornecedor_cnpj = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-pessoa-pesquisa-cadastro[@name='fornecedor']//input[@name='cpfCnpj']"
)))
campo_fornecedor_cnpj.send_keys("12345678000199")

campo_prazo_execucao = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//input-number[@name='prazoExecucao']//input[@type='number']"
)))
campo_prazo_execucao.send_keys("30")

campo_objeto = wait.until(EC.visibility_of_element_located((
    By.XPATH, "//input-textarea[@name='Objeto']//textarea"
)))
campo_objeto.send_keys("Contratação de serviços de apoio técnico-administrativo.")

# salvar e avançar
wait.until(EC.element_to_be_clickable((
    By.XPATH, "//button[contains(normalize-space(.),'Salvar') and contains(normalize-space(.),'Próximo')]"
))).click()

# salvar valor para uso posterior
valor_pagina1 = campo_valor.get_attribute("value")

# ————— Página 2 – Itens —————
wait.until(EC.element_to_be_clickable((
    By.XPATH, "//fa-icon[@title='Itens']/ancestor::li[1]"
))).click()
wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-itens-lote//button[contains(normalize-space(.),'Incluir Novo Item')]"
))).click()

# Item: preencher modal
modal_numero = wait.until(EC.visibility_of_element_located((By.NAME, "posicao")))
modal_numero.clear()
modal_numero.send_keys("1")

texto_objeto = campo_objeto.get_attribute("value")
modal_descricao = driver.find_element(
    By.XPATH, "//input-textarea[@name='Descricao']//textarea"
)
modal_descricao.clear()
modal_descricao.send_keys(texto_objeto)

modal_qtd = driver.find_element(
    By.XPATH, "//input-number[@name='quantidade']//input[@type='number']"
)
modal_qtd.clear()
modal_qtd.send_keys("1")

Select(driver.find_element(
    By.XPATH, "//input-select[@name='unidadeMedida']//select"
)).select_by_visible_text("serv")

modal_valor_unit = driver.find_element(
    By.XPATH, "//input-currency[@name='ValorUnitario']//input[@currencymask]"
)
modal_valor_unit.clear()
modal_valor_unit.send_keys(valor_pagina1)

wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-item-lote-cadastro-modal//button[contains(normalize-space(.),'Salvar')]"
))).click()

# ————— Página 3 – Documentos —————
wait.until(EC.element_to_be_clickable((
    By.XPATH, "//span[normalize-space()='3 - Documentos']/ancestor::a[1]"
))).click()
wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-documentos-cadastro//button[contains(normalize-space(.),'Incluir Documento')]"
))).click()

Select(wait.until(EC.element_to_be_clickable((
    By.XPATH, "//label[normalize-space()='Ato *']/following-sibling::select"
)))).select_by_visible_text("principal")

Select(wait.until(EC.element_to_be_clickable((
    By.XPATH, "//label[normalize-space()='Tipo de Documento *']/following-sibling::select"
)))).select_by_visible_text("documento do ato")

input_upload = wait.until(EC.presence_of_element_located((By.ID, "input-upload-1-1")))
input_upload.send_keys(r"C:\Users\pedro\Downloads\modelo_de_termo_de_referncia_prestao_de_servio_comum.pdf")

wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-documentos-cadastro//button[contains(normalize-space(.),'Salvar')]"
))).click()

# ————— Página 4 – Empenhos —————
wait.until(EC.element_to_be_clickable((
    By.XPATH, "//svg//title[normalize-space()='4 - Empenhos']/ancestor::a[1]"
))).click()

wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-empenho-estado-listagem//button[contains(normalize-space(.),'Incluir Empenho')]"
))).click()

modal_ano = wait.until(EC.visibility_of_element_located((
    By.XPATH, "//input-number[@name='ano']//input"
)))
modal_ano.clear()
modal_ano.send_keys("2025")

modal_data_empenho = driver.find_element(
    By.XPATH, "//input-date[@name='data']//input"
)
modal_data_empenho.clear()
modal_data_empenho.send_keys("06/07/2025")

modal_ug = driver.find_element(
    By.XPATH, "//input-text-mask[@name='condigoUnidadeGestoraSiafe']//input"
)
modal_ug.clear()
modal_ug.send_keys("100100")

modal_numero_empenho = driver.find_element(
    By.XPATH, "//input-text-mask[@name='numeroEmpenho']//input"
)
modal_numero_empenho.clear()
modal_numero_empenho.send_keys("2025NE01402")

modal_valor_empenho = driver.find_element(
    By.XPATH, "//input-currency[@name='valorEmpenho']//input[@currencymask]"
)
modal_valor_empenho.clear()
modal_valor_empenho.send_keys(valor_pagina1)

wait.until(EC.element_to_be_clickable((
    By.XPATH, "//app-empenho-estado-modal-cadastro//button[contains(normalize-space(.),'Salvar')]"
))).click()
