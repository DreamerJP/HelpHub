from datetime import datetime
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
        task.ultima_execucao = datetime.now()
        task.status = status
        task.mensagem = mensagem
        if prox_venc:
            task.prox_vencimento = prox_venc

        task.save()
        return task
