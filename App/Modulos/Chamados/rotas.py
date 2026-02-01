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
from App.banco import db
from App.Modulos.Chamados.modelo import Chamado, Andamento
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.formulario import ChamadoForm, AndamentoForm
from App.upload_manager import UploadManager
from flask import current_app
from datetime import datetime

chamados_bp = Blueprint(
    "chamados", __name__, template_folder="templates", url_prefix="/chamados"
)


@chamados_bp.route("/")
@login_required
def lista():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "ativos")

    query = Chamado.query.join(Cliente).order_by(Chamado.created_at.desc())

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
    else:  # Default: Todos exceto Fechado (agora chamado 'Abertos' na UI)
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
        flash(f"Chamado {chamado.protocolo} criado com sucesso!", "success")
        return redirect(url_for("chamados.detalhe", id=chamado.id))

    return render_template("chamado_form.html", form=form)


@chamados_bp.route("/detalhe/<id>", methods=["GET", "POST"])
@login_required
def detalhe(id):
    chamado = db.get_or_404(Chamado, id)
    form = AndamentoForm()

    if form.validate_on_submit():
        # Lógica de Upload Seguro
        caminho_anexo = None
        if form.anexo.data:
            try:
                # Usa UploadManager para salvar e validar "Magic Numbers"
                # organizando por Cliente
                sub_diretorio = (
                    f"Clientes/{chamado.cliente_id}/{datetime.now().strftime('%Y')}"
                )
                caminho_anexo = UploadManager.salvar(
                    form.anexo.data, subfolder=sub_diretorio
                )
            except ValueError as e:
                flash(f"Erro no upload: {str(e)}", "error")
                return redirect(url_for("chamados.detalhe", id=id))

        # Novo Andamento
        andamento = Andamento(
            chamado_id=chamado.id,
            usuario_id=current_user.id,
            texto=form.texto.data,
            tipo="Resposta",
            anexo=caminho_anexo,
            created_by=current_user.id,
        )
        andamento.save()

        # Workflow de Status
        if form.novo_status.data and form.novo_status.data != chamado.status:
            velho_status = chamado.status
            novo_status = form.novo_status.data
            chamado.status = novo_status
            chamado.save()

            # Lógica extra por status
            if novo_status == "Escalonado":
                chamado.tecnico_id = None  # Libera para o Nível Superior assumir

            # Se for agendado, tenta criar a visita na agenda
            if (
                novo_status == "Agendado"
                and form.data_inicio.data
                and form.data_fim.data
            ):
                from App.Modulos.Agenda.modelo import Agendamento
                from App.Modulos.Agenda.agenda_logica import verificar_conflito
                import arrow

                inicio = arrow.get(form.data_inicio.data).datetime
                fim = arrow.get(form.data_fim.data).datetime

                if not verificar_conflito(current_user.id, inicio, fim):
                    visita = Agendamento(
                        chamado_id=chamado.id,
                        tecnico_id=current_user.id,
                        data_inicio=inicio,
                        data_fim=fim,
                        instrucoes_tecnicas=form.instrucoes_tecnicas.data,
                        created_by=current_user.id,
                    )
                    db.session.add(visita)
                    msg_agenda = (
                        f" (Visita agendada para {inicio.strftime('%d/%m/%Y %H:%M')})"
                    )
                else:
                    msg_agenda = " (AVISO: Conflito de horário detectado na agenda!)"
            else:
                msg_agenda = ""

            # Registra evento de sistema
            evt = Andamento(
                chamado_id=chamado.id,
                usuario_id=current_user.id,
                texto=f"Alterou status de **{velho_status}** para **{chamado.status}**{msg_agenda}",
                tipo="Evento",
            )
            evt.save()
            db.session.commit()

        flash("Interação registrada.", "success")
        return redirect(url_for("chamados.detalhe", id=id))

    return render_template("chamado_detalhe.html", chamado=chamado, form=form)


@chamados_bp.route("/atualizar_visita/<id>", methods=["POST"])
@login_required
def atualizar_visita(id):
    from App.Modulos.Agenda.modelo import Agendamento

    visita = db.get_or_404(Agendamento, id)
    chamado_id = visita.chamado_id

    instrucoes = request.form.get("instrucoes_tecnicas")
    visita.instrucoes_tecnicas = instrucoes
    visita.save()

    flash("Instruções técnicas atualizadas!", "success")
    return redirect(url_for("chamados.detalhe", id=chamado_id))


@chamados_bp.route("/anexo/<path:filename>")
@login_required
def baixar_anexo(filename):
    # Serve arquivos seguros da pasta Data/Uploads
    uploads = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(uploads, filename)
