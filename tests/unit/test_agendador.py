from unittest.mock import MagicMock, patch
from App.servicos.agendador import (
    configurar_agendamento,
    rotina_backup_diario,
    rotina_fechamento_automatico,
    scheduler,
    verificar_tarefas_atrasadas,
)
from App.Modulos.Administracao.modelo import TarefaMonitor
from App.banco import db
import arrow


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
            assert call_backup.kwargs["id"] == "auto_backup_diario"
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
        scheduler.add_job(id="auto_backup_diario", func=lambda: None)
        scheduler.add_job(id="auto_fechar_pendentes", func=lambda: None)

        with patch.object(scheduler, "add_job") as mock_add_job:
            configurar_agendamento(app)
            mock_add_job.assert_not_called()

        # Cleanup
        scheduler.remove_all_jobs()

    def test_rotina_backup_diario_sucesso(self, app):
        """Testa a rotina de backup real (sem mocks) contra o banco de teste."""
        app.logger = MagicMock()

        # Executa a rotina real
        rotina_backup_diario(app)

        # Verifica se o monitor registrou o sucesso no banco real de teste
        with app.app_context():
            task = TarefaMonitor.query.filter_by(tarefa_id="backup_diario").first()
            assert task is not None
            assert task.status == "Sucesso"
            assert "Backup" in task.mensagem

    def test_rotina_fechamento_automatico_real(self, app, admin_user):
        """Testa a rotina real de fechamento (sem mocks) com dados reais no banco."""
        from App.Modulos.Chamados.modelo import Chamado, Andamento
        from App.banco import db
        from datetime import datetime, timedelta

        app.logger = MagicMock()

        with app.app_context():
            # 1. Criar um cliente para o chamado
            from App.Modulos.Clientes.modelo import Cliente

            cliente = Cliente(
                nome_razao="Test Agendador Corp",
                cpf_cnpj="123",
                created_by=admin_user.id,
            )
            db.session.add(cliente)
            db.session.commit()

            # 2. Criar um chamado pendente antigo (3 dias atrás)
            antigo = datetime.now() - timedelta(days=3)
            chamado = Chamado(
                assunto="Teste Real Agendador",
                descricao="Deve fechar",
                status="Pendente",
                cliente_id=cliente.id,
                created_at=antigo,
                updated_at=antigo,
            )
            chamado.gerar_protocolo()
            db.session.add(chamado)
            db.session.flush()

            andamento = Andamento(
                chamado_id=chamado.id,
                usuario_id=admin_user.id,
                texto="Aguardando",
                created_at=antigo,
            )
            db.session.add(andamento)
            db.session.commit()
            chamado_id = chamado.id

        # 3. Executa a rotina real (ela deve encontrar e fechar 1 chamado)
        rotina_fechamento_automatico(app)

        # 4. Verificações
        with app.app_context():
            # O chamado deve estar fechado
            ch = db.session.get(Chamado, chamado_id)
            assert ch.status == "Fechado"

            # O monitor deve registrar 1 item processado
            task = TarefaMonitor.query.filter_by(tarefa_id="fechar_pendentes").first()
            assert task.status == "Sucesso"
            assert "1 itens" in task.mensagem

    def test_verificar_tarefas_atrasadas_detecta_pendencia(self, app, _db):
        """Testa se a função detecta corretamente tarefas que não rodaram."""

        with app.app_context():
            # Manter a limpeza para o teste
            TarefaMonitor.query.delete()
            db.session.commit()

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

    def test_monitorar_tarefa_isolamento_contexto(self, app):
        """
        Testa o ponto crítico: o decorador monitorar_tarefa deve funcionar
        mesmo se for chamado de um local sem um contexto ativo prévio.
        """
        app.logger = MagicMock()

        # Criamos uma função simples decorada
        from App.servicos.agendador import monitorar_tarefa

        @monitorar_tarefa("tarefa_teste", "Tarefa de Teste Contexto")
        def minha_funcao_sem_contexto(app):
            # Esta função simula estar rodando em uma thread "crua"
            # Ela tenta acessar o db para provar que o decorador abriu o contexto
            from App.Modulos.Autenticacao.modelo import Usuario

            return Usuario.query.first() is not None or True

        # Chamamos a função FORA de um bloco 'with app.app_context()'
        # Se o decorador não abrir o contexto, isso aqui vai explodir
        resultado = minha_funcao_sem_contexto(app)
        assert resultado is True

        with app.app_context():
            task = TarefaMonitor.query.filter_by(tarefa_id="tarefa_teste").first()
            assert task.status == "Sucesso"
            assert task.nome_amigavel == "Tarefa de Teste Contexto"
