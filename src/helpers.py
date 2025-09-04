# helpers.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

# Seletores típicos de overlay/loader do seu app (Angular, block-ui, spinners etc.)
_OVERLAY_SELECTORS = [
    ".block-ui-overlay",
    ".block-ui.active",
    ".ngx-loading",
    ".loading-overlay",
    ".loading",
    ".throbber",
    ".spinner",
]

def _has_busy_overlays(driver) -> bool:
    """
    Retorna True se algum overlay/loader está visível.
    Usa querySelector para qualquer seletor da lista _OVERLAY_SELECTORS.
    """
    js = """
      const sels = arguments[0];
      for (let i = 0; i < sels.length; i++) {
        const el = document.querySelector(sels[i]);
        if (!el) continue;
        const s = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        if (s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0) {
          return true;
        }
      }
      return false;
    """
    try:
        return bool(driver.execute_script(js, _OVERLAY_SELECTORS))
    except Exception:
        # Se o JS falhar por qualquer motivo, não bloqueie o fluxo
        return False


def wait_for_page_complete(driver, wait, extra_delay: float = 0.15, overlay_timeout: float = 4.0):
    """
    Espera:
      1) document.readyState == 'complete'
      2) ausência de overlays/loader "reais" (timeout curto)
      3) pequeno respiro (extra_delay)
    """
    # 1) DOM pronto
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    # 2) overlays reais (timeout curto)
    try:
        WebDriverWait(driver, overlay_timeout, poll_frequency=0.2).until(
            lambda d: _has_busy_overlays(d) is False
        )
    except TimeoutException:
        # segue mesmo que algum overlay residual persista
        pass

    # 3) respiro
    if extra_delay:
        time.sleep(extra_delay)


def js_select_value(driver, select_el, value):
    """
    Define value em <select> escondido (Angular) e dispara eventos.
    """
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
        select_el, value
    )


def fill_input(driver, wait, selector, value, by: By = By.CSS_SELECTOR, fire_events: bool = True):
    """
    Preenche inputs/textareas com scroll central, limpa com Ctrl+A+Del e dispara eventos.
    Retorna o elemento.
    """
    el = wait.until(EC.presence_of_element_located((by, selector)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)

    try:
        el.click()
    except Exception:
        pass

    # Limpeza robusta
    try:
        el.clear()  # rápido quando suportado
    except Exception:
        pass
    try:
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
    except Exception:
        pass

    if value not in (None, ""):
        el.send_keys(value)

    if fire_events:
        # Garante que Angular/validações captem a mudança
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('blur', {bubbles:true}));",
            el
        )
    return el


def aguardar_carregamento_final(driver, wait, timeout: float = 6.0):
    """
    Espera final curta para sumir overlays/spinners reais.
    """
    try:
        print("[DEBUG] Aguardando carregamento completo final...")
        WebDriverWait(driver, timeout, poll_frequency=0.2).until(
            lambda d: _has_busy_overlays(d) is False
        )
        time.sleep(0.1)
        print("[✔] Página carregada e pronta.")
    except TimeoutException:
        print("[⚠] Timeout: overlays ainda aparentes; seguindo assim mesmo.")
