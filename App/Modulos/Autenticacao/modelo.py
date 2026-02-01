from App.banco import db
from App.base_model import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class Usuario(BaseModel, UserMixin):
    __tablename__ = "usuarios"

    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default="Operador")  # 'Admin' ou 'Operador'

    # Campos pessoais básicos
    nome = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    ativo = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        """Cria o hash da senha usando salt automático (padrão pbkdf2 do Werkzeug)."""
        self.password_hash = generate_password_hash(password)

    @property
    def is_admin(self):
        return self.role == "Admin"

    def check_password(self, password):
        """Verifica se a senha bate com o hash salvo."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.username}>"
