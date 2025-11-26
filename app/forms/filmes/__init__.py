from datetime import datetime

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DecimalField, HiddenField, IntegerField, StringField, \
    ValidationError
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, \
    Optional as OptionalValidator

from ..validators import CampoImutavel, PositiveDecimalValidator, UUIDValidator, \
    YearRangeValidator, \
    YouTubeURLValidator
from ...services.imageprocessing_service import ImageProcessingService


class AvaliacaoForm(FlaskForm):
    """Formulário para avaliação de filmes.

    Permite que usuários avaliem filmes com nota de 1 a 10,
    comentário opcional e indicação de recomendação.
    """

    nota = SelectField(
            label="Nota",
            choices=[(i, str(i)) for i in range(0, 11)],
            coerce=int,
            default=0,
            validators=[InputRequired(message="É obrigatório informar uma nota"),
                        NumberRange(min=0, max=10, message="A nota deve estar entre 0 e 10"),
                        ]
    )

    comentario = TextAreaField(
            label="Comentário",
            validators=[Length(max=4096, message="O comentário pode ter até 4096 caracteres"),
                        ],
            render_kw={
                'placeholder': 'Compartilhe sua opinião sobre o filme (opcional)',
                'rows'       : 4
            }
    )

    recomendaria = BooleanField(
            label="Recomendaria este filme?",
            default=False
    )

    submit = SubmitField("Salvar Avaliação")


class FilmeCrudForm(FlaskForm):
    """
    Form for creating and editing movie records.

    Handles all movie fields with proper validation according to requirements:
    - titulo_original: Required, max 180 characters
    - ano_lancamento: Optional, between 1800 and current year + 10
    - duracao_minutos: Optional, positive integer
    - orcamento_milhares and faturamento_lancamento_milhares: Optional, positive decimals
    - trailer_youtube: Optional, valid YouTube URL format
    """

    # Basic movie information
    titulo_original = StringField(
            'Título Original',
            validators=[
                DataRequired(message="Título original é obrigatório"),
                Length(max=180, message="Título original deve ter no máximo 180 caracteres")
            ],
            render_kw={
                'placeholder': 'Digite o título original do filme',
                'class'      : 'form-control'
            }
    )

    titulo_portugues = StringField(
            'Título em Português',
            validators=[
                OptionalValidator(),
                Length(max=180, message="Título em português deve ter no máximo 180 caracteres")
            ],
            render_kw={
                'placeholder': 'Digite o título em português (opcional)',
                'class'      : 'form-control'
            }
    )

    ano_lancamento = IntegerField(
            'Ano de Lançamento',
            validators=[
                OptionalValidator(),
                YearRangeValidator()
            ],
            render_kw={
                'placeholder': 'Ex: 2023',
                'class'      : 'form-control',
                'min'        : '1800',
                'max'        : str(datetime.now().year + 10)
            }
    )

    lancado = BooleanField(
            'Filme já foi lançado?',
            default=False,
            render_kw={'class': 'form-check-input'}
    )

    duracao_minutos = IntegerField(
            'Duração (minutos)',
            validators=[
                OptionalValidator(),
                NumberRange(min=1, message="Duração deve ser um número positivo")
            ],
            render_kw={
                'placeholder': 'Ex: 120',
                'class'      : 'form-control',
                'min'        : '1'
            }
    )

    sinopse = TextAreaField(
            'Sinopse',
            validators=[OptionalValidator()],
            render_kw={
                'placeholder': 'Digite a sinopse do filme (opcional)',
                'class'      : 'form-control',
                'rows'       : 4
            }
    )

    # Financial information
    orcamento_milhares = DecimalField(
            'Orçamento (em milhares)',
            validators=[
                OptionalValidator(),
                PositiveDecimalValidator(message="Orçamento deve ser um valor positivo")
            ],
            render_kw={
                'placeholder': 'Ex: 50000.00',
                'class'      : 'form-control',
                'step'       : '0.01',
                'min'        : '0'
            }
    )

    faturamento_lancamento_milhares = DecimalField(
            'Faturamento de Lançamento (em milhares)',
            validators=[
                OptionalValidator(),
                PositiveDecimalValidator(message="Faturamento deve ser um valor positivo")
            ],
            render_kw={
                'placeholder': 'Ex: 150000.00',
                'class'      : 'form-control',
                'step'       : '0.01',
                'min'        : '0'
            }
    )

    # Media information
    poster = FileField(
            'Poster do Filme',
            validators=[
                OptionalValidator(),
                FileAllowed(ImageProcessingService.ALLOWED_EXTENSIONS,
                            "Apenas imagens "
                            f"{" ou ".join([", ".join(list(ImageProcessingService.SUPPORTED_FORMATS)[:-1]), list(ImageProcessingService.SUPPORTED_FORMATS)[-1]])} "
                            "são permitidas")
            ],
            render_kw={
                'class' : 'form-control',
                'accept': 'image/*'
            }
    )

    trailer_youtube = StringField(
            'URL do Trailer (YouTube)',
            validators=[
                OptionalValidator(),
                YouTubeURLValidator()
            ],
            render_kw={
                'placeholder': 'https://www.youtube.com/watch?v=...',
                'class'      : 'form-control'
            }
    )

    # Genre selection (handled via JavaScript, fallback for non-JS browsers)
    generos_selecionados = HiddenField(
            'Gêneros Selecionados',
            default='[]'  # JSON array of genre IDs
    )

    # Submit buttons
    submit = SubmitField(
            'Salvar Filme',
            render_kw={'class': 'btn btn-primary'}
    )

    cancel = SubmitField(
            'Cancelar',
            render_kw={'class': 'btn btn-secondary', 'formnovalidate': True}
    )

    def __init__(self, obj=None, **kwargs):
        """
        Initialize the form with optional object for editing.

        Args:
            obj: Optional Filme object for editing (sets reference_obj for validation)
            **kwargs: Additional form arguments
        """
        super().__init__(**kwargs)
        self.reference_obj = obj


