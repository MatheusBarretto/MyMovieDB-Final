"""Serviço de busca genérica.

Este módulo fornece a camada de serviço para operações de busca genérica
em filmes e pessoas, permitindo pesquisar simultaneamente em ambas as entidades.

Classes principais:
    - SearchService: Serviço principal com métodos para busca genérica
    - SearchResult: Resultado consolidado da busca
    - FilmeSearchResult: Resultado específico para filmes
    - PessoaSearchResult: Resultado específico para pessoas
"""
import uuid
from dataclasses import dataclass
from typing import Optional

from flask import current_app
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.infra.modulos import db
from app.models.filme import Filme
from app.models.pessoa import Ator, Pessoa


class SearchServiceError(Exception):
    """Exceção customizada para operações do SearchService."""
    pass


@dataclass
class FilmeSearchResult:
    """Resultado de busca para um filme."""
    id: uuid.UUID
    titulo_original: str
    titulo_portugues: Optional[str]
    ano_lancamento: Optional[int]
    com_poster: bool


@dataclass
class PessoaSearchResult:
    """Resultado de busca para uma pessoa."""
    id: uuid.UUID
    nome: str
    nome_artistico: Optional[str]
    com_foto: bool
    eh_ator: bool


@dataclass
class SearchResult:
    """Resultado consolidado da busca genérica."""
    filmes: list[FilmeSearchResult]
    pessoas: list[PessoaSearchResult]
    termo_busca: str
    total_filmes: int
    total_pessoas: int


