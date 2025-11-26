import re
import uuid
from collections import namedtuple
from typing import Any, Callable, Optional

from flask import current_app
from wtforms import ValidationError

from app.models.autenticacao import User
from app.services.email_service import EmailValidationService


class UniqueEmail(object):
    """
    Validador WTForms para garantir que o email informado não está cadastrado no sistema.

    Args:
        message (Optional[str]): Mensagem de erro personalizada.
    """

    def __init__(self, message: Optional[str] = None):
        if not message:
            message = "Já existe um usuário com este email"
        self.message = message

    def __call__(self, form, field):
        """
        Verifica se um email já está cadastrado.

        Args:
            form: O formulário sendo validado.
            field: O campo de email a ser verificado.

        Raises:
            ValidationError: Se o email já estiver cadastrado.
        """
        try:
            email = EmailValidationService.normalize(field.data)
        except ValueError:
            raise ValidationError("Endereço de email inválido.")
        if User.get_by_email(email):
            raise ValidationError(self.message)


class SenhaComplexa(object):
    """
    Validador WTForms para garantir que a senha informada atende aos requisitos de complexidade definidos.

    Os requisitos são definidos pelas seguintes chaves inteiras e booleanas no dicionário de
    configuração da aplicação:

    - PASSWORD_MIN: 8
    - PASSWORD_MINUSCULA: false
    - PASSWORD_NUMERO: false
    - PASSWORD_SIMBOLO: false
    - PASSWORD_MAIUSCULA: false
    """

    def __init__(self):
        """Inicializa o validador de complexidade de senha.

        Os requisitos são obtidos dinamicamente da configuração da aplicação
        em tempo de validação via current_app.config.
        """
        pass

    def __call__(self, form, field):
        """
        Realiza a validação da senha conforme os requisitos definidos.

        Args:
            form: O formulário sendo validado.
            field: O campo de senha a ser verificado.

        Raises:
            ValidationError: Se a senha não atender aos requisitos de complexidade.
        """
        Teste = namedtuple('Teste', ['config', 'mensagem', 're'])

        lista_de_testes = [
            Teste('PASSWORD_MAIUSCULA', "letras maiúsculas", r'[A-Z]'),
            Teste('PASSWORD_MINUSCULA', "letras minúsculas", r'[a-z]'),
            Teste('PASSWORD_NUMERO', "números", r'\d'),
            Teste('PASSWORD_SIMBOLO', "símbolos especiais", r'\W')
        ]

        senha_valida = True
        mensagens = []

        if current_app.config.get('PASSWORD_MIN', False):
            try:
                min_caracteres = int(current_app.config.get('PASSWORD_MIN', 0))
            except (TypeError, ValueError):
                current_app.logger.warning("PASSWORD_MIN deve ser inteiro")
                min_caracteres = 0
            senha_valida = senha_valida and (len(field.data) >= min_caracteres)
            mensagens.append(f"pelo menos {min_caracteres} caracteres")

        for teste in lista_de_testes:
            config_value = current_app.config.get(teste.config, False)
            if not isinstance(config_value, bool):
                current_app.logger.warning("%s deve ser bool, mas é %s" %
                                           (teste.config, type(config_value).__name__,))
                config_value = False
            if config_value:
                senha_valida = senha_valida and (re.search(teste.re, field.data) is not None)
                mensagens.append(teste.mensagem)

        if not senha_valida:
            mensagem = "A sua senha precisa conter "
            if len(mensagens) > 1:
                mensagem = mensagem + " e ".join([", ".join(mensagens[:-1]), mensagens[-1]])
            else:
                mensagem = mensagem + mensagens[0]
            mensagem = mensagem + "."
            raise ValidationError(mensagem)

        return


