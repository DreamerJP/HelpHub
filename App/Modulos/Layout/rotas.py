from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    current_app,
)
from flask_login import login_required
from sqlalchemy import or_
from App.Modulos.Chamados.modelo import Chamado
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Agenda.modelo import Agendamento
from App.banco import db
from datetime import datetime, timezone

layout_bp = Blueprint(
    "layout",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/layout",
)


@layout_bp.route("/")
@login_required
def index():
    from datetime import timedelta
    from App.Modulos.Departamentos.modelo import Departamento

    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Métricas principais
    total_abertos = Chamado.query.filter_by(status="Aberto").count()
    total_agendados = Chamado.query.filter_by(status="Agendado").count()
    total_pendentes = Chamado.query.filter_by(status="Pendente").count()
    total_clientes = Cliente.query.count()

    # Agendamentos de hoje - Queremos saber o progresso (X de Y)
    # Consulta otimizada: Agendamentos + Status do Chamado em um único JOIN
    todos_agendamentos_hoje = (
        db.session.query(Agendamento, Chamado.status)
        .outerjoin(Chamado, Agendamento.chamado_id == Chamado.id)
        .filter(
            Agendamento.data_inicio >= hoje,
            Agendamento.data_inicio < hoje + timedelta(days=1),
        )
        .order_by(Agendamento.data_inicio)
        .all()
    )

    total_hoje = len(todos_agendamentos_hoje)
    concluidos_hoje = len([r for r in todos_agendamentos_hoje if r.status == "Fechado"])
    agendamentos_lista = [r[0] for r in todos_agendamentos_hoje[:7]]
    remanescentes_agenda = max(0, total_hoje - 7)

    # Chamados recentes (últimos 5)
    chamados_recentes = Chamado.query.order_by(Chamado.created_at.desc()).limit(5).all()

    # Estatísticas por status para gráfico (Dinâmico)
    from sqlalchemy import func

    status_counts = (
        db.session.query(Chamado.status, func.count(Chamado.id))
        .group_by(Chamado.status)
        .all()
    )
    stats_status = {s[0]: s[1] for s in status_counts}

    # Garantir que os status principais existam no dicionário (mesmo que com zero)
    for s in ["Aberto", "Agendado", "Pendente", "Escalonado", "Fechado"]:
        if s not in stats_status:
            stats_status[s] = 0

    # Tendência (Chamados por dia) - Últimos 30 dias
    from sqlalchemy import func

    inicio_periodo = hoje - timedelta(days=29)

    # Query otimizada: Uma única consulta agrupada por data
    contagens = (
        db.session.query(
            func.date(Chamado.created_at).label("data"),
            func.count(Chamado.id).label("total"),
        )
        .filter(Chamado.created_at >= inicio_periodo)
        .group_by(func.date(Chamado.created_at))
        .all()
    )

    # Mapeamos o resultado para um dicionário para busca rápida { 'YYYY-MM-DD': total }
    mapa_contagens = {c.data: c.total for c in contagens}

    tendencia_ano = []
    for i in range(29, -1, -1):
        dia = hoje - timedelta(days=i)
        str_dia = dia.strftime("%Y-%m-%d")
        tendencia_ano.append(
            {
                "data": dia.strftime("%d/%m"),
                "iso": str_dia,
                "total": mapa_contagens.get(str_dia, 0),
            }
        )

    # Estatísticas por departamento (Otimizado: 1 Query)
    stats_departamentos_query = (
        db.session.query(Departamento.nome, func.count(Chamado.id))
        .join(Chamado, Departamento.id == Chamado.departamento_id)
        .filter(Departamento.ativo)
        .group_by(Departamento.nome)
        .all()
    )
    stats_departamentos = [
        {"nome": nome, "total": total} for nome, total in stats_departamentos_query
    ]

    return render_template(
        "dashboard.html",
        abertos=total_abertos,
        agendados=total_agendados,
        pendentes=total_pendentes,
        total_clientes=total_clientes,
        agendamentos_hoje=agendamentos_lista,
        agenda_total=total_hoje,
        agenda_concluidos=concluidos_hoje,
        agenda_remanescentes=remanescentes_agenda,
        chamados_recentes=chamados_recentes,
        stats_status=stats_status,
        tendencia_ano=tendencia_ano,
        stats_departamentos=stats_departamentos,
    )


@layout_bp.route("/buscar")
@login_required
def buscar():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("layout.index"))

    # Busca em Clientes
    clientes = Cliente.query.filter(
        or_(
            Cliente.nome_razao.ilike(f"%{query}%"), Cliente.cpf_cnpj.ilike(f"%{query}%")
        )
    ).all()

    # Busca em Chamados (Protocolo, Assunto ou Nome do Cliente)
    chamados = (
        Chamado.query.join(Cliente)
        .filter(
            or_(
                Chamado.protocolo.ilike(f"%{query}%"),
                Chamado.assunto.ilike(f"%{query}%"),
                Cliente.nome_razao.ilike(f"%{query}%"),
            )
        )
        .all()
    )

    # Busca em Agendamentos (pelo protocolo do chamado vinculado ou nome do cliente)
    agendamentos = (
        Agendamento.query.join(Chamado)
        .join(Cliente)
        .filter(
            or_(
                Chamado.protocolo.ilike(f"%{query}%"),
                Cliente.nome_razao.ilike(f"%{query}%"),
            )
        )
        .all()
    )

    return render_template(
        "resultado_busca.html",
        query=query,
        clientes=clientes,
        chamados=chamados,
        agendamentos=agendamentos,
    )


@layout_bp.route("/sync/check")
@login_required
def sync_check():
    """
    ENDPOINT DE SINCRONIZAÇÃO SILENCIOSA
    O frontend chama esta rota periodicamente para saber se algo mudou no banco.
    --- UPGRADE PATH (Pusher / WebSocket) ---
    Ao mudar para sincronização por milissegundos, este endpoint torna-se obsoleto,
    pois o servidor 'avisaria' o frontend via socket em vez do frontend 'perguntar'.
    """
    from App.Modulos.Administracao.modelo import SyncControl

    return {
        "chamados": SyncControl.get_versao("chamados"),
        "clientes": SyncControl.get_versao("clientes"),
        "usuarios": SyncControl.get_versao("usuarios"),
        "departamentos": SyncControl.get_versao("departamentos"),
    }


# Tratamento de Erros
@layout_bp.app_errorhandler(403)
def erro_403(e):
    return render_template("erro_403.html"), 403


@layout_bp.app_errorhandler(413)
def erro_413(e):
    return render_template("erro_413.html"), 413


@layout_bp.app_errorhandler(429)
def erro_429(e):
    return render_template("erro_429.html"), 429


@layout_bp.app_errorhandler(404)
def erro_404(e):
    return render_template("erro_404.html"), 404


@layout_bp.app_errorhandler(500)
def erro_500(e):
    return render_template("erro_500.html"), 500


@layout_bp.route("/uploads/<path:filename>")
@login_required
def servir_upload(filename):
    """Rota global para servir arquivos da pasta Data/Uploads"""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
