# helpers.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

#   Função para esperar a página carregar completamente
def wait_for_page_complete(driver, wait, extra_delay=0.5):
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    try:
        spinner = (By.CSS_SELECTOR, ".loading-overlay, .spinner, .ng-star-inserted")
        wait.until(EC.invisibility_of_element_located(spinner))
    except:
        pass
    time.sleep(extra_delay)

#    Função para selecionar valor em um <select> via JavaScript
def js_select_value(driver, select_el, value):
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('change'));",
        select_el, value
    )

#    Função para preencher um campo de input
def fill_input(driver, wait, selector, value, by=By.CSS_SELECTOR):
    # Espera o input estar presente, rola até ele, limpa e preenche
    inp = wait.until(EC.presence_of_element_located((by, selector)))
    # Rola até o input
    driver.execute_script("arguments[0].scrollIntoView(true);", inp)
    # Limpa e preenche
    inp.clear()
    # Preenche caractere a caractere para simular digitação humana
    inp.send_keys(value)
    return inp

#    Função para aguardar carregamento final
def aguardar_carregamento_final(driver, wait, timeout=20):
    #    Aguarda a ausência de elementos .loading ou throbber para garantir que a página está pronta.
    try:
        #print("[DEBUG] Aguardando carregamento completo final antes de enviar...")
        wait.until_not(EC.presence_of_element_located((By.CSS_SELECTOR, ".loading, .throbber, .spinner"))) # Ajuste o seletor conforme necessário
        time.sleep(1) # Pequeno atraso extra para garantir estabilidade
        #print("[✔] Página carregada e pronta.")
    except Exception:
        #print("[⚠] Timeout: elementos de carregamento ainda visíveis.")
        pass # Continua mesmo se der timeout

# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC

# def set_field_value(driver, wait, selector, value, by=By.CSS_SELECTOR):
#     """
#     Define valor em input, select nativo ou wrapper (<input-select>).
#     - Localiza por presence (DOM)
#     - Scroll até o centro
#     - Injeta valor da forma correta
#     - Valida que 'value' foi aplicado
#     Retorna o elemento alvo de valor (o input ou o <select> interno).
#     """
#     el = wait.until(EC.presence_of_element_located((by, selector)))
#     driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
#     tag = (el.tag_name or '').lower()

#     # Caso 1: input/textarea
#     if tag in ("input", "textarea"):
#         el.clear()
#         el.send_keys(str(value))
#         wait.until(lambda d: (el.get_attribute("value") or "").strip() == str(value).strip())
#         return el

#     # Caso 2: select nativo
#     if tag == "select":
#         driver.execute_script("""
#             arguments[0].value = arguments[1];
#             arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
#             arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
#         """, el, str(value))
#         wait.until(lambda d: el.get_attribute("value") == str(value))
#         return el

#     # Caso 3: wrapper (ex.: <input-select>) com <select> interno
#     try:
#         inner = el.find_element(By.TAG_NAME, "select")
#         driver.execute_script("""
#             arguments[0].value = arguments[1];
#             arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
#             arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
#         """, inner, str(value))
#         wait.until(lambda d: inner.get_attribute("value") == str(value))
#         return inner
#     except Exception:
#         raise Exception(f"Elemento '{selector}' não é input, select ou wrapper-select")

# def click_js(driver, wait, selector, by=By.CSS_SELECTOR):
#     el = wait.until(EC.presence_of_element_located((by, selector)))
#     driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
#     driver.execute_script("arguments[0].click();", el)
#     return el
