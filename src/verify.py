# verify.py
# -*- coding: utf-8 -*-
"""
Conferencia pos-gravacao (read-back).

Apos preencher cada aba, le de volta o que o SIGFIS efetivamente mostrou nos
grids e compara com o que deveria ter sido gravado. "Sem excecao" NAO e' o
mesmo que "gravado certo" — estas funcoes existem para pegar valor trocado,
empenho com numero errado etc. ANTES de o registro ser dado como concluido.

Cada funcao retorna uma tupla (ok: bool, mensagem: str) e nunca lanca excecao.
"""

import re
from selenium.webdriver.common.by import By

from helpers import norm_money_digits
from logger import get_logger

log = get_logger("verify")


def _digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _alnum(s) -> str:
    return "".join(ch for ch in str(s or "") if ch.isalnum()).upper()


def ler_id_dispensa(driver) -> str:
    """Le o 'Nº Dispensa SIGFIS' gerado apos salvar os Dados Basicos."""
    for sel in ('input-text[name="id"] input', '#input-text-0'):
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            val = (el.get_attribute("value") or "").strip()
            if val:
                return val
        except Exception:
            continue
    return ""


def _ultima_linha(driver, grid_id):
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, f"#{grid_id} tbody tr")
        rows = [r for r in rows if r.find_elements(By.CSS_SELECTOR, "td")
                and "empty-results" not in (r.get_attribute("innerHTML") or "")]
        return rows[-1] if rows else None
    except Exception:
        return None


def verificar_item(driver, cfg):
    """Confere a ultima linha do grid de Itens (Preco Total x VALOR)."""
    try:
        row = _ultima_linha(driver, "datagrid-1")
        if row is None:
            return False, "Item: nenhuma linha no grid"
        tds = row.find_elements(By.CSS_SELECTOR, "td")
        total = tds[6].text if len(tds) > 6 else ""
        if norm_money_digits(total) == norm_money_digits(cfg.get("VALOR")):
            return True, f"Item OK (total={total.strip()})"
        return False, f"Item divergente: grid={total.strip()} esperado={cfg.get('VALOR')}"
    except Exception as e:
        return False, f"Item: erro ao conferir ({e})"


def verificar_documento(driver, cfg):
    """Confere presenca do documento no grid (se houver FILE_PATH)."""
    try:
        if not str(cfg.get("FILE_PATH", "")).strip():
            return True, "Documento: sem arquivo (FILE_PATH vazio) - ignorado"
        row = _ultima_linha(driver, "datagrid-0")
        if row is None:
            return False, "Documento: nao apareceu no grid"
        return True, "Documento OK (presente no grid)"
    except Exception as e:
        return False, f"Documento: erro ao conferir ({e})"


def verificar_empenho(driver, cfg):
    """Confere a ultima linha do grid de Empenhos (Numero e Valor)."""
    try:
        row = _ultima_linha(driver, "datagrid-2")
        if row is None:
            return False, "Empenho: nenhuma linha no grid"
        tds = row.find_elements(By.CSS_SELECTOR, "td")
        numero = tds[4].text if len(tds) > 4 else ""
        valor = tds[5].text if len(tds) > 5 else ""
        n_ok = _alnum(numero) == _alnum(cfg.get("NUM_EMPENHO"))
        v_ok = norm_money_digits(valor) == norm_money_digits(cfg.get("VALOR"))
        if n_ok and v_ok:
            return True, f"Empenho OK (n={numero.strip()}, v={valor.strip()})"
        falhas = []
        if not n_ok:
            falhas.append(f"numero grid={numero.strip()} esperado={cfg.get('NUM_EMPENHO')}")
        if not v_ok:
            falhas.append(f"valor grid={valor.strip()} esperado={cfg.get('VALOR')}")
        return False, "Empenho divergente: " + "; ".join(falhas)
    except Exception as e:
        return False, f"Empenho: erro ao conferir ({e})"
