import hashlib
import io
import re
from base64 import b64decode, b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from flask import current_app, Response
from PIL import Image, ImageDraw, ImageFont


class ImageProcessingError(Exception):
    """Exceção customizada para erros de processamento de imagem.
    """
    pass


@dataclass
class ImageProcessingResult:
    imagem_base64: str  # Imagem original em base64
    avatar_base64: str  # Avatar redimensionado em base64
    mime_type: str  # Tipo MIME da imagem
    formato_original: str  # Formato original (JPEG, PNG, etc)
    dimensoes_originais: Tuple[int, int]  # (largura, altura) original
    dimensoes_avatar: Tuple[int, int]  # (largura, altura) do avatar
    tamanho_arquivo: int  # Tamanho do arquivo original em bytes


class ImageProcessingService:
    """Serviço responsável por processamento e manipulação de imagens.
    """
    # Formatos suportados
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP'}

    # Extensões permitidas (para validação de upload)
    ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp']

    # Tamanhos padrão
    DEFAULT_AVATAR_SIZE = 64
    DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_MAX_DIMENSIONS = (2048, 2048)

    # Qualidade de compressão
    JPEG_QUALITY = 85
    PNG_OPTIMIZE = True

    @staticmethod
    def processar_upload_imagem(arquivo_upload,
                                avatar_size: Optional[int] = None,
                                max_file_size: Optional[int] = None,
                                max_dimensions: Optional[
                                  Tuple[int, int]] = None,
                                crop_aspect_ratio: bool = False) -> ImageProcessingResult:
        """Processa um arquivo de imagem enviado via upload, gerando imagem original e avatar.

        Args:
            arquivo_upload (FileStorage): Objeto de arquivo (FileStorage do Flask).
            avatar_size (Optional[int]): Tamanho do avatar em pixels. Se None, usa configuração da app ou 32.
            max_file_size (Optional[int]): Tamanho máximo do arquivo em bytes. Se None, usa configuração da app ou 5MiB.
            max_dimensions (Optional[Tuple[int, int]]): Dimensões máximas permitidas (largura, altura). Se None, usa configuração da app ou (2048, 2048).
            crop_aspect_ratio (bool): Se True, aplica crop para aspect ratio 2:3. Default: False

        Returns:
            ImageProcessingResult: Resultado do processamento da imagem.

        Raises:
            ImageProcessingError: Em caso de erro no processamento.
            ValueError: Para arquivos inválidos ou muito grandes.
        """
        if arquivo_upload is None:
            raise ValueError("Nenhum arquivo fornecido")

        # Configurações com fallbacks
        avatar_size = avatar_size or \
                      current_app.config.get('AVATAR_SIZE',
                                             ImageProcessingService.DEFAULT_AVATAR_SIZE)
        max_file_size = max_file_size or \
                        current_app.config.get('MAX_IMAGE_SIZE',
                                               ImageProcessingService.DEFAULT_MAX_FILE_SIZE)
        max_dimensions = max_dimensions or \
                         current_app.config.get('MAX_IMAGE_DIMENSIONS',
                                                ImageProcessingService.DEFAULT_MAX_DIMENSIONS)

        try:
            # Lê os dados do arquivo
            arquivo_upload.seek(0)  # Garante que está no início
            imagem_data = arquivo_upload.read()

            if not imagem_data:
                raise ValueError("Arquivo de imagem vazio")

            # Validação de tamanho
            if len(imagem_data) > max_file_size:
                raise ValueError(
                        f"Arquivo muito grande. Máximo permitido: "
                        f"{max_file_size / (1024 * 1024):.1f}MB")

            # Processa a imagem
            return ImageProcessingService._processar_imagem_bytes(imagem_data,
                                                                  arquivo_upload.mimetype,
                                                                  avatar_size,
                                                                  max_dimensions,
                                                                  crop_aspect_ratio)

        except (AttributeError, OSError) as e:
            raise ImageProcessingError(f"Erro ao processar arquivo de imagem: {str(e)}") from e

    @staticmethod
    def processar_pessoa_foto(arquivo_upload,
                             avatar_size: Optional[int] = None,
                             max_file_size: Optional[int] = None,
                             max_dimensions: Optional[Tuple[int, int]] = None,
                             crop_aspect_ratio: bool = True) -> ImageProcessingResult:
        """Processa foto de pessoa com crop automático para aspect ratio 2:3.

        Atalho para processar_upload_imagem com crop_aspect_ratio=True por padrão.
        Aplica crop automático para o aspect ratio 2:3 (padrão para fotos de pessoas)
        antes do processamento.

        Args:
            arquivo_upload (FileStorage): Objeto de arquivo (FileStorage do Flask).
            avatar_size (Optional[int]): Tamanho do avatar em pixels. Se None, usa configuração da app ou 64.
            max_file_size (Optional[int]): Tamanho máximo do arquivo em bytes. Se None, usa configuração da app ou 5MiB.
            max_dimensions (Optional[Tuple[int, int]]): Dimensões máximas permitidas (largura, altura). Se None, usa configuração da app ou (2048, 2048).
            crop_aspect_ratio (bool): Se True, aplica crop para aspect ratio 2:3. Default: True

        Returns:
            ImageProcessingResult: Resultado do processamento da imagem com crop aplicado.

        Raises:
            ImageProcessingError: Em caso de erro no processamento.
            ValueError: Para arquivos inválidos ou muito grandes.

        Examples:
            >>> # Processar foto de pessoa com crop automático
            >>> resultado = ImageProcessingService.processar_pessoa_foto(arquivo)

            >>> # Processar sem crop (comportamento original)
            >>> resultado = ImageProcessingService.processar_pessoa_foto(arquivo, crop_aspect_ratio=False)
        """
        return ImageProcessingService.processar_upload_imagem(
            arquivo_upload,
            avatar_size,
            max_file_size,
            max_dimensions,
            crop_aspect_ratio
        )

    @staticmethod
    def processar_base64(base64_string: str,
                         avatar_size: Optional[int] = None,
                         max_file_size: Optional[int] = None,
                         max_dimensions: Optional[Tuple[int, int]] = None) -> ImageProcessingResult:
        """Processa uma imagem em formato base64 (data URI ou base64 puro).

        Args:
            base64_string (str): String base64 da imagem (pode incluir data URI prefix).
            avatar_size (Optional[int]): Tamanho do avatar em pixels.
            max_file_size (Optional[int]): Tamanho máximo do arquivo em bytes.
            max_dimensions (Optional[Tuple[int, int]]): Dimensões máximas permitidas.

        Returns:
            ImageProcessingResult: Resultado do processamento da imagem.

        Raises:
            ImageProcessingError: Em caso de erro no processamento.
            ValueError: Para dados inválidos.
        """
        if not base64_string:
            raise ValueError("String base64 vazia")

        # Configurações com fallbacks
        avatar_size = avatar_size or current_app.config.get('AVATAR_SIZE',
                                                            ImageProcessingService.DEFAULT_AVATAR_SIZE)
        max_file_size = max_file_size or current_app.config.get('MAX_IMAGE_SIZE',
                                                                ImageProcessingService.DEFAULT_MAX_FILE_SIZE)
        max_dimensions = max_dimensions or current_app.config.get('MAX_IMAGE_DIMENSIONS',
                                                                  ImageProcessingService.DEFAULT_MAX_DIMENSIONS)

        try:
            # Remove o prefixo data URI se presente (ex: "data:image/jpeg;base64,")
            mime_type = 'image/jpeg'  # default
            if base64_string.startswith('data:'):
                match = re.match(r'data:(image/[a-z]+);base64,(.+)', base64_string)
                if match:
                    mime_type = match.group(1)
                    base64_string = match.group(2)
                else:
                    raise ValueError("Formato de data URI inválido")

            # Decodifica base64
            imagem_data = b64decode(base64_string)

            if not imagem_data:
                raise ValueError("Dados de imagem vazios após decodificação")

            # Validação de tamanho
            if len(imagem_data) > max_file_size:
                raise ValueError(
                        f"Arquivo muito grande. Máximo permitido: "
                        f"{max_file_size / (1024 * 1024):.1f}MB")

            # Processa a imagem
            return ImageProcessingService._processar_imagem_bytes(imagem_data, mime_type,
                                                                  avatar_size, max_dimensions)

        except (ValueError, TypeError) as e:
            if isinstance(e, ValueError):
                raise
            raise ImageProcessingError(f"Erro ao decodificar base64: {str(e)}") from e

    @staticmethod
    def _processar_imagem_bytes(imagem_data: bytes,
                                mime_type: str,
                                avatar_size: int,
                                max_dimensions: Tuple[int, int],
                                crop_aspect_ratio: bool = False,
                                aspect_width: int = 2,
                                aspect_height: int = 3) -> ImageProcessingResult:
        """Processa dados de imagem em bytes com opção de crop.

        Args:
            imagem_data (bytes): Dados da imagem em bytes.
            mime_type (str): Tipo MIME fornecido pelo upload.
            avatar_size (int): Tamanho do avatar.
            max_dimensions (Tuple[int, int]): Dimensões máximas.
            crop_aspect_ratio (bool): Se True, aplica crop para aspect ratio 2:3. Default: False

        Returns:
            ImageProcessingResult: Resultado do processamento.
        """
        try:
            with Image.open(io.BytesIO(imagem_data)) as imagem:
                # Validações básicas
                if not hasattr(imagem, 'format') or imagem.format is None:
                    raise ImageProcessingError("Formato de imagem não reconhecido")

                if imagem.format not in ImageProcessingService.SUPPORTED_FORMATS:
                    raise ImageProcessingError(f"Formato {imagem.format} não suportado. "
                                               f"Formatos aceitos: "
                                               f"{', '.join(ImageProcessingService.SUPPORTED_FORMATS)}")

                largura_orig, altura_orig = imagem.size

                # Validação de dimensões
                if largura_orig > max_dimensions[0] or altura_orig > max_dimensions[1]:
                    raise ValueError(
                            f"Imagem muito grande. Máximo: {max_dimensions[0]}x{max_dimensions[
                                1]} pixels")

                # Preserva o formato original antes do crop
                formato_original = imagem.format

                # Aplica crop se solicitado
                if crop_aspect_ratio:
                    imagem = ImageProcessingService.crop_to_aspect_ratio(imagem,
                                                                         aspect_width,
                                                                         aspect_height)
                    # Restaura o formato após o crop
                    imagem.format = formato_original

                # Salva foto processada em buffer
                buffer_imagem = io.BytesIO()
                imagem.save(buffer_imagem, format=formato_original, optimize=True)
                foto_bytes = buffer_imagem.getvalue()

                # Gera avatar
                avatar_data, avatar_dims = ImageProcessingService._gerar_avatar(imagem, avatar_size)

                return ImageProcessingResult(
                        imagem_base64=b64encode(foto_bytes).decode('utf-8'),
                        avatar_base64=b64encode(avatar_data).decode('utf-8'),
                        mime_type=mime_type,
                        formato_original=imagem.format,
                        dimensoes_originais=(largura_orig, altura_orig),
                        dimensoes_avatar=avatar_dims,
                        tamanho_arquivo=len(imagem_data))

        except Exception as e:
            if isinstance(e, (ImageProcessingError, ValueError)):
                raise
            raise ImageProcessingError(f"Erro no processamento da imagem: {str(e)}") from e

    @staticmethod
    def _gerar_avatar(imagem: Image.Image,
                      avatar_size: int = None) -> Tuple[bytes, Tuple[int, int]]:
        """Gera avatar redimensionado a partir da imagem.

        Redimensiona a imagem proporcionalmente mantendo o aspect ratio original,
        de forma que nenhuma dimensão exceda avatar_size. Se a imagem já for menor
        que o tamanho desejado, não há redimensionamento (evita upscaling).

        Args:
            imagem (PIL.Image.Image): Objeto PIL Image.
            avatar_size (int): Tamanho máximo desejado do avatar (largura ou altura).

        Returns:
            typing.Tuple[bytes, typing.Tuple[int, int]]: Tupla contendo (dados_avatar, dimensoes_finais).

        Note:
            Utiliza Image.Resampling.LANCZOS para alta qualidade no redimensionamento.
        """
        largura, altura = imagem.size
        formato_original = imagem.format
        avatar_size = avatar_size or \
                      current_app.config.get('AVATAR_SIZE',
                                             ImageProcessingService.DEFAULT_AVATAR_SIZE)

        imagem_avatar = imagem.copy()
        # Otimização: pula redimensionamento se já está no tamanho adequado
        if max(largura, altura) > avatar_size:
            # Calcula novo tamanho mantendo proporção
            fator_escala = min(avatar_size / largura, avatar_size / altura)
            novo_tamanho = (
                int(largura * fator_escala),
                int(altura * fator_escala)
            )
            imagem_avatar = imagem.copy()
            imagem_avatar.thumbnail(novo_tamanho, Image.Resampling.LANCZOS)
        buffer_avatar = io.BytesIO()
        imagem_avatar.save(buffer_avatar, format=formato_original, optimize=True)
        return buffer_avatar.getvalue(), imagem_avatar.size

    @staticmethod
    def crop_to_aspect_ratio(imagem: Image.Image, 
                           aspect_width: int = 2, 
                           aspect_height: int = 3) -> Image.Image:
        """Corta uma imagem para um aspect ratio específico usando crop centralizado.

        Corta a imagem para o aspect ratio desejado, mantendo a maior área possível
        da imagem original. O crop é feito de forma centralizada.

        Args:
            imagem (PIL.Image.Image): Objeto PIL Image a ser cortado.
            aspect_width (int): Largura do aspect ratio desejado. Default: 2
            aspect_height (int): Altura do aspect ratio desejado. Default: 3

        Returns:
            PIL.Image.Image: Nova imagem cortada com o aspect ratio especificado.

        Examples:
            >>> # Crop para 2:3 (padrão para pessoas)
            >>> cropped = ImageProcessingService.crop_to_aspect_ratio(image)
            
            >>> # Crop para 16:9
            >>> cropped = ImageProcessingService.crop_to_aspect_ratio(image, 16, 9)
        """
        largura_orig, altura_orig = imagem.size
        aspect_ratio_desejado = aspect_width / aspect_height
        aspect_ratio_atual = largura_orig / altura_orig

        if aspect_ratio_atual > aspect_ratio_desejado:
            # Imagem é mais larga que o desejado - corta nas laterais
            nova_largura = int(altura_orig * aspect_ratio_desejado)
            nova_altura = altura_orig
            left = (largura_orig - nova_largura) // 2
            top = 0
            right = left + nova_largura
            bottom = nova_altura
        else:
            # Imagem é mais alta que o desejado - corta em cima e embaixo
            nova_largura = largura_orig
            nova_altura = int(largura_orig / aspect_ratio_desejado)
            left = 0
            top = (altura_orig - nova_altura) // 2
            right = nova_largura
            bottom = top + nova_altura

        return imagem.crop((left, top, right, bottom))

    @staticmethod
    def generate_identicon_base64(data: str,
                                  grid_size: int = 8,
                                  image_size: int = 128,
                                  foreground: Optional[list] = None,
                                  background: Optional[str] = None) -> tuple[str, str]:
        """Gera um identicon em PNG com fundo transparente, codificado em base64, a partir de uma string.

        Args:
            data (str): String usada para gerar o identicon (ex: e-mail ou nome de usuário).
            grid_size (int, opcional): Número de blocos na grade (ex: 8 para 8x8). Padrão: 9. Máximo: 15.
            image_size (int, opcional): Tamanho da imagem em pixels (ex: 240 para 240x240). Padrão: 128. Máximo: 256.
            foreground (list, opcional): Lista de cores hexadecimais para o identicon. Padrão: uma paleta de cores.
            background (str, opcional): Cor de fundo em hexadecimal. Padrão: None (transparente).

        Returns:
            str: String base64 contendo o PNG do identicon.
            str: Tipo MIME da imagem ("image/png").

        Raises:
            ImageProcessingError: Em caso de erro na geração do identicon.
        """
        import pydenticon
        import re

        grid_size = max(1, min(grid_size, 15))
        image_size = max(16, min(image_size, 256))

        # Valores padrão se não forem fornecidos
        if foreground is None:
            foreground = [
                "#1abc9c", "#16a085", "#2ecc71", "#27ae60", "#3498db",
                "#2980b9", "#9b59b6", "#8e44ad", "#e67e22", "#d35400",
                "#e74c3c", "#c0392b", "#f1c40f", "#f39c12", "#34495e"
            ]

        if background is not None:
            if not isinstance(background, str) or not re.match(r'^#([A-Fa-f0-9]{6})$', background):
                background = None  # Reseta para None se inválido

        try:
            generator = pydenticon.Generator(
                    grid_size, grid_size,
                    digest=hashlib.sha512,
                    foreground=foreground,
                    background=background
            )
            identicon_png = generator.generate(data, image_size, image_size, output_format="png")
        except ValueError:
            raise ImageProcessingError("Erro ao gerar identicon com os parâmetros fornecidos.")
        except Exception as e:
            raise ImageProcessingError(f"Erro inesperado ao gerar identicon: {str(e)}") from e
        identicon_base64 = b64encode(identicon_png).decode("utf-8")

        return identicon_base64, "image/png"

    @staticmethod
    def gerar_placeholder(largura: int,
                          altura: int,
                          texto: Optional[str] = None,
                          tamanho_fonte: Optional[int] = None,
                          font_file: str = 'arial.ttf') -> bytes:
        """Gera uma imagem placeholder com texto centralizado.

        Args:
            largura (int): Largura da imagem em pixels
            altura (int): Altura da imagem em pixels
            texto (str, opcional): Texto a ser exibido (pode conter \n)
            tamanho_fonte (int, opcional): Tamanho da fonte. Use -1 para determinação automática
            font_file (str): Nome do arquivo de fonte em app/static/fonts/. Default: 'arial.ttf'

        Returns:
            bytes: Dados da imagem PNG em bytes

        Raises:
            ImageProcessingError: Se texto for fornecido mas tamanho_fonte não for.

        Examples:
            >>> # Placeholder com tamanho de fonte fixo e fonte padrão (Arial)
            >>> placeholder = ImageProcessingService.gerar_placeholder(300, 400, "Texto", 36)

            >>> # Placeholder com tamanho de fonte automático
            >>> placeholder = ImageProcessingService.gerar_placeholder(300, 400, "Texto Longo", -1)

            >>> # Placeholder com fonte customizada
            >>> placeholder = ImageProcessingService.gerar_placeholder(300, 400, "Texto", 36, 'roboto.ttf')
        """
        if texto and tamanho_fonte is None:
            raise ImageProcessingError(
                "Se texto for fornecido, tamanho_fonte deve ser especificado.")

        img = Image.new('RGB', (largura, altura), color='#6c757d')
        draw = ImageDraw.Draw(img)

        if texto and tamanho_fonte is not None:
            # Determina o caminho da fonte
            # Tenta usar a fonte especificada do diretório static/fonts, senão usa fonte padrão
            font_path = None
            if current_app:
                static_font_path = Path(current_app.static_folder) / 'fonts' / font_file
                if static_font_path.exists():
                    font_path = str(static_font_path)

            # Se tamanho_fonte é -1, calcula automaticamente
            if tamanho_fonte == -1:
                tamanho_fonte = ImageProcessingService._calculate_max_font_size(
                    texto,
                    (largura, altura),
                    font_path,
                    margin=20  # Margem de 20px ao redor do texto
                )

            # Carrega a fonte (TrueType ou padrão)
            try:
                fonte = ImageFont.truetype(font_path, tamanho_fonte)
            except (OSError, ValueError):
                fonte = ImageFont.load_default(size=tamanho_fonte)
            except Exception as e:
                raise ImageProcessingError(f"Erro ao carregar fonte: {str(e)}") from e

            bbox = draw.textbbox((0, 0), texto, font=fonte)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = ((largura - text_width) // 2, (altura - text_height) // 2)
            draw.text(position, texto, fill='white', align='center', font=fonte)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def servir_imagem(imagem_data: bytes,
                      mime_type: str = 'image/png') -> Response:
        """Cria uma Response com headers apropriados para servir imagem.

        Args:
            imagem_data (bytes): Dados da imagem
            mime_type (str): Tipo MIME da imagem. Default: 'image/png'

        Returns:
            Response: Response Flask com headers de cache
        """
        response = Response(imagem_data, mimetype=mime_type)
        response.headers['Content-Type'] = mime_type
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response


    @staticmethod
    def _calculate_max_font_size(text: str,
                                 image_size,
                                 font_path: Optional[str] = None,
                                 margin=0) -> int:
        """Calcula o maior tamanho de fonte que permite que o texto caiba dentro das dimensões da imagem.

        Args:
            text (str): Texto a ser renderizado.
            image_size (Tuple[int, int]): Dimensões da imagem (largura, altura).
            font_path (Optional[str]): Caminho para o arquivo de fonte TrueType (.ttf).
                                       Se None ou inválido, usa a fonte padrão do PIL.
            margin (int): Margem em pixels a ser deixada ao redor do texto. Default é 0.

        Returns:
            int: O maior tamanho de fonte que permite que o texto caiba na imagem.

        Note:
            Se a fonte TrueType não estiver disponível, faz fallback automático para ImageFont.load_default().
        """
        img_width, img_height = image_size
        max_width = img_width - 2 * margin
        max_height = img_height - 2 * margin

        draw = ImageDraw.Draw(Image.new("RGB", image_size))

        # Tenta determinar se deve usar TrueType ou fonte padrão
        use_truetype = False
        if font_path:
            try:
                # Testa se a fonte TrueType está disponível
                ImageFont.truetype(font_path, 10)
                use_truetype = True
            except (OSError, ValueError):
                use_truetype = False

        # Binary search para encontrar o melhor tamanho de fonte
        low, high = 1, 500  # Limites razoáveis de tamanho de fonte
        best_size = low

        while low <= high:
            mid = (low + high) // 2

            # Carrega a fonte apropriada
            if use_truetype:
                try:
                    font = ImageFont.truetype(font_path, mid)
                except (OSError, ValueError):
                    # Se falhar durante a busca binária, usa fonte padrão
                    font = ImageFont.load_default(size=mid)
            else:
                font = ImageFont.load_default(size=mid)

            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            if text_width <= max_width and text_height <= max_height:
                best_size = mid
                low = mid + 1  # Tenta uma fonte maior
            else:
                high = mid - 1  # Tenta uma fonte menor

        return best_size
