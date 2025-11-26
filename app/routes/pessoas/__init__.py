from flask import abort, Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app.models import Pessoa
from app.services.imageprocessing_service import ImageProcessingService
from app.services.pessoa_service import PessoaService, PessoaError
from app.services.ator_service import AtorService
from app.forms.pessoas import PessoaForm

pessoa_bp = Blueprint(name='pessoa',
                      import_name=__name__,
                      url_prefix='/pessoa',
                      template_folder="templates", )


@pessoa_bp.route('/', methods=['GET'])
def pessoa_list():
    """Lista pessoas com paginação e busca por nome.
    
    Parâmetros de query string:
        page (int): Número da página (padrão: 1)
        per_page (int): Registros por página (padrão: 20)
        search (str): Termo de busca para filtrar por nome
        
    Returns:
        Template renderizado com lista paginada de pessoas
        
    Requirements: 1.1, 1.2
    """
    # Obter parâmetros da query string
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    search = request.args.get('search', '', type=str)
    
    # Limitar per_page para evitar sobrecarga
    per_page = min(per_page, 100)
    
    try:
        # Obter pessoas paginadas usando o serviço
        pagination = PessoaService.listar_pessoas(
            page=page,
            per_page=per_page,
            search=search if search.strip() else None
        )
        
        return render_template('pessoa/web/list.jinja2',
                             title="Lista de Pessoas",
                             pagination=pagination,
                             search=search,
                             per_page=per_page,
                             current_user=current_user,
                             csrf_token=generate_csrf())
                             
    except Exception as e:
        current_app.logger.error(f"Erro ao listar pessoas: {str(e)}")
        abort(500)


@pessoa_bp.route('/<uuid:pessoa_id>/foto', methods=['GET'])
def pessoa_foto(pessoa_id):
    """Serve a foto da pessoa

    Args:
        pessoa_id (uuid.UUID): ID da pessoa.

    Returns:
        flask.Response: Imagem da foto da pessoa.
    """
    try:
        pessoa = Pessoa.get_by_id(pessoa_id,
                                  raise_if_not_found=True)
    except Pessoa.RecordNotFoundError:
        # Pessoa não encontrada - retorna placeholder
        foto_data = ImageProcessingService.gerar_placeholder(300, 400,
                                                                    "Pessoa\nnão encontrada",
                                                                    36)
        mime_type = 'image/png'
    else:
        foto_data, mime_type = pessoa.foto
    return ImageProcessingService.servir_imagem(foto_data, mime_type)


@pessoa_bp.route('/<uuid:pessoa_id>/detail', methods=['GET'])
def pessoa_detalhes(pessoa_id):
    """Apresenta os detalhes completos de uma pessoa.
    
    Args:
        pessoa_id (uuid.UUID): ID da pessoa
        
    Returns:
        Template renderizado com detalhes da pessoa
        
    Raises:
        404: Se a pessoa não for encontrada
    """
    try:
        pessoa = Pessoa.get_by_id(pessoa_id,
                                  raise_if_not_found=True)
    except Pessoa.RecordNotFoundError:
        abort(404)
    
    # Obter funções técnicas da pessoa
    funcoes_tecnicas = PessoaService.obter_funcoes(pessoa)
    
    # Obter papéis de atuação se a pessoa for ator
    papeis = []
    if pessoa.ator:
        papeis = AtorService.obter_papeis(pessoa.ator)
    
    return render_template('pessoa/web/details.jinja2',
                           title=f"Detalhes de '{pessoa.nome}'",
                           pessoa=pessoa,
                           papeis=papeis,
                           funcoes_tecnicas=funcoes_tecnicas,
                           csrf_token=generate_csrf())


@pessoa_bp.route('/create', methods=['GET', 'POST'])
@login_required
def pessoa_create():
    """Cria uma nova pessoa.
    
    GET: Exibe formulário de criação
    POST: Processa dados do formulário e cria nova pessoa
    
    Returns:
        GET: Template de criação com formulário
        POST: Redirect para detalhes da pessoa criada ou template com erros
        
    Requirements: 2.1, 2.4, 2.5, 6.2
    """
    form = PessoaForm()
    
    if form.validate_on_submit():
        try:
            # Validar unicidade da pessoa
            if not PessoaService.validar_pessoa_unica(
                form.nome.data, 
                form.data_nascimento.data
            ):
                flash('Já existe uma pessoa com este nome e data de nascimento.', 'error')
                return render_template('pessoa/web/create.jinja2',
                                     title="Criar Pessoa",
                                     form=form)
            
            # Criar nova pessoa
            pessoa = PessoaService.criar_pessoa(form)
            
            flash(f'Pessoa "{pessoa.nome}" criada com sucesso!', 'success')
            return redirect(url_for('pessoa.pessoa_detalhes', pessoa_id=pessoa.id))
            
        except PessoaError as e:
            current_app.logger.error(f"Erro ao criar pessoa: {str(e)}")
            flash('Erro ao criar pessoa. Tente novamente.', 'error')
        except Exception as e:
            current_app.logger.error(f"Erro inesperado ao criar pessoa: {str(e)}")
            flash('Erro inesperado. Tente novamente.', 'error')
    
    return render_template('pessoa/web/create.jinja2',
                         title="Criar Pessoa",
                         form=form)


