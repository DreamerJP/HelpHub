"""
Testes de Segurança de Payload e Integridade de Dados.
Verifica se as restrições de tamanho (Length) são impostas pelo servidor
mesmo que a proteção de interface (Anti-Freeze JS) seja ignorada.
"""

from flask import url_for
from App.Modulos.Clientes.modelo import Cliente


def test_payload_protection_cliente(client, admin_user):
    """Verifica se o servidor rejeita nomes de clientes excessivamente longos."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Nome com 101 caracteres (Limite no form é 100)
    nome_gigante = "A" * 101

    response = client.post(
        url_for("clientes.novo"),
        data={
            "nome_razao": nome_gigante,
            "cpf_cnpj": "12345678900",
            "email": "teste@exemplo.com",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # O cliente não deve ter sido criado
    with client.application.app_context():
        cli = Cliente.query.filter_by(nome_razao=nome_gigante).first()
        assert cli is None


def test_payload_protection_chamado(client, admin_user):
    """Verifica se o servidor rejeita assuntos de chamados muito longos."""
    # Setup Cliente
    cliente = Cliente(nome_razao="Base Corp", cpf_cnpj="1", created_by=admin_user.id)
    cliente.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Assunto com 151 caracteres (Limite no form é 150)
    assunto_gigante = "S" * 151

    response = client.post(
        url_for("chamados.novo"),
        data={
            "cliente_id": cliente.id,
            "assunto": assunto_gigante,
            "descricao": "Teste de payload",
            "prioridade": "Normal",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # O chamado não deve ter sido criado
    from App.Modulos.Chamados.modelo import Chamado

    with client.application.app_context():
        chamado = Chamado.query.filter_by(assunto=assunto_gigante).first()
        assert chamado is None


def test_payload_protection_andamento(client, admin_user):
    """Verifica se o servidor rejeita textos de andamento acima de 10.000 caracteres."""
    # Setup Chamado
    cliente = Cliente(nome_razao="Base Corp 2", cpf_cnpj="2", created_by=admin_user.id)
    cliente.save()
    from App.Modulos.Chamados.modelo import Chamado, Andamento

    chamado = Chamado(
        cliente_id=cliente.id,
        assunto="Test",
        descricao="Test",
        created_by=admin_user.id,
    )
    chamado.gerar_protocolo()
    chamado.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Texto com 10.001 caracteres (Limite no form é 10.000)
    texto_gigante = "X" * 10001

    response = client.post(
        url_for("chamados.detalhe", id=chamado.id),
        data={
            "texto": texto_gigante,
            "novo_status": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # O andamento não deve ter sido criado
    with client.application.app_context():
        andamento = Andamento.query.filter_by(texto=texto_gigante).first()
        assert andamento is None
