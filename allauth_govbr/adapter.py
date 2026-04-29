"""
allauth_govbr.adapter  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~~~~~
SocialAccountAdapter com vinculação de contas por CPF.

Mudanças em relação ao branch main (allauth 0.51.x):
  - Herança: DefaultSocialAccountAdapter → geonode.people.adapters.SocialAccountAdapter
    para herdar a lógica de aprovação de usuários, grupos padrão e outros
    comportamentos específicos do GeoNode 5.x.
  - Profile IS o usuário: em GeoNode, Profile(AbstractUser) é o AUTH_USER_MODEL.
    Não há campo .user — perfil IS o usuário. Corrigido:
    * perfil.user → perfil
    * Profile.objects.get(user=...) → Profile.objects.get(pk=sociallogin.user.pk)
      (ou simplesmente sociallogin.user, que já é uma instância de Profile)

Configuração em local_settings.py:
    SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"
"""
import logging

from allauth.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect

from .cpf import cpf_valido, extrair_cpf, mascarar_cpf

logger = logging.getLogger(__name__)


class GovIdentityAccountAdapter:
    """
    Mixin de vinculação por CPF.

    Não herda diretamente aqui para permitir que apps.py injete a herança
    correta de geonode.people.adapters.SocialAccountAdapter em tempo de
    carregamento, evitando importações circulares durante o setup do Django.
    A classe real é construída em apps.py via _build_adapter_class().
    """
    pass


def _build_adapter_class():
    """
    Constrói GovIdentityAccountAdapter herdando de SocialAccountAdapter do GeoNode.
    Chamado em apps.py após o setup completo do Django para evitar ImportError
    circular entre geonode.people e allauth_govbr durante INSTALLED_APPS loading.
    """
    try:
        from geonode.people.adapters import SocialAccountAdapter as GeoNodeAdapter
        base = GeoNodeAdapter
    except ImportError:
        from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
        base = DefaultSocialAccountAdapter
        logger.warning(
            "[GovAdapter] geonode.people.adapters não disponível; "
            "usando DefaultSocialAccountAdapter como base."
        )

    class _GovIdentityAccountAdapter(base):
        """
        Adapter que vincula contas de diferentes provedores gov ao mesmo
        usuário GeoNode usando o CPF como chave.
        """

        def pre_social_login(self, request, sociallogin):
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
                    "[GovAdapter] CPF inválido | provider=%s | cpf=%s",
                    sociallogin.account.provider,
                    mascarar_cpf(cpf),
                )
                return

            self._vincular_por_cpf(request, sociallogin, cpf)

        def post_social_login(self, request, sociallogin):
            super().post_social_login(request, sociallogin)
            self._persistir_cpf(sociallogin)

        def _vincular_por_cpf(self, request, sociallogin, cpf: str):
            from geonode.people.models import Profile

            try:
                # Profile IS o usuário (Profile extends AbstractUser)
                perfil = Profile.objects.get(cpf=cpf)
            except Profile.DoesNotExist:
                sociallogin.account.extra_data["_cpf_normalizado"] = cpf
                logger.debug(
                    "[GovAdapter] CPF não encontrado no DB | cpf=%s",
                    mascarar_cpf(cpf),
                )
                return
            except Profile.MultipleObjectsReturned:
                logger.error(
                    "[GovAdapter] Múltiplos profiles com CPF=%s",
                    mascarar_cpf(cpf),
                )
                return

            # perfil IS o usuário — sem campo .user separado
            usuario = perfil

            if not usuario.is_active:
                messages.error(
                    request,
                    "Sua conta está inativa. Entre em contato com o administrador.",
                )
                raise ImmediateHttpResponse(redirect("account_login"))

            sociallogin.connect(request, usuario)

            logger.info(
                "[GovAdapter] Conta vinculada por CPF | user=%s | provider=%s | cpf=%s",
                usuario.username,
                sociallogin.account.provider,
                mascarar_cpf(cpf),
            )

        def _persistir_cpf(self, sociallogin):
            cpf = (
                extrair_cpf(sociallogin)
                or sociallogin.account.extra_data.get("_cpf_normalizado", "")
            )

            if not cpf or not cpf_valido(cpf):
                return

            # sociallogin.user já é uma instância de Profile (Profile IS o usuário)
            perfil = sociallogin.user

            if not getattr(perfil, "cpf", None):
                try:
                    with transaction.atomic():
                        perfil.cpf = cpf
                        perfil.save(update_fields=["cpf"])
                    logger.info(
                        "[GovAdapter] CPF persistido | user=%s",
                        sociallogin.user.username,
                    )
                except Exception:
                    logger.exception(
                        "[GovAdapter] Erro ao persistir CPF | user=%s",
                        sociallogin.user.username,
                    )

    return _GovIdentityAccountAdapter


# Instanciada em apps.py após Django setup; referenciada aqui como proxy
# para que SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"
# funcione normalmente.
GovIdentityAccountAdapter = None  # será substituído em apps.py
