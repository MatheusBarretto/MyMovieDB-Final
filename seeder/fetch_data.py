import argparse
import json
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Configurações da API do TMDB
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # w500 = largura 500px (boa qualidade)
TMDB_IMAGE_BASE_LARGE = "https://image.tmdb.org/t/p/original"  # Para pôsteres em alta qualidade

logger = logging.getLogger(__name__)


class TMDBDataFetcher:
    """Classe para buscar dados sobre um filme na API do TMDB"""

    def __init__(self, api_key: str):
        """
        Inicializa o fetcher com a chave da API

        Args:
            api_key: Chave da API do TMDB
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {"api_key": self.api_key}

    def fetch_movie(self,
                    movie_id: int,
                    language: str = 'en-US'):
        """
        Busca os detalhes de um filme pelo ID

        Args:
            movie_id: ID do filme no TMDB
            language: Código do idioma para os detalhes do filme (padrão: 'en-US')
        """

        file_path = Path(f"movies/{movie_id}.movie.json")
        if file_path.exists():
            logger.warning(f"Dados do filme {movie_id} já existem localmente.")
            return False

        url = f"{TMDB_API_BASE}/movie/{movie_id}?language={language}"
        response = self.session.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            json_data = response.json()
            with file_path.open("w", encoding="utf-8") as f:
                logger.info(f"Salvando dados do filme {movie_id} em {file_path}")
                json.dump(json_data, f, ensure_ascii=False, indent=2)

        return True

    def fetch_credits(self,
                      movie_id: int,
                      fetch_person: bool = True,
                      language: str = 'en-US',
                      max_people: int = 0,
                      fetch_main_roles: bool = False):
        """
        Busca os créditos de um filme pelo ID

        Args:
            movie_id: ID do filme no TMDB
            fetch_person: Se True, busca os detalhes de cada pessoa no elenco e equipe
            language: Código do idioma para os detalhes do filme (padrão: 'en-US')
            max_people: Número máximo de membros de `cast` e `crew` a buscar (0 = sem limite)
            fetch_main_roles: Garante que as funções técnicas básicas serão importadas
        
        Note:
            As funções técnicas básicas são: "Director", "Editor", "Executive Producer",
            "Novel", "Producer", "Screenplay", "Special Effects", "Writer"
        """
        file_path = Path(f"movies/{movie_id}.movie.credits.json")
        if file_path.exists():
            logger.warning(f"Dados de créditos do filme {movie_id} já existem localmente.")
            return False

        url = f"{TMDB_API_BASE}/movie/{movie_id}/credits?language={language}"
        response = self.session.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            json_data = response.json()
            with file_path.open("w", encoding="utf-8") as f:
                logger.info(f"Salvando dados de créditos do filme {movie_id} em {file_path}")
                json.dump(json_data, f, ensure_ascii=False, indent=2)
                if not fetch_person:
                    return True
        else:
            return False

        # Definir funções técnicas principais que devem ser sempre buscadas
        main_roles = {
            "Director", "Editor", "Executive Producer", "Novel", 
            "Producer", "Screenplay", "Special Effects", "Writer"
        }
        
        # Processar elenco (cast)
        cast = json_data.get("cast", [])
        if max_people and max_people > 0:
            cast = cast[:max_people]
        for member in cast:
            person_id = member.get("id")
            if person_id:
                self.fetch_person(person_id, language)
                # Rate limiting: aguardar 0.25s entre requisições
                time.sleep(0.25)
        
        # Processar equipe técnica (crew)
        crew = json_data.get("crew", [])
        fetched_person_ids = set()
        
        # Se fetch_main_roles estiver ativo, primeiro buscar pessoas com funções principais
        if fetch_main_roles:
            for member in crew:
                job = member.get("job", "")
                person_id = member.get("id")
                if job in main_roles and person_id:
                    self.fetch_person(person_id, language)
                    fetched_person_ids.add(person_id)
                    # Rate limiting: aguardar 0.25s entre requisições
                    time.sleep(0.25)
        
        # Processar o restante da equipe técnica respeitando max_people
        crew_to_process = crew
        if max_people and max_people > 0:
            crew_to_process = crew[:max_people]
            
        for member in crew_to_process:
            person_id = member.get("id")
            # Só buscar se ainda não foi buscado (evitar duplicatas)
            if person_id and person_id not in fetched_person_ids:
                self.fetch_person(person_id, language)
                # Rate limiting: aguardar 0.25s entre requisições
                time.sleep(0.25)
        return True

    def fetch_person(self, person_id: int, language: str = 'en-US'):
        """
        Busca os detalhes de uma pessoa pelo ID

        Args:
            person_id: ID da pessoa no TMDB
            language: Código do idioma para os detalhes da pessoa (padrão: 'en-US')
        """
        file_path = Path(f"person/{person_id}.person.json")
        if file_path.exists():
            logger.warning(f"Dados da pessoa {person_id} ja exitem localmente.")
            return

        url = f"{TMDB_API_BASE}/person/{person_id}?language={language}"
        response = self.session.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            json_data = response.json()
            with file_path.open("w", encoding="utf-8") as f:
                logger.info(f"Salvando dados da pessoa {person_id} em {file_path}")
                json.dump(json_data, f, ensure_ascii=False, indent=2)


def read_movie_ids_from_file(file_path: Path) -> list[int]:
    """Lê IDs de filmes de um arquivo de texto.

    Args:
        file_path: Caminho para o arquivo de texto contendo IDs de filmes.

    Returns:
        Lista de IDs de filmes.
    """
    if not file_path.exists():
        logger.warning(f"Arquivo {file_path} não encontrado")
        exit(2)

    movie_ids = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            try:
                movie_ids.append(int(line))
            except ValueError:
                logger.warning(f"Ignorando linha inválida em `{file_path}`: {line}")
    return movie_ids


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)


    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    if not TMDB_API_KEY:
        raise ValueError("A variável de ambiente TMDB_API_KEY não está definida.")

    parser = argparse.ArgumentParser(description="Buscar dados do TMDB e salvar localmente.")
    parser.add_argument("--fetch-persons", action="store_true",
                        help="Buscar detalhes das pessoas do elenco/crew.")
    parser.add_argument("--fetch-main-roles", action="store_true",
                        help="Obtém, obrigatoriamente, as funções técnias básicas do filme (diretor, editor, produtor...)")
    parser.add_argument("--max-people", type=int, default=0,
                        help="Número máximo de pessoas a buscar (apenas válido se "
                             "--fetch-persons). 0 = sem limite.")
    parser.add_argument("--language", default="pt-BR",
                        help="Idioma para as requisições (ex: pt-BR, en-US).")
    parser.add_argument("--movies-file", default="movies_id.txt",
                        help="Arquivo com IDs de filmes, um por linha.")
    args = parser.parse_args()

    if args.max_people and not args.fetch_persons:
        parser.error("--max-people só pode ser usado quando --fetch-persons for especificado.")

    fetcher = TMDBDataFetcher(api_key=TMDB_API_KEY)

    # IDs de filmes para buscar
    movie_ids = read_movie_ids_from_file(Path(args.movies_file))
    path_obj = Path("movies")
    path_obj.mkdir(parents=True, exist_ok=True)
    path_obj = Path("person")
    path_obj.mkdir(parents=True, exist_ok=True)

    for movie_id in movie_ids:
        try:
            success = fetcher.fetch_movie(movie_id, args.language)
            if success:
                logger.info(f"Dados do filme {movie_id} buscados e salvos com sucesso.")
            else:
                logger.info(f"Dados do filme {movie_id} já existem localmente.")
        except Exception as e:
            logger.error(f"Erro ao buscar dados do filme {movie_id}: {e}")
        time.sleep(0.5)  # Rate limiting: aguardar 0.5s entre requisições de filmes
        try:
            success = fetcher.fetch_credits(movie_id,
                                            args.fetch_persons,
                                            args.language,
                                            args.max_people or 0,
                                            args.fetch_main_roles)
            if success:
                logger.info(f"Créditos do filme {movie_id} buscados e salvos com sucesso.")
            else:
                logger.info(f"Créditos do filme {movie_id} já existem localmente.")
        except Exception as e:
            logger.error(f"Erro ao buscar dados do filme {movie_id}: {e}")
        time.sleep(1)  # Rate limiting: aguardar 1s entre iterações
