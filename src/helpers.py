# helpers.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from logger import get_logger

log = get_logger("helpers")

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
    log.debug("select -> %s", value)
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
    # Log enxuto: o detalhe campo a campo vai para o arquivo de log (DEBUG)
    val_preview = "" if value in (None, "") else str(value)
    log.debug("fill  %s = %r", selector, val_preview)

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


def confirm_or_warn(driver, condition, descricao: str, timeout: float = 3.0) -> bool:
    """
    Aguarda `condition` por `timeout`. Em vez de estourar TimeoutException com
    'Message:' vazio (que travava o registro inteiro), registra um WARNING e segue.
    Retorna True se a condição foi satisfeita, False caso contrário.
    """
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.2).until(condition)
        return True
    except TimeoutException:
        log.warning("Confirmacao nao satisfeita: %s", descricao)
        return False


def aguardar_carregamento_final(driver, wait, timeout: float = 6.0):
    """
    Espera final curta para sumir overlays/spinners reais.
    """
    try:
        log.debug("Aguardando carregamento completo final...")
        WebDriverWait(driver, timeout, poll_frequency=0.2).until(
            lambda d: _has_busy_overlays(d) is False
        )
        time.sleep(0.1)
        log.debug("Pagina carregada e pronta.")
    except TimeoutException:
        log.warning("Timeout: overlays ainda aparentes; seguindo assim mesmo.")


def safe_click(driver, wait, locator_or_element, scroll_block: str = 'center', use_js: bool = True):
    """Click robusto com scroll e fallback JS.
    Aceita um locator (tuple By, selector) OU um WebElement.
    """
    try:
        from selenium.webdriver.remote.webelement import WebElement
    except Exception:
        WebElement = None

    if WebElement and isinstance(locator_or_element, WebElement):
        el = locator_or_element
    else:
        el = wait.until(EC.element_to_be_clickable(locator_or_element))

    try:
        driver.execute_script(f"arguments[0].scrollIntoView({{block:'{scroll_block}'}});", el)
    except Exception:
        pass

    if use_js:
        try:
            driver.execute_script("arguments[0].click();", el)
            return el
        except Exception:
            pass
    # fallback to native click
    el.click()
    return el


def swal_click_confirm(driver, wait, *labels, timeout: float = 5.0):
    """Clica no botão de confirmação do SweetAlert2.
    Se *labels for fornecido, tenta casar texto (ex.: 'OK', 'Sim', 'Emitir').
    Retorna True se conseguiu clicar, False caso contrário.
    """
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.2).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.swal2-container.swal2-shown, div.swal2-popup.swal2-modal"))
        )
    except Exception:
        return False

    # Tenta via API primeiro
    try:
        api = driver.execute_script("if (window.Swal && Swal.isVisible()) { Swal.clickConfirm(); return true } return false;")
        if api:
            return True
    except Exception:
        pass

    # Fallback: encontra botões .swal2-confirm
    btns = driver.find_elements(By.CSS_SELECTOR, ".swal2-container.swal2-shown button.swal2-confirm, div.swal2-popup.swal2-modal button.swal2-confirm")
    if not btns:
        return False

    if labels:
        wants = [str(x).strip().lower() for x in labels if x]
        for b in btns:
            try:
                if not b.is_displayed():
                    continue
                txt = (b.text or "").strip().lower()
                if any(w in txt for w in wants):
                    try:
                        driver.execute_script("arguments[0].focus(); arguments[0].click();", b)
                    except Exception:
                        b.click()
                    return True
            except Exception:
                continue

    # Sem labels ou nenhuma casou: clica no primeiro visível
    for b in btns:
        try:
            if b.is_displayed():
                try:
                    driver.execute_script("arguments[0].click();", b)
                except Exception:
                    b.click()
                return True
        except Exception:
            continue
    return False


def norm_money_digits(raw: str) -> str:
    """Normaliza valor monetário em uma string SÓ de dígitos adequada para inputs mascarados de moeda.
    Exemplos:
      '1.234,56' -> '123456'
      '1234.56'  -> '123456'
      '100'      -> '10000' (interpreta como 100,00)
      ''         -> ''
    Regras:
      - Remove tudo que não for dígito ou separador decimal (vírgula/ponto).
      - Se houver separador decimal, mantém 2 casas (zerando/podando se necessário) e depois remove o separador.
      - Se NÃO houver separador, assume que o valor já está em reais e adiciona '00' de centavos.
    """
    import re as _re
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    # detecta separador decimal (última vírgula ou ponto)
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    sep_idx = max(last_comma, last_dot)

    if sep_idx >= 0:
        int_part = _re.sub(r"\D", "", s[:sep_idx])
        frac_part = _re.sub(r"\D", "", s[sep_idx+1:])
        frac_part = (frac_part + "00")[:2] if frac_part else "00"
        out = (int_part or "0") + frac_part
        out = out.lstrip("0")
        if len(out) < 1:
            out = "0"
        return out
    else:
        only_digits = _re.sub(r"\D", "", s)
        out = (only_digits or "0") + "00"
        out = out.lstrip("0")
        return out or "0"
