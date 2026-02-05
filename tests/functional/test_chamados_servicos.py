from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado, Andamento
from App.Modulos.Agenda.modelo import Agendamento
from App.Modulos.Autenticacao.modelo import Usuario
from App.Modulos.Chamados.servicos import ChamadoService
from App.banco import db
import arrow
from datetime import datetime, timezone


def test_registrar_interacao_chamado_fechado(app, admin_user):
    """Testa que não é possível interagir em um chamado fechado (exceto reabrir)."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Test Closed Corp", cpf_cnpj="111", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado Fechado",
            descricao="Test",
            status="Fechado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

        # Tentar adicionar interação em chamado fechado
        success, msg = ChamadoService.registrar_interacao(
            chamado_id=chamado_id,
            usuario_id=admin_user.id,
            texto="Tentando interagir",
            tipo="Nota",
        )

        assert success is False
        assert "fechado" in msg.lower()


def test_registrar_interacao_reabrir_chamado_fechado(app, admin_user):
    """Testa que é possível reabrir um chamado fechado mudando status para Aberto."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Reopen Corp", cpf_cnpj="222", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Para Reabrir",
            descricao="Test",
            status="Fechado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

        # Reabrir chamado (mudar para Aberto)
        success, msg = ChamadoService.registrar_interacao(
            chamado_id=chamado_id,
            usuario_id=admin_user.id,
            texto="Reabrindo chamado",
            tipo="Nota",
            novo_status="Aberto",
        )

        assert success is True

        # Verificar que foi reaberto
        chamado = db.session.get(Chamado, chamado_id)
        assert chamado.status == "Aberto"


def test_registrar_interacao_chamado_inexistente(app, admin_user):
    """Testa retorno de erro quando chamado não existe."""
    with app.app_context():
        success, msg = ChamadoService.registrar_interacao(
            chamado_id="id-invalido-123",
            usuario_id=admin_user.id,
            texto="Test",
        )

        assert success is False
        assert "não encontrado" in msg.lower()


def test_finalizar_visita_invalida(app, admin_user):
    """Testa finalizar visita que não existe ou já foi finalizada."""
    with app.app_context():
        # Tentar finalizar visita inexistente
        success, msg = ChamadoService.finalizar_visita(
            agendamento_id="id-invalido", usuario_id=admin_user.id, relatorio="Test"
        )

        assert success is False
        assert "inválido" in msg.lower() or "não encontrado" in msg.lower()


def test_finalizar_visita_ja_finalizada(app, admin_user):
    """Testa que não é possível finalizar uma visita já realizada."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Double Finish Corp", cpf_cnpj="333", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test",
            descricao="Test",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar visita já realizada
        agendamento = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            status="Realizado",  # Já finalizada
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        ag_id = agendamento.id

        # Tentar finalizar novamente
        success, msg = ChamadoService.finalizar_visita(
            agendamento_id=ag_id, usuario_id=admin_user.id, relatorio="Teste"
        )

        assert success is False
        assert "inválido" in msg.lower() or "finalizado" in msg.lower()


def test_retratar_andamento_nao_autor(app, admin_user):
    """Testa que apenas o autor pode retratar um andamento."""
    with app.app_context():
        # Criar outro usuário
        outro_user = Usuario(
            username="outro_user", email="outro@test.com", role="Operador"
        )
        outro_user.set_password("123456")
        db.session.add(outro_user)
        db.session.commit()
        outro_id = outro_user.id

        cliente = Cliente(
            nome_razao="Retract Corp", cpf_cnpj="444", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test",
            descricao="Test",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Admin cria um andamento
        andamento = Andamento(
            chamado_id=chamado.id,
            usuario_id=admin_user.id,
            texto="Andamento do admin",
            tipo="Nota",
            created_by=admin_user.id,
        )
        db.session.add(andamento)
        db.session.commit()
        and_id = andamento.id

        # Outro usuário tenta retratar
        success, msg = ChamadoService.retratar_andamento(
            andamento_id=and_id, usuario_id=outro_id
        )

        assert success is False
        assert "autor" in msg.lower()


def test_retratar_andamento_ja_retratado(app, admin_user):
    """Testa que não é possível retratar um andamento já retratado."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Double Retract Corp", cpf_cnpj="555", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test",
            descricao="Test",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar andamento já retratado
        andamento = Andamento(
            chamado_id=chamado.id,
            usuario_id=admin_user.id,
            texto="Andamento retratado",
            tipo="Nota",
            foi_retratado=True,  # Já retratado
            created_by=admin_user.id,
        )
        db.session.add(andamento)
        db.session.commit()
        and_id = andamento.id

        # Tentar retratar novamente
        success, msg = ChamadoService.retratar_andamento(
            andamento_id=and_id, usuario_id=admin_user.id
        )

        assert success is False
        assert "já foi retratado" in msg.lower()


