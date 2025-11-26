from flask_wtf import FlaskForm
from wtforms.fields.simple import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length


class FuncaoTecnicaEditForm(FlaskForm):
    """Formulário para edição de funções técnicas.

    Attributes:
        nome: Nome da função técnica (obrigatório, até 100 caracteres)
        descricao: Descrição do gênero (opcional, até 1024 caracteres)
        ativo: Indica se a função técnica está ativa (padrão: True)
        submit: Botão de submissão do formulário
    """
    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome para a função técnica"),
                        Length(max=100, message="O nome pode ter até 100 caracteres"),],
            render_kw={
                'placeholder': 'Digite o nome da função técnica'
            }
    )

    descricao = TextAreaField(
            label="Descrição",
            validators=[Length(max=1024, message="A descrição pode ter até 1024 caracteres")],
            render_kw={
                'placeholder': 'O que essa função técnica faz?'
            }

    )

    ativo = BooleanField(
            label="Ativo?",
            default=True
    )

    submit = SubmitField('Salvar mudanças')