class SearchService:
    """Serviço para operações de busca genérica.

    Centraliza a lógica de busca simultânea em filmes e pessoas,
    fornecendo resultados organizados e limitados.
    """

    # Sessão padrão a ser utilizada quando nenhuma sessão é fornecida
    _default_session = db.session

    @classmethod
    def set_default_session(cls, session):
        """Define a sessão padrão a ser utilizada pelo serviço.

        Args:
            session: Sessão SQLAlchemy a ser utilizada como padrão
        """
        cls._default_session = session

    @classmethod
    def buscar_geral(cls,
                     termo: str,
                     session=None,
                     auto_commit: bool = True) -> SearchResult:
        """Executa busca genérica em filmes e pessoas.

        Pesquisa simultaneamente em filmes (título original, título português, sinopse)
        e pessoas (nome, nome artístico, biografia) usando busca case-insensitive.
        Limita os resultados a 20 itens por categoria.

        Args:
            termo: Termo de busca (mínimo 2 caracteres)
            session: Sessão SQLAlchemy opcional
            auto_commit: Se deve fazer auto-commit da transação

        Returns:
            SearchResult: Resultado consolidado da busca

        Raises:
            SearchServiceError: Quando a operação falha ou termo é muito curto
        """
        if session is None:
            session = cls._default_session

        # Validação do termo de busca
        if not termo or len(termo.strip()) < 2:
            raise SearchServiceError("Termo de busca deve ter pelo menos 2 caracteres")

        termo_limpo = termo.strip()

        try:
            # Busca em filmes
            filmes_resultado = cls._buscar_filmes(termo_limpo, session)
            
            # Busca em pessoas
            pessoas_resultado = cls._buscar_pessoas(termo_limpo, session)

            if auto_commit:
                session.commit()

            return SearchResult(
                filmes=filmes_resultado,
                pessoas=pessoas_resultado,
                termo_busca=termo_limpo,
                total_filmes=len(filmes_resultado),
                total_pessoas=len(pessoas_resultado)
            )

        except SQLAlchemyError as e:
            session.rollback()
            current_app.logger.error(f"Erro de banco de dados na busca: {str(e)}")
            raise SearchServiceError(f"Erro de banco de dados no {cls.__name__}.buscar_geral: {str(e)}") from e
        except Exception as e:
            session.rollback()
            current_app.logger.error(f"Erro inesperado na busca: {str(e)}")
            raise SearchServiceError(f"Erro inesperado no {cls.__name__}.buscar_geral: {str(e)}") from e

    @classmethod
    def _buscar_filmes(cls, termo: str, session) -> list[FilmeSearchResult]:
        """Busca filmes por título original, título português e sinopse.

        Implementa busca inteligente que procura pelo termo completo e palavras individuais,
        dando preferência aos resultados que contêm o termo completo.

        Args:
            termo: Termo de busca limpo
            session: Sessão SQLAlchemy

        Returns:
            list[FilmeSearchResult]: Lista de filmes encontrados (máximo 20)
        """
        # Prepara termos de busca
        termo_completo = f"%{termo}%"
        palavras = termo.split()
        
        # Constrói condições de busca
        campos_busca = [Filme.titulo_original, Filme.titulo_portugues, Filme.sinopse]
        
        # Condição para termo completo (prioridade alta)
        condicao_termo_completo = or_(*[
            func.lower(campo).like(func.lower(termo_completo))
            for campo in campos_busca
        ])
        
        # Condições para palavras individuais (prioridade baixa)
        condicoes_palavras = []
        for palavra in palavras:
            if len(palavra.strip()) >= 2:  # Ignora palavras muito curtas
                palavra_like = f"%{palavra.strip()}%"
                condicao_palavra = or_(*[
                    func.lower(campo).like(func.lower(palavra_like))
                    for campo in campos_busca
                ])
                condicoes_palavras.append(condicao_palavra)
        
        # Combina todas as condições
        if condicoes_palavras:
            condicao_final = or_(condicao_termo_completo, *condicoes_palavras)
        else:
            condicao_final = condicao_termo_completo
        
        # Query com ordenação que prioriza matches do termo completo
        stmt = (
            select(
                Filme.id, 
                Filme.titulo_original, 
                Filme.titulo_portugues, 
                Filme.ano_lancamento, 
                Filme.com_poster,
                # Score para ordenação: 1 se match completo, 0 se apenas palavras
                case(
                    (condicao_termo_completo, 1),
                    else_=0
                ).label('match_score')
            )
            .where(condicao_final)
            .order_by(
                case(
                    (condicao_termo_completo, 1),
                    else_=0
                ).desc(),  # Prioriza matches completos
                Filme.titulo_original  # Ordem alfabética como critério secundário
            )
            .limit(20)
        )

        resultado = session.execute(stmt).all()
        
        return [
            FilmeSearchResult(
                id=row.id,
                titulo_original=row.titulo_original,
                titulo_portugues=row.titulo_portugues,
                ano_lancamento=row.ano_lancamento,
                com_poster=row.com_poster
            )
            for row in resultado
        ]

    @classmethod
    def _buscar_pessoas(cls, termo: str, session) -> list[PessoaSearchResult]:
        """Busca pessoas por nome, nome artístico e biografia.

        Implementa busca inteligente que procura pelo termo completo e palavras individuais,
        dando preferência aos resultados que contêm o termo completo.

        Args:
            termo: Termo de busca limpo
            session: Sessão SQLAlchemy

        Returns:
            list[PessoaSearchResult]: Lista de pessoas encontradas (máximo 20)
        """
        # Prepara termos de busca
        termo_completo = f"%{termo}%"
        palavras = termo.split()
        
        # Constrói condições de busca
        campos_busca = [Pessoa.nome, Ator.nome_artistico, Pessoa.biografia]
        
        # Condição para termo completo (prioridade alta)
        condicao_termo_completo = or_(*[
            func.lower(campo).like(func.lower(termo_completo))
            for campo in campos_busca
        ])
        
        # Condições para palavras individuais (prioridade baixa)
        condicoes_palavras = []
        for palavra in palavras:
            if len(palavra.strip()) >= 2:  # Ignora palavras muito curtas
                palavra_like = f"%{palavra.strip()}%"
                condicao_palavra = or_(*[
                    func.lower(campo).like(func.lower(palavra_like))
                    for campo in campos_busca
                ])
                condicoes_palavras.append(condicao_palavra)
        
        # Combina todas as condições
        if condicoes_palavras:
            condicao_final = or_(condicao_termo_completo, *condicoes_palavras)
        else:
            condicao_final = condicao_termo_completo
        
        # Query com ordenação que prioriza matches do termo completo
        stmt = (
            select(
                Pessoa.id, 
                Pessoa.nome, 
                Ator.nome_artistico, 
                Pessoa.com_foto,
                case((Ator.id.is_not(None), True), else_=False).label('eh_ator'),
                # Score para ordenação: 1 se match completo, 0 se apenas palavras
                case(
                    (condicao_termo_completo, 1),
                    else_=0
                ).label('match_score')
            )
            .outerjoin(Ator, Pessoa.id == Ator.pessoa_id)
            .where(condicao_final)
            .order_by(
                case(
                    (condicao_termo_completo, 1),
                    else_=0
                ).desc(),  # Prioriza matches completos
                Pessoa.nome  # Ordem alfabética como critério secundário
            )
            .limit(20)
        )

        resultado = session.execute(stmt).all()
        
        return [
            PessoaSearchResult(
                id=row.id,
                nome=row.nome,
                nome_artistico=row.nome_artistico,
                com_foto=row.com_foto,
                eh_ator=row.eh_ator
            )
            for row in resultado
        ]