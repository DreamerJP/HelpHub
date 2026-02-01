from wtforms import StringField, TextAreaField, SelectField, FileField
from wtforms.validators import DataRequired, Length, Optional
from App.base_form import AppBaseForm
from App.Modulos.Departamentos.modelo import Departamento
from App.Modulos.Clientes.modelo import Cliente


class ChamadoForm(AppBaseForm):
    cliente_id = SelectField("Cliente", validators=[DataRequired()])
    departamento_id = SelectField("Departamento", validators=[Optional()])
    assunto = StringField("Assunto", validators=[DataRequired(), Length(max=150)])
    descricao = TextAreaField("Descrição Detalhada", validators=[DataRequired()])
    prioridade = SelectField(
        "Prioridade",
        choices=[
            ("Baixa", "Baixa"),
            ("Normal", "Normal"),
            ("Alta", "Alta"),
            ("Critica", "Crítica"),
        ],
        default="Normal",
    )

    def __init__(self, *args, **kwargs):
        super(ChamadoForm, self).__init__(*args, **kwargs)
        # Popula choices dinamicamente
        self.cliente_id.choices = [
            (c.id, f"{c.nome_razao} ({c.cpf_cnpj})")
            for c in Cliente.query.filter_by(ativo=True)
            .order_by(Cliente.nome_razao)
            .all()
        ]
        self.cliente_id.choices.insert(
            0, ("", "")
        )  # Opção vazia para o TomSelect placeholder

        self.departamento_id.choices = [
            (d.id, d.nome) for d in Departamento.query.filter_by(ativo=True).all()
        ]
        self.departamento_id.choices.insert(0, ("", "--- Triagem Geral ---"))


class AndamentoForm(AppBaseForm):
    texto = TextAreaField("Nova Interação / Resposta", validators=[DataRequired()])
    novo_status = SelectField(
        "Alterar Status para",
        choices=[
            ("", "Manter Atual"),
            ("Aberto", "Aberto"),
            ("Agendado", "Agendado (Agendar Visita)"),
            ("Pendente", "Pendente (Aguardando Cliente)"),
            ("Escalonado", "Escalonado (Nível Superior)"),
            ("Fechado", "Encerrar Chamado"),
        ],
        validators=[Optional()],
    )

    anexo = FileField("Anexar Arquivo (PDF, Imagem, Doc)", validators=[Optional()])

    # Campos para Agendamento (Surgem se status for Agendado)
    data_inicio = StringField("Início da Visita", validators=[Optional()])
    data_fim = StringField("Fim Estimado", validators=[Optional()])
    instrucoes_tecnicas = TextAreaField(
        "Instruções Técnicas / Tarefa", validators=[Optional()]
    )
