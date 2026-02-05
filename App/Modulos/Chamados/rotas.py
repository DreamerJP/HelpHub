from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    send_from_directory,
)
from flask_login import login_required, current_user
from App.servicos.seguranca import admin_required
from App.banco import db
from App.Modulos.Chamados.modelo import Chamado, Andamento
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.formulario import ChamadoForm, AndamentoForm
from App.servicos.upload_manager import UploadManager
from App.servicos.notificador import Notificador
from flask import current_app
from datetime import datetime, timezone

chamados_bp = Blueprint(
    "chamados", __name__, template_folder="templates", url_prefix="/chamados"
)


@chamados_bp.route("/")
@login_required
def lista():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "ativos")

    from sqlalchemy.orm import joinedload

    query = Chamado.query.options(
        joinedload(Chamado.cliente),
        joinedload(Chamado.departamento),
        joinedload(Chamado.tecnico),
    ).join(Cliente)

    # Otimização: Eager load das visitas apenas na aba Agendados
    if status_filter == "agendados":
        query = query.options(joinedload(Chamado.visitas))

    # Ordenação Dinâmica (1 Linha)
    query = Chamado.apply_sort(
        query, request.args.get("sort"), request.args.get("order")
    )

    # Ordenação Padrão (se não houve dinâmica)
    if not request.args.get("sort"):
        query = query.order_by(Chamado.created_at.desc())

    # Filtros de Status
    if status_filter == "abertos":
        query = query.filter(Chamado.status == "Aberto")
    elif status_filter == "agendados":
        query = query.filter(Chamado.status == "Agendado")
    elif status_filter == "escalonados":
        query = query.filter(Chamado.status == "Escalonado")
    elif status_filter == "pendentes":
        query = query.filter(Chamado.status == "Pendente")
    elif status_filter == "fechados":
        query = query.filter(Chamado.status == "Fechado")
    else:  # Default: Todos exceto Fechado
        status_filter = "ativos"
        query = query.filter(Chamado.status != "Fechado")

    if q:
        query = query.filter(
            (Chamado.protocolo.ilike(f"%{q}%"))
            | (Chamado.assunto.ilike(f"%{q}%"))
            | (Cliente.nome_razao.ilike(f"%{q}%"))
        )

    chamados = query.paginate(page=page, per_page=20)
    return render_template(
        "chamado_lista.html", chamados=chamados, q=q, status_filter=status_filter
    )


@chamados_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    form = ChamadoForm()
    if form.validate_on_submit():
        chamado = Chamado()
        chamado.cliente_id = form.cliente_id.data
        # Trata select opcional (vazio = None)
        chamado.departamento_id = (
            form.departamento_id.data if form.departamento_id.data else None
        )
        chamado.assunto = form.assunto.data
        chamado.descricao = form.descricao.data
        chamado.prioridade = form.prioridade.data
        chamado.gerar_protocolo()

        # Campo de Auditoria Auto-Fill pelo BaseModel
        chamado.created_by = current_user.id

        chamado.save()

        # Dispara Notificações (Telegram/Email) via Hub Central
        try:
            Notificador.notify_new_ticket(chamado)
        except Exception as e:
            current_app.logger.error(f"Erro ao disparar notificações: {e}")

        flash(f"Chamado {chamado.protocolo} criado com sucesso!", "success")
        return redirect(url_for("chamados.detalhe", id=chamado.id))

    return render_template("chamado_form.html", form=form, titulo="Novo Chamado")


