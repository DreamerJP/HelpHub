import os
import sys
import subprocess


def main():
    # 1. Configurar o ambiente
    # Adicionar o diretório pai (raiz do projeto) ao PYTHONPATH
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)

    print("=" * 60)
    print(" INICIANDO BATERIA DE TESTES - HELPHUB 4.0")
    print(f" Diretorio Raiz: {project_root}")
    print("=" * 60)

    # 2. Comando para rodar os testes
    # Usamos sys.executable para garantir que usamos o mesmo Python do ambiente atual
    cmd = [sys.executable, "-m", "pytest", "-c", "tests/pyproject.toml", "tests/"]

    try:
        # Roda o comando e mostra saida em tempo real
        result = subprocess.run(cmd, cwd=project_root)

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print(" SUCESSO! Todos os testes passaram.")
        else:
            print(" FALHA! Alguns testes encontraram problemas.")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n  Testes interrompidos pelo usuario.")
    except Exception as e:
        print(f"\n Erro ao executar testes: {e}")

    # 3. Pausa para o usuário ver o resultado (importante no Windows)
    input("\nPressione ENTER para fechar esta janela...")


if __name__ == "__main__":
    main()
