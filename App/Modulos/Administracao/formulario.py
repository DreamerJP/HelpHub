from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Email, Optional


class ConfiguracaoForm(FlaskForm):
    empresa_nome = StringField("Nome da Empresa", validators=[DataRequired()])
    empresa_cnpj = StringField("CNPJ")
    empresa_email = StringField("E-mail de Contato", validators=[Optional(), Email()])
    empresa_telefone = StringField("Telefone")
    empresa_endereco = StringField("Endereço Completo")
    empresa_logo = FileField(
        "Logo da Empresa (PNG, JPG)",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Apenas imagens!")],
    )
    submit = SubmitField("Salvar Configurações")
