"""
Testes funcionais de rotas/controllers do módulo Chamados.
Testes de UI, formulários, renderização e interações com usuário.
"""

from flask import url_for
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado
from App.Modulos.Autenticacao.modelo import Usuario
from App.banco import db
import arrow


# ============================================================================
# CRUD - Criação, Leitura, Edição, Exclusão
# ============================================================================


def test_create_chamado(client, app, admin_user):
    """Test creating a ticket via UI."""
    # Setup dependencies
    cliente = Cliente(
        nome_razao="Mega Corp",
        cpf_cnpj="99988877000199",
        email="mega@corp.com",
        created_by=admin_user.id,
    )
    db.session.add(cliente)

    # Seed Department
    from App.Modulos.Departamentos.modelo import Departamento

    dept = Departamento(
        nome="IT Support", descricao="Tech stuff", created_by=admin_user.id
    )
    db.session.add(dept)

    db.session.commit()
    cliente_id = cliente.id
    dept_id = dept.id

    # Login
    response = client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )
    assert b"Sair" in response.data

    # Access Creation Page
    response = client.get(url_for("chamados.novo"))
    assert response.status_code == 200

    # Submit Form
    response = client.post(
        url_for("chamados.novo"),
        data={
            "cliente_id": cliente_id,
            "assunto": "Server Crash",
            "descricao": "All systems down",
            "prioridade": "Alta",
            "departamento_id": dept_id,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        chamado = Chamado.query.filter_by(assunto="Server Crash").first()
        assert chamado is not None
        assert chamado.status == "Aberto"


def test_create_chamado_validation_error(client, app, admin_user):
    """Test that creating a ticket without client fails validation."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # Submit Form without selecting client (empty string)
    response = client.post(
        url_for("chamados.novo"),
        data={
            "cliente_id": "",
            "assunto": "No Client Test",
            "descricao": "This should fail",
            "prioridade": "Normal",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # Should stay on the same page with validation errors
    assert b"Novo Chamado" in response.data

    with app.app_context():
        chamado = Chamado.query.filter_by(assunto="No Client Test").first()
        assert chamado is None


def test_excluir_chamado_como_admin(client, app, admin_user):
    """Testa que admin pode excluir chamado."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Delete Test Corp",
            cpf_cnpj="delete123",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Para Excluir",
            descricao="Este será excluído",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id
        protocolo = chamado.protocolo

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Excluir chamado
    response = client.post(
        url_for("chamados.excluir", id=chamado_id), follow_redirects=True
    )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert protocolo in html
    assert "excluído" in html.lower()

    # Verificar que foi excluído do banco
    with app.app_context():
        chamado = db.session.get(Chamado, chamado_id)
        assert chamado is None


def test_excluir_chamado_como_nao_admin(client, app, admin_user):
    """Testa que não-admin não pode excluir chamado."""
    with app.app_context():
        # Criar usuário não-admin
        operador = Usuario(
            username="operador_test", email="op@test.com", role="Operador"
        )
        operador.set_password("123456")
        db.session.add(operador)
        db.session.commit()

        cliente = Cliente(
            nome_razao="No Delete Corp", cpf_cnpj="nodelete", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.commit()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Não pode deletar",
            descricao="Test",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

    # Login como operador
    client.post(
        url_for("auth.login"),
        data={"username": "operador_test", "password": "123456"},
    )

    # Tentar excluir (deve ser bloqueado)
    response = client.post(
        url_for("chamados.excluir", id=chamado_id), follow_redirects=True
    )

    # Deve ser redirecionado ou mostrar erro 403
    assert response.status_code in [200, 403]

    # Se retornou 200, deve ter mensagem de acesso negado
    if response.status_code == 200:
        html = response.data.decode("utf-8")
        assert "acesso" in html.lower() or "permissão" in html.lower()

    # Verificar que NÃO foi excluído
    with app.app_context():
        chamado = db.session.get(Chamado, chamado_id)
        assert chamado is not None


# ============================================================================
# Listagem e Busca
# ============================================================================


def test_lista_chamados_com_busca(client, app, admin_user):
    """Testa a busca de chamados por protocolo, assunto e cliente."""
    with app.app_context():
        cliente1 = Cliente(
            nome_razao="Cliente Busca A", cpf_cnpj="111", created_by=admin_user.id
        )
        cliente2 = Cliente(
            nome_razao="Cliente Busca B", cpf_cnpj="222", created_by=admin_user.id
        )
        db.session.add(cliente1)
        db.session.add(cliente2)
        db.session.flush()

        chamado1 = Chamado(
            cliente_id=cliente1.id,
            assunto="Problema de Rede",
            descricao="Internet lenta",
            prioridade="Alta",
            created_by=admin_user.id,
        )
        chamado1.gerar_protocolo()

        chamado2 = Chamado(
            cliente_id=cliente2.id,
            assunto="Erro no Sistema",
            descricao="Sistema travando",
            prioridade="Normal",
            created_by=admin_user.id,
        )
        chamado2.gerar_protocolo()

        db.session.add(chamado1)
        db.session.add(chamado2)
        db.session.commit()

        protocolo1 = chamado1.protocolo

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Busca por assunto
    response = client.get(url_for("chamados.lista", q="Rede"))
    assert b"Problema de Rede" in response.data
    assert b"Erro no Sistema" not in response.data

    # Busca por protocolo
    response = client.get(url_for("chamados.lista", q=protocolo1))
    assert b"Problema de Rede" in response.data

    # Busca por nome do cliente
    response = client.get(url_for("chamados.lista", q="Cliente Busca A"))
    assert b"Problema de Rede" in response.data
    assert b"Erro no Sistema" not in response.data


def test_lista_chamados_paginacao(client, app, admin_user):
    """Testa a paginacao da lista de chamados."""
    with app.app_context():
        cliente = Cliente(
            nome_razao="Cliente Paginacao", cpf_cnpj="999", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.flush()

        # Criar 25 chamados para forcar paginacao (20 por pagina)
        for i in range(25):
            chamado = Chamado(
                cliente_id=cliente.id,
                assunto=f"Chamado Teste {i + 1}",
                descricao=f"Descricao do chamado {i + 1}",
                prioridade="Normal",
                created_by=admin_user.id,
            )
            chamado.gerar_protocolo()
            db.session.add(chamado)

        db.session.commit()

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Primeira pagina
    response = client.get(url_for("chamados.lista", page=1))
    assert response.status_code == 200
    assert b"Chamado Teste" in response.data

    # Segunda pagina
    response = client.get(url_for("chamados.lista", page=2))
    assert response.status_code == 200


# ============================================================================
# Andamentos e Interações
# ============================================================================


def test_adicionar_andamento_com_anexo(client, app, admin_user):
    """Testa adicionar andamento com anexo de arquivo."""
    from App.Modulos.Chamados.modelo import Andamento
    import io

    with app.app_context():
        cliente = Cliente(
            nome_razao="Cliente Anexo", cpf_cnpj="888", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado com Anexo",
            descricao="Teste de upload",
            prioridade="Normal",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Adicionar andamento com anexo
    data = {
        "texto": "Segue o arquivo solicitado",
        "novo_status": "",
        "anexo": (io.BytesIO(b"conteudo do arquivo de teste"), "documento.txt"),
    }

    response = client.post(
        url_for("chamados.detalhe", id=chamado_id),
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Interação registrada com sucesso.".encode("utf-8") in response.data

    # Verificar se o andamento foi criado com anexo
    with app.app_context():
        andamento = (
            Andamento.query.filter_by(chamado_id=chamado_id)
            .filter(Andamento.anexo.isnot(None))
            .first()
        )
        assert andamento is not None
        assert andamento.anexo is not None
        assert "Clientes/" in andamento.anexo


def test_adicionar_andamento_anexo_invalido(client, app, admin_user):
    """Testa tratamento de erro ao tentar anexar arquivo invalido."""
    import io

    with app.app_context():
        cliente = Cliente(
            nome_razao="Cliente Erro Upload",
            cpf_cnpj="777",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado Erro Upload",
            descricao="Teste de erro",
            prioridade="Normal",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar anexar arquivo vazio (pode causar erro no UploadManager)
    data = {
        "texto": "Tentando anexar arquivo vazio",
        "novo_status": "",
        "anexo": (io.BytesIO(b""), "vazio.bin"),
    }

    response = client.post(
        url_for("chamados.detalhe", id=chamado_id),
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    # Deve redirecionar, pode ter mensagem de erro
    assert response.status_code == 200


def test_retratar_andamento_inexistente_redirect(client, app, admin_user):
    """Testa que retratação de andamento inexistente redireciona corretamente."""
    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar retratar andamento que não existe
    response = client.post(
        url_for("chamados.retratar_andamento", id="id-invalido"),
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Deve redirecionar para lista de chamados
    html = response.data.decode("utf-8")
    # Verifica se está na lista ou mostra erro
    assert "chamado" in html.lower() or "não encontrado" in html.lower()


def test_download_anexo(client, app, admin_user):
    """Testa o download de anexo de chamado."""
    from App.Modulos.Chamados.modelo import Andamento
    import os

    with app.app_context():
        cliente = Cliente(
            nome_razao="Cliente Download", cpf_cnpj="333", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado Download",
            descricao="Teste de download",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.flush()

        # Criar um caminho de anexo fake (em ambiente de teste)
        caminho_anexo = f"Clientes/{cliente.id}/2026/teste_download.txt"

        andamento = Andamento(
            chamado_id=chamado.id,
            usuario_id=admin_user.id,
            texto="Andamento com anexo para download",
            tipo="Resposta",
            anexo=caminho_anexo,
            created_by=admin_user.id,
        )
        db.session.add(andamento)
        db.session.commit()

        # Criar arquivo fisico no diretorio de uploads do teste
        upload_folder = client.application.config["UPLOAD_FOLDER"]
        full_path = os.path.join(upload_folder, caminho_anexo)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w") as f:
            f.write("Conteudo do arquivo de teste para download")

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar fazer download
    response = client.get(url_for("chamados.baixar_anexo", filename=caminho_anexo))

    assert response.status_code == 200
    assert b"Conteudo do arquivo de teste para download" in response.data


# ============================================================================
# Agendamento de Visitas
# ============================================================================


def test_atualizar_visita_instrucoes(client, app, admin_user):
    """Test updating technical instructions of an appointment."""
    from App.Modulos.Agenda.modelo import Agendamento
    from datetime import datetime, timedelta

    with app.app_context():
        # Setup: Cliente, Chamado e Agendamento
        cliente = Cliente(
            nome_razao="Base Corp", cpf_cnpj="1", created_by=admin_user.id
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Old Task",
            descricao="Work to be done",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.flush()

        visita = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=datetime.now(),
            data_fim=datetime.now() + timedelta(hours=1),
            instrucoes_tecnicas="Initial instructions",
            created_by=admin_user.id,
        )
        db.session.add(visita)
        db.session.commit()
        visita_id = visita.id

    # Login
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # Update instructions and required fields
    inicio = datetime.now().strftime("%Y-%m-%dT%H:%M")
    fim = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    
    response = client.post(
        url_for("chamados.atualizar_visita", id=visita_id),
        data={
            "tecnico_id": admin_user.id,
            "data_inicio": inicio,
            "data_fim": fim,
            "instrucoes_tecnicas": "Updated and improved instructions"
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Agendamento t\xc3\xa9cnico atualizado com sucesso!" in response.data

    with app.app_context():
        v = db.session.get(Agendamento, visita_id)
        assert v.instrucoes_tecnicas == "Updated and improved instructions"


def test_mudar_status_para_agendado(client, app, admin_user):
    """Testa mudanca de status para Agendado e criacao de visita."""
    from App.Modulos.Agenda.modelo import Agendamento
    from datetime import datetime, timedelta

    with app.app_context():
        cliente = Cliente(
            nome_razao="Cliente Agendamento",
            cpf_cnpj="666",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.flush()

        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado Para Agendar",
            descricao="Precisa de visita tecnica",
            prioridade="Alta",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Agendar visita
    inicio = (datetime.now() + timedelta(days=1)).isoformat()
    fim = (datetime.now() + timedelta(days=1, hours=2)).isoformat()

    data = {
        "texto": "Agendando visita tecnica",
        "novo_status": "Agendado",
        "data_inicio": inicio,
        "data_fim": fim,
        "instrucoes_tecnicas": "Levar equipamento de teste",
    }

    response = client.post(
        url_for("chamados.detalhe", id=chamado_id),
        data=data,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Interação registrada com sucesso.".encode("utf-8") in response.data

    # Verificar se agendamento foi criado
    with app.app_context():
        ch = db.session.get(Chamado, chamado_id)
        assert ch.status == "Agendado"

        visita = Agendamento.query.filter_by(chamado_id=chamado_id).first()
        assert visita is not None
        assert visita.instrucoes_tecnicas == "Levar equipamento de teste"

def test_agendamento_rapido_com_selecao_tecnico(client, app, admin_user):
    """Garante que a seleção de técnico no agendamento rápido funciona corretamente."""
    from App.Modulos.Agenda.modelo import Agendamento
    
    with app.app_context():
        # Setup: Criar um segundo técnico
        tecnico_dois = Usuario(username="tecnico_dois", email="t2@test.com", role="Operador")
        tecnico_dois.set_password("123456")
        db.session.add(tecnico_dois)
        
        cliente = Cliente(nome_razao="Quick Test", cpf_cnpj="123", created_by=admin_user.id)
        db.session.add(cliente)
        db.session.commit()
        
        chamado = Chamado(
            cliente_id=cliente.id, 
            assunto="Teste Agendamento", 
            descricao="Descrição obrigatória para o teste",
            created_by=admin_user.id
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        
        chamado_id = chamado.id
        tecnico_id = tecnico_dois.id

    # Login como Admin
    client.post(url_for("auth.login"), data={"username": "admin_test", "password": "123456"})

    # Simular Agendamento Rápido escolhendo o Técnico Dois
    inicio = arrow.now().shift(days=1).format("YYYY-MM-DDTHH:mm")
    fim = arrow.now().shift(days=1, hours=2).format("YYYY-MM-DDTHH:mm")
    
    response = client.post(
        url_for("chamados.detalhe", id=chamado_id),
        data={
            "texto": "Visita agendada para outro técnico",
            "novo_status": "Agendado",
            "tecnico_id": tecnico_id,
            "data_inicio": inicio,
            "data_fim": fim
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    
    # Validar se o técnico correto foi salvo no agendamento
    with app.app_context():
        visita = Agendamento.query.filter_by(chamado_id=chamado_id).first()
        assert visita is not None
        assert visita.tecnico_id == tecnico_id
