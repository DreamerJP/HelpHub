def verificar_conflito(tecnico_id, inicio, fim, ignorar_id=None):
    """
    Verifica se já existe agendamento para o técnico no intervalo.
    Retorna True se houver conflito.
    """
    from sqlalchemy import text
    from App.banco import db

    sql = """
        SELECT COUNT(*) FROM agendamentos 
        WHERE tecnico_id = :tecnico_id 
        AND status != 'Cancelado'
        AND data_inicio < :fim 
        AND data_fim > :inicio
    """
    params = {"tecnico_id": tecnico_id, "inicio": inicio, "fim": fim}

    if ignorar_id:
        sql += " AND id != :ignorar_id"
        params["ignorar_id"] = ignorar_id

    result = db.session.execute(text(sql), params).scalar()
    return result > 0
