from datetime import datetime, timedelta
from App.banco import db


def encerrar_chamados_pendentes_excedidos():
    """
    Localiza chamados em status 'Pendente' que não tiveram interação por mais de 48 horas
    e os encerra automaticamente.
    """
    from App.Modulos.Chamados.modelo import Chamado, Andamento
    from flask import current_app

    limite = datetime.now() - timedelta(hours=48)

    # Busca chamados pendentes
    pendentes = Chamado.query.filter_by(status="Pendente").all()
    encerrados_count = 0

    for chamado in pendentes:
        # Pega a última interação
        ultima_interacao = (
            Andamento.query.filter_by(chamado_id=chamado.id)
            .order_by(Andamento.created_at.desc())
            .first()
        )

        if ultima_interacao and ultima_interacao.created_at < limite:
            # Encerra o chamado
            chamado.status = "Fechado"

            # Registra o evento de sistema
            evento = Andamento(
                chamado_id=chamado.id,
                usuario_id=1,  # ID do Sistema/Admin geralmente é 1
                texto="Encerrado automaticamente pelo sistema por falta de interação do cliente (excedido 48h).",
                tipo="Evento",
                created_by=1,
            )

            db.session.add(evento)
            encerrados_count += 1
            current_app.logger.info(
                f"Chamado #{chamado.protocolo} encerrado automaticamente."
            )

    if encerrados_count > 0:
        db.session.commit()

    return encerrados_count
