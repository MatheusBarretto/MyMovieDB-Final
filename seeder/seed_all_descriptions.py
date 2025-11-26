import os
import sys
import time
import traceback
from pathlib import Path

# Adicionar o diretório pai ao path para importar o módulo app
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from flask import current_app

from app import create_app
from app.infra.modulos import db
from app.models.filme import FuncaoTecnica, Genero

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
        
    def get_funcao_description_openai(self, funcao_nome: str) -> str:
        """Gera descrição para função técnica usando OpenAI GPT"""
        if not self.client:
            return None
            
        prompt = f"Na indústria cinematográfica, o que faz um {funcao_nome}? Responda em menos de 1000 caracteres em português brasileiro."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            description = response.choices[0].message.content.strip()
            
            if len(description) > 1000:
                description = description[:997] + "..."
                
            return description
            
        except Exception as e:
            print(f"  ❌ Erro ao consultar OpenAI para função '{funcao_nome}': {e}")
            return None
    
    def get_genero_description_openai(self, genero_nome: str) -> str:
        """Gera descrição para gênero cinematográfico usando OpenAI GPT"""
        if not self.client:
            return None
            
        prompt = f"Descreva as principais características do gênero cinematográfico {genero_nome}, e liste três filmes clássicos desse gênero. Responda em menos de 1000 caracteres em português brasileiro."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            description = response.choices[0].message.content.strip()
            
            if len(description) > 1000:
                description = description[:997] + "..."
                
            return description
            
        except Exception as e:
            print(f"  ❌ Erro ao consultar OpenAI para gênero '{genero_nome}': {e}")
            return None
    
    def get_funcao_fallback(self, funcao_nome: str) -> str:
        """Descrição de fallback para função técnica"""
        return f"Profissional responsável pela função de {funcao_nome.lower()} na produção cinematográfica."
    
    def get_genero_fallback(self, genero_nome: str) -> str:
        """Descrição de fallback para gênero cinematográfico"""
        return f"Gênero cinematográfico {genero_nome.lower()} com características e elementos específicos que o distinguem de outros gêneros."


def seed_funcoes_tecnicas(ai_service, force_update=False):
    """Atualiza as descrições das funções técnicas"""
    print("📝 PROCESSANDO FUNÇÕES TÉCNICAS")
    print("-" * 50)
    
    # Buscar funções sem descrição ou forçar atualização
    if force_update:
        funcoes = FuncaoTecnica.query.all()
        print(f"Modo força ativado - processando todas as {len(funcoes)} funções técnicas")
    else:
        funcoes = FuncaoTecnica.query.filter(
            db.or_(
                FuncaoTecnica.descricao.is_(None),
                FuncaoTecnica.descricao == ""
            )
        ).all()
        print(f"Encontradas {len(funcoes)} funções técnicas sem descrição")
    
    if not funcoes:
        print("✅ Todas as funções técnicas já possuem descrição!")
        return 0, 0
    
    success_count = 0
    error_count = 0
    
    for i, funcao in enumerate(funcoes, 1):
        print(f"[{i}/{len(funcoes)}] {funcao.nome}")
        
        try:
            description = ai_service.get_funcao_description_openai(funcao.nome)
            
            if description:
                funcao.descricao = description
                success_count += 1
                print(f"  ✓ IA: {description[:80]}{'...' if len(description) > 80 else ''}")
            else:
                fallback_desc = ai_service.get_funcao_fallback(funcao.nome)
                funcao.descricao = fallback_desc
                error_count += 1
                print(f"  ⚠️ Fallback: {fallback_desc[:80]}{'...' if len(fallback_desc) > 80 else ''}")
            
            db.session.add(funcao)
            db.session.commit()
            time.sleep(0.5)  # Pausa menor para funções
            
        except Exception as e:
            print(f"  ❌ Erro: {e}")
            db.session.rollback()
            error_count += 1
    
    return success_count, error_count


def seed_generos(ai_service, force_update=False):
    """Atualiza as descrições dos gêneros cinematográficos"""
    print("\n📝 PROCESSANDO GÊNEROS CINEMATOGRÁFICOS")
    print("-" * 50)
    
    # Buscar gêneros sem descrição ou forçar atualização
    if force_update:
        generos = Genero.query.all()
        print(f"Modo força ativado - processando todos os {len(generos)} gêneros")
    else:
        generos = Genero.query.filter(
            db.or_(
                Genero.descricao.is_(None),
                Genero.descricao == ""
            )
        ).all()
        print(f"Encontrados {len(generos)} gêneros sem descrição")
    
    if not generos:
        print("✅ Todos os gêneros já possuem descrição!")
        return 0, 0
    
    success_count = 0
    error_count = 0
    
    for i, genero in enumerate(generos, 1):
        print(f"[{i}/{len(generos)}] {genero.nome}")
        
        try:
            description = ai_service.get_genero_description_openai(genero.nome)
            
            if description:
                genero.descricao = description
                success_count += 1
                print(f"  ✓ IA: {description[:80]}{'...' if len(description) > 80 else ''}")
            else:
                fallback_desc = ai_service.get_genero_fallback(genero.nome)
                genero.descricao = fallback_desc
                error_count += 1
                print(f"  ⚠️ Fallback: {fallback_desc[:80]}{'...' if len(fallback_desc) > 80 else ''}")
            
            db.session.add(genero)
            db.session.commit()
            time.sleep(1)  # Pausa maior para gêneros (mais texto)
            
        except Exception as e:
            print(f"  ❌ Erro: {e}")
            db.session.rollback()
            error_count += 1
    
    return success_count, error_count


def main():
    """Função principal"""
    load_dotenv()
    
    # Verificar argumentos
    force_update = "--force" in sys.argv
    only_funcoes = "--funcoes" in sys.argv
    only_generos = "--generos" in sys.argv
    
    # Verificar chave da OpenAI
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("⚠️ AVISO: OPENAI_API_KEY não encontrada!")
        print("Para usar a API da OpenAI, defina: $Env:OPENAI_API_KEY=\"sua_chave\"")
        print("O script continuará usando descrições de fallback.\n")
    
    print("=" * 80)
    print("SEED DE DESCRIÇÕES - COMPLETO")
    print("=" * 80)
    if force_update:
        print("🔄 MODO FORÇA: Atualizando TODAS as descrições")
    if only_funcoes:
        print("🎯 Processando apenas FUNÇÕES TÉCNICAS")
    elif only_generos:
        print("🎯 Processando apenas GÊNEROS")
    print()
    
    # Criar app e contexto
    app = create_app()
    
    with app.app_context():
        try:
            ai_service = AIDescriptionService()
            
            total_ai_success = 0
            total_fallback = 0
            
            # Processar funções técnicas
            if not only_generos:
                func_success, func_error = seed_funcoes_tecnicas(ai_service, force_update)
                total_ai_success += func_success
                total_fallback += func_error
            
            # Processar gêneros
            if not only_funcoes:
                gen_success, gen_error = seed_generos(ai_service, force_update)
                total_ai_success += gen_success
                total_fallback += gen_error
            
            print("\n" + "=" * 80)
            print("✅ SEED COMPLETO CONCLUÍDO!")
            print("=" * 80)
            print(f"Resumo geral:")
            print(f"  • {total_ai_success} descrições geradas com IA")
            print(f"  • {total_fallback} descrições de fallback")
            print(f"  • {total_ai_success + total_fallback} itens processados")
            print()
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()