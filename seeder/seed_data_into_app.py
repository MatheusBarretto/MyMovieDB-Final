import base64
import json
import os

import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from flask import current_app

# Adicionar o diretório raiz do projeto ao Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.infra.modulos import db
from app.models.filme import Filme, Genero, FuncaoTecnica
from app.models.pessoa import Pessoa, Ator
from app.models.juncoes import EquipeTecnica, Atuacao

# Configurações da API do TMDB
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # w500 = largura 500px (boa qualidade)
TMDB_IMAGE_BASE_LARGE = "https://image.tmdb.org/t/p/original"  # Para pôsteres em alta qualidade


class TMDBImageFetcher:
    """Classe para buscar imagens do TMDB e converter para base64"""

    def __init__(self, api_key: str):
        """
        Inicializa o fetcher com a chave da API

        Args:
            api_key: Chave da API do TMDB
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {"api_key": self.api_key}

    @staticmethod
    def download_and_cache_image_as_base64(image_path: str, use_large: bool = False) -> Optional[
        tuple[str, str]]:
        """
        Baixa uma imagem do TMDB e converte para base64, com cache local

        Args:
            image_path: Caminho da imagem retornado pela API (ex: "/abc123.jpg")
            use_large: Se True, usa imagem em alta qualidade

        Returns:
            Tupla (mime_type, base64_string) da imagem ou None se erro
        """
        if not image_path:
            return None

        try:
            # Criar diretório de cache se não existir
            cache_dir = Path("seeder/images")
            cache_dir.mkdir(exist_ok=True)

            # Nome do arquivo local (remover a barra inicial do image_path)
            filename = image_path.lstrip('/')
            local_file = cache_dir / filename

            # Verificar se já existe localmente
            if local_file.exists():
                print(f"  📁 Usando imagem em cache: {filename}")
                with local_file.open('rb') as f:
                    image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')

                mime_type = "image/jpeg"
                if image_path.lower().endswith('.png'):
                    mime_type = "image/png"

                return mime_type, image_base64

            # Baixar da internet se não existir localmente
            base_url = TMDB_IMAGE_BASE_LARGE if use_large else TMDB_IMAGE_BASE
            image_url = f"{base_url}{image_path}"

            print(f"  🌐 Baixando imagem: {filename}")
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Salvar localmente
            with local_file.open('wb') as f:
                f.write(response.content)

            # Converter para base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')

            mime_type = "image/jpeg"
            if image_path.lower().endswith('.png'):
                mime_type = "image/png"

            return mime_type, image_base64
        except Exception as e:
            print(f"  ❌ Erro ao processar imagem {image_path}: {e}")
            return None


def criar_generos(source_file: Path) -> Optional[dict[str, Genero]]:
    """Criar gêneros a partir de um arquivo de texto.

    Se existir um arquivo generos_completo.json no mesmo diretório,
    usa os dados completos incluindo descrições.
    """
    if not source_file.exists():
        current_app.logger.warning(f"Arquivo de generos não encontrado: {source_file}")

    generos = dict()
    print("📝 Criando gêneros...")

    # Verificar se existe arquivo completo com descrições
    json_file = source_file.parent / "generos_completo.json"
    generos_completos = {}
    if json_file.exists():
        print(f"  📄 Usando dados completos de {json_file.name}")
        with json_file.open("r", encoding="utf-8") as f:
            generos_list = json.load(f)
            generos_completos = {g["nome"]: g for g in generos_list}

    with source_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            genero = Genero.get_first_or_none_by("nome", line)
            if not genero:
                # Usar dados completos se disponível
                if line in generos_completos:
                    genero_data = generos_completos[line]
                    genero = Genero(
                            nome=line,
                            descricao=genero_data.get("descricao"),
                            ativo=genero_data.get("ativo", True)
                    )
                else:
                    genero = Genero(nome=line, ativo=True)
                db.session.add(genero)
                print(f"  ✓ {line}")
            else:
                print(f"  ⊙ {line} (já existe)")
            generos[line] = genero

        db.session.commit()
        return generos


def criar_funcoes_tecnicas(source_file: Path) -> Optional[dict[str, FuncaoTecnica]]:
    """Criar funções técnicas a partir de um arquivo de texto.

    Se existir um arquivo funcoes_tecnicas_completo.json no mesmo diretório,
    usa os dados completos incluindo descrições.
    """
    if not source_file.exists():
        current_app.logger.warning(f"Arquivo de funções técnicas não encontrado: {source_file}")

    funcoes = dict()
    print("\n📝 Criando funções técnicas...")

    # Verificar se existe arquivo completo com descrições
    json_file = source_file.parent / "funcoes_tecnicas_completo.json"
    funcoes_completas = {}
    if json_file.exists():
        print(f"  📄 Usando dados completos de {json_file.name}")
        with json_file.open("r", encoding="utf-8") as f:
            funcoes_list = json.load(f)
            funcoes_completas = {f["nome"]: f for f in funcoes_list}

    with source_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            funcao = FuncaoTecnica.get_first_or_none_by("nome", line)
            if not funcao:
                # Usar dados completos se disponível
                if line in funcoes_completas:
                    funcao_data = funcoes_completas[line]
                    funcao = FuncaoTecnica(
                            nome=line,
                            descricao=funcao_data.get("descricao"),
                            ativo=funcao_data.get("ativo", True)
                    )
                else:
                    funcao = FuncaoTecnica(nome=line, ativo=True)
                db.session.add(funcao)
                print(f"  ✓ {line}")
            else:
                print(f"  ⊙ {line} (já existe)")
            funcoes[line] = funcao

        db.session.commit()
        return funcoes


def criar_pessoas(source_path: Path, fetch_image: bool = False) -> Optional[dict[str, Pessoa]]:
    """Importar todas as pessoas de um diretório contendo arquivos JSON."""
    # Define the directory containing your JSON files
    json_directory = Path(source_path)

    # Check if the directory exists to avoid errors
    if not json_directory.is_dir():
        print(f"Error: Directory not found at '{json_directory}'")
        return

    # Get the list of JSON files (using rglob to be thorough)
    files_to_process = list(json_directory.rglob('*person.processed.json'))

    if not files_to_process:
        print(f"No JSON files found in '{json_directory}'.")
        return

    pessoas = dict()
    print("\n📝 Criando pessoas...")

    for file_path in files_to_process:
        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            # Verificar se pessoa já existe
            pessoa = Pessoa.get_first_or_none_by("nome", data["nome"])

            if not pessoa:
                nascimento = datetime.strptime(data["data_nascimento"], "%Y-%m-%d") \
                    if data["data_nascimento"] else None

                morte = datetime.strptime(data["data_falecimento"], "%Y-%m-%d") \
                    if data["data_falecimento"] else None

                # Criar pessoa primeiro (sempre)
                pessoa = Pessoa(
                        nome=data["nome"],
                        data_nascimento=nascimento,
                        data_falecimento=morte,
                        local_nascimento=data["local_nascimento"],
                        biografia=data["biografia"]
                )
                # Verificar se tem foto em base64 (de dump do banco)
                if data.get("foto_base64") and data.get("foto_mime"):
                    pessoa.foto_mime = data["foto_mime"]
                    pessoa.foto_base64 = data["foto_base64"]
                    pessoa.com_foto = True
                    print(f"    ✓ Foto carregada do dump para {data['nome']}")
                # Caso contrário, baixar foto se necessário
                elif fetch_image and data.get("foto_path"):
                    mime_type, image_base64 = TMDBImageFetcher. \
                        download_and_cache_image_as_base64(data.get("foto_path"))
                    if mime_type and image_base64:
                        pessoa.foto_mime = mime_type
                        pessoa.foto_base64 = image_base64
                        pessoa.com_foto = True
                        current_app.logger.info(f"  ✓ Foto baixada para {data['nome']}")
                    else:
                        current_app.logger.warning(f"  ❌ Falha ao baixar foto para {data['nome']}")
                db.session.add(pessoa)
                print(f"  ✓ {data['nome']}")
            else:
                print(f"  ⊙ {data['nome']} (já existe)")
            pessoas[data["nome"]] = pessoa

        except json.JSONDecodeError:
            print(f"  Error: Could not decode JSON from {file_path.name}.")
        except Exception as e:
            print(f"  An unexpected error occurred: {e}")
    db.session.commit()

    return pessoas


def criar_filmes(source_path: Path,
                 generos: dict[str, Genero],
                 pessoas: dict[str, Pessoa],
                 funcoes: dict[str, FuncaoTecnica],
                 fetch_image: bool = False) -> Optional[dict[int, Filme]]:
    """Importar todos os filmes de um diretório contendo arquivos JSON."""
    # Define the directory containing your JSON files
    json_directory = Path(source_path)

    # Check if the directory exists to avoid errors
    if not json_directory.is_dir():
        print(f"Error: Directory not found at '{json_directory}'")
        return

    # Get the list of JSON files (using rglob to be thorough)
    files_to_process = list(json_directory.rglob('*movie.processed.json'))

    if not files_to_process:
        print(f"No JSON files found in '{json_directory}'.")
        return

    filmes = dict()
    print("\n📝 Criando filmes...")

    for file_path in files_to_process:
        try:
            with file_path.open('r', encoding='utf-8') as f:
                d = json.load(f)
            # Verificar se o filme já existe
            filme = Filme.get_all_by({"titulo_original": d["titulo_original"],
                                      "ano_lancamento" : d["ano_lancamento"]},
                                     order_by="id").first()
            if not filme:
                # Criar filme
                filme = Filme(
                        titulo_original=d["titulo_original"],
                        titulo_portugues=d["titulo_portugues"],
                        ano_lancamento=int(d["ano_lancamento"]),
                        lancado=d["lancado"],
                        duracao_minutos=int(d["duracao_minutos"]),
                        sinopse=d["sinopse"],
                        orcamento_milhares=d["orcamento_milhares"],
                        faturamento_lancamento_milhares=d["faturamento_lancamento_milhares"]
                )
                # Adicionar filme à sessão e fazer flush para obter ID
                db.session.add(filme)
                db.session.flush()  # Garantir que o filme tenha um ID

                for g in d["generos_do_filme"]:
                    filme.generos.append(generos[g])

                for eq in d["equipe_tecnica"]:
                    if eq["nome"] not in pessoas:
                        print(f"  ⚠️ Pessoa '{eq['nome']}' não encontrada, criando pessoa básica")
                        # Criar pessoa básica se não existir
                        pessoa_nova = Pessoa(nome=eq["nome"])
                        db.session.add(pessoa_nova)
                        db.session.flush()
                        pessoas[eq["nome"]] = pessoa_nova
                    pessoa = pessoas[eq["nome"]]
                    funcao = funcoes[eq["funcao"]]
                    equipe_tecnica = EquipeTecnica(
                            filme=filme,
                            pessoa=pessoa,
                            funcao_tecnica=funcao
                    )
                    db.session.add(equipe_tecnica)

                for at in d["elenco"]:
                    if at["nome"] not in pessoas:
                        print(f"  ⚠️ Pessoa '{at['nome']}' não encontrada, criando pessoa básica")
                        # Criar pessoa básica se não existir
                        pessoa_nova = Pessoa(nome=at["nome"])
                        db.session.add(pessoa_nova)
                        db.session.flush()
                        pessoas[at["nome"]] = pessoa_nova

                    if pessoas[at["nome"]].ator is None:
                        # Garantir que a pessoa é um ator
                        ator = Ator(pessoa=pessoas[at["nome"]])
                        db.session.add(ator)
                        db.session.flush()  # Garantir que o ID seja gerado
                        pessoas[at["nome"]].ator = ator
                    ator = pessoas[at["nome"]].ator
                    atuacao = Atuacao(
                            filme=filme,
                            ator=ator,
                            personagem=at["personagem"],
                            creditado=at["creditado"]
                    )
                    db.session.add(atuacao)

                # Verificar se tem poster em base64 (de dump do banco)
                if d.get("poster_base64") and d.get("poster_mime"):
                    filme.poster_mime = d["poster_mime"]
                    filme.poster_base64 = d["poster_base64"]
                    filme.com_poster = True
                    print(f"    ✓ Poster carregado do dump para {d['titulo_original']}")
                # Caso contrário, baixar poster se necessário
                elif fetch_image and d.get("poster_path"):
                    mime_type, image_base64 = TMDBImageFetcher. \
                        download_and_cache_image_as_base64(d.get("poster_path"))
                    if mime_type and image_base64:
                        filme.poster_mime = mime_type
                        filme.poster_base64 = image_base64
                        filme.com_poster = True
                        current_app.logger.info(f"  ✓ Poster baixado para {d['titulo_original']}")
                    else:
                        current_app.logger.warning(
                            f"  ❌ Falha ao baixar poster para {d['titulo_original']}")
                print(f"  ✓ {d["titulo_original"]}, {d["ano_lancamento"]}")
            else:
                print(f"  ⊙ {d["titulo_original"]}, {d["ano_lancamento"]} (já existe)")
            filmes[f'{d["titulo_original"]}, {d["ano_lancamento"]}'] = filme

        except json.JSONDecodeError:
            print(f"  Error: Could not decode JSON from {file_path.name}.")
        except Exception as e:
            print(f"  An unexpected error occurred: {e}")
        db.session.commit()

    return filmes


def main():
    """Função principal"""
    # Verificar chave da API
    from dotenv import load_dotenv

    # Carregar variáveis de ambiente do arquivo .env
    load_dotenv()
    api_key = os.getenv('TMDB_API_KEY')

    if not api_key:
        print("❌ ERRO: Chave da API do TMDB não encontrada!")
        print(
            "\nPara usar este script defina a variável de ambiente: "
            "$Env.TMDB_API_KEY=\"sua_chave\"")
        sys.exit(1)

    print("=" * 80)
    print("SEED DE DADOS - MYMOVIEDB")
    print("=" * 80)
    print()

    # Criar app e contexto
    app = create_app()

    with app.app_context():
        try:
            # Criar dados
            generos = criar_generos(Path("seeder/output/movies/generos.txt"))
            funcoes = criar_funcoes_tecnicas(Path("seeder/output/movies/funcoes_tecnicas.txt"))
            pessoas = criar_pessoas(Path("seeder/output/person"), fetch_image=True)
            filmes = criar_filmes(Path("seeder/output/movies"), generos, pessoas, funcoes,
                                  fetch_image=True)

            print("\n" + "=" * 80)
            print("✅ SEED CONCLUÍDO COM SUCESSO!")
            print("=" * 80)
            print(f"\nResumo:")
            print(f"  • {len(generos)} gêneros")
            print(f"  • {len(funcoes)} funções técnicas")
            print(f"  • {len(pessoas)} pessoas")
            print(f"  • {len(filmes)} filmes")
            print()

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
