from App.utils import get_real_ip
from flask import Flask


class TestUtils:
    def test_get_real_ip_with_x_forwarded_for(self):
        """Testa a obtenção do IP via header X-Forwarded-For."""
        app = Flask(__name__)
        with app.test_request_context(
            headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
        ):
            ip = get_real_ip()
            assert ip == "203.0.113.195"

    def test_get_real_ip_without_header(self):
        """Testa o fallback para remote_addr quando não há header de proxy."""
        app = Flask(__name__)
        with app.test_request_context(environ_base={"REMOTE_ADDR": "192.168.1.50"}):
            ip = get_real_ip()
            assert ip == "192.168.1.50"

    def test_get_real_ip_default(self):
        """Testa o fallback padrão se remote_addr e headers falharem (ex: ambiente simulado)."""
        app = Flask(__name__)
        # Sem environ_base de remote_addr explícito
        with app.test_request_context():
            # Flask geralmente define 127.0.0.1 por padrão em teste se não especificado,
            # mas vamos garantir que o utils lida com o retorno.
            ip = get_real_ip()
            assert ip in [
                "127.0.0.1",
                None,
            ]  # O código tem fallback explícito "or '127.0.0.1'"
