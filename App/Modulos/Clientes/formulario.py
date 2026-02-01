from wtforms import StringField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional, Length
from App.base_form import AppBaseForm


class ClienteForm(AppBaseForm):
    nome_razao = StringField(
        "Nome / Razão Social", validators=[DataRequired(), Length(max=100)]
    )
    nome_fantasia = StringField(
        "Nome Fantasia", validators=[Optional(), Length(max=100)]
    )
    cpf_cnpj = StringField("CPF/CNPJ", validators=[DataRequired(), Length(max=20)])

    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    telefone = StringField("Telefone", validators=[Optional(), Length(max=20)])

    # Endereço
    cep = StringField(
        "CEP", validators=[Optional(), Length(max=10)], render_kw={"class": "cep-mask"}
    )
    logradouro = StringField("Endereço", validators=[Optional(), Length(max=150)])
    numero = StringField("Número", validators=[Optional(), Length(max=20)])
    complemento = StringField("Complemento", validators=[Optional(), Length(max=100)])
    bairro = StringField("Bairro", validators=[Optional(), Length(max=60)])
    cidade = StringField("Cidade", validators=[Optional(), Length(max=60)])
    uf = StringField("UF", validators=[Optional(), Length(max=2)])

    observacoes = TextAreaField("Anotações do Cliente", validators=[Optional()])

    ativo = BooleanField("Cliente Ativo", default=True)
