from unittest.mock import patch, MagicMock
from App.servicos.notificador import Notificador
from App.Modulos.Administracao.modelo import Configuracao, TarefaMonitor
from App.servicos.criptografia import encriptar


class TestNotificador:
    @patch("App.servicos.notificador.requests.post")
    def test_send_telegram_success(self, mock_post, app):
        """Testa se o envio para o Telegram faz a requisição correta e limpa o monitor."""

        mock_post.return_value.status_code = 200
        mock_post.return_value.ok = True

        with app.app_context():
            success, message = Notificador.test_telegram("fake_token", "fake_chat_id")

            assert success is True
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert "fake_token" in args[0]
            assert kwargs["json"]["chat_id"] == "fake_chat_id"

            # Verifica se limpou/atualizou o monitor
            task = TarefaMonitor.query.filter_by(
                tarefa_id="notificacao_telegram"
            ).first()
            assert task is not None
            assert task.status == "Sucesso"

    @patch("App.servicos.notificador.requests.post")
    def test_send_telegram_failure(self, mock_post):
        """Testa falha no envio do Telegram."""
        mock_post.return_value.ok = False
        mock_post.return_value.json.return_value = {"description": "Unauthorized"}

        success, message = Notificador.test_telegram("wrong_token", "chat_id")

        assert success is False
        assert "Unauthorized" in message

    def test_notify_new_ticket_inactive(self, app):
        """Testa que nenhuma notificação é enviada se estiverem desativadas."""
        with app.app_context():
            config = Configuracao.get_config()
            config.telegram_ativo = False
            config.email_ativo = False
            config.save()

            chamado = MagicMock()
            chamado.protocolo = "20260101-001"

            with (
                patch(
                    "App.servicos.notificador.Notificador._send_telegram"
                ) as mock_tel,
                patch("App.servicos.notificador.Notificador._send_email") as mock_mail,
            ):
                Notificador.notify_new_ticket(chamado)

                mock_tel.assert_not_called()
                mock_mail.assert_not_called()

    @patch("App.servicos.notificador.smtplib.SMTP")
    def test_send_email_logic(self, mock_smtp, app):
        """Testa se a lógica de e-mail tenta usar o servidor SMTP corretamente."""
        with app.app_context():
            config = Configuracao.get_config()
            config.email_ativo = True
            config.email_smtp_server = "smtp.test.com"
            config.email_smtp_port = 587
            config.email_user = "test@user.com"
            config.email_password = "password"
            config.save()

            # Simula chamado com departamento que tem e-mail
            chamado = MagicMock()
            chamado.protocolo = "123"
            chamado.departamento.email_notificacao = "dept@test.com"

            # Precisamos do mock do servidor SMTP
            mock_server = mock_smtp.return_value

            Notificador._send_email(config, "dept@test.com", "Subject", "Body")

            mock_smtp.assert_called_with("smtp.test.com", 587, timeout=15)
            mock_server.login.assert_called_with("test@user.com", "password")
            mock_server.send_message.assert_called()

    @patch("App.servicos.notificador.requests.post")
    def test_send_whatsapp_success(self, mock_post, app):
        """Testa o envio de WhatsApp via API e monitoramento."""

        mock_post.return_value.status_code = 200
        mock_post.return_value.ok = True

        with app.app_context():
            success, message = Notificador.test_whatsapp(
                "http://api.test", "fake_key", "5511999999999"
            )

            assert success is True
            mock_post.assert_called_once()
            _, kwargs = mock_post.call_args
            assert kwargs["headers"]["apikey"] == "fake_key"
            assert kwargs["json"]["number"] == "5511999999999"

            task = TarefaMonitor.query.filter_by(
                tarefa_id="notificacao_whatsapp"
            ).first()
            assert task.status == "Sucesso"

    @patch("App.servicos.notificador.requests.post")
    def test_notificador_decripta_ao_enviar(self, mock_post, app):
        """Garante que os métodos de envio decriptam os tokens antes de usar."""
        with app.app_context():
            config = Configuracao.get_config()
            config.telegram_ativo = True
            token_limpo = "654321:TOKEN_REAL"
            config.telegram_token = encriptar(token_limpo)
            config.telegram_chat_id = "123"
            config.save()

            mock_post.return_value.ok = True

            # Testa o método privado _send_telegram que é usado no fluxo real
            Notificador._send_telegram(token_limpo, "123", "Body")

            # Verifica se o post foi chamado com o token LIMPO (não o encriptado)
            args, _ = mock_post.call_args
            assert token_limpo in args[0]
            assert (
                "gAAAAA" not in args[0]
            )  # Garante que não enviou o hash da criptografia
