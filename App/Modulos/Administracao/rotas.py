import os
import glob
from datetime import datetime, timezone
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
from App.servicos.seguranca import limiter, admin_required

from App.Modulos.Administracao.modelo import Configuracao, TarefaMonitor
from App.Modulos.Administracao.formulario import ConfiguracaoForm, NotificacaoForm
from App.servicos.upload_manager import UploadManager
from App.servicos.agendador import scheduler
from App.servicos.notificador import Notificador
from App.servicos.criptografia import encriptar, decriptar

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


@admin_bp.route("/notificacoes")
@login_required
@admin_required
def notificacoes():
    cfg = Configuracao.get_config()
    # Lista estática de provedores acompanhando o padrão de IDs do sistema
    provedores = [
        {
            "id": "telegram",
            "uuid": "7b2e9a11-5fc3-4a1e-8d2b-f9e0a1b2c3d4",
            "nome": "Telegram Bot",
            "descricao": "Alertas em tempo real via Bot",
            "ativo": cfg.telegram_ativo,
            "icone": "ph-paper-plane-tilt",
            "cor": "blue",
        },
        {
            "id": "email",
            "uuid": "4f9d8c7a-3b2e-1a0d-9c8b-7a6f5e4d3c2b",
            "nome": "E-mail (SMTP)",
            "descricao": "Notificações por email SMTP",
            "ativo": cfg.email_ativo,
            "icone": "ph-envelope",
            "cor": "gray",
        },
        {
            "id": "whatsapp",
            "uuid": "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
            "nome": "WhatsApp Business",
            "descricao": "Integração via API Evolution",
            "ativo": cfg.whatsapp_ativo,
            "icone": "ph-whatsapp-logo",
            "cor": "green",
        },
    ]
    return render_template("admin_notificacoes.html", provedores=provedores, config=cfg)


@admin_bp.route("/notificacoes/editar/<provedor>", methods=["GET", "POST"])
@login_required
@admin_required
def notificacao_editar(provedor):
    cfg = Configuracao.get_config()
    form = NotificacaoForm(obj=cfg)

    if form.validate_on_submit():
        # Lógica Dinâmica: Pegamos todos os campos do formulário que começam com o nome do provedor
        # Ex: se provedor for 'telegram', pegamos 'telegram_token', 'telegram_ativo', etc.
        prefixo = f"{provedor}_"

        for campo_nome, campo_objeto in form._fields.items():
            if campo_nome.startswith(prefixo):
                if hasattr(cfg, campo_nome):
                    # Se for campo de senha e estiver vazio, não sobrescrevemos o banco
                    if (
                        campo_nome
                        in ["email_password", "whatsapp_key", "telegram_token"]
                        and not campo_objeto.data
                    ):
                        continue

                    # Se houver dados em campo de senha, encriptamos
                    if campo_nome in [
                        "email_password",
                        "whatsapp_key",
                        "telegram_token",
                    ]:
                        setattr(cfg, campo_nome, encriptar(campo_objeto.data))
                    else:
                        setattr(cfg, campo_nome, campo_objeto.data)

        cfg.save()
        flash(f"Integração {provedor.capitalize()} atualizada!", "success")
        return redirect(url_for("admin.notificacoes"))

    return render_template(
        "admin_notificacao_form.html", form=form, provedor=provedor, config=cfg
    )


@admin_bp.route("/notificacoes/teste-telegram", methods=["POST"])
@login_required
@admin_required
def teste_telegram():
    token = request.form.get("token")
    chat_id = request.form.get("chat_id")

    # Se o token vier vazio do form de teste, tenta pegar o encriptado do banco e decriptar
    if not token:
        cfg = Configuracao.get_config()
        token = decriptar(cfg.telegram_token)

    if not token or not chat_id:
        return {"success": False, "message": "Preencha Token e Chat ID para testar."}

    sucesso, mensagem = Notificador.test_telegram(token, chat_id)
    return {"success": sucesso, "message": mensagem or "Teste enviado!"}


