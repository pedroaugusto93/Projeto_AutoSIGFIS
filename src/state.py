# state.py
# -*- coding: utf-8 -*-
"""
Controle de duplicidade e retomada.

Guarda, num arquivo JSON (logs/estado_processados.json), quais registros já
geraram uma Dispensa no SIGFIS. A regra de "já feito" é simples e segura:

    -> um registro está "feito" quando possui um numero de Dispensa (dispensa_id).

Assim, se o lote cair no meio e for re-executado, registros que JA criaram uma
dispensa nao sao recriados (evita duplicar no sistema oficial), e o lote
"retoma" de onde parou. Quem falhou ANTES de criar a dispensa (sem dispensa_id)
e' re-tentado normalmente.

Optou-se por um arquivo de estado separado (e nao por reescrever a planilha)
para nao arriscar corromper o .xlsx via openpyxl.

Para reprocessar tudo do zero, defina a variavel de ambiente SIGFIS_FORCE=1
(cuidado: pode duplicar registros ja criados).
"""

import json
from datetime import datetime
from pathlib import Path

from logger import get_logger

log = get_logger("state")

STATE_DIR = Path(__file__).resolve().parent / "logs"
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "estado_processados.json"


def _canon(s) -> str:
    return "".join(ch for ch in str(s or "") if ch.isalnum()).upper()


def assinatura(cfg) -> str:
    """Chave estavel do registro: processo + numero de empenho + CPF/CNPJ."""
    return "|".join([
        _canon(cfg.get("PROCESSO")),
        _canon(cfg.get("NUM_EMPENHO")),
        _canon(cfg.get("CNPJ_FORNECEDOR")),
    ])


class EstadoProcessados:
    def __init__(self, force: bool = False):
        self.force = force
        self.data = {}
        if force:
            log.info("FORCE ativo: estado anterior sera ignorado (pode duplicar).")
        elif STATE_FILE.exists():
            try:
                self.data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                log.info("Estado carregado: %d registro(s) conhecido(s).", len(self.data))
            except Exception as e:
                log.warning("Nao foi possivel ler o estado (%s); comecando vazio.", e)

    def ja_feito(self, cfg) -> bool:
        """True se ja existe uma dispensa criada para este registro."""
        if self.force:
            return False
        rec = self.data.get(assinatura(cfg))
        return bool(rec and rec.get("dispensa_id"))

    def info(self, cfg):
        return self.data.get(assinatura(cfg))

    def marcar(self, cfg, status: str, dispensa_id: str = "", detalhe: str = "", perc=None):
        self.data[assinatura(cfg)] = {
            "status": status,
            "dispensa_id": dispensa_id or "",
            "perc": perc,
            "detalhe": detalhe or "",
            "processo": cfg.get("PROCESSO"),
            "num_empenho": cfg.get("NUM_EMPENHO"),
            "cnpj": cfg.get("CNPJ_FORNECEDOR"),
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._salvar()

    def _salvar(self):
        try:
            STATE_FILE.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("Falha ao salvar estado: %s", e)
