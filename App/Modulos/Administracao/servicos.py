import os
import shutil
import glob
from datetime import datetime, timezone
from flask import current_app

MAX_BACKUPS = 14


def executar_backup_banco(origem_manual=False, usuario=None):
    """
    Lógica centralizada para gerar backup do banco.db e realizar a rotação.
    """
    base_dir = current_app.config["BASE_DIR"]
    data_dir = os.path.join(base_dir, "Data")
    backup_dir = os.path.join(data_dir, "Backups")
    # Tenta pegar DB_PATH da config, senão usa o padrão banco.db
    db_file = current_app.config.get("DB_PATH") or os.path.join(data_dir, "banco.db")

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    if not os.path.exists(db_file):
        current_app.logger.error("Falha no backup: banco.db não encontrado.")
        return False, "Banco de dados não encontrado."

    try:
        # 1. Gerar o Backup
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = "manual" if origem_manual else "auto"
        filename = f"banco_{timestamp}_{suffix}.db"
        dest_path = os.path.join(backup_dir, filename)

        shutil.copy2(db_file, dest_path)

        # 2. Rotação
        files = glob.glob(os.path.join(backup_dir, "*.db"))
        files.sort(key=os.path.getmtime, reverse=True)

        if len(files) > MAX_BACKUPS:
            for old_file in files[MAX_BACKUPS:]:
                os.remove(old_file)

        msg_log = f"Backup {suffix} gerado: {filename}"
        if usuario:
            msg_log += f" por {usuario}"

        current_app.logger.info(msg_log)

        # Atualiza a "memória" do sistema para resiliência do agendador
        try:
            from .modelo import Configuracao

            cfg = Configuracao.get_config()
            cfg.ultimo_backup_auto = datetime.now(timezone.utc)
            cfg.save()
            current_app.config["BACKUP_ATRASADO"] = False
        except Exception as e:
            current_app.logger.warning(
                f"Não foi possível salvar timestamp do backup: {e}"
            )

        return True, "Backup realizado com sucesso."

    except Exception as e:
        current_app.logger.error(f"Erro ao executar backup: {str(e)}")
        return False, f"Erro interno: {str(e)}"
