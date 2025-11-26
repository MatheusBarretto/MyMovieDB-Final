"""Script para exportar dados do banco de dados para arquivos JSON.

Este script exporta todas as entidades do banco de dados (filmes, pessoas, gêneros,
funções técnicas, etc.) para arquivos JSON que podem ser usados como base para
um processo de seeding, eliminando a necessidade de buscar dados da API do TMDB.
"""
import json
import sys
import traceback
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

# Adicionar o diretório raiz do projeto ao Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.infra.modulos import db
from app.models.filme import Filme, Genero, FuncaoTecnica
from app.models.pessoa import Pessoa, Ator
from app.models.juncoes import Atuacao, EquipeTecnica


def serialize_date(obj: Any) -> str:
    """Serializa objetos date para string no formato ISO.

    Args:
        obj: Objeto a ser serializado

    Returns:
        String no formato YYYY-MM-DD ou None
    """
    if isinstance(obj, date):
        return obj.strftime("%Y-%m-%d")
    return None


def serialize_decimal(obj: Any) -> float:
    """Serializa objetos Decimal para float.

    Args:
        obj: Objeto a ser serializado

    Returns:
        Float ou None
    """
    if isinstance(obj, Decimal):
        return float(obj)
    return None


def dump_generos(output_dir: Path) -> dict[str, Genero]:
    """Exporta todos os gêneros para arquivo de texto.

    Args:
        output_dir: Diretório de saída

    Returns:
        Dicionário mapeando nome do gênero para o objeto Genero
    """
    print("\n📝 Exportando gêneros...")
    generos_dict = {}

    # Criar diretório de saída se não existir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Buscar todos os gêneros ordenados por nome
    generos = db.session.execute(
        db.select(Genero).order_by(Genero.nome)
    ).scalars().all()

    # Salvar como arquivo de texto simples (compatível com seed_data_into_app.py)
    output_file = output_dir / "generos.txt"
    with output_file.open("w", encoding="utf-8") as f:
        for genero in generos:
            f.write(f"{genero.nome}\n")
            generos_dict[genero.nome] = genero
            print(f"  ✓ {genero.nome}")

    # Também salvar versão completa com descrições em JSON
    output_file_json = output_dir / "generos_completo.json"
    generos_data = []
    for genero in generos:
        generos_data.append({
            "nome": genero.nome,
            "descricao": genero.descricao,
            "ativo": genero.ativo
        })

    with output_file_json.open("w", encoding="utf-8") as f:
        json.dump(generos_data, f, ensure_ascii=False, indent=2)

    print(f"  📁 Arquivo criado: {output_file}")
    print(f"  📁 Arquivo criado: {output_file_json}")
    return generos_dict


def dump_funcoes_tecnicas(output_dir: Path) -> dict[str, FuncaoTecnica]:
    """Exporta todas as funções técnicas para arquivo de texto.

    Args:
        output_dir: Diretório de saída

    Returns:
        Dicionário mapeando nome da função para o objeto FuncaoTecnica
    """
    print("\n📝 Exportando funções técnicas...")
    funcoes_dict = {}

    # Criar diretório de saída se não existir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Buscar todas as funções técnicas ordenadas por nome
    funcoes = db.session.execute(
        db.select(FuncaoTecnica).order_by(FuncaoTecnica.nome)
    ).scalars().all()

    # Salvar como arquivo de texto simples (compatível com seed_data_into_app.py)
    output_file = output_dir / "funcoes_tecnicas.txt"
    with output_file.open("w", encoding="utf-8") as f:
        for funcao in funcoes:
            f.write(f"{funcao.nome}\n")
            funcoes_dict[funcao.nome] = funcao
            print(f"  ✓ {funcao.nome}")

    # Também salvar versão completa com descrições em JSON
    output_file_json = output_dir / "funcoes_tecnicas_completo.json"
    funcoes_data = []
    for funcao in funcoes:
        funcoes_data.append({
            "nome": funcao.nome,
            "descricao": funcao.descricao,
            "ativo": funcao.ativo
        })

    with output_file_json.open("w", encoding="utf-8") as f:
        json.dump(funcoes_data, f, ensure_ascii=False, indent=2)

    print(f"  📁 Arquivo criado: {output_file}")
    print(f"  📁 Arquivo criado: {output_file_json}")
    return funcoes_dict


def dump_pessoas(output_dir: Path) -> dict[str, Pessoa]:
    """Exporta todas as pessoas para arquivos JSON individuais.

    Args:
        output_dir: Diretório de saída para os arquivos JSON

    Returns:
        Dicionário mapeando nome da pessoa para o objeto Pessoa
    """
    print("\n📝 Exportando pessoas...")
    pessoas_dict = {}

    # Criar diretório de saída para pessoas se não existir
    person_dir = output_dir / "person"
    person_dir.mkdir(parents=True, exist_ok=True)

    # Buscar todas as pessoas ordenadas por nome
    pessoas = db.session.execute(
        db.select(Pessoa).order_by(Pessoa.nome)
    ).scalars().all()

    for idx, pessoa in enumerate(pessoas, start=1):
        # Criar dados da pessoa no formato esperado
        pessoa_data = {
            "nome": pessoa.nome,
            "data_nascimento": serialize_date(pessoa.data_nascimento),
            "data_falecimento": serialize_date(pessoa.data_falecimento),
            "local_nascimento": pessoa.local_nascimento,
            "biografia": pessoa.biografia or "",
            "foto_path": None,  # Será mantido None pois não temos o path original da API
            "com_foto": pessoa.com_foto,
            # Incluir dados da foto em base64 para preservar as imagens
            "foto_base64": pessoa.foto_base64 if pessoa.com_foto else None,
            "foto_mime": pessoa.foto_mime if pessoa.com_foto else None,
        }

        # Incluir nome artístico se for ator
        if pessoa.ator:
            pessoa_data["nome_artistico"] = pessoa.ator.nome_artistico

        # Salvar arquivo JSON individual
        # Usar índice sequencial para evitar problemas com caracteres especiais no nome
        output_file = person_dir / f"{idx:05d}.person.processed.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(pessoa_data, f, ensure_ascii=False, indent=2)

        pessoas_dict[pessoa.nome] = pessoa
        print(f"  ✓ {pessoa.nome} -> {output_file.name}")

    print(f"  📁 {len(pessoas)} pessoas exportadas para {person_dir}")
    return pessoas_dict


