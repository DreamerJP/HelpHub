from unittest.mock import MagicMock, patch
from flask import url_for


class TestAuthRoutes:
    # --- LOGIN CASES ---

    def test_login_invalid_credentials_logs_warning(self, client, app):
        """Testa se credenciais inválidas geram log de aviso e flash message."""
        # Usuario não existe ou senha errada
        with patch("App.Modulos.Autenticacao.rotas.Usuario") as mock_user_cls:
            mock_user_cls.query.filter_by.return_value.first.return_value = (
                None  # Usuário não encontrado
            )

            # Mock do logger
            app.logger = MagicMock()

            response = client.post(
                url_for("auth.login"),
                data={
                    "username": "hacker",
                    "password": "wrongpassword",
                    "csrf_token": "disabled",
                },
                follow_redirects=True,
            )

            assert "Usuário ou senha inválidos." in response.get_data(as_text=True)
            # Verifica se logou
            app.logger.warning.assert_called()
            # Verifica conteúdo do log
            args, _ = app.logger.warning.call_args
            assert "Falha de login" in args[0]

    def test_login_inactive_user_blocks_access(self, client, app):
        """Testa se usuário inativo é bloqueado."""
        mock_user = MagicMock()
        mock_user.check_password.return_value = True
        mock_user.ativo = False
        mock_user.username = "sleeping_beauty"

        with patch("App.Modulos.Autenticacao.rotas.Usuario") as mock_user_cls:
            mock_user_cls.query.filter_by.return_value.first.return_value = mock_user

            response = client.post(
                url_for("auth.login"),
                data={
                    "username": "sleeping_beauty",
                    "password": "correct",
                    "csrf_token": "disabled",
                },
                follow_redirects=True,
            )

            assert "Usuário inativo" in response.get_data(as_text=True)

    def test_login_redirect_safe_next(self, client, app):
        """Testa o redirecionamento seguro (evita open redirect)."""
        mock_user = MagicMock()
        mock_user.check_password.return_value = True
        mock_user.ativo = True
        mock_user.is_authenticated = True
        mock_user.get_id.return_value = "1"

        with patch("App.Modulos.Autenticacao.rotas.Usuario") as mock_user_cls:
            mock_user_cls.query.filter_by.return_value.first.return_value = mock_user

            # Mock login_user do flask_login para não precisar de sessão real complexa
            with patch("App.Modulos.Autenticacao.rotas.login_user"):
                # Teste 1: Next inseguro (http externo) -> deve ir para index
                response = client.post(
                    url_for("auth.login", next="http://evil.com"),
                    data={"username": "user", "password": "123"},
                )
                # O status code 302 indica redirect. Verificamos o Location header.
                assert response.status_code == 302
                assert (
                    response.location == url_for("layout.index", _external=False)
                    or url_for("layout.index", _external=True) in response.location
                )

    # --- ADMIN PERMISSIONS ---

    def test_admin_routes_block_non_admin(self, client, app):
        """Testa se rotas de admin bloqueiam usuários comuns."""
        # Logar como usuário comum
        with client.session_transaction() as sess:
            sess["_user_id"] = "2"  # ID fake

        with patch("flask_login.utils._get_user") as mock_curr_user:
            user = MagicMock()
            user.is_authenticated = True
            user.is_admin = False  # NÃO É ADMIN
            mock_curr_user.return_value = user

            # Validar bloqueio em várias rotas
            rotas = [
                "/usuarios",
                "/usuarios/novo",
                "/usuarios/editar/1",
                "/usuarios/toggle/1",
            ]

            for rota in rotas:
                response = client.get(rota, follow_redirects=True)
                assert "Acesso Negado" in response.get_data(as_text=True)

    # --- USER MANAGEMENT LOGIC ---

    def test_editar_usuario_duplicado(self, client, app):
        """Testa validação de nome de usuário duplicado na edição."""
        # Logar como admin
        with client.session_transaction() as sess:
            sess["_user_id"] = "uuid-1"

        with patch("flask_login.utils._get_user") as mock_curr_user:
            admin = MagicMock()
            admin.is_authenticated = True
            admin.is_admin = True
            mock_curr_user.return_value = admin

            # Mock do banco: User sendo editado (ID 2) e Outro user existente (ID 3)
            user_editing = MagicMock()
            user_editing.id = 2

            user_existing = MagicMock()
            user_existing.id = 3  # ID diferente -> conflito

            with patch(
                "App.Modulos.Autenticacao.rotas.db.session.get",
                return_value=user_editing,
            ):
                with patch(
                    "App.Modulos.Autenticacao.rotas.Usuario.query"
                ) as mock_query:
                    # Quando buscar por username, retorna o user_existing
                    mock_query.filter_by.return_value.first.return_value = user_existing

                    response = client.post(
                        "/usuarios/editar/uuid-2",
                        data={
                            "nome": "New Name",
                            "username": "taken_name",
                            "email": "a@a.com",
                            "role": "Operador",
                            "ativo": "y",
                        },
                        follow_redirects=True,
                    )

                    assert "Este nome de usuário já está em uso" in response.get_data(
                        as_text=True
                    )

    def test_toggle_usuario_self_block(self, client, app):
        """Testa se admin não pode desativar a si mesmo."""
        with client.session_transaction() as sess:
            sess["_user_id"] = "uuid-1"

        with patch("flask_login.utils._get_user") as mock_curr_user:
            admin = MagicMock()
            admin.is_authenticated = True
            admin.is_admin = True
            admin.id = "uuid-1"  # ID string
            mock_curr_user.return_value = admin

            # Mock get retorna o próprio admin
            with patch(
                "App.Modulos.Autenticacao.rotas.db.session.get", return_value=admin
            ):
                response = client.get("/usuarios/toggle/uuid-1", follow_redirects=True)
                assert (
                    "Você não pode desativar seu próprio usuário"
                    in response.get_data(as_text=True)
                )

    def test_editar_usuario_404(self, client):
        """Testa erro 404 se usuário não existe na edição."""
        with client.session_transaction() as sess:
            sess["_user_id"] = "uuid-1"

        with patch("flask_login.utils._get_user") as mock_curr_user:
            # Setup admin
            admin = MagicMock()
            admin.is_authenticated = True
            admin.is_admin = True
            mock_curr_user.return_value = admin

            with patch(
                "App.Modulos.Autenticacao.rotas.db.session.get", return_value=None
            ):
                response = client.get("/usuarios/editar/999")
                assert response.status_code == 404

    # --- PASSWORD CHANGE ---

    def test_change_password_wrong_old(self, client, app):
        """Testa falha ao errar a senha antiga."""
        # Logar
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"

        with patch("flask_login.utils._get_user") as mock_curr_user:
            user = MagicMock()
            user.is_authenticated = True
            user.check_password.return_value = False  # Senha antiga errada
            mock_curr_user.return_value = user

            # Necessário desabilitar CSRF explicitamente ou passar token se o form for validado
            # app.config['WTF_CSRF_ENABLED'] = False já deve estar no conftest

            response = client.post(
                url_for("auth.perfil"),
                data={
                    "password_old": "wrong",
                    "password_new": "new123456",
                    "password_confirm": "new123456",
                },
                follow_redirects=True,
            )

            assert "Senha atual incorreta" in response.get_data(as_text=True)

    # --- ERROR HANDLING ---

    def test_rate_limit_handler(self, client, app):
        """Testa o handler de limite de requisições."""
        from flask_limiter import RateLimitExceeded

        # Mock do objeto Limit interno que o Flask-Limiter espera na exceção
        mock_limit = MagicMock()
        mock_limit.limit = "1 per minute"
        mock_limit.error_message = None  # Importante pro handler nao quebrar

        # Cria rota temporária
        @app.route("/test_limit")
        def trigger_error():
            # A assinatura muda entre versões, mas geralmente recebe um objeto Limit ou msg
            raise RateLimitExceeded(mock_limit)

        # IMPORTANTE: O handler acessa current_user.is_authenticated.
        # Precisamos garantir que current_user não quebre (mesmo se anonimo).
        # Com flask-login, anonimo funciona, mas precisamos garantir contexto.

        with patch("flask_login.utils._get_user") as mock_curr_user:
            # Simula usuário anônimo
            anon = MagicMock()
            anon.is_authenticated = False
            mock_curr_user.return_value = anon

            response = client.get("/test_limit", follow_redirects=True)
            assert "Muitas requisições ao sistema" in response.get_data(as_text=True)
