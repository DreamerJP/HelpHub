from flask import url_for
from App.banco import db
from App.Modulos.Autenticacao.modelo import Usuario


def test_operator_cannot_access_admin_routes(client, app):
    """Verifica se um usuário com role 'Operador' é bloqueado em rotas de admin."""

    # 1. Criar um usuário operador
    with app.app_context():
        # Limpa usuários anteriores se necessário (ou assume banco limpo pelo fixture)
        op = Usuario(
            username="operador_teste",
            nome="Operador",
            email="op@teste.com",
            role="Operador",
        )
        op.set_password("123456")
        db.session.add(op)
        db.session.commit()

    # 2. Fazer login como operador
    client.post(
        url_for("auth.login"),
        data={"username": "operador_teste", "password": "123456"},
        follow_redirects=True,
    )

    # 3. Tentar acessar rotas administrativas
    rotas_admin = [
        url_for("admin.configuracoes"),
        url_for("admin.logs"),
        url_for("admin.backups"),
        url_for("departamentos.lista"),
        url_for("departamentos.novo"),
        url_for("auth.lista_usuarios"),
    ]

    for rota in rotas_admin:
        response = client.get(rota)
        # O esperado é que ele receba 403 (Proibido) com o novo template personalizado
        assert response.status_code == 403, (
            f"Falha de segurança! Operador acessou {rota}"
        )
        assert (
            b"Acesso Negado" in response.data
            or b"possuem as permiss\xc3\xb5es" in response.data
        )