def dump_filmes(output_dir: Path,
                pessoas_dict: dict[str, Pessoa],
                generos_dict: dict[str, Genero],
                funcoes_dict: dict[str, FuncaoTecnica]) -> dict[str, Filme]:
    """Exporta todos os filmes para arquivos JSON individuais.

    Args:
        output_dir: Diretório de saída para os arquivos JSON
        pessoas_dict: Dicionário com todas as pessoas
        generos_dict: Dicionário com todos os gêneros
        funcoes_dict: Dicionário com todas as funções técnicas

    Returns:
        Dicionário mapeando chave do filme para o objeto Filme
    """
    print("\n📝 Exportando filmes...")
    filmes_dict = {}

    # Criar diretório de saída para filmes se não existir
    movies_dir = output_dir / "movies"
    movies_dir.mkdir(parents=True, exist_ok=True)

    # Buscar todos os filmes ordenados por ano e título
    filmes = db.session.execute(
        db.select(Filme).order_by(Filme.ano_lancamento, Filme.titulo_original)
    ).scalars().all()

    for idx, filme in enumerate(filmes, start=1):
        # Coletar gêneros do filme
        generos_do_filme = [genero.nome for genero in filme.generos]

        # Coletar elenco
        elenco = []
        for atuacao in filme.elenco:
            elenco.append({
                "nome": atuacao.ator.pessoa.nome,
                "personagem": atuacao.personagem,
                "creditado": atuacao.creditado,
                "protagonista": atuacao.protagonista,
                "tempo_de_tela_minutos": atuacao.tempo_de_tela_minutos
            })

        # Coletar equipe técnica
        equipe_tecnica = []
        for membro in filme.equipe_tecnica:
            equipe_tecnica.append({
                "nome": membro.pessoa.nome,
                "funcao": membro.funcao_tecnica.nome,
                "creditado": membro.creditado
            })

        # Criar dados do filme no formato esperado
        filme_data = {
            "titulo_original": filme.titulo_original,
            "titulo_portugues": filme.titulo_portugues,
            "ano_lancamento": filme.ano_lancamento,
            "lancado": filme.lancado,
            "duracao_minutos": filme.duracao_minutos,
            "sinopse": filme.sinopse or "",
            "orcamento_milhares": serialize_decimal(filme.orcamento_milhares),
            "faturamento_lancamento_milhares": serialize_decimal(filme.faturamento_lancamento_milhares),
            "poster_path": None,  # Será mantido None pois não temos o path original da API
            "com_poster": filme.com_poster,
            # Incluir dados do poster em base64 para preservar as imagens
            "poster_base64": filme.poster_base64 if filme.com_poster else None,
            "poster_mime": filme.poster_mime if filme.com_poster else None,
            "trailer_youtube": filme.trailer_youtube,
            "generos_do_filme": generos_do_filme,
            "elenco": elenco,
            "equipe_tecnica": equipe_tecnica
        }

        # Salvar arquivo JSON individual
        # Usar índice sequencial para evitar problemas com caracteres especiais no título
        output_file = movies_dir / f"{idx:05d}.movie.processed.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(filme_data, f, ensure_ascii=False, indent=2)

        chave = f"{filme.titulo_original}, {filme.ano_lancamento}"
        filmes_dict[chave] = filme
        print(f"  ✓ {chave} -> {output_file.name}")

    print(f"  📁 {len(filmes)} filmes exportados para {movies_dir}")
    return filmes_dict


def main():
    """Função principal do script de dump."""
    print("=" * 80)
    print("DUMP DE DADOS - MYMOVIEDB")
    print("=" * 80)
    print()

    # Criar app e contexto
    app = create_app()

    with app.app_context():
        try:
            # Definir diretório de saída
            output_dir = Path("seeder/output")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Exportar dados
            generos_dict = dump_generos(output_dir / "movies")
            funcoes_dict = dump_funcoes_tecnicas(output_dir / "movies")
            pessoas_dict = dump_pessoas(output_dir)
            filmes_dict = dump_filmes(output_dir, pessoas_dict, generos_dict, funcoes_dict)

            print("\n" + "=" * 80)
            print("✅ DUMP CONCLUÍDO COM SUCESSO!")
            print("=" * 80)
            print(f"\nResumo:")
            print(f"  • {len(generos_dict)} gêneros")
            print(f"  • {len(funcoes_dict)} funções técnicas")
            print(f"  • {len(pessoas_dict)} pessoas")
            print(f"  • {len(filmes_dict)} filmes")
            print(f"\nArquivos salvos em: {output_dir.absolute()}")
            print()

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