@admin_bp.route("/notificacoes/teste-email", methods=["POST"])
@login_required
@admin_required
def teste_email():
    host = request.form.get("host")
    port = request.form.get("port")
    user = request.form.get("user")
    password = request.form.get("password")

    # Se a senha vier vazia do form de teste, tenta pegar a encriptada do banco e decriptar
    if not password:
        cfg = Configuracao.get_config()
        password = decriptar(cfg.email_password)

    if not all([host, port, user, password]):
        return {"success": False, "message": "Preencha todos os campos do SMTP."}

    sucesso, mensagem = Notificador.test_email(host, port, user, password)
    return {"success": sucesso, "message": mensagem}


@admin_bp.route("/notificacoes/teste-whatsapp", methods=["POST"])
@login_required
@admin_required
def teste_whatsapp():
    url = request.form.get("url")
    key = request.form.get("key")
    destination = request.form.get("destination")

    # Se a key vier vazia do form de teste, tenta pegar a encriptada do banco e decriptar
    if not key:
        cfg = Configuracao.get_config()
        key = decriptar(cfg.whatsapp_key)

    if not url or not key:
        return {"success": False, "message": "Preencha URL e Key para testar."}

    sucesso, mensagem = Notificador.test_whatsapp(url, key, destination)
    return {"success": sucesso, "message": mensagem}


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
                    "data": datetime.fromtimestamp(
                        stats.st_mtime, tz=timezone.utc
                    ).strftime("%d/%m/%Y %H:%M:%S"),
                }
            )

    # --- MONITORAMENTO DE TAREFAS ---
    # Busca status do banco (TarefaMonitor)
    stats_tarefas = {t.tarefa_id: t for t in TarefaMonitor.query.all()}

    # Busca jobs ativos no scheduler
    jobs_ativos = []
    try:
        for job in scheduler.get_jobs():
            # Tenta encontrar o monitor correspondente removendo padrões de automação
            id_limpo = job.id.replace("auto_", "").replace("_auto", "")
            monitor = stats_tarefas.get(id_limpo)
            if not monitor:
                monitor = stats_tarefas.get(job.id)

            jobs_ativos.append(
                {
                    "id": job.id,
                    "proxima_execucao": job.next_run_time.strftime("%d/%m/%Y %H:%M:%S")
                    if job.next_run_time
                    else "Pausado",
                    "id_amigavel": job.id.replace("_", " ").title(),
                    "pausado": job.next_run_time is None,
                    "monitor": monitor,
                }
            )
    except Exception as e:
        current_app.logger.warning(f"Não foi possível ler jobs do scheduler: {e}")

    return render_template("admin_backups.html", backups=arquivos, jobs=jobs_ativos)


@admin_bp.route("/tarefa/executar/<id>")
@login_required
@admin_required
def executar_tarefa(id):
    """Executa uma tarefa do agendador imediatamente."""
    job = scheduler.get_job(id)
    if not job:
        flash("Tarefa não encontrada no agendador.", "danger")
        return redirect(url_for("admin.backups"))

    try:
        # Executa a função do job passando o app context
        job.func(current_app._get_current_object())
        flash(f"Tarefa '{id}' disparada com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao executar tarefa: {str(e)}", "danger")

    return redirect(url_for("admin.backups"))


@admin_bp.route("/tarefa/pausar/<id>")
@login_required
@admin_required
def pausar_tarefa(id):
    """Pausa uma tarefa agendada."""
    try:
        scheduler.pause_job(id)
        flash("Tarefa pausada com sucesso.", "info")
    except Exception as e:
        flash(f"Erro ao pausar: {str(e)}", "danger")
    return redirect(url_for("admin.backups"))


@admin_bp.route("/tarefa/retomar/<id>")
@login_required
@admin_required
def retomar_tarefa(id):
    """Retoma uma tarefa agendada."""
    try:
        scheduler.resume_job(id)
        flash("Tarefa retomada com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao retomar: {str(e)}", "danger")
    return redirect(url_for("admin.backups"))


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
