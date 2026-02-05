from App.banco import db
from App.base_model import BaseModel


class Cliente(BaseModel):
    __tablename__ = "clientes"

    # Dados Pessoais / Empresariais
    nome_razao = db.Column(
        db.String(100, collation="NOCASE"), nullable=False, index=True
    )
    nome_fantasia = db.Column(
        db.String(100, collation="NOCASE"), nullable=True
    )  # Opcional se for PF
    cpf_cnpj = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # Contato
    email = db.Column(db.String(120), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)

    # Endereço
    cep = db.Column(db.String(10), nullable=True)
    logradouro = db.Column(db.String(150), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(60), nullable=True)
    cidade = db.Column(db.String(60), nullable=True)
    uf = db.Column(db.String(2), nullable=True)

    # Notas e Observações
    observacoes = db.Column(db.Text, nullable=True)

    ativo = db.Column(db.Boolean, default=True)

    # Relacionamentos
    documentos = db.relationship(
        "DocumentoCliente", backref="cliente", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Cliente {self.nome_razao}>"


class DocumentoCliente(BaseModel):
    __tablename__ = "documentos_clientes"

    cliente_id = db.Column(db.String(36), db.ForeignKey("clientes.id"), nullable=False)
    nome_original = db.Column(db.String(150), nullable=False)
    caminho = db.Column(
        db.String(255), nullable=False
    )  # Caminho relativo em Data/Uploads
    tipo = db.Column(db.String(50), nullable=True)  # Mime type ou extensão

    def __repr__(self):
        return f"<Documento {self.nome_original} - Cliente {self.cliente_id}>"
