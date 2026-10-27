# -*- coding: utf-8 -*-
"""Testes independentes de Selenium e do ambiente do TCE."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from entrada_caminhos import solicitar_caminhos, _normalizar_entrada
from nomes_recibos import nome_recibo_tce, caminho_disponivel


class EntradaCaminhosTests(unittest.TestCase):
    def test_remove_somente_aspas_externas(self):
        self.assertEqual(
            _normalizar_entrada('  "C:\\Users\\Usuario\\OneDrive - MPRJ\\Controle.xlsx"  '),
            os.path.normpath("C:\\Users\\Usuario\\OneDrive - MPRJ\\Controle.xlsx"),
        )

    def test_solicitacao_sequencial_validacao_e_acentos(self):
        with tempfile.TemporaryDirectory() as raiz:
            pasta = Path(raiz) / "Recibos Acadêmicos"
            pasta.mkdir()
            planilha = Path(raiz) / "Cadastro MPRJ.xlsx"
            planilha.write_bytes(b"planilha de teste")
            prompts = []
            entradas = iter([
                '"arquivo-inexistente.xlsx"',
                f'"{planilha}"',
                f'"{pasta}"',
            ])

            def responder(prompt):
                prompts.append(prompt)
                return next(entradas)

            with patch("builtins.input", side_effect=responder), patch("builtins.print"):
                excel, recibos = solicitar_caminhos()

            self.assertEqual(excel, str(planilha))
            self.assertEqual(recibos, str(pasta))
            self.assertEqual(len(prompts), 3)
            self.assertIn("planilha", prompts[0])
            self.assertIn("planilha", prompts[1])
            self.assertIn("recibos", prompts[2])


class NomeReciboTests(unittest.TestCase):
    def test_padrao_tce_e_caracteres_invalidos(self):
        self.assertEqual(
            nome_recibo_tce("20.22.0001/2026", "Empresa: Exemplo Ltda"),
            "TCE - 20.22.0001-2026 - Empresa- Exemplo Ltda.pdf",
        )

    def test_protege_arquivo_existente(self):
        with tempfile.TemporaryDirectory() as pasta:
            nome = nome_recibo_tce("123", "Fornecedor")
            (Path(pasta) / nome).write_bytes(b"recibo anterior")
            caminho = caminho_disponivel(pasta, nome)
            self.assertEqual(Path(caminho).name, "TCE - 123 - Fornecedor (2).pdf")

    def test_nao_inventa_fornecedor(self):
        with self.assertRaises(ValueError):
            nome_recibo_tce("123", "")


if __name__ == "__main__":
    unittest.main()
