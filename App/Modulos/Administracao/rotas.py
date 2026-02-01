import os
import glob
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    send_from_directory,
    flash,
    current_app,
    redirect,
    url_for,
    request,
)
from flask_login import login_required, current_user
from App.seguranca import limiter, admin_required

from App.Modulos.Administracao.modelo import Configuracao
from App.Modulos.Administracao.formulario import ConfiguracaoForm
from App.upload_manager import UploadManager

# Blueprint para ferramentas Admin (Logs e Backups)
admin_bp = Blueprint(
    "admin", __name__, template_folder="templates", url_prefix="/admin"
)


@admin_bp.route("/config", methods=["GET", "POST"])
@login_required
@admin_required
def configuracoes():
    cfg = Configuracao.get_config()
    form = ConfiguracaoForm(obj=cfg)

    if form.validate_on_submit():
        # Preserva o caminho atual da logo para evitar que o populate_obj
        # coloque um objeto FileStorage no lugar de uma String no banco.
        logo_atual = cfg.empresa_logo
        form.populate_obj(cfg)
        cfg.empresa_logo = logo_atual

        # Tratar Upload de Logo
        if form.empresa_logo.data:
            try:
                # Salva na pasta de sistema
                caminho = UploadManager.salvar(
                    form.empresa_logo.data, subfolder="Sistema"
                )
                cfg.empresa_logo = caminho
            except Exception as e:
                flash(f"Erro ao salvar logo: {str(e)}", "error")

        cfg.save()
        flash("Configurações atualizadas com sucesso!", "success")
        return redirect(url_for("admin.configuracoes"))

    return render_template("admin_config.html", form=form, config=cfg)


@admin_bp.route("/logs")
@login_required
@admin_required
@limiter.exempt
def logs():
    import re

    # Lê o arquivo real de logs (Data/Logs/system.log)
    log_file = os.path.join(
        current_app.config["BASE_DIR"], "Data", "Logs", "system.log"
    )
    logs_data = []
    filtro_cat = request.args.get("cat", "todos")

    # Regex para capturar: DATA HORA, [IP], LEVEL, MSG, ORIGEM
    log_pattern = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(.*?)\] (.*?): (.*) \[in (.*):(\d+)\]$"
    )

    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                # Processamos as últimas 100 linhas
                for line in reversed(lines[-100:]):
                    match = log_pattern.match(line.strip())
                    if match:
                        timestamp, ip, level, msg, path, line_num = match.groups()

                        # Inteligência de Categorização
                        categoria = "geral"
                        security_keywords = [
                            "login",
                            "acesso",
                            "negado",
                            "backup",
                            "autorizado",
                            "security",
                        ]

                        if level in ["ERROR", "CRITICAL"]:
                            categoria = "erro"
                        elif any(kw in msg.lower() for kw in security_keywords):
                            categoria = "seguranca"

                        # Filtro por categoria (se não for "todos")
                        if filtro_cat != "todos" and categoria != filtro_cat:
                            continue

                        logs_data.append(
                            {
                                "time": timestamp,
                                "ip": ip,
                                "level": level,
                                "msg": msg,
                                "origin": f"{os.path.basename(path)}:{line_num}",
                                "categoria": categoria,
                            }
                        )
                    else:
                        if filtro_cat == "todos":
                            logs_data.append(
                                {
                                    "time": "-",
                                    "level": "RAW",
                                    "msg": line,
                                    "categoria": "geral",
                                    "ip": "-",
                                }
                            )

        except Exception as e:
            logs_data.append(
                {
                    "time": "-",
                    "level": "ERROR",
                    "msg": f"Erro ao ler logs: {str(e)}",
                    "categoria": "erro",
                    "ip": "-",
                }
            )
    else:
        logs_data.append(
            {
                "time": "-",
                "level": "INFO",
                "msg": "Arquivo de log ainda não criado.",
                "categoria": "geral",
                "ip": "-",
            }
        )

    return render_template(
        "admin_logs.html", logs=logs_data, categoria_ativa=filtro_cat
    )


# --- BACKUP MANAGER ---

MAX_BACKUPS = 14


@admin_bp.route("/backups")
@login_required
@admin_required
@limiter.exempt
def backups():
    backup_dir = os.path.join(current_app.config["BASE_DIR"], "Data", "Backups")
    arquivos = []

    if os.path.exists(backup_dir):
        # Lista arquivos .db ordenados por data (mais recente primeiro)
        files = glob.glob(os.path.join(backup_dir, "*.db"))
        files.sort(key=os.path.getmtime, reverse=True)

        for f in files:
            stats = os.stat(f)
            arquivos.append(
                {
                    "nome": os.path.basename(f),
                    "tamanho": f"{stats.st_size / 1024:.2f} KB",
                    "data": datetime.fromtimestamp(stats.st_mtime).strftime(
                        "%d/%m/%Y %H:%M:%S"
                    ),
                }
            )

    return render_template("admin_backups.html", backups=arquivos)


@admin_bp.route("/backup/gerar")
@login_required
@admin_required
def gerar_backup():
    """Gera um backup instantâneo do banco.db e rotaciona os antigos."""
    from .servicos import executar_backup_banco

    sucesso, mensagem = executar_backup_banco(
        origem_manual=True, usuario=current_user.username
    )

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("admin.backups"))


@admin_bp.route("/backup/download/<filename>")
@login_required
@admin_required
def download_backup(filename):
    backup_dir = os.path.join(current_app.config["BASE_DIR"], "Data", "Backups")
    current_app.logger.info(f"Download backup {filename} por {current_user.username}")
    return send_from_directory(backup_dir, filename, as_attachment=True)
