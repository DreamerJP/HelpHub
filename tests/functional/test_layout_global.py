from flask import url_for
from App.Modulos.Autenticacao.modelo import Usuario
from App.banco import db


def test_layout_base_sidebar_links(client, admin_user):
    """Garante que a sidebar contém os links essenciais para o Admin."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )
    response = client.get(url_for("layout.index"))

    assert b"Clientes" in response.data
    assert b"Chamados" in response.data
    assert b"Agenda" in response.data
    assert b"Logs do Sistema" in response.data
    assert b"Backups" in response.data
    assert b"Configura\xc3\xa7\xc3\xb5es OS" in response.data


def test_layout_base_operator_restrictions(client, app):
    """Garante que Operador não vê links administrativos na sidebar."""
    with app.app_context():
        op = Usuario(username="op_test", email="op@test.com", role="Operador")
        op.set_password("123456")
        db.session.add(op)
        db.session.commit()

    client.post(
        url_for("auth.login"), data={"username": "op_test", "password": "123456"}
    )
    response = client.get(url_for("layout.index"))

    assert b"Clientes" in response.data
    assert b"Logs do Sistema" not in response.data
    assert b"Backups" not in response.data
    assert b"Configura\xc3\xa7\xc3\xb5es OS" not in response.data


def test_layout_notification_system_presence(client, admin_user):
    """Verifica se o sistema de toasts (notificações) está presente no HTML."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )
    response = client.get(url_for("layout.index"))

    # Verifica o x-data do sistema de notificações
    assert b"notificationSystem" in response.data
    # Verifica o container de toasts
    assert b"flash-container" in response.data


def test_layout_anti_dos_script_presence(client):
    """Verifica se o script de proteção contra colagem massiva (Anti-DoS) está presente no layout global."""
    # A página de login utiliza o layout_base.html, portanto o script de segurança deve estar presente.
    response = client.get(url_for("auth.login"))

    # Valida presença do script de monitoramento de colagem (Paste Protection)
    assert b"ANTI-FREEZE & DoS PROTECTION" in response.data
    assert b"addEventListener('paste'" in response.data
    assert b"maxlength" in response.data


def test_layout_profile_avatar_link(client, admin_user):
    """Verifica se o link do perfil com avatar está presente na sidebar."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )
    response = client.get(url_for("layout.index"))

    assert b'href="/perfil"' in response.data
    assert b"ph-user" in response.data or b"img" in response.data