def test_retratar_andamento_tempo_expirado(app, admin_user):
    """Testa que não é possível retratar após 10 minutos."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Expired Corp", cpf_cnpj="666", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test",
            descricao="Test",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar andamento antigo (mais de 10 min)
        andamento = Andamento(
            chamado_id=chamado.id,
            usuario_id=admin_user.id,
            texto="Andamento antigo",
            tipo="Nota",
            created_by=admin_user.id,
        )
        db.session.add(andamento)
        db.session.commit()

        # Forçar created_at para ser antigo (12 minutos atrás)
        from datetime import timedelta

        andamento.created_at = datetime.now(timezone.utc) - timedelta(minutes=12)
        db.session.commit()
        and_id = andamento.id

        # Tentar retratar
        success, msg = ChamadoService.retratar_andamento(
            andamento_id=and_id, usuario_id=admin_user.id
        )

        assert success is False
        assert "tempo" in msg.lower() or "expirou" in msg.lower()


def test_retratar_andamento_inexistente(app, admin_user):
    """Testa retratar andamento que não existe."""
    with app.app_context():
        success, msg = ChamadoService.retratar_andamento(
            andamento_id="id-invalido", usuario_id=admin_user.id
        )

        assert success is False
        assert "não encontrado" in msg.lower()


def test_cancelar_visitas_pendentes(app, admin_user):
    """Testa o cancelamento automático de visitas pendentes."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Cancel Pending Corp", cpf_cnpj="777", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test Cancel",
            descricao="Test",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar 2 visitas pendentes
        ag1 = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            status="Agendado",
            created_by=admin_user.id,
        )
        ag2 = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=2).datetime,
            data_fim=arrow.now().shift(days=2, hours=1).datetime,
            status="Agendado",
            created_by=admin_user.id,
        )
        db.session.add_all([ag1, ag2])
        db.session.commit()

        # Cancelar todas as visitas pendentes
        count = ChamadoService.cancelar_visitas_pendentes(
            chamado_id=chamado.id, usuario_id=admin_user.id
        )

        assert count == 2

        # Verificar que ambas foram canceladas
        ag1_depois = db.session.get(Agendamento, ag1.id)
        ag2_depois = db.session.get(Agendamento, ag2.id)
        assert ag1_depois.status == "Cancelado"
        assert ag2_depois.status == "Cancelado"


def test_anular_visita_status_invalido(app, admin_user):
    """Testa que apenas visitas com status Agendado podem ser anuladas."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Invalid Status Corp", cpf_cnpj="888", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test",
            descricao="Test",
            status="Fechado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar visita já realizada
        ag = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            status="Realizado",
            created_by=admin_user.id,
        )
        db.session.add(ag)
        db.session.commit()
        ag_id = ag.id

        # Tentar anular
        success, msg = ChamadoService.anular_visita(
            agendamento_id=ag_id, usuario_id=admin_user.id
        )

        assert success is False
        assert "agendadas" in msg.lower() or "anuladas" in msg.lower()


def test_anular_visita_inexistente(app, admin_user):
    """Testa anular visita que não existe."""
    with app.app_context():
        success, msg = ChamadoService.anular_visita(
            agendamento_id="id-invalido", usuario_id=admin_user.id
        )

        assert success is False
        assert "não encontrado" in msg.lower()


def test_registrar_interacao_agendamento_sem_datas(app, admin_user):
    """Testa erro quando tenta agendar sem fornecer datas."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="No Dates Corp", cpf_cnpj="999", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test",
            descricao="Test",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Tentar mudar para Agendado sem dados de agendamento
        success, msg = ChamadoService.registrar_interacao(
            chamado_id=chamado.id,
            usuario_id=admin_user.id,
            texto="Tentando agendar",
            novo_status="Agendado",
            dados_agendamento={"inicio": None, "fim": None},  # Sem datas
        )

        assert success is False
        assert "obrigatórias" in msg.lower() or "datas" in msg.lower()


def test_reagendar_agendamento_inexistente(app, admin_user):
    """Testa reagendar agendamento que não existe."""
    with app.app_context():
        success, msg = ChamadoService.reagendar_visita(
            agendamento_id="id-invalido",
            nova_data_inicio=arrow.now().shift(days=1).datetime,
            nova_data_fim=arrow.now().shift(days=1, hours=1).datetime,
            tecnico_id=admin_user.id,
            usuario_id=admin_user.id,
        )

        assert success is False
        assert "não encontrado" in msg.lower()


def test_escalonamento_remove_tecnico(app, admin_user):
    """Testa que escalonar um chamado remove o técnico atribuído."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Escalate Corp", cpf_cnpj="1010", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test Escalate",
            descricao="Test",
            tecnico_id=admin_user.id,  # Tem técnico
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

        # Escalonar
        success, msg = ChamadoService.registrar_interacao(
            chamado_id=chamado_id,
            usuario_id=admin_user.id,
            texto="Escalonando para N2",
            novo_status="Escalonado",
        )

        assert success is True

        # Verificar que técnico foi removido
        chamado = db.session.get(Chamado, chamado_id)
        assert chamado.tecnico_id is None
        assert chamado.status == "Escalonado"


def test_fechar_chamado_cancela_visitas_pendentes(app, admin_user):
    """Testa que fechar um chamado cancela automaticamente visitas pendentes."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Close Cancel Corp", cpf_cnpj="1111", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test Close",
            descricao="Test",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar visita pendente
        ag = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            status="Agendado",
            created_by=admin_user.id,
        )
        db.session.add(ag)
        db.session.commit()
        ag_id = ag.id

        # Fechar chamado
        success, msg = ChamadoService.registrar_interacao(
            chamado_id=chamado.id,
            usuario_id=admin_user.id,
            texto="Resolvido",
            novo_status="Fechado",
        )

        assert success is True

        # Verificar que visita foi cancelada
        ag = db.session.get(Agendamento, ag_id)
        assert ag.status == "Cancelado"
