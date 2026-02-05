from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine
import sqlite3
import datetime

# Convenção de nomes para Constraints (Fundacional para Migrações e MySQL)
# Isso garante que FKs, PKs e Índices tenham nomes previsíveis.
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


# --- SUPORTE A DATAS NO SQLITE (PYTHON 3.12+) ---
@event.listens_for(Engine, "connect")
def set_sqlite_pro_processing(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Ensina o SQLite a converter datas corretamente sem gerar Warnings
        sqlite3.register_adapter(datetime.date, lambda v: v.isoformat())
        sqlite3.register_adapter(datetime.datetime, lambda v: v.isoformat(sep=" "))


# Instância compartilhada do SQLAlchemy com padronização profissional.
db = SQLAlchemy(metadata=metadata)
