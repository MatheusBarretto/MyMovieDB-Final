import uuid
from datetime import datetime
from typing import Any, Optional, Self, Union
from uuid import UUID

import sqlalchemy as sa
from flask import current_app
from sqlalchemy import DateTime, func, inspect, ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class BasicRepositoryMixin:
    """Mixin básico para repositórios SQLAlchemy.

    Fornece métodos utilitários para operações comuns de consulta.
    """

    class RecordNotFoundError(Exception):
        """Exceção levantada quando um registro não é encontrado."""
        pass

    class InvalidIdentifierError(Exception):
        """Exceção levantada quando um identificador é inválido."""
        pass

    @classmethod
    def get_by_id(cls,
                  cls_id: Union[str, int, UUID, None],
                  session=None,
                  raise_if_not_found: bool = False) -> Optional[Self]:
        """Busca um registro pelo seu ID.

        O metodo detecta automaticamente o tipo da chave primária da classe
        e realiza a conversão apropriada do identificador fornecido.

        Args:
            cls_id (Union[str, int, UUID, None]): O identificador do registro (UUID, int, string ou None).
                    O tipo aceito depende da chave primária da classe.
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            raise_if_not_found (bool): Se True, levanta RecordNotFoundError quando não encontrado.

        Returns:
            typing.Optional[typing.Self]: Instância encontrada ou None.

        Raises:
            InvalidIdentifierError: Se o ID não puder ser convertido para o tipo da PK.
            RecordNotFoundError: Se raise_if_not_found=True e o registro não existir.
            RuntimeError: Se a classe tiver chave primária composta ou ausente.
            SQLAlchemyError: Para erros de banco de dados não tratados.

        Examples:
            # Para modelo com UUID como PK
            user = User.get_by_id("550e8400-e29b-41d4-a716-446655440000")
            user = User.get_by_id(uuid.uuid4())

            # Para modelo com int como PK
            product = Product.get_by_id(42)
            product = Product.get_by_id("42")  # Converte automaticamente

            # Com tratamento de erro explícito
            try:
                user = User.get_by_id(user_id, raise_if_not_found=True)
            except User.RecordNotFoundError:
                # Trata usuário não encontrado
                pass
        """
        if session is None:
            session = db.session

        try:
            # Determina o tipo da chave primária
            pk_type = cls._get_primary_key_type()

            # Converte o identificador para o tipo correto
            obj_id = cls._convert_identifier(cls_id, pk_type)

            if obj_id is None:
                if raise_if_not_found:
                    raise cls.RecordNotFoundError(
                            f"ID None fornecido para busca em {cls.__name__}"
                    )
                return None

            # Executa a busca no banco de dados
            instance = session.get(cls, obj_id)

            if instance is None and raise_if_not_found:
                raise cls.RecordNotFoundError(
                        f"Registro de {cls.__name__} com ID {obj_id} não encontrado"
                )

            return instance

        except (cls.InvalidIdentifierError, RuntimeError):
            # Re-lança erros de identificador inválido ou configuração
            current_app.logger.warning(
                    f"Tentativa de busca com ID inválido em {cls.__name__}: {cls_id} "
                    f"(tipo: {type(cls_id).__name__})"
            )
            raise

        except SQLAlchemyError as e:
            # Registra e re-lança erros de banco de dados
            current_app.logger.error(
                    f"Erro de banco de dados ao buscar {cls.__name__} por ID {cls_id}: {str(e)}",
                    exc_info=True
            )
            raise

        except Exception as e:
            # Captura erros inesperados
            current_app.logger.error(
                    f"Erro inesperado ao buscar {cls.__name__} por ID {cls_id}: {str(e)}",
                    exc_info=True
            )
            raise

    @classmethod
    def get_by_composed_id(cls,
                           cls_dict_id: dict[str, Any],
                           session=None,
                           raise_if_not_found: bool = False) -> Optional[Self]:
        """Busca um registro por um ID composto.

        O metodo detecta automaticamente os tipos de cada componente da chave
        primária composta e realiza as conversões apropriadas.

        Args:
            cls_dict_id (dict[str, Any]): Dicionário com os campos do ID composto.
                        As chaves devem corresponder exatamente aos nomes das colunas da chave primária.
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            raise_if_not_found (bool): Se True, levanta RecordNotFoundError quando não encontrado.

        Returns:
            typing.Optional[typing.Self]: Instância encontrada ou None.

        Raises:
            InvalidIdentifierError: Se o dicionário tiver chaves faltantes, extras, ou valores que
                    não podem ser convertidos.
            RecordNotFoundError: Se raise_if_not_found=True e o registro não existir.
            RuntimeError: Se a classe não tiver chave primária composta.
            SQLAlchemyError: Para erros de banco de dados não tratados.

        Examples:
            # Para modelo com chave composta (user_id: UUID, role_id: int)
            user_role = UserRole.get_by_composed_id({
                'user_id': '550e8400-e29b-41d4-a716-446655440000',
                'role_id': 1
            })

            # Com conversão automática de tipos
            user_role = UserRole.get_by_composed_id({
                'user_id': uuid.uuid4(),  # UUID object
                'role_id': '1'  # String convertida para int
            })

            # Com tratamento de erro explícito
            try:
                assignment = Assignment.get_by_composed_id(
                    {'student_id': sid, 'course_id': cid},
                    raise_if_not_found=True
                )
            except Assignment.RecordNotFoundError:
                # Trata registro não encontrado
                pass
            except Assignment.InvalidIdentifierError as e:
                # Trata ID inválido
                print(f"ID inválido: {e}")
        """
        if session is None:
            session = db.session

        # Validação de entrada
        if not isinstance(cls_dict_id, dict):
            raise cls.InvalidIdentifierError(
                    f"cls_dict_id deve ser um dicionário, recebido: {type(cls_dict_id).__name__}"
            )

        if not cls_dict_id:
            if raise_if_not_found:
                raise cls.RecordNotFoundError(
                        f"Dicionário vazio fornecido para busca em {cls.__name__}"
                )
            return None

        try:
            # Determina os tipos da chave primária composta
            pk_types = cls._get_composite_primary_key_types()

            # Valida se todas as chaves necessárias estão presentes
            cls._validate_composite_id_keys(cls_dict_id, pk_types)

            # Converte cada componente para o tipo correto
            converted_id = cls._convert_composite_id(cls_dict_id, pk_types)

            # Verifica se algum componente é None
            none_keys = [k for k, v in converted_id.items() if v is None]
            if none_keys:
                if raise_if_not_found:
                    raise cls.RecordNotFoundError(
                            f"Componentes None no ID composto de {cls.__name__}: {none_keys}"
                    )
                return None

            # Executa a busca no banco de dados
            instance = session.get(cls, converted_id)

            if instance is None and raise_if_not_found:
                raise cls.RecordNotFoundError(
                        f"Registro de {cls.__name__} com ID composto {converted_id} não encontrado"
                )

            return instance

        except (cls.InvalidIdentifierError, RuntimeError):
            # Re-lança erros de identificador inválido ou configuração
            current_app.logger.warning(
                    f"Tentativa de busca com ID composto inválido em {cls.__name__}: {cls_dict_id}"
            )
            raise

        except SQLAlchemyError as e:
            # Registra e re-lança erros de banco de dados
            current_app.logger.error(
                    f"Erro de banco de dados ao buscar {cls.__name__} por ID composto "
                    f"{cls_dict_id}: {str(e)}",
                    exc_info=True
            )
            raise

        except Exception as e:
            # Captura erros inesperados
            current_app.logger.error(
                    f"Erro inesperado ao buscar {cls.__name__} por ID composto {cls_dict_id}: "
                    f"{str(e)}",
                    exc_info=True
            )
            raise

    @classmethod
    def count_all(cls,
                  session=None,
                  criteria: Optional[dict[str, Any]] = None,
                  raise_on_error: bool = False) -> int:
        """Conta todos os registros na tabela associada à classe.

        Args:
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            criteria (Optional[dict[str, Any]]): Dicionário opcional com critérios de filtro (atributo: valor).
                     Permite contar apenas registros que atendam condições específicas.
            raise_on_error (bool): Se True, propaga exceções de banco de dados.
                                   Se False, registra erro e retorna 0.

        Returns:
            int: Número total de registros que atendem aos critérios.

        Raises:
            SQLAlchemyError: Se raise_on_error=True e ocorrer erro de banco de dados.
            InvalidIdentifierError: Se algum critério usar atributo inexistente.

        Examples:
            # Contagem simples
            total_users = User.count_all()

            # Contagem com filtro
            active_users = User.count_all(criteria={'active': True})

            # Com sessão customizada
            with custom_session() as session:
                count = User.count_all(session=session)

            # Com tratamento de erro explícito
            try:
                count = User.count_all(raise_on_error=True)
            except SQLAlchemyError as e:
                print(f"Erro ao contar: {e}")
        """
        if session is None:
            session = db.session

        try:
            # Constrói a query base
            sentenca = sa.select(sa.func.count()).select_from(cls)

            # Aplica filtros se fornecidos
            if criteria is not None:
                if not isinstance(criteria, dict):
                    raise cls.InvalidIdentifierError(
                            f"criteria deve ser um dicionário, recebido: {type(criteria).__name__}"
                    )

                sentenca = cls._apply_criteria_filters(sentenca, criteria)

            # Executa a contagem
            result = session.scalar(sentenca)

            # COUNT nunca deve retornar None, mas por segurança
            if result is None:
                current_app.logger.warning(
                        f"COUNT retornou None para {cls.__name__} - possível problema de "
                        f"configuração"
                )
                return 0

            return result

        except cls.InvalidIdentifierError:
            # Re-lança erros de critério inválido
            current_app.logger.error(
                    f"Critério inválido em count_all para {cls.__name__}: {criteria}"
            )
            raise

        except SQLAlchemyError as e:
            # Registra erro de banco de dados
            current_app.logger.error(
                    f"Erro de banco de dados ao contar registros de {cls.__name__}: {str(e)}",
                    exc_info=True
            )

            if raise_on_error:
                raise

            # Retorna 0 em caso de erro se raise_on_error=False
            return 0

        except Exception as e:
            # Captura erros inesperados
            current_app.logger.error(
                    f"Erro inesperado ao contar registros de {cls.__name__}: {str(e)}",
                    exc_info=True
            )

            if raise_on_error:
                raise

            return 0

    @classmethod
    def is_empty(cls,
                 session=None,
                 criteria: Optional[dict[str, Any]] = None,
                 raise_on_error: bool = False) -> bool:
        """Verifica se a tabela associada à classe está vazia.

        Este metodo é otimizado para verificação de existência, utilizando
        EXISTS ao invés de COUNT quando possível para melhor performance.

        Args:
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            criteria (Optional[dict[str, Any]]): Dicionário opcional com critérios de filtro (atributo: valor).
                    Permite verificar se existem registros que atendam condições específicas.
            raise_on_error (bool): Se True, propaga exceções de banco de dados.
                           Se False, registra erro e retorna True (assume vazio por segurança).

        Returns:
            bool: True se não houver registros (atendendo aos critérios, se fornecidos),
                 False caso contrário.

        Raises:
            SQLAlchemyError: Se raise_on_error=True e ocorrer erro de banco de dados.
            InvalidIdentifierError: Se algum critério usar atributo inexistente.

        Examples:
            # Verificação simples
            if User.is_empty():
                print("Nenhum usuário cadastrado")

            # Verificação com filtro
            if User.is_empty(criteria={'active': False}):
                print("Nenhum usuário inativo")

            # Com tratamento de erro explícito
            try:
                empty = User.is_empty(raise_on_error=True)
            except SQLAlchemyError:
                print("Erro ao verificar tabela")
        """
        if session is None:
            session = db.session

        try:
            sentenca = sa.select(sa.literal(1)).select_from(cls).limit(1)
            # Aplica filtros se fornecidos
            if criteria is not None and criteria:
                sentenca = cls._apply_criteria_filters(sentenca, criteria)
            exists_query = sa.select(sa.exists(sentenca))
            result = session.scalar(exists_query)
            return not result

        except cls.InvalidIdentifierError:
            # Re-lança erros de critério inválido
            current_app.logger.error(
                    f"Critério inválido em is_empty para {cls.__name__}: {criteria}"
            )
            raise

        except SQLAlchemyError as e:
            # Registra erro de banco de dados
            current_app.logger.error(
                    f"Erro de banco de dados ao verificar se {cls.__name__} está vazio: {str(e)}",
                    exc_info=True
            )

            if raise_on_error:
                raise

            # Retorna True (vazio) por segurança em caso de erro
            # Isto evita assumir que há dados quando não é possível verificar
            current_app.logger.warning(
                    f"Assumindo tabela {cls.__name__} como vazia devido a erro"
            )
            return True

        except Exception as e:
            # Captura erros inesperados
            current_app.logger.error(
                    f"Erro inesperado ao verificar se {cls.__name__} está vazio: {str(e)}",
                    exc_info=True
            )

            if raise_on_error:
                raise

            return True

    @classmethod
    def get_top_n(cls,
                  top_n: int = -1,
                  order_by: Optional[Union[str, list[str]]] = None,
                  ascending: bool = True,
                  session=None,
                  criteria: Optional[dict[str, Any]] = None) -> ScalarResult[Self]:
        """Retorna os top N registros, opcionalmente ordenados e filtrados.

        Args:
            top_n (int): Número de registros a retornar. Se -1, retorna todos.
                    Limitado a máximo de 10000 registros por segurança.
            order_by (Optional[Union[str, list[str]]]): Nome do atributo para ordenação, ou lista de atributos.
                    Se None, usa ordem natural do banco de dados.
            ascending (bool): Se True, ordena de forma ascendente. Se False, descendente.
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            criteria (Optional[dict[str, Any]]): Dicionário opcional com critérios de filtro (atributo: valor).

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias.

        Raises:
            InvalidIdentifierError: Se order_by ou criteria referenciar atributo inexistente.
            ValueError: Se top_n for inválido (< -1 ou 0).
            SQLAlchemyError: Para erros de banco de dados.

        Examples:
            # Top 10 usuários mais recentes
            recent_users = User.get_top_n(10, order_by='created_at', ascending=False)

            # Top 5 produtos ativos ordenados por preço
            products = Product.get_top_n(
                5,
                order_by='price',
                criteria={'active': True}
            )

            # Ordenação por múltiplos campos
            users = User.get_top_n(10, order_by=['last_name', 'first_name'])

            # Todos os registros ordenados
            all_sorted = User.get_top_n(order_by='email')
        """
        if session is None:
            session = db.session

        # Validação de top_n
        if top_n == 0 or top_n < -1:
            raise ValueError(
                    f"top_n deve ser -1 (todos) ou positivo, recebido: {top_n}"
            )

        # Limita top_n a um valor seguro
        if top_n > 10000:
            current_app.logger.warning(
                    f"top_n={top_n} excede limite de 10000 para {cls.__name__}, "
                    f"limitando a 10000"
            )
            top_n = 10000

        try:
            # Constrói a query base
            sentenca = sa.select(cls)

            # Aplica filtros se fornecidos
            if criteria is not None:
                sentenca = cls._apply_criteria_filters(sentenca, criteria)

            # Aplica ordenação se fornecida
            if order_by is not None:
                sentenca = cls._apply_ordering(sentenca, order_by, ascending)

            # Aplica limite se especificado
            if top_n > 0:
                sentenca = sentenca.limit(top_n)

            return session.scalars(sentenca)

        except cls.InvalidIdentifierError:
            current_app.logger.error(
                    f"Atributo inválido em get_top_n para {cls.__name__}: "
                    f"order_by={order_by}, criteria={criteria}"
            )
            raise

        except SQLAlchemyError as e:
            current_app.logger.error(
                    f"Erro de banco de dados em get_top_n para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

        except Exception as e:
            current_app.logger.error(
                    f"Erro inesperado em get_top_n para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

    @classmethod
    def get_all(cls,
                order_by: Optional[Union[str, list[str]]] = None,
                ascending: bool = True,
                session=None,
                limit: Optional[int] = None) -> ScalarResult[Self]:
        """Retorna todos os registros, opcionalmente ordenados.

        Args:
            order_by (Optional[Union[str, list[str]]]): Nome do atributo para ordenação, ou lista de atributos.
            ascending (bool): Se True, ordena de forma ascendente. Se False, descendente.
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            limit (Optional[int]): Limite opcional de registros. Se None, retorna todos.
                    Útil para prevenir carregamento excessivo de memória.

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias.

        Raises:
            InvalidIdentifierError: Se order_by referenciar atributo inexistente.
            SQLAlchemyError: Para erros de banco de dados.

        Examples:
            # Todos os usuários
            all_users = User.get_all()

            # Todos ordenados por email
            sorted_users = User.get_all(order_by='email')

            # Ordenação descendente
            users_desc = User.get_all(order_by='created_at', ascending=False)

            # Com limite de segurança
            users_limited = User.get_all(limit=1000)
        """
        if session is None:
            session = db.session

        try:
            # Constrói a query base
            sentenca = sa.select(cls)

            # Aplica ordenação se fornecida
            if order_by is not None:
                sentenca = cls._apply_ordering(sentenca, order_by, ascending)

            # Aplica limite se fornecido
            if limit is not None:
                if limit <= 0:
                    raise ValueError(f"limit deve ser positivo, recebido: {limit}")

                if limit > 100000:
                    current_app.logger.warning(
                            f"limit={limit} muito alto para {cls.__name__}, "
                            f"considere paginação"
                    )

                sentenca = sentenca.limit(limit)

            return session.scalars(sentenca)

        except cls.InvalidIdentifierError:
            current_app.logger.error(
                    f"Atributo inválido em get_all para {cls.__name__}: order_by={order_by}"
            )
            raise

        except SQLAlchemyError as e:
            current_app.logger.error(
                    f"Erro de banco de dados em get_all para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

        except Exception as e:
            current_app.logger.error(
                    f"Erro inesperado em get_all para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

    @classmethod
    def get_all_by(cls,
                   criteria: Optional[dict[str, Any]] = None,
                   order_by: Optional[Union[str, list[str]]] = None,
                   ascending: bool = True,
                   session=None,
                   limit: Optional[int] = None) -> ScalarResult[Self]:
        """Retorna todos os registros filtrados, opcionalmente ordenados.

        Args:
            criteria (Optional[dict[str, Any]]): Dicionário com critérios de filtro (atributo: valor).
                    Se None ou vazio, retorna todos os registros.
            order_by (Optional[Union[str, list[str]]]): Nome do atributo para ordenação, ou lista de atributos.
            ascending (bool): Se True, ordena de forma ascendente. Se False, descendente.
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            limit (Optional[int]): Limite opcional de registros retornados.

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias.

        Raises:
            InvalidIdentifierError: Se criteria ou order_by referenciar atributo inexistente.
            SQLAlchemyError: Para erros de banco de dados.

        Examples:
            # Usuários ativos
            active_users = User.get_all_by(criteria={'active': True})

            # Produtos de uma categoria, ordenados por preço
            products = Product.get_all_by(
                criteria={'category_id': cat_id, 'in_stock': True},
                order_by='price'
            )

            # Múltiplos critérios com ordenação descendente
            items = Item.get_all_by(
                criteria={'status': 'pending', 'priority': 'high'},
                order_by='created_at',
                ascending=False,
                limit=50
            )
        """
        if session is None:
            session = db.session

        try:
            # Constrói a query base
            sentenca = sa.select(cls)

            # Aplica filtros se fornecidos
            if criteria is not None and criteria:
                sentenca = cls._apply_criteria_filters(sentenca, criteria)

            # Aplica ordenação se fornecida
            if order_by is not None:
                sentenca = cls._apply_ordering(sentenca, order_by, ascending)

            # Aplica limite se fornecido
            if limit is not None:
                if limit <= 0:
                    raise ValueError(f"limit deve ser positivo, recebido: {limit}")
                sentenca = sentenca.limit(limit)

            return session.scalars(sentenca)

        except cls.InvalidIdentifierError:
            current_app.logger.error(
                    f"Atributo inválido em get_all_by para {cls.__name__}: "
                    f"criteria={criteria}, order_by={order_by}"
            )
            raise

        except SQLAlchemyError as e:
            current_app.logger.error(
                    f"Erro de banco de dados em get_all_by para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

        except Exception as e:
            current_app.logger.error(
                    f"Erro inesperado em get_all_by para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

    @classmethod
    def get_first_or_none_by(cls,
                             atributo: str,
                             valor: Any,
                             casesensitive: bool = True,
                             session=None,
                             additional_criteria: Optional[dict[str, Any]] = None) -> Optional[
        Self]:
        """Busca o primeiro registro que corresponde ao valor de um atributo.

        Args:
            atributo (str): Nome do atributo para busca.
            valor (Any): Valor a ser buscado.
            casesensitive (bool): Se a busca deve ser case sensitive (apenas para strings).
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            additional_criteria (Optional[dict[str, Any]]): Critérios adicionais de filtro opcionais.

        Returns:
            typing.Optional[typing.Self]: Instância encontrada ou None.

        Raises:
            InvalidIdentifierError: Se o atributo não existir na classe.
            TypeError: Se casesensitive=False e o valor não for string.
            SQLAlchemyError: Para erros de banco de dados.

        Examples:
            # Busca por email (case sensitive)
            user = User.get_first_or_none_by('email', 'user@example.com')

            # Busca case insensitive
            user = User.get_first_or_none_by(
                'username',
                'JOHN',
                casesensitive=False
            )

            # Com critérios adicionais
            product = Product.get_first_or_none_by(
                'sku',
                'ABC123',
                additional_criteria={'active': True}
            )
        """
        if session is None:
            session = db.session

        # Validação do atributo
        if not hasattr(cls, atributo):
            valid_attrs = [c.name for c in inspect(cls).columns]
            raise cls.InvalidIdentifierError(
                    f"Atributo '{atributo}' não existe em {cls.__name__}. "
                    f"Atributos válidos: {valid_attrs}"
            )

        try:
            # Constrói a query base
            sentenca = sa.select(cls)

            # Aplica o filtro principal
            attr = getattr(cls, atributo)

            if casesensitive:
                # Busca case sensitive
                if valor is None:
                    sentenca = sentenca.where(attr.is_(None))
                elif isinstance(valor, bool):
                    sentenca = sentenca.where(attr.is_(valor))
                else:
                    sentenca = sentenca.where(attr == valor)
            else:
                # Busca case insensitive (apenas para strings)
                if not isinstance(valor, str):
                    raise TypeError(
                            f"Para busca case insensitive, o valor deve ser string. "
                            f"Recebido: {type(valor).__name__}"
                    )

                # Verifica se o atributo é do tipo string
                try:
                    col_type = attr.type.python_type
                except AttributeError:
                    col_type = None
                if col_type != str:
                    current_app.logger.warning(
                            f"Busca case insensitive em atributo não-string: "
                            f"{cls.__name__}.{atributo} (tipo: {col_type.__name__})"
                    )

                sentenca = sentenca.where(
                        sa.func.lower(attr) == sa.func.lower(valor)
                )

            # Aplica critérios adicionais se fornecidos
            if additional_criteria is not None and additional_criteria:
                sentenca = cls._apply_criteria_filters(sentenca, additional_criteria)

            # Limita a um resultado
            sentenca = sentenca.limit(1)

            return session.scalar(sentenca)

        except (cls.InvalidIdentifierError, TypeError):
            current_app.logger.error(
                    f"Erro de validação em get_first_or_none_by para {cls.__name__}: "
                    f"atributo={atributo}, valor={valor}, casesensitive={casesensitive}"
            )
            raise

        except SQLAlchemyError as e:
            current_app.logger.error(
                    f"Erro de banco de dados em get_first_or_none_by para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

        except Exception as e:
            current_app.logger.error(
                    f"Erro inesperado em get_first_or_none_by para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

    @classmethod
    def get_page(cls,
                 page: int = 1,
                 page_size: int = 10,
                 order_by: Optional[Union[str, list[str]]] = None,
                 ascending: bool = True,
                 session=None,
                 criteria: Optional[dict[str, Any]] = None,
                 include_total: bool = False) -> Union[
        ScalarResult[Self], tuple[ScalarResult[Self], int]]:
        """Retorna uma página de registros com paginação e ordenação opcional.

        Args:
            page (int): Número da página (começa em 1). Limitado entre 1 e 10000.
            page_size (int): Número de registros por página. Limitado entre 1 e 1000.
            order_by (Optional[Union[str, list[str]]]): Nome do atributo para ordenação, ou lista de atributos.
            ascending (bool): Se True, ordena de forma ascendente. Se False, descendente.
            session (sqlalchemy.orm.scoping.scoped_session): Sessão SQLAlchemy opcional.
                    Se None, usa db.session.
            criteria (Optional[dict[str, Any]]): Dicionário opcional com critérios de filtro.
            include_total (bool): Se True, retorna tupla (resultados, total_count).
                          Se False, retorna apenas resultados.

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias na página.
            OU
            tuple[sqlalchemy.ScalarResult[typing.Self], int]: Tupla com (resultados, total).

        Raises:
            ValueError: Se page ou page_size forem inválidos.
            InvalidIdentifierError: Se order_by ou criteria referenciar atributo inexistente.
            SQLAlchemyError: Para erros de banco de dados.

        Examples:
            # Página simples
            users_page = User.get_page(page=2, page_size=20)

            # Com contagem total para UI de paginação
            users, total = User.get_page(
                page=1,
                page_size=10,
                include_total=True
            )
            total_pages = (total + page_size - 1) // page_size

            # Página filtrada e ordenada
            products, total = Product.get_page(
                page=1,
                page_size=25,
                criteria={'category': 'electronics', 'active': True},
                order_by='price',
                ascending=False,
                include_total=True
            )
        """
        if session is None:
            session = db.session

        # Validação de parâmetros
        if page < 1:
            raise ValueError(f"page deve ser >= 1, recebido: {page}")
        if page_size < 1:
            raise ValueError(f"page_size deve ser >= 1, recebido: {page_size}")

        # Aplica limites de segurança
        original_page = page
        original_page_size = page_size

        page = max(1, min(page, 10000))
        page_size = max(1, min(page_size, 1000))

        if original_page != page or original_page_size != page_size:
            current_app.logger.warning(
                    f"Parâmetros de paginação ajustados para {cls.__name__}: "
                    f"page {original_page}->{page}, page_size {original_page_size}->{page_size}"
            )

        try:
            # Constrói a query base
            sentenca = sa.select(cls)

            # Aplica filtros se fornecidos
            if criteria is not None and criteria:
                sentenca = cls._apply_criteria_filters(sentenca, criteria)

            # Calcula total se solicitado (antes de aplicar paginação)
            total_count = None
            if include_total:
                # Cria uma query de contagem baseada nos mesmos filtros
                count_query = sa.select(sa.func.count()).select_from(cls)
                if criteria is not None and criteria:
                    count_query = cls._apply_criteria_filters(count_query, criteria)
                total_count = session.scalar(count_query) or 0

            # Aplica ordenação se fornecida
            if order_by is not None:
                sentenca = cls._apply_ordering(sentenca, order_by, ascending)

            # Aplica paginação
            offset = (page - 1) * page_size
            sentenca = sentenca.offset(offset).limit(page_size)

            results = session.scalars(sentenca)

            # Retorna resultados com ou sem contagem total
            if include_total:
                return results, total_count
            return results

        except cls.InvalidIdentifierError:
            current_app.logger.error(
                    f"Atributo inválido em get_page para {cls.__name__}: "
                    f"order_by={order_by}, criteria={criteria}"
            )
            raise

        except SQLAlchemyError as e:
            current_app.logger.error(
                    f"Erro de banco de dados em get_page para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

        except Exception as e:
            current_app.logger.error(
                    f"Erro inesperado em get_page para {cls.__name__}: {str(e)}",
                    exc_info=True
            )
            raise

    @classmethod
    def _apply_ordering(cls,
                        sentenca,
                        order_by: Union[str, list[str]],
                        ascending: bool = True):
        """Aplica ordenação a uma sentença SQLAlchemy.

        Este metodo centraliza a lógica de ordenação, suportando
        ordenação por um ou múltiplos atributos.

        Args:
            sentenca: Sentença SQLAlchemy a ser ordenada.
            order_by (Union[str, list[str]]): Nome do atributo ou lista de atributos para ordenação.
            ascending (bool): Se True, ordena ascendente. Se False, descendente.

        Returns:
            Sentença SQLAlchemy com ordenação aplicada.

        Raises:
            InvalidIdentifierError: Se algum atributo não existir na classe.
        """
        # Normaliza order_by para lista
        if isinstance(order_by, str):
            order_by_list = [order_by]
        elif isinstance(order_by, list):
            order_by_list = order_by
        else:
            raise cls.InvalidIdentifierError(
                    f"order_by deve ser string ou lista de strings, "
                    f"recebido: {type(order_by).__name__}"
            )

        # Valida e aplica ordenação para cada atributo
        invalid_attrs = []
        for attr_name in order_by_list:
            if not hasattr(cls, attr_name):
                invalid_attrs.append(attr_name)
                continue

            attr = getattr(cls, attr_name)

            if ascending:
                sentenca = sentenca.order_by(attr.asc())
            else:
                sentenca = sentenca.order_by(attr.desc())

        if invalid_attrs:
            valid_attrs = [c.name for c in inspect(cls).columns]
            raise cls.InvalidIdentifierError(
                    f"Atributos de ordenação inexistentes em {cls.__name__}: {invalid_attrs}. "
                    f"Atributos válidos: {valid_attrs}"
            )

        return sentenca

    @classmethod
    def _apply_criteria_filters(cls,
                                sentenca,
                                criteria: dict[str, Any]):
        """Aplica filtros de critérios a uma sentença SQLAlchemy.

        Este metodo centraliza a lógica de aplicação de filtros,
        garantindo consistência entre diferentes métodos de consulta.

        Args:
            sentenca: Sentença SQLAlchemy a ser filtrada.
            criteria (dict[str, Any]): Dicionário com critérios de filtro (atributo: valor).

        Returns:
            Sentença SQLAlchemy com filtros aplicados.

        Raises:
            InvalidIdentifierError: Se algum atributo do critério não existir na classe.
        """
        invalid_attrs = []

        for k, v in criteria.items():
            if not hasattr(cls, k):
                invalid_attrs.append(k)
                continue

            attr = getattr(cls, k)

            # Tratamento especial para valores booleanos
            # Usa IS ao invés de = para compatibilidade com NULL em alguns bancos
            if isinstance(v, bool):
                sentenca = sentenca.where(attr.is_(v))
            # Tratamento para None (IS NULL)
            elif v is None:
                sentenca = sentenca.where(attr.is_(None))
            # Comparação padrão de igualdade
            else:
                sentenca = sentenca.where(attr == v)

        if invalid_attrs:
            raise cls.InvalidIdentifierError(
                    f"Atributos inexistentes em {cls.__name__}: {invalid_attrs}. "
                    f"Atributos válidos incluem: {[c.name for c in inspect(cls).columns]}"
            )

        return sentenca

    @classmethod
    def _get_primary_key_type(cls) -> type:
        """Determina o tipo da chave primária da classe.

        Returns:
            type: O tipo Python da chave primária (UUID, int, str, etc.).

        Raises:
            RuntimeError: Se a classe não tiver chave primária ou tiver chave composta.
        """
        mapper = inspect(cls)
        primary_keys = mapper.primary_key

        if len(primary_keys) == 0:
            raise RuntimeError(f"Classe {cls.__name__} não possui chave primária definida")

        if len(primary_keys) > 1:
            raise RuntimeError(
                    f"Classe {cls.__name__} possui chave primária composta. "
                    f"Use get_by_composed_id() ao invés de get_by_id()"
            )

        pk_column = primary_keys[0]
        return pk_column.type.python_type

    @classmethod
    def _convert_identifier(cls,
                            identifier: Any,
                            target_type: type) -> Any:
        """Converte um identificador para o tipo esperado da chave primária.

        Args:
            identifier: O identificador a ser convertido.
            target_type: O tipo alvo da conversão.

        Returns:
            typing.Any: Identificador convertido para o tipo apropriado.

        Raises:
            InvalidIdentifierError: Se a conversão falhar.
        """
        if identifier is None:
            return None

        # Se já é do tipo correto, retorna diretamente
        if isinstance(identifier, target_type):
            return identifier

        try:
            # Roteamento baseado no tipo da chave primária
            if target_type == UUID:
                return cls._convert_to_uuid(identifier)
            elif target_type == int:
                return cls._convert_to_int(identifier)
            elif target_type == str:
                return cls._convert_to_str(identifier)
            else:
                # Para tipos customizados, tenta conversão direta
                return target_type(identifier)

        except (ValueError, TypeError, AttributeError) as e:
            raise cls.InvalidIdentifierError(
                    f"Não foi possível converter '{identifier}' (tipo: "
                    f"{type(identifier).__name__}) "
                    f"para {target_type.__name__}: {str(e)}"
            ) from e

    @classmethod
    def _convert_to_uuid(cls,
                         identifier: Union[str, UUID]) -> UUID:
        """Converte um identificador para UUID.

        Args:
            identifier (Union[str, UUID]): String ou UUID.

        Returns:
            uuid.UUID: UUID convertido.

        Raises:
            InvalidIdentifierError: Se a conversão falhar.
        """
        if isinstance(identifier, UUID):
            return identifier

        if not isinstance(identifier, str):
            raise cls.InvalidIdentifierError(
                    f"Para chave UUID, identificador deve ser UUID ou string, "
                    f"recebido: {type(identifier).__name__}"
            )

        try:
            return uuid.UUID(identifier)
        except (ValueError, AttributeError) as e:
            raise cls.InvalidIdentifierError(
                    f"String '{identifier}' não é um UUID válido: {str(e)}"
            ) from e

    @classmethod
    def _convert_to_int(cls,
                        identifier: Union[int, str]) -> int:
        """Converte um identificador para inteiro.

        Args:
            identifier (Union[int, str]): Inteiro ou string representando inteiro.

        Returns:
            int: Inteiro convertido.

        Raises:
            InvalidIdentifierError: Se a conversão falhar.
        """
        if isinstance(identifier, int):
            return identifier

        if isinstance(identifier, str):
            try:
                return int(identifier)
            except ValueError as e:
                raise cls.InvalidIdentifierError(
                        f"String '{identifier}' não pode ser convertida para inteiro: {str(e)}"
                ) from e

        raise cls.InvalidIdentifierError(
                f"Para chave inteira, identificador deve ser int ou string, "
                f"recebido: {type(identifier).__name__}"
        )

    @classmethod
    def _convert_to_str(cls,
                        identifier: Any) -> str:
        """Converte um identificador para string.

        Args:
            identifier (typing.Any): Qualquer valor conversível para string.

        Returns:
            str: String convertida.

        Raises:
            InvalidIdentifierError: Se a conversão falhar.
        """
        if isinstance(identifier, str):
            return identifier

        try:
            return str(identifier)
        except Exception as e:
            raise cls.InvalidIdentifierError(
                    f"Não foi possível converter '{identifier}' para string: {str(e)}"
            ) from e

    @classmethod
    def _get_composite_primary_key_types(cls) -> dict[str, type]:
        """Determina os tipos de cada componente da chave primária composta.

        Returns:
            dict[str, type]: Dicionário mapeando nome da coluna para seu tipo Python.

        Raises:
            RuntimeError: Se a classe não tiver chave primária composta.
        """
        mapper = inspect(cls)
        primary_keys = mapper.primary_key

        if len(primary_keys) == 0:
            raise RuntimeError(f"Classe {cls.__name__} não possui chave primária definida")

        if len(primary_keys) == 1:
            raise RuntimeError(
                    f"Classe {cls.__name__} possui chave primária simples. "
                    f"Use get_by_id() ao invés de get_by_composed_id()"
            )

        # Retorna dicionário com nome da coluna e seu tipo Python
        return {pk_column.name: pk_column.type.python_type for pk_column in primary_keys}

    @classmethod
    def _validate_composite_id_keys(cls,
                                    cls_dict_id: dict[str, Any],
                                    pk_types: dict[str, type]) -> None:
        """Valida se o dicionário de ID composto contém todas as chaves necessárias.

        Args:
            cls_dict_id (dict[str, Any]): Dicionário com os componentes do ID composto.
            pk_types (dict[str, type]): Dicionário com os tipos esperados para cada componente.

        Raises:
            InvalidIdentifierError: Se houver chaves faltantes ou extras.
        """
        provided_keys = set(cls_dict_id.keys())
        required_keys = set(pk_types.keys())

        missing_keys = required_keys - provided_keys
        if missing_keys:
            raise cls.InvalidIdentifierError(
                    f"Chaves faltantes no ID composto de {cls.__name__}: {missing_keys}. "
                    f"Chaves esperadas: {required_keys}"
            )

        extra_keys = provided_keys - required_keys
        if extra_keys:
            raise cls.InvalidIdentifierError(
                    f"Chaves extras no ID composto de {cls.__name__}: {extra_keys}. "
                    f"Chaves esperadas: {required_keys}"
            )

    @classmethod
    def _convert_composite_id(cls,
                              cls_dict_id: dict[str, Any],
                              pk_types: dict[str, type]) -> dict[str, Any]:
        """Converte cada componente do ID composto para seu tipo apropriado.

        Args:
            cls_dict_id (dict[str, Any]): Dicionário com os componentes do ID composto.
            pk_types (dict[str, type]): Dicionário com os tipos esperados para cada componente.

        Returns:
            dict[str, typing.Any]: Dicionário com valores convertidos.

        Raises:
            InvalidIdentifierError: Se alguma conversão falhar.
        """
        converted_id = {}
        conversion_errors = []

        for key, value in cls_dict_id.items():
            target_type = pk_types[key]
            try:
                converted_id[key] = cls._convert_identifier(value, target_type)
            except cls.InvalidIdentifierError as e:
                conversion_errors.append(f"  - {key}: {str(e)}")

        if conversion_errors:
            error_msg = (
                    f"Erros na conversão do ID composto de {cls.__name__}:\n" +
                    "\n".join(conversion_errors)
            )
            raise cls.InvalidIdentifierError(error_msg)

        return converted_id


class AuditMixin:
    """Mixin para adicionar campos de auditoria a modelos SQLAlchemy.

    Adiciona campos de criação e atualização automaticamente gerenciados.
    """
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now(),
                                                 onupdate=func.now())
