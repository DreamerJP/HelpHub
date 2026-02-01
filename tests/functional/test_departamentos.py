from flask import url_for
from App.Modulos.Departamentos.modelo import Departamento
from App.banco import db


def test_lista_departamentos_vazia(client, admin_user):
    """Verifica se a listagem de departamentos funciona quando nao ha registros."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(url_for("departamentos.lista"))
    assert response.status_code == 200
    assert b"Departamentos" in response.data or b"departamentos" in response.data


def test_lista_departamentos_com_dados(client, admin_user):
    """Verifica se a listagem exibe departamentos cadastrados."""
    # Criar departamentos de teste
    dept1 = Departamento(
        nome="TI - Tecnologia da Informacao",
        email_notificacao="ti@empresa.com",
        descricao="Departamento de TI",
        ativo=True,
        created_by=admin_user.id,
    )
    dept2 = Departamento(
        nome="Financeiro",
        email_notificacao="financeiro@empresa.com",
        descricao="Departamento Financeiro",
        ativo=True,
        created_by=admin_user.id,
    )
    dept1.save()
    dept2.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(url_for("departamentos.lista"))
    assert response.status_code == 200
    assert b"TI - Tecnologia da Informacao" in response.data
    assert b"Financeiro" in response.data
    assert b"ti@empresa.com" in response.data
    assert b"financeiro@empresa.com" in response.data


def test_criar_departamento_sucesso(client, admin_user):
    """Verifica se a criacao de departamento funciona corretamente."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # GET na pagina de novo departamento
    response = client.get(url_for("departamentos.novo"))
    assert response.status_code == 200
    assert b"Novo Departamento" in response.data

    # POST para criar departamento
    response = client.post(
        url_for("departamentos.novo"),
        data={
            "nome": "RH - Recursos Humanos",
            "email_notificacao": "rh@empresa.com",
            "descricao": "Gestao de pessoas e beneficios",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Departamento criado com sucesso!" in response.data

    # Verificar no banco de dados
    with client.application.app_context():
        dept = Departamento.query.filter_by(nome="RH - Recursos Humanos").first()
        assert dept is not None
        assert dept.email_notificacao == "rh@empresa.com"
        assert dept.descricao == "Gestao de pessoas e beneficios"
        assert dept.ativo is True


def test_criar_departamento_sem_email(client, admin_user):
    """Verifica se e possivel criar departamento sem email de notificacao."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.post(
        url_for("departamentos.novo"),
        data={
            "nome": "Comercial",
            "email_notificacao": "",
            "descricao": "Vendas e atendimento",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Departamento criado com sucesso!" in response.data

    with client.application.app_context():
        dept = Departamento.query.filter_by(nome="Comercial").first()
        assert dept is not None
        assert dept.email_notificacao is None or dept.email_notificacao == ""


def test_criar_departamento_sem_nome(client, admin_user):
    """Verifica validacao quando tenta criar departamento sem nome."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.post(
        url_for("departamentos.novo"),
        data={
            "nome": "",
            "email_notificacao": "teste@empresa.com",
            "descricao": "Teste sem nome",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    # Deve retornar erro de validacao
    assert response.status_code == 200
    # O formulario deve reaparecer ou mostrar erro
    with client.application.app_context():
        dept_count = Departamento.query.count()
        assert dept_count == 0  # Nao deve ter criado


def test_editar_departamento_sucesso(client, admin_user):
    """Verifica se a edicao de departamento funciona corretamente."""
    # Criar departamento para editar
    dept = Departamento(
        nome="Marketing Original",
        email_notificacao="marketing@empresa.com",
        descricao="Descricao original",
        ativo=True,
        created_by=admin_user.id,
    )
    dept.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # GET na pagina de edicao
    response = client.get(url_for("departamentos.editar", id=dept.id))
    assert response.status_code == 200
    assert b"Editar Departamento" in response.data
    assert b"Marketing Original" in response.data

    # POST para atualizar
    response = client.post(
        url_for("departamentos.editar", id=dept.id),
        data={
            "nome": "Marketing e Comunicacao",
            "email_notificacao": "mkt@empresa.com",
            "descricao": "Marketing, branding e comunicacao interna",
            "ativo": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Departamento atualizado!" in response.data

    # Verificar alteracoes no banco
    with client.application.app_context():
        dept_editado = db.session.get(Departamento, dept.id)
        assert dept_editado.nome == "Marketing e Comunicacao"
        assert dept_editado.email_notificacao == "mkt@empresa.com"
        assert dept_editado.descricao == "Marketing, branding e comunicacao interna"


def test_editar_departamento_desativar(client, admin_user):
    """Verifica se e possivel desativar um departamento."""
    dept = Departamento(
        nome="Departamento Inativo",
        email_notificacao="inativo@empresa.com",
        ativo=True,
        created_by=admin_user.id,
    )
    dept.save()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Editar e desativar (nao enviar 'ativo' no POST desativa checkbox)
    response = client.post(
        url_for("departamentos.editar", id=dept.id),
        data={
            "nome": "Departamento Inativo",
            "email_notificacao": "inativo@empresa.com",
            "descricao": "Teste de desativacao",
            # 'ativo' nao enviado = False
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with client.application.app_context():
        dept_editado = db.session.get(Departamento, dept.id)
        assert dept_editado.ativo is False


def test_excluir_departamento(client, admin_user):
    """Verifica se a exclusao de departamento funciona."""
    dept = Departamento(
        nome="Departamento Para Excluir",
        email_notificacao="excluir@empresa.com",
        created_by=admin_user.id,
    )
    dept.save()
    dept_id = dept.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(
        url_for("departamentos.excluir", id=dept_id), follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Departamento removido." in response.data

    # Verificar se foi excluido do banco
    with client.application.app_context():
        dept_excluido = db.session.get(Departamento, dept_id)
        assert dept_excluido is None


def test_editar_departamento_inexistente(client, admin_user):
    """Verifica comportamento ao tentar editar departamento que nao existe."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(url_for("departamentos.editar", id=9999))
    # Deve retornar 404
    assert response.status_code == 404


def test_excluir_departamento_inexistente(client, admin_user):
    """Verifica comportamento ao tentar excluir departamento que nao existe."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    response = client.get(url_for("departamentos.excluir", id=9999))
    # Deve retornar 404
    assert response.status_code == 404