class FilmeDeleteForm(FlaskForm):
    """
    Form for confirming movie deletion.

    Requires user to type the movie title for confirmation to prevent
    accidental deletions.
    """

    filme_id = HiddenField('ID do Filme',
                           validators=[CampoImutavel('id')]
                           )

    confirm_title = StringField(label="",
                                validators=[
                                    DataRequired(
                                        message="É necessário digitar o título para confirmar a "
                                                "exclusão")
                                ],
                                render_kw={
                                    'placeholder' : 'Digite o título original do filme',
                                    'class'       : 'form-control',
                                    'autocomplete': 'off'
                                }
                                )

    submit = SubmitField('Confirmar Exclusão',
                         render_kw={'class': 'btn btn-danger'}
                         )

    cancel = SubmitField('Cancelar',
                         render_kw={'class': 'btn btn-secondary', 'formnovalidate': True}
                         )

    def __init__(self, obj=None, **kwargs):
        """
        Initialize the delete form with the movie object.

        Args:
            obj: Filme object to be deleted (required for validation)
            **kwargs: Additional form arguments
        """
        super().__init__(**kwargs)
        self.reference_obj = obj
        if obj:
            self.filme_id.data = str(obj.id)

    def validate_confirm_title(self, field):
        """
        Custom validation to ensure the entered title matches the movie title.

        Args:
            field: The confirm_title field

        Raises:
            ValidationError: If the title doesn't match
        """
        if not self.reference_obj:
            raise ValidationError("Erro interno: objeto de referência não encontrado")

        entered_title = field.data.strip() if field.data else ""
        original_title = self.reference_obj.titulo_original.strip()

        if entered_title.lower() != original_title.lower():
            raise ValidationError(
                    f"O título digitado não confere. Digite exatamente: {original_title}"
            )


class AdicionarElencoForm(FlaskForm):
    """
    Formulário para adicionar membros do elenco a um filme.
    
    Permite selecionar uma pessoa e definir o personagem que ela interpreta.
    """

    pessoa_id = HiddenField(
            'ID da Pessoa',
            validators=[
                DataRequired(message="É obrigatório selecionar uma pessoa"),
                UUIDValidator(message="ID da pessoa inválido")
            ]
    )

    personagem = StringField(
            'Personagem',
            validators=[
                DataRequired(message="É obrigatório informar o nome do personagem"),
                Length(max=100, message="O nome do personagem deve ter no máximo 100 caracteres")
            ],
            render_kw={
                'placeholder': 'Digite o nome do personagem',
                'class'      : 'form-control'
            }
    )

    creditado = BooleanField(
            'Creditado no filme?',
            default=True
    )

    tempo_de_tela_minutos = IntegerField(
            'Tempo de tela (minutos)',
            validators=[
                OptionalValidator(),
                NumberRange(min=1, message="O tempo de tela deve ser um número positivo")
            ],
            render_kw={
                'placeholder': 'Ex: 90',
                'class'      : 'form-control',
                'min'        : '1'
            }
    )

    submit = SubmitField(
            'Adicionar ao Elenco',
            render_kw={'class': 'btn btn-primary'}
    )


