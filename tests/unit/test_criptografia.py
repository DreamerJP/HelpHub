from App.servicos.criptografia import encriptar, decriptar


def test_encriptar_decriptar_sucesso(app):
    """Testa o fluxo completo de criptografia e descriptografia."""
    with app.app_context():
        texto_original = "Token-Secreto-123"
        texto_encriptado = encriptar(texto_original)

        assert texto_encriptado != texto_original
        assert decriptar(texto_encriptado) == texto_original


def test_criptografia_valores_vazios(app):
    """Testa o comportamento com valores None ou vazios."""
    with app.app_context():
        assert encriptar(None) is None
        assert (
            encriptar("") is None
        )  # Mudança aqui: strings vazias retornam None na nossa lógica
        assert decriptar(None) is None


def test_decriptar_texto_puro(app):
    """Prevenção: Garante que decriptar texto não encriptado retorna o original (resiliência)."""
    with app.app_context():
        texto_puro = "texto_nao_encriptado"
        # Deve retornar o original em caso de erro na descriptografia
        assert decriptar(texto_puro) == texto_puro


def test_criptografia_resiliencia_consistencia(app):
    """Garante que códigos encriptados diferentes (por causa do salt/IV) retornam o mesmo valor."""
    with app.app_context():
        texto = "minha-senha"
        enc1 = encriptar(texto)
        enc2 = encriptar(texto)

        # O Fernet gera códigos diferentes para o mesmo texto por segurança (IV aleatório)
        assert enc1 != enc2
        # Mas ambos devem voltar para o valor original
        assert decriptar(enc1) == texto
        assert decriptar(enc2) == texto


def test_criptografia_chaves_diferentes(app):
    """Verifica que se a SECRET_KEY mudar, a descriptografia falha (retorna original)."""
    with app.app_context():
        texto = "secreto"
        enc = encriptar(texto)

        # Simula mudança de chave
        app.config["SECRET_KEY"] = "OUTRA_CHAVE_COMPLETAMENTE_DIFERENTE_123"

        # Como a chave mudou, o decriptar deve falhar e retornar o encriptado (pela nossa lógica de resiliência)
        # ou o original dependendo de como o erro é tratado. No nosso caso, retorna o encriptado se falhar o decifrador.
        assert decriptar(enc) != texto
