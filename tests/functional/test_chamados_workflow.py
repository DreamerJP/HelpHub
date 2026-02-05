from flask import url_for
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado, Andamento
from App.banco import db
from datetime import datetime, timedelta


def test_status_filtering_tabs(client, app, admin_user):
    """Testa se os filtros de aba (status) estão funcionando corretamente na lista."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Test Corp", cpf_cnpj="123", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.flush()

        # Criar chamados com diferentes status
        c1 = Chamado(
            cliente_id=cliente.id,
            assunto="Aberto Ticket",
            descricao="Desc 1",
            status="Aberto",
            created_by=admin_user.id,
        )
        c2 = Chamado(
            cliente_id=cliente.id,
            assunto="Agendado Ticket",
            descricao="Desc 2",
            status="Agendado",
            created_by=admin_user.id,
        )
        c3 = Chamado(
            cliente_id=cliente.id,
            assunto="Escalonado Ticket",
            descricao="Desc 3",
            status="Escalonado",
            created_by=admin_user.id,
        )
        c4 = Chamado(
            cliente_id=cliente.id,
            assunto="Pendente Ticket",
            descricao="Desc 4",
            status="Pendente",
            created_by=admin_user.id,
        )
        c5 = Chamado(
            cliente_id=cliente.id,
            assunto="Fechado Ticket",
            descricao="Desc 5",
            status="Fechado",
            created_by=admin_user.id,
        )

        for c in [c1, c2, c3, c4, c5]:
            c.gerar_protocolo()
            db.session.add(c)
        db.session.commit()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Teste Aba Abertos (Geral - Tudo exceto Fechado)
    response = client.get(url_for("chamados.lista", status="ativos"))
    assert b"Aberto Ticket" in response.data
    assert b"Agendado Ticket" in response.data
    assert b"Pendente Ticket" in response.data
    assert b"Escalonado Ticket" in response.data  # Agora está incluso!
    assert b"Fechado Ticket" not in response.data

    # Teste Aba Triagem (Abertos)
    response = client.get(url_for("chamados.lista", status="abertos"))
    assert b"Aberto Ticket" in response.data
    assert b"Agendado Ticket" not in response.data

    # Teste Aba Visitas (Agendados)
    response = client.get(url_for("chamados.lista", status="agendados"))
    assert b"Agendado Ticket" in response.data
    assert b"Aberto Ticket" not in response.data

    # Teste Aba Nível Superior (Escalonados)
    response = client.get(url_for("chamados.lista", status="escalonados"))
    assert b"Escalonado Ticket" in response.data
    assert b"Aberto Ticket" not in response.data


def test_escalation_clears_technician(client, app, admin_user):
    """Testa se mudar para Escalonado remove o técnico atribuído."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Escala Corp", cpf_cnpj="456", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Ticket para Escalar",
            descricao="Precisa escalar",
            status="Aberto",
            tecnico_id=admin_user.id,
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Mudar status para Escalonado
    client.post(
        url_for("chamados.detalhe", id=chamado_id),
        data={"texto": "Escalando para N2", "novo_status": "Escalonado"},
        follow_redirects=True,
    )

    with app.app_context():
        ch = db.session.get(Chamado, chamado_id)
        assert ch.status == "Escalonado"
        assert ch.tecnico_id is None  # Deve ter sido limpo


def test_auto_closure_logic(app, admin_user):
    """Testa a lógica de fechamento automático de chamados pendentes (Zelador)."""
    from App.Modulos.Chamados.servicos import encerrar_chamados_pendentes_excedidos

    with app.app_context():
        cliente = Cliente(
            nome_razao="Zombie Corp", cpf_cnpj="999", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.flush()

        # Chamado 1: Pendente há mais de 48h (Deve fechar)
        c1 = Chamado(
            cliente_id=cliente.id,
            assunto="Old Pending",
            descricao="Desc pending",
            status="Pendente",
            created_by=admin_user.id,
        )
        c1.gerar_protocolo()
        db.session.add(c1)
        db.session.flush()

        # Retroceder a data da última interação (andamento)
        data_antiga = datetime.now() - timedelta(hours=50)
        and1 = Andamento(
            chamado_id=c1.id,
            usuario_id=admin_user.id,
            texto="Client help?",
            created_by=admin_user.id,
        )
        and1.created_at = data_antiga
        db.session.add(and1)

        # Chamado 2: Pendente há menos de 48h (Não deve fechar)
        c2 = Chamado(
            cliente_id=cliente.id,
            assunto="New Pending",
            descricao="Desc new pending",
            status="Pendente",
            created_by=admin_user.id,
        )
        c2.gerar_protocolo()
        db.session.add(c2)
        db.session.flush()

        and2 = Andamento(
            chamado_id=c2.id,
            usuario_id=admin_user.id,
            texto="Just sent",
            created_by=admin_user.id,
        )
        db.session.add(and2)

        db.session.commit()

        # Executar o serviço
        count = encerrar_chamados_pendentes_excedidos()
        assert count == 1

        # Verificar estados
        db.session.refresh(c1)
        db.session.refresh(c2)
        assert c1.status == "Fechado"
        assert c2.status == "Pendente"

        # Verificar log de sistema no c1
        ultimo_log = (
            Andamento.query.filter_by(chamado_id=c1.id)
            .order_by(Andamento.created_at.desc())
            .first()
        )
        assert "Encerrado automaticamente" in ultimo_log.texto
        assert "Encerrado automaticamente" in ultimo_log.texto


def test_auto_assignment_on_interaction(client, app, admin_user):
    """Testa a regra de auto-atribuição: Técnico assume, Admin NÃO assume."""
    from App.Modulos.Autenticacao.modelo import Usuario

    with app.app_context():
        cliente = Cliente(
            nome_razao="Interaction Corp", cpf_cnpj="789", created_by=admin_user.id
        )
        db.session.add(cliente)

        # Criar um técnico comum (Operador)
        tecnico = Usuario(username="tec_test", email="tec@test.com", role="Operador")
        tecnico.set_password("123456")
        db.session.add(tecnico)
        db.session.flush()
        tecnico_id = tecnico.id

        # Criar chamado SEM técnico
        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Ticket sem Dono",
            descricao="Ninguém pegou ainda",
            status="Aberto",
            tecnico_id=None,
            created_by=1,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

    # 1. Testar com ADMIN: NÃO deve assumir
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )
    client.post(
        url_for("chamados.detalhe", id=chamado_id),
        data={"texto": "Nota de supervisor (Admin)", "novo_status": ""},
        follow_redirects=True,
    )

    with app.app_context():
        ch = db.session.get(Chamado, chamado_id)
        assert ch.tecnico_id is None, "Admin não deveria assumir o chamado!"

    # 2. Testar com TÉCNICO: DEVE assumir
    client.get(url_for("auth.logout"), follow_redirects=True)
    client.post(
        url_for("auth.login"), data={"username": "tec_test", "password": "123456"}
    )
    client.post(
        url_for("chamados.detalhe", id=chamado_id),
        data={"texto": "Vou resolver isso agora (Técnico)", "novo_status": ""},
        follow_redirects=True,
    )

    with app.app_context():
        db.session.expire_all()
        ch = db.session.get(Chamado, chamado_id)
        assert ch.tecnico_id == tecnico_id, "Técnico comum deveria assumir o chamado!"
