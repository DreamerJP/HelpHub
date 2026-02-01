from App.banco import db
from App.base_model import BaseModel
from datetime import datetime


class Chamado(BaseModel):
    __tablename__ = "chamados"

    protocolo = db.Column(db.String(20), unique=True, nullable=False)
    assunto = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)

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

    andamentos = db.relationship(
        "Andamento",
        backref="chamado",
        cascade="all, delete-orphan",
        order_by="Andamento.created_at.desc()",
    )

    def gerar_protocolo(self):
        """Gera protocolo único baseado no Ano + ID sequencial ou UUID encurtado."""
        import uuid

        agora = datetime.now()
        # Ex: 20260129-A1B2
        self.protocolo = f"{agora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"


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

    usuario = db.relationship("Usuario")

    def __repr__(self):
        return f"<Andamento {self.id} - Chamado {self.chamado_id}>"
