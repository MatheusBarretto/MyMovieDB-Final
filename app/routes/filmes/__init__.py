import json
import uuid

from flask import abort, Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.forms.filmes import AdicionarElencoForm, AdicionarEquipeTecnicaForm, AvaliacaoForm, \
    EditarElencoForm, EditarEquipeTecnicaForm, FilmeCrudForm, FilmeDeleteForm
from app.infra.modulos import db
from app.models.filme import Filme, FuncaoTecnica
from app.models.juncoes import Atuacao, EquipeTecnica
from app.services.elencoequipe_service import ElencoEquipeService, ElencoEquipeServiceError
from app.services.filme_service import FilmeOperationResult, FilmeService, FilmeServiceError
from app.services.imageprocessing_service import ImageProcessingService
from app.services.review_service import ReviewOperationResult, ReviewService

filme_bp = Blueprint(name='filme',
                     import_name=__name__,
                     url_prefix='/filme',
                     template_folder="templates", )


# Funções auxiliares para operações CRUD de filmes

def _preparar_form_data_filme(form: FilmeCrudForm) -> dict:
    """Extrai e prepara dados do formulário de filme para o serviço.

    Args:
        form: Formulário de filme validado

    Returns:
        dict: Dicionário com dados do filme prontos para o serviço
    """
    form_data = {
        'titulo_original'                : form.titulo_original.data,
        'titulo_portugues'               : form.titulo_portugues.data,
        'ano_lancamento'                 : form.ano_lancamento.data,
        'lancado'                        : form.lancado.data,
        'duracao_minutos'                : form.duracao_minutos.data,
        'sinopse'                        : form.sinopse.data,
        'orcamento_milhares'             : form.orcamento_milhares.data,
        'faturamento_lancamento_milhares': form.faturamento_lancamento_milhares.data,
        'trailer_youtube'                : form.trailer_youtube.data,
        'poster'                         : form.poster.data,
        'generos_selecionados'           : []
    }

    # Processar IDs de gêneros do campo oculto
    try:
        genero_ids_str = form.generos_selecionados.data or '[]'
        genero_ids = json.loads(genero_ids_str)
        form_data['generos_selecionados'] = genero_ids
    except (json.JSONDecodeError, TypeError):
        form_data['generos_selecionados'] = []

    return form_data


def _processar_resultado_filme(result: FilmeOperationResult, success_url: str):
    """Processa resultado da operação de filme e exibe mensagens apropriadas.

    Args:
        result: Resultado da operação do FilmeService
        success_url: URL para redirecionamento em caso de sucesso

    Returns:
        flask.Response: Redirecionamento para a URL apropriada
    """
    if result.success:
        flash(result.message, category='success')
        return redirect(success_url)
    else:
        flash(result.message, category='error')
        return None


@filme_bp.route('/random', methods=['GET'])
def random_filme():
    """Seleciona um filme aleatório e redireciona para sua página de detalhes.

    Returns:
        flask.Response: Redirecionamento para a rota detail_filme
    """
    # Retorna apenas os dados do Filme, sem dados relacionados (joined)
    filme = db.session.scalar(select(Filme).order_by(func.random()))

    if filme is None:
        flash("Nenhum filme encontrado no banco de dados.", category='info')
        return redirect(url_for('filme.listar_filmes'))

    return redirect(url_for('filme.detail_filme', filme_id=filme.id))


@filme_bp.route('/<uuid:filme_id>/avaliar', methods=['POST'])
@login_required
def avaliar_filme(filme_id):
    """Cria ou atualiza uma avaliação do filme pelo usuário atual.

    Args:
        filme_id (uuid.UUID): ID do filme a ser avaliado.

    Returns:
        flask.Response: Redireciona de volta para a página do filme.
    """
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = AvaliacaoForm()

    if form.validate_on_submit():
        # Usar o ReviewService para criar/atualizar a avaliação
        resultado = ReviewService.criar_ou_atualizar_avaliacao(
                filme=filme,
                usuario=current_user,
                nota=form.nota.data,
                comentario=form.comentario.data or None,
                recomendaria=form.recomendaria.data
        )

        # Processar resultado
        if resultado.status in [ReviewOperationResult.CREATED, ReviewOperationResult.UPDATED]:
            flash(resultado.message, category='success')
        else:
            flash(resultado.message, category='error')

    # Redireciona para a página de detalhes do mesmo filme
    return redirect(url_for('filme.detail_filme', filme_id=filme_id))


