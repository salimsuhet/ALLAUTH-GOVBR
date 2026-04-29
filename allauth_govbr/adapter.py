"""
allauth_govbr.adapter
~~~~~~~~~~~~~~~~~~~~~
SocialAccountAdapter com vinculação de contas por CPF.

Compatível com GeoNode 4.x (django-allauth 0.51.x).

Configuração em local_settings.py:
    SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"
"""
import logging

from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect

from .cpf import cpf_valido, extrair_cpf, mascarar_cpf

logger = logging.getLogger(__name__)


class GovIdentityAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter que vincula contas de diferentes provedores gov (Gov.br e
    Acesso Cidadão ES) ao mesmo usuário GeoNode usando o CPF como chave.

    Herda de DefaultSocialAccountAdapter para compatibilidade máxima.
    Se precisar manter lógicas do GeoNode (aprovação de usuário, grupos
    padrão), troque a herança:

        from geonode.people.adapters import SocialAccountAdapter as GeoNodeAdapter
        class GovIdentityAccountAdapter(GeoNodeAdapter): ...
    """

    # ------------------------------------------------------------------
    # Hooks principais do allauth
    # ------------------------------------------------------------------

    def pre_social_login(self, request, sociallogin):
        """
        Chamado após autenticação no provider, antes de criar/logar o usuário.

        Fluxo:
        1. Se a conta social já está conectada a um usuário → passa.
        2. Extrai e valida o CPF do extra_data.
        3. Busca Profile com esse CPF no banco.
        4a. Encontrou → conecta o sociallogin ao usuário existente.
        4b. Não encontrou → salva CPF normalizado para persistir depois.
        """
        # 1. Conta já existente — nada a fazer
        if sociallogin.is_existing:
            return

        cpf = extrair_cpf(sociallogin)

        if not cpf:
            logger.debug(
                "[GovAdapter] CPF não disponível | provider=%s",
                sociallogin.account.provider,
            )
            return

        if not cpf_valido(cpf):
            logger.warning(
                "[GovAdapter] CPF inválido recebido | provider=%s | cpf=%s",
                sociallogin.account.provider,
                mascarar_cpf(cpf),
            )
            return

        self._vincular_por_cpf(request, sociallogin, cpf)

    def post_social_login(self, request, sociallogin):
        """
        Chamado após login/registro social bem-sucedido.
        Persiste o CPF no Profile se ainda não estiver salvo.
        """
        super().post_social_login(request, sociallogin)
        self._persistir_cpf(sociallogin)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _vincular_por_cpf(self, request, sociallogin, cpf: str):
        """
        Tenta encontrar um Profile pelo CPF e conectar o sociallogin a ele.
        """
        from geonode.people.models import Profile

        try:
            perfil = Profile.objects.get(cpf=cpf)
        except Profile.DoesNotExist:
            # Cidadão novo — marca o CPF para ser salvo em post_social_login
            sociallogin.account.extra_data["_cpf_normalizado"] = cpf
            logger.debug(
                "[GovAdapter] CPF não encontrado no DB, novo usuário | cpf=%s",
                mascarar_cpf(cpf),
            )
            return
        except Profile.MultipleObjectsReturned:
            logger.error(
                "[GovAdapter] ERRO: múltiplos profiles com mesmo CPF=%s",
                mascarar_cpf(cpf),
            )
            return

        usuario = perfil.user

        if not usuario.is_active:
            messages.error(
                request,
                "Sua conta está inativa. Entre em contato com o administrador.",
            )
            raise ImmediateHttpResponse(redirect("account_login"))

        # Conecta o sociallogin ao usuário encontrado
        sociallogin.connect(request, usuario)

        logger.info(
            "[GovAdapter] Conta vinculada por CPF | user=%s | provider=%s | cpf=%s",
            usuario.username,
            sociallogin.account.provider,
            mascarar_cpf(cpf),
        )

    def _persistir_cpf(self, sociallogin):
        """
        Salva o CPF no Profile do usuário, se ainda não estiver preenchido.
        Usa transaction.atomic() para garantir consistência caso o save falhe.
        """
        cpf = (
            extrair_cpf(sociallogin)
            or sociallogin.account.extra_data.get("_cpf_normalizado", "")
        )

        if not cpf or not cpf_valido(cpf):
            return

        from geonode.people.models import Profile

        try:
            perfil = Profile.objects.get(user=sociallogin.user)
        except Profile.DoesNotExist:
            return

        if not getattr(perfil, "cpf", None):
            try:
                with transaction.atomic():
                    perfil.cpf = cpf
                    perfil.save(update_fields=["cpf"])
                logger.info(
                    "[GovAdapter] CPF persistido no Profile | user=%s",
                    sociallogin.user.username,
                )
            except Exception:
                logger.exception(
                    "[GovAdapter] Erro ao persistir CPF | user=%s",
                    sociallogin.user.username,
                )