class CampoImutavel:
    """
    Validador WTForms genérico para garantir que um campo não seja modificado pelo usuário no lado do cliente.

    Usa introspecção para acessar o objeto de referência através do formulário.

    Examples:
        class ProfileForm(FlaskForm):
            def __init__(self, obj=None, **kwargs):
                super().__init__(**kwargs)
                self.reference_obj = obj or current_user

            id = HiddenField(validators=[CampoImutavel('id')])
            email = StringField(validators=[CampoImutavel('email')])
    """

    def __init__(self,
                 field_name: str,
                 attr_name: Optional[str] = None,
                 message: Optional[str] = None,
                 converter: Optional[Callable[[Any], Any]] = None) -> None:
        # @formatter:off
        """
        Inicializa o validador de campos imutáveis genérico.

        Args:
            field_name (str): Nome do campo no formulário.
            attr_name (Optional[str]): Nome do atributo no objeto de referência (padrão: mesmo que field_name).
            message (Optional[str]): Mensagem de erro personalizada.
            converter (Optional[Callable[[Any], Any]]): Função para converter o valor de referência.

        Returns:
            None
        """
        # @formatter:on
        self.field_name = field_name
        self.attr_name = attr_name or field_name
        self.converter = converter or (str if field_name == 'id' else lambda x: x)
        self.message = message or f"Tentativa de modificação não autorizada do campo {field_name}"

    def __call__(self, form, field) -> None:
        """
        Executa a validação do campo imutável usando introspecção no formulário.

        Args:
            form: O formulário WTForms sendo validado.
            field: O campo a ser verificado.

        Returns:
            None

        Raises:
            ValidationError: Se o valor do campo for diferente do valor esperado.
        """
        # Verifica se o formulário tem um objeto de referência
        if not hasattr(form, 'reference_obj'):
            raise ValidationError("Formulário deve ter atributo 'reference_obj'")

        reference_obj = form.reference_obj
        if reference_obj is None:
            raise ValidationError("Objeto de referência não pode ser None")

        try:
            expected_value = getattr(reference_obj, self.attr_name)
            expected_value = self.converter(expected_value)
        except AttributeError:
            current_app.logger.error("Atributo '%s' não encontrado no objeto %s" %
                                     (self.attr_name, type(reference_obj).__name__,))
            raise ValidationError("Erro interno na validação")
        except Exception as e:
            current_app.logger.error("Erro ao processar valor de referência para %s: %s" %
                                     (self.field_name, str(e),))
            raise ValidationError("Erro interno na validação")

        if field.data != expected_value:
            current_app.logger.warning(
                    "Violação da integridade: campo %s alterado de '%s' para '%s'" %
                    (self.field_name, expected_value, field.data,))
            raise ValidationError(self.message)


class ValidadorDataAntesDe:
    """
    Validador WTForms para garantir que uma data seja anterior a uma data de referência.
    
    Pode receber uma data específica ou o nome de um campo no formulário para comparação.
    """
    
    def __init__(self, reference_date, message: Optional[str] = None):
        """
        Inicializa o validador de data anterior.
        
        Args:
            reference_date: Data de referência (datetime.date) ou nome do campo (str) no formulário.
            message (Optional[str]): Mensagem de erro personalizada.
        """
        self.reference_date = reference_date
        self.message = message or "A data deve ser anterior à data de referência"
    
    def __call__(self, form, field):
        """
        Valida que a data do campo é anterior à data de referência.
        
        Args:
            form: O formulário sendo validado.
            field: O campo de data sendo verificado.
            
        Raises:
            ValidationError: Se a data for posterior ou igual à data de referência.
        """
        if not field.data:
            return  # Campo vazio é válido (usar Optional() se necessário)
        
        # Se reference_date é uma string, busca o campo no formulário
        if isinstance(self.reference_date, str):
            if not hasattr(form, self.reference_date):
                return  # Campo de referência não existe
            reference_field = getattr(form, self.reference_date)
            if not reference_field.data:
                return  # Campo de referência vazio, não valida
            ref_date = reference_field.data
        else:
            ref_date = self.reference_date
        
        if field.data >= ref_date:
            raise ValidationError(self.message)


