from datetime import datetime
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, \
    url_for
from flask_login import current_user, fresh_login_required, login_required
from markupsafe import Markup

from app import anonymous_required
from app.forms.auth import AskToResetPasswordForm, LoginForm, ProfileForm, Read2FACodeForm, \
    RegistrationForm, \
    SetNewPasswordForm
from app.models import User
from app.services.backup2fa_service import Backup2FAService
from app.services.imageprocessing_service import ImageProcessingService
from app.services.user_2fa_service import Autenticacao2FA, User2FAService
from app.services.user_service import UserOperationStatus, UserService

auth_bp = Blueprint(name='auth',
                    import_name=__name__,
                    url_prefix='/auth',
                    template_folder="templates", )


@auth_bp.route('/register', methods=['GET', 'POST'])
@anonymous_required
def register():
    """Exibe o formulário de registro de usuário e processa o cadastro.

    Usuários já autenticados não podem acessar esta rota. Se o formulário for
    enviado e validado, delega o registro ao UserService. O usuário deve confirmar
    o email antes de conseguir logar. Caso contrário, renderiza o template de registro.

    Returns:
        flask.Response: Redireciona para a página inicial ou renderiza o template
            de registro.
    """
    email_service = current_app.extensions.get('email_service')
    if not email_service:
        raise ValueError("EmailService não configurado na aplicação")

    form = RegistrationForm()
    if form.validate_on_submit():
        resultado = UserService.registrar_usuario(
                nome=form.nome.data,
                email=form.email.data,
                password=form.password.data,
                email_service=email_service
        )

        if resultado.status == UserOperationStatus.SUCCESS:
            flash("Cadastro efetuado com sucesso. Antes de logar na aplicação, ative a "
                  "sua conta seguindo as instruções da mensagem de email que lhe foi "
                  "enviada.", category='success')
            return redirect(url_for('root.index'))
        else:
            flash(f"Erro ao registrar usuário: {resultado.error_message}", category='danger')

    return render_template('auth/web/register.jinja2',
                           title="Cadastrar um novo usuário",
                           form=form)


@auth_bp.route('/ativar_usuario/<token>')
@anonymous_required
def ativar_usuario(token):
    """Valida o email do usuário a partir de um token JWT enviado na URL.

    Usuários autenticados não podem acessar esta rota. Delega ao UserService
    a validação do token e ativação do usuário. Exibe mensagens de sucesso ou
    erro conforme o caso.

    Args:
        token (str): Token JWT enviado na URL para validação do email.

    Returns:
        flask.Response: Redireciona para a página de login ou inicial, conforme o caso.
    """
    resultado = UserService.ativar_usuario_por_token(token)

    if resultado.status == UserOperationStatus.SUCCESS:
        flash(f"Conta ativada e email {resultado.user.email} validado!", category='success')
        return redirect(url_for('auth.login'))
    elif resultado.status == UserOperationStatus.USER_ALREADY_ACTIVE:
        flash(f"Conta já havia sido ativada e o email {resultado.user.email} validado.",
              category='info')
        return redirect(url_for('auth.login'))
    else:
        flash("Processo de ativação da conta falhou. Inicie uma nova ativação.", category='warning')
    return redirect(url_for('root.index'))


@auth_bp.route('/reativar_usuario/<uuid:user_id>')
@anonymous_required
def reativar_usuario(user_id):
    """Reenvia o email de ativação para o usuário com o ID fornecido.

    Usuários autenticados não podem acessar esta rota. Delega ao UserService
    a geração de token e envio de email. Sempre exibe uma mensagem informando
    que, se houver uma conta inativa, um email será enviado. Caso contrário,
    redireciona para a página inicial.

    Args:
        user_id (uuid.UUID): ID do usuário para o qual o email de ativação será reenviado.

    Returns:
        flask.Response: Redireciona para a página inicial.
    """
    email_service = current_app.extensions.get('email_service')
    if not email_service:
        raise ValueError("EmailService não configurado na aplicação")

    # Solicita reativação (o serviço normaliza o email internamente)
    resultado = UserService.reativar_usuario(user_id, email_service)

    # Por segurança, sempre exibe a mesma mensagem
    flash(f"Se houver uma conta inativa com o ID {user_id}, uma mensagem será enviada com as "
          f"instruções para ativação da conta", category='info')

    # Opcionalmente, exibe erro de envio
    if resultado.status == UserOperationStatus.SEND_EMAIL_ERROR:
        flash("Erro no envio do email de ativação", category="danger")

    return redirect(url_for('root.index'))


