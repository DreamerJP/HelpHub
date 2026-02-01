import pytest
from App.iniciar import create_app
from App.banco import db
from App.Modulos.Autenticacao.modelo import Usuario


@pytest.fixture(scope="function")
def app():
    """Create and configure a new app instance for each test session."""
    import uuid
    import os

    # We use a single predictable DB name for the test transaction to ensure
    # that the client (running in a thread/process) and the test setup share the same file
    # if using sqlite. But unique names are better for parallelism.
    # The issue might be that client.post/get spawns a separate context that loses the db_name if not config'd right?
    # No, with create_app(test_config) it should be baked in.

    # Create tests/instance directory if it doesn't exist
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.path.join(tests_dir, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    db_name = os.path.join(instance_dir, f"tests_{uuid.uuid4().hex}.db")
    # Fix for Windows: SQLite URI requires forward slashes
    db_name_uri = db_name.replace(os.sep, "/")

    import sqlalchemy.pool

    upload_dir = os.path.join(instance_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_name_uri}",
        "SQLALCHEMY_ENGINE_OPTIONS": {"poolclass": sqlalchemy.pool.NullPool},
        "UPLOAD_FOLDER": upload_dir,
        "BASE_DIR": instance_dir,
        "TIMEZONE": "America/Sao_Paulo",
        "WTF_CSRF_ENABLED": False,
        "PRESERVE_CONTEXT_ON_EXCEPTION": False,
    }

    app = create_app(config_name="testing", test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    # Clean up files
    import shutil

    try:
        if os.path.exists(db_name):
            os.remove(db_name)
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
    except Exception as e:
        print(f"Error during cleanup: {e}")


@pytest.fixture(scope="function")
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """A test runner for the app."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def _db(app):
    """
    Fixture for database rollback transactions.
    Used internally by pytest-flask-sqlalchemy or custom db handling if needed.
    Here we rely on app context from 'app' fixture but can add per-function cleanup.
    """
    with app.app_context():
        yield db


@pytest.fixture(scope="function")
def admin_user(app):
    """Create a test admin user."""
    with app.app_context():
        user = Usuario(username="admin_test", email="admin@test.com", role="Admin")
        user.set_password("123456")
        db.session.add(user)
        db.session.commit()

        yield user
