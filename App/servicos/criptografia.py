import base64
from cryptography.fernet import Fernet
from flask import current_app


def get_cipher():
    """Cria uma instância do Fernet baseada na SECRET_KEY do app."""
    # A Fernet key deve ser 32 bytes codificados em base64.
    # Usamos a SECRET_KEY do Flask como semente.
    key = current_app.config.get("SECRET_KEY", "dev-key-mudar-em-producao-123")

    # Ajusta a chave para ter exatamente 32 bytes para o Fernet
    # Fazemos um hash simples ou truncamos/preenchemos
    hashed_key = key.ljust(32)[:32].encode("utf-8")
    base64_key = base64.urlsafe_b64encode(hashed_key)
    return Fernet(base64_key)


def encriptar(texto):
    """Criptografa um texto em texto puro."""
    if not texto:
        return None
    cipher = get_cipher()
    return cipher.encrypt(texto.encode("utf-8")).decode("utf-8")


def decriptar(texto_encriptado):
    """Descriptografa um texto codificado."""
    if not texto_encriptado:
        return None
    try:
        cipher = get_cipher()
        return cipher.decrypt(texto_encriptado.encode("utf-8")).decode("utf-8")
    except Exception:
        # Se falhar (ex: dados antigos em texto puro), retorna o original
        # Isso ajuda na transição
        return texto_encriptado
