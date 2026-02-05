from flask import request, has_request_context
import logging


def get_real_ip():
    """
    Obtém o IP verdadeiro do cliente, mesmo atrás de proxies (Nginx/Cloudflare).
    Verifica o header X-Forwarded-For antes do remote_addr.
    """
    if request.headers.getlist("X-Forwarded-For"):
        # O primeiro IP da lista é o original do cliente
        return request.headers.getlist("X-Forwarded-For")[0].split(",")[0].strip()
    else:
        return request.remote_addr or "127.0.0.1"


class RequestEntityFilter(logging.Filter):
    """
    Filtro de Log para injetar o IP real do cliente no record.
    """

    def filter(self, record):
        if has_request_context():
            record.clientip = get_real_ip()
        else:
            record.clientip = "SISTEMA"
        return True
