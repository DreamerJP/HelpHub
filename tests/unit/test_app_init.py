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
        assert data["sistema"] == "HelpHub 4.0"