class ValidadorDataDepoisDe:
    """
    Validador WTForms para garantir que uma data seja posterior a uma data de referência.
    
    Pode receber uma data específica ou o nome de um campo no formulário para comparação.
    """
    
    def __init__(self, reference_date, message: Optional[str] = None):
        """
        Inicializa o validador de data posterior.
        
        Args:
            reference_date: Data de referência (datetime.date) ou nome do campo (str) no formulário.
            message (Optional[str]): Mensagem de erro personalizada.
        """
        self.reference_date = reference_date
        self.message = message or "A data deve ser posterior à data de referência"
    
    def __call__(self, form, field):
        """
        Valida que a data do campo é posterior à data de referência.
        
        Args:
            form: O formulário sendo validado.
            field: O campo de data sendo verificado.
            
        Raises:
            ValidationError: Se a data for anterior ou igual à data de referência.
        """
        if not field.data:
            return  # Campo vazio é válido (usar Optional() se necessário)
        
        # Se reference_date é uma string, busca o campo no formulário
        if isinstance(self.reference_date, str):
            if not hasattr(form, self.reference_date):
                return  # Campo de referência não existe
            reference_field = getattr(form, self.reference_date)
            if not reference_field.data:
                return  # Campo de referência vazio, não valida
            ref_date = reference_field.data
        else:
            ref_date = self.reference_date
        
        if field.data <= ref_date:
            raise ValidationError(self.message)


class YouTubeURLValidator:
    """
    Validador customizado para validação de formato de URL do YouTube.

    Valida que a URL é uma URL válida de vídeo do YouTube em vários formatos:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - http://www.youtube.com/watch?v=VIDEO_ID
    """

    def __init__(self, message: Optional[str] = None):
        self.message = message or "URL do YouTube inválida"

    def __call__(self, form, field):
        if not field.data:
            return  # Campo vazio é válido (use OptionalValidator se necessário)
        
        # YouTube URL patterns
        youtube_patterns = [
            r'^https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})(?:&.*)?$',
            r'^https?://youtu\.be/([a-zA-Z0-9_-]{11})(?:\?.*)?$',
            r'^https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})(?:\?.*)?$'
        ]
        
        url = field.data.strip()
        is_valid = any(re.match(pattern, url) for pattern in youtube_patterns)
        
        if not is_valid:
            raise ValidationError(self.message)


class YearRangeValidator:
    """
    Validador customizado para validação de intervalo de ano.

    Valida que o ano está entre 1800 e ano atual + 10.
    """

    def __init__(self, message: Optional[str] = None):
        self.message = message or "Ano deve estar entre 1800 e {max_year}"

    def __call__(self, form, field):
        if not field.data:
            return  # Campo vazio é válido
        
        from datetime import datetime
        current_year = datetime.now().year
        min_year = 1800
        max_year = current_year + 10
        
        if not (min_year <= field.data <= max_year):
            raise ValidationError(self.message.format(max_year=max_year))


class PositiveDecimalValidator:
    """Validador customizado para valores decimais positivos."""

    def __init__(self, message: Optional[str] = None):
        self.message = message or "Valor deve ser positivo"

    def __call__(self, form, field):
        if not field.data:
            return  # Campo vazio é válido
        
        from decimal import Decimal, InvalidOperation
        try:
            value = Decimal(str(field.data))
            if value < 0:
                raise ValidationError(self.message)
        except (InvalidOperation, ValueError):
            raise ValidationError("Valor numérico inválido")


class UUIDValidator:
    """Validador customizado para campos UUID."""

    def __init__(self, message: Optional[str] = None):
        self.message = message or "UUID inválido"

    def __call__(self, form, field):
        if not field.data:
            return  # Campo vazio é válido (use DataRequired se necessário)
        
        try:
            uuid.UUID(str(field.data))
        except (ValueError, TypeError):
            raise ValidationError(self.message)
