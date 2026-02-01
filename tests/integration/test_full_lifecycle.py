import pytest
import sys
from App.iniciar import create_app
from App.banco import db
from App.Modulos.Autenticacao.modelo import Usuario


@pytest.fixture(scope="module")
def app_integration():
    """Cria uma instância real do app para teste de integração (ciclo completo)."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Banco real em memória
        "WTF_CSRF_ENABLED": False,  # Facilita requests de form
        "WTF_CSRF_CHECK_DEFAULT": False,  # Desabilita verificação global
        "SECRET_KEY": "integration-test-key",
        "BASE_DIR": "/tmp/helphub_integration",
        "TIMEZONE": "America/Sao_Paulo",
    }
    app = create_app(test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="module")
def client_integration(app_integration):
    return app_integration.test_client()


class TestFullLifecycle:
    """Teste de Integração: Simula o uso real do sistema do inicio ao fim."""

    def test_admin_login_integration(self, client_integration, app_integration):
        # 1. SETUP: Criar Administrador
        with app_integration.app_context():
            # Limpa banco antes para garantir
            db.create_all()

            if not Usuario.query.filter_by(username="admin_integ").first():
                admin = Usuario(
                    nome="Admin Integration",
                    username="admin_integ",
                    email="admin@test.com",
                    role="Admin",
                    ativo=True,
                )
                admin.set_password("123456")
                admin.save()

        # 2. LOGIN: Autenticar no sistema (Rota é /login, sem prefixo)
        # Verifica se usuario existe mesmo
        with app_integration.app_context():
            u = Usuario.query.filter_by(username="admin_integ").first()
            assert u is not None, "Usuario admin não foi criado no setup!"

        login_resp = client_integration.post(
            "/login",
            data={"username": "admin_integ", "password": "123456"},
            follow_redirects=True,
        )

        # Verifica se logou com sucesso
        body = login_resp.get_data(as_text=True)
        if login_resp.status_code != 200 or "Sair" not in body:
            print(f"DEBUG LOGIN FAIL. Body parcial: {body[:300]}", file=sys.stderr)

        assert login_resp.status_code == 200
        # "Dashboard" é o título comum da home. "Sair" indica menu logado.
        assert any(x in body for x in ["Dashboard", "Sair", "Olá, Admin"])
        print("\n[SUCCESS] Admin Integration Login OK!")

    def test_acesso_protegido_anonimo(self, client_integration):
        """Verifica se rotas protegidas barram acesso sem login."""
        client_integration.get("/logout", follow_redirects=True)  # Rota /logout

        # Tenta acessar admin config (rota protegida existente)
        resp = client_integration.get("/admin/config", follow_redirects=True)

        # Verifica se caiu na tela de login
        body = resp.get_data(as_text=True)
        assert "Entrar" in body or "Lembrar-me" in body or "/login" in resp.request.path