@auth_bp.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    """Exibe o formulário de login e processa a autenticação do usuário.

    Usuários já autenticados não podem acessar esta rota. Se o formulário for
    enviado e validado, verifica as credenciais do usuário. Se o usuário existir,
    estiver ativo e a senha estiver correta, realiza o login. Se efetuar o login
    redireciona para a página desejada ou para a página inicial. Caso contrário,
    exibe mensagens de erro e permanece na página de login.

    Returns:
        flask.Response: Redireciona para a página desejada, página inicial ou
            renderiza o template de login.
    """
    form = LoginForm()

    if form.validate_on_submit():
        from app.services.email_service import EmailValidationService

        try:
            email_normalizado = EmailValidationService.normalize(form.email.data)
        except ValueError:
            flash("Email ou senha incorretos", category='warning')
            return render_template('auth/web/login.jinja2',
                                   title="Login",
                                   form=form)

        usuario = User.get_by_email(email_normalizado)

        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('root.index')

        if usuario is None or not usuario.check_password(form.password.data):
            flash("Email ou senha incorretos", category='warning')
        elif not UserService.conta_ativa(usuario):
            flash(Markup("Sua conta ainda não foi ativada. "
                         f"Precisa de um <a href='"
                         f"{url_for('auth.reativar_usuario', user_id=usuario.id)}'>"
                         "novo email de ativação</a>?"), category='warning')
        elif usuario.usa_2fa:
            # CRITICO: Token indicando que a verificação da senha está feita, mas o 2FA
            #  ainda não. Necessário para proteger a rota /get2fa.
            session['pending_2fa_token'] = UserService. \
                set_pending_2fa_token_data(usuario=usuario,
                                           remember_me=bool(form.remember_me.data),
                                           next_page=next_page)
            current_app.logger.debug("pending_2fa_token: %s" % (session['pending_2fa_token'],))
            flash("Conclua o login digitando o código do segundo fator de autenticação",
                  category='info')
            return redirect(url_for('auth.get2fa'))
        else:
            UserService.efetuar_login(usuario, remember_me=form.remember_me.data)
            flash(f"Usuario {usuario.email} logado", category='success')

            # Verifica a idade da senha
            max_age = current_app.config.get('PASSWORD_MAX_AGE', 0)
            if max_age > 0:
                idade_senha = UserService.verificar_idade_senha(usuario)
                if idade_senha is not None and idade_senha > max_age:
                    flash(f"Sua senha tem {idade_senha} dias. Por motivos de segurança, "
                          f"recomendamos que você altere sua senha.",
                          category='warning')
            return redirect(next_page)

    return render_template('auth/web/login.jinja2',
                           title="Login",
                           form=form)


