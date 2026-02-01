from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired, Email, Optional, Length
from App.base_form import AppBaseForm


class DepartamentoForm(AppBaseForm):
    nome = StringField(
        "Nome do Departamento", validators=[DataRequired(), Length(max=64)]
    )
    email_notificacao = StringField(
        "Email para Notificações", validators=[Optional(), Email(), Length(max=120)]
    )
    descricao = StringField("Descrição", validators=[Optional(), Length(max=255)])
    ativo = BooleanField("Ativo", default=True)
