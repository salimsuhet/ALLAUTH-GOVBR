"""
Migration para adicionar o campo CPF ao model Profile do GeoNode.

INSTRUÇÕES:
    1. Copie este arquivo para a pasta de migrations do app 'people' do GeoNode:
       geonode/people/migrations/

    2. Ajuste o número sequencial e a dependência conforme a última migration
       existente no seu projeto. Ex: se a última for 0030_..., renomeie este
       arquivo para 0031_add_cpf_to_profile.py e ajuste dependencies abaixo.

    3. Execute:
       python manage.py migrate people
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    # !! Ajuste a dependência para a última migration do app 'people' !!
    dependencies = [
        ("people", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="cpf",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=14,
                null=True,
                unique=True,
                verbose_name="CPF",
                help_text="CPF do cidadão (somente dígitos). "
                          "Preenchido automaticamente via Login Gov.br ou Acesso Cidadão ES.",
            ),
        ),
    ]
