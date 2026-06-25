# recibo_pdf.py
# -*- coding: utf-8 -*-
"""
Captura o modal de recibo do SIGFIS em PDF SEM destruir a pagina atual.

Usado pelo fluxo de "baixar recibos" (page_pesquisa), onde a tabela de
resultados precisa continuar viva para processar as outras linhas e paginar.
Tecnica: le o cartao do recibo da aba atual, abre uma ABA NOVA limpa, recria
o recibo la (copiando as folhas de estilo do SIGFIS), gera o PDF via CDP
(Page.printToPDF) com a folha encaixando no conteudo, e fecha a aba nova.

(O fluxo de ENVIO usa a captura propria em page_enviar.py, que pode ser
destrutiva porque navega para outra pagina logo depois.)
"""

import os
import time
import base64

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from logger import get_logger

log = get_logger("recibo_pdf")

# Espera o conteudo do recibo carregar de fato (protocolo presente, sem "Carregando...").
_JS_RECIBO_PRONTO = r"""
const el = Array.from(document.querySelectorAll('.modal-content,.modal-body'))
                .find(e => /Recibo de Entrega do Ato/i.test(e.textContent||''));
if (!el) return false;
const t = (el.textContent || '');
return !/Carregando/i.test(t) && /\d+-\d+\/\d{4}/.test(t);
"""


def _esperar_recibo_pronto(driver, timeout=15.0):
    try:
        WebDriverWait(driver, timeout, 0.3).until(
            lambda d: d.execute_script(_JS_RECIBO_PRONTO))
        return True
    except Exception:
        return False

# Le o cartao do recibo (sem botoes) e o protocolo. NAO copia estilos do SIGFIS
# de proposito: os estilos do site trazem a versao de "impressao" do recibo junto,
# o que causa duplicacao/ordem trocada. Igual ao page_enviar, renderizamos limpo.
_JS_COLETAR = r"""
const re = /Recibo de Entrega do Ato/i;
let card = Array.from(document.querySelectorAll('.modal-content')).find(el => re.test(el.textContent||''));
if (!card) {
  const host = Array.from(document.querySelectorAll('.modal-body, .modal-dialog, .modal, modal-container'))
                    .find(el => re.test(el.textContent||''));
  if (host) card = host.querySelector('.modal-content') || host.querySelector('.modal-body') || host;
}
if (!card) return null;
const clone = card.cloneNode(true);
clone.querySelectorAll('.modal-footer, button, .close, [class*="close"]').forEach(e => e.remove());
const txt = (card.textContent || '').replace(/\s+/g,' ');
let protocolo = '';
const m = txt.match(/Protocolo[^\d]*?(\d+-\d+\/\d{4})/i);
if (m) protocolo = m[1];
return { html: clone.outerHTML, protocolo: protocolo };
"""

# Monta a aba nova com o recibo e CSS limpo proprio (sem estilo do SIGFIS),
# identico ao metodo aprovado do page_enviar. Folha encaixa no conteudo.
_JS_ESCREVER = r"""
const d = arguments[0];
const W = 760;
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
  + '<div id="__rw__">' + d.html + '</div>';
window.scrollTo(0,0);
"""


def capturar_recibo_nova_aba(driver, wait, dest_path, espera_layout=0.3):
    """
    Captura o recibo aberto (modal na aba atual) para `dest_path`, sem destruir
    a pagina. Retorna (ok: bool, protocolo: str).
    """
    aba_grid = driver.current_window_handle

    # espera o recibo terminar de carregar (evita salvar a tela "Carregando...")
    if not _esperar_recibo_pronto(driver):
        log.warning("Recibo nao terminou de carregar a tempo; pulando esta captura.")
        return False, ""

    try:
        dados = driver.execute_script(_JS_COLETAR)
    except Exception as e:
        log.error("Falha ao ler o recibo da tela: %s", e)
        return False, ""
    if not dados or not dados.get("html"):
        log.error("Recibo nao encontrado na tela (modal nao abriu?).")
        return False, ""

    protocolo = dados.get("protocolo", "") or ""
    nova = None
    try:
        driver.switch_to.new_window('tab')
        nova = driver.current_window_handle
        driver.execute_script(_JS_ESCREVER, dados)
        time.sleep(espera_layout)  # instante para o layout assentar antes de imprimir

        pasta = os.path.dirname(dest_path)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        res = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "preferCSSPageSize": True,
            "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
        })
        data = res.get("data") if isinstance(res, dict) else None
        if not data:
            log.error("printToPDF nao retornou dados; recibo nao salvo.")
            return False, protocolo
        with open(dest_path, "wb") as f:
            f.write(base64.b64decode(data))
        log.info("Recibo salvo: %s%s", dest_path, f" (protocolo {protocolo})" if protocolo else "")
        return True, protocolo
    except Exception as e:
        log.error("Falha ao gerar o PDF do recibo (%s).", e)
        return False, protocolo
    finally:
        # fecha a aba nova e volta para a aba da tabela
        try:
            if nova and nova in driver.window_handles:
                driver.switch_to.window(nova)
                driver.close()
        except Exception:
            pass
        try:
            driver.switch_to.window(aba_grid)
        except Exception:
            pass
