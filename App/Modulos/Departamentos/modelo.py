from App.banco import db
from App.base_model import BaseModel


class Departamento(BaseModel):
    __tablename__ = "departamentos"

    nome = db.Column(db.String(64), unique=True, nullable=False)
    email_notificacao = db.Column(db.String(120), nullable=True)
    descricao = db.Column(db.String(255), nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Departamento {self.nome}>"
