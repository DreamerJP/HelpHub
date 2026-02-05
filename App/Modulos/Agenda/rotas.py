from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from App.Modulos.Agenda.modelo import Agendamento
from App.Modulos.Chamados.modelo import Chamado
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
    from App.Modulos.Chamados.servicos import ChamadoService

    chamado_id = request.form.get("chamado_id")
    inicio_str = request.form.get("data_inicio")
    fim_str = request.form.get("data_fim")
    tecnico_id = request.form.get("tecnico_id") or current_user.id
    instrucoes = request.form.get("instrucoes_tecnicas")

    if not all([chamado_id, inicio_str, fim_str]):
        flash("Dados incompletos para agendamento.", "error")
        return redirect(url_for("agenda.calendario"))

    # Normalização de Datas
    inicio = arrow.get(inicio_str).replace(second=0, microsecond=0).naive
    fim = arrow.get(fim_str).replace(second=0, microsecond=0).naive

    success, msg = ChamadoService.agendar_visita(
        chamado_id=chamado_id,
        tecnico_id=tecnico_id,
        inicio=inicio,
        fim=fim,
        usuario_id=current_user.id,
        instrucoes=instrucoes,
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "error")

    return redirect(url_for("agenda.calendario"))


@agenda_bp.route("/agenda/finalizar/<id>", methods=["POST"])
@login_required
def finalizar_visita(id):
    relatorio = request.form.get("relatorio")

    if not relatorio:
        flash("O relatório da visita é obrigatório.", "error")
        return redirect(url_for("agenda.calendario"))

    from App.Modulos.Chamados.servicos import ChamadoService

    success, msg = ChamadoService.finalizar_visita(
        agendamento_id=id, usuario_id=current_user.id, relatorio=relatorio
    )

    if success:
        flash("Visita e Chamado finalizados com sucesso!", "success")
    else:
        flash(f"Erro ao finalizar: {msg}", "error")

    return redirect(url_for("agenda.calendario"))


@agenda_bp.route("/agenda/api/reagendar/<id>", methods=["POST"])
@login_required
def api_reagendar(id):
    from App.Modulos.Chamados.servicos import ChamadoService

    data = request.get_json()
    if not data or "start" not in data or "end" not in data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    # Normalização
    nova_dt_inicio = arrow.get(data["start"]).replace(second=0, microsecond=0).naive
    nova_dt_fim = arrow.get(data["end"]).replace(second=0, microsecond=0).naive

    # Se trocar de coluna (técnico) no Drag & Drop
    resource_id = data.get("resourceId")

    success, msg = ChamadoService.reagendar_visita(
        agendamento_id=id,
        nova_data_inicio=nova_dt_inicio,
        nova_data_fim=nova_dt_fim,
        tecnico_id=resource_id,  # Se for None, o serviço manterá o atual no banco
        usuario_id=current_user.id,
    )

    if success:
        return jsonify({"success": True, "message": msg})
    else:
        return jsonify({"success": False, "message": msg}), 400


@agenda_bp.route("/agenda/api/cancelar/<id>", methods=["POST"])
@login_required
def api_cancelar(id):
    from App.Modulos.Chamados.servicos import ChamadoService

    success, msg = ChamadoService.anular_visita(
        agendamento_id=id, usuario_id=current_user.id
    )

    if success:
        return jsonify({"success": True, "message": msg})
    else:
        return jsonify({"success": False, "message": msg}), 400


@agenda_bp.route("/gerar_os/<chamado_id>")
@login_required
def baixar_os(chamado_id):
    from App.Modulos.Chamados.modelo import Chamado
    from App.Modulos.Agenda.modelo import Agendamento

    chamado = db.get_or_404(Chamado, chamado_id)
    # Prioriza a visita ATIVA (Agendado ou Em Andamento)
    visita = (
        Agendamento.query.filter(
            Agendamento.chamado_id == chamado_id,
            Agendamento.status.in_(["Agendado", "Em Andamento"])
        )
        .order_by(Agendamento.data_inicio.desc())
        .first()
    )

    # Se não houver ativa (ex: chamado já fechado), pega a última registrada
    if not visita:
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