@pessoa_bp.route('/<uuid:pessoa_id>/edit', methods=['GET', 'POST'])
@login_required
def pessoa_edit(pessoa_id):
    """Edita uma pessoa existente.
    
    GET: Exibe formulário de edição pré-preenchido com dados atuais
    POST: Processa dados do formulário e atualiza a pessoa
    
    Args:
        pessoa_id (uuid.UUID): ID da pessoa a ser editada
    
    Returns:
        GET: Template de edição com formulário pré-preenchido
        POST: Redirect para detalhes da pessoa atualizada ou template com erros
        
    Raises:
        404: Se a pessoa não for encontrada
        
    Requirements: 3.1, 3.4, 3.5, 6.2
    """
    try:
        pessoa = Pessoa.get_by_id(pessoa_id,
                                  raise_if_not_found=True)
    except Pessoa.RecordNotFoundError:
        abort(404)

    # Inicializar formulário: pré-preencher apenas em GET requests
    # Em POST requests, Flask-WTF já processou os dados do request
    if request.method == 'GET':
        form = PessoaForm(pessoa=pessoa)
    else:
        form = PessoaForm()
    
    if form.validate_on_submit():
        try:
            # Validar unicidade da pessoa (excluindo a pessoa atual)
            if not PessoaService.validar_pessoa_unica(
                form.nome.data, 
                form.data_nascimento.data,
                pessoa_id=pessoa.id
            ):
                flash('Já existe uma pessoa com este nome e data de nascimento.', 'error')
                return render_template('pessoa/web/edit.jinja2',
                                     title=f"Editar {pessoa.nome}",
                                     form=form,
                                     pessoa=pessoa)
            
            # Atualizar pessoa existente
            pessoa_atualizada = PessoaService.atualizar_pessoa(pessoa, form)
            
            flash(f'Pessoa "{pessoa_atualizada.nome}" atualizada com sucesso!', 'success')
            return redirect(url_for('pessoa.pessoa_detalhes', pessoa_id=pessoa_atualizada.id))
            
        except PessoaError as e:
            current_app.logger.error(f"Erro ao atualizar pessoa: {str(e)}")
            flash('Erro ao atualizar pessoa. Tente novamente.', 'error')
        except Exception as e:
            current_app.logger.error(f"Erro inesperado ao atualizar pessoa: {str(e)}")
            flash('Erro inesperado. Tente novamente.', 'error')
    
    return render_template('pessoa/web/edit.jinja2',
                         title=f"Editar {pessoa.nome}",
                         form=form,
                         pessoa=pessoa)


@pessoa_bp.route('/<uuid:pessoa_id>/delete', methods=['POST'])
@login_required
def pessoa_delete(pessoa_id):
    """Deleta uma pessoa existente.
    
    POST: Processa a deleção da pessoa com verificação de relacionamentos
    
    Args:
        pessoa_id (uuid.UUID): ID da pessoa a ser deletada
    
    Returns:
        Redirect para lista de pessoas com mensagem de sucesso ou erro
        
    Raises:
        404: Se a pessoa não for encontrada
        
    Requirements: 4.1, 4.2, 4.3, 4.5, 6.2
    """
    try:
        pessoa = Pessoa.get_by_id(pessoa_id,
                                  raise_if_not_found=True)
    except Pessoa.RecordNotFoundError:
        abort(404)
    
    try:
        # Tentar deletar a pessoa usando o serviço
        resultado = PessoaService.deletar_pessoa(pessoa)
        
        if resultado['success']:
            flash(f'Pessoa "{pessoa.nome}" deletada com sucesso!', 'success')
        else:
            # Pessoa tem relacionamentos - não pode ser deletada
            flash(resultado['message'], 'error')
            
            # Adicionar informações específicas sobre relacionamentos
            relacionamentos = resultado['relacionamentos']
            if relacionamentos['ator'] > 0:
                flash('A pessoa possui papéis de atuação em filmes.', 'warning')
            if relacionamentos['funcoes_tecnicas'] > 0:
                flash(f'A pessoa possui {relacionamentos["funcoes_tecnicas"]} função(ões) técnica(s) em filmes.', 'warning')
        
    except PessoaError as e:
        current_app.logger.error(f"Erro ao deletar pessoa: {str(e)}")
        flash('Erro ao deletar pessoa. Tente novamente.', 'error')
    except Exception as e:
        current_app.logger.error(f"Erro inesperado ao deletar pessoa: {str(e)}")
        flash('Erro inesperado. Tente novamente.', 'error')
    
    return redirect(url_for('pessoa.pessoa_list'))
