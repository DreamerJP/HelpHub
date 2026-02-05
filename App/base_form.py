from flask_wtf import FlaskForm


class AppBaseForm(FlaskForm):
    """
    Formulário Base do HelpHub 4.1.
    Garante proteção CSRF em todos os formulários do sistema.
    """

    pass
