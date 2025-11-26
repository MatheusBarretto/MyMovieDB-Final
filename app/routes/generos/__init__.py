import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from flask_wtf import FlaskForm

from app.forms.generos import GeneroEditForm
from app.infra.modulos import db
from app.models.filme import Genero
from app.services.crud_service import CrudService

genero_bp = Blueprint(name='genero',
                      import_name=__name__,
                      url_prefix='/genero',
                      template_folder="templates", )


@genero_bp.route('/', methods=['GET'])
def listar_generos():
    """Lista todos os gêneros com suporte a filtros e paginação.

    Query Parameters:
        page (int): Número da página (padrão: 1)
        pp (int): Itens por página (padrão: 50, máximo: MAX_PER_PAGE)
        q (str): Filtro de busca parcial por nome
        a (int): Filtro de status ativo (0=todos, 1=ativos, 2=inativos)

    Returns:
        Template renderizado com a lista paginada de gêneros
    """
    page = request.args.get('page', default=1, type=int)
    pp = request.args.get('pp', default=50, type=int)
    q = request.args.get('q', default=None, type=str)
    a = request.args.get('a', default=0, type=int)

    # Usa o CrudService para obter os dados paginados
    rset_page, redirected = CrudService.listar_com_paginacao(
            model_class=Genero,
            page=page,
            per_page=pp,
            search_field='nome',
            search_query=q,
            active_filter=a,
            order_by_field='nome'
    )

    # Se houve redirecionamento para a primeira página, informa o usuário
    if redirected:
        flash("Não existem registros na página solicitada. Apresentando primeira página",
              category='info')
        page = 1

    # Cria um form vazio apenas para gerar CSRF token
    csrf_form = FlaskForm()

    return render_template('genero/web/lista.jinja2',
                           title="Lista de gêneros",
                           rset_page=rset_page,
                           page=page,
                           q=q,
                           pp=pp,
                           a=a,
                           csrf_form=csrf_form)


@genero_bp.route('/new', methods=['GET', 'POST'])
@login_required
def criar_genero():
    """Cria um novo gênero.

    Returns:
        Template renderizado com o formulário de criação ou redirect após salvar
    """
    form = GeneroEditForm()
    del form.ativo

    if form.validate_on_submit():
        # Cria um novo gênero com os dados do formulário
        genero = Genero()
        genero.nome = form.nome.data.strip()
        genero.ativo = True
        genero.descricao = form.descricao.data

        # Salva no banco de dados
        try:
            db.session.add(genero)
            db.session.commit()
            flash("Gênero criado com sucesso.", category='success')
            return redirect(url_for('genero.listar_generos'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar gênero: {e}")
            flash("Ocorreu um erro ao criar o gênero. Tente novamente.", category='danger')

    return render_template('genero/web/criar.jinja2',
                           title="Novo gênero",
                           form=form)


@genero_bp.route('/<uuid:genero_id>/edit', methods=['GET', 'POST'])
@login_required
def editar_genero(genero_id: uuid.UUID):
    """Edita um gênero existente.

    Args:
        genero_id: UUID do gênero a ser editado

    Returns:
        Template renderizado com o formulário de edição ou redirect após salvar
    """
    try:
        genero = Genero.get_by_id(genero_id,
                                  raise_if_not_found=True)
    except Genero.RecordNotFoundError:
        flash("Gênero não encontrado.", category='warning')
        return redirect(url_for('generos.listar_generos'))

    # Conta o número de filmes com esse gênero
    numero_de_filmes = len(genero.filmes)

    form = GeneroEditForm()
    if request.method == 'GET':
        # Preenche o formulário com os dados atuais do gênero
        form.nome.data = genero.nome
        form.ativo.data = genero.ativo
        form.descricao.data = genero.descricao

    if form.validate_on_submit():
        # Atualiza os campos do gênero usando os dados do formulário WTForms
        genero.nome = form.nome.data.strip()
        genero.ativo = form.ativo.data
        genero.descricao = form.descricao.data

        # Salva as alterações no banco de dados
        try:
            db.session.commit()
            flash("Gênero atualizado com sucesso.", category='success')
            return redirect(url_for('genero.listar_generos'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar gênero: {e}")
            flash("Ocorreu um erro ao atualizar o gênero. Tente novamente.", category='danger')

    return render_template('genero/web/editar.jinja2',
                           title="Editar gênero",
                           form=form,
                           numero_de_filmes=numero_de_filmes)


@genero_bp.route('/<uuid:genero_id>/delete', methods=['POST'])
@login_required
def deletar_genero(genero_id: uuid.UUID):
    """Deleta um gênero existente, se não tiver associações.

    Args:
        genero_id: UUID do gênero a ser deletado

    Returns:
        Redirect para a lista de gêneros
    """
    try:
        genero = Genero.get_by_id(genero_id,
                                  raise_if_not_found=True)
    except Genero.RecordNotFoundError:
        flash("Gênero não encontrado.", category='warning')
        return redirect(url_for('generos.listar_generos'))

    # Verifica se há filmes associados
    numero_de_filmes = len(genero.filmes)
    if numero_de_filmes > 0:
        flash(
            f"Não é possível excluir o gênero '{genero.nome}' pois ele está "
            f"associado a {numero_de_filmes} filme(s).",
            category='danger'
        )
        return redirect(url_for('genero.listar_generos'))

    # Salva o nome antes de deletar (para a mensagem)
    nome_genero = genero.nome

    # Deleta o gênero
    try:
        db.session.delete(genero)
        db.session.commit()
        flash(f"Gênero '{nome_genero}' excluído com sucesso.", category='success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar gênero: {e}")
        flash("Ocorreu um erro ao excluir o gênero. Tente novamente.", category='danger')

    return redirect(url_for('genero.listar_generos'))


@genero_bp.route('/<uuid:genero_id>/filmes', methods=['GET'])
def listar_filmes_do_genero(genero_id: uuid.UUID):
    """Lista todos os filmes de um gênero específico com paginação.

    Args:
        genero_id: UUID do gênero

    Query Parameters:
        page (int): Número da página (padrão: 1)
        per_page (int): Itens por página (padrão: 24)
        search (str): Filtro de busca por título

    Returns:
        Template renderizado com a lista paginada de filmes do gênero
    """
    from app.services.filme_service import FilmeService

    # Busca o gênero
    try:
        genero = Genero.get_by_id(genero_id, raise_if_not_found=True)
    except Genero.RecordNotFoundError:
        flash("Gênero não encontrado.", category='warning')
        return redirect(url_for('genero.listar_generos'))

    # Parâmetros de paginação e busca
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=24, type=int)
    search = request.args.get('search', default=None, type=str)

    # Limita per_page ao máximo configurado
    max_per_page = current_app.config.get('MAX_PER_PAGE', 500)
    per_page = min(per_page, max_per_page)

    # Busca filmes do gênero usando o service
    pagination = FilmeService.listar_filmes_por_genero(
        genero=genero,
        page=page,
        per_page=per_page,
        search=search
    )

    return render_template('genero/web/filmes.jinja2',
                           title=f"Filmes de {genero.nome}",
                           genero=genero,
                           pagination=pagination,
                           page=page,
                           per_page=per_page,
                           search=search)
