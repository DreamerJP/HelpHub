from flask import url_for
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado
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
