from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from App.Modulos.Agenda.modelo import Agendamento
from App.Modulos.Chamados.modelo import Chamado, Andamento
from App.Modulos.Agenda.agenda_logica import verificar_conflito
from App.Modulos.Autenticacao.modelo import Usuario
from App.banco import db
from sqlalchemy.orm import joinedload
import arrow

agenda_bp = Blueprint("agenda", __name__, template_folder="templates")


@agenda_bp.route("/agenda")
@login_required
def calendario():
    # Carrega chamados que podem ser agendados (Abertos ou já Agendados)
    chamados_disponiveis = (
        Chamado.query.options(joinedload(Chamado.cliente))
        .filter(Chamado.status.in_(["Aberto", "Agendado"]))
        .all()
    )

    # Carrega técnicos ativos para as colunas da agenda
    tecnicos = Usuario.query.filter_by(ativo=True).order_by(Usuario.nome).all()

    return render_template(
        "agenda_view.html",
        chamados_disponiveis=chamados_disponiveis,
        tecnicos=tecnicos,
    )


@agenda_bp.route("/agenda/api/eventos")
@login_required
def api_eventos():
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    # Usamos joinedload para trazer chamado, cliente e técnico em uma única consulta
    query = Agendamento.query.options(
        joinedload(Agendamento.chamado).joinedload(Chamado.cliente),
        joinedload(Agendamento.tecnico),
    ).filter(Agendamento.status != "Cancelado")

    if start_str and end_str:
        start_dt = arrow.get(start_str).datetime
        end_dt = arrow.get(end_str).datetime
        query = query.filter(
            Agendamento.data_inicio >= start_dt, Agendamento.data_inicio <= end_dt
        )

    agendamentos = query.all()
    eventos = []

    for a in agendamentos:
        cliente = a.chamado.cliente
        endereco = ""
        if cliente:
            partes = [cliente.logradouro or ""]
            if cliente.numero:
                partes.append(f", {cliente.numero}")
            if cliente.complemento:
                partes.append(f" ({cliente.complemento})")
            if cliente.bairro:
                partes.append(f" - {cliente.bairro}")
            if cliente.cidade:
                partes.append(f" - {cliente.cidade}/{cliente.uf if cliente.uf else ''}")
            endereco = "".join(partes)

        # Lógica de Atraso
        now = arrow.now().naive
        is_delayed = a.status == "Agendado" and a.data_fim < now

        color = "#10B981"  # Verde (Realizado)
        if a.status == "Agendado":
            color = (
                "#F59E0B" if is_delayed else "#3B82F6"
            )  # Laranja (Atrasado) ou Azul (Agendado)

        eventos.append(
            {
                "id": a.id,
                "resourceId": a.tecnico_id,  # Vincula o evento à coluna do técnico
                "title": f"#{a.chamado.protocolo} - {cliente.nome_razao if cliente else 'S/C'}",
                "start": a.data_inicio.isoformat(),
                "end": a.data_fim.isoformat(),
                "color": color,
                "extendedProps": {
                    "protocolo": a.chamado.protocolo,
                    "assunto": a.chamado.assunto,
                    "cliente": cliente.nome_razao if cliente else "Não informado",
                    "bairro": cliente.bairro if (cliente and cliente.bairro) else "",
                    "cidade": cliente.cidade if (cliente and cliente.cidade) else "",
                    "endereco": endereco,
                    "tecnico": a.tecnico.username,
                    "status": "Atrasado" if is_delayed else a.status,
                    "is_delayed": is_delayed,
                    "chamado_id": a.chamado_id,
                },
            }
        )

    return jsonify(eventos)


@agenda_bp.route("/agenda/agendar", methods=["POST"])
@login_required
def agendar():
    chamado_id = request.form.get("chamado_id")
    inicio_str = request.form.get("data_inicio")
    fim_str = request.form.get("data_fim")

    if not all([chamado_id, inicio_str, fim_str]):
        flash("Dados incompletos para agendamento.", "error")
        return redirect(url_for("agenda.calendario"))

    tecnico_id = request.form.get("tecnico_id") or current_user.id

    inicio = arrow.get(inicio_str).datetime
    fim = arrow.get(fim_str).datetime

    # Verificar se o chamado já possui agendamento ativo
    agendamento_existente = (
        Agendamento.query.filter_by(chamado_id=chamado_id)
        .filter(Agendamento.status != "Cancelado")
        .first()
    )

    if agendamento_existente:
        flash("Este chamado já possui um agendamento ativo.", "error")
        return redirect(url_for("agenda.calendario"))

    # Verificar conflito
    tecnico = db.session.get(Usuario, tecnico_id)
    if verificar_conflito(tecnico_id, inicio, fim):
        flash(
            f"Conflito de horário detectado para o técnico {tecnico.nome if tecnico else ''}.",
            "error",
        )
        return redirect(url_for("agenda.calendario"))

    # Criar Agendamento
    novo_agendamento = Agendamento(
        chamado_id=chamado_id,
        tecnico_id=tecnico_id,
        data_inicio=inicio,
        data_fim=fim,
        created_by=current_user.id,
    )

    # Atualizar Chamado para "Agendado"
    chamado = db.session.get(Chamado, chamado_id)
    if chamado:
        chamado.status = "Agendado"

        # Registrar na Timeline
        evento = Andamento(
            chamado_id=chamado.id,
            usuario_id=current_user.id,
            texto=f"Visita agendada para {inicio.strftime('%d/%m/%Y %H:%M')}.",
            tipo="Evento",
        )
        db.session.add(evento)

    db.session.add(novo_agendamento)
    db.session.commit()

    flash("Visita agendada com sucesso!", "success")
    return redirect(url_for("agenda.calendario"))


