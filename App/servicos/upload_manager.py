import os
import uuid
import filetype
from flask import current_app


class UploadManager:
    """
    Gerenciador de Uploads Seguro (Nível Hard).
    """

    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "doc", "docx", "txt"}

    @staticmethod
    def allowed_file(filename):
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in UploadManager.ALLOWED_EXTENSIONS
        )

    @staticmethod
    def salvar(file_storage, subfolder=""):
        """
        Salva o arquivo com 4 camadas de segurança:
        1. Verifica extensão.
        2. Renomeia para UUID (Impede Path Traversal e Sobrescrita).
        3. Verifica Magic Numbers (Impede script kiddies mudando .exe para .jpg).
        4. Salva fora da pasta App (Data/Uploads).

        Retorna: Caminho relativo (para salvar no banco) ou None se falhar.
        """
        if not file_storage or file_storage.filename == "":
            return None

        # 1. Validação de Extensão Básica
        if not UploadManager.allowed_file(file_storage.filename):
            raise ValueError("Tipo de arquivo não permitido (Extensão negada).")

        # Preparar diretório
        upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # 2. Renomeação Segura (UUID)
        ext = file_storage.filename.rsplit(".", 1)[1].lower()
        novo_nome = f"{uuid.uuid4().hex}.{ext}"
        caminho_completo = os.path.join(upload_folder, novo_nome)

        # Salva temporariamente para verificação profunda
        file_storage.save(caminho_completo)

        # 3. Validação de Magic Numbers (Conteúdo Real)
        try:
            kind = filetype.guess(caminho_completo)
            if kind is None and ext not in ["txt", "csv"]:
                # Arquivos texto puro podem não ter magic number claro, tratamos com exceção ou bloqueio.
                # Para maior segurança, se não detectou tipo e não é txt intencional, removemos.
                os.remove(caminho_completo)
                raise ValueError(
                    "Arquivo corrompido ou tipo desconhecido (Magic Number falhou)."
                )

            # Se detectou, valida se bate com a extensão esperada
            if kind:
                if kind.extension not in ["jpg", "png", "pdf", "doc", "docx", "zip"]:
                    # Nota: filetype as vezes detecta 'jpeg' como 'jpg', ok.
                    # Mas se detectou 'exe', deleta.
                    permissoes_mime = [
                        "image/jpeg",
                        "image/png",
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ]
                    if kind.mime not in permissoes_mime and ext != "txt":
                        os.remove(caminho_completo)
                        raise ValueError(f"Conteúdo do arquivo suspeito ({kind.mime}).")

        except Exception as e:
            # Em caso de qualquer erro na validação, limpa o arquivo
            if os.path.exists(caminho_completo):
                os.remove(caminho_completo)
            raise e

        # Retorna caminho relativo para o banco (Ex: '2026/arquivo.jpg')
        # Aqui simplificamos retornando apenas o nome se subfolder for vazio
        return os.path.join(subfolder, novo_nome).replace("\\", "/")
