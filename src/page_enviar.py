# page_enviar.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from helpers import wait_for_page_complete


def enviar_e_imprimir(driver, wait, cfg):
    # ===================== Helpers =====================

    def wait_overlay_disappear():
        """Aguarda o overlay Angular sumir (quando presente)."""
        try:
            wait.until(EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, ".block-ui-overlay")
            ))
        except TimeoutException:
            pass

    def safe_click(locator, scroll=True):
        """Rebusca o elemento clicável e executa click via JS (evita intercept/anim.)."""
        el = wait.until(EC.element_to_be_clickable(locator))
        if scroll:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)
        return el

    def achar_botao_enviar():
        """Localiza o botão 'Enviar ao TCE' dentro de #BotoesComuns com vários fallbacks."""
        locators = [
            (By.XPATH, "//div[@id='BotoesComuns']//button[contains(@class,'btn-outline-success') and contains(normalize-space(.),'Enviar ao TCE')]"),
            (By.XPATH, "//div[@id='BotoesComuns']//button[.//i[contains(@class,'fa-save')]]"),
            (By.CSS_SELECTOR, "#BotoesComuns button.btn.btn-outline-success"),
            (By.XPATH, "//button[contains(@class,'btn-outline-success') and contains(normalize-space(.),'Enviar ao TCE')]"),
        ]
        last_exc = None
        for loc in locators:
            try:
                return wait.until(EC.element_to_be_clickable(loc))
            except Exception as e:
                last_exc = e
        raise last_exc if last_exc else Exception("Botão 'Enviar ao TCE' não encontrado.")

    def _visible_swal_container():
        return wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.swal2-container.swal2-shown, div.swal2-popup.swal2-modal")
        ))

    def _click_swal_confirm_with_labels(*labels):
        """No SweetAlert2 visível, clica .swal2-confirm cujo texto contenha um dos rótulos."""
        try:
            _visible_swal_container()
        except TimeoutException:
            return False

        try:
            btns = driver.find_elements(
                By.CSS_SELECTOR,
                ".swal2-container.swal2-shown button.swal2-confirm, div.swal2-popup.swal2-modal button.swal2-confirm"
            )
        except Exception:
            btns = []

        for label in labels:
            want = label.lower()
            for b in btns:
                try:
                    if not b.is_displayed():
                        continue
                    txt = (b.text or "").strip().lower()
                    if want in txt:
                        driver.execute_script("arguments[0].focus(); arguments[0].click();", b)
                        try:
                            wait.until(EC.staleness_of(b))
                        except Exception:
                            wait.until(EC.invisibility_of_element_located(
                                (By.CSS_SELECTOR, "div.swal2-popup.swal2-modal")
                            ))
                        wait_overlay_disappear()
                        wait_for_page_complete(driver, wait)
                        return True
                except StaleElementReferenceException:
                    return _click_swal_confirm_with_labels(label)
        return False

    def click_recibo_cancelar_js():
        """
        Fecha o popup de 'Recibo' clicando no botão 'Cancelar' via JS.
        Não depende de classes Bootstrap; procura por um botão visível com texto 'Cancelar'
        preferencialmente dentro de um rodapé de popup.
        """
        js = r"""
        const isVisible = el => {
          if (!el) return false;
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
        };

        // 1) Tenta Cancelar dentro de um 'footer' do popup (mais preciso)
        let btns = Array.from(document.querySelectorAll(
          ".modal-footer button, .dialog-footer button, .actions button, button.btn"
        ));
        let alvo = btns.find(b => /cancelar/i.test(b.textContent || b.innerText) && isVisible(b));
        if (!alvo) {
          // 2) Fallback global: qualquer botão 'Cancelar' visível
          btns = Array.from(document.querySelectorAll("button"));
          alvo = btns.find(b => /cancelar/i.test(b.textContent || b.innerText) && isVisible(b));
        }
        if (alvo) {
          alvo.scrollIntoView({block:'center'});
          alvo.click();
          return true;
        }
        return false;
        """
        try:
            return bool(driver.execute_script(js))
        except Exception:
            return False

    # ===================== Fluxo =====================

    wait_overlay_disappear()

    # [1] Enviar ao TCE
    print("[1] Localizando e clicando em 'Enviar ao TCE'")
    btn = achar_botao_enviar()
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    driver.execute_script("arguments[0].click();", btn)

    # [2] Confirmações (até 2 em sequência): prioriza 'Emitir', senão 'Sim'
    print("[2] Confirmando modais ('Emitir' / 'Sim')")
    confirmed_once = _click_swal_confirm_with_labels("Emitir", "Sim")
    if confirmed_once:
        _click_swal_confirm_with_labels("Emitir", "Sim")

    wait_overlay_disappear()
    wait_for_page_complete(driver, wait)

    # [3] Popup de Recibo → clicar CANCELAR via JS
    print("[3] Fechando popup 'Recibo' com 'Cancelar'")
    ok = click_recibo_cancelar_js()
    if ok:
        # aguarda sumir qualquer diálogo/popup visível após o clique
        try:
            wait.until(EC.invisibility_of_element_located(
                (By.XPATH, "//*[contains(normalize-space(.),'Recibo')][ancestor::*[contains(@style,'z-index') or contains(@class,'dialog') or contains(@class,'modal')]][1]")
            ))
        except Exception:
            pass
        print("[✔] Popup 'Recibo' fechado (Cancelar).")
    else:
        print("[i] Não achei botão 'Cancelar' do Recibo; seguindo mesmo assim.")

    wait_overlay_disappear()
    wait_for_page_complete(driver, wait)
    print("[✔] Envio concluído.")
