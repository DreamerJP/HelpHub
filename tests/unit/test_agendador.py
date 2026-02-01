from unittest.mock import MagicMock, patch
from App.agendador import (
    configurar_agendamento,
    rotina_backup_diario,
    rotina_fechamento_automatico,
    scheduler,
    verificar_tarefas_atrasadas,
)
from App.Modulos.Administracao.modelo import TarefaMonitor


class TestAgendador:
    def test_configurar_agendamento_add_jobs(self, app):
        """Testa se os jobs (backup e fechamento) são adicionados corretamente se não existirem."""
        # Limpa jobs existentes para isolamento
        scheduler.remove_all_jobs()

        with patch.object(scheduler, "add_job") as mock_add_job:
            configurar_agendamento(app)

            # Agora temos 2 jobs: backup e auto_fechar
            assert mock_add_job.call_count == 2

            # Verifica o job de Backup
            call_backup = mock_add_job.call_args_list[0]
            assert call_backup.kwargs["id"] == "backup_diario_auto"
            assert call_backup.kwargs["hour"] == 3
            assert call_backup.kwargs["minute"] == 0

            # Verifica o job de Fechamento Automático
            call_fechar = mock_add_job.call_args_list[1]
            assert call_fechar.kwargs["id"] == "auto_fechar_pendentes"
            assert call_fechar.kwargs["hour"] == 3
            assert call_fechar.kwargs["minute"] == 5

    def test_configurar_agendamento_jobs_exist(self, app):
        """Testa se os jobs não são adicionados novamente se já existirem."""
        # Limpa e adiciona jobs fakes
        scheduler.remove_all_jobs()
        scheduler.add_job(id="backup_diario_auto", func=lambda: None)
        scheduler.add_job(id="auto_fechar_pendentes", func=lambda: None)

        with patch.object(scheduler, "add_job") as mock_add_job:
            configurar_agendamento(app)
            mock_add_job.assert_not_called()

        # Cleanup
        scheduler.remove_all_jobs()

    @patch("App.Modulos.Administracao.servicos.executar_backup_banco")
    def test_rotina_backup_diario_sucesso(self, mock_backup, app):
        """Testa a rotina de backup em caso de sucesso."""
        mock_backup.return_value = (True, "Backup OK")
        app.logger = MagicMock()

        rotina_backup_diario(app)

        mock_backup.assert_called_once()

        # Verifica se o monitor registrou o sucesso
        with app.app_context():
            task = TarefaMonitor.query.filter_by(tarefa_id="backup_diario").first()
            assert task is not None
            assert task.status == "Sucesso"
            assert "Backup OK" in task.mensagem

    @patch("App.Modulos.Chamados.servicos.encerrar_chamados_pendentes_excedidos")
    def test_rotina_fechamento_automatico(self, mock_fechar, app):
        """Testa a rotina de fechamento automático de chamados."""
        mock_fechar.return_value = 5  # Simula 5 chamados fechados
        app.logger = MagicMock()

        rotina_fechamento_automatico(app)

        mock_fechar.assert_called_once()

        # Verifica se o monitor registrou o sucesso
        with app.app_context():
            task = TarefaMonitor.query.filter_by(tarefa_id="fechar_pendentes").first()
            assert task is not None
            assert task.status == "Sucesso"
            assert "5 itens" in task.mensagem

    def test_verificar_tarefas_atrasadas_detecta_pendencia(self, app, _db):
        """Testa se a função detecta corretamente tarefas que não rodaram."""
        import arrow

        with app.app_context():
            # Força o horário para 10:00 da manhã (onde a verificação ocorre)
            agora = arrow.now(app.config["TIMEZONE"]).replace(hour=10)

            with patch("arrow.now", return_value=agora):
                # Caso 1: Nenhuma tarefa registrada (deve detectar atraso)
                verificar_tarefas_atrasadas(app)
                assert len(app.config["TAREFAS_ATRASADAS"]) == 2

                # Caso 2: Tarefa registrada como rodada hoje
                TarefaMonitor.atualizar("backup_diario", "Backup", "Sucesso", "OK")
                TarefaMonitor.atualizar("fechar_pendentes", "Fechar", "Sucesso", "OK")

                verificar_tarefas_atrasadas(app)
                assert len(app.config["TAREFAS_ATRASADAS"]) == 0

    @patch("App.Modulos.Administracao.servicos.executar_backup_banco")
    def test_monitorar_tarefa_registra_erro(self, mock_backup, app):
        """Testa se o decorador captura e registra exceções no banco."""
        mock_backup.side_effect = Exception("Fusível queimado")
        app.logger = MagicMock()

        try:
            rotina_backup_diario(app)
        except Exception:
            pass

        with app.app_context():
            task = TarefaMonitor.query.filter_by(tarefa_id="backup_diario").first()
            assert task.status == "Erro"
            assert "Fusível queimado" in task.mensagem