@auth_bp.route('/get2fa', methods=['GET', 'POST'])
@anonymous_required
def get2fa():
    """Exibe e processa o formulário de segundo fator de autenticação (2FA).

    Usuários já autenticados não podem acessar esta rota. Verifica se a sessão
    contém informações de usuário pendente de 2FA. Implementa expiração da sessão
    de 2FA baseada em tempo (opcional). Valida o código 2FA informado pelo usuário
    (TOTP ou código reserva). Finaliza o login se o código estiver correto, ou
    exibe mensagem de erro. Limpa variáveis de sessão após sucesso ou falha.

    Returns:
        flask.Response: Redireciona para a página de login, página desejada após
            login ou renderiza o formulário de 2FA.
    """
    # CRITICO: Verifica se a variável de sessão que indica que a senha foi validada
    #  está presente. Se não estiver, redireciona para a página de login.
    pending_2fa_token = session.get('pending_2fa_token')
    if not pending_2fa_token:
        current_app.logger.warning(
                "Tentativa de acesso 2FA não autorizado a partir do IP %s" % (request.remote_addr,))
        flash("Ocorreu um problema durante o seu login.", category='danger')
        return redirect(url_for('auth.login'))

    dados_token = UserService.get_pending_2fa_token_data(pending_2fa_token)
    if not dados_token.status == UserOperationStatus.SUCCESS:
        # Token inválido ou expirado. Limpa variável de sessão e redireciona para login
        session.pop('pending_2fa_token', None)
        current_app.logger.warning(
                "Tentativa de acesso 2FA com token inválido ou expirado a partir do IP %s" %
                (request.remote_addr,))
        flash("Sessão de autenticação inválida ou expirada. Reinicie o login.", category='warning')
        return redirect(url_for('auth.login'))

    usuario = dados_token.user
    remember_me = dados_token.extra_data.get('remember_me', False)
    next_page = dados_token.extra_data.get('next')

    form = Read2FACodeForm()
    if form.validate_on_submit():
        if usuario is None or not usuario.usa_2fa:
            session.pop('pending_2fa_token', None)
            return redirect(url_for('auth.login'))

        token = str(form.codigo.data)
        resultado_validacao = User2FAService.validar_codigo_2fa(usuario, token)

        if resultado_validacao.success:
            session.pop('pending_2fa_token', None)
            UserService.efetuar_login(usuario, remember_me=remember_me)
            flash(f"Usuario {usuario.email} logado", category='success')

            if len(resultado_validacao.security_warnings) > 0:
                for warning in resultado_validacao.security_warnings:
                    flash(Markup(warning), category='warning')

            # Verifica a idade da senha
            max_age = current_app.config.get('PASSWORD_MAX_AGE', 0)
            if max_age > 0:
                idade_senha = UserService.verificar_idade_senha(usuario)
                if idade_senha is not None and idade_senha > max_age:
                    flash(f"Sua senha tem {idade_senha} dias. Por motivos de segurança, "
                          f"recomendamos que você altere sua senha.",
                          category='warning')
            return redirect(next_page)

        if resultado_validacao.method_used == Autenticacao2FA.NOT_ENABLED:
            # Usuário não tem 2FA habilitado. Limpa variáveis de sessão e volta para o login
            session.pop('pending_2fa_token', None)
            current_app.logger.error("Usuário %s sem 2FA tentando acessar a página de 2FA" % (
                usuario.id,))
            flash("Acesso negado. Reinicie o processo de login.", category='danger')
            return redirect(url_for('auth.login'))

        # Código errado ou reusado. Registra tentativa falha e permanece na página de 2FA
        # current_app.logger.warning("Código 2FA inválido para usuario %s a partir do IP %s" % (
        #     usuario.id, request.remote_addr,))
        flash("Código incorreto. Tente novamente", category='warning')

    return render_template('auth/web/2fa.jinja2',
                           title="Login",
                           title_card="Segundo fator de autenticação",
                           form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Realiza o logout do usuário autenticado.

    Encerra a sessão do usuário, exibe uma mensagem de sucesso e redireciona
    para a página inicial.

    Returns:
        flask.Response: Redireciona para a página inicial após logout.
    """
    UserService.efetuar_logout(current_user)
    flash("Logout efetuado com sucesso!", category='success')
    return redirect(url_for('root.index'))


@auth_bp.route('/new_password', methods=['GET', 'POST'])
@anonymous_required
def new_password():
    """Exibe o formulário para solicitar redefinição de senha.

    Usuários autenticados não podem acessar esta rota. Delega ao UserService
    a geração de token e envio de email. Sempre exibe uma mensagem informando
    que, se houver uma conta, um email será enviado. Renderiza o formulário caso
    não seja enviado ou validado.

    Returns:
        flask.Response: Redireciona para a página de login ou renderiza o formulário.
    """
    email_service = current_app.extensions.get('email_service')
    if not email_service:
        raise ValueError("EmailService não configurado na aplicação")

    form = AskToResetPasswordForm()
    if form.validate_on_submit():
        email = form.email.data

        # Solicita reset (o serviço normaliza o email internamente)
        resultado = UserService.solicitar_reset_senha(email, email_service)

        # Por segurança, sempre exibe a mesma mensagem
        flash(f"Se houver uma conta com o email {email}, uma mensagem será enviada com as "
              f"instruções para a troca da senha", category='info')

        # Opcionalmente, exibe erro de envio
        if resultado.status == UserOperationStatus.SEND_EMAIL_ERROR:
            flash("Erro no envio do email de redefinição de senha", category="danger")

        return redirect(url_for('auth.login'))

    return render_template('auth/web/ask_for_email.jinja2',
                           title="Solicitar nova senha",
                           title_card="Redefinir minha senha",
                           form=form)


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
@anonymous_required
def reset_password(token):
    """Exibe o formulário para redefinição de senha e processa a troca de senha.

    Usuários autenticados não podem acessar esta rota. Delega ao UserService
    a validação do token e redefinição da senha. Em caso de token inválido ou
    usuário inexistente, exibe mensagem de erro.

    Args:
        token (str): Token JWT enviado na URL para redefinição de senha.

    Returns:
        flask.Response: Redireciona para a página de login ou inicial, ou renderiza
            o formulário de redefinição de senha.
    """
    form = SetNewPasswordForm()
    if form.validate_on_submit():
        resultado = UserService.redefinir_senha_por_token(token, form.password.data)

        if resultado.status == UserOperationStatus.SUCCESS:
            flash("Sua senha foi redefinida com sucesso", category='success')
            return redirect(url_for('auth.login'))
        elif resultado.status == UserOperationStatus.TOKEN_EXPIRED:
            flash("A operação demorou mais do que o esperado. Solicite uma nova :"
                  "redefinição de senha", category='warning')
            return redirect(url_for('auth.new_password'))
        elif resultado.status == UserOperationStatus.INVALID_TOKEN:
            flash("Token inválido ou expirado", category='warning')
            return redirect(url_for('root.index'))
        else:
            flash("Erro ao redefinir senha", category='warning')
            return redirect(url_for('root.index'))

    return render_template('auth/web/new_password.jinja2',
                           title="Redefinir senha",
                           title_card="Escolha uma nova senha",
                           form=form)


@auth_bp.route('/<uuid:user_id>/foto')
@login_required
def foto(user_id):
    """Serve a foto do usuário.

    Requer autenticação. Apenas usuários logados podem ver fotos.
    Se o usuário não possui foto, retorna o identicon gerado automaticamente.

    Args:
        user_id (uuid.UUID): ID do usuário.

    Returns:
        flask.Response: Imagem da foto do usuário ou identicon.
    """
    try:
        usuario = User.get_by_id(user_id,
                                 raise_if_not_found=True)
    except User.RecordNotFoundError:
        # Usuário não encontrado - retorna placeholder
        foto_data = ImageProcessingService.gerar_placeholder(300, 400,
                                                             "Usuário\nnão encontrado",
                                                             36)
        mime_type = 'image/png'
    else:
        foto_data, mime_type = usuario.foto
    return ImageProcessingService.servir_imagem(foto_data, mime_type)


@auth_bp.route('/<uuid:user_id>/avatar')
@login_required
def avatar(user_id):
    """Serve o avatar do usuário.

    Requer autenticação. Apenas usuários logados podem ver avatares.
    Se o usuário não possui foto, retorna o identicon gerado automaticamente.

    Args:
        user_id (uuid.UUID): ID do usuário.

    Returns:
        flask.Response: Imagem do avatar do usuário ou identicon.
    """
    try:
        usuario = User.get_by_id(user_id,
                                 raise_if_not_found=True)
    except User.RecordNotFoundError:
        # Usuário não encontrado - retorna placeholder
        avatar_data = ImageProcessingService.gerar_placeholder(64, 64,
                                                                    "Usuário\nnão encontrado",
                                                                    12)
        mime_type = 'image/png'
    else:
        avatar_data, mime_type = usuario.avatar
    return ImageProcessingService.servir_imagem(avatar_data, mime_type)


@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/profile', methods=['GET', 'POST'])
@fresh_login_required
def profile():
    """Exibe e processa o formulário de edição do perfil do usuário autenticado.

    Permite ao usuário alterar seu nome. O email não pode ser alterado por segurança.
    Valida e processa as alterações, salvando no banco de dados e exibindo mensagens
    de sucesso ou erro.

    Returns:
        flask.Response: Redireciona para a página de perfil após alterações ou
            renderiza o formulário de perfil.
    """
    form = ProfileForm(user=current_user)

    # Preenche o formulário com dados atuais do usuário no GET
    if request.method == 'GET':
        # Limpa secret órfão de ativações 2FA incompletas/expiradas
        # Se o usuário tem otp_secret mas usa_2fa=False e não há token válido, limpa o secret
        if current_user.otp_secret and not current_user.usa_2fa:
            activating_2fa_token = session.get('activating_2fa_token')
            if not activating_2fa_token:
                # Não há token, então a ativação foi abandonada - limpa o secret
                from app import db
                current_user.otp_secret = None
                db.session.commit()
                current_app.logger.debug(
                        "Secret órfão removido para usuário %s (sem token de ativação válido)" % (
                            current_user.email,))

        form.id.data = str(current_user.id)
        form.nome.data = current_user.nome
        form.email.data = current_user.email
        form.usa_2fa.data = current_user.usa_2fa

    if form.validate_on_submit():
        # Captura o estado do 2FA ANTES de atualizar perfil
        # (precisamos comparar antes do commit para evitar problemas com refresh)
        quer_ativar_2fa = form.usa_2fa.data and not current_user.usa_2fa

        # Verifica se há foto cropada
        foto_cropada_file = request.files.get('foto_cropada', None)
        if foto_cropada_file and foto_cropada_file.filename:
            nova_foto = foto_cropada_file
        else:
            # Processa foto do upload original (ignora se o arquivo estiver vazio ou sem nome)
            nova_foto = None
            if form.foto.data and hasattr(form.foto.data, 'filename') and form.foto.data.filename:
                nova_foto = form.foto.data

        resultado = UserService.atualizar_perfil(
                usuario=current_user,
                novo_nome=form.nome.data,
                nova_foto=nova_foto,
                remover_foto=form.remover_foto.data
        )

        if resultado.status != UserOperationStatus.SUCCESS:
            flash(f"Erro ao atualizar perfil: {resultado.error_message}",
                  category='danger')
            return redirect(url_for('auth.profile'))

        # Agora processa mudanças de 2FA
        if quer_ativar_2fa:
            # Ativar 2FA - inicia fluxo de ativação
            resultado_2fa = User2FAService.iniciar_ativacao_2fa(current_user)
            if resultado_2fa.status == Autenticacao2FA.ENABLING:
                # Salva o token na sessão para validação posterior
                session['activating_2fa_token'] = resultado_2fa.token
                # Redireciona para página de validação com QR code
                return redirect(url_for('auth.ativar_2fa'))
            else:
                flash("Erro na ativação do 2FA", 'danger')
                return redirect(url_for('auth.profile'))
        # Nota: desativação de 2FA é tratada via modal e rota /disable_2fa

        # Se não mudou 2FA, apenas mostra sucesso
        flash('Perfil atualizado com sucesso', 'success')
        return redirect(url_for('root.index'))

    # Se chegou aqui e é POST, a validação falhou
    # Restaura campos imutáveis aos valores corretos antes de renderizar
    if request.method == 'POST':
        form.id.data = str(current_user.id)
        form.email.data = current_user.email

    backup_codes_count = 0
    if current_user.usa_2fa:
        backup_codes_count = Backup2FAService.contar_tokens_disponiveis(current_user)

    # Busca as avaliações do usuário ordenadas por título do filme (A-Z)
    avaliacoes = UserService.listar_avaliacoes(current_user, order_by='titulo', ascending=True)

    return render_template('auth/web/profile.jinja2',
                           title="Perfil do usuário",
                           title_card="Altere seus dados",
                           form=form,
                           backup_codes_count=backup_codes_count,
                           avaliacoes=avaliacoes)


@auth_bp.route('ativar_2fa', methods=['GET', 'POST'])
@login_required
def ativar_2fa():
    """Ativa o segundo fator de autenticação (2FA) para o usuário autenticado.

    Se o usuário já possui 2FA ativado, exibe mensagem informativa e redireciona
    para o perfil. Valida o token de ativação da sessão. Exibe o formulário para
    digitar o código TOTP gerado pelo autenticador. Se o código for válido, ativa
    o 2FA, gera códigos de backup e exibe-os ao usuário. Se o código for inválido,
    exibe mensagem de erro e redireciona para a página de ativação. Renderiza o
    formulário de ativação do 2FA caso não seja enviado ou validado.

    Returns:
        flask.Response: Redireciona para o perfil, página de ativação do 2FA,
            renderiza o formulário de ativação do 2FA ou exibe os códigos de backup.
    """
    if current_user.usa_2fa:
        flash("Configuração já efetuada. Para alterar, desative e reative o uso do "
              "segundo fator de autenticação", category='info')
        return redirect(url_for('auth.profile'))

    # Valida o token de ativação 2FA da sessão
    activating_2fa_token = session.get('activating_2fa_token')
    validacao = User2FAService.validar_token_ativacao_2fa(current_user, activating_2fa_token)

    if validacao.status != Autenticacao2FA.ENABLING:
        session.pop('activating_2fa_token', None)

        # Limpa secret temporário se a validação falhou (token inválido/expirado)
        # Isso evita deixar secrets órfãos no banco de dados
        if current_user.otp_secret and not current_user.usa_2fa:
            from app import db
            current_user.otp_secret = None
            db.session.commit()
            current_app.logger.debug(
                    "Secret temporário removido para usuário %s (token inválido/expirado)" % (
                        current_user.email,))

        current_app.logger.warning(
                "Falha no processo de ativação do 2FA a partir do IP %s: %s" % (
                    request.remote_addr, validacao.status))
        flash("Reinicie o processo de configuração do 2FA.", category='danger')
        return redirect(url_for('auth.profile'))

    # Regenera o QR code a partir do secret do banco (por segurança, o QR code não
    # trafega no token JWT). O secret já está salvo de forma criptografada no banco.
    from app.services.qrcode_service import QRCodeService, QRCodeConfig
    qr_service = QRCodeService.create_default()
    app_name = current_app.config.get('APP_NAME', 'Sistema')
    qr_config = QRCodeConfig()
    qr_code_base64 = qr_service.generate_totp_qrcode(
            secret=validacao.secret,
            user=current_user.email,
            issuer=app_name,
            config=qr_config,
            as_bytes=False
    )

    form = Read2FACodeForm()
    if request.method == 'POST' and form.validate():
        resultado = User2FAService.confirmar_ativacao_2fa(current_user,
                                                          secret=validacao.secret,
                                                          codigo_confirmacao=form.codigo.data)
        if resultado.status == Autenticacao2FA.ENABLED:
            codigos = resultado.backup_codes
            session.pop('activating_2fa_token', None)
            flash("Segundo fator de autenticação ativado", category='success')
            return render_template('auth/web/show_2fa_backup.jinja2',
                                   codigos=codigos,
                                   title="Códigos reserva",
                                   now=datetime.now())
        else:  # Autenticacao2FA.INVALID_CODE
            flash("O código informado está incorreto. Tente novamente.", category='warning')
        return redirect(url_for('auth.ativar_2fa'))

    return render_template('auth/web/enable_2fa.jinja2',
                           title="Ativação do 2FA",
                           title_card="Ativação do segundo fator de autenticação",
                           form=form,
                           imagem=qr_code_base64,
                           token=User2FAService.otp_secret_formatted(validacao.secret))


@auth_bp.route('/disable_2fa', methods=['POST'])
@fresh_login_required
def disable_2fa():
    """Desativa o segundo fator de autenticação (2FA) após confirmação de senha.

    Requer que o usuário digite sua senha para confirmar a desativação.
    Isso garante que apenas o dono da conta pode desativar o 2FA,
    mesmo em situações onde perdeu o aplicativo autenticador ou códigos de backup.

    Returns:
        flask.Response: Redireciona para o perfil com mensagem de sucesso ou erro.
    """
    # Verifica se o usuário realmente tem 2FA ativado
    if not current_user.usa_2fa:
        flash("O segundo fator de autenticação já está desativado", category='info')
        return redirect(url_for('auth.profile'))

    # Obtém a senha do formulário
    senha = request.form.get('password')

    if not senha:
        flash("É necessário informar a senha para desativar o 2FA", category='danger')
        return redirect(url_for('auth.profile'))

    # Valida a senha
    if not current_user.check_password(senha):
        current_app.logger.warning(
                "Tentativa de desativação de 2FA com senha incorreta para usuário %s a partir do "
                "IP %s" % (current_user.email, request.remote_addr))
        flash("Senha incorreta. A desativação do 2FA foi cancelada.", category='danger')
        return redirect(url_for('auth.profile'))

    # Senha correta - desativa o 2FA
    resultado = User2FAService.desativar_2fa(current_user)

    if resultado.status == Autenticacao2FA.DISABLED:
        current_app.logger.info("2FA desativado para usuário %s" % (current_user.email,))
        flash("Segundo fator de autenticação desativado com sucesso", category='success')
    elif resultado.status == Autenticacao2FA.NOT_ENABLED:
        flash("O segundo fator de autenticação já estava desativado", category='info')
    else:
        flash("Erro ao desativar o segundo fator de autenticação", category='danger')

    return redirect(url_for('auth.profile'))
