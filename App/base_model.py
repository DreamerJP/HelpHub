from .banco import db
from datetime import datetime, timezone
import arrow


# Usamos o decorator nos campos de auditoria


import uuid


class BaseModel(db.Model):
    """
    Classe Abstrata Base para todos os modelos do HelpHub 4.0.
    Adiciona automaticamente campos de auditoria e métodos úteis.
    """

    __abstract__ = True

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Sempre salvamos em UTC no banco para evitar dores de cabeça,
    # mas a aplicação converte para America/Sao_Paulo na exibição.
    # Ou, conforme planejamento, forçamos o timezone na criação.
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Auditoria de Autoria
    created_by = db.Column(db.String(36), nullable=True)  # UUID do usuário
    updated_by = db.Column(db.String(36), nullable=True)  # UUID do usuário

    # Rastreabilidade
    audit_ip = db.Column(db.String(45), nullable=True)  # Suporta IPv6

    def save(self):
        """Salva a instância no banco de dados."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        """Remove a instância do banco de dados."""
        db.session.delete(self)
        db.session.commit()

    @property
    def created_at_br(self):
        """Retorna a data de criação formatada em Timezone BR."""
        if self.created_at:
            return (
                arrow.get(self.created_at)
                .to("America/Sao_Paulo")
                .format("DD/MM/YYYY HH:mm:ss")
            )
        return None