@filme_bp.route('/avaliacao/<uuid:avaliacao_id>/excluir', methods=['POST'])
@login_required
def excluir_avaliacao(avaliacao_id):
    """Exclui uma avaliação do usuário atual.

    Args:
        avaliacao_id (uuid.UUID): ID da avaliação a ser excluída.

    Returns:
        flask.Response: Redireciona de volta para a página do filme.
    """
    # Busca a avaliação antes de excluir para obter o filme_id
    from app.models.juncoes import Avaliacao
    try:
        avaliacao = Avaliacao.get_by_id(avaliacao_id,
                                        raise_if_not_found=True)
        filme_id = avaliacao.filme_id
    except Avaliacao.RecordNotFoundError:
        flash("Avaliação não encontrada.", category='error')
        return redirect(url_for('filme.listar_filmes'))

    # Usar o ReviewService para excluir a avaliação
    resultado = ReviewService.excluir_avaliacao(avaliacao_id, current_user)

    # Processar resultado
    if resultado.status == ReviewOperationResult.DELETED:
        flash(resultado.message, category='success')
    else:
        flash(resultado.message, category='error')

    # Redireciona para a página de detalhes do mesmo filme
    return redirect(url_for('filme.detail_filme', filme_id=filme_id))


@filme_bp.route('/<uuid:filme_id>/poster', methods=['GET'])
def filme_poster(filme_id):
    """Serve o poster do filme

    Args:
        filme_id (uuid.UUID): ID do filme.

    Returns:
        flask.Response: Imagem do poster ou placeholder.
    """
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        # Filme não encontrado - retorna placeholder
        poster_data = ImageProcessingService.gerar_placeholder(300, 400,
                                                               "Filme\nnão encontrado",
                                                               36)
        mime_type = 'image/png'
    else:
        poster_data, mime_type = filme.poster
    return ImageProcessingService.servir_imagem(poster_data, mime_type)


@filme_bp.route('/<uuid:filme_id>/detail', methods=['GET'])
def detail_filme(filme_id):
    """Apresenta um filme do banco de dados.

    Returns:
        Template renderizado com o filme
    """
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        abort(404)

    # Retorna dados do filme com IDs de relacionamento se usuário autenticado
    if current_user.is_authenticated:
        elenco = FilmeService.obter_elenco(filme, incluir_atuacao_id=True)
        equipe_tecnica = FilmeService.obter_equipe_tecnica(filme, incluir_equipe_id=True)
    else:
        elenco = FilmeService.obter_elenco(filme)
        equipe_tecnica = FilmeService.obter_equipe_tecnica(filme)
    estatisticas = FilmeService.obter_estatisticas_avaliacoes(filme)

    # Buscar avaliação do usuário atual (se autenticado)
    avaliacao_usuario = None
    if current_user.is_authenticated:
        avaliacao_usuario = ReviewService.obter_avaliacao_usuario(filme, current_user)

    # Inicializar formulário de avaliação
    form = AvaliacaoForm()

    # Preencher formulário com dados existentes apenas em GET
    if request.method == 'GET' and avaliacao_usuario:
        # Definir os valores diretamente nos campos
        form.nota.data = avaliacao_usuario.nota
        form.comentario.data = avaliacao_usuario.comentario
        form.recomendaria.data = avaliacao_usuario.recomendaria

    # Buscar todas as avaliações do filme
    avaliacoes = ReviewService.obter_avaliacoes_filme(filme)

    return render_template('filme/web/details.jinja2',
                           title=f"Detalhes de '{filme.titulo_portugues}'",
                           elenco=elenco,
                           equipe_tecnica=equipe_tecnica,
                           estatisticas=estatisticas,
                           filme=filme,
                           form=form,
                           avaliacao_usuario=avaliacao_usuario,
                           avaliacoes=avaliacoes)


