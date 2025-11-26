from flask_wtf import FlaskForm
from wtforms.fields.simple import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length


class GeneroEditForm(FlaskForm):
    """Formulário para edição de gêneros.

    Attributes:
        nome: Nome do gênero (obrigatório, até 40 caracteres)
        descricao: Descrição do gênero (opcional, até 1024 caracteres)
        ativo: Indica se o gênero está ativo (padrão: True)
        submit: Botão de submissão do formulário
    """
    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome para o gênero"),
                        Length(max=40, message="O nome pode ter até 40 caracteres")],
            render_kw={
                'placeholder': 'Digite o nome do gênero'
            }

    )

    descricao = TextAreaField(
            label="Descrição",
            validators=[Length(max=1024, message="A descrição pode ter até 1024 caracteres")],
            render_kw={
                'placeholder': 'O que caracteriza esse gênero?'
            }

    )

    ativo = BooleanField(
            label="Ativo?",
            default=True
    )

    submit = SubmitField('Salvar mudanças')
