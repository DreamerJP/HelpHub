from flask import url_for
from App.Modulos.Administracao.modelo import Configuracao


def test_admin_config_access_denied_for_non_auth(client):
    """Test that unauthorized users can't access config."""
    response = client.get(url_for("admin.configuracoes"))
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_admin_config_update(client, app, admin_user):
    """Test updating company configuration."""
    # Login
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # Initial state
    with app.app_context():
        cfg = Configuracao.get_config()
        assert cfg.empresa_nome == "Minha Empresa"

    # Update through form
    response = client.post(
        url_for("admin.configuracoes"),
        data={
            "empresa_nome": "Global Tech",
            "empresa_cnpj": "00.111.222/0001-33",
            "empresa_email": "admin@globaltech.com",
            "empresa_telefone": "555-0199",
            "empresa_endereco": "One Apple Park Way, Cupertino, CA",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Configura\xc3\xa7\xc3\xb5es atualizadas com sucesso!" in response.data

    with app.app_context():
        cfg = Configuracao.get_config()
        assert cfg.empresa_nome == "Global Tech"
        assert cfg.empresa_cnpj == "00.111.222/0001-33"


def test_admin_config_logo_upload(client, app, admin_user):
    """Testa o upload de logo da empresa."""
    import io
    import os

    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # Simular upload de imagem com Magic Number real de PNG
    logo_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    data = {
        "empresa_nome": "Tech Corp",
        "empresa_logo": (io.BytesIO(logo_content), "logo_teste.png"),
    }

    response = client.post(
        url_for("admin.configuracoes"),
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Configura".encode("utf-8") in response.data

    with app.app_context():
        cfg = Configuracao.get_config()
        assert "Sistema/" in cfg.empresa_logo
        assert cfg.empresa_logo.endswith(".png")

        # Verificar se o arquivo existe fisicamente no UPLOAD_FOLDER (isolado no conftest)
        caminho_real = os.path.join(app.config["UPLOAD_FOLDER"], cfg.empresa_logo)
        assert os.path.exists(caminho_real)


def test_admin_logs_view_and_filters(client, app, admin_user):
    """Testa a visualizacao e filtragem de logs."""
    import os

    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # Setup: Criar um arquivo de log fake
    # O rotas.py busca em BASE_DIR/Data/Logs/system.log
    # Para nao sujar a raiz, vamos mudar temporariamente a config de BASE_DIR se possivel
    # ou apenas garantir que o teste lida com o que encontrar.
    # Como queremos cobertura, vamos injetar um log.

    base_dir = app.config["BASE_DIR"]
    log_dir = os.path.join(base_dir, "Data", "Logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "system.log")

    log_entries = [
        "2026-01-30 15:00:00,000 [127.0.0.1] INFO: Teste log comum [in test.py:1]\n",
        "2026-01-30 15:01:00,000 [127.0.0.1] ERROR: Teste de erro critico [in test.py:2]\n",
        "2026-01-30 15:02:00,000 [127.0.0.1] INFO: Tentativa de login bem sucedida [in test.py:3]\n",
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        f.writelines(log_entries)

    # 1. Ver todos os logs
    response = client.get(url_for("admin.logs"))
    assert response.status_code == 200
    assert b"Teste log comum" in response.data
    assert b"Teste de erro critico" in response.data

    # 2. Filtrar por seguranca (palavra 'login' deve categorizar como seguranca)
    response = client.get(url_for("admin.logs", cat="seguranca"))
    assert response.status_code == 200
    assert b"login bem sucedida" in response.data
    assert b"Teste log comum" not in response.data

    # 3. Filtrar por erro
    response = client.get(url_for("admin.logs", cat="erro"))
    assert response.status_code == 200
    assert b"erro critico" in response.data
    assert b"Teste log comum" not in response.data


def test_admin_backups_manage(client, app, admin_user):
    """Testa listagem, geracao e download de backups."""
    import os

    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    base_dir = app.config["BASE_DIR"]
    data_dir = os.path.join(base_dir, "Data")
    backup_dir = os.path.join(data_dir, "Backups")
    os.makedirs(backup_dir, exist_ok=True)

    # 1. Testar Listagem (vazia ou com arquivos)
    # Criar um arquivo dummy de backup
    backup_file = os.path.join(backup_dir, "banco_test_manual.db")
    with open(backup_file, "w") as f:
        f.write("dummy db content")

    response = client.get(url_for("admin.backups"))
    assert response.status_code == 200
    assert b"banco_test_manual.db" in response.data

    # 2. Testar Geracao de Backup
    # Precisa que Data/banco.db exista
    db_original = os.path.join(data_dir, "banco.db")
    if not os.path.exists(db_original):
        with open(db_original, "w") as f:
            f.write("original db content")

    response = client.get(url_for("admin.gerar_backup"), follow_redirects=True)
    assert response.status_code == 200
    assert "sucesso".encode("utf-8") in response.data.lower()

    # 3. Testar Download de Backup
    response = client.get(
        url_for("admin.download_backup", filename="banco_test_manual.db")
    )
    assert response.status_code == 200
    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename=banco_test_manual.db"
    )
    assert b"dummy db content" in response.data


def test_admin_logs_file_not_found(client, app, admin_user):
    """Testa visualizacao de logs quando o arquivo nao existe."""
    import os

    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    base_dir = app.config["BASE_DIR"]
    log_file = os.path.join(base_dir, "Data", "Logs", "system.log")

    # Garantir que nao existe
    if os.path.exists(log_file):
        os.remove(log_file)

    response = client.get(url_for("admin.logs"))
    assert response.status_code == 200
    assert "ainda não criado".encode("utf-8") in response.data


def test_admin_backups_scheduler_error_alert(client, app, admin_user):
    """Testa se o alerta de erro do agendador aparece na tela de backups quando há erro."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # Simular erro no agendador injetando na config
    app.config["SCHEDULER_ERROR"] = "Erro de Threads uWSGI simulado"

    response = client.get(url_for("admin.backups"))
    assert response.status_code == 200
    assert "Aviso: Agendador de Tarefas Inativo".encode("utf-8") in response.data
    assert "Erro de Threads uWSGI simulado".encode("utf-8") in response.data

    # Limpar após o teste
    app.config["SCHEDULER_ERROR"] = False