@filme_bp.route('/', methods=['GET'])
def listar_filmes():
    """Lista filmes com paginação e busca por título.

    Parâmetros de query string:
        page (int): Número da página (padrão: 1)
        per_page (int): Registros por página (padrão: 12)
        search (str): Termo de busca para filtrar por título

    Returns:
        Template renderizado com lista paginada de filmes
    """
    # Obter parâmetros da query string
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    search = request.args.get('search', '', type=str)

    # Limitar per_page para evitar sobrecarga
    per_page = min(per_page, 100)

    try:
        # Obter filmes paginados usando o serviço
        pagination = FilmeService.listar_filmes(
            page=page,
            per_page=per_page,
            search=search if search.strip() else None
        )

        return render_template('filme/web/lista.jinja2',
                             title="Lista de Filmes",
                             pagination=pagination,
                             search=search,
                             per_page=per_page)

    except Exception as e:
        current_app.logger.error(f"Erro ao listar filmes: {str(e)}")
        abort(500)


@filme_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_filme():
    """Trata requisição GET para exibir formulário de criação e POST para processar submissão.

    Returns:
        flask.Response: Template renderizado para GET ou redirecionamento para POST bem-sucedido
    """
    form = FilmeCrudForm()

    if request.method == 'POST':
        # Cuida do botão de cancelamento
        if form.cancel.data:
            return redirect(url_for('filme.listar_filmes'))

        if form.validate_on_submit():
            try:
                # Preparar dados do formulário usando função auxiliar
                form_data = _preparar_form_data_filme(form)

                # Criar filme usando o serviço
                result = FilmeService.create_filme(form_data)

                # Processar resultado usando função auxiliar
                response = _processar_resultado_filme(
                        result,
                        url_for('filme.detail_filme',
                                filme_id=result.filme.id) if result.success else None
                )
                if response:
                    return response

            except FilmeServiceError as e:
                current_app.logger.error("Erro ao criar filme: %s", (str(e),))
                flash(f"Erro ao criar filme. Tente novamente", category='error')
            except Exception as e:
                current_app.logger.error("Erro ao criar filme: %s", (str(e),))
                flash("Erro interno do sistema. Tente novamente.", category='error')
        # else:
        #     # Mostrar erros de validação do formulário
        #     for field, errors in form.errors.items():
        #         for error in errors:
        #             flash(f"Erro no campo {field}: {error}", category='error')

    return render_template('filme/web/create.jinja2',
                           title="Criar Novo Filme",
                           form=form)


