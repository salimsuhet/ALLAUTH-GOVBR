"""
allauth_govbr.cpf
~~~~~~~~~~~~~~~~~
Utilitários para extração e validação de CPF.
"""


def extrair_cpf(sociallogin) -> str:
    """
    Extrai e normaliza o CPF do extra_data do sociallogin,
    independente do provider.

    - Gov.br federal: o ``sub`` do userinfo é o CPF.
    - Acesso Cidadão ES: campo ``cpf`` (requer scope aprovado pelo PRODEST).

    Retorna string com apenas dígitos, ou string vazia se não disponível.
    """
    data = sociallogin.account.extra_data
    provider = sociallogin.account.provider

    if provider == "govbr":
        # No Gov.br, o sub É o CPF (11 dígitos numéricos)
        cpf = data.get("cpf") or data.get("sub", "")
    elif provider == "acessocidadaoes":
        # No Acesso Cidadão ES, vem no campo "cpf" (scope cpf aprovado)
        cpf = data.get("cpf", "")
    else:
        cpf = ""

    return "".join(filter(str.isdigit, cpf or ""))


def cpf_valido(cpf: str) -> bool:
    """
    Valida um CPF já normalizado (somente dígitos).

    Verifica:
    - Comprimento de 11 dígitos
    - Não é sequência repetida (ex: 111.111.111-11)
    - Dígitos verificadores corretos
    """
    if not cpf or len(cpf) != 11:
        return False
    if len(set(cpf)) == 1:
        return False

    # Dígito verificador 1
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    r = (soma * 10) % 11
    if r == 10:
        r = 0
    if r != int(cpf[9]):
        return False

    # Dígito verificador 2
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    r = (soma * 10) % 11
    if r == 10:
        r = 0
    return r == int(cpf[10])


def formatar_cpf(cpf: str) -> str:
    """
    Formata CPF normalizado para exibição: XXX.XXX.XXX-XX.
    Espera string com 11 dígitos.
    """
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def mascarar_cpf(cpf: str) -> str:
    """
    Mascara CPF para logs: XXX.***.***-XX.
    Evita exposição completa em arquivos de log.
    """
    if len(cpf) != 11:
        return "***"
    return f"{cpf[:3]}.***.***-{cpf[9:]}"
