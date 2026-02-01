import pytest

from unittest.mock import MagicMock, patch
from App.upload_manager import UploadManager


class TestUploadManager:
    def test_allowed_file_valid_extensions(self):
        """Testa se extensões válidas são aceitas."""
        valid_files = ["image.png", "doc.pdf", "text.txt", "photo.jpg", "doc.docx"]
        for filename in valid_files:
            assert UploadManager.allowed_file(filename) is True

    def test_allowed_file_invalid_extensions(self):
        """Testa se extensões inválidas são rejeitadas."""
        invalid_files = ["script.exe", "code.py", "site.html", "no_extension", "file."]
        for filename in invalid_files:
            assert UploadManager.allowed_file(filename) is False

    def test_save_computes_none_for_empty_file(self):
        """Testa se retorna None para arquivo vazio ou sem nome."""
        file_storage = MagicMock()
        file_storage.filename = ""
        assert UploadManager.salvar(file_storage) is None

        assert UploadManager.salvar(None) is None

    def test_save_raises_error_invalid_extension(self):
        """Testa se lança erro para extensão não permitida."""
        file_storage = MagicMock()
        file_storage.filename = "malware.exe"

        with pytest.raises(ValueError, match="Tipo de arquivo não permitido"):
            UploadManager.salvar(file_storage)

    @patch("App.upload_manager.os.makedirs")
    @patch("App.upload_manager.os.path.exists")
    @patch("App.upload_manager.filetype.guess")
    def test_save_valid_image(self, mock_guess, mock_exists, mock_makedirs, app):
        """Testa o salvamento bem sucedido de uma imagem válida."""
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        mock_exists.return_value = True

        file_storage = MagicMock()
        file_storage.filename = "avatar.png"

        mock_kind = MagicMock()
        mock_kind.extension = "png"
        mock_kind.mime = "image/png"
        mock_guess.return_value = mock_kind

        with app.app_context():
            result = UploadManager.salvar(file_storage)

        assert result is not None
        assert result.endswith(".png")
        file_storage.save.assert_called()

    @patch("App.upload_manager.os.makedirs")
    @patch("App.upload_manager.os.path.exists")
    @patch("App.upload_manager.filetype.guess")
    @patch("App.upload_manager.os.remove")
    def test_save_removes_file_on_magic_number_mismatch(
        self, mock_remove, mock_guess, mock_exists, mock_makedirs, app
    ):
        """Testa se remove arquivo quando magic number não detecta tipo válido (e não é txt)."""
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        mock_exists.return_value = True

        file_storage = MagicMock()
        file_storage.filename = "fake_image.png"

        mock_guess.return_value = None

        with pytest.raises(ValueError, match="Arquivo corrompido ou tipo desconhecido"):
            with app.app_context():
                UploadManager.salvar(file_storage)

        mock_remove.assert_called()

    @patch("App.upload_manager.os.makedirs")
    @patch("App.upload_manager.os.path.exists")
    @patch("App.upload_manager.filetype.guess")
    @patch("App.upload_manager.os.remove")
    def test_save_removes_file_on_suspicious_mime(
        self, mock_remove, mock_guess, mock_exists, mock_makedirs, app
    ):
        """Testa se remove arquivo quando MIME type é suspeito (ex: exe renomeado para png)."""
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        mock_exists.return_value = True

        file_storage = MagicMock()
        file_storage.filename = "trojan.png"

        mock_kind = MagicMock()
        mock_kind.extension = "exe"
        mock_kind.mime = "application/x-msdownload"
        mock_guess.return_value = mock_kind

        with pytest.raises(ValueError, match="Conteúdo do arquivo suspeito"):
            with app.app_context():
                UploadManager.salvar(file_storage)

        mock_remove.assert_called()

    @patch("App.upload_manager.os.makedirs")
    @patch("App.upload_manager.os.path.exists")
    @patch("App.upload_manager.filetype.guess")
    def test_save_creates_folder_if_not_exists(
        self, mock_guess, mock_exists, mock_makedirs, app
    ):
        """Testa se cria o diretório de upload se não existir."""
        app.config["UPLOAD_FOLDER"] = "C:/tmp/uploads"
        mock_exists.return_value = False  # Pasta não existe

        file_storage = MagicMock()
        file_storage.filename = "doc.pdf"

        mock_kind = MagicMock()
        mock_kind.extension = "pdf"
        mock_kind.mime = "application/pdf"
        mock_guess.return_value = mock_kind

        with app.app_context():
            UploadManager.salvar(file_storage)

        mock_makedirs.assert_called()
        args, _ = mock_makedirs.call_args
        # Garante que o path usado termina com /tmp/uploads (normalizando barras)
        assert "C:/tmp/uploads" in args[0].replace("\\", "/")

    @patch("App.upload_manager.os.makedirs")
    @patch("App.upload_manager.os.path.exists")
    @patch("App.upload_manager.filetype.guess")
    @patch("App.upload_manager.os.remove")
    def test_save_exception_handling_removes_file(
        self, mock_remove, mock_guess, mock_exists, mock_makedirs, app
    ):
        """Testa se remove o arquivo se ocorrer uma exceção genérica durante a validação."""
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        mock_exists.return_value = True

        file_storage = MagicMock()
        file_storage.filename = "buggy.png"

        mock_guess.side_effect = Exception("File system error")

        with pytest.raises(Exception, match="File system error"):
            with app.app_context():
                UploadManager.salvar(file_storage)

        assert mock_remove.called

    @patch("App.upload_manager.os.makedirs")
    @patch("App.upload_manager.os.path.exists")
    @patch("App.upload_manager.filetype.guess")
    @patch("App.upload_manager.os.remove")
    def test_save_exception_cleanup_simulated_missing_file(
        self, mock_remove, mock_guess, mock_exists, mock_makedirs, app
    ):
        """Testa o catch de exceção quando o arquivo não existe (não deve tentar remover)."""
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        # 1o exists (pasta): True
        # 2o exists (arquivo cleanup): False
        mock_exists.side_effect = [True, False]

        file_storage = MagicMock()
        file_storage.filename = "ghost.png"

        mock_guess.side_effect = Exception("Boom")

        with pytest.raises(Exception, match="Boom"):
            with app.app_context():
                UploadManager.salvar(file_storage)

        # mock_remove NÃO deve ser chamado pois o arquivo "não existe"
        mock_remove.assert_not_called()

    @patch("App.upload_manager.os.makedirs")
    @patch("App.upload_manager.os.path.exists")
    @patch("App.upload_manager.filetype.guess")
    def test_save_valid_text_file(self, mock_guess, mock_exists, mock_makedirs, app):
        """Testa o salvamento de arquivo txt (onde magic number é None mas é permitido)."""
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        mock_exists.return_value = True

        file_storage = MagicMock()
        file_storage.filename = "notes.txt"

        # txt geralmente retorna None no filetype
        mock_guess.return_value = None

        with app.app_context():
            result = UploadManager.salvar(file_storage)

        assert result is not None
        assert result.endswith(".txt")
