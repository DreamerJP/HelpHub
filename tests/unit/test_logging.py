import logging
from unittest.mock import patch
from flask import Flask
from App.utils import RequestEntityFilter


class TestLoggingFilter:
    def test_filter_adds_clientip_with_context(self):
        """Testa se o filtro adiciona o IP do cliente quando há contexto de request."""
        filtro = RequestEntityFilter()
        record = logging.LogRecord("name", logging.INFO, "path", 10, "msg", (), None)

        app = Flask(__name__)

        # Mock get_real_ip para retornar um IP fixo
        with patch("App.utils.get_real_ip", return_value="10.0.0.99"):
            with app.test_request_context():
                result = filtro.filter(record)

        assert result is True
        assert hasattr(record, "clientip")
        assert record.clientip == "10.0.0.99"

    def test_filter_adds_sistema_without_context(self):
        """Testa se o filtro adiciona 'SISTEMA' quando não há contexto de request."""
        filtro = RequestEntityFilter()
        record = logging.LogRecord("name", logging.INFO, "path", 10, "msg", (), None)

        # Sem contexto de request
        result = filtro.filter(record)

        assert result is True
        assert hasattr(record, "clientip")
        assert record.clientip == "SISTEMA"
