import os

# Caminho base do projeto (raiz do HelpHub 4.0)
# App/configurar.py -> parent is App -> parent is Root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data")


class Config:
    """Configurações Base"""

    # Paths Globais
    BASE_DIR = BASE_DIR

    # Segurança
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-mudar-em-producao-123"

    # Banco de Dados (SQLite em Data/banco.db)
    DB_PATH = os.path.join(DATA_DIR, "banco.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configurações Regionais
    TIMEZONE = "America/Sao_Paulo"

    # Uploads (Fora do App)
    UPLOAD_FOLDER = os.path.join(DATA_DIR, "Uploads")
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB limite

    # Controle de Sessão
    from datetime import timedelta

    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # Expira em 2h de inatividade
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


# Dicionário de exportação
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
