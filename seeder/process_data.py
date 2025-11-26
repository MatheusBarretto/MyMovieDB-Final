import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Processar dados do TMDB salvos localmente.")
    parser.add_argument("--movies-file", default="movies_id.txt",
                        help="Arquivo com IDs de filmes, um por linha.")
    args = parser.parse_args()

    # IDs de filmes para buscar
    movie_ids = read_movie_ids_from_file(Path(args.movies_file))

    movies_path = Path("movies")
    movies_path.mkdir(parents=True, exist_ok=True)
    person_path = Path("person")
    person_path.mkdir(parents=True, exist_ok=True)
    movie_output_path = Path("output/movies")
    movie_output_path.mkdir(parents=True, exist_ok=True)
    person_output_path = Path("output/person")
    person_output_path.mkdir(parents=True, exist_ok=True)

    generos = set()
    funcoes_tecnicas = set()
    persons_to_process = set()

    for movie_id in movie_ids:
        movie_file = movies_path / f"{movie_id}.movie.json"

        if not movie_file.exists():
            logger.warning(f"Arquivo de filme não encontrado: {movie_file}")
            continue

        with movie_file.open("r", encoding="utf-8") as f:
            movie_data = json.load(f)

        filme_data = dict()

        # Processar dados do filme
        filme_data["titulo_original"] = movie_data.get("original_title", "N/A")
        filme_data["titulo_portugues"] = movie_data.get("title", filme_data["titulo_original"])
        filme_data["ano_lancamento"] = movie_data.get("release_date", "N/A")[:4]
        filme_data["lancado"] = True if movie_data.get("status",
                                                       "").lower() == "released" else False
        filme_data["duracao_minutos"] = movie_data.get("runtime", 0)
        filme_data["sinopse"] = movie_data.get("overview", "")
        filme_data["orcamento_milhares"] = movie_data.get("budget", 0) // 1000
        filme_data["faturamento_lancamento_milhares"] = movie_data.get("revenue", 0) // 1000
        filme_data["poster_path"] = movie_data.get("poster_path", "")
        filme_data["com_poster"] = bool(filme_data["poster_path"])
        filme_data["generos_do_filme"] = [genre["name"] for genre in movie_data.get("genres", [])]
        filme_data["elenco"] = []
        filme_data["equipe_tecnica"] = []

        generos.update(filme_data["generos_do_filme"])

        credits_file = movies_path / f"{movie_id}.movie.credits.json"

        # Processar elenco
        if credits_file.exists():
            with credits_file.open("r", encoding="utf-8") as f:
                credits_data = json.load(f)
        else:
            logger.warning(f"Arquivo de créditos não encontrado: {credits_file}")
            continue

        cast = credits_data.get("cast", [])
        for member in cast:
            id_pessoa = member.get("id")
            if not Path(f"person/{id_pessoa}.person.json").exists():
                logger.warning(f"Arquivo de pessoa não encontrado: person/{id_pessoa}.person.json")
                continue
            persons_to_process.add(id_pessoa)
            nome_do_ator = member.get("name")
            if "/" in member.get("character"):
                personagens = member.get("character").split("/")
                for p in personagens:
                    personagem = p.strip()
                    if "uncredited" in personagem:
                        personagem = personagem.replace("(uncredited)", "").strip()
                        creditado = False
                    else:
                        creditado = True
                    filme_data["elenco"].append({"nome"      : nome_do_ator,
                                                 "personagem": p,
                                                 "creditado" : creditado})
            else:
                personagem = member.get("character", "") or ""
                if "uncredited" in personagem:
                    personagem = personagem.replace("(uncredited)", "").strip()
                    creditado = False
                else:
                    creditado = True
                filme_data["elenco"].append({"nome"      : nome_do_ator,
                                             "personagem": personagem,
                                             "creditado" : creditado}
                                            )
        crew = credits_data.get("crew", [])
        for member in crew:
            id_pessoa = member.get("id")
            if not Path(f"person/{id_pessoa}.person.json").exists():
                logger.warning(f"Arquivo de pessoa não encontrado: person/{id_pessoa}.person.json")
                continue
            persons_to_process.add(id_pessoa)
            nome_do_membro = member.get("original_name")
            funcao = member.get("job")
            funcoes_tecnicas.add(funcao)
            filme_data["equipe_tecnica"].append({"nome"  : nome_do_membro,
                                                 "funcao": funcao}
                                                )
        with (movie_output_path / f"{movie_id}.movie.processed.json").open("w", encoding="utf-8") as f:
            json.dump(filme_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Processado filme ID {movie_id}: {filme_data['titulo_portugues']}")

    with (movie_output_path / "generos.txt").open("w", encoding="utf-8") as f:
        for genero in sorted(generos):
            f.write(f"{genero}\n")

    with (movie_output_path / "funcoes_tecnicas.txt").open("w", encoding="utf-8") as f:
        for funcao in sorted(funcoes_tecnicas):
            f.write(f"{funcao}\n")

    logger.info(f"Processando dados de {len(persons_to_process)} pessoas...")

    for person in persons_to_process:
        person_file = person_path / f"{person}.person.json"
        if not person_file.exists():
            logger.warning(f"Arquivo de pessoa não encontrado: {person_file}")
            continue

        with person_file.open("r", encoding="utf-8") as f:
            person_data = json.load(f)

        pessoa_info = {
            "nome": person_data.get("name", "N/A"),
            "data_nascimento": person_data.get("birthday", None),
            "data_falecimento": person_data.get("deathday", None),
            "local_nascimento": person_data.get("place_of_birth", None),
            "biografia": person_data.get("biography", ""),
            "foto_path": person_data.get("profile_path", ""),
            "com_foto": bool(person_data.get("profile_path", "")),
        }

        with (person_output_path / f"{person}.person.processed.json").open("w", encoding="utf-8") as f:
            json.dump(pessoa_info, f, ensure_ascii=False, indent=2)
        logger.info(f"Processada pessoa ID {person}: {pessoa_info['nome']}")


    logger.info(f"Total de gêneros únicos: {len(generos)}")
    logger.info(f"Total de funções técnicas únicas: {len(funcoes_tecnicas)}")
    logger.info(f"Total de pessoas processadas: {len(persons_to_process)}")
