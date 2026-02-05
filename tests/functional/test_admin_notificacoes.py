from flask import url_for
from App.Modulos.Administracao.modelo import Configuracao
from App.servicos.criptografia import encriptar, decriptar


def test_admin_notificacoes_view(client, app, admin_user):
    """Testa a visualização da central de integrações."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    response = client.get(url_for("admin.notificacoes"))
    assert response.status_code == 200
    assert b"Telegram" in response.data
    assert b"E-mail" in response.data
    assert b"WhatsApp" in response.data


def test_admin_notificacao_edit_telegram(client, app, admin_user):
    """Testa a edição de uma configuração de notificação (Telegram)."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    response = client.post(
        url_for("admin.notificacao_editar", provedor="telegram"),
        data={
            "telegram_token": "123456:ABC-DEF",
            "telegram_chat_id": "987654321",
            "telegram_ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "atualizada".encode("utf-8") in response.data

    with app.app_context():
        cfg = Configuracao.get_config()
        assert decriptar(cfg.telegram_token) == "123456:ABC-DEF"
        assert cfg.telegram_chat_id == "987654321"
        assert cfg.telegram_ativo


def test_admin_notificacao_edit_whatsapp(client, app, admin_user):
    """Testa a edição de uma configuração do WhatsApp."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    response = client.post(
        url_for("admin.notificacao_editar", provedor="whatsapp"),
        data={
            "whatsapp_api_url": "https://api.teste.com",
            "whatsapp_key": "secret123",
            "whatsapp_ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "atualizada".encode("utf-8") in response.data

    with app.app_context():
        cfg = Configuracao.get_config()
        assert cfg.whatsapp_api_url == "https://api.teste.com"
        assert decriptar(cfg.whatsapp_key) == "secret123"
        assert cfg.whatsapp_ativo


def test_admin_notificacao_password_protection(client, app, admin_user):
    """Testa se campos de senha vazios NÃO sobrescrevem o banco de dados."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # 1. Definir uma senha inicial
    with app.app_context():
        cfg = Configuracao.get_config()
        cfg.email_password = "SENHA_ORIGINAL"
        cfg.save()

    # 2. Tentar editar outras informações enviando a senha VAZIA
    client.post(
        url_for("admin.notificacao_editar", provedor="email"),
        data={
            "email_smtp_server": "smtp.novo.com",
            "email_user": "novo@teste.com",
            "email_password": "",  # Enviando vazio
            "email_ativo": "y",
        },
        follow_redirects=True,
    )

    # 3. Verificar se o servidor mudou mas a senha CONTINUA a mesma (mesmo encriptada)
    with app.app_context():
        cfg = Configuracao.get_config()
        assert cfg.email_smtp_server == "smtp.novo.com"
        assert decriptar(cfg.email_password) == "SENHA_ORIGINAL"


def test_admin_notificacao_teste_telegram(client, app, admin_user):
    """Testa a rota de teste de conexão do Telegram."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    from unittest.mock import patch

    with patch(
        "App.servicos.notificador.Notificador.test_telegram", return_value=(True, "OK")
    ):
        response = client.post(
            url_for("admin.teste_telegram"), data={"token": "test", "chat_id": "123"}
        )
        assert response.status_code == 200
        assert response.json["success"]
        assert response.json["message"] == "OK"


def test_admin_notificacao_teste_whatsapp(client, app, admin_user):
    """Testa a rota de teste de conexão do WhatsApp."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    from unittest.mock import patch

    with patch(
        "App.servicos.notificador.Notificador.test_whatsapp", return_value=(True, "OK")
    ):
        response = client.post(
            url_for("admin.teste_whatsapp"),
            data={"url": "http://api.test", "key": "abc", "destination": "SISTEMA"},
        )
        assert response.status_code == 200
        assert response.json["success"]
        assert response.json["message"] == "OK"


def test_admin_notificacao_ignore_non_tokens(client, app, admin_user):
    """Garante que campos comuns (servidor, user) NÃO são encriptados por engano."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    client.post(
        url_for("admin.notificacao_editar", provedor="email"),
        data={
            "email_smtp_server": "smtp.comum.com",
            "email_user": "u_comum",
            "email_ativo": "y",
        },
        follow_redirects=True,
    )

    with app.app_context():
        cfg = Configuracao.get_config()
        # Campos comuns devem ser salvos em texto puro
        assert cfg.email_smtp_server == "smtp.comum.com"
        assert cfg.email_user == "u_comum"


def test_admin_notificacao_teste_com_token_banco(client, app, admin_user):
    """Testa se o teste de conexão usa o token do banco quando o campo do form vem vazio."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # 1. Salva um token no banco primeiro
    with app.app_context():
        cfg = Configuracao.get_config()
        cfg.telegram_token = encriptar("TOKEN_DO_BANCO")
        cfg.telegram_chat_id = "123"
        cfg.save()

    # 2. Testa o envio com token VAZIO no form (deve decriptar do banco)
    from unittest.mock import patch

    with patch("App.servicos.notificador.Notificador.test_telegram") as mock_test:
        mock_test.return_value = (True, "OK")
        client.post(
            url_for("admin.teste_telegram"), data={"token": "", "chat_id": "123"}
        )
        # Verifica se o mock recebeu o token DECRIPTADO corretamente
        mock_test.assert_called_with("TOKEN_DO_BANCO", "123")
