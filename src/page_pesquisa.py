# page_pesquisa.py
# -*- coding: utf-8 -*-
"""
Opera a tela de CONSULTA de Dispensas do SIGFIS:
  - pesquisa um numero de processo;
  - percorre todas as paginas de resultado;
  - para cada dispensa ENVIADA (que tem o botao de recibo), baixa o recibo em PDF.

A dispensa "tem recibo" quando a linha possui o botao de prancheta (fa-clipboard).
Linhas sem esse botao (ex.: "Excluido após Envio") sao puladas.

Protecoes:
  - usa especificamente o campo "Numero do Processo";
  - aguarda a grade AJAX realmente atualizar;
  - valida que cada linha pertence ao processo pesquisado antes de baixar.
"""

import os
import re
import time

import config
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from helpers import wait_for_page_complete, safe_click
from logger import get_logger
import recibo_pdf

log = get_logger("pesquisa")

GRID = "#datagrid-0"
INPUT_NUMERO_PROCESSO = 'input-text[name="NumeroProcesso"] input'


def _normalizar_processo(valor):
    return re.sub(r"\s+", "", str(valor or "").strip()).upper()


def _achar_campo_processo(driver, wait):
    """
    Localiza especificamente o campo 'Numero do Processo'.
    """
    try:
        return wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, INPUT_NUMERO_PROCESSO)
            )
        )
    except Exception as e:
        raise RuntimeError(
            "Campo 'Numero do Processo' nao encontrado na tela de consulta."
        ) from e


def _processos_na_grade(driver):
    """
    Le a coluna Numero do Processo da grade.
    """
    try:
        return driver.execute_script(r"""
            return Array.from(
                document.querySelectorAll('#datagrid-0 tbody tr')
            ).map(tr => {
                const tds = tr.querySelectorAll('td');
                if (!tds[2]) return '';
                return (tds[2].innerText || '').trim();
            }).filter(Boolean);
        """) or []
    except Exception:
        return []


def _sem_resultados(driver):
    texto = (driver.page_source or "").lower()

    indicadores = (
        "nenhum registro",
        "nenhum resultado",
        "0 registro",
        "0 registros",
    )

    return any(x in texto for x in indicadores)


def pesquisar(driver, wait, processo):
    """
    Abre a consulta, preenche especificamente o campo Numero do Processo,
    pesquisa e so retorna quando a grade estiver realmente filtrada.
    """
    processo = str(processo).strip()
    alvo = _normalizar_processo(processo)

    log.info("Pesquisando processo %s...", processo)

    driver.get(config.URL_CONSULTA)
    wait_for_page_complete(driver, wait)

    campo = _achar_campo_processo(driver, wait)

    campo.click()
    campo.send_keys(Keys.CONTROL, "a")
    campo.send_keys(Keys.DELETE)
    campo.send_keys(processo)

    try:
        WebDriverWait(driver, 10, 0.2).until(
            lambda d: _normalizar_processo(
                d.find_element(
                    By.CSS_SELECTOR,
                    INPUT_NUMERO_PROCESSO
                ).get_attribute("value")
            ) == alvo
        )
    except TimeoutException as e:
        raise RuntimeError(
            f"O SIGFIS nao manteve o numero do processo no campo: {processo}"
        ) from e

    log.info("Campo preenchido corretamente: %s", processo)

    try:
        botao = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "div.col-md-12 > button.btn.btn-outline-primary"
            ))
        )
    except Exception:
        botao = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(normalize-space(.),'Pesquisar')]"
            ))
        )

    safe_click(driver, wait, botao)

    # document.readyState pode ficar "complete" enquanto a grade ainda
    # esta sendo atualizada por AJAX, mas mantemos esta espera inicial.
    wait_for_page_complete(driver, wait)

    def pesquisa_concluida(d):
        processos_grade = _processos_na_grade(d)

        if processos_grade:
            normalizados = [
                _normalizar_processo(p)
                for p in processos_grade
            ]
            return alvo in normalizados

        return _sem_resultados(d)

    try:
        WebDriverWait(driver, 20, 0.25).until(pesquisa_concluida)
    except TimeoutException as e:
        encontrados = _processos_na_grade(driver)
        raise RuntimeError(
            "A pesquisa nao foi confirmada pelo SIGFIS. "
            f"Processo solicitado: {processo}. "
            f"Processos atualmente visiveis na grade: {encontrados}. "
            "Por seguranca, nenhum recibo sera baixado."
        ) from e

    processos_grade = _processos_na_grade(driver)

    if processos_grade:
        log.info(
            "Pesquisa confirmada. Processo %s encontrado na grade.",
            processo
        )
    else:
        log.info(
            "Pesquisa concluida. Processo %s sem registros.",
            processo
        )


