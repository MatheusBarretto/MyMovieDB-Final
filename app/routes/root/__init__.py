from flask import Blueprint, render_template, request, current_app

from app.models.filme import Filme
from app.models.pessoa import Pessoa
from app.services.search_service import SearchService, SearchServiceError

root_bp = Blueprint('root',
                    __name__,
                    url_prefix='/',
                    template_folder='templates',
                    )


@root_bp.route("/")
def index():
    """
    Retorna a página principal da aplicação.

    Returns:
        str: Página HTML da página principal.
    """
    # Obtém a contagem de filmes e pessoas cadastrados
    total_filmes = Filme.count_all()
    total_pessoas = Pessoa.count_all()

    return render_template("root/index.jinja2",
                           title="Página principal",
                           total_filmes=total_filmes,
                           total_pessoas=total_pessoas)


@root_bp.route("/buscar")
def buscar():
    """
    Executa busca genérica em filmes e pessoas.

    Recebe o termo de busca via parâmetro 'q' da query string,
    valida a entrada e executa a busca usando o SearchService.

    Returns:
        str: Página HTML com resultados da busca ou mensagens de erro.
    """
    # Obtém o termo de busca da query string
    termo_busca = request.args.get('q', '').strip()
    
    # Log da tentativa de busca
    current_app.logger.info(f"Busca solicitada com termo: '{termo_busca}'")
    
    # Validação de entrada - mínimo 2 caracteres
    if not termo_busca:
        current_app.logger.warning("Busca tentada sem termo")
        return render_template("root/buscar.jinja2",
                             title="Buscar",
                             erro="Por favor, digite um termo para buscar.",
                             termo_busca="")
    
    if len(termo_busca) < 2:
        current_app.logger.warning(f"Busca tentada com termo muito curto: '{termo_busca}'")
        return render_template("root/buscar.jinja2",
                             title="Buscar",
                             erro="O termo de busca deve ter pelo menos 2 caracteres.",
                             termo_busca=termo_busca)
    
    try:
        # Executa a busca usando o SearchService
        resultado = SearchService.buscar_geral(termo_busca)
        
        # Log do resultado
        current_app.logger.info(
            f"Busca concluída para '{termo_busca}': "
            f"{resultado.total_filmes} filmes, {resultado.total_pessoas} pessoas"
        )
        
        # Renderiza template com resultados
        return render_template("root/buscar.jinja2",
                             title=f"Resultados para '{termo_busca}'",
                             resultado=resultado,
                             termo_busca=termo_busca)
        
    except SearchServiceError as e:
        # Log do erro específico do serviço
        current_app.logger.error(f"Erro no SearchService para termo '{termo_busca}': {str(e)}")
        return render_template("root/buscar.jinja2",
                             title="Buscar",
                             erro="Erro interno na busca. Tente novamente.",
                             termo_busca=termo_busca)
        
    except Exception as e:
        # Log de erro inesperado
        current_app.logger.error(f"Erro inesperado na busca para termo '{termo_busca}': {str(e)}")
        return render_template("root/buscar.jinja2",
                             title="Buscar",
                             erro="Erro interno na busca. Tente novamente.",
                             termo_busca=termo_busca)
