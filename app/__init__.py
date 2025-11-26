import json
import logging
import os
import sys
from functools import wraps
from pathlib import Path

from flask import Flask

from app.infra import app_logging
from app.infra.modulos import bootstrap, db, login_manager, migrate, secrets_manager
from app.services.email_service import EmailService
from app.services.secret_service import consolidate_and_remove_keys, SecretsManagerError


def anonymous_required(f):
    """Decorador para restringir acesso a rotas apenas para usuários anônimos.

    Se o usuário estiver autenticado, exibe uma mensagem de aviso e redireciona para a página
    inicial; caso contrário, permite o acesso à função decorada.

    Args:
        f (function): Função a ser decorada.

    Returns:
        function: Função decorada que verifica se o usuário não está autenticado.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from flask import redirect, url_for, flash
        if current_user.is_authenticated:
            flash("Acesso não autorizado para usuários logados no sistema", category='warning')
            return redirect(url_for('root.index'))
        return f(*args, **kwargs)

    return decorated_function


def create_app(config_filename: str = 'config.dev.json') -> Flask:
    from dotenv import load_dotenv
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates',
                )

    # Criar diretório instance se não existir
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app_logging.configure_logging(logging.DEBUG)

    app.logger.info(
            "Lendo a configuração da aplicação a partir do arquivo '%s'" % (config_filename,))

    # 1. Carregar JSON base
    try:
        app.config.from_file(config_filename, load=json.load)
    except FileNotFoundError:
        app.logger.fatal("O arquivo de configuração '%s' não existe" % (config_filename,))
        sys.exit(1)
    except json.JSONDecodeError as e:
        app.logger.fatal(
                "O arquivo de configuração '%s' não é um JSON válido: %s" % (config_filename,
                                                                             str(e),))
        sys.exit(1)
    except Exception as e:
        app.logger.fatal(
                "Erro ao carregar o arquivo de configuração '%s': %s" % (config_filename, str(e),))
        sys.exit(1)

    # 2. Carregar .env.crypto se existir (procura em instance/)
    crypto_file = Path(app.instance_path) / '.env.crypto'
    if crypto_file.exists():
        load_dotenv(str(crypto_file), override=True)
        app.logger.info("Arquivo '%s' carregado" % (crypto_file, ))
    else:
        app.logger.debug("Arquivo '%s' não encontrado" % (crypto_file, ))

    # 3. Sobrescrever com variáveis de ambiente
    for key in list(app.config.keys()):
        if key in os.environ:
            app.config[key] = os.environ[key]
            app.logger.debug(f"  - Configuração sobrescrita: {key}")

    # 4. Consolidar as chaves em formato de dicionário
    encryption_keys = consolidate_and_remove_keys(app)

    # Atribuir ao config
    if encryption_keys:
        app.config['ENCRYPTION_KEYS'] = encryption_keys
        app.logger.info(f"Chaves consolidadas: {list(encryption_keys.keys())}")

    app.logger.debug("Aplicando configurações")
    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.logger.fatal("A chave 'SQLALCHEMY_DATABASE_URI' não está "
                         "presente no arquivo de configuração")
        sys.exit(1)

    if "APP_HOST" not in app.config or \
            not isinstance(app.config.get("APP_HOST"), str) or \
            app.config.get("APP_HOST") == "":
        app.logger.warning("A chave 'APP_HOST' não está presente no "
                           "arquivo de configuração. Utilizando 0.0.0.0")
        app.config["APP_HOST"] = "0.0.0.0"

    if "APP_PORT" not in app.config or \
            not isinstance(app.config.get("APP_PORT"), int) or \
            not (0 < app.config.get("APP_PORT") < 65536):
        app.logger.warning("A chave 'APP_PORT' não está presente no "
                           "arquivo de configuração. Utilizando 5000")
        app.config["APP_PORT"] = 5000

    if "SECRET_KEY" not in app.config or app.config.get("SECRET_KEY") is None:
        secret_key = os.urandom(32).hex()
        app.logger.warning("A chave 'SECRET_KEY' não está presente no arquivo de configuração")
        app.logger.warning("Gerando chave aleatória: '%s'" % (secret_key,))
        app.logger.warning("Para não invalidar os tokens gerados nesta instância da aplicação, "
                           "adicione a chave acima ao arquivo de configuração")
        app.config["SECRET_KEY"] = secret_key

    # Configura o tamanho máximo de upload (padrão: 16 MB)
    if "MAX_CONTENT_LENGTH" not in app.config or app.config.get("MAX_CONTENT_LENGTH") is None:
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
    max_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
    app.logger.info(f"MAX_CONTENT_LENGTH configurado para {max_mb:.2f} MB")

    app.logger.debug("Registrando blueprints")
    from .routes.root import root_bp
    from .routes.auth import auth_bp
    from .routes.generos import genero_bp
    from .routes.funcoes_tecnicas import funcao_tecnica_bp
    from .routes.pessoas import pessoa_bp
    from .routes.filmes import filme_bp
    from .routes.api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(root_bp)
    app.register_blueprint(genero_bp)
    app.register_blueprint(funcao_tecnica_bp)
    app.register_blueprint(pessoa_bp)
    app.register_blueprint(filme_bp)
    app.register_blueprint(api_bp)
    app.logger.debug("=====[ Rotas registradas")
    contador = 0
    for rule in app.url_map.iter_rules():
        contador += 1
        app.logger.debug("Endpoint: %s, Rule: %s" %
                         (rule.endpoint, rule))
    app.logger.debug("=====[ Total de rotas registradas: %d" % (contador, ))

    app.logger.debug("Registrando modulos")
    bootstrap.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    login_manager.init_app(app)
    try:
        secrets_manager.init_app(app)
    except SecretsManagerError as e:
        app.logger.fatal("Não foi possível inicializar o gerenciador de segredos")
        app.logger.fatal(str(e))
        sys.exit(1)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "É necessário estar logado para acessar esta funcionalidade."
    login_manager.login_message_category = 'warning'
    login_manager.refresh_view = 'auth.login'
    login_manager.needs_refresh_message = ("Para proteger a sua conta, é necessário "
                                           "logar novamente antes de acessar esta funcionalidade.")
    login_manager.needs_refresh_message_category = "info"

    app.logger.debug("Registrando o callback do login manager")

    @login_manager.user_loader
    def load_user(user_id):  # https://flask-login.readthedocs.io/en/latest/#alternative-tokens
        import uuid
        from app.models.autenticacao import User
        identifier, final_password = user_id.split('|', 1)
        try:
            auth_id = uuid.UUID(identifier)
        except ValueError:
            return None
        user = User.get_by_id(auth_id)
        return user if user and user.password.endswith(final_password) else None

    app.logger.debug("Definindo processadores de contexto")

    @app.context_processor
    def inject_globals():
        return dict(app_config=app.config)

    app.logger.debug("Configurando as extensões da aplicação")
    # Configura o serviço de email
    email_service = EmailService.create_from_config(app.config)
    app.extensions['email_service'] = email_service

    app.logger.debug("Registrando comandos CLI")
    from app.cli.secrets_cli import secrets_cli
    app.cli.add_command(secrets_cli)

    app.logger.debug("Configurando hooks de requisição")

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Trata o erro de arquivo muito grande no upload.

        Args:
            error: Erro capturado pelo Flask.

        Returns:
            flask.Response: Redireciona para a página anterior com mensagem de erro.
        """
        from flask import flash, redirect, request, url_for

        # Log detalhado para debug
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) / (1024 * 1024)
        content_length = request.content_length or 0
        content_mb = content_length / (1024 * 1024)

        app.logger.warning(f"Erro 413: Requisição muito grande")
        app.logger.warning(f"  Tamanho da requisição: {content_mb:.2f} MB ({content_length} bytes)")
        app.logger.warning(
                f"  Limite configurado: {max_mb:.2f} MB ("
                f"{app.config.get('MAX_CONTENT_LENGTH', 0)} bytes)")
        app.logger.warning(f"  URL: {request.path}")
        app.logger.warning(f"  Content-Type: {request.content_type}")

        flash(f"O arquivo enviado é muito grande. O tamanho máximo permitido é {max_mb:.0f} MB.",
              category='danger')

        # Tenta redirecionar para a página de origem ou para o perfil
        referrer = request.referrer
        if referrer and referrer.startswith(request.host_url):
            return redirect(referrer)
        return redirect(url_for('auth.profile'))

    @app.errorhandler(SecretsManagerError)
    def handle_secrets_manager_error(error):
        """Trata erros relacionados ao gerenciamento de chaves de criptografia.

        Args:
            error: Instância de SecretsManagerError.

        Returns:
            flask.Response: Renderiza página de erro com instruções.
        """
        from datetime import datetime
        from flask import render_template, request

        app.logger.error(f"Erro no gerenciamento de segredos: {error}")
        app.logger.error(f"  URL: {request.path}")
        app.logger.error(f"  Método: {request.method}")

        error_message = (
            "Erro de configuração: Sistema de criptografia não inicializado corretamente. "
            "Execute 'flask secrets generate' para criar as chaves de criptografia."
        )

        return render_template(
            'error.jinja2',
            error_code=500,
            error_title="Erro de Configuração",
            error_message=error_message,
            error_details=str(error),
            show_details=app.debug,
            timestamp=datetime.now()
        ), 500

    @app.errorhandler(500)
    def internal_server_error(error):
        """Trata erros internos do servidor (500).

        Args:
            error: Erro capturado pelo Flask.

        Returns:
            flask.Response: Renderiza página de erro genérica.
        """
        from datetime import datetime
        from flask import render_template, request

        app.logger.error(f"Erro interno do servidor: {error}", exc_info=True)
        app.logger.error(f"  URL: {request.path}")
        app.logger.error(f"  Método: {request.method}")

        error_message = (
            "Ocorreu um erro interno no servidor. "
            "Nossa equipe foi notificada e está trabalhando para resolver o problema."
        )

        return render_template(
            'error.jinja2',
            error_code=500,
            error_title="Erro Interno do Servidor",
            error_message=error_message,
            error_details=str(error) if app.debug else None,
            show_details=app.debug,
            timestamp=datetime.now()
        ), 500

    @app.errorhandler(404)
    def not_found_error(error):
        """Trata erros de página não encontrada (404).

        Args:
            error: Erro capturado pelo Flask.

        Returns:
            flask.Response: Renderiza página de erro 404.
        """
        from datetime import datetime
        from flask import render_template, request

        if request.path in ['/favicon.ico', '/robots.txt']:
            return '', 204  # No Content para evitar logs desnecessários

        app.logger.warning(f"Página não encontrada: {request.path}")
        app.logger.warning(f"  Método: {request.method}")
        app.logger.warning(f"  Referrer: {request.referrer}")

        error_message = (
            "A página que você está procurando não foi encontrada. "
            "Ela pode ter sido removida, renomeada ou estar temporariamente indisponível."
        )

        return render_template(
            'error.jinja2',
            error_code=404,
            error_title="Página Não Encontrada",
            error_message=error_message,
            error_details=None,
            show_details=False,
            timestamp=datetime.now()
        ), 404

    app.logger.info("Aplicação configurada com sucesso")
    return app
