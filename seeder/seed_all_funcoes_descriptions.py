"""Script para preencher descrições de TODAS as funções técnicas no banco de dados.

Este script adiciona descrições detalhadas para todas as 143 funções técnicas
encontradas no sistema MyMovieDB.

Uso:
    python seeder/seed_all_funcoes_descriptions.py
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models.filme import FuncaoTecnica

# Dicionário completo com descrições de TODAS as funções técnicas (143 funções)
DESCRICOES_FUNCOES = {
    # ===== DIREÇÃO =====
    "Director": "O diretor é o principal responsável pela visão criativa e artística do filme, coordenando todos os aspectos da produção desde a interpretação dos atores até a composição visual de cada cena.",
    "Assistant Director": "Responsável pela logística e organização do set, gerencia cronogramas, coordena equipe e elenco, atuando como elo entre o diretor e a produção.",
    "First Assistant Director": "Braço direito do diretor, gerencia o set e mantém a produção no cronograma, coordenando todos os departamentos e organizando chamados diários.",
    "Second Assistant Director": "Apoia o primeiro assistente focando em logística de elenco e figuração, preparando chamados diários e coordenando transporte.",
    "Second Unit Director": "Filma cenas adicionais, sequências de ação e planos de estabelecimento simultaneamente à unidade principal para aumentar eficiência.",
    "Second Unit Director of Photography": "Diretor de fotografia da segunda unidade, mantém consistência visual com a unidade principal enquanto filma cenas adicionais e sequências de ação.",
    
    # ===== PRODUÇÃO =====
    "Producer": "Supervisiona todos os aspectos da produção cinematográfica, gerenciando orçamento, contratando equipe e coordenando logística do desenvolvimento à distribuição.",
    "Executive Producer": "Responsável pelo financiamento e decisões de negócios de alto nível, representando estúdio ou investidores com autoridade final sobre orçamento e estratégia.",
    "Co-Producer": "Trabalha em conjunto com o produtor principal, compartilhando responsabilidades e focando em áreas específicas como orçamento ou logística.",
    "Associate Producer": "Auxilia produtores principais em tarefas específicas como pesquisa, desenvolvimento de roteiro ou coordenação de locações.",
    "Co-Executive Producer": "Compartilha responsabilidades executivas, frequentemente representando diferentes investidores ou estúdios envolvidos no projeto.",
    "Executive in Charge of Finance": "Supervisiona todos os aspectos financeiros incluindo orçamento, fluxo de caixa, relatórios e conformidade fiscal.",
    "Unit Production Manager": "Supervisiona operações diárias gerenciando orçamento, cronograma e logística, coordenando todos os departamentos.",
    "Production Manager": "Coordena aspectos logísticos e administrativos, gerenciando recursos, equipamentos, locações e pessoal.",
    "Production Supervisor": "Monitora progresso diário garantindo cumprimento de cronograma e uso eficiente de recursos.",
    "Production Director": "Supervisiona aspectos técnicos e logísticos coordenando entre departamentos criativos e operacionais.",
    "Producer's Assistant": "Apoia o produtor em tarefas administrativas, gerenciando agendas, coordenando reuniões e preparando documentos.",
    "Post Production Supervisor": "Coordena todas as atividades de pós-produção incluindo edição, efeitos visuais, mixagem de som e finalização.",
    "Post Production Consulting": "Oferece expertise especializada em aspectos técnicos e criativos da pós-produção, aconselhando sobre fluxos de trabalho e tecnologias.",
    
    # ===== ROTEIRO E ESCRITA =====
    "Screenplay": "Cria ou adapta a história do filme, desenvolvendo diálogos, personagens, estrutura narrativa e descrições de cenas.",
    "Writer": "Contribui para desenvolvimento da história e roteiro, trabalhando no conceito original, adaptações ou reescritas.",
    "Novel": "Autor do romance original no qual o filme é baseado, cuja obra literária serve como fonte primária para adaptação.",
    "Book": "Autor do livro que serve como material fonte para o filme, seja ficção ou não-ficção.",
    "Short Story": "Autor do conto original que inspirou ou serviu de base para o filme.",
    "Story": "Criador da história original ou conceito narrativo, desenvolvendo premissa básica, personagens e estrutura.",
    "Characters": "Criador dos personagens originais, especialmente relevante em adaptações de quadrinhos ou outras mídias.",
    "Comic Book": "Criador da história em quadrinhos original que serve como base para o filme.",
    "Graphic Novel Illustrator": "Ilustrador da graphic novel cujo trabalho artístico influencia o design visual do filme.",
    "Original Film Writer": "Escritor que criou o conceito ou roteiro original de um filme anterior sendo refeito ou continuado.",
    "Script Supervisor": "Monitora detalhes de cada tomada para garantir consistência entre cenas, anotando posições, diálogos e movimentos.",
    
    # ===== FOTOGRAFIA E CÂMERA =====
    "Director of Photography": "Responsável pela criação da linguagem visual do filme, definindo iluminação, composição, movimento de câmera e paleta de cores.",
    "Camera Operator": "Opera a câmera durante as filmagens, executando movimentos e enquadramentos conforme direção do diretor de fotografia.",
    '"A" Camera Operator': "Opera a câmera principal (câmera A) que captura as tomadas primárias e mais importantes de cada cena.",
    '"B" Camera Operator': "Opera a câmera secundária (câmera B) que captura ângulos alternativos ou cobertura adicional simultaneamente.",
    "Steadicam Operator": "Especialista em operar câmera Steadicam, criando movimentos fluidos e estáveis sem trilhos ou grua.",
    "Assistant Camera": "Auxilia o operador de câmera, responsável por foco, manutenção de equipamento e preparação de câmeras.",
    'First Assistant "A" Camera': "Responsável pelo foco da câmera principal, medindo distâncias e ajustando foco durante tomadas.",
    'First Assistant "B" Camera': "Responsável pelo foco da câmera secundária, garantindo nitidez nas tomadas de cobertura.",
    'Second Assistant "A" Camera': "Auxilia na câmera principal, carregando filmes/cartões, organizando equipamento e mantendo registros.",
    'Second Assistant "B" Camera': "Auxilia na câmera secundária com tarefas de suporte e organização de equipamento.",
    "Camera Department Production Assistant": "Assistente de produção do departamento de câmera, auxiliando em tarefas gerais e logística.",
    "Dolly Grip": "Opera o dolly (carrinho de câmera), executando movimentos suaves de câmera em trilhos ou rodas.",
    "Key Grip": "Chefe do departamento de grip, supervisiona equipamento de suporte de câmera, trilhos, gruas e rigging.",
    "Rigging Gaffer": "Especialista em instalação de equipamento de iluminação em locações complexas ou estruturas elevadas.",
    "Gaffer": "Chefe do departamento de iluminação, executa o plano de iluminação do diretor de fotografia.",
    "Still Photographer": "Fotógrafo de cena que captura imagens estáticas para divulgação, arquivo e materiais promocionais.",
    
    # ===== EDIÇÃO =====
    "Editor": "Seleciona e organiza tomadas filmadas para criar a narrativa final, trabalhando com ritmo, timing e continuidade.",
    "Supervising Editor": "Supervisiona o processo de edição, coordenando múltiplos editores e garantindo consistência narrativa e técnica.",
    "Assistant Editor": "Auxilia o editor organizando material filmado, sincronizando áudio, preparando sequências e gerenciando arquivos.",
    "First Assistant Editor": "Principal assistente de edição, gerencia organização de material, sincronização e preparação de sequências para o editor.",
    "Dialogue Editor": "Especialista em edição de diálogos, limpando áudio, removendo ruídos e garantindo clareza das falas.",
    "Sound Editor": "Edita e organiza todos os elementos sonoros do filme, criando a estrutura da trilha sonora final.",
    "Supervising Sound Editor": "Supervisiona todo o departamento de edição de som, coordenando editores de diálogo, efeitos e música.",
    "Sound Effects Editor": "Cria e edita efeitos sonoros, desde sons ambientes sutis até efeitos dramáticos de ação.",
    "Supervising Sound Effects Editor": "Supervisiona a criação e edição de todos os efeitos sonoros, garantindo qualidade e consistência.",
    "Music Editor": "Edita e sincroniza música com imagem, trabalhando com compositor e diretor para timing perfeito.",
    "Visual Effects Editor": "Edita e integra efeitos visuais digitais com filmagem real, gerenciando placeholders e versões finais.",
    "Color Timer": "Ajusta cor e exposição de cada cena para criar consistência visual e mood desejado (termo tradicional para colorista).",
    "Colorist": "Especialista em correção e gradação de cor, criando a paleta visual final e mood do filme.",
    "Digital Intermediate": "Técnico especializado no processo de finalização digital, convertendo e processando imagens para distribuição.",
    
    # ===== SOM =====
    "Sound Designer": "Cria e manipula elementos sonoros para construir a paisagem sonora do filme, desenvolvendo efeitos e texturas auditivas.",
    "Sound": "Profissional geral de som responsável por aspectos da captação, edição ou mixagem de áudio.",
    "Production Sound Mixer": "Capta e mixa áudio durante as filmagens, garantindo qualidade de gravação de diálogos e sons de cena.",
    "Sound Mixer": "Mixa elementos sonoros, balanceando níveis de diálogo, música e efeitos para criar a trilha sonora final.",
    "Sound Re-Recording Mixer": "Especialista em mixagem final, combinando todas as trilhas de som em master final para distribuição.",
    "Additional Sound Re-Recording Mixer": "Mixador adicional que auxilia na mixagem final de elementos sonoros específicos.",
    "Sound Recordist": "Técnico responsável pela gravação de som no set, operando equipamento de captação de áudio.",
    "Sound Supervisor": "Supervisiona todos os aspectos de som do filme, coordenando captação, edição e mixagem.",
    "Sound Montage Associate": "Auxilia na montagem e organização de elementos sonoros durante o processo de edição.",
    "Foley": "Profissional que cria efeitos sonoros práticos sincronizados com imagem, como passos, movimentos de roupa e manipulação de objetos.",
    "Foley Artist": "Artista especializado em criar sons de Foley, usando objetos e superfícies para recriar sons naturais.",
    "Scoring Mixer": "Mixador especializado em gravação e mixagem de trilha sonora musical original.",
    "ADR & Dubbing": "Técnico especializado em gravação de diálogos adicionais (ADR) e dublagem para substituir ou melhorar áudio original.",
    
    # ===== MÚSICA =====
    "Original Music Composer": "Cria a trilha sonora original que acompanha e realça a narrativa, desenvolvendo temas musicais para personagens e emoções.",
    "Music Director": "Dirige a execução musical, coordenando músicos e garantindo que a música sirva à visão do filme.",
    "Music Producer": "Produz a gravação da trilha sonora, supervisionando sessões de gravação e qualidade técnica da música.",
    "Music Supervisor": "Seleciona e licencia músicas existentes para o filme, coordenando entre compositores, artistas e produção.",
    "Conductor": "Rege a orquestra durante gravação da trilha sonora, interpretando a partitura do compositor.",
    "Orchestrator": "Adapta composições do compositor para orquestra completa, criando arranjos instrumentais detalhados.",
    "Additional Music": "Compositor adicional que contribui com peças musicais suplementares ou variações de temas principais.",
    "Vocals": "Artista vocal que executa canções ou vocalizações para a trilha sonora do filme.",
    
    # ===== DESIGN DE PRODUÇÃO E ARTE =====
    "Production Design": "Concebe a visão visual geral do filme incluindo cenários, locações, adereços e estética, criando o mundo físico da história.",
    "Art Direction": "Executa o design visual do filme, coordenando construção de cenários, seleção de locações e criação de adereços.",
    "Supervising Art Director": "Supervisiona múltiplos diretores de arte, garantindo consistência visual em produções de grande escala.",
    "Standby Art Director": "Diretor de arte presente no set durante filmagens para resolver questões visuais e fazer ajustes imediatos.",
    "Set Decoration": "Seleciona e posiciona objetos móveis nos cenários, incluindo móveis, obras de arte e itens decorativos.",
    "Set Designer": "Desenha e planeja cenários específicos, criando plantas e especificações para construção.",
    "Conceptual Design": "Cria conceitos visuais iniciais e arte conceitual que estabelecem o visual e atmosfera do filme.",
    "Graphic Designer": "Cria elementos gráficos para o filme como logos, sinalizações, documentos e outros materiais visuais de cena.",
    "Title Designer": "Desenha sequência de créditos iniciais e finais, criando tipografia e animações que complementam o filme.",
    "Art Department Coordinator": "Coordena logística e administração do departamento de arte, gerenciando orçamento e cronograma.",
    "Set Production Assistant": "Assistente de produção do departamento de arte, auxiliando em tarefas gerais e logística de set.",
    "Property Master": "Responsável por todos os adereços do filme, desde aquisição até manutenção e continuidade.",
    "Assistant Property Master": "Auxilia o property master na gestão, organização e manutenção de adereços.",
    "Greensman": "Especialista em vegetação e plantas para cenários, criando e mantendo elementos naturais em sets.",
    "Lighting Design": "Projeta esquema de iluminação geral do filme, trabalhando com diretor de fotografia para criar mood visual.",
    
    # ===== FIGURINO E MAQUIAGEM =====
    "Costume Design": "Cria e seleciona roupas e acessórios dos personagens, desenvolvendo visual que reflete personalidade e época.",
    "Costume Designer": "Designer responsável por conceber e executar todos os figurinos do filme.",
    "Wardrobe Designer": "Projeta guarda-roupa dos personagens, focando em estilo, período e caracterização.",
    "Wardrobe Supervisor": "Supervisiona departamento de figurino, gerenciando equipe, orçamento e manutenção de roupas.",
    "Key Costumer": "Principal assistente de figurino, coordena equipe e garante que figurinos estejam prontos para cada cena.",
    "Set Costumer": "Figurinista presente no set durante filmagens, fazendo ajustes e mantendo continuidade de figurinos.",
    "Makeup Artist": "Cria e aplica maquiagem nos atores para alcançar aparência desejada dos personagens.",
    "Makeup Designer": "Designer responsável por conceber visual de maquiagem de todos os personagens.",
    "Makeup Department Head": "Chefe do departamento de maquiagem, supervisiona equipe e coordena com outros departamentos.",
    "Makeup Supervisor": "Supervisiona aplicação de maquiagem, garantindo consistência e qualidade em todas as cenas.",
    "Makeup & Hair": "Profissional responsável tanto por maquiagem quanto penteados dos atores.",
    "Hair Designer": "Designer responsável por conceber penteados e visual capilar de todos os personagens.",
    "Hair Department Head": "Chefe do departamento de cabelo, supervisiona cabeleireiros e coordena visual capilar.",
    "Hairstylist": "Cabeleireiro que cria e mantém penteados dos atores durante produção.",
    "Prosthetic Designer": "Designer especializado em criar próteses e aplicações especiais de maquiagem.",
    "Prosthetic Makeup Artist": "Artista especializado em aplicar e manter próteses e maquiagem de efeitos especiais.",
    "Prosthetics": "Profissional geral de próteses responsável por criação e aplicação de peças protéticas.",
    
    # ===== ELENCO =====
    "Casting": "Encontra e seleciona atores para todos os papéis, organizando audições e negociando contratos.",
    "Dialect Coach": "Treinador especializado em sotaques e dialetos, ajudando atores a desenvolver fala autêntica para seus personagens.",
    "Dialogue Coach": "Treinador que auxilia atores com entrega de diálogos, timing e interpretação de falas.",
    "Choreographer": "Cria e ensaia coreografias de dança ou movimento para cenas específicas.",
    "Fight Choreographer": "Especialista em coreografar cenas de luta e combate, garantindo segurança e impacto visual.",
    "Stand In": "Substituto de ator usado durante preparação de iluminação e câmera, com físico similar ao ator principal.",
    
    # ===== STUNTS E EFEITOS ESPECIAIS =====
    "Stunt Coordinator": "Planeja e supervisiona todas as cenas de ação e sequências perigosas, garantindo segurança e impacto visual.",
    "Stunt Double": "Dublê que substitui ator em cenas perigosas ou que requerem habilidades físicas específicas.",
    "Stunt Driver": "Dublê especializado em direção de veículos em cenas de ação e perseguições.",
    "Stunts": "Profissional geral de dublagem que executa ações perigosas ou fisicamente exigentes.",
    "Utility Stunts": "Dublê versátil que executa diversos tipos de stunts conforme necessário.",
    "Special Effects": "Cria efeitos físicos práticos durante filmagens como explosões, chuva, neve e fumaça.",
    "Special Effects Coordinator": "Coordena todos os efeitos especiais práticos, planejando execução e garantindo segurança.",
    "Special Effects Supervisor": "Supervisiona departamento de efeitos especiais, gerenciando equipe e orçamento.",
    "Special Effects Technician": "Técnico que executa e opera efeitos especiais práticos no set.",
    "Special Effects Assistant": "Auxilia equipe de efeitos especiais em preparação e execução de efeitos práticos.",
    "Pyrotechnician": "Especialista em pirotecnia, criando e executando efeitos de fogo, explosões e fogos de artifício com segurança.",
    "Visual Effects": "Profissional geral de efeitos visuais digitais responsável por criação ou supervisão de VFX.",
    "Visual Effects Supervisor": "Coordena criação e integração de todos os efeitos visuais digitais do filme.",
    "Visual Effects Producer": "Produz efeitos visuais, gerenciando orçamento, cronograma e coordenação com estúdios de VFX.",
    "VFX Artist": "Artista digital que cria elementos de efeitos visuais usando software especializado.",
    "CG Supervisor": "Supervisiona criação de elementos em computação gráfica, coordenando artistas 3D e técnicos.",
    "Animation Director": "Dirige elementos animados do filme, supervisionando animadores e garantindo qualidade de movimento.",
    
    # ===== LOCAÇÕES =====
    "Location Manager": "Encontra e gerencia locações para filmagem, negociando permissões e coordenando logística.",
    "Location Coordinator": "Coordena aspectos práticos de filmagem em locações, lidando com logística e comunicação local.",
    
    # ===== STORYBOARD =====
    "Storyboard": "Profissional geral responsável por criação de storyboards visualizando cenas antes das filmagens.",
    "Storyboard Artist": "Artista que desenha storyboards, criando representações visuais sequenciais de cenas planejadas.",
    
    # ===== CRÉDITOS ESPECIAIS =====
    "Thanks": "Pessoa ou organização que recebe agradecimento especial por contribuição ou apoio ao filme.",
    "In Memory Of": "Dedicatória em memória de pessoa falecida que teve conexão significativa com o filme ou equipe.",
    "Military Consultant": "Consultor militar que garante autenticidade em aspectos militares, táticas e procedimentos.",
}


def seed_descricoes():
    """Preenche as descrições de TODAS as funções técnicas no banco de dados."""
    
    print("=" * 80)
    print("PREENCHIMENTO COMPLETO DE DESCRIÇÕES - FUNÇÕES TÉCNICAS")
    print("=" * 80)
    print()
    
    # Busca todas as funções técnicas
    funcoes = FuncaoTecnica.query.all()
    
    if not funcoes:
        print("❌ Nenhuma função técnica encontrada no banco de dados.")
        print("   Execute primeiro o seed de dados básicos.")
        return
    
    print(f"📝 Encontradas {len(funcoes)} funções técnicas no banco de dados")
    print(f"📚 Descrições disponíveis para {len(DESCRICOES_FUNCOES)} funções")
    print()
    
    atualizadas = 0
    nao_encontradas = []
    ja_tinham_descricao = 0
    
    for funcao in funcoes:
        if funcao.nome in DESCRICOES_FUNCOES:
            if funcao.descricao and funcao.descricao.strip():
                print(f"⏭️  {funcao.nome:45} - Já possui descrição")
                ja_tinham_descricao += 1
            else:
                funcao.descricao = DESCRICOES_FUNCOES[funcao.nome]
                print(f"✅ {funcao.nome:45} - Descrição adicionada")
                atualizadas += 1
        else:
            nao_encontradas.append(funcao.nome)
            print(f"⚠️  {funcao.nome:45} - Descrição não disponível")
    
    # Commit das alterações
    if atualizadas > 0:
        try:
            db.session.commit()
            print()
            print(f"💾 {atualizadas} descrições salvas no banco de dados com sucesso!")
        except Exception as e:
            db.session.rollback()
            print()
            print(f"❌ Erro ao salvar no banco de dados: {e}")
            return
    
    # Resumo
    print()
    print("=" * 80)
    print("✅ PREENCHIMENTO CONCLUÍDO!")
    print("=" * 80)
    print(f"Resumo:")
    print(f"  • {atualizadas} descrições adicionadas")
    print(f"  • {ja_tinham_descricao} já possuíam descrição")
    print(f"  • {len(nao_encontradas)} sem descrição disponível")
    print(f"  • {len(DESCRICOES_FUNCOES)} descrições no dicionário")
    print(f"  • {len(funcoes)} funções no banco de dados")
    
    if nao_encontradas:
        print()
        print("Funções sem descrição disponível:")
        for nome in sorted(nao_encontradas):
            print(f"  - {nome}")
        print()
        print("💡 Dica: Adicione descrições para estas funções editando o script")
        print("   ou manualmente via interface web em /funcao_tecnica/<id>/edit")
    
    # Estatísticas de cobertura
    cobertura = (len(DESCRICOES_FUNCOES) / len(funcoes) * 100) if funcoes else 0
    print()
    print(f"📊 Cobertura: {cobertura:.1f}% das funções têm descrição disponível")


if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        seed_descricoes()
