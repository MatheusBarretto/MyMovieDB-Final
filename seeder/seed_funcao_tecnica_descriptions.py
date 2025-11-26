import os
import sys
import time
import traceback
from pathlib import Path

# Adicionar o diretório pai ao path para importar o módulo app
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from app import create_app
from app.infra.modulos import db
from app.models.filme import FuncaoTecnica

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ Pacote 'openai' não encontrado. Instale com: pip install openai")


class AIDescriptionService:
    """Serviço para gerar descrições usando APIs de IA"""

    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.client = None

        if OPENAI_AVAILABLE and self.openai_api_key:
            try:
                self.client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                print(f"⚠️ Erro ao inicializar cliente OpenAI: {e}")

    def get_description_openai(self, funcao_nome: str) -> str:
        """
        Gera descrição usando OpenAI GPT
        
        Args:
            funcao_nome: Nome da função técnica
            
        Returns:
            Descrição gerada ou None se erro
        """
        if not self.client:
            return None

        prompt = f"Na indústria cinematográfica, o que faz um {funcao_nome}? Responda em menos de " \
                 f"1000 caracteres em português brasileiro."

        try:
            response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role"   : "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=300,
                    temperature=0.7
            )

            description = response.choices[0].message.content.strip()

            # Garantir que não exceda 1000 caracteres
            if len(description) > 1000:
                description = description[:997] + "..."

            return description

        except Exception as e:
            print(f"  ❌ Erro ao consultar OpenAI para '{funcao_nome}': {e}")
            return None

    def get_description_fallback(self, funcao_nome: str) -> str:
        """
        Descrição de fallback caso as APIs não funcionem
        
        Args:
            funcao_nome: Nome da função técnica
            
        Returns:
            Descrição básica
        """
        return f"Profissional responsável pela função de {funcao_nome.lower()} na produção " \
               f"cinematográfica."


def seed_funcao_tecnica_descriptions():
    """
    Atualiza as descrições das funções técnicas usando IA
    """
    print("=" * 80)
    print("SEED DE DESCRIÇÕES - FUNÇÕES TÉCNICAS")
    print("=" * 80)
    print()

    # Inicializar serviço de IA
    ai_service = AIDescriptionService()

    # Buscar todas as funções técnicas sem descrição ou com descrição vazia
    funcoes = FuncaoTecnica.query.filter(
            db.or_(
                    FuncaoTecnica.descricao.is_(None),
                    FuncaoTecnica.descricao == ""
            )
    ).all()

    if not funcoes:
        print("✅ Todas as funções técnicas já possuem descrição!")
        return

    print(f"📝 Encontradas {len(funcoes)} funções técnicas sem descrição:")
    for funcao in funcoes:
        print(f"  • {funcao.nome}")
    print()

    # Processar cada função
    success_count = 0
    error_count = 0

    for i, funcao in enumerate(funcoes, 1):
        print(f"[{i}/{len(funcoes)}] Processando: {funcao.nome}")

        try:
            # Tentar gerar descrição com OpenAI
            description = ai_service.get_description_openai(funcao.nome)

            if description:
                funcao.descricao = description
                db.session.add(funcao)
                print(
                    f"  ✓ Descrição gerada: {description
                    [:100]}{'...' if len(description) > 100 else ''}")
                success_count += 1
            else:
                # Usar fallback se a API falhar
                fallback_desc = ai_service.get_description_fallback(funcao.nome)
                funcao.descricao = fallback_desc
                db.session.add(funcao)
                print(f"  ⚠️ Usando descrição de fallback: {fallback_desc}")
                error_count += 1

            # Commit a cada função para evitar perder progresso
            db.session.commit()

            # Pequena pausa para não sobrecarregar a API
            time.sleep(1)

        except Exception as e:
            print(f"  ❌ Erro ao processar '{funcao.nome}': {e}")
            db.session.rollback()

            # Tentar salvar com descrição de fallback
            try:
                fallback_desc = ai_service.get_description_fallback(funcao.nome)
                funcao.descricao = fallback_desc
                db.session.add(funcao)
                db.session.commit()
                print(f"  ⚠️ Salvo com descrição de fallback: {fallback_desc}")
                error_count += 1
            except Exception as e2:
                print(f"  ❌ Falha total para '{funcao.nome}': {e2}")
                db.session.rollback()

    print("\n" + "=" * 80)
    print("✅ SEED DE DESCRIÇÕES CONCLUÍDO!")
    print("=" * 80)
    print(f"\nResumo:")
    print(f"  • {success_count} descrições geradas com IA")
    print(f"  • {error_count} descrições de fallback")
    print(f"  • {len(funcoes)} funções processadas")
    print()


def main():
    """Função principal"""
    # Carregar variáveis de ambiente
    load_dotenv()

    # Verificar se a chave da OpenAI está configurada
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("⚠️ AVISO: OPENAI_API_KEY não encontrada!")
        print("Para usar a API da OpenAI, defina: $Env:OPENAI_API_KEY=\"sua_chave\"")
        print("O script continuará usando descrições de fallback.\n")

    # Criar app e contexto
    app = create_app()

    with app.app_context():
        try:
            seed_funcao_tecnica_descriptions()

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
