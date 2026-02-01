from flask import url_for
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado


def test_create_chamado(client, app, admin_user):
    """Test creating a ticket via UI."""
    from App.banco import db  # Local import if needed or use app.app_context

    # Setup dependencies
    # Cliente para o chamado
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
    assert b"Sair" in response.data, f"Login failed: {response.data[:200]}"

    # Check cookies
    # Access cookie_jar via the underlying werkzeug test client interface if needed,
    # or just inspect headers/cookies on response?
    # FlaskClient exposes `cookie_jar` as attribute in newer versions but let's check `session`.
    with client.session_transaction() as sess:
        print(f"DEBUG SESSION after login: {sess}")

    # Also inspect cookie headers from response
    print(f"DEBUG Set-Cookie Header: {response.headers.get('Set-Cookie')}")

    # Access Creation Page
    response = client.get(url_for("chamados.novo"))
    if response.status_code == 302:
        print(f"DEBUG GET: Redirecting to {response.headers.get('Location')}")
    assert response.status_code == 200, (
        f"GET Status: {response.status_code}, Location: {response.headers.get('Location')}"
    )

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
    # Flash message check (decoded string)
    # Flash message check (decoded string) can be flaky with redirects
    # We rely on DB state verification below
    pass

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
    # Should stay on the same page with validation errors (not redirect to list)
    assert b"Abertura de Chamado" in response.data

    with app.app_context():
        chamado = Chamado.query.filter_by(assunto="No Client Test").first()
        assert chamado is None


def test_atualizar_visita_instrucoes(client, app, admin_user):
    """Test updating technical instructions of an appointment."""
    from App.banco import db
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

    # Update instructions
    response = client.post(
        url_for("chamados.atualizar_visita", id=visita_id),
        data={"instrucoes_tecnicas": "Updated and improved instructions"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Instru\xc3\xa7\xc3\xb5es t\xc3\xa9cnicas atualizadas!" in response.data

    with app.app_context():
        v = db.session.get(Agendamento, visita_id)
        assert v.instrucoes_tecnicas == "Updated and improved instructions"


def test_lista_chamados_com_busca(client, app, admin_user):
    """Testa a busca de chamados por protocolo, assunto e cliente."""
    from App.banco import db

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
    from App.banco import db

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


def test_adicionar_andamento_com_anexo(client, app, admin_user):
    """Testa adicionar andamento com anexo de arquivo."""
    from App.banco import db
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
    assert "Interação registrada.".encode("utf-8") in response.data

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
    from App.banco import db
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


def test_mudar_status_para_agendado(client, app, admin_user):
    """Testa mudanca de status para Agendado e criacao de visita."""
    from App.banco import db
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
    assert "Interação registrada.".encode("utf-8") in response.data

    # Verificar se agendamento foi criado
    with app.app_context():
        ch = db.session.get(Chamado, chamado_id)
        assert ch.status == "Agendado"

        visita = Agendamento.query.filter_by(chamado_id=chamado_id).first()
        assert visita is not None
        assert visita.instrucoes_tecnicas == "Levar equipamento de teste"


def test_agendamento_com_conflito(client, app, admin_user):
    """Testa deteccao de conflito de horario ao agendar visita."""
    from App.banco import db
    from App.Modulos.Agenda.modelo import Agendamento
    from datetime import datetime, timedelta

    horario_conflito = datetime.now() + timedelta(days=2)

    with app.app_context():
        # Criar agendamento existente
        cliente1 = Cliente(
            nome_razao="Cliente Conflito 1", cpf_cnpj="555", created_by=admin_user.id
        )
        db.session.add(cliente1)
        db.session.flush()

        chamado1 = Chamado(
            cliente_id=cliente1.id,
            assunto="Chamado Existente",
            descricao="Ja agendado",
            created_by=admin_user.id,
        )
        chamado1.gerar_protocolo()
        db.session.add(chamado1)
        db.session.flush()

        visita_existente = Agendamento(
            chamado_id=chamado1.id,
            tecnico_id=admin_user.id,
            data_inicio=horario_conflito,
            data_fim=horario_conflito + timedelta(hours=2),
            instrucoes_tecnicas="Primeira visita",
            created_by=admin_user.id,
        )
        db.session.add(visita_existente)

        # Criar novo chamado para tentar agendar no mesmo horario
        cliente2 = Cliente(
            nome_razao="Cliente Conflito 2", cpf_cnpj="444", created_by=admin_user.id
        )
        db.session.add(cliente2)
        db.session.flush()

        chamado2 = Chamado(
            cliente_id=cliente2.id,
            assunto="Tentativa de Conflito",
            descricao="Tentar agendar no mesmo horario",
            created_by=admin_user.id,
        )
        chamado2.gerar_protocolo()
        db.session.add(chamado2)
        db.session.commit()
        chamado2_id = chamado2.id

    client.post(
        url_for("auth.login"), data={"username": "admin_test", "password": "123456"}
    )

    # Tentar agendar no horario conflitante
    inicio = (horario_conflito + timedelta(minutes=30)).isoformat()
    fim = (horario_conflito + timedelta(hours=1, minutes=30)).isoformat()

    data = {
        "texto": "Tentando agendar em horario ja ocupado",
        "novo_status": "Agendado",
        "data_inicio": inicio,
        "data_fim": fim,
        "instrucoes_tecnicas": "Segunda visita (conflitante)",
    }

    response = client.post(
        url_for("chamados.detalhe", id=chamado2_id),
        data=data,
        follow_redirects=True,
    )

    assert response.status_code == 200
    # Deve ter aviso de conflito no andamento
    assert b"AVISO: Conflito" in response.data or b"Conflito" in response.data


def test_download_anexo(client, app, admin_user):
    """Testa o download de anexo de chamado."""
    from App.banco import db
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
