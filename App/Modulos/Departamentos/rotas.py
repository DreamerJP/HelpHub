from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from App.banco import db
from App.Modulos.Departamentos.modelo import Departamento
from App.Modulos.Departamentos.formulario import DepartamentoForm
from App.servicos.seguranca import admin_required

dept_bp = Blueprint(
    "departamentos",
    __name__,
    template_folder="templates",
    url_prefix="/admin/departamentos",
)


@dept_bp.route("/")
@login_required
@admin_required
def lista():
    query = Departamento.query
    query = Departamento.apply_sort(
        query, request.args.get("sort"), request.args.get("order")
    )

    if not request.args.get("sort"):
        query = query.order_by(Departamento.nome.asc())

    departamentos = query.all()
    return render_template("depto_lista.html", departamentos=departamentos)


@dept_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo():
    form = DepartamentoForm()
    if form.validate_on_submit():
        dept = Departamento()
        form.populate_obj(dept)
        dept.save()
        flash("Departamento criado com sucesso!", "success")
        return redirect(url_for("departamentos.lista"))
    return render_template("depto_form.html", form=form, titulo="Novo Departamento")


@dept_bp.route("/editar/<id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id):
    dept = db.get_or_404(Departamento, id)
    form = DepartamentoForm(obj=dept)
    if form.validate_on_submit():
        form.populate_obj(dept)
        dept.save()  # Base model cuida do update e updated_at
        flash("Departamento atualizado!", "success")
        return redirect(url_for("departamentos.lista"))
    return render_template("depto_form.html", form=form, titulo="Editar Departamento")


@dept_bp.route("/excluir/<id>")
@login_required
@admin_required
def excluir(id):
    dept = db.get_or_404(Departamento, id)
    # Futuro: Verificar se há chamados vinculados antes de excluir
    dept.delete()
    flash("Departamento removido.", "success")
    return redirect(url_for("departamentos.lista"))
