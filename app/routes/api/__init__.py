from flask import Blueprint, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import select, or_

from app import db
from app.models.pessoa import Pessoa, Ator
from app.models.filme import Genero, FuncaoTecnica

api_bp = Blueprint(name='api',
                    import_name=__name__,
                    url_prefix='/api',
                    template_folder="templates", )


@api_bp.route('/pessoas/search')
def search_pessoa():
    """Procura pessoas ou atores pelo nome ou nome artistico para uso em função de autocomplete

    Query Parameters:
        - q: String de busca (mínimo de 3 caracteres)
        - limit: Número máximo de resultados (default: 10, max: 50)

    Returns:
        JSON array de instâncias de Pessoa com id, nome e, se for o caso, nome artistico
    """
    if not current_user.is_authenticated:
        abort(403)

    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 10)), 50)

    if len(query) < 3:
        return jsonify([])

    try:
        # Procura uma pessoa pelo nome, ou pelo nome artistico (case-insensitive)
        search_pattern = f"%{query}%"

        # Query com LEFT JOIN para incluir informações do ator se existir
        stmt = (
            select(Pessoa, Ator)
            .outerjoin(Ator, Pessoa.id == Ator.pessoa_id)
            .where(
                or_(
                    Pessoa.nome.ilike(search_pattern),
                    Ator.nome_artistico.ilike(search_pattern)
                )
            )
            .order_by(Pessoa.nome)
            .limit(limit)
        )

        resultado = db.session.execute(stmt).all()

        # Convert to JSON format
        results = []
        for pessoa, ator in resultado:
            results.append({
                'id': str(pessoa.id),
                'nome': pessoa.nome,
                'nome_artistico': ator.nome_artistico if ator else None
            })

        return jsonify(results)

    except Exception as e:
        current_app.logger.error("Falha na busca de pessoa '%s' para autocomplete: %s", query, str(e))
        return jsonify([]), 500


@api_bp.route('/generos/search')
def search_genero():
    """Procura gêneros pelo nome para uso em função de autocomplete

    Query Parameters:
        - q: String de busca (mínimo de 2 caracteres)
        - limit: Número máximo de resultados (default: 10, max: 50)
        - only_active: Se True, retorna apenas gêneros ativos (default: True)

    Returns:
        JSON array de instâncias de Genero com id, nome e descricao
    """
    if not current_user.is_authenticated:
        abort(403)

    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 10)), 50)
    only_active = request.args.get('only_active', 'true').lower() in ('true', '1', 'yes')

    if len(query) < 2:
        return jsonify([])

    try:
        # Procura gênero pelo nome (case-insensitive)
        search_pattern = f"%{query}%"

        stmt = (
            select(Genero)
            .where(Genero.nome.ilike(search_pattern))
            .order_by(Genero.nome)
            .limit(limit)
        )

        # Filtra apenas ativos se solicitado
        if only_active:
            stmt = stmt.where(Genero.ativo == True)

        resultado = db.session.execute(stmt).scalars().all()

        # Convert to JSON format
        results = []
        for genero in resultado:
            results.append({
                'id': str(genero.id),
                'nome': genero.nome
            })

        return jsonify(results)

    except Exception as e:
        current_app.logger.error("Falha na busca de gênero '%s' para autocomplete: %s", query, str(e))
        return jsonify([]), 500


@api_bp.route('/funcoes-tecnicas/search')
def search_funcao_tecnica():
    """Procura funções técnicas pelo nome para uso em função de autocomplete

    Query Parameters:
        - q: String de busca (mínimo de 2 caracteres)
        - limit: Número máximo de resultados (default: 10, max: 50)
        - only_active: Se True, retorna apenas funções ativas (default: True)

    Returns:
        JSON array de instâncias de FuncaoTecnica com id, nome e descricao
    """
    if not current_user.is_authenticated:
        abort(403)

    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 10)), 50)
    only_active = request.args.get('only_active', 'true').lower() in ('true', '1', 'yes')

    if len(query) < 2:
        return jsonify([])

    try:
        # Procura função técnica pelo nome (case-insensitive)
        search_pattern = f"%{query}%"

        stmt = (
            select(FuncaoTecnica)
            .where(FuncaoTecnica.nome.ilike(search_pattern))
            .order_by(FuncaoTecnica.nome)
            .limit(limit)
        )

        # Filtra apenas ativos se solicitado
        if only_active:
            stmt = stmt.where(FuncaoTecnica.ativo == True)

        resultado = db.session.execute(stmt).scalars().all()

        # Convert to JSON format
        results = []
        for funcao in resultado:
            results.append({
                'id': str(funcao.id),
                'nome': funcao.nome
            })

        return jsonify(results)

    except Exception as e:
        current_app.logger.error("Falha na busca de função técnica '%s' para autocomplete: %s", query, str(e))
        return jsonify([]), 500
