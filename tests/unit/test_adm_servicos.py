import os
import shutil
import pytest
import time
from App.Modulos.Administracao.servicos import executar_backup_banco


def test_executar_backup_fluxo_completo(app, tmp_path):
    """
    Testa o fluxo completo de backup: criação do arquivo e rotação.
    """
    # 1. Configurar diretórios temporários usando tmp_path do pytest
    # Isso garante que não tocaremos em NADA do projeto real
    temp_root = tmp_path / "project_root"
    data_dir = temp_root / "Data"
    backup_dir = data_dir / "Backups"
    db_file = data_dir / "banco.db"

    data_dir.mkdir(parents=True)
    backup_dir.mkdir()

    # Criar um "banco.db" falso
    db_file.write_text("dados de teste")

    with app.app_context():
        # Sobrescrevemos o BASE_DIR na config do app para este teste
        # Note: No Flask real, se as constantes já foram criadas, isso pode variar,
        # mas como o serviço lê da config em tempo de execução, deve funcionar.
        app.config["BASE_DIR"] = str(temp_root)

        # 2. Testar Backup Manual
        sucesso, msg = executar_backup_banco(origem_manual=True, usuario="test_user")
        assert sucesso is True

        files = os.listdir(str(backup_dir))
        assert any("_manual.db" in f for f in files)

        # 3. Testar Rotação (Limite de 14 arquivos)
        # Vamos criar 15 arquivos de backup antigos
        for i in range(15):
            filename = f"banco_20260101_{i:02d}0000_old.db"
            target = backup_dir / filename
            target.write_text("backup antigo")
            # Ajusta mtime para garantir ordem de exclusão
            mtime = time.time() - (1000 - i)
            os.utime(str(target), (mtime, mtime))

        # Agora executamos mais um backup
        executar_backup_banco(origem_manual=False)

        # Verificar se a pasta tem exatamente 14 arquivos
        final_files = os.listdir(str(backup_dir))
        assert len(final_files) == 14


def test_backup_falha_sem_banco(app, tmp_path):
    """
    Testa se o sistema reporta erro caso o banco.db não exista.
    """
    temp_root = tmp_path / "project_root_fail"
    data_dir = temp_root / "Data"
    data_dir.mkdir(parents=True)

    with app.app_context():
        app.config["BASE_DIR"] = str(temp_root)
        # Não criamos o banco.db aqui

        sucesso, msg = executar_backup_banco()
        assert sucesso is False
        assert "não encontrado" in msg
