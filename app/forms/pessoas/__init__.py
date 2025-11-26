from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms.fields.simple import StringField, SubmitField, TextAreaField
from wtforms.fields.datetime import DateField
from wtforms.validators import InputRequired, Length, Optional

from app.services.imageprocessing_service import ImageProcessingService
from app.forms.validators import ValidadorDataAntesDe, ValidadorDataDepoisDe


class PessoaForm(FlaskForm):
    """Formulário para criação e edição de pessoas.
    
    Permite gerenciar todas as informações de uma pessoa incluindo dados biográficos
    e upload de foto com validação adequada.
    """
    
    nome = StringField(
        label="Nome",
        validators=[
            InputRequired(message="É obrigatório informar o nome da pessoa"),
            Length(max=100, message="O nome pode ter até 100 caracteres")
        ],
        render_kw={
            'placeholder': 'Nome completo da pessoa'
        }
    )
    
    data_nascimento = DateField(
        label="Data de Nascimento",
        validators=[
            Optional(), 
            ValidadorDataAntesDe(
                datetime.now().date(), 
                message="A data de nascimento não pode ser futura"
            )
        ],
        render_kw={
            'placeholder': 'dd/mm/aaaa'
        }
    )
    
    data_falecimento = DateField(
        label="Data de Falecimento",
        validators=[
            Optional(), 
            ValidadorDataDepoisDe(
                'data_nascimento', 
                message="A data de falecimento deve ser posterior à data de nascimento"
            )
        ],
        render_kw={
            'placeholder': 'dd/mm/aaaa (opcional)'
        }
    )
    
    local_nascimento = StringField(
        label="Local de Nascimento",
        validators=[
            Optional(),
            Length(max=100, message="O local de nascimento pode ter até 100 caracteres")
        ],
        render_kw={
            'placeholder': 'Cidade, Estado/País'
        }
    )
    
    biografia = TextAreaField(
        label="Biografia",
        validators=[Optional()],
        render_kw={
            'placeholder': 'Informações biográficas sobre a pessoa',
            'rows': 6
        }
    )
    
    foto = FileField(
        label="Foto",
        validators=[
            Optional(),
            FileAllowed(
                ImageProcessingService.ALLOWED_EXTENSIONS,
                f"Apenas imagens {' ou '.join([', '.join(ImageProcessingService.ALLOWED_EXTENSIONS[:-1]), ImageProcessingService.ALLOWED_EXTENSIONS[-1]])} são permitidas"
            )
        ],
        render_kw={
            'accept': 'image/*'
        }
    )
    
    # Campo para nome artístico (apenas quando a pessoa é ator)
    nome_artistico = StringField(
        label="Nome Artístico",
        validators=[
            Optional(),
            Length(max=100, message="O nome artístico pode ter até 100 caracteres")
        ],
        render_kw={
            'placeholder': 'Nome artístico do ator (opcional)'
        }
    )
    
    submit = SubmitField("Salvar")
    
    def __init__(self, *args, **kwargs):
        """Inicializa o formulário.
        
        Args:
            pessoa: Instância de Pessoa para pré-preenchimento (opcional)
            **kwargs: Argumentos adicionais para FlaskForm
        """
        pessoa = kwargs.pop('pessoa', None)
        super().__init__(*args, **kwargs)
        
        # Se uma pessoa foi fornecida, pré-preencher os campos
        if pessoa:
            self.nome.data = pessoa.nome
            self.data_nascimento.data = pessoa.data_nascimento
            self.data_falecimento.data = pessoa.data_falecimento
            self.local_nascimento.data = pessoa.local_nascimento
            self.biografia.data = pessoa.biografia
            
            # Se a pessoa é um ator, pré-preencher o nome artístico
            if pessoa.ator:
                self.nome_artistico.data = pessoa.ator.nome_artistico