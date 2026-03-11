"""
tests/test_cpf.py
~~~~~~~~~~~~~~~~~
Testes unitários para os utilitários de CPF.
"""
import pytest
from allauth_govbr.cpf import cpf_valido, extrair_cpf, formatar_cpf, mascarar_cpf


class TestCpfValido:
    def test_cpf_valido_real(self):
        # CPF válido gerado para teste
        assert cpf_valido("52998224725") is True

    def test_cpf_invalido_digito(self):
        assert cpf_valido("52998224726") is False

    def test_cpf_sequencia_repetida(self):
        assert cpf_valido("11111111111") is False
        assert cpf_valido("00000000000") is False

    def test_cpf_curto(self):
        assert cpf_valido("1234567") is False

    def test_cpf_vazio(self):
        assert cpf_valido("") is False

    def test_cpf_none(self):
        assert cpf_valido(None) is False


class TestFormatarCpf:
    def test_formata_corretamente(self):
        assert formatar_cpf("52998224725") == "529.982.247-25"

    def test_cpf_invalido_retorna_original(self):
        assert formatar_cpf("123") == "123"


class TestMascarar:
    def test_mascara_fragmento(self):
        resultado = mascarar_cpf("52998224725")
        assert resultado.startswith("529")
        assert resultado.endswith("25")
        assert "982" not in resultado


class TestExtrairCpf:
    def _make_sociallogin(self, provider, extra_data):
        """Helper para criar um mock de sociallogin."""

        class FakeAccount:
            pass

        class FakeSocialLogin:
            account = FakeAccount()

        sl = FakeSocialLogin()
        sl.account.provider = provider
        sl.account.extra_data = extra_data
        return sl

    def test_extrai_govbr_via_sub(self):
        sl = self._make_sociallogin("govbr", {"sub": "52998224725"})
        assert extrair_cpf(sl) == "52998224725"

    def test_extrai_govbr_com_formatacao(self):
        sl = self._make_sociallogin("govbr", {"sub": "529.982.247-25"})
        assert extrair_cpf(sl) == "52998224725"

    def test_extrai_acessocidadao_via_cpf(self):
        sl = self._make_sociallogin(
            "acessocidadaoes", {"cpf": "529.982.247-25", "subNovo": "abc123"}
        )
        assert extrair_cpf(sl) == "52998224725"

    def test_sem_cpf_retorna_vazio(self):
        sl = self._make_sociallogin("acessocidadaoes", {"subNovo": "abc123"})
        assert extrair_cpf(sl) == ""

    def test_provider_desconhecido(self):
        sl = self._make_sociallogin("github", {"sub": "12345"})
        assert extrair_cpf(sl) == ""
