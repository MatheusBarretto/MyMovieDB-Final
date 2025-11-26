import os
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

# Adicionar o diretório pai ao path para importar o módulo app
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from app import create_app
from app.infra.modulos import db
from app.models.pessoa import Pessoa

try:
    from perplexity import Perplexity
    PERPLEXITY_AVAILABLE = True
except ImportError:
    PERPLEXITY_AVAILABLE = False
    print("⚠️ Pacote 'perplexity' não encontrado. Instale com: pip install perplexityai")


class AIBiographyService:
    """Serviço para coletar biografias a partir da API da Perplexity AI"""
    
    def __init__(self):
        self.perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
        self.client = None
        
        if PERPLEXITY_AVAILABLE and self.perplexity_api_key:
            try:
                self.client = Perplexity(api_key=self.perplexity_api_key)
            except Exception as e:
                print(f"⚠️ Erro ao inicializar cliente Perplexity: {e}")
        
    def get_biography_perplexity(self, nome_pessoa: str) -> Optional[str]:
        """
        Gera biografia usando a API da Perplexity AI

        Args:
            nome_pessoa: Nome do profissional de cinema

        Returns:
            Biografia ou None se erro
        """
        if not self.client:
            return None

        prompt = f"Construa uma biografia em português brasileiro de até 2000 caracteres sobre " \
                 f"o ator {nome_pessoa}, incluindo detalhes sobre sua carreira, prêmios e " \
                 f"vida pessoal. Utilize uma linguagem simples e direta, evitando " \
                 f"adjetivos e focando em fatos. Produza um texto com três parágrafos: o " \
                 f"primeiro parágrafo deve conter os dados básicos (data de nascimento, local de " \
                 f"nascimento, nacionalidade e outros fatos relevantes), o segundo parágrafo deve " \
                 f"focar na carreira cinematográfica e o terceiro parágrafo deve abordar a vida " \
                 f"pessoal e prêmios. Não inclua menções a fontes ou citações."

        try:
            response = self.client.chat.completions.create(
                    model="sonar",
                    messages=[{"role"   : "user",
                               "content": prompt }]
            )

            biografia = response.choices[0].message.content.strip()

            lines = biografia.strip().split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            biografia = ' '.join(non_empty_lines)
            
            # Garantir que não exceda 2000 caracteres
            if len(biografia) > 2000:
                biografia = biografia[:1997] + "..."
            biografia = biografia + " (Biografia obtida a partir da Perplexity AI)"
                
            return biografia
            
        except Exception as e:
            print(f"  ❌ Erro ao consultar Perplexity para '{nome_pessoa}': {e}")
            return None
    
    @staticmethod
    def get_biography_fallback(nome_pessoa: str) -> str:
        """
        Descrição de fallback caso as APIs não funcionem
        
        Args:
            nome_pessoa: Nome do gênero cinematográfico
            
        Returns:
            Descrição básica
        """
        return f"{nome_pessoa.capitalize()} é um profissional da indústria cinematográfica."


def seed_biographies():
    """
    Atualiza as biografias usando chamadas à Perplexity AI ou fallback
    """
    print("=" * 80)
    print("SEED DE BIOGRAFIAS")
    print("=" * 80)
    print()
    
    # Inicializar serviço de IA
    ai_service = AIBiographyService()
    
    # Buscar todos as pessoas que são atores e sem biografia ou biografia vazia
    pessoas = Pessoa.query.filter(
        Pessoa.ator.has(),  # Apenas pessoas que são atores
        db.or_(
            Pessoa.biografia.is_(None),
            Pessoa.biografia == ""
        )
    ).all()
    
    if not pessoas:
        print("✅ Todas as pessoas já possuem biografia!")
        return
    
    print(f"📝 Encontradas {len(pessoas)} pessoas sem biografia:")
    for pessoa in pessoas:
        print(f"  • {pessoa.nome}")
    print()
    
    # Processar cada pessoa
    success_count = 0
    error_count = 0
    
    for i, pessoa in enumerate(pessoas, 1):
        print(f"[{i}/{len(pessoas)}] Processando: {pessoa.nome}")
        
        try:
            # Tentar gerar descrição com OpenAI
            biografia = ai_service.get_biography_perplexity(pessoa.nome)
            
            if biografia:
                pessoa.biografia = biografia
                db.session.add(pessoa)
                print(f"  ✓ Biografia coletada: {biografia[:100]}{'...' if len(biografia) > 100 else ''}")
                success_count += 1
            else:
                # Usar fallback se a API falhar
                fallback_bio = ai_service.get_biography_fallback(pessoa.nome)
                pessoa.biografia = fallback_bio
                db.session.add(pessoa)
                print(f"  ⚠️ Usando biografia de fallback: {fallback_bio}")
                error_count += 1
            
            # Commit a cada pessoa para evitar perder progresso
            db.session.commit()
            
            # Pequena pausa para não sobrecarregar a API
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ Erro ao processar '{pessoa.nome}': {e}")
            db.session.rollback()
            
            # Tentar salvar com biografia de fallback
            try:
                fallback_bio = ai_service.get_biography_fallback(pessoa.nome)
                pessoa.descricao = fallback_bio
                db.session.add(pessoa)
                db.session.commit()
                print(f"  ⚠️ Salvo com biografia de fallback: {fallback_bio}")
                error_count += 1
            except Exception as e2:
                print(f"  ❌ Falha total para '{pessoa.nome}': {e2}")
                db.session.rollback()
    
    print("\n" + "=" * 80)
    print("✅ SEED DE BIOGRAFIAS CONCLUÍDO!")
    print("=" * 80)
    print(f"\nResumo:")
    print(f"  • {success_count} biografias coletadas com IA")
    print(f"  • {error_count} biografias de fallback")
    print(f"  • {len(pessoas)} pessoas processadas")
    print()


def main():
    """Função principal"""
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar se a chave da OpenAI está configurada
    openai_key = os.getenv('PERPLEXITY_API_KEY')
    if not openai_key:
        print("⚠️ AVISO: PERPLEXITY_API_KEY não encontrada!")
        print("Para usar a API da Perplexity, defina: $Env:PERPLEXITY_API_KEY=\"sua_chave\"")
        print("O script continuará usando descrições de fallback.\n")
    
    # Criar app e contexto
    app = create_app()
    
    with app.app_context():
        try:
            seed_biographies()
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
