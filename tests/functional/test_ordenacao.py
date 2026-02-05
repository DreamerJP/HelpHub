from flask import url_for
from App.Modulos.Clientes.modelo import Cliente


def test_ordenacao_clientes_nome(client, admin_user):
    """Verifica se a ordenação por nome funciona via URL."""
    # Setup: Criar clientes com nomes específicos
    c1 = Cliente(nome_razao="Zezinho", cpf_cnpj="1", created_by=admin_user.id)
    c2 = Cliente(nome_razao="Aninha", cpf_cnpj="2", created_by=admin_user.id)
    c1.save()
    c2.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # 1. Testar Ascendente (A -> Z)
    response = client.get(url_for("clientes.lista", sort="nome_razao", order="asc"))
    html = response.data.decode()
    pos_aninha = html.find("Aninha")
    pos_zezinho = html.find("Zezinho")
    assert pos_aninha < pos_zezinho, "Aninha deveria vir antes de Zezinho na ordem ASC"

    # 2. Testar Descendente (Z -> A)
    response = client.get(url_for("clientes.lista", sort="nome_razao", order="desc"))
    html = response.data.decode()
    pos_aninha = html.find("Aninha")
    pos_zezinho = html.find("Zezinho")
    assert pos_zezinho < pos_aninha, "Zezinho deveria vir antes de Aninha na ordem DESC"


def test_ordenacao_case_insensitive(client, admin_user):
    """Verifica se a ordenação ignora maiúsculas e minúsculas (Problema do 'das Neves')."""
    c1 = Cliente(nome_razao="Yasmin", cpf_cnpj="3", created_by=admin_user.id)
    c2 = Cliente(nome_razao="das Neves", cpf_cnpj="4", created_by=admin_user.id)
    c1.save()
    c2.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Na ordem Descendente, 'Yasmin' (Y) deve vir antes de 'das Neves' (d/D)
    response = client.get(url_for("clientes.lista", sort="nome_razao", order="desc"))
    html = response.data.decode()
    pos_yasmin = html.find("Yasmin")
    pos_das_neves = html.find("das Neves")
    assert pos_yasmin < pos_das_neves, (
        "Yasmin (Y) deveria vir antes de das Neves (d) na ordem DESC"
    )
