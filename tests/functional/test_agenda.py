from flask import url_for
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado, Andamento
from App.Modulos.Agenda.modelo import Agendamento
from App.banco import db
import arrow


def test_agenda_fluxo_completo(client, app, admin_user):
    """Testa o fluxo completo da agenda: Agendar -> Reagendar -> Finalizar."""

    # 1. Setup Data
    with app.app_context():
        cliente = Cliente(
            nome_razao="Agenda Test Corp",
            cpf_cnpj="11122233000199",
            email="agenda@test.com",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Visita Técnica de Teste",
            descricao="Problema na rede",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        chamado_id = chamado.id

    # 2. Login
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # 3. Testar Página da Agenda
    response = client.get(url_for("agenda.calendario"))
    assert response.status_code == 200

    # 4. Testar Criar Agendamento (POST)
    inicio = (
        arrow.now().shift(days=1).replace(hour=10, minute=0, second=0, microsecond=0)
    )
    fim = inicio.shift(hours=2)

    response = client.post(
        url_for("agenda.agendar"),
        data={
            "chamado_id": chamado_id,
            "data_inicio": inicio.format("YYYY-MM-DDTHH:mm"),
            "data_fim": fim.format("YYYY-MM-DDTHH:mm"),
        },
        follow_redirects=True,
    )
    assert "agendada com sucesso" in response.data.decode("utf-8")

    # Capturar agendamento_id
    with app.app_context():
        ag = Agendamento.query.filter_by(chamado_id=chamado_id).first()
        assert ag is not None
        agendamento_id = ag.id

    # 5. Testar API de Eventos
    response = client.get(url_for("agenda.api_eventos"))
    assert response.status_code == 200
    json_data = response.get_json()
    assert any(e["id"] == agendamento_id for e in json_data)

    # 6. Testar Reagendamento (Drag & Drop API)
    novo_inicio = inicio.shift(days=1)
    novo_fim = novo_inicio.shift(hours=1)

    response = client.post(
        url_for("agenda.api_reagendar", id=agendamento_id),
        json={
            "start": novo_inicio.format("YYYY-MM-DDTHH:mm:ss"),
            "end": novo_fim.format("YYYY-MM-DDTHH:mm:ss"),
        },
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    # 7. Testar Bloqueio de Duplicata
    response = client.post(
        url_for("agenda.agendar"),
        data={
            "chamado_id": chamado_id,
            "data_inicio": novo_inicio.shift(days=2).format("YYYY-MM-DDTHH:mm"),
            "data_fim": novo_fim.shift(days=2).format("YYYY-MM-DDTHH:mm"),
        },
        follow_redirects=True,
    )
    assert "possui um agendamento ativo" in response.data.decode("utf-8")

    # 8. Testar Finalização
    response = client.post(
        url_for("agenda.finalizar_visita", id=agendamento_id),
        data={"relatorio": "Serviço realizado com sucesso."},
        follow_redirects=True,
    )
    assert response.status_code == 200

    # Validar Estados Finais
    with app.app_context():
        a = db.session.get(Agendamento, agendamento_id)
        assert a.status == "Realizado"

        c = db.session.get(Chamado, chamado_id)
        assert c.status == "Fechado"

    # 9. Testar Bloqueio de Reagendamento de visita finalizada
    response = client.post(
        url_for("agenda.api_reagendar", id=agendamento_id),
        json={
            "start": arrow.now().format("YYYY-MM-DDTHH:mm:ss"),
            "end": arrow.now().shift(hours=1).format("YYYY-MM-DDTHH:mm:ss"),
        },
    )
    assert response.status_code == 400
    json_result = response.get_json()
    assert "status: Realizado" in json_result["message"]


def test_agenda_cancelamento(client, app, admin_user):
    """Testa o fluxo de anular um agendamento e verificar o status do chamado."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Cancel Corp", cpf_cnpj="777", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        # Chamado Agendado
        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Teste Cancelar",
            descricao="Vai ser cancelado",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

        # Agendamento
        agendamento = Agendamento(
            chamado_id=chamado_id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        agendamento_id = agendamento.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Executar Anulação
    response = client.post(
        url_for("agenda.api_cancelar", id=agendamento_id), follow_redirects=True
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    # Verificar banco
    with app.app_context():
        # Visita deve estar Cancelada
        ag = db.session.get(Agendamento, agendamento_id)
        assert ag.status == "Cancelado"

        # Chamado deve ter voltado para Aberto (pois era o único agendamento)
        ch = db.session.get(Chamado, chamado_id)
        assert ch.status == "Aberto"

        # Verificar Log
        log = (
            Andamento.query.filter_by(chamado_id=chamado_id)
            .order_by(Andamento.created_at.desc())
            .first()
        )
        assert "anulado manualmente" in log.texto


def test_agenda_troca_tecnico(client, app, admin_user):
    """Testa reagendamento com troca de técnico (Drag & Drop entre colunas)."""
    from App.Modulos.Autenticacao.modelo import Usuario

    with app.app_context():
        # Criar outro técnico
        tec2 = Usuario(username="tecnico_dois", email="t2@test.com", role="Operador")
        tec2.set_password("123456")
        db.session.add(tec2)
        db.session.commit()
        tec2_id = tec2.id

        cliente = Cliente(
            nome_razao="Troca Tec Corp", cpf_cnpj="555", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        # Chamado e Agendamento para Admin
        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Troca Tecnico",
            descricao="Test",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

        ag = Agendamento(
            chamado_id=chamado_id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            created_by=admin_user.id,
        )
        db.session.add(ag)
        db.session.commit()
        ag_id = ag.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Reagendar trocando para tecnico 2
    nova_ini = arrow.now().shift(days=2)
    nova_fim = nova_ini.shift(hours=1)

    response = client.post(
        url_for("agenda.api_reagendar", id=ag_id),
        json={
            "start": nova_ini.format("YYYY-MM-DDTHH:mm:ss"),
            "end": nova_fim.format("YYYY-MM-DDTHH:mm:ss"),
            "resourceId": tec2_id,  # Aqui acontece a mágica
        },
    )
    assert response.status_code == 200

    # Validar
    with app.app_context():
        ag_banco = db.session.get(Agendamento, ag_id)
        assert ag_banco.tecnico_id == tec2_id  # Trocou de dono?

        # Log deve mencionar a troca
        log = (
            Andamento.query.filter_by(chamado_id=chamado_id)
            .order_by(Andamento.created_at.desc())
            .first()
        )
        assert "Técnico alterado para: tecnico_dois" in log.texto


def test_agenda_gerar_os(client, app, admin_user):
    """Testa a geração de Ordem de Serviço (OS) para impressão."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="OS Test Corp",
            cpf_cnpj="12345678901",
            logradouro="Rua Teste",
            numero="123",
            bairro="Centro",
            cidade="Test City",
            uf="TS",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Instalar Fibra Óptica",
            descricao="Instalação de 100MB",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id
        protocolo = chamado.protocolo  # Capturar dentro do contexto

        # Criar agendamento
        agendamento = Agendamento(
            chamado_id=chamado_id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=2).datetime,
            instrucoes_tecnicas="Levar cabo de 50m",
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Testar geração de OS
    response = client.get(url_for("agenda.baixar_os", chamado_id=chamado_id))
    assert response.status_code == 200
    # Verificar se contém informações essenciais
    html = response.data.decode("utf-8")
    assert "Ordem de Serviço" in html or "OS Test Corp" in html
    assert protocolo in html


def test_agenda_validacao_dados_incompletos(client, app, admin_user):
    """Testa validação quando dados obrigatórios estão faltando."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Validation Corp", cpf_cnpj="999", created_by=admin_user.id
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
        chamado_id = chamado.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar agendar sem data_fim
    response = client.post(
        url_for("agenda.agendar"),
        data={
            "chamado_id": chamado_id,
            "data_inicio": arrow.now().shift(days=1).format("YYYY-MM-DDTHH:mm"),
            # data_fim ausente
        },
        follow_redirects=True,
    )
    assert "Dados incompletos" in response.data.decode("utf-8")


def test_agenda_validacao_relatorio_obrigatorio(client, app, admin_user):
    """Testa que o relatório é obrigatório ao finalizar visita."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Report Test Corp", cpf_cnpj="888", created_by=admin_user.id
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

        agendamento = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        ag_id = agendamento.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar finalizar sem relatório
    response = client.post(
        url_for("agenda.finalizar_visita", id=ag_id),
        data={},  # Relatório ausente
        follow_redirects=True,
    )
    assert "relatório" in response.data.decode("utf-8").lower()
    assert "obrigatório" in response.data.decode("utf-8").lower()


def test_agenda_api_eventos_com_filtros(client, app, admin_user):
    """Testa a API de eventos com filtros de data."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Filter Test Corp", cpf_cnpj="777", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Test Filter",
            descricao="Test",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar agendamento dentro do período
        data_inicio_filtro = arrow.now().shift(days=2)
        agendamento = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=data_inicio_filtro.datetime,
            data_fim=data_inicio_filtro.shift(hours=1).datetime,
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        ag_id = agendamento.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Testar API com filtros de data
    start_filter = arrow.now().shift(days=1).format("YYYY-MM-DD")
    end_filter = arrow.now().shift(days=3).format("YYYY-MM-DD")

    response = client.get(
        url_for("agenda.api_eventos", start=start_filter, end=end_filter)
    )
    assert response.status_code == 200
    eventos = response.get_json()

    # Deve incluir o agendamento criado
    assert any(e["id"] == ag_id for e in eventos)

    # Testar filtro que NÃO deve incluir o agendamento
    response2 = client.get(
        url_for(
            "agenda.api_eventos",
            start=arrow.now().shift(days=5).format("YYYY-MM-DD"),
            end=arrow.now().shift(days=6).format("YYYY-MM-DD"),
        )
    )
    eventos2 = response2.get_json()
    assert not any(e["id"] == ag_id for e in eventos2)


def test_agenda_detectar_atraso(client, app, admin_user):
    """Testa detecção de visitas atrasadas."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Delay Test Corp", cpf_cnpj="666", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Visita Atrasada",
            descricao="Test",
            status="Agendado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()

        # Criar agendamento no PASSADO (atrasado)
        agendamento = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(hours=-2).datetime,
            data_fim=arrow.now().shift(hours=-1).datetime,  # Terminou há 1 hora
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        ag_id = agendamento.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Buscar eventos via API
    response = client.get(url_for("agenda.api_eventos"))
    assert response.status_code == 200
    eventos = response.get_json()

    # Encontrar o evento atrasado
    evento_atrasado = next((e for e in eventos if e["id"] == ag_id), None)
    assert evento_atrasado is not None
    assert evento_atrasado["extendedProps"]["is_delayed"] is True
    assert evento_atrasado["extendedProps"]["status"] == "Atrasado"
    assert evento_atrasado["color"] == "#F59E0B"  # Cor laranja para atrasado


def test_agenda_conflito_horario(client, app, admin_user):
    """Testa detecção de conflito de horário ao agendar."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Conflict Corp", cpf_cnpj="555", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        # Criar dois chamados
        chamado1 = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado 1",
            descricao="Test",
            created_by=admin_user.id,
        )
        chamado1.gerar_protocolo()
        db.session.add(chamado1)

        chamado2 = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado 2",
            descricao="Test",
            created_by=admin_user.id,
        )
        chamado2.gerar_protocolo()
        db.session.add(chamado2)
        db.session.commit()

        # Agendar o primeiro
        inicio = arrow.now().shift(days=3, hours=1).replace(second=0, microsecond=0)
        fim = inicio.shift(hours=2)

        agendamento1 = Agendamento(
            chamado_id=chamado1.id,
            tecnico_id=admin_user.id,
            data_inicio=inicio.datetime,
            data_fim=fim.datetime,
            created_by=admin_user.id,
        )
        db.session.add(agendamento1)
        db.session.commit()
        chamado2_id = chamado2.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar agendar o segundo no MESMO horário (conflito)
    response = client.post(
        url_for("agenda.agendar"),
        data={
            "chamado_id": chamado2_id,
            "tecnico_id": admin_user.id,
            "data_inicio": inicio.format("YYYY-MM-DDTHH:mm"),
            "data_fim": fim.format("YYYY-MM-DDTHH:mm"),
        },
        follow_redirects=True,
    )
    assert "Conflito" in response.data.decode("utf-8")


def test_agenda_datas_invalidas(client, app, admin_user):
    """Testa validação quando data_inicio >= data_fim."""
    from App.Modulos.Chamados.servicos import ChamadoService

    with app.app_context():
        cliente = Cliente(
            nome_razao="Invalid Date Corp", cpf_cnpj="444", created_by=admin_user.id
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

        # Tentar agendar com data_fim ANTES de data_inicio
        inicio = arrow.now().shift(days=1).datetime
        fim = arrow.now().shift(hours=12).datetime  # Antes do início!

        success, msg = ChamadoService.agendar_visita(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            inicio=inicio,
            fim=fim,
            usuario_id=admin_user.id,
        )

        assert success is False
        assert "posterior" in msg.lower() or "término" in msg.lower()


def test_agenda_ocultar_cancelados(client, app, admin_user):
    """Testa que eventos cancelados não aparecem na API."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Cancelled Corp", cpf_cnpj="333", created_by=admin_user.id
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

        # Criar e cancelar agendamento
        agendamento = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=arrow.now().shift(days=1).datetime,
            data_fim=arrow.now().shift(days=1, hours=1).datetime,
            status="Cancelado",  # Já criado como cancelado
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        ag_id = agendamento.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Verificar que NÃO aparece na API
    response = client.get(url_for("agenda.api_eventos"))
    eventos = response.get_json()
    assert not any(e["id"] == ag_id for e in eventos)
