from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from App.banco import db

from App.Modulos.Clientes.modelo import Cliente
from App.Modulos.Clientes.formulario import ClienteForm
from App.Modulos.Chamados.modelo import Chamado

clientes_bp = Blueprint(
    "clientes", __name__, template_folder="templates", url_prefix="/clientes"
)


@clientes_bp.route("/")
@login_required
def lista():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()

    query = Cliente.query.order_by(Cliente.nome_razao)

    if q:
        # Filtra por Nome ou CPF/CNPJ
        query = query.filter(
            (Cliente.nome_razao.ilike(f"%{q}%"))
            | (Cliente.nome_fantasia.ilike(f"%{q}%"))
            | (Cliente.cpf_cnpj.contains(q))
        )

    clientes = query.paginate(page=page, per_page=20)
    return render_template("cliente_lista.html", clientes=clientes, q=q)


@clientes_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    form = ClienteForm()
    if form.validate_on_submit():
        cliente = Cliente()
        form.populate_obj(cliente)
        try:
            cliente.save()
            flash("Cliente cadastrado com sucesso!", "success")
            return redirect(url_for("clientes.lista"))
        except Exception as e:
            flash(f"Erro ao salvar: {str(e)}", "error")

    return render_template("cliente_form.html", form=form, titulo="Novo Cliente")


@clientes_bp.route("/detalhe/<id>", methods=["GET", "POST"])
@clientes_bp.route("/editar/<id>", methods=["GET", "POST"])
@login_required
def editar(id):
    cliente = db.get_or_404(Cliente, id)
    form = ClienteForm(obj=cliente)

    # Busca chamados recentes deste cliente
    chamados_recentes = (
        Chamado.query.filter_by(cliente_id=id)
        .order_by(Chamado.created_at.desc())
        .limit(3)
        .all()
    )
    total_chamados = Chamado.query.filter_by(cliente_id=id).count()

    if form.validate_on_submit():
        form.populate_obj(cliente)
        try:
            cliente.save()
            flash("Dados do cliente atualizados com sucesso!", "success")
            return redirect(url_for("clientes.editar", id=id))
        except Exception as e:
            flash(f"Erro ao salvar: {str(e)}", "error")

    return render_template(
        "cliente_perfil.html",
        form=form,
        cliente=cliente,
        chamados=chamados_recentes,
        total_chamados=total_chamados,
    )


@clientes_bp.route("/upload_documento/<id>", methods=["POST"])
@login_required
def upload_documento(id):
    from App.Modulos.Clientes.modelo import DocumentoCliente
    from App.upload_manager import UploadManager
    from datetime import datetime

    cliente = db.get_or_404(Cliente, id)
    file = request.files.get("arquivo")

    if file:
        try:
            sub_diretorio = f"Clientes/{cliente.id}/{datetime.now().strftime('%Y')}"
            caminho = UploadManager.salvar(file, subfolder=sub_diretorio)

            doc = DocumentoCliente(
                cliente_id=cliente.id,
                nome_original=file.filename,
                caminho=caminho,
                tipo=file.content_type,
                created_by=current_user.id,
            )
            doc.save()
            flash("Documento anexado com sucesso!", "success")
        except Exception as e:
            flash(f"Erro no upload: {str(e)}", "error")

    return redirect(url_for("clientes.editar", id=id))


@clientes_bp.route("/excluir_documento/<id>")
@login_required
def excluir_documento(id):
    from App.Modulos.Clientes.modelo import DocumentoCliente

    doc = db.get_or_404(DocumentoCliente, id)
    cliente_id = doc.cliente_id

    # Opcional: Remover o arquivo físico também
    # ...

    doc.delete()
    flash("Documento removido.", "success")
    return redirect(url_for("clientes.editar", id=cliente_id))


@clientes_bp.route("/excluir/<id>")
@login_required
def excluir(id):
    cliente = db.get_or_404(Cliente, id)
    # Lógica de Soft Delete preferencialmente, mas aqui faremos hard delete conforme padrão simples
    cliente.delete()
    flash("Cliente excluído.", "success")
    return redirect(url_for("clientes.lista"))
