from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
)
from flask_login import login_user, logout_user, current_user, login_required
from App.Modulos.Autenticacao.modelo import Usuario
from App.Modulos.Autenticacao.formulario import (
    LoginForm,
    UsuarioForm,
    AlterarSenhaForm,
    PerfilForm,
)
from App.servicos.seguranca import limiter, admin_required
from flask_limiter import RateLimitExceeded
from App.banco import db
from App.servicos.upload_manager import UploadManager
import os

# Blueprint da Autenticação
auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("layout.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(username=form.username.data).first()

        # Verifica Usuário E Senha de forma segura
        if user is None or not user.check_password(form.password.data):
            current_app.logger.warning(
                f"[SEGURANÇA] Falha de login: Usuário '{form.username.data}' não encontrado ou senha errada."
            )
            flash("Usuário ou senha inválidos.", "error")
            return redirect(url_for("auth.login"))

        if not user.ativo:
            current_app.logger.warning(
                f"[SEGURANÇA] Acesso negado: Usuário '{user.username}' está inativo."
            )
            flash("Usuário inativo. Contate o suporte.", "warning")
            return redirect(url_for("auth.login"))

        from flask import session

        session.permanent = True
        login_user(user, remember=form.remember_me.data)
        current_app.logger.info(
            f"[SEGURANÇA] Login bem-sucedido: Usuário '{user.username}' acessou o sistema."
        )

        # Redirecionamento seguro (Next parameter)
        next_page = request.args.get("next")
        if not next_page or not next_page.startswith("/"):
            next_page = url_for("layout.index")

        return redirect(next_page)

    return render_template("auth_login.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# --- GESTÃO DE EQUIPE (ADMIN ONLY) ---


@auth_bp.route("/usuarios")
@login_required
@admin_required
def lista_usuarios():
    query = Usuario.query
    query = Usuario.apply_sort(
        query, request.args.get("sort"), request.args.get("order")
    )
    if not request.args.get("sort"):
        query = query.order_by(Usuario.nome)

    usuarios = query.all()
    return render_template("usuarios_lista.html", usuarios=usuarios)


@auth_bp.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo_usuario():
    form = UsuarioForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash("A senha é obrigatória para novos usuários.", "error")
            return render_template("usuario_form.html", form=form, titulo="Novo Membro")

        if Usuario.query.filter_by(username=form.username.data).first():
            flash("Este nome de usuário já está em uso.", "error")
            return render_template("usuario_form.html", form=form, titulo="Novo Membro")

        user = Usuario(
            nome=form.nome.data,
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            ativo=form.ativo.data,
        )
        user.set_password(form.password.data)

        user.save()
        flash(f"Usuário {user.username} criado com sucesso!", "success")
        return redirect(url_for("auth.lista_usuarios"))

    return render_template("usuario_form.html", form=form, titulo="Novo Membro")


@auth_bp.route("/usuarios/editar/<id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar_usuario(id):
    user = db.session.get(Usuario, id)
    if not user:
        from flask import abort

        abort(404)

    form = UsuarioForm(obj=user)

    if form.validate_on_submit():
        # Verifica se mudou username e se o novo já existe
        existente = Usuario.query.filter_by(username=form.username.data).first()
        if existente and existente.id != user.id:
            flash("Este nome de usuário já está em uso.", "error")
            return render_template(
                "usuario_form.html", form=form, titulo="Editar Membro"
            )

        user.nome = form.nome.data
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.ativo = form.ativo.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for("auth.lista_usuarios"))

    return render_template("usuario_form.html", form=form, titulo="Editar Membro")


@auth_bp.route("/usuarios/toggle/<id>")
@login_required
@admin_required
def toggle_usuario(id):
    user = db.session.get(Usuario, id)
    if not user:
        from flask import abort

        abort(404)

    if id == current_user.id:
        flash("Você não pode desativar seu próprio usuário.", "error")
        return redirect(url_for("auth.lista_usuarios"))

    user.ativo = not user.ativo
    db.session.commit()

    status = "ativado" if user.ativo else "desativado"
    flash(f"Usuário {user.username} foi {status}.", "info")
    return redirect(url_for("auth.lista_usuarios"))


@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    form_senha = AlterarSenhaForm()
    form_perfil = PerfilForm(obj=current_user)

    # Identifica qual form foi submetido
    if "btn_senha" in request.form and form_senha.validate_on_submit():
        if not current_user.check_password(form_senha.password_old.data):
            flash("Senha atual incorreta.", "error")
        else:
            current_user.set_password(form_senha.password_new.data)
            db.session.commit()
            flash("Sua senha foi alterada com sucesso!", "success")
            return redirect(url_for("auth.perfil"))

    if "btn_perfil" in request.form and form_perfil.validate_on_submit():
        current_user.nome = form_perfil.nome.data
        current_user.email = form_perfil.email.data

        # Logica de Upload de Avatar
        if form_perfil.avatar.data:
            try:
                # 1. Se já tem um avatar, remove o antigo do disco para não ocupar espaço
                if current_user.avatar:
                    old_path = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], current_user.avatar
                    )
                    if os.path.exists(old_path):
                        os.remove(old_path)

                # 2. Salva o novo
                subfolder = f"Profiles/{current_user.id}"
                filename = UploadManager.salvar(
                    form_perfil.avatar.data, subfolder=subfolder
                )
                current_user.avatar = filename
            except Exception as e:
                flash(f"Erro ao salvar foto: {str(e)}", "error")
                return redirect(url_for("auth.perfil"))

        db.session.commit()
        flash("Dados atualizados com sucesso!", "success")
        return redirect(url_for("auth.perfil"))

    return render_template(
        "perfil.html", form_senha=form_senha, form_perfil=form_perfil
    )


@auth_bp.route("/perfil/remover_avatar")
@login_required
def remover_avatar():
    """Remove a foto de perfil do usuário e apaga o arquivo físico."""
    if current_user.avatar:
        try:
            path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], current_user.avatar
            )
            if os.path.exists(path):
                os.remove(path)

            current_user.avatar = None
            db.session.commit()
            flash("Foto de perfil removida.", "info")
        except Exception as e:
            flash(f"Erro ao remover arquivo: {str(e)}", "error")

    return redirect(url_for("auth.perfil"))


@auth_bp.app_errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    if request.endpoint == "auth.login":
        flash(
            "Muitas tentativas de login. Aguarde um minuto e tente novamente.", "error"
        )
    else:
        flash(
            "Muitas requisições ao sistema. Por favor, aguarde um momento.", "warning"
        )

    if current_user.is_authenticated:
        return redirect(url_for("layout.index"))
    return redirect(url_for("auth.login"))
