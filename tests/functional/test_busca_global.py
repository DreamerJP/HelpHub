from flask import url_for
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado
from App.Modulos.Agenda.modelo import Agendamento
from App.banco import db
from datetime import datetime, timedelta


def test_busca_global_por_nome_cliente(client, app, admin_user):
    """Testa se a busca global encontra cliente, seus chamados e agendamentos pelo nome."""

    with app.app_context():
        # Setup data
        cliente = Cliente(
            nome_razao="Bruno das Neves Teste",
            cpf_cnpj="999.888.777-66",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Instalação de Fibra",
            descricao="Nova instalação",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.flush()

        agendamento = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=datetime.now() + timedelta(days=1),
            data_fim=datetime.now() + timedelta(days=1, hours=2),
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        protocolo = chamado.protocolo

    # Login
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # 1. Busca pelo nome do cliente
    response = client.get(url_for("layout.buscar", q="Bruno das Neves"))
    assert response.status_code == 200

    # Verifica se encontrou o cliente
    assert b"Bruno das Neves Teste" in response.data
    # Verifica se encontrou o chamado (nossa nova melhoria!)
    assert protocolo.encode() in response.data
    assert b"Instala\xc3\xa7\xc3\xa3o de Fibra" in response.data
    # Verifica se encontrou o agendamento
    assert b"Agendamentos Encontrados (1)" in response.data


def test_busca_global_por_protocolo(client, app, admin_user):
    """Testa se a busca global encontra o chamado e agendamento pelo protocolo."""

    with app.app_context():
        # Setup data
        cliente = Cliente(
            nome_razao="Maria Silva Busca",
            cpf_cnpj="111.222.333-44",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Troca de Roteador",
            descricao="Roteador queimado",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.flush()

        agendamento = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=datetime.now() + timedelta(days=2),
            data_fim=datetime.now() + timedelta(days=2, hours=1),
            created_by=admin_user.id,
        )
        db.session.add(agendamento)
        db.session.commit()
        protocolo = chamado.protocolo

    # Login
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Busca pelo protocolo
    response = client.get(url_for("layout.buscar", q=protocolo))
    assert response.status_code == 200

    assert protocolo.encode() in response.data
    assert b"Troca de Roteador" in response.data
    assert b"Agendamentos Encontrados (1)" in response.data


def test_busca_global_sem_resultados(client, app, admin_user):
    """Testa a busca global com um termo que não existe."""

    # Login
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(url_for("layout.buscar", q="TermoInexistenteXYZ"))
    assert response.status_code == 200

    assert b"Nenhum cliente." in response.data
    assert b"Nenhum chamado." in response.data
    assert b"Nenhum agendamento encontrado." in response.data
