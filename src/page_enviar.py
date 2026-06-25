# page_enviar.py
# -*- coding: utf-8 -*-
"""
Acao IRREVERSIVEL: transmite a dispensa ao TCE-RJ e salva o recibo em PDF.

Fluxo no site:
  1) clica "Enviar ao TCE"
  2) confirma o SweetAlert "Sim"
  3) confirma o SweetAlert "Emitir Recibo"
  4) o recibo aparece como um modal SOBRE a pagina de pesquisa; em vez de clicar
     "Imprimir" (que abre a janela NATIVA do Chrome, fora do alcance do Selenium),
     ISOLAMOS so o cartao do recibo (removendo o fundo e o posicionamento fixo) e
     capturamos o PDF pelo Chrome DevTools Protocol (Page.printToPDF), gravando no
     caminho/arquivo desejado.

So deve ser chamada para registros 100% OK e apenas quando config.ENVIAR_AO_TCE
for True (a decisao fica em main.py).

Retorno de enviar_ao_tce():
  True  -> envio confirmado (clicou "Sim");
  False -> envio incerto (a confirmacao nao apareceu).
O recibo em PDF e best-effort: se falhar, o envio NAO e revertido; apenas
registra-se um aviso no log.
"""

import os
import re
import time
import base64

from selenium.webdriver.common.by import By
from helpers import wait_for_page_complete, safe_click, swal_click_confirm
from logger import get_logger
import config

log = get_logger("enviar")

_BTN_ENVIAR = "//button[contains(normalize-space(.),'Enviar ao TCE')]"

# JS: localiza o cartao do recibo, extrai o protocolo e ISOLA o recibo na pagina
# (substitui o body so pelo recibo, em fluxo normal) para o PDF sair limpo e em 1 pagina.
_JS_ISOLAR_RECIBO = r"""
const re = /Recibo de Entrega do Ato/i;
// pega o CARTAO do recibo, nunca o modal inteiro
let card = Array.from(document.querySelectorAll('.modal-content')).find(el => re.test(el.textContent||''));
if (!card) {
  const host = Array.from(document.querySelectorAll('.modal-body, .modal-dialog, .modal, modal-container'))
                    .find(el => re.test(el.textContent||''));
  if (host) card = host.querySelector('.modal-content') || host.querySelector('.modal-body') || host;
}
if (!card) return null;
// remove os botoes (Cancelar/Imprimir) e o "x" de fechar do recibo antes de imprimir
card.querySelectorAll('.modal-footer, button, .close, [class*="close"]').forEach(el => el.remove());
const txt = (card.textContent || '').replace(/\s+/g,' ');
let protocolo = '';
const m = txt.match(/Protocolo[^\d]*?(\d+-\d+\/\d{4})/i);
if (m) protocolo = m[1];
const html = card.outerHTML;
const W = 760; // largura do recibo (px)
document.head.innerHTML = '<meta charset="utf-8">';
document.documentElement.setAttribute('style','background:#fff;margin:0;padding:0;height:auto;min-height:0;');
document.body.setAttribute('style','background:#fff;margin:0;padding:0;height:auto;min-height:0;');
document.body.innerHTML =
  '<style>'
  + '@page { size: ' + W + 'px auto; margin: 10mm; }'
  + 'html, body { background:#fff !important; }'
  + '#__rw__, #__rw__ * { box-sizing:border-box; }'
  + '#__rw__ { width:' + W + 'px; margin:0; padding:0; background:#fff; color:#000; font-family:Arial,Helvetica,sans-serif; }'
  + '#__rw__ .modal-content,#__rw__ .modal-body,#__rw__ .modal-dialog,#__rw__ .modal {'
  + '  width:100%!important; max-width:none!important; min-height:0!important; height:auto!important;'
  + '  margin:0!important; box-shadow:none!important; border:none!important; position:static!important;'
  + '  transform:none!important; background:#fff!important; overflow:visible!important; }'
  + '#__rw__ table { width:100%!important; }'
  + '</style>'
  + '<div id="__rw__">' + html + '</div>';
window.scrollTo(0,0);
return protocolo;
"""


def _visiveis(driver, xpath):
    achados = []
    for b in driver.find_elements(By.XPATH, xpath):
        try:
            if b.is_displayed():
                achados.append(b)
        except Exception:
            continue
    return achados


