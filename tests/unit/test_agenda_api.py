import pytest
import arrow
from App.Modulos.Agenda.modelo import Agendamento
from App.Modulos.Chamados.modelo import Chamado
from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Autenticacao.modelo import Usuario


class TestAgenda:
    @pytest.fixture
    def dados_agenda(self, _db, app):
        """Cria dados de teste: Cliente, Técnico, Chamado e Agendamentos."""
        with app.app_context():
            tecnico = Usuario(
                username="Tecnico1", email="tec@test.com", role="Operador"
            )
            tecnico.set_password("123")
            _db.session.add(tecnico)

            cliente = Cliente(
                nome_razao="Cliente Teste",
                cpf_cnpj="12345678900",
                logradouro="Rua A",
                numero="100",
                bairro="Centro",
                cidade="Metropolis",
                uf="SP",
            )
            _db.session.add(cliente)
            _db.session.commit()

            chamado = Chamado(
                assunto="Instalação",
                descricao="Instalar fibra",
                cliente_id=cliente.id,
                tecnico_id=tecnico.id,
            )
            chamado.gerar_protocolo()  # Garante que tenha protocolo
            _db.session.add(chamado)
            _db.session.commit()

            # Agendamento 1: Futuro (Normal)
            inicio_futuro = arrow.now().shift(days=1).datetime
            fim_futuro = arrow.now().shift(days=1, hours=2).datetime
            agenda_futuro = Agendamento(
                chamado_id=chamado.id,
                tecnico_id=tecnico.id,
                data_inicio=inicio_futuro,
                data_fim=fim_futuro,
                status="Agendado",
            )

            # Agendamento 2: Passado (Atrasado)
            inicio_passado = arrow.now().shift(days=-1, hours=-2).datetime
            fim_passado = arrow.now().shift(days=-1).datetime
            agenda_atrasado = Agendamento(
                chamado_id=chamado.id,
                tecnico_id=tecnico.id,
                data_inicio=inicio_passado,
                data_fim=fim_passado,
                status="Agendado",
            )

            _db.session.add(agenda_futuro)
            _db.session.add(agenda_atrasado)
            _db.session.commit()

            return {
                "tecnico_id": tecnico.id,
                "cliente_id": cliente.id,
                "futuro_id": agenda_futuro.id,
                "atrasado_id": agenda_atrasado.id,
            }

    def test_api_eventos_estrutura(self, client, dados_agenda):
        """Testa se a API retorna a estrutura correta e os metadados de endereço."""
        # Login
        client.post("/login", data={"username": "Tecnico1", "password": "123"})

        response = client.get("/agenda/api/eventos")
        assert response.status_code == 200
        eventos = response.json

        assert len(eventos) >= 2

        # Encontra o evento futuro
        evento_futuro = next(e for e in eventos if e["id"] == dados_agenda["futuro_id"])

        # Verifica metadados de endereço
        props = evento_futuro["extendedProps"]
        assert props["bairro"] == "Centro"
        assert props["cidade"] == "Metropolis"
        assert "Rua A" in props["endereco"]
        assert ", 100" in props["endereco"]

    def test_api_eventos_atraso(self, client, dados_agenda):
        """Testa se a lógica de atraso (cor e flag) está correta."""
        # Login
        client.post("/login", data={"username": "Tecnico1", "password": "123"})

        response = client.get("/agenda/api/eventos")
        eventos = response.json

        # Verifica evento Atrasado
        evento_atrasado = next(
            e for e in eventos if e["id"] == dados_agenda["atrasado_id"]
        )
        props = evento_atrasado["extendedProps"]

        assert props["is_delayed"] is True
        assert props["status"] == "Atrasado"
        assert evento_atrasado["color"] == "#F59E0B"  # Laranja (Warning)
        # Note: Atualizei a cor esperada para consistência com o frontend

        # Verifica evento Futuro (Não atrasado)
        evento_futuro = next(e for e in eventos if e["id"] == dados_agenda["futuro_id"])
        props_futuro = evento_futuro["extendedProps"]

        assert props_futuro["is_delayed"] is False
        assert props_futuro["status"] == "Agendado"
        assert evento_futuro["color"] == "#3B82F6"  # Azul
