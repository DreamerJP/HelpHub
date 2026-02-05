from datetime import datetime, timedelta, timezone
from App.banco import db
from flask import current_app


class ChamadoService:
    """
    Motor Central de Inteligência para Chamados e Integração com Agenda.
    Centraliza regras de negócio, mudanças de status e logs de auditoria.
    """

    @staticmethod
    def registrar_interacao(
        chamado_id,
        usuario_id,
        texto=None,
        tipo="Nota",
        novo_status=None,
        anexo=None,
        dados_agendamento=None,  # Novo: dict com {inicio, fim, tecnico_id, instrucoes}
    ):
        """
        Registra uma nova interação no chamado e processa regras de integração.
        """
        from App.Modulos.Chamados.modelo import Chamado, Andamento
        from App.Modulos.Autenticacao.modelo import Usuario

        chamado = db.session.get(Chamado, chamado_id)
        usuario = db.session.get(Usuario, usuario_id)

        if not chamado:
            return False, "Chamado não encontrado."

        if chamado.status == "Fechado" and novo_status != "Aberto":
            return False, "Não é possível interagir em um chamado fechado."

        # 1. Processar Mudança de Status se houver
        if novo_status and novo_status != chamado.status:
            velho_status = chamado.status

            # Regra Crítica: Se for "Agendado", precisamos criar o registro na agenda primeiro
            if novo_status == "Agendado":
                if not dados_agendamento:
                    return (
                        False,
                        "É necessário preencher os dados de agendamento para este status.",
                    )

                from App.Modulos.Agenda.modelo import Agendamento
                from App.Modulos.Agenda.agenda_logica import verificar_conflito

                inicio = dados_agendamento.get("inicio")
                fim = dados_agendamento.get("fim")
                tecnico_agendado_id = dados_agendamento.get("tecnico_id") or usuario_id

                if inicio and fim:
                    if not verificar_conflito(tecnico_agendado_id, inicio, fim):
                        visita = Agendamento(
                            chamado_id=chamado.id,
                            tecnico_id=tecnico_agendado_id,
                            data_inicio=inicio,
                            data_fim=fim,
                            instrucoes_tecnicas=dados_agendamento.get("instrucoes"),
                            created_by=usuario_id,
                        )
                        db.session.add(visita)
                        # O técnico do chamado passa a ser o técnico agendado
                        chamado.tecnico_id = tecnico_agendado_id
                    else:
                        return (
                            False,
                            "Conflito na agenda do técnico. Escolha outro horário.",
                        )
                else:
                    return (
                        False,
                        "Datas de início e fim são obrigatórias para agendamento.",
                    )

            chamado.status = novo_status

            # Log de Mudança de Status como Evento
            evento_status = Andamento(
                chamado_id=chamado.id,
                usuario_id=usuario_id,
                texto=f"Alterou status de {velho_status} para {novo_status}.",
                tipo="Evento",
                created_by=usuario_id,
            )
            db.session.add(evento_status)

            # Regra: Se fechar o chamado, cancelar visitas pendentes
            if novo_status == "Fechado":
                ChamadoService.cancelar_visitas_pendentes(chamado_id, usuario_id)

            # Regra: Se escalonar, remover técnico atual
            if novo_status == "Escalonado":
                chamado.tecnico_id = None

        # 2. Auto-atribuição Inteligente (Se não for Admin e o chamado estiver sem técnico)
        if not chamado.tecnico_id and usuario and not usuario.is_admin:
            chamado.tecnico_id = usuario_id
            evento_atribuicao = Andamento(
                chamado_id=chamado.id,
                usuario_id=usuario_id,
                texto=f"Chamado atribuído automaticamente ao técnico {usuario.nome}.",
                tipo="Evento",
                created_by=usuario_id,
            )
            db.session.add(evento_atribuicao)

        # 3. Registrar o Andamento (Resposta/Nota) se houver texto
        if texto:
            andamento = Andamento(
                chamado_id=chamado_id,
                usuario_id=usuario_id,
                texto=texto,
                tipo=tipo,
                anexo=anexo,
                created_by=usuario_id,
            )
            db.session.add(andamento)

        try:
            db.session.commit()
            return True, "Interação registrada com sucesso."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao registrar interação: {e}")
            return False, f"Erro interno: {str(e)}"

    @staticmethod
    def finalizar_visita(agendamento_id, usuario_id, relatorio):
        """
        Finaliza uma visita técnica e consequentemente encerra o chamado.
        """
        from App.Modulos.Agenda.modelo import Agendamento
        from App.Modulos.Chamados.modelo import Andamento

        agendamento = db.session.get(Agendamento, agendamento_id)
        if not agendamento or agendamento.status != "Agendado":
            return False, "Agendamento inválido ou já finalizado."

        # 1. Atualizar Agendamento
        agendamento.status = "Realizado"

        # 2. Registrar na Timeline via registrar_interacao para garantir consistência
        # Montamos o texto do relatório
        inicio_f = agendamento.data_inicio.strftime("%d/%m/%Y %H:%M")
        fim_f = (
            agendamento.data_fim.strftime("%H:%M")
            if agendamento.data_inicio.date() == agendamento.data_fim.date()
            else agendamento.data_fim.strftime("%d/%m/%Y %H:%M")
        )

        texto_visita = (
            f"VISITA TÉCNICA REALIZADA\n"
            f"Período Planejado: {inicio_f} até {fim_f}\n\n"
            f"RELATÓRIO: {relatorio}"
        )

        success, msg = ChamadoService.registrar_interacao(
            chamado_id=agendamento.chamado_id,
            usuario_id=usuario_id,
            texto=texto_visita,
            tipo="Resposta",
            novo_status="Fechado",  # Visita finalizada = Chamado Fechado
        )

        if success:
            # Log extra de encerramento automático após visita
            evento_fim = Andamento(
                chamado_id=agendamento.chamado_id,
                usuario_id=usuario_id,
                texto="Chamado encerrado automaticamente após conclusão da visita técnica.",
                tipo="Evento",
                created_by=usuario_id,
            )
            db.session.add(evento_fim)
            db.session.commit()

        return success, msg

    @staticmethod
    def agendar_visita(
        chamado_id, tecnico_id, inicio, fim, usuario_id, instrucoes=None
    ):
        """
        Cria um novo agendamento, valida conflitos e registra na timeline.
        """
        from App.Modulos.Agenda.modelo import Agendamento
        from App.Modulos.Agenda.agenda_logica import verificar_conflito
        from App.Modulos.Autenticacao.modelo import Usuario

        if inicio >= fim:
            return False, "A data de término deve ser posterior à de início."

        # Bloqueio de duplicata: Verifica se já existe um agendamento ativo para este chamado
        agendamento_ativo = Agendamento.query.filter_by(
            chamado_id=chamado_id, status="Agendado"
        ).first()
        if agendamento_ativo:
            return False, "Este chamado já possui um agendamento ativo no calendário."

        if verificar_conflito(tecnico_id, inicio, fim):
            tecnico = db.session.get(Usuario, tecnico_id)
            nome_tec = tecnico.nome if tecnico else "técnico"
            return False, f"Conflito de horário detectado para o técnico {nome_tec}."

        # 1. Criar Agendamento
        novo_agendamento = Agendamento(
            chamado_id=chamado_id,
            tecnico_id=tecnico_id,
            data_inicio=inicio,
            data_fim=fim,
            instrucoes_tecnicas=instrucoes,
            created_by=usuario_id,
        )
        db.session.add(novo_agendamento)

        # Atualizar o técnico principal do chamado (Assumir a OS)
        from App.Modulos.Chamados.modelo import Chamado

        chamado = db.session.get(Chamado, chamado_id)
        if chamado:
            chamado.tecnico_id = tecnico_id

        # 2. Registrar na Timeline
        tecnico = db.session.get(Usuario, tecnico_id)
        ChamadoService.registrar_interacao(
            chamado_id=chamado_id,
            usuario_id=usuario_id,
            novo_status="Agendado",
            texto=f"Visita AGENDADA para {inicio.strftime('%d/%m/%Y %H:%M')} (Técnico: {tecnico.nome if tecnico else 'N/I'}).",
            tipo="Evento",
        )

        try:
            db.session.commit()
            return True, "Visita agendada com sucesso."
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def reagendar_visita(
        agendamento_id, nova_data_inicio, nova_data_fim, tecnico_id, usuario_id
    ):
        """
        Atualiza um agendamento existente (arrastar ou editar manual).
        """
        from App.Modulos.Agenda.modelo import Agendamento
        from App.Modulos.Agenda.agenda_logica import verificar_conflito
        from App.Modulos.Autenticacao.modelo import Usuario

        agendamento = db.session.get(Agendamento, agendamento_id)
        if not agendamento:
            return False, "Agendamento não encontrado."

        if agendamento.status != "Agendado":
            return (
                False,
                f"Não é possível reagendar uma visita com status: {agendamento.status}",
            )

        # Verificar conflito
        if verificar_conflito(
            tecnico_id, nova_data_inicio, nova_data_fim, ignorar_id=agendamento_id
        ):
            return False, "Conflito de horário detectado para o técnico selecionado."

        # Identificar se houve troca de técnico para log
        trocou_tecnico = False
        tecnico_final_id = tecnico_id if tecnico_id else agendamento.tecnico_id
        novo_tecnico = None

        if tecnico_final_id != agendamento.tecnico_id:
            trocou_tecnico = True
            novo_tecnico = db.session.get(Usuario, tecnico_final_id)

        # Atualizar
        agendamento.data_inicio = nova_data_inicio
        agendamento.data_fim = nova_data_fim
        agendamento.tecnico_id = tecnico_final_id

        # Registrar na Timeline
        texto_log = (
            f"Visita REAGENDADA para {nova_data_inicio.strftime('%d/%m/%Y %H:%M')}."
        )
        if trocou_tecnico and novo_tecnico:
            texto_log += f" Técnico alterado para: {novo_tecnico.username}."

        ChamadoService.registrar_interacao(
            chamado_id=agendamento.chamado_id,
            usuario_id=usuario_id,
            texto=texto_log,
            tipo="Evento",
        )

        try:
            db.session.commit()
            return True, texto_log
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def cancelar_visitas_pendentes(chamado_id, usuario_id):
        """
        Localiza e cancela qualquer visita agendada para o chamado.
        """
        from App.Modulos.Agenda.modelo import Agendamento
        from App.Modulos.Chamados.modelo import Andamento

        visitas_pendentes = Agendamento.query.filter_by(
            chamado_id=chamado_id, status="Agendado"
        ).all()

        for v in visitas_pendentes:
            v.status = "Cancelado"
            log_cancel = Andamento(
                chamado_id=chamado_id,
                usuario_id=usuario_id,
                texto=f"Agendamento ({v.data_inicio.strftime('%d/%m/%Y')}) cancelado automaticamente devido ao fechamento ou alteração do chamado.",
                tipo="Evento",
                created_by=usuario_id,
            )
            db.session.add(log_cancel)

        return len(visitas_pendentes)

    @staticmethod
    def retratar_andamento(andamento_id, usuario_id):
        """
        Permite que o autor de um andamento o retrate (anule) dentro de um limite de tempo.
        """
        from App.Modulos.Chamados.modelo import Andamento
        from datetime import timezone

        andamento = db.session.get(Andamento, andamento_id)
        if not andamento:
            return False, "Andamento não encontrado."

        if andamento.usuario_id != usuario_id:
            return False, "Apenas o autor pode retratar este andamento."

        if andamento.foi_retratado:
            return False, "Este andamento já foi retratado."

        # Limite de 10 minutos para retratação
        agora = datetime.now(timezone.utc)
        diferenca = agora - andamento.created_at.replace(tzinfo=timezone.utc)

        if diferenca.total_seconds() > 600:  # 10 minutos
            return False, "O tempo limite para retratação (10 min) expirou."

        # Remove anexo físico do servidor se existir
        if andamento.anexo:
            try:
                from flask import current_app
                import os

                upload_path = current_app.config.get("UPLOAD_FOLDER")
                if upload_path:
                    # O anamento.anexo já guarda o caminho relativo (ex: Clientes/uuid/2026/arquivo.jpg)
                    file_full_path = os.path.join(upload_path, andamento.anexo)
                    if os.path.exists(file_full_path):
                        os.remove(file_full_path)
                        # Removemos a referência no banco também para limpar o rastro
                        andamento.anexo = None
            except Exception as e:
                # Não bloqueamos a retratação se a deleção do arquivo falhar, apenas logamos
                from flask import current_app

                current_app.logger.error(f"Falha ao deletar anexo físico: {str(e)}")

        andamento.foi_retratado = True

        try:
            db.session.commit()
            return True, "Andamento retratado com sucesso."
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def anular_visita(agendamento_id, usuario_id):
        """
        Anula manualmente um agendamento específico e ajusta o status do chamado.
        """
        from App.Modulos.Agenda.modelo import Agendamento
        from App.Modulos.Chamados.modelo import Chamado

        agendamento = db.session.get(Agendamento, agendamento_id)
        if not agendamento:
            return False, "Agendamento não encontrado."

        if agendamento.status != "Agendado":
            return False, "Apenas visitas agendadas podem ser anuladas."

        chamado_id = agendamento.chamado_id
        data_f = agendamento.data_inicio.strftime("%d/%m/%Y")

        # 1. Marcar como Cancelado
        agendamento.status = "Cancelado"

        # 2. Registrar na Timeline
        ChamadoService.registrar_interacao(
            chamado_id=chamado_id,
            usuario_id=usuario_id,
            texto=f"Agendamento ({data_f}) anulado manualmente via agenda.",
            tipo="Evento",
        )

        # 3. Se não houver outros agendamentos ativos, voltar status do chamado para Aberto
        outros_ativos = Agendamento.query.filter_by(
            chamado_id=chamado_id, status="Agendado"
        ).count()
        if outros_ativos == 0:
            chamado = db.session.get(Chamado, chamado_id)
            if chamado and chamado.status == "Agendado":
                chamado.status = "Aberto"

        try:
            db.session.commit()
            return True, "Agendamento anulado com sucesso."
        except Exception as e:
            db.session.rollback()
            return False, str(e)


def encerrar_chamados_pendentes_excedidos():
    """
    Mantido para compatibilidade com o agendador de tarefas.
    Utiliza o ChamadoService para realizar o fechamento seguro.
    """
    from App.Modulos.Chamados.modelo import Chamado, Andamento

    limite = datetime.now(timezone.utc) - timedelta(hours=48)
    pendentes = Chamado.query.filter_by(status="Pendente").all()
    count = 0

    for chamado in pendentes:
        ultima = (
            Andamento.query.filter_by(chamado_id=chamado.id)
            .order_by(Andamento.created_at.desc())
            .first()
        )
        if ultima and ultima.created_at.replace(tzinfo=timezone.utc) < limite:
            ChamadoService.registrar_interacao(
                chamado_id=chamado.id,
                usuario_id=1,
                texto="Encerrado automaticamente pelo sistema por falta de interação do cliente (excedido 48h).",
                tipo="Evento",
                novo_status="Fechado",
            )
            count += 1

    return count
