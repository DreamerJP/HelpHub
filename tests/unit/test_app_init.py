from App.iniciar import create_app


class TestAppInit:
    def test_create_app_testing_config(self):
        test_config = {
            "TESTING": True,
            "SECRET_KEY": "dev",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "TIMEZONE": "UTC",
            "BASE_DIR": "/tmp",
        }
        app = create_app(test_config=test_config)
        assert app.testing

    def test_health_check(self):
        test_config = {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "TIMEZONE": "UTC",
            "BASE_DIR": "/tmp",
        }
        app = create_app(test_config=test_config)
        client = app.test_client()
        response = client.get("/health-check")
        assert response.status_code == 200
        data = response.get_json()
        assert data["sistema"] == "HelpHub 4.1"

    def test_db_naming_convention_setup(self, app):
        """Verifica se a convenção de nomes do SQLAlchemy foi carregada corretamente."""
        with app.app_context():
            from App.banco import db

            naming_convention = db.metadata.naming_convention
            assert (
                naming_convention["fk"]
                == "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
            )
            assert naming_convention["pk"] == "pk_%(table_name)s"

    def test_migrate_directory_setup(self):
        """Verifica se o Migrate está configurado para a pasta App/migrations."""
        app = create_app()  # Usa config padrão
        # O migrate fica guardado nas extensões do app
        migrate = app.extensions.get("migrate")
        assert migrate is not None
        # Verifica se o diretório termina com App\migrations ou App/migrations
        assert "App" in migrate.directory
        assert "migrations" in migrate.directory