class EditarElencoForm(FlaskForm):
    """
    Formulário para editar membros do elenco de um filme.

    Permite alterar a pessoa e/ou o personagem de uma atuação existente.
    """

    pessoa_id = HiddenField(
            'ID da Pessoa',
            validators=[
                DataRequired(message="É obrigatório selecionar uma pessoa"),
                UUIDValidator(message="ID da pessoa inválido"),
                CampoImutavel('pessoa_id')
            ]
    )

    personagem = StringField(
            'Personagem',
            validators=[
                DataRequired(message="É obrigatório informar o nome do personagem"),
                Length(max=100, message="O nome do personagem deve ter no máximo 100 caracteres")
            ],
            render_kw={
                'placeholder': 'Digite o nome do personagem',
                'class'      : 'form-control'
            }
    )

    creditado = BooleanField(
            'Creditado no filme?',
            default=True
    )

    tempo_de_tela_minutos = IntegerField(
            'Tempo de tela (minutos)',
            validators=[
                OptionalValidator(),
                NumberRange(min=1, message="O tempo de tela deve ser um número positivo")
            ],
            render_kw={
                'placeholder': 'Ex: 90',
                'class'      : 'form-control',
                'min'        : '1'
            }
    )

    submit = SubmitField(
            'Salvar Alterações',
            render_kw={'class': 'btn btn-primary'}
    )

    def __init__(self, obj=None, **kwargs):
        """
        Initialize the form with optional object for editing.

        Args:
            obj: Optional Atuacao object for editing (sets reference_obj for validation)
            **kwargs: Additional form arguments
        """
        super().__init__(**kwargs)
        self.reference_obj = obj


class AdicionarEquipeTecnicaForm(FlaskForm):
    """
    Formulário para adicionar membros da equipe técnica a um filme.
    
    Permite selecionar uma pessoa e definir sua função técnica no filme.
    """

    pessoa_id = HiddenField(
            'ID da Pessoa',
            validators=[
                DataRequired(message="É obrigatório selecionar uma pessoa"),
                UUIDValidator(message="ID da pessoa inválido")
            ]
    )

    funcao_tecnica_id = SelectField(
            'Função Técnica',
            validators=[
                DataRequired(message="É obrigatório selecionar uma função técnica")
            ],
            coerce=str,
            render_kw={
                'class': 'form-select'
            }
    )

    creditado = BooleanField(
            'Creditado no filme?',
            default=True
    )

    submit = SubmitField(
            'Adicionar à Equipe Técnica',
            render_kw={'class': 'btn btn-primary'}
    )


class EditarEquipeTecnicaForm(FlaskForm):
    """
    Formulário para editar membros da equipe técnica de um filme.
    
    Permite alterar a pessoa e/ou a função técnica de um membro da equipe.
    """

    pessoa_id = HiddenField(
            'ID da Pessoa',
            validators=[
                DataRequired(message="É obrigatório selecionar uma pessoa"),
                UUIDValidator(message="ID da pessoa inválido"),
                CampoImutavel('pessoa_id')
            ]
    )

    funcao_tecnica_id = SelectField(
            'Função Técnica',
            validators=[
                DataRequired(message="É obrigatório selecionar uma função técnica")
            ],
            coerce=str,
            render_kw={
                'class': 'form-select'
            }
    )

    creditado = BooleanField(
            'Creditado no filme?',
            default=True
    )

    submit = SubmitField(
            'Salvar Alterações',
            render_kw={'class': 'btn btn-primary'}
    )

    def __init__(self, obj=None, **kwargs):
        """
        Initialize the form with optional object for editing.

        Args:
            obj: Optional EquipeTecnica object for editing (sets reference_obj for validation)
            **kwargs: Additional form arguments
        """
        super().__init__(**kwargs)
        self.reference_obj = obj
