from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms.fields.simple import BooleanField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from app.services.imageprocessing_service import ImageProcessingService
from ..validators import CampoImutavel, SenhaComplexa, UniqueEmail


class RegistrationForm(FlaskForm):
    """Formulário para cadastro de usuário com validação de email.

    Valida o nome do usuário, a exclusividade do email e a complexidade da senha.
    """
    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome para cadastro"),
                        Length(max=60, message="O nome pode ter até 60 caracteres")])
    email = StringField(
            label="Email",
            validators=[InputRequired(message="É obrigatório informar um email para cadastro"),
                        Email(message="Informe um email válido"),
                        Length(max=180, message="O email pode ter até 180 caracteres"),
                        UniqueEmail(message="Este email já está cadastrado no sistema")])
    password = PasswordField(
            label="Senha",
            validators=[InputRequired(message="É necessário escolher uma senha"),
                        SenhaComplexa()])
    password2 = PasswordField(
            label="Confirme a senha",
            validators=[InputRequired(message="É necessário repetir a senha"),
                        EqualTo('password', message="As senhas não são iguais")])
    submit = SubmitField("Criar uma conta no sistema")


class LoginForm(FlaskForm):
    """
    Form for user login with email and password.

    Includes optional remember me functionality.
    """
    email = StringField(
            label="Email",
            validators=[InputRequired(message="É obrigatório informar um email para login"),
                        Email(message="Informe um email válido"),
                        Length(max=180, message="O email pode ter até 180 caracteres")])
    password = PasswordField(
            label="Senha",
            validators=[InputRequired(message="É necessário informar a senha")])
    remember_me = BooleanField(
            label="Permanecer conectado?",
            default=True)
    submit = SubmitField("Entrar")


class AskToResetPasswordForm(FlaskForm):
    """Formulário para solicitar redefinição de senha.

    Valida o formato do email antes de enviar o link de redefinição de senha.
    """
    email = StringField(
            label="Email",
            validators=[
                InputRequired(message="É obrigatório informar o email para o qual se deseja "
                                      "definir nova senha"),
                Email(message="Informe um email válido"),
                Length(max=180, message="O email pode ter até 180 caracteres")
            ])
    submit = SubmitField("Solicitar redefinição de senha")


class SetNewPasswordForm(FlaskForm):
    """Formulário para definir nova senha após reset.

    Valida a complexidade da senha e confirma que as senhas correspondem.
    """
    password = PasswordField(
            label="Nova senha",
            validators=[InputRequired(message="É necessário escolher uma senha"),
                        SenhaComplexa()])
    password2 = PasswordField(
            label="Confirme a senha",
            validators=[InputRequired(message="É necessário repetir a senha"),
                        EqualTo('password', message="As senhas não são iguais")])
    submit = SubmitField("Redefinir senha")


class ProfileForm(FlaskForm):
    """
    Form for updating user profile information.

    Allows modification of name, 2FA settings, and profile photo.
    Email is immutable once set.
    """

    def __init__(self, user=None, **kwargs):
        """
        Initialize profile form with reference user.

        Args:
            user: moviedb.models.user.User | None: User object to validate against, defaults to
            current_user.
            **kwargs: dict: Additional keyword arguments passed to FlaskForm.
        """
        super().__init__(**kwargs)
        self.reference_obj = user or current_user

    id = HiddenField(validators=[CampoImutavel(field_name='id',
                                               message="Você não pode alterar o ID do usuário.")])

    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome"),
                        Length(max=60,
                               message="O nome pode ter até 60 caracteres")],
            render_kw={
                'placeholder': 'Digite o seu nome'
            }
    )
    email = StringField(
            label="Email",
            validators=[CampoImutavel(field_name='email',
                                      message="Você não pode alterar o email.")],
            render_kw={
                'placeholder': 'Digite o seu melhor email'
            }
    )

    usa_2fa = BooleanField(
            label="Ativar o segundo fator de autenticação")

    foto = FileField(
            label="Foto de perfil",
            validators=[FileAllowed(ImageProcessingService.ALLOWED_EXTENSIONS,
                                    "Apenas imagens "
                                    f"{" ou ".join([", ".join(list(ImageProcessingService.SUPPORTED_FORMATS)[:-1]), list(ImageProcessingService.SUPPORTED_FORMATS)[-1]])} "
                                    "são permitidas")])

    remover_foto = BooleanField(
            label="Remover foto atual",
            default=False)

    submit = SubmitField("Efetuar as mudanças")


class Read2FACodeForm(FlaskForm):
    """
    Form for reading and validating 2FA codes.

    Accepts either 6-character TOTP codes or 8-character backup codes.
    """
    codigo = StringField(
            label="Código",
            validators=[
                InputRequired(
                        message="Informe o código fornecido pelo aplicativo autenticador ou um código "
                                "de reserva"),
                Length(min=6, max=8)],
            render_kw={'autocomplete': 'one-time-code',
                       'pattern'     : r'^([A-Za-z0-9]{6}|[A-Za-z0-9]{8})$'})  # 6 ou 8
    # caracteres alfanuméricos
    submit = SubmitField("Enviar código")
