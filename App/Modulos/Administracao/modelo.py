from datetime import datetime, timezone
from App.banco import db
from App.base_model import BaseModel


class Configuracao(BaseModel):
    __tablename__ = "configuracoes"

    # Dados da Empresa para a OS
    empresa_nome = db.Column(db.String(100), default="Minha Empresa")
    empresa_cnpj = db.Column(db.String(20), nullable=True)
    empresa_email = db.Column(db.String(120), nullable=True)
    empresa_telefone = db.Column(db.String(20), nullable=True)
    empresa_endereco = db.Column(db.String(200), nullable=True)
    empresa_logo = db.Column(db.String(255), nullable=True)  # Caminho relativo da logo

    # Configurações de Notificação - Telegram
    telegram_token = db.Column(db.String(100), nullable=True)
    telegram_chat_id = db.Column(
        db.String(50), nullable=True
    )  # Chat ID padrão (opcional)
    telegram_ativo = db.Column(db.Boolean, default=False)

    # Configurações de Notificação - Email (SMTP)
    email_smtp_server = db.Column(db.String(100), nullable=True)
    email_smtp_port = db.Column(db.Integer, default=587)
    email_user = db.Column(db.String(100), nullable=True)
    email_password = db.Column(db.String(100), nullable=True)
    email_ativo = db.Column(db.Boolean, default=False)

    # Configurações de Notificação - WhatsApp (Placeholder para futuro)
    whatsapp_api_url = db.Column(db.String(255), nullable=True)
    whatsapp_key = db.Column(db.String(255), nullable=True)
    whatsapp_ativo = db.Column(db.Boolean, default=False)

    @staticmethod
    def get_config():
        """Retorna a primeira configuração ou cria uma padrão se não existir."""
        cfg = Configuracao.query.first()
        if not cfg:
            cfg = Configuracao()
            cfg.save()
        return cfg

    def __repr__(self):
        return f"<Configuracao {self.empresa_nome}>"


class TarefaMonitor(BaseModel):
    __tablename__ = "tarefas_monitor"

    tarefa_id = db.Column(
        db.String(50), unique=True, nullable=False
    )  # Ex: 'backup_diario'
    nome_amigavel = db.Column(db.String(100))
    ultima_execucao = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # 'Sucesso', 'Erro', 'Aviso'
    mensagem = db.Column(db.Text)  # Detalhes do erro ou sucesso
    prox_vencimento = db.Column(db.DateTime, nullable=True)  # Quando ela DEVERIA rodar

    @staticmethod
    def atualizar(tarefa_id, nome, status, mensagem, prox_venc=None):
        """Atualiza ou cria o registro de monitoramento de uma tarefa."""
        task = TarefaMonitor.query.filter_by(tarefa_id=tarefa_id).first()
        if not task:
            task = TarefaMonitor(tarefa_id=tarefa_id)

        task.nome_amigavel = nome
        task.ultima_execucao = datetime.now(timezone.utc)
        task.status = status
        task.mensagem = mensagem
        if prox_venc:
            task.prox_vencimento = prox_venc

        task.save()
        return task


class SyncControl(BaseModel):
    """
    CONTROLE DE SINCRONIZAÇÃO GLOBAL (HelpHub Live System)
    Este modelo gerencia a versão dos dados no banco.
    Sempre que um chamado ou registro crítico muda, a versão é incrementada.
    """

    __tablename__ = "sync_control"

    entidade = db.Column(
        db.String(50), unique=True, nullable=False
    )  # Ex: 'chamados', 'clientes'
    versao = db.Column(db.Integer, default=1)
    ultima_mudanca = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @classmethod
    def incrementar(cls, entidade):
        """
        Incrementa a versão de uma entidade para forçar o recarregamento nos clientes.
        --- UPGRADE PATH ---
        Se no futuro desejar sincronização por milissegundos via WebSockets (Pusher):
        Basta disparar o evento do Pusher logo após o incremento desta versão.
        """
        registro = cls.query.filter_by(entidade=entidade).first()
        if not registro:
            registro = cls(entidade=entidade, versao=1)
            db.session.add(registro)
        else:
            registro.versao += 1

        db.session.commit()
        return registro.versao

    @classmethod
    def get_versao(cls, entidade):
        """Retorna a versão atual de uma entidade."""
        reg = cls.query.filter_by(entidade=entidade).first()
        return reg.versao if reg else 1
