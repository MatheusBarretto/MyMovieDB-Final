import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required

from flask_wtf import FlaskForm

from app.forms.funcoes_tecnicas import FuncaoTecnicaEditForm
from app.infra.modulos import db
from app.models.filme import FuncaoTecnica
from app.services.crud_service import CrudService

funcao_tecnica_bp = Blueprint(name='funcao_tecnica',
                              import_name=__name__,
                              url_prefix='/funcao_tecnica',
                              template_folder="templates", )


@funcao_tecnica_bp.route('/', methods=['GET'])
def listar_funcoes_tecnicas():
    """Lista todas as funções técnicas com suporte a filtros e paginação.

    Query Parameters:
        page (int): Número da página (padrão: 1)
        pp (int): Itens por página (padrão: 50, máximo: MAX_PER_PAGE)
        q (str): Filtro de busca parcial por nome
        a (int): Filtro de status ativo (0=todos, 1=ativos, 2=inativos)

    Returns:
        Template renderizado com a lista paginada de funções técnicas
    """
    page = request.args.get('page', default=1, type=int)
    pp = request.args.get('pp', default=50, type=int)
    q = request.args.get('q', default=None, type=str)
    a = request.args.get('a', default=0, type=int)

    # Usa o CrudService para obter os dados paginados
    rset_page, redirected = CrudService.listar_com_paginacao(
            model_class=FuncaoTecnica,
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

    return render_template('funcao_tecnica/web/lista.jinja2',
                           title="Lista de funções técnicas",
                           rset_page=rset_page,
                           page=page,
                           q=q,
                           pp=pp,
                           a=a,
                           csrf_form=csrf_form)


@funcao_tecnica_bp.route('/new', methods=['GET', 'POST'])
@login_required
def criar_funcao_tecnica():
    """Cria uma nova função técnica.

    Returns:
        Template renderizado com o formulário de criação ou redirect após salvar
    """
    form = FuncaoTecnicaEditForm()
    del form.ativo

    if form.validate_on_submit():
        # Cria uma nova função técnica com os dados do formulário
        funcao_tecnica = FuncaoTecnica()
        funcao_tecnica.nome = form.nome.data.strip()
        funcao_tecnica.descricao = form.descricao.data
        funcao_tecnica.ativo = True

        # Salva no banco de dados
        try:
            db.session.add(funcao_tecnica)
            db.session.commit()
            flash("Função técnica criada com sucesso.", category='success')
            return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar função técnica: {e}")
            flash("Ocorreu um erro ao criar a função técnica. Tente novamente.", category='danger')

    return render_template('funcao_tecnica/web/criar.jinja2',
                           title="Nova função técnica",
                           form=form)


@funcao_tecnica_bp.route('/<uuid:funcao_tecnica_id>/edit', methods=['GET', 'POST'])
@login_required
def editar_funcao_tecnica(funcao_tecnica_id: uuid.UUID):
    """Edita uma função técnica existente.

    Args:
        funcao_tecnica_id: UUID da função técnica a ser editada

    Returns:
        Template renderizado com o formulário de edição ou redirect após salvar
    """
    try:
        funcao_tecnica = FuncaoTecnica.get_by_id(funcao_tecnica_id,
                                                 raise_if_not_found=True)
    except FuncaoTecnica.RecordNotFoundError:
        flash("Função técnica não encontrada.", category='warning')
        return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))

    # Conta o número de pessoas executando esta função
    numero_de_pessoas = len(funcao_tecnica.pessoas)

    form = FuncaoTecnicaEditForm()
    if request.method == 'GET':
        # Preenche o formulário com os dados atuais da função técnica
        form.nome.data = funcao_tecnica.nome
        form.descricao.data = funcao_tecnica.descricao
        form.ativo.data = funcao_tecnica.ativo

    if form.validate_on_submit():
        # Atualiza os campos da função técnica usando os dados do formulário WTForms
        funcao_tecnica.nome = form.nome.data.strip()
        funcao_tecnica.descricao = form.descricao.data
        funcao_tecnica.ativo = form.ativo.data

        # Salva as alterações no banco de dados
        try:
            db.session.commit()
            flash("Função técnica atualizada com sucesso.", category='success')
            return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar função técnica: {e}")
            flash("Ocorreu um erro ao atualizar a função técnica. Tente novamente.",
                  category='danger')

    return render_template('funcao_tecnica/web/editar.jinja2',
                           title="Editar função técnica",
                           form=form,
                           numero_de_pessoas=numero_de_pessoas)


@funcao_tecnica_bp.route('/<uuid:funcao_tecnica_id>/delete', methods=['POST'])
@login_required
def deletar_funcao_tecnica(funcao_tecnica_id: uuid.UUID):
    """Deleta uma função técnica existente, se não tiver associações.

    Args:
        funcao_tecnica_id: UUID da função técnica a ser deletada

    Returns:
        Redirect para a lista de funções técnicas
    """
    try:
        funcao_tecnica = FuncaoTecnica.get_by_id(funcao_tecnica_id,
                                                 raise_if_not_found=True)
    except FuncaoTecnica.RecordNotFoundError:
        flash("Função técnica não encontrada.", category='warning')
        return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))

    # Verifica se há pessoas executando esta função
    numero_de_pessoas = len(funcao_tecnica.pessoas_executando)
    if numero_de_pessoas > 0:
        flash(
            f"Não é possível excluir a função técnica '{funcao_tecnica.nome}' pois ela está "
            f"associada a {numero_de_pessoas} pessoa(s) em filme(s).",
            category='danger'
        )
        return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))

    # Salva o nome antes de deletar (para a mensagem)
    nome_funcao = funcao_tecnica.nome

    # Deleta a função técnica
    try:
        db.session.delete(funcao_tecnica)
        db.session.commit()
        flash(f"Função técnica '{nome_funcao}' excluída com sucesso.", category='success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar função técnica: {e}")
        flash("Ocorreu um erro ao excluir a função técnica. Tente novamente.", category='danger')

    return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))


@funcao_tecnica_bp.route('/<uuid:funcao_tecnica_id>/pessoas', methods=['GET'])
def listar_pessoas_da_funcao(funcao_tecnica_id: uuid.UUID):
    """Lista todas as pessoas que executam uma função técnica específica.

    Args:
        funcao_tecnica_id: UUID da função técnica

    Query Parameters:
        page (int): Número da página (padrão: 1)
        per_page (int): Itens por página (padrão: 20)
        search (str): Filtro de busca por nome

    Returns:
        Template renderizado com a lista paginada de pessoas da função técnica
    """
    from app.services.pessoa_service import PessoaService

    # Busca a função técnica
    try:
        funcao_tecnica = FuncaoTecnica.get_by_id(funcao_tecnica_id, raise_if_not_found=True)
    except FuncaoTecnica.RecordNotFoundError:
        flash("Função técnica não encontrada.", category='warning')
        return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))

    # Parâmetros de paginação e busca
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)
    search = request.args.get('search', default=None, type=str)

    # Limita per_page ao máximo configurado
    max_per_page = current_app.config.get('MAX_PER_PAGE', 500)
    per_page = min(per_page, max_per_page)

    # Busca pessoas da função técnica usando o service
    pagination = PessoaService.listar_pessoas_por_funcao_tecnica(
        funcao_tecnica=funcao_tecnica,
        page=page,
        per_page=per_page,
        search=search
    )

    return render_template('funcao_tecnica/web/pessoas.jinja2',
                           title=f"Pessoas - {funcao_tecnica.nome}",
                           funcao_tecnica=funcao_tecnica,
                           pagination=pagination,
                           page=page,
                           per_page=per_page,
                           search=search)
