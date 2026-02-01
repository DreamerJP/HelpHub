from flask import url_for
from App.Modulos.Autenticacao.modelo import Usuario
from App.banco import db


def test_admin_access_user_list(client, admin_user):
    """Test that admin can access user list."""
    # Login as admin
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(url_for("auth.lista_usuarios"))
    assert response.status_code == 200
    assert b"Membros da Equipe" in response.data
    assert b"admin_test" in response.data


def test_operator_cannot_access_user_list(client, app):
    """Test that operator cannot access user list."""
    with app.app_context():
        op = Usuario(username="op_test", email="op@test.com", role="Operador")
        op.set_password("123456")
        db.session.add(op)
        db.session.commit()

    # Login as operator
    client.post(
        url_for("auth.login"), data={"username": "op_test", "password": "123456"}
    )

    response = client.get(url_for("auth.lista_usuarios"), follow_redirects=True)
    assert b"Acesso Negado" in response.data


def test_create_new_user(client, admin_user):
    """Test creating a new user as admin."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.post(
        url_for("auth.novo_usuario"),
        data={
            "nome": "Novo Tecnico",
            "username": "tecnico1",
            "email": "tecnico1@test.com",
            "role": "Operador",
            "password": "password123",
            "ativo": True,
        },
        follow_redirects=True,
    )

    assert b"Usu\xc3\xa1rio tecnico1 criado com sucesso!" in response.data

    user = Usuario.query.filter_by(username="tecnico1").first()
    assert user is not None
    assert user.nome == "Novo Tecnico"
    assert user.check_password("password123")


def test_edit_user(client, admin_user, app):
    """Test editing an existing user as admin."""
    with app.app_context():
        user = Usuario(username="edit_me", email="edit@test.com", role="Operador")
        user.set_password("123456")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.post(
        url_for("auth.editar_usuario", id=user_id),
        data={
            "nome": "Nome Editado",
            "username": "editado",
            "email": "editado@test.com",
            "role": "Admin",
        },
        follow_redirects=True,
    )

    assert b"Usu\xc3\xa1rio atualizado com sucesso!" in response.data

    updated_user = db.session.get(Usuario, user_id)
    assert updated_user.nome == "Nome Editado"
    assert updated_user.username == "editado"
    assert updated_user.role == "Admin"
    assert updated_user.ativo is False


def test_toggle_user_status(client, admin_user, app):
    """Test toggling user active status."""
    with app.app_context():
        user = Usuario(
            username="toggle_me", email="toggle@test.com", role="Operador", ativo=True
        )
        user.set_password("123456")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Toggle to False
    response = client.get(
        url_for("auth.toggle_usuario", id=user_id), follow_redirects=True
    )
    assert b"foi desativado" in response.data
    assert db.session.get(Usuario, user_id).ativo is False

    # Toggle back to True
    response = client.get(
        url_for("auth.toggle_usuario", id=user_id), follow_redirects=True
    )
    assert b"foi ativado" in response.data
    assert db.session.get(Usuario, user_id).ativo is True


def test_change_password_profile(client, app):
    """Test that a user can change their own password in profile."""
    with app.app_context():
        user = Usuario(username="user_pass", email="pass@test.com", role="Operador")
        user.set_password("old_password")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post(
        url_for("auth.login"),
        data={"username": "user_pass", "password": "old_password"},
    )

    response = client.post(
        url_for("auth.perfil"),
        data={
            "password_old": "old_password",
            "password_new": "new_password",
            "password_confirm": "new_password",
        },
        follow_redirects=True,
    )

    assert b"Sua senha foi alterada com sucesso!" in response.data

    updated_user = db.session.get(Usuario, user_id)
    assert updated_user.check_password("new_password")
    assert not updated_user.check_password("old_password")
