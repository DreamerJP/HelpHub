# === ATALHO PARA DESENVOLVIMENTO (DEBUG) ===
# USE APENAS NO SEU COMPUTADOR LOCAL!
# Este arquivo ativa o modo de inspeção e reinicialização automática.
# No servidor (PythonAnywhere), o sistema ignora este arquivo e usa WSGI.

from App.iniciar import create_app

# Força o modo 'development' para ter acesso ao Debugger na tela
app = create_app("development")

if __name__ == "__main__":
    print("\n[AVISO] Iniciando servidor de DESENVOLVIMENTO...")
    print("[AVISO] Nao use este modo em producao (na internet).\n")

    app.run(host="127.0.0.1", port=5000, debug=True)
