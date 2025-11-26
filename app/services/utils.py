"""Utilitários compartilhados entre os serviços.

Este módulo contém funções auxiliares reutilizáveis pelos diferentes serviços
para evitar duplicação de código.
"""
from sqlalchemy import Select


def aplicar_filtro_creditado(stmt: Select,
                             campo_creditado,
                             creditado: bool = True,
                             nao_creditado: bool = True) -> Select:
    """Aplica filtros de creditado/não creditado a uma query SQLAlchemy.
    
    Args:
        stmt (Select): Statement SQLAlchemy a ser filtrado
        campo_creditado: Campo booleano que indica se é creditado (ex: Atuacao.creditado)
        creditado (bool): Se True, inclui registros creditados. Default: True
        nao_creditado (bool): Se True, inclui registros não creditados. Default: True
        
    Returns:
        Select: Statement com filtros aplicados
        
    Raises:
        ValueError: Se ambos os filtros forem False
        
    Examples:
        >>> stmt = select(Atuacao).where(Atuacao.ator_id == ator.id_pessoa)
        >>> stmt = aplicar_filtro_creditado(stmt, Atuacao.creditado, True, False)
    """
    # Valida que pelo menos um filtro está ativo
    if not creditado and not nao_creditado:
        raise ValueError("Pelo menos um dos filtros (creditado ou nao_creditado) deve ser True")

    # Aplica filtros de creditado
    if creditado and not nao_creditado:  # Apenas creditados
        stmt = stmt.where(campo_creditado == True)
    elif nao_creditado and not creditado:  # Apenas não creditados
        stmt = stmt.where(campo_creditado == False)
    # Se ambos forem True, não aplica filtro (retorna todos)

    return stmt
