from flask_apscheduler import APScheduler
import arrow
from functools import wraps
from .Modulos.Administracao.modelo import TarefaMonitor

scheduler = APScheduler()


def configurar_agendamento(app):
    """
    Configura as tarefas automáticas do sistema.
    """
    with app.app_context():
        # Evita registrar o job duplicado caso o Flask recarregue
        if not scheduler.get_job("backup_diario_auto"):
            # Agenda para rodar todo dia às 03:00 da manhã
            scheduler.add_job(
                id="backup_diario_auto",
                func=rotina_backup_diario,
                trigger="cron",
                hour=3,
                minute=0,
                args=[app],
            )

        if not scheduler.get_job("auto_fechar_pendentes"):
            # Agenda para rodar todo dia às 03:00 da manhã também
            scheduler.add_job(
                id="auto_fechar_pendentes",
                func=rotina_fechamento_automatico,
                trigger="cron",
                hour=3,
                minute=5,  # 5 minutos após o backup
                args=[app],
            )


def monitorar_tarefa(tarefa_id, nome):
    """Decorador para registrar o status de execução de uma tarefa no banco."""

    def decorator(f):
        @wraps(f)
        def decorated_function(app, *args, **kwargs):
            try:
                # Se for backup, registra o próximo vencimento (amanhã às 03:00)
                # (Isso pode ser expandido depois conforme a tarefa)
                resultado = f(app, *args, **kwargs)

                msg = "Executada com sucesso."
                if isinstance(resultado, tuple) and len(resultado) == 2:
                    msg = str(resultado[1])
                elif isinstance(resultado, int):
                    msg = f"Processados {resultado} itens."

                TarefaMonitor.atualizar(tarefa_id, nome, "Sucesso", msg)
                return resultado
            except Exception as e:
                app.logger.error(f"Erro na tarefa {nome}: {e}")
                TarefaMonitor.atualizar(tarefa_id, nome, "Erro", str(e))
                raise e

        return decorated_function

    return decorator


def verificar_tarefas_atrasadas(app):
    """
    Verifica se tarefas críticas deixaram de rodar
    porque o servidor estava desligado.
    """
    with app.app_context():
        agora = arrow.now(app.config["TIMEZONE"])
        status_geral = []

        # 1. Checar Backup Automático (Deveria rodar às 03h)
        if agora.hour >= 3:
            task = TarefaMonitor.query.filter_by(tarefa_id="backup_diario").first()
            if not task or (
                task.ultima_execucao
                and arrow.get(task.ultima_execucao).date() < agora.date()
            ):
                status_geral.append({"tarefa": "Backup Diário", "id": "backup_diario"})

        # 2. Checar Fechamento de Chamados (Deveria rodar às 03h)
        if agora.hour >= 3:
            task = TarefaMonitor.query.filter_by(tarefa_id="fechar_pendentes").first()
            if not task or (
                task.ultima_execucao
                and arrow.get(task.ultima_execucao).date() < agora.date()
            ):
                status_geral.append(
                    {"tarefa": "Fechamento de Chamados", "id": "fechar_pendentes"}
                )

        app.config["TAREFAS_ATRASADAS"] = status_geral


@monitorar_tarefa("backup_diario", "Backup Diário Automático")
def rotina_backup_diario(app):
    """
    Wrapper para rodar o backup dentro do contexto da aplicação.
    """
    with app.app_context():
        from .Modulos.Administracao.servicos import executar_backup_banco

        app.logger.info("Iniciando rotina de backup automático agendado.")
        sucesso, msg = executar_backup_banco(origem_manual=False)
        return sucesso, msg


@monitorar_tarefa("fechar_pendentes", "Fechamento de Chamados por Inatividade")
def rotina_fechamento_automatico(app):
    """
    Wrapper para rodar o encerramento automático dentro do contexto da aplicação.
    """
    with app.app_context():
        from .Modulos.Chamados.servicos import encerrar_chamados_pendentes_excedidos

        app.logger.info(
            "Iniciando rotina de fechamento automático de chamados pendentes."
        )
        count = encerrar_chamados_pendentes_excedidos()
        return count
