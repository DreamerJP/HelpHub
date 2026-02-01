from App.Modulos.Autenticacao.modelo import Usuario
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado, Andamento
from App.Modulos.Departamentos.modelo import Departamento
from App.Modulos.Agenda.modelo import Agendamento
from App.Modulos.Administracao.modelo import Configuracao
from datetime import datetime, timedelta


def test_usuario_creation(app):
    """Test user creation and password hashing."""
    with app.app_context():
        user = Usuario(username="testuser", email="test@test.com")
        user.set_password("securepassword")

        assert user.username == "testuser"
        assert user.email == "test@test.com"
        assert user.password_hash is not None
        assert user.check_password("securepassword")
        assert not user.check_password("wrongpassword")
        assert not user.is_admin


def test_cliente_creation(app, _db):
    """Test client creation and validation."""
    with app.app_context():
        # Create user for created_by
        user = Usuario(username="creator", email="c@c.com")
        user.set_password("123456")
        _db.session.add(user)
        _db.session.commit()

        cliente = Cliente(
            nome_razao="Test Company",
            cpf_cnpj="12345678000199",
            email="contact@company.com",
            created_by=user.id,
        )
        _db.session.add(cliente)
        _db.session.commit()

        saved_cliente = Cliente.query.first()
        assert saved_cliente.nome_razao == "Test Company"
        assert saved_cliente.cpf_cnpj == "12345678000199"
        assert saved_cliente.created_by == user.id


def test_chamado_workflow(app, _db):
    """Test ticket creation, protocol generation, and status."""
    with app.app_context():
        user = Usuario(username="tech", email="tech@hub.com")
        user.set_password("123456")
        _db.session.add(user)

        dept = Departamento(nome="Suporte")
        _db.session.add(dept)

        cliente = Cliente(
            nome_razao="Client X", cpf_cnpj="11122233300", email="x@x.com", created_by=1
        )
        _db.session.add(cliente)
        _db.session.commit()  # Get IDs

        chamado = Chamado(
            cliente_id=cliente.id,
            departamento_id=dept.id,
            assunto="Internet Down",
            descricao="No connection",
            prioridade="Alta",
            created_by=user.id,
        )
        chamado.gerar_protocolo()

        _db.session.add(chamado)
        _db.session.commit()

        assert chamado.status == "Aberto"  # Default
        assert chamado.protocolo is not None
        assert len(chamado.protocolo) > 10
        assert "Internet Down" in chamado.assunto


def test_andamento_creation(app, _db):
    """Test adding updates to a ticket."""
    with app.app_context():
        # Setup prerequisites
        user = Usuario(username="agent", email="agent@hub.com")
        user.set_password("123456")
        _db.session.add(user)
        cliente = Cliente(
            nome_razao="Client Y", cpf_cnpj="22233344400", email="y@y.com", created_by=1
        )
        _db.session.add(cliente)
        _db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id, assunto="Test", descricao="Desc", created_by=user.id
        )
        chamado.gerar_protocolo()
        _db.session.add(chamado)
        _db.session.commit()

        # Add update
        andamento = Andamento(
            chamado_id=chamado.id,
            usuario_id=user.id,
            texto="Investigating issue...",
            tipo="Nota Interna",
            created_by=user.id,
        )
        _db.session.add(andamento)
        _db.session.commit()

        assert len(chamado.andamentos) == 1
        assert chamado.andamentos[0].texto == "Investigating issue..."
        assert chamado.andamentos[0].usuario.username == "agent"


def test_agendamento_creation(app, _db):
    """Test scheduling creation."""
    with app.app_context():
        # Setup
        user = Usuario(username="scheduler", email="sched@hub.com")
        user.set_password("123456")
        _db.session.add(user)
        cliente = Cliente(
            nome_razao="Client Z", cpf_cnpj="33344455500", email="z@z.com", created_by=1
        )
        _db.session.add(cliente)
        _db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Visit",
            descricao="Visit needed",
            created_by=user.id,
        )
        chamado.gerar_protocolo()
        _db.session.add(chamado)
        _db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=1)

        agenda = Agendamento(
            chamado_id=chamado.id,
            data_inicio=start,
            data_fim=end,
            tecnico_id=user.id,
            created_by=user.id,
            instrucoes_tecnicas="Doing something...",
        )
        _db.session.add(agenda)
        _db.session.commit()

        saved_agenda = Agendamento.query.first()
        assert saved_agenda.chamado_id == chamado.id
        assert saved_agenda.tecnico.username == "scheduler"
        assert saved_agenda.status == "Agendado"  # Default
        assert saved_agenda.instrucoes_tecnicas == "Doing something..."


def test_configuracao_model(app, _db):
    """Test Configuracao model singleton behavior and default values."""
    with app.app_context():
        cfg = Configuracao.get_config()
        assert cfg.empresa_nome == "Minha Empresa"

        cfg.empresa_nome = "HelpHub Inc."
        cfg.save()

        # Should return the same record
        cfg2 = Configuracao.get_config()
        assert cfg2.empresa_nome == "HelpHub Inc."
        assert Configuracao.query.count() == 1


def test_tarefa_monitor_model(app, _db):
    """Test TarefaMonitor static methods and persistence."""
    from App.Modulos.Administracao.modelo import TarefaMonitor

    with app.app_context():
        # Testa criação/atualização
        TarefaMonitor.atualizar(
            "tarefa_teste", "Tarefa de Teste", "Sucesso", "Mensagem OK"
        )

        task = TarefaMonitor.query.filter_by(tarefa_id="tarefa_teste").first()
        assert task.nome_amigavel == "Tarefa de Teste"
        assert task.status == "Sucesso"

        # Testa atualização do mesmo registro
        TarefaMonitor.atualizar(
            "tarefa_teste", "Tarefa de Teste", "Erro", "Falhou agora"
        )
        assert TarefaMonitor.query.count() == 1
        assert (
            TarefaMonitor.query.filter_by(tarefa_id="tarefa_teste").first().status
            == "Erro"
        )
