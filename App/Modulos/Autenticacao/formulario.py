from wtforms import StringField, PasswordField, BooleanField, SelectField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from App.base_form import AppBaseForm


class LoginForm(AppBaseForm):
    username = StringField("Usuário", validators=[DataRequired()])
    password = PasswordField("Senha", validators=[DataRequired()])
    remember_me = BooleanField("Manter conectado")


class UsuarioForm(AppBaseForm):
    nome = StringField(
        "Nome Completo", validators=[DataRequired(), Length(min=3, max=100)]
    )
    username = StringField(
        "Nome de Usuário", validators=[DataRequired(), Length(min=3, max=64)]
    )
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Senha", validators=[Optional(), Length(min=6)])
    role = SelectField(
        "Cargo/Permissão",
        choices=[("Operador", "Operador (Atendimento)"), ("Admin", "Administrador")],
        validators=[DataRequired()],
    )
    ativo = BooleanField("Usuário Ativo", default=True)


class AlterarSenhaForm(AppBaseForm):
    password_old = PasswordField("Senha Atual", validators=[DataRequired()])
    password_new = PasswordField(
        "Nova Senha", validators=[DataRequired(), Length(min=6)]
    )
    password_confirm = PasswordField(
        "Confirmar Nova Senha",
        validators=[
            DataRequired(),
            EqualTo("password_new", message="As senhas devem ser iguais."),
        ],
    )


class PerfilForm(AppBaseForm):
    nome = StringField(
        "Nome Completo", validators=[DataRequired(), Length(min=3, max=100)]
    )
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    avatar = FileField("Foto de Perfil (JPG, PNG)", validators=[Optional()])
