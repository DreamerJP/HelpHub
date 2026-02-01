from flask import Flask
from flask_login import LoginManager
import logging
from logging.handlers import RotatingFileHandler
import os

# Imports locais/internos do App
from flask_wtf import CSRFProtect
from .configurar import config
from .banco import db
from .seguranca import limiter
from .agendador import scheduler, configurar_agendamento, verificar_tarefas_atrasadas

# Import Blueprints
from .Modulos.Layout.rotas import layout_bp
from .Modulos.Autenticacao.rotas import auth_bp
from .Modulos.Departamentos.rotas import dept_bp
from .Modulos.Administracao.rotas import admin_bp
from .Modulos.Clientes.rotas import clientes_bp
from .Modulos.Chamados.rotas import chamados_bp
from .Modulos.Agenda.rotas import agenda_bp

# Import Modelos para o SQLAlchemy reconhecer na criação
from .Modulos.Autenticacao.modelo import Usuario
from .Modulos.Departamentos.modelo import Departamento  # noqa
from .Modulos.Clientes.modelo import Cliente  # noqa
from .Modulos.Chamados.modelo import Chamado, Andamento  # noqa
from .Modulos.Agenda.modelo import Agendamento  # noqa
from .Modulos.Administracao.modelo import Configuracao  # noqa

csrf = CSRFProtect()


def create_app(config_name=None, test_config=None):
    app = Flask(__name__)

    if test_config:
        app.config.from_mapping(test_config)
    else:
        # Prioridade: Argumento -> Variável de Ambiente -> 'production'
        if not config_name:
            config_name = os.environ.get("FLASK_CONFIG", "production")

        app.config.from_object(config.get(config_name, config["production"]))

    # 0. Garantir que as pastas base existam (Data, Logs, Uploads)
    # Isso evita erros ao tentar criar o banco de dados ou arquivos de log
    if not app.config.get("TESTING"):
        data_dir = os.path.join(app.config["BASE_DIR"], "Data")
        logs_dir = os.path.join(data_dir, "Logs")
        uploads_dir = os.path.join(data_dir, "Uploads")

        for directory in [data_dir, logs_dir, uploads_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    # 1. Configurar Logger (Arquivo real em Data/Logs/system.log)
    # Habilitamos logs em arquivo sempre, exceto em ambiente de teste
    if not app.testing:
        log_dir = os.path.join(app.config["BASE_DIR"], "Data", "Logs")

        # Filtro para injetar o IP real no log
        from .utils import RequestEntityFilter

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "system.log"),
            maxBytes=1024 * 1024,  # 1MB
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(clientip)s] %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.addFilter(RequestEntityFilter())
        file_handler.setLevel(logging.INFO)

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("HelpHub 4.0 Iniciado")

    # 2. Inicializar Extensões
    db.init_app(app)
    csrf.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    # Inicializar Limiter
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, user_id)

    # 4. Inicializar Agendador (Apenas se não for ambiente de teste)
    app.config["SCHEDULER_ERROR"] = False
    if not app.config.get("TESTING"):
        # No Windows/Werkzeug, isso roda 2x. O if garante que rode apenas no processo principal.
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
            try:
                scheduler.init_app(app)
                scheduler.start()
                configurar_agendamento(app)
                app.logger.info("Agendador de tarefas iniciado com sucesso.")
            except RuntimeError as e:
                app.config["SCHEDULER_ERROR"] = str(e)
                if "uWSGI" in str(e):
                    app.logger.warning(
                        "Agendador detectou uWSGI sem threads. Pulando inicializacao..."
                    )
                else:
                    app.logger.error(f"Erro ao iniciar agendador: {e}")
                    raise e
            except Exception as e:
                app.config["SCHEDULER_ERROR"] = str(e)
                app.logger.error(f"Erro inesperado no agendador: {e}")

    # 5. Context Processor para globais de template
    @app.context_processor
    def inject_globals():
        return {
            "SCHEDULER_ERROR": app.config.get("SCHEDULER_ERROR"),
            "TAREFAS_ATRASADAS": app.config.get("TAREFAS_ATRASADAS", []),
            "TIMEZONE": app.config["TIMEZONE"],
        }

    # 6. Registrar Blueprints
    app.register_blueprint(layout_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dept_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(chamados_bp)
    app.register_blueprint(agenda_bp)

    # 6. Rota de Diagnóstico
    @app.route("/health-check")
    def health_check():
        try:
            import arrow

            # Garante que estamos pegando a hora correta (UTC-3)
            agora = arrow.now(app.config["TIMEZONE"])
            time_str = agora.format("YYYY-MM-DD HH:mm:ss")
        except ImportError:
            time_str = "Instale a biblioteca 'arrow' para ver a hora correta."

        return {
            "sistema": "HelpHub 4.0",
            "status": "Online/Pronto",
            "config_timezone": app.config["TIMEZONE"],
            "hora_atual_servidor": time_str,
        }

    # 7. Criação Automática do Banco e Usuário Admin (Apenas se NÃO for teste)
    if not app.config.get("TESTING"):
        with app.app_context():
            # Cria as tabelas se não existirem
            db.create_all()

            # Cria admin padrão se não houver usuários
            if not Usuario.query.first():
                print("--- Criando Usuario Admin Padrão... ---")
                admin = Usuario(
                    username="admin",
                    nome="Administrador Sistema",
                    email="admin@helphub.com",
                    role="Admin",
                )
                admin.set_password("admin123")
                admin.save()
                # Log de criação do admin
                app.logger.info("Usuário Admin criado automaticamente.")
                print("--- Admin criado: admin / admin123 ---")

            # 8. Verificar tarefas atrasadas (resiliência) após o banco estar pronto
            verificar_tarefas_atrasadas(app)

    return app