def _ler_linhas_pagina(driver):
    """Retorna a lista de dispensas da pagina atual (com flag de recibo)."""
    js = r"""
    return Array.from(document.querySelectorAll('#datagrid-0 tbody tr')).map(tr => {
      const tds = tr.querySelectorAll('td');
      const temRecibo = !!tr.querySelector('td.action button i.fa-clipboard');
      const t = i => (tds[i] ? (tds[i].innerText||'').trim() : '');
      return {
        dispensa: t(1),
        processo: t(2),
        protocolo: t(3),
        fornecedor: t(6),
        situacao: t(21),
        temRecibo: temRecibo
      };
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

    try:
        WebDriverWait(driver, 8, 0.2).until(
            lambda d: d.execute_script(
                "return !!Array.from(document.querySelectorAll('.modal-content,.modal-body'))"
                ".find(e=>/Recibo de Entrega do Ato/i.test(e.textContent||''));"
            )
        )
        return True
    except Exception:
        return False


def _fechar_modal(driver):
    try:
        driver.execute_script(r"""
          const m = document.querySelector('.modal.show, modal-container, .modal');
          if (!m) return;
          let b = Array.from(m.querySelectorAll('button')).find(
                    x => /cancelar/i.test(x.textContent||'')
                  ) || m.querySelector('.close, [class*="close"]');
          if (b) b.click();
        """)
    except Exception:
        pass

    try:
        WebDriverWait(driver, 4, 0.2).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".modal.show"))
        )
    except Exception:
        pass


def _pagina_ativa(driver):
    els = driver.find_elements(
        By.CSS_SELECTOR,
        "ul.pagination li.pagination-page.active a"
    )
    return els[0].text.strip() if els else ""


def _proxima_pagina(driver, wait):
    lis = driver.find_elements(
        By.CSS_SELECTOR,
        "ul.pagination li.pagination-next"
    )

    if not lis or "disabled" in (lis[0].get_attribute("class") or ""):
        return False

    antes = _pagina_ativa(driver)
    a = lis[0].find_element(By.CSS_SELECTOR, "a")

    driver.execute_script("arguments[0].click();", a)

    try:
        WebDriverWait(driver, 8, 0.2).until(
            lambda d: _pagina_ativa(d) != antes
        )
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
        pasta_individuais = os.path.join(
            config.RECIBOS_LOTE_DIR,
            "individuais"
        )

    os.makedirs(pasta_individuais, exist_ok=True)

    pesquisar(driver, wait, processo)

    salvos = []
    vistos = set()
    pagina = 1
    MAX_PAGINAS = 200

    proc_esperado = _normalizar_processo(processo)

    while pagina <= MAX_PAGINAS:
        linhas = _ler_linhas_pagina(driver)

        if not linhas:
            log.info(
                "Processo %s: nenhuma dispensa na pagina %d.",
                processo,
                pagina
            )

        for r in linhas:
            proc_linha = _normalizar_processo(r.get("processo"))

            if proc_linha != proc_esperado:
                log.error(
                    "BLOQUEADO: a grade contem o processo %s, "
                    "mas estamos pesquisando %s. "
                    "Nenhum recibo desta linha sera baixado.",
                    r.get("processo"),
                    processo,
                )
                continue

            disp = r["dispensa"]

            if disp in vistos:
                continue

            vistos.add(disp)

            if not r["temRecibo"]:
                log.info(
                    "  Dispensa %s (%s) sem recibo [situacao=%s]; pulando.",
                    disp,
                    r["fornecedor"],
                    r["situacao"] or "?"
                )
                continue

            if not _clicar_recibo(driver, wait, disp):
                log.warning(
                    "  Dispensa %s: nao consegui abrir o recibo; pulando.",
                    disp
                )
                continue

            dest = os.path.join(
                pasta_individuais,
                _nome_arquivo(
                    processo,
                    disp,
                    r["fornecedor"]
                )
            )

            ok, _proto = recibo_pdf.capturar_recibo_nova_aba(
                driver,
                wait,
                dest
            )

            if ok:
                salvos.append(dest)

            _fechar_modal(driver)

        if not _proxima_pagina(driver, wait):
            break

        pagina += 1

    log.info(
        "Processo %s: %d recibo(s) baixado(s) de %d dispensa(s).",
        processo,
        len(salvos),
        len(vistos)
    )

    return salvos
