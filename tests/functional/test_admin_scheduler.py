from flask import url_for
from unittest.mock import patch, MagicMock
from App.servicos.agendador import scheduler


def test_admin_backups_with_no_jobs(client, app, admin_user):
    """Testa a visualização de backups quando não há jobs no agendador."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    with patch.object(scheduler, "get_jobs", return_value=[]):
        response = client.get(url_for("admin.backups"))
        assert response.status_code == 200
        assert b"Nenhuma tarefa agendada encontrada" in response.data


def test_admin_backups_with_jobs(client, app, admin_user):
    """Testa a visualização de backups com jobs ativos."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    mock_job = MagicMock()
    mock_job.id = "auto_backup_diario"
    mock_job.next_run_time.strftime.return_value = "01/01/2026 03:00:00"

    with patch.object(scheduler, "get_jobs", return_value=[mock_job]):
        response = client.get(url_for("admin.backups"))
        assert response.status_code == 200
        assert b"Auto Backup Diario" in response.data
        assert b"01/01/2026 03:00:00" in response.data


def test_executar_tarefa_success(client, app, admin_user):
    """Testa o disparo imediato de uma tarefa."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    mock_job = MagicMock()
    mock_job.id = "test_job"

    with patch.object(scheduler, "get_job", return_value=mock_job):
        response = client.get(
            url_for("admin.executar_tarefa", id="test_job"), follow_redirects=True
        )
        assert response.status_code == 200
        assert "disparada com sucesso".encode("utf-8") in response.data
        mock_job.func.assert_called_once()


def test_pausar_retomar_tarefa(client, app, admin_user):
    """Testa pausar e retomar uma tarefa."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    with patch.object(scheduler, "pause_job") as mock_pause:
        response = client.get(
            url_for("admin.pausar_tarefa", id="test_job"), follow_redirects=True
        )
        assert response.status_code == 200
        assert "Tarefa pausada com sucesso".encode("utf-8") in response.data
        mock_pause.assert_called_once_with("test_job")

    with patch.object(scheduler, "resume_job") as mock_resume:
        response = client.get(
            url_for("admin.retomar_tarefa", id="test_job"), follow_redirects=True
        )
        assert response.status_code == 200
        assert "Tarefa retomada com sucesso".encode("utf-8") in response.data
        mock_resume.assert_called_once_with("test_job")


def test_executar_tarefa_not_found(client, app, admin_user):
    """Testa erro ao tentar executar tarefa inexistente."""
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    with patch.object(scheduler, "get_job", return_value=None):
        response = client.get(
            url_for("admin.executar_tarefa", id="ghost"), follow_redirects=True
        )
        assert response.status_code == 200
        assert "Tarefa não encontrada".encode("utf-8") in response.data
