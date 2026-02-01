from flask import url_for
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Chamados.modelo import Chamado
from App.Modulos.Agenda.modelo import Agendamento
from App.Modulos.Administracao.modelo import Configuracao
from App.banco import db
import arrow


def test_impressao_os_html(client, app, admin_user):
    """Testa a geração da página de impressão da OS (HTML)."""

    # 1. Setup de Dados
    with app.app_context():
        # Configurar empresa (para testar logos e dados no header)
        cfg = Configuracao.get_config()
        cfg.empresa_nome = "Empresa Teste Ltda"
        cfg.empresa_cnpj = "12.345.678/0001-90"
        cfg.save()

        # Criar Cliente
        cliente = Cliente(
            nome_razao="Cliente Impressão",
            cpf_cnpj="111.222.333-44",
            email="cliente@print.com",
            logradouro="Rua Teste",
            numero="123",
            bairro="Centro",
            cidade="Cidade Teste",
            uf="TS",
            created_by=admin_user.id,
        )
        db.session.add(cliente)
        db.session.commit()

        # Criar Chamado
        chamado = Chamado(
            cliente_id=cliente.id,
            assunto="Chamado para Impressão",
            descricao="Teste de visualização de impressão",
            created_by=admin_user.id,
        )
        chamado.gerar_protocolo()
        db.session.add(chamado)
        db.session.commit()
        chamado_id = chamado.id
        protocolo = chamado.protocolo

        # Criar Agendamento (para testar dados da visita na OS)
        inicio = arrow.now().shift(days=1)
        visita = Agendamento(
            chamado_id=chamado.id,
            tecnico_id=admin_user.id,
            data_inicio=inicio.datetime,
            data_fim=inicio.shift(hours=1).datetime,
            instrucoes_tecnicas="Instruções para o técnico testar impressao",
            created_by=admin_user.id,
        )
        db.session.add(visita)
        db.session.commit()

    # 2. Login
    client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=True,
    )

    # 3. Acessar Rota de Impressão
    # OBS: A rota baixar_os está no blueprint 'agenda'
    response = client.get(url_for("agenda.baixar_os", chamado_id=chamado_id))

    # 4. Asserções
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    # Verificar elementos estruturais do HTML novo
    assert "<!doctype html>" in html
    assert "page-container" in html
    assert "header" in html

    # Verificar dados dinâmicos
    assert f"OS #{protocolo}" in html
    assert "Empresa Teste Ltda" in html
    assert "12.345.678/0001-90" in html
    assert "Cliente Impressão" in html
    assert "Rua Teste, 123, Centro, Cidade Teste/TS" in html
    assert "Chamado para Impressão" in html
    assert "Instruções para o técnico testar impressao" in html

    # Verificar se as assinaturas estão presentes
    assert "Técnico HelpHub" in html
    assert "Cliente / Responsável" in html
