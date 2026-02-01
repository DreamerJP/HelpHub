from flask import url_for
from App.Modulos.Clientes.modelo import Cliente, DocumentoCliente
from App.Modulos.Chamados.modelo import Chamado
from App.banco import db
import io


def test_perfil_cliente_carregamento(client, admin_user):
    """Verifica se a página de perfil carrega corretamente com as novas informações."""
    # Setup: Criar um cliente
    cliente = Cliente(
        nome_razao="Cliente Teste Perfil",
        cpf_cnpj="11122233344",
        email="perfil@teste.com",
        created_by=admin_user.id,
    )
    cliente.save()

    # Criar um chamado para este cliente
    chamado = Chamado(
        cliente_id=cliente.id,
        assunto="Chamado de Teste Perfil",
        descricao="Descrição do chamado de teste para verificar no perfil",
        prioridade="Média",
        created_by=admin_user.id,
    )
    chamado.gerar_protocolo()
    chamado.save()

    # Login
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Acessar rota de detalhe (alias da editar)
    response = client.get(url_for("clientes.editar", id=cliente.id))
    assert response.status_code == 200
    assert b"Perfil do Cliente" in response.data
    assert b"Cliente Teste Perfil" in response.data
    assert b"Chamado de Teste Perfil" in response.data
    assert "Informações".encode("utf-8") in response.data
    assert "Cadastro".encode("utf-8") in response.data


