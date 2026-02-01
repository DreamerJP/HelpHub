from flask_sqlalchemy import SQLAlchemy
import sqlite3
from datetime import datetime, date
from sqlalchemy import event
from sqlalchemy.engine import Engine


# --- CONFIGURAÇÃO DE INFRAESTRUTURA: SUPORTE A DATAS NO SQLITE (PYTHON 3.12+) ---
# Registramos os adaptadores oficiais para garantir que objetos datetime/date
# sejam persistidos corretamente como strings ISO, preservando a compatibilidade.
@event.listens_for(Engine, "connect")
def _set_sqlite_adapters(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Registramos no nível do módulo apenas uma vez, de forma controlada.
        # Isso garante que o SQLite saiba traduzir os tipos do Python.
        sqlite3.register_adapter(datetime, lambda val: val.isoformat(sep=" "))
        sqlite3.register_adapter(date, lambda val: val.isoformat())


# Instância compartilhada do SQLAlchemy.
db = SQLAlchemy()
