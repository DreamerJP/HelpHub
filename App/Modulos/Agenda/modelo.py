from App.banco import db
from App.base_model import BaseModel


class Agendamento(BaseModel):
    __tablename__ = "agendamentos"

    chamado_id = db.Column(db.String(36), db.ForeignKey("chamados.id"), nullable=False)
    tecnico_id = db.Column(db.String(36), db.ForeignKey("usuarios.id"), nullable=False)

    data_inicio = db.Column(db.DateTime, nullable=False, index=True)
    data_fim = db.Column(db.DateTime, nullable=False, index=True)

    status = db.Column(
        db.String(20), default="Agendado", index=True
    )  # Agendado, Realizado, Cancelado

    instrucoes_tecnicas = db.Column(
        db.Text, nullable=True
    )  # O que deve ser feito na visita

    chamado = db.relationship("Chamado", backref="visitas")
    tecnico = db.relationship("Usuario", backref="visitas_agenda")

    def __repr__(self):
        return f"<Visita {self.id} - {self.data_inicio}>"
