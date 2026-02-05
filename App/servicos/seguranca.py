from flask_limiter import Limiter
from .utils import get_real_ip
from flask import abort
from flask_login import current_user
from functools import wraps

# Instância compartilhada do Rate Limiter.
# Responsável por fornecer as travas de segurança (como bloqueio de força bruta no login).
limiter = Limiter(
    key_func=get_real_ip,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://",
)


def admin_required(f):
    """Garante que apenas usuários com role 'Admin' possam acessar a rota."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function
