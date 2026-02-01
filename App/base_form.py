from flask_wtf import FlaskForm


class AppBaseForm(FlaskForm):
    """
    Formulário Base do HelpHub 4.0.
    Garante proteção CSRF em todos os formulários do sistema.
    """

    pass
