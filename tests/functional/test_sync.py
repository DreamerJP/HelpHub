from flask import url_for
from App.Modulos.Administracao.modelo import SyncControl
from App.Modulos.Chamados.modelo import Chamado
from App.Modulos.Clientes.modelo import Cliente


def test_sync_increment_on_ticket_save(app, admin_user):
    """Garante que a versão de chamados sobe ao criar um novo."""
    with app.app_context():
        # Inicializar o SyncControl para garantir que o registro existe
        SyncControl.incrementar("chamados")
        v_inicial = SyncControl.get_versao("chamados")

        # Criar um chamado fake
        c = Chamado(
            protocolo="SYNC-TEST-01",
            assunto="Teste de Sincronia",
            descricao="Descrição obrigatória",
            cliente_id="fake-id",
            created_by=admin_user.id,
        )
        # O save do BaseModel deve disparar o SyncControl.incrementar
        c.save()

        v_final = SyncControl.get_versao("chamados")
        assert v_final > v_inicial


def test_sync_increment_on_ticket_delete(app, admin_user):
    """Garante que a versão sobe ao excluir um chamado."""
    with app.app_context():
        SyncControl.incrementar("chamados")

        c = Chamado(
            protocolo="SYNC-TEST-02",
            assunto="Teste Delete",
            descricao="X",
            cliente_id="fake-id",
            created_by=admin_user.id,
        )
        c.save()
        v_antes_delete = SyncControl.get_versao("chamados")

        # O delete do BaseModel deve disparar o SyncControl.incrementar
        c.delete()

        v_depois_delete = SyncControl.get_versao("chamados")
        assert v_depois_delete > v_antes_delete


def test_sync_check_route(client, app, admin_user):
    """Valida se a rota de verificação está online e requer login."""
    with app.app_context():
        url = url_for("layout.sync_check")
        login_url = url_for("auth.login")

    # 1. Deslogado deve redirecionar (302 para login)
    response = client.get(url)
    assert response.status_code == 302

    # 2. Logar
    client.post(login_url, data={"username": "admin_test", "password": "123456"})

    # 3. Logado deve funcionar
    response = client.get(url)
    assert response.status_code == 200
    data = response.get_json()
    assert "chamados" in data
    assert "clientes" in data


def test_different_entities_sync(app, admin_user):
    """Garante que mudar um cliente não afeta a versão de chamados."""
    with app.app_context():
        # Garantir registros iniciais
        SyncControl.incrementar("chamados")
        SyncControl.incrementar("clientes")

        v_chamados_antes = SyncControl.get_versao("chamados")

        # Salvar um cliente
        cl = Cliente(
            nome_razao="Cliente Teste Sync", cpf_cnpj="123", created_by=admin_user.id
        )
        cl.save()

        v_clientes = SyncControl.get_versao("clientes")
        v_chamados_depois = SyncControl.get_versao("chamados")

        # O contador de clientes deve ter subido (devido ao cl.save())
        assert v_clientes > 1
        # O de chamados deve continuar o mesmo
        assert v_chamados_depois == v_chamados_antes