@filme_bp.route('/<uuid:filme_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_filme(filme_id):
    """Trata requisição GET para exibir formulário pré-populado de edição e POST para processar
    atualizações.

    Args:
        filme_id (uuid.UUID): ID do filme a ser editado

    Returns:
        flask.Response: Template renderizado para GET ou redirecionamento para POST bem-sucedido
    """
    # Verificar existência do filme e tratar casos 404
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = FilmeCrudForm(obj=filme)

    if request.method == 'GET':
        # Pre-popula os campos do formulário
        form.titulo_original.data = filme.titulo_original
        form.titulo_portugues.data = filme.titulo_portugues
        form.ano_lancamento.data = filme.ano_lancamento
        form.lancado.data = filme.lancado
        form.duracao_minutos.data = filme.duracao_minutos
        form.sinopse.data = filme.sinopse
        form.orcamento_milhares.data = filme.orcamento_milhares
        form.faturamento_lancamento_milhares.data = filme.faturamento_lancamento_milhares
        form.trailer_youtube.data = filme.trailer_youtube

        # Pre-popula seleção de gêneros
        genero_ids = FilmeService.obter_genero_ids(filme)
        form.generos_selecionados.data = json.dumps(genero_ids)

    elif request.method == 'POST':
        # Cuida do botão de cancelamento
        if form.cancel.data:
            return redirect(url_for('filme.detail_filme', filme_id=filme_id))

        if form.validate_on_submit():
            try:
                # Preparar dados do formulário usando função auxiliar
                form_data = _preparar_form_data_filme(form)

                # Atualizar filme usando o serviço
                result = FilmeService.update_filme(filme_id, form_data)

                # Processar resultado usando função auxiliar
                response = _processar_resultado_filme(
                        result,
                        url_for('filme.detail_filme', filme_id=filme_id)
                )
                if response:
                    return response

            except FilmeServiceError as e:
                current_app.logger.error("Erro ao atualizar filme %s: %s", (filme_id, str(e),))
                flash(f"Erro ao atualizar filme. Tente novamente", category='error')
            except Exception as e:
                current_app.logger.error("Erro ao atualizar filme %s: %s", (filme_id, str(e),))
                flash("Erro interno do sistema. Tente novamente.", category='error')
        # else:
        #     # Mostrar erros de validação do formulário
        #     for field, errors in form.errors.items():
        #         for error in errors:
        #             flash(f"Erro no campo {field}: {error}", category='error')

    return render_template('filme/web/edit.jinja2',
                           title=f"Editar '{filme.titulo_original}'",
                           form=form,
                           filme=filme)


@filme_bp.route('/<uuid:filme_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_filme(filme_id):
    """Trata requisição GET para exibir confirmação de exclusão e POST para processar a exclusão.

    Args:
        filme_id (uuid.UUID): ID do filme a ser excluído

    Returns:
        flask.Response: Template renderizado para GET ou redirecionamento para POST bem-sucedido
    """
    # Validate filme existence and handle 404 cases
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = FilmeDeleteForm(obj=filme)

    if request.method == 'POST':
        # Handle cancel button
        if form.cancel.data:
            return redirect(url_for('filme.detail_filme', filme_id=filme_id))

        if form.validate_on_submit():
            try:
                # Delete filme using service
                result = FilmeService.delete_filme(filme_id)

                if result.success:
                    flash(result.message, category='success')
                    return redirect(url_for('filme.listar_filmes'))
                else:
                    flash(result.message, category='error')

            except FilmeServiceError as e:
                current_app.logger.error("Erro ao remover filme %s: %s", (filme_id, str(e),))
                flash(f"Erro ao remover filme. Tente novamente", category='error')
            except Exception as e:
                current_app.logger.error("Erro ao remover filme %s: %s", (filme_id, str(e),))
                flash("Erro interno do sistema. Tente novamente.", category='error')
        # else:
        #     # Show form validation errors
        #     for field, errors in form.errors.items():
        #         for error in errors:
        #             flash(f"Erro no campo {field}: {error}", category='error')

    return render_template('filme/web/delete.jinja2',
                           title=f"Excluir '{filme.titulo_original}'",
                           form=form,
                           filme=filme)


@filme_bp.route('/<uuid:filme_id>/elenco/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_elenco(filme_id):
    """Adiciona um ator ao elenco do filme.

    Args:
        filme_id (uuid.UUID): ID do filme.

    Returns:
        flask.Response: Template de adição ou redirecionamento após sucesso.
    """
    try:
        filme = Filme.get_by_id(filme_id, raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = AdicionarElencoForm()

    if form.validate_on_submit():
        try:
            # Convert string UUIDs to UUID objects
            try:
                pessoa_uuid = uuid.UUID(form.pessoa_id.data)
            except (ValueError, TypeError):
                flash("ID da pessoa inválido.", category='error')
                return render_template('filme/web/adicionar_elenco.jinja2',
                                       title=f"Adicionar Elenco - "
                                             f"{filme.titulo_portugues or filme.titulo_original}",
                                       filme=filme,
                                       form=form)

            # Usar o ElencoEquipeService para adicionar o ator ao elenco
            resultado = ElencoEquipeService.adicionar_elenco(
                    filme_id=filme_id,
                    pessoa_id=pessoa_uuid,
                    personagem=form.personagem.data,
                    creditado=form.creditado.data,
                    tempo_de_tela_minutos=form.tempo_de_tela_minutos.data
            )

            # Processar resultado
            if resultado.success:
                flash(resultado.message, category='success')
                return redirect(url_for('filme.detail_filme', filme_id=filme_id))
            else:
                flash(resultado.message, category='error')

        except ElencoEquipeServiceError as e:
            current_app.logger.error("Erro ao adicionar ator %s ao elenco "
                                     "do filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash(f"Erro ao adicionar o ator ao elenco. Tente novamente", category='error')
        except Exception as e:
            current_app.logger.error("Erro ao adicionar ator %s ao elenco "
                                     "do filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash("Erro interno do sistema. Tente novamente.", category='error')

    # Renderizar template de adição
    return render_template('filme/web/adicionar_elenco.jinja2',
                           title=f"Adicionar Ele"
                                 f"nco - {filme.titulo_portugues or filme.titulo_original}",
                           filme=filme,
                           form=form)


@filme_bp.route('/<uuid:filme_id>/elenco/<uuid:atuacao_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_elenco(filme_id, atuacao_id):
    """Edita uma atuação existente no elenco do filme.

    Args:
        filme_id (uuid.UUID): ID do filme.
        atuacao_id (uuid.UUID): ID da atuação a ser editada.

    Returns:
        flask.Response: Template de edição ou redirecionamento após sucesso.
    """
    try:
        filme = Filme.get_by_id(filme_id, raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    try:
        atuacao: Atuacao = Atuacao.get_by_id(atuacao_id, raise_if_not_found=True)
    except Atuacao.RecordNotFoundError:
        flash("Atuação não encontrada.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Verificar se a atuação pertence ao filme correto
    if atuacao.filme_id != filme_id:
        flash("Atuação não pertence a este filme.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Create a reference object for CampoImutavel validation
    class AtuacaoRef:
        def __init__(self, atuacao):
            self.pessoa_id = str(atuacao.ator.pessoa.id)
            self.personagem = atuacao.personagem

    form = EditarElencoForm()
    form.reference_obj = AtuacaoRef(atuacao)

    # Pré-preencher formulário em GET
    if request.method == 'GET':
        form.pessoa_id.data = str(atuacao.ator.pessoa.id)
        form.personagem.data = atuacao.personagem
        form.creditado.data = atuacao.creditado
        form.tempo_de_tela_minutos.data = atuacao.tempo_de_tela_minutos

        # Renderizar template de edição para GET
        return render_template('filme/web/editar_elenco.jinja2',
                               title=f"Editar Elenco - "
                                     f"{filme.titulo_portugues or filme.titulo_original}",
                               filme=filme,
                               atuacao=atuacao,
                               form=form)

    if form.validate_on_submit():
        try:
            # Usar o ElencoEquipeService para editar a atuação
            resultado = ElencoEquipeService.editar_elenco(
                    atuacao_id=atuacao_id,
                    pessoa_id=uuid.UUID(form.pessoa_id.data),
                    personagem=form.personagem.data,
                    creditado=form.creditado.data,
                    tempo_de_tela_minutos=form.tempo_de_tela_minutos.data
            )

            # Processar resultado
            if resultado.success:
                flash(resultado.message, category='success')
                return redirect(url_for('filme.detail_filme', filme_id=filme_id))
            else:
                flash(resultado.message, category='error')

        except ElencoEquipeServiceError as e:
            current_app.logger.error("Erro ao alterar ator %s do elenco "
                                     "do filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash(f"Erro ao alterar o elenco. Tente novamente", category='error')
        except Exception as e:
            current_app.logger.error("Erro ao alterar ator %s do elenco "
                                     "do filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash("Erro interno do sistema. Tente novamente.", category='error')

    # Renderizar template de edição para POST com erros
    return render_template('filme/web/editar_elenco.jinja2',
                           title=f"Editar Ele"
                                 f"nco - {filme.titulo_portugues or filme.titulo_original}",
                           filme=filme,
                           atuacao=atuacao,
                           form=form)


@filme_bp.route('/<uuid:filme_id>/elenco/<uuid:atuacao_id>/remover', methods=['GET', 'POST'])
@login_required
def remover_elenco(filme_id, atuacao_id):
    """Remove uma atuação do elenco do filme.

    Args:
        filme_id (uuid.UUID): ID do filme.
        atuacao_id (uuid.UUID): ID da atuação a ser removida.

    Returns:
        flask.Response: Template de confirmação ou redirecionamento após remoção.
    """
    try:
        filme = Filme.get_by_id(filme_id, raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    try:
        atuacao: Atuacao = Atuacao.get_by_id(atuacao_id, raise_if_not_found=True)
    except Atuacao.RecordNotFoundError:
        flash("Atuação não encontrada.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Verificar se a atuação pertence ao filme correto
    if atuacao.filme_id != filme_id:
        flash("Atuação não pertence a este filme.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Se for POST, processar a remoção
    if request.method == 'POST':
        try:
            # Usar o ElencoEquipeService para remover a atuação
            resultado = ElencoEquipeService.remover_elenco(atuacao_id=atuacao_id)

            # Processar resultado
            if resultado.success:
                flash(resultado.message, category='success')
            else:
                flash(resultado.message, category='error')

        except ElencoEquipeServiceError as e:
            current_app.logger.error("Erro ao remover atuacao %s: %s", (atuacao_id, str(e),))
            flash(f"Erro ao remover a atuação. Tente novamente", category='error')
        except Exception as e:
            current_app.logger.error("Erro ao remover atuacao %s: %s", (atuacao_id, str(e),))
            flash("Erro interno do sistema. Tente novamente.", category='error')

        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Se for GET, mostrar página de confirmação
    return render_template('filme/web/remover_elenco.jinja2',
                           title=f"Remover Ele"
                                 f"nco - {filme.titulo_portugues or filme.titulo_original}",
                           filme=filme,
                           atuacao=atuacao)


@filme_bp.route('/<uuid:filme_id>/equipe-tecnica/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_equipe_tecnica(filme_id):
    """Adiciona uma pessoa à equipe técnica do filme.

    Args:
        filme_id (uuid.UUID): ID do filme.

    Returns:
        flask.Response: Template de adição ou redirecionamento após sucesso.
    """
    try:
        filme = Filme.get_by_id(filme_id, raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = AdicionarEquipeTecnicaForm()

    form.funcao_tecnica_id.choices = FuncaoTecnica.get_choices_for_dropdown()

    if form.validate_on_submit():
        try:
            # Usar o ElencoEquipeService para adicionar a pessoa à equipe técnica
            resultado = ElencoEquipeService.adicionar_equipe_tecnica(
                    filme_id=filme_id,
                    pessoa_id=uuid.UUID(form.pessoa_id.data),
                    funcao_tecnica_id=uuid.UUID(form.funcao_tecnica_id.data),
                    creditado=form.creditado.data
            )

            # Processar resultado
            if resultado.success:
                flash(resultado.message, category='success')
                return redirect(url_for('filme.detail_filme', filme_id=filme_id))
            else:
                flash(resultado.message, category='error')

        except ElencoEquipeServiceError as e:
            current_app.logger.error("Erro ao adicionar pessoa %s à equipe técnica do "
                                     "filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash(f"Erro ao adicionar membro da equipe técnica. Tente novamente", category='error')
        except Exception as e:
            current_app.logger.error("Erro ao adicionar pessoa %s à equipe técnica do "
                                     "filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash("Erro interno do sistema. Tente novamente.", category='error')

    # Renderizar template de adição
    return render_template('filme/web/adicionar_equipe_tecnica.jinja2',
                           title=f"Adicionar Equipe Técn"
                                 f"ica - {filme.titulo_portugues or filme.titulo_original}",
                           filme=filme,
                           form=form)


@filme_bp.route('/<uuid:filme_id>/equipe-tecnica/<uuid:equipe_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_equipe_tecnica(filme_id, equipe_id):
    """Edita uma entrada existente na equipe técnica do filme.

    Args:
        filme_id (uuid.UUID): ID do filme.
        equipe_id (uuid.UUID): ID da entrada na equipe técnica a ser editada.

    Returns:
        flask.Response: Redireciona de volta para a página do filme.
    """
    try:
        filme = Filme.get_by_id(filme_id, raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    try:
        equipe_tecnica = EquipeTecnica.get_by_id(equipe_id, raise_if_not_found=True)
    except EquipeTecnica.RecordNotFoundError:
        flash("Entrada na equipe técnica não encontrada.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Verificar se a entrada na equipe técnica pertence ao filme correto
    if equipe_tecnica.filme_id != filme_id:
        flash("Entrada na equipe técnica não pertence a este filme.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Create a reference object for CampoImutavel validation
    class EquipeRef:
        def __init__(self, equipe):
            self.pessoa_id = str(equipe.pessoa.id)
            self.funcao_tecnica_id = str(equipe.funcao_tecnica.id)

    form = EditarEquipeTecnicaForm()
    form.reference_obj = EquipeRef(equipe_tecnica)

    form.funcao_tecnica_id.choices = FuncaoTecnica.get_choices_for_dropdown()

    # Pré-preencher formulário em GET
    if request.method == 'GET':
        form.pessoa_id.data = str(equipe_tecnica.pessoa.id)
        form.funcao_tecnica_id.data = str(equipe_tecnica.funcao_tecnica.id)
        form.creditado.data = equipe_tecnica.creditado

        # Renderizar template de edição para GET
        return render_template('filme/web/editar_equipe_tecnica.jinja2',
                               title=f"Editar Equipe Técnica - "
                                     f"{filme.titulo_portugues or filme.titulo_original}",
                               filme=filme,
                               equipe_tecnica=equipe_tecnica,
                               form=form)

    if form.validate_on_submit():
        try:
            # Usar o ElencoEquipeService para editar a entrada na equipe técnica
            resultado = ElencoEquipeService.editar_equipe_tecnica(
                    equipe_id=equipe_id,
                    pessoa_id=uuid.UUID(form.pessoa_id.data),
                    funcao_tecnica_id=uuid.UUID(form.funcao_tecnica_id.data),
                    creditado=form.creditado.data
            )

            # Processar resultado
            if resultado.success:
                flash(resultado.message, category='success')
                return redirect(url_for('filme.detail_filme', filme_id=filme_id))
            else:
                flash(resultado.message, category='error')

        except ElencoEquipeServiceError as e:
            current_app.logger.error("Erro ao alterar pessoa %s à equipe técnica do "
                                     "filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash(f"Erro ao alterar membro da equipe técnica. Tente novamente", category='error')
        except Exception as e:
            current_app.logger.error("Erro ao alterar pessoa %s à equipe técnica do "
                                     "filme %s: %s", (form.pessoa_id.data, filme_id, str(e),))
            flash("Erro interno do sistema. Tente novamente.", category='error')

    # Renderizar template de edição
    return render_template('filme/web/editar_equipe_tecnica.jinja2',
                           title=f"Editar Equipe Técnica - "
                                 f"{filme.titulo_portugues or filme.titulo_original}",
                           filme=filme,
                           equipe_tecnica=equipe_tecnica,
                           form=form)


@filme_bp.route('/<uuid:filme_id>/equipe-tecnica/<uuid:equipe_id>/remover', methods=['GET', 'POST'])
@login_required
def remover_equipe_tecnica(filme_id, equipe_id):
    """Remove uma entrada da equipe técnica do filme.

    Args:
        filme_id (uuid.UUID): ID do filme.
        equipe_id (uuid.UUID): ID da entrada na equipe técnica a ser removida.

    Returns:
        flask.Response: Template de confirmação ou redirecionamento após remoção.
    """
    try:
        filme = Filme.get_by_id(filme_id, raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    try:
        equipe_tecnica = EquipeTecnica.get_by_id(equipe_id, raise_if_not_found=True)
    except EquipeTecnica.RecordNotFoundError:
        flash("Entrada na equipe técnica não encontrada.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Verificar se a entrada na equipe técnica pertence ao filme correto
    if equipe_tecnica.filme_id != filme_id:
        flash("Entrada na equipe técnica não pertence a este filme.", category='error')
        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Se for POST, processar a remoção
    if request.method == 'POST':
        try:
            # Usar o ElencoEquipeService para remover a entrada da equipe técnica
            resultado = ElencoEquipeService.remover_equipe_tecnica(equipe_id=equipe_id)

            # Processar resultado
            if resultado.success:
                flash(resultado.message, category='success')
            else:
                flash(resultado.message, category='error')

        except ElencoEquipeServiceError as e:
            current_app.logger.error("Erro ao remover entrada de equipe técnica %s: %s",
                                     (equipe_id, str(e),))
            flash(f"Erro ao remover membro da equipe técnica. Tente novamente", category='error')
        except Exception as e:
            current_app.logger.error("Erro ao remover entrada de equipe técnica %s: %s",
                                     (equipe_id, str(e),))
            flash("Erro interno do sistema. Tente novamente.", category='error')

        return redirect(url_for('filme.detail_filme', filme_id=filme_id))

    # Se for GET, mostrar página de confirmação
    return render_template('filme/web/remover_equipe_tecnica.jinja2',
                           title=f"Remover Equipe Técnica - "
                                 f"{filme.titulo_portugues or filme.titulo_original}",
                           filme=filme,
                           equipe_tecnica=equipe_tecnica)
