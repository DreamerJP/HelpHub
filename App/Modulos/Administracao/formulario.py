from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, IntegerField, PasswordField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Email, Optional, Length


class ConfiguracaoForm(FlaskForm):
    empresa_nome = StringField(
        "Nome da Empresa", validators=[DataRequired(), Length(max=100)]
    )
    empresa_cnpj = StringField("CNPJ", validators=[Optional(), Length(max=20)])
    empresa_email = StringField(
        "E-mail de Contato", validators=[Optional(), Email(), Length(max=120)]
    )
    empresa_telefone = StringField("Telefone", validators=[Optional(), Length(max=20)])
    empresa_endereco = StringField(
        "Endereço Completo", validators=[Optional(), Length(max=255)]
    )
    empresa_logo = FileField(
        "Logo da Empresa (PNG, JPG)",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Apenas imagens!")],
    )
    submit = SubmitField("Salvar Configurações")


class NotificacaoForm(FlaskForm):
    # Telegram
    telegram_token = StringField(
        "Token do Bot (Remetente)", validators=[Optional(), Length(max=100)]
    )
    telegram_chat_id = StringField(
        "ID(s) dos Chats de Destino", validators=[Optional(), Length(max=255)]
    )
    telegram_ativo = BooleanField("Habilitar Notificações via Telegram")

    # Email
    email_smtp_server = StringField(
        "Host do Servidor SMTP", validators=[Optional(), Length(max=120)]
    )
    email_smtp_port = IntegerField("Porta SMTP", default=587, validators=[Optional()])
    email_user = StringField(
        "Usuário / E-mail de Envio", validators=[Optional(), Length(max=120)]
    )
    email_password = PasswordField(
        "Senha / App Password", validators=[Optional(), Length(max=100)]
    )
    email_ativo = BooleanField("Habilitar Notificações via E-mail")

    # WhatsApp (Evolution API)
    whatsapp_api_url = StringField(
        "URL da Instância API", validators=[Optional(), Length(max=255)]
    )
    whatsapp_key = PasswordField(
        "Chave de API Secreta", validators=[Optional(), Length(max=100)]
    )
    whatsapp_ativo = BooleanField("Habilitar Notificações via WhatsApp")

    submit = SubmitField("Salvar Configurações da Integração")