def _nome_arquivo(cfg):
    """Nome do recibo = numero do processo + nome do fornecedor, sem chars proibidos."""
    proc = str(cfg.get("PROCESSO", "") or "").strip()
    forn = str(cfg.get("NOME_FORNECEDOR", "") or "").strip()
    base = f"{proc}_{forn}".strip("_")
    base = re.sub(r'[\\/:*?"<>|\r\n\t]+', "", base)   # proibidos no Windows
    base = re.sub(r"\s+", " ", base).strip()
    return (base[:150] or "recibo") + ".pdf"


def salvar_recibo_pdf(driver, wait, cfg):
    """Isola o recibo, extrai o protocolo e gera o PDF via CDP. Retorna o caminho salvo ou ''."""
    dest_dir = getattr(config, "RECIBO_DIR", "") or os.getcwd()
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except Exception as e:
        log.error("Nao consegui criar a pasta de recibos (%s): %s", dest_dir, e)
        return ""

    dest = os.path.join(dest_dir, _nome_arquivo(cfg))
    try:
        wait_for_page_complete(driver, wait)
    except Exception:
        pass

    # Isola o recibo (so o cartao, fundo branco) e captura o protocolo. O tamanho
    # da folha e definido por CSS (@page size: W auto) e o Chrome encaixa no conteudo.
    try:
        protocolo = driver.execute_script(_JS_ISOLAR_RECIBO)
        if protocolo:
            log.info("Protocolo de entrega ao TCE: %s", protocolo)
        elif protocolo is None:
            log.warning("Nao localizei o cartao do recibo para isolar; o PDF pode sair com o fundo.")
        time.sleep(0.3)
    except Exception as e:
        log.warning("Falha ao isolar o recibo (%s); seguindo com a pagina inteira.", e)

    try:
        res = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "preferCSSPageSize": True,   # respeita o @page (size: W auto) -> folha encaixa no recibo
            "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
        })
        data = res.get("data") if isinstance(res, dict) else None
        if not data:
            log.error("printToPDF nao retornou dados; recibo nao salvo.")
            return ""
        with open(dest, "wb") as f:
            f.write(base64.b64decode(data))
        log.info("Recibo salvo em PDF: %s", dest)
        return dest
    except Exception as e:
        log.error("Falha ao gerar o PDF do recibo via CDP (%s). O ENVIO foi feito; "
                  "o recibo esta na tela para impressao manual, se necessario.", e)
        return ""


def enviar_ao_tce(driver, wait, cfg):
    botoes = _visiveis(driver, _BTN_ENVIAR)
    if not botoes:
        log.error("Botao 'Enviar ao TCE' nao encontrado/visivel; envio nao realizado.")
        return False

    handles_antes = set(driver.window_handles)
    try:
        aba_origem = driver.current_window_handle
    except Exception:
        aba_origem = None

    log.info("Clicando em 'Enviar ao TCE'...")
    safe_click(driver, wait, botoes[0])
    wait_for_page_complete(driver, wait)

    # 1) Confirmacao do envio ("Sim"). Esta e a etapa que de fato transmite.
    if not swal_click_confirm(driver, wait, 'Sim', 'Confirmar', 'OK', timeout=8):
        log.warning("Confirmacao 'Sim' do envio nao apareceu; envio INCERTO.")
        return False
    log.info("Confirmacao 'Sim' clicada (dispensa transmitida).")
    wait_for_page_complete(driver, wait)

    # 2) "Emitir Recibo" (segundo SweetAlert)
    if swal_click_confirm(driver, wait, 'Emitir Recibo', 'Emitir', 'OK', timeout=8):
        log.info("'Emitir Recibo' clicado.")
    else:
        log.warning("Dialogo 'Emitir Recibo' nao apareceu; tentando capturar o recibo mesmo assim.")
    wait_for_page_complete(driver, wait)

    # 3) O recibo pode abrir em NOVA ABA. Detecta e troca para ela.
    time.sleep(1.0)
    novos = set(driver.window_handles) - handles_antes
    aba_recibo = None
    if novos:
        aba_recibo = novos.pop()
        try:
            driver.switch_to.window(aba_recibo)
            wait_for_page_complete(driver, wait)
            log.info("Recibo aberto em nova aba.")
        except Exception as e:
            log.warning("Nao consegui trocar para a aba do recibo: %s", e)
            aba_recibo = None

    # 4) Isola o recibo, extrai o protocolo e salva o PDF (sem a janela nativa do Windows)
    salvar_recibo_pdf(driver, wait, cfg)

    # 5) Se abrimos uma aba so para o recibo, fecha e volta para a original
    if aba_recibo and aba_origem:
        try:
            driver.close()
        except Exception:
            pass
        try:
            driver.switch_to.window(aba_origem)
        except Exception:
            pass

    # O ENVIO foi confirmado em (1); o PDF e complementar.
    return True