@agenda_bp.route("/agenda/finalizar/<id>", methods=["POST"])
@login_required
def finalizar_visita(id):
    agendamento = db.get_or_404(Agendamento, id)
    relatorio = request.form.get("relatorio")

    if not relatorio:
        flash("O relatório da visita é obrigatório.", "error")
        return redirect(url_for("agenda.calendario"))

    # 1. Finalizar Agendamento
    agendamento.status = "Realizado"

    # 2. Registrar Relatório na Timeline
    andamento = Andamento(
        chamado_id=agendamento.chamado_id,
        usuario_id=current_user.id,
        texto=f"RELATÓRIO DE VISITA: {relatorio}",
        tipo="Resposta",
    )
    db.session.add(andamento)

    # 3. Finalizar Chamado (Combo)
    chamado = agendamento.chamado
    chamado.status = "Fechado"

    # Evento de encerramento automático
    evento_fim = Andamento(
        chamado_id=chamado.id,
        usuario_id=current_user.id,
        texto="Chamado encerrado automaticamente após conclusão da visita técnica.",
        tipo="Evento",
    )
    db.session.add(evento_fim)

    db.session.commit()

    flash("Visita e Chamado finalizados com sucesso!", "success")
    return redirect(url_for("agenda.calendario"))


@agenda_bp.route("/agenda/api/reagendar/<id>", methods=["POST"])
@login_required
def api_reagendar(id):
    agendamento = db.session.get(Agendamento, id)
    if not agendamento:
        return jsonify({"success": False, "message": "Agendamento não encontrado"}), 404

    if agendamento.status != "Agendado":
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Não é possível reagendar uma visita com status: {agendamento.status}",
                }
            ),
            400,
        )

    data = request.get_json()
    if not data or "start" not in data or "end" not in data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    nova_data_inicio = arrow.get(data["start"]).datetime
    nova_data_fim = arrow.get(data["end"]).datetime

    resource_id = data.get("resourceId")
    tecnico_id = resource_id if resource_id else agendamento.tecnico_id

    # Verificar conflito
    if verificar_conflito(tecnico_id, nova_data_inicio, nova_data_fim, ignorar_id=id):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Conflito de horário detectado para o técnico selecionado.",
                }
            ),
            400,
        )

    # Identificar se houve troca de técnico para log
    trocou_tecnico = False
    if tecnico_id != agendamento.tecnico_id:
        trocou_tecnico = True
        novo_tecnico = db.session.get(Usuario, tecnico_id)

    # Atualizar Agendamento
    agendamento.data_inicio = nova_data_inicio
    agendamento.data_fim = nova_data_fim
    agendamento.tecnico_id = tecnico_id

    # Registrar na Timeline
    texto_log = f"Visita REAGENDADA para {nova_data_inicio.strftime('%d/%m/%Y %H:%M')}."
    if trocou_tecnico:
        texto_log += f" Técnico alterado para: {novo_tecnico.nome}."

    andamento = Andamento(
        chamado_id=agendamento.chamado_id,
        usuario_id=current_user.id,
        texto=texto_log,
        tipo="Evento",
        created_by=current_user.id,
    )
    db.session.add(andamento)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Erro ao salvar: {str(e)}"}), 500

    return jsonify({"success": True, "message": texto_log})


@agenda_bp.route("/gerar_os/<chamado_id>")
@login_required
def baixar_os(chamado_id):
    from App.Modulos.Chamados.modelo import Chamado
    from App.Modulos.Agenda.modelo import Agendamento

    chamado = db.get_or_404(Chamado, chamado_id)
    # Tenta pegar o último agendamento vinculado, se houver
    visita = (
        Agendamento.query.filter_by(chamado_id=chamado_id)
        .order_by(Agendamento.data_inicio.desc())
        .first()
    )

    hoje = arrow.now().format("DD/MM/YYYY HH:mm")

    from App.Modulos.Administracao.modelo import Configuracao

    cfg = Configuracao.get_config()

    return render_template(
        "ordem_servico_print.html", chamado=chamado, visita=visita, hoje=hoje, cfg=cfg
    )