@chamados_bp.route("/detalhe/<id>", methods=["GET", "POST"])
@login_required
def detalhe(id):
    chamado = db.get_or_404(Chamado, id)
    form = AndamentoForm()

    if form.validate_on_submit():
        from App.Modulos.Chamados.servicos import ChamadoService

        # Lógica de Upload Seguro
        caminho_anexo = None
        if form.anexo.data:
            try:
                sub_diretorio = f"Clientes/{chamado.cliente_id}/{datetime.now(timezone.utc).strftime('%Y')}"
                caminho_anexo = UploadManager.salvar(
                    form.anexo.data, subfolder=sub_diretorio
                )
            except ValueError as e:
                flash(f"Erro no upload: {str(e)}", "error")
                return redirect(url_for("chamados.detalhe", id=id))

        # Preparar dados de agendamento se necessário
        dados_agendamento = None
        if (
            form.novo_status.data == "Agendado"
            and form.data_inicio.data
            and form.data_fim.data
        ):
            import arrow

            # Usa o técnico selecionado no formulário, ou o usuário atual se não foi selecionado
            tecnico_selecionado = form.tecnico_id.data if form.tecnico_id.data else current_user.id

            dados_agendamento = {
                "inicio": arrow.get(form.data_inicio.data)
                .replace(second=0, microsecond=0)
                .naive,
                "fim": arrow.get(form.data_fim.data)
                .replace(second=0, microsecond=0)
                .naive,
                "instrucoes": form.instrucoes_tecnicas.data,
                "tecnico_id": tecnico_selecionado,
            }

        # Registrar Interação Completa via Serviço
        success, msg = ChamadoService.registrar_interacao(
            chamado_id=id,
            usuario_id=current_user.id,
            texto=form.texto.data,
            tipo="Resposta",
            novo_status=form.novo_status.data
            if form.novo_status.data != chamado.status
            else None,
            anexo=caminho_anexo,
            dados_agendamento=dados_agendamento,
        )

        if not success:
            flash(msg, "error")
            return redirect(url_for("chamados.detalhe", id=id))

        flash(msg, "success")
        return redirect(url_for("chamados.detalhe", id=id))

    # VALIDAÇÃO BACKEND: Calcula se cada andamento pode ser retratado
    agora = datetime.now(timezone.utc)
    for andamento in chamado.andamentos:
        # Garante que created_at tenha timezone (compatibilidade com dados antigos)
        created_at = andamento.created_at
        if created_at.tzinfo is None:
            # Se for naive, assume UTC
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        tempo_decorrido = (agora - created_at).total_seconds()
        andamento.pode_retratar = (
            tempo_decorrido < 600  # 10 minutos = 600 segundos
            and andamento.usuario_id == current_user.id
            and not andamento.foi_retratado
            and andamento.tipo != "Evento"
        )

    return render_template("chamado_detalhe.html", chamado=chamado, form=form)


@chamados_bp.route("/andamento/retratar/<id>", methods=["POST"])
@login_required
def retratar_andamento(id):
    from .servicos import ChamadoService

    success, msg = ChamadoService.retratar_andamento(
        andamento_id=id, usuario_id=current_user.id
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "error")

    # Redireciona de volta para o detalhe do chamado
    # Precisamos do ID do chamado, vamos pegar do andamento
    andamento = db.session.get(Andamento, id)
    if andamento:
        return redirect(url_for("chamados.detalhe", id=andamento.chamado_id))

    return redirect(url_for("chamados.lista"))


@chamados_bp.route("/atualizar_visita/<id>", methods=["POST"])
@login_required
def atualizar_visita(id):
    from App.Modulos.Agenda.modelo import Agendamento
    from App.Modulos.Chamados.servicos import ChamadoService
    import arrow

    visita = db.get_or_404(Agendamento, id)
    chamado_id = visita.chamado_id

    # 1. Preparar e Validar Reagendamento via Motor Central
    try:
        inicio_str = request.form.get("data_inicio")
        fim_str = request.form.get("data_fim")
        tecnico_id = request.form.get("tecnico_id")
        
        if not all([inicio_str, fim_str, tecnico_id]):
            flash("Todos os campos de agendamento são obrigatórios.", "warning")
            return redirect(url_for("chamados.detalhe", id=chamado_id))

        nova_dt_inicio = arrow.get(inicio_str).replace(second=0, microsecond=0).naive
        nova_dt_fim = arrow.get(fim_str).replace(second=0, microsecond=0).naive

        # Chama o serviço central para validar conflitos, atualizar datas/técnico e gerar logs
        success, msg = ChamadoService.reagendar_visita(
            agendamento_id=id,
            nova_data_inicio=nova_dt_inicio,
            nova_data_fim=nova_dt_fim,
            tecnico_id=tecnico_id,
            usuario_id=current_user.id
        )

        if not success:
            flash(msg, "error")
            return redirect(url_for("chamados.detalhe", id=chamado_id))

        # 2. Atualizar Instruções Técnicas (Campo específico deste agendamento)
        visita.instrucoes_tecnicas = request.form.get("instrucoes_tecnicas")
        visita.save()

        flash("Agendamento técnico atualizado com sucesso!", "success")
        
    except Exception as e:
        flash(f"Erro inesperado no agendamento: {str(e)}", "error")

    return redirect(url_for("chamados.detalhe", id=chamado_id))


@chamados_bp.route("/excluir/<id>", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    chamado = db.get_or_404(Chamado, id)
    protocolo = chamado.protocolo
    chamado.delete()
    flash(f"Chamado {protocolo} excluído permanentemente!", "success")
    return redirect(url_for("chamados.lista"))


@chamados_bp.route("/anexo/<path:filename>")
@login_required
def baixar_anexo(filename):
    # Serve arquivos seguros da pasta Data/Uploads
    uploads = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(uploads, filename)