def test_edicao_cliente_no_perfil(client, admin_user):
    """Verifica se o formulário de edição dentro do perfil funciona via POST."""
    cliente = Cliente(
        nome_razao="Antes da Edicao", cpf_cnpj="99988877766", created_by=admin_user.id
    )
    cliente.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # POST para a rota de edição
    response = client.post(
        url_for("clientes.editar", id=cliente.id),
        data={
            "nome_razao": "Depois da Edicao",
            "cpf_cnpj": "99988877766",
            "nome_fantasia": "Novo Fantasia",
            "email": "novo@email.com",
            "observacoes": "Nova observacao de teste",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Dados do cliente atualizados com sucesso!" in response.data

    # Verifica no banco
    cliente_editado = db.session.get(Cliente, cliente.id)
    assert cliente_editado.nome_razao == "Depois da Edicao"
    assert cliente_editado.nome_fantasia == "Novo Fantasia"
    assert cliente_editado.observacoes == "Nova observacao de teste"


def test_upload_documento_cliente(client, admin_user):
    """Verifica se o upload de documento para o cliente funciona."""
    cliente = Cliente(
        nome_razao="Cliente Para Upload",
        cpf_cnpj="55544433322",
        created_by=admin_user.id,
    )
    cliente.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Simular um arquivo (usando .txt para evitar falha no Magic Number check do filetype com buffer vazio)
    data = {"arquivo": (io.BytesIO(b"conteudo de teste"), "notas.txt")}

    response = client.post(
        url_for("clientes.upload_documento", id=cliente.id),
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Documento anexado com sucesso!" in response.data

    # Verifica se o documento existe no banco
    with client.application.app_context():
        doc = DocumentoCliente.query.filter_by(cliente_id=cliente.id).first()
        assert doc is not None
        assert doc.nome_original == "notas.txt"
        assert f"Clientes/{cliente.id}/" in doc.caminho

    # Verifica se o documento aparece no perfil
    response = client.get(url_for("clientes.editar", id=cliente.id))
    assert b"notas.txt" in response.data


def test_lista_clientes_busca(client, admin_user):
    """Testa se a listagem e a busca de clientes estão funcionando."""
    cliente1 = Cliente(
        nome_razao="Busca Alfa", cpf_cnpj="111", created_by=admin_user.id
    )
    cliente2 = Cliente(
        nome_razao="Busca Beta", cpf_cnpj="222", created_by=admin_user.id
    )
    cliente1.save()
    cliente2.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Busca por 'Alfa'
    response = client.get(url_for("clientes.lista", q="Alfa"))
    assert b"Busca Alfa" in response.data
    assert b"Busca Beta" not in response.data

    # Verifica botão 'Detalhes'
    assert b"Detalhes" in response.data
    assert url_for("clientes.editar", id=cliente1.id) in response.data.decode()


def test_lista_clientes_busca_por_cpf_cnpj(client, admin_user):
    """Testa busca de clientes por CPF/CNPJ."""
    cliente1 = Cliente(
        nome_razao="Empresa A", cpf_cnpj="12345678901", created_by=admin_user.id
    )
    cliente2 = Cliente(
        nome_razao="Empresa B", cpf_cnpj="98765432100", created_by=admin_user.id
    )
    cliente1.save()
    cliente2.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Busca por CPF/CNPJ parcial
    response = client.get(url_for("clientes.lista", q="123456"))
    assert b"Empresa A" in response.data
    assert b"Empresa B" not in response.data


def test_lista_clientes_busca_por_nome_fantasia(client, admin_user):
    """Testa busca de clientes por nome fantasia."""
    cliente1 = Cliente(
        nome_razao="Razao Social ABC",
        nome_fantasia="Fantasia XYZ",
        cpf_cnpj="111",
        created_by=admin_user.id,
    )
    cliente2 = Cliente(
        nome_razao="Razao Social DEF",
        nome_fantasia="Fantasia QWE",
        cpf_cnpj="222",
        created_by=admin_user.id,
    )
    cliente1.save()
    cliente2.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Busca por nome fantasia
    response = client.get(url_for("clientes.lista", q="XYZ"))
    assert b"Razao Social ABC" in response.data or b"Fantasia XYZ" in response.data
    assert b"Razao Social DEF" not in response.data


def test_criar_cliente_validacao_nome_obrigatorio(client, admin_user):
    """Verifica validacao ao tentar criar cliente sem nome."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar criar sem nome_razao
    response = client.post(
        url_for("clientes.novo"),
        data={
            "nome_razao": "",
            "cpf_cnpj": "12345678900",
            "email": "teste@exemplo.com",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # Nao deve ter criado o cliente
    with client.application.app_context():
        count = Cliente.query.count()
        assert count == 0


def test_upload_documento_sem_arquivo(client, admin_user):
    """Verifica comportamento ao tentar fazer upload sem arquivo."""
    cliente = Cliente(
        nome_razao="Cliente Upload Vazio",
        cpf_cnpj="77788899900",
        created_by=admin_user.id,
    )
    cliente.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # POST sem arquivo
    response = client.post(
        url_for("clientes.upload_documento", id=cliente.id),
        data={},
        follow_redirects=True,
    )

    # Deve redirecionar sem erro critico
    assert response.status_code == 200

    # Nao deve ter criado documento
    with client.application.app_context():
        doc_count = DocumentoCliente.query.filter_by(cliente_id=cliente.id).count()
        assert doc_count == 0


def test_excluir_documento_cliente(client, admin_user):
    """Verifica se a exclusao de documento do cliente funciona."""
    cliente = Cliente(
        nome_razao="Cliente Exclusao Doc",
        cpf_cnpj="44455566677",
        created_by=admin_user.id,
    )
    cliente.save()

    # Criar documento
    doc = DocumentoCliente(
        cliente_id=cliente.id,
        nome_original="contrato.pdf",
        caminho=f"Clientes/{cliente.id}/2026/contrato.pdf",
        tipo="application/pdf",
        created_by=admin_user.id,
    )
    doc.save()
    doc_id = doc.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(
        url_for("clientes.excluir_documento", id=doc_id), follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Documento removido." in response.data

    # Verificar se foi excluido
    with client.application.app_context():
        doc_excluido = db.session.get(DocumentoCliente, doc_id)
        assert doc_excluido is None


def test_excluir_cliente(client, admin_user):
    """Verifica se a exclusao de cliente funciona."""
    cliente = Cliente(
        nome_razao="Cliente Para Excluir",
        cpf_cnpj="88899900011",
        created_by=admin_user.id,
    )
    cliente.save()
    cliente_id = cliente.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(
        url_for("clientes.excluir", id=cliente_id), follow_redirects=True
    )

    assert response.status_code == 200
    assert (
        "Cliente excluído.".encode("utf-8") in response.data
        or b"Cliente excluido." in response.data
    )

    # Verificar se foi excluido do banco
    with client.application.app_context():
        cliente_excluido = db.session.get(Cliente, cliente_id)
        assert cliente_excluido is None


def test_criar_cliente_sucesso(client, admin_user):
    """Verifica se a criacao de cliente funciona corretamente."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.post(
        url_for("clientes.novo"),
        data={
            "nome_razao": "Novo Cliente Ltda",
            "nome_fantasia": "NovoCliente",
            "cpf_cnpj": "12345678000199",
            "email": "contato@novocliente.com",
            "telefone": "(11) 98765-4321",
            "observacoes": "Cliente criado em teste",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Cliente cadastrado com sucesso!" in response.data

    # Verificar no banco
    with client.application.app_context():
        cliente = Cliente.query.filter_by(nome_razao="Novo Cliente Ltda").first()
        assert cliente is not None
        assert cliente.nome_fantasia == "NovoCliente"
        assert cliente.email == "contato@novocliente.com"
        assert cliente.ativo is True
