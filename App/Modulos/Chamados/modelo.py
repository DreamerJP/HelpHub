from App.banco import db
from App.base_model import BaseModel
from datetime import datetime, timezone


class Chamado(BaseModel):
    __tablename__ = "chamados"

    protocolo = db.Column(
        db.String(20, collation="NOCASE"), unique=True, nullable=False
    )
    assunto = db.Column(db.String(150, collation="NOCASE"), nullable=False)
    descricao = db.Column(db.Text(collation="NOCASE"), nullable=False)

    # Status (Workflow: A, B, C, D)
    # Aberto, Agendado, Pendente, Fechado, Escalonado
    status = db.Column(db.String(20), default="Aberto", index=True)
    prioridade = db.Column(db.String(20), default="Normal")

    # Chaves Estrangeiras
    cliente_id = db.Column(
        db.String(36), db.ForeignKey("clientes.id"), nullable=False, index=True
    )
    departamento_id = db.Column(
        db.String(36), db.ForeignKey("departamentos.id"), nullable=True
    )  # Pode ser null se for triagem geral
    tecnico_id = db.Column(
        db.String(36), db.ForeignKey("usuarios.id"), nullable=True, index=True
    )

    # Relacionamentos
    cliente = db.relationship("Cliente", backref="chamados")
    departamento = db.relationship("Departamento", backref="chamados")
    tecnico = db.relationship("Usuario", backref="chamados_atribuidos")
    visitas = db.relationship(
        "Agendamento", back_populates="chamado", cascade="all, delete-orphan"
    )

    andamentos = db.relationship(
        "Andamento",
        backref="chamado",
        cascade="all, delete-orphan",
        order_by="Andamento.created_at.desc()",
    )

    @property
    def proximo_agendamento(self):
        """Retorna a próxima visita agendada (data_inicio mais próxima)."""
        from App.Modulos.Agenda.modelo import Agendamento

        return (
            Agendamento.query.filter(
                Agendamento.chamado_id == self.id,
                Agendamento.status == "Agendado",
            )
            .order_by(Agendamento.data_inicio.asc())
            .first()
        )

    @classmethod
    def apply_sort(cls, query, field, order="asc"):
        """Override para ordenar prioridade por peso de urgencia."""
        if field == "prioridade":
            from sqlalchemy import case

            # Mapeamento de urgencia (Maior numero = Maior urgencia)
            ordem_urgencia = case(
                (cls.prioridade == "Crítica", 4),
                (cls.prioridade == "Alta", 3),
                (cls.prioridade == "Normal", 2),
                (cls.prioridade == "Baixa", 1),
                else_=0,
            )
            return (
                query.order_by(ordem_urgencia.desc())
                if order == "desc"
                else query.order_by(ordem_urgencia.asc())
            )

        # Ordenação por próximo agendamento
        if field == "proximo_agendamento":
            from sqlalchemy import select, func
            from App.Modulos.Agenda.modelo import Agendamento

            # Subquery que pega o MIN(data_inicio) para cada chamado
            subq = (
                select(
                    Agendamento.chamado_id,
                    func.min(Agendamento.data_inicio).label("proxima_data"),
                )
                .where(Agendamento.status == "Agendado")
                .group_by(Agendamento.chamado_id)
                .subquery()
            )

            # LEFT JOIN para incluir chamados sem agendamento (ficam no final)
            query = query.outerjoin(subq, cls.id == subq.c.chamado_id)

            # Ordena: NULLs vão para o final, depois ordena pela data
            if order == "desc":
                return query.order_by(subq.c.proxima_data.desc().nullslast())
            else:
                return query.order_by(subq.c.proxima_data.asc().nullslast())

        return super().apply_sort(query, field, order)

    def gerar_protocolo(self):
        """Gera protocolo único baseado no Ano + ID sequencial ou UUID encurtado."""
        import uuid

        agora = datetime.now(timezone.utc)
        # Ex: 20260129-A1B2C3D4E5
        # 10 caracteres para garantir unicidade absoluta (16^10 combinações por dia)
        self.protocolo = f"{agora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:10].upper()}"


class Andamento(BaseModel):
    __tablename__ = "andamentos"

    chamado_id = db.Column(
        db.String(36), db.ForeignKey("chamados.id"), nullable=False, index=True
    )
    usuario_id = db.Column(db.String(36), db.ForeignKey("usuarios.id"), nullable=False)

    texto = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), default="Nota")  # Nota, Resposta, Evento (Sistema)

    # Anexo (Caminho relativo do arquivo)
    anexo = db.Column(db.String(255), nullable=True)

    # Controle de Erros (Retratação)
    foi_retratado = db.Column(db.Boolean, default=False)

    usuario = db.relationship("Usuario")

    def __repr__(self):
        return f"<Andamento {self.id} - Chamado {self.chamado_id}>"
