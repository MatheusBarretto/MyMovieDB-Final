"""Testes para o ReviewService."""
import pytest
from unittest.mock import Mock

from app.services.review_service import ReviewService, ReviewOperationResult
from app.models.filme import Filme
from app.models.autenticacao import User


class TestReviewService:
    """Testes para a classe ReviewService."""

    def test_criar_avaliacao_nota_valida(self):
        """Testa criação de avaliação com nota válida."""
        # Arrange
        filme = Mock(spec=Filme)
        filme.id = "filme-123"
        
        usuario = Mock(spec=User)
        usuario.id = "user-123"
        
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = None  # Não existe avaliação
        
        # Act
        resultado = ReviewService.criar_ou_atualizar_avaliacao(
            filme=filme,
            usuario=usuario,
            nota=8,
            comentario="Ótimo filme!",
            recomendaria=True,
            session=session
        )
        
        # Assert
        assert resultado.status == ReviewOperationResult.CREATED
        assert "sucesso" in resultado.message.lower()
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_criar_avaliacao_nota_invalida(self):
        """Testa criação de avaliação com nota inválida."""
        # Arrange
        filme = Mock(spec=Filme)
        usuario = Mock(spec=User)
        session = Mock()
        
        # Act
        resultado = ReviewService.criar_ou_atualizar_avaliacao(
            filme=filme,
            usuario=usuario,
            nota=15,  # Nota inválida
            session=session
        )
        
        # Assert
        assert resultado.status == ReviewOperationResult.VALIDATION_ERROR
        assert "nota deve ser" in resultado.message.lower()
        assert resultado.errors is not None
        session.add.assert_not_called()
        session.commit.assert_not_called()

    def test_excluir_avaliacao_permissao_negada(self):
        """Testa exclusão de avaliação sem permissão."""
        # Arrange
        avaliacao_mock = Mock()
        avaliacao_mock.usuario_id = "outro-user"
        
        usuario = Mock(spec=User)
        usuario.id = "user-123"
        
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = avaliacao_mock
        
        # Act
        resultado = ReviewService.excluir_avaliacao("avaliacao-123", usuario, session)
        
        # Assert
        assert resultado.status == ReviewOperationResult.PERMISSION_DENIED
        assert "permissão" in resultado.message.lower()
        session.delete.assert_not_called()
        session.commit.assert_not_called()