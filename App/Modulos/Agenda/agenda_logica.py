def verificar_conflito(tecnico_id, inicio, fim, ignorar_id=None):
    """
    Verifica se já existe agendamento para o técnico no intervalo.
    Retorna True se houver conflito.
    """
    from sqlalchemy import text
    from App.banco import db
    import arrow

    # Normaliza e limpa precision (importante para SQLite)
    # Convertemos para naive (sem fuso horário) e zeramos segundos/milissegundos
    inicio_norm = arrow.get(inicio).replace(second=0, microsecond=0).naive
    fim_norm = arrow.get(fim).replace(second=0, microsecond=0).naive

    if inicio_norm >= fim_norm:
        return True

    # Convertemos para a string ISO sem fuso horário
    inicio_str = inicio_norm.strftime("%Y-%m-%d %H:%M:%S")
    fim_str = fim_norm.strftime("%Y-%m-%d %H:%M:%S")

    # A lógica 'data_inicio < :fim AND data_fim > :inicio' em strings ISO no SQLite
    # funciona perfeitamente para detectar sobreposição.
    # Usamos strftime para garantir que o SQLite compare strings LIMPAS (sem +00:00)
    sql = """
        SELECT COUNT(*) FROM agendamentos 
        WHERE tecnico_id = :tecnico_id 
        AND status != 'Cancelado'
        AND strftime('%Y-%m-%d %H:%M:%S', data_inicio) < :fim_str 
        AND strftime('%Y-%m-%d %H:%M:%S', data_fim) > :inicio_str
    """
    params = {
        "tecnico_id": tecnico_id,
        "inicio_str": inicio_str,
        "fim_str": fim_str
    }

    if ignorar_id:
        sql += " AND id != :ignorar_id"
        params["ignorar_id"] = str(ignorar_id)

    result = db.session.execute(text(sql), params).scalar()
    return result > 0
