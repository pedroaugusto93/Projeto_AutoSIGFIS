# page_pesquisa.py
# -*- coding: utf-8 -*-
"""
Opera a tela de CONSULTA de Dispensas do SIGFIS:
  - pesquisa um numero de processo;
  - percorre todas as paginas de resultado;
  - para cada dispensa ENVIADA (que tem o botao de recibo), baixa o recibo em PDF.

A dispensa "tem recibo" quando a linha possui o botao de prancheta (fa-clipboard).
Linhas sem esse botao (ex.: "Excluido após Envio") sao puladas.
"""

import os
import re
import time

import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from helpers import wait_for_page_complete, safe_click
from logger import get_logger
import recibo_pdf

log = get_logger("pesquisa")

GRID = "#datagrid-0"


def _achar_campo_processo(driver, wait):
    # 1) campo com maxlength=200 (caracteristico do "Numero do Processo");
    # 2) senao, primeiro input de texto visivel da tela de consulta.
    for css in ("input[maxlength='200']", "input.form-control[type='text']", "input[type='text']"):
        els = [e for e in driver.find_elements(By.CSS_SELECTOR, css) if e.is_displayed()]
        if els:
            return els[0]
    raise RuntimeError("Campo de numero do processo nao encontrado na tela de consulta.")


def pesquisar(driver, wait, processo):
    """Abre a consulta, preenche o processo e clica em Pesquisar."""
    driver.get(config.URL_CONSULTA)
    wait_for_page_complete(driver, wait)

    campo = _achar_campo_processo(driver, wait)
    campo.clear()
    campo.send_keys(str(processo).strip())

    botao = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(normalize-space(.),'Pesquisar')]")))
    safe_click(driver, wait, botao)
    wait_for_page_complete(driver, wait)
    # aguarda a tabela responder (linhas ou "0 registros")
    try:
        WebDriverWait(driver, 10, 0.3).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, f"{GRID} tbody tr")
            or "registros" in (d.page_source or "").lower())
    except Exception:
        pass
    time.sleep(0.4)


def _ler_linhas_pagina(driver):
    """Retorna a lista de dispensas da pagina atual (com flag de recibo)."""
    js = r"""
    return Array.from(document.querySelectorAll('#datagrid-0 tbody tr')).map(tr => {
      const tds = tr.querySelectorAll('td');
      const temRecibo = !!tr.querySelector('td.action button i.fa-clipboard');
      const t = i => (tds[i] ? (tds[i].innerText||'').trim() : '');
      return { dispensa: t(1), protocolo: t(3), fornecedor: t(6), situacao: t(21), temRecibo: temRecibo };
    }).filter(r => r.dispensa);
    """
    try:
        return driver.execute_script(js) or []
    except Exception as e:
        log.error("Falha ao ler as linhas da pagina: %s", e)
        return []


def _clicar_recibo(driver, wait, dispensa_id):
    """Acha a linha pela dispensa e clica no botao de recibo (fa-clipboard)."""
    btn = driver.execute_script(r"""
      const id = arguments[0];
      for (const tr of document.querySelectorAll('#datagrid-0 tbody tr')) {
        const tds = tr.querySelectorAll('td');
        if (tds[1] && (tds[1].innerText||'').trim() === id) {
          const i = tr.querySelector('td.action button i.fa-clipboard');
          return i ? i.closest('button') : null;
        }
      }
      return null;
    """, dispensa_id)
    if not btn:
        return False
    safe_click(driver, wait, btn)
    # espera o modal do recibo aparecer
    try:
        WebDriverWait(driver, 8, 0.2).until(lambda d: d.execute_script(
            "return !!Array.from(document.querySelectorAll('.modal-content,.modal-body'))"
            ".find(e=>/Recibo de Entrega do Ato/i.test(e.textContent||''));"))
        return True
    except Exception:
        return False


def _fechar_modal(driver):
    try:
        driver.execute_script(r"""
          const m = document.querySelector('.modal.show, modal-container, .modal');
          if (!m) return;
          let b = Array.from(m.querySelectorAll('button')).find(x => /cancelar/i.test(x.textContent||''))
                  || m.querySelector('.close, [class*="close"]');
          if (b) b.click();
        """)
    except Exception:
        pass
    try:
        WebDriverWait(driver, 4, 0.2).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".modal.show")))
    except Exception:
        pass


def _pagina_ativa(driver):
    els = driver.find_elements(By.CSS_SELECTOR, "ul.pagination li.pagination-page.active a")
    return els[0].text.strip() if els else ""


def _proxima_pagina(driver, wait):
    lis = driver.find_elements(By.CSS_SELECTOR, "ul.pagination li.pagination-next")
    if not lis or "disabled" in (lis[0].get_attribute("class") or ""):
        return False
    antes = _pagina_ativa(driver)
    a = lis[0].find_element(By.CSS_SELECTOR, "a")
    driver.execute_script("arguments[0].click();", a)
    try:
        WebDriverWait(driver, 8, 0.2).until(lambda d: _pagina_ativa(d) != antes)
    except Exception:
        pass
    wait_for_page_complete(driver, wait)
    time.sleep(0.3)
    return True


def _nome_arquivo(processo, dispensa, fornecedor):
    base = f"{processo}_{dispensa}_{fornecedor}".strip("_")
    base = re.sub(r'[\\/:*?"<>|\r\n\t]+', "", base)
    base = re.sub(r"\s+", " ", base).strip()
    return (base[:150] or "recibo") + ".pdf"


def baixar_recibos_do_processo(driver, wait, processo, pasta_individuais=None):
    """
    Pesquisa o processo e baixa o recibo de cada dispensa enviada.
    Retorna a lista de caminhos PDF salvos.
    """
    if pasta_individuais is None:
        pasta_individuais = os.path.join(config.RECIBOS_LOTE_DIR, "individuais")
    os.makedirs(pasta_individuais, exist_ok=True)

    pesquisar(driver, wait, processo)

    salvos = []
    vistos = set()
    pagina = 1
    MAX_PAGINAS = 200
    while pagina <= MAX_PAGINAS:
        linhas = _ler_linhas_pagina(driver)
        if not linhas:
            log.info("Processo %s: nenhuma dispensa na pagina %d.", processo, pagina)
        for r in linhas:
            disp = r["dispensa"]
            if disp in vistos:
                continue
            vistos.add(disp)
            if not r["temRecibo"]:
                log.info("  Dispensa %s (%s) sem recibo [situacao=%s]; pulando.",
                         disp, r["fornecedor"], r["situacao"] or "?")
                continue
            if not _clicar_recibo(driver, wait, disp):
                log.warning("  Dispensa %s: nao consegui abrir o recibo; pulando.", disp)
                continue
            dest = os.path.join(pasta_individuais, _nome_arquivo(processo, disp, r["fornecedor"]))
            ok, _proto = recibo_pdf.capturar_recibo_nova_aba(driver, wait, dest)
            if ok:
                salvos.append(dest)
            _fechar_modal(driver)

        if not _proxima_pagina(driver, wait):
            break
        pagina += 1

    log.info("Processo %s: %d recibo(s) baixado(s) de %d dispensa(s).",
             processo, len(salvos), len(vistos))
    return salvos
