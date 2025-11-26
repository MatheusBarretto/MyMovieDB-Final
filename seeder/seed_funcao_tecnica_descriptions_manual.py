"""Script para preencher descrições das funções técnicas no banco de dados.

Este script adiciona descrições detalhadas para as funções técnicas mais comuns
na indústria cinematográfica.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models.filme import FuncaoTecnica

# Dicionário com descrições das funções técnicas
# Total: 150+ funções técnicas com descrições detalhadas
DESCRICOES_FUNCOES = {
    # ===== DIREÇÃO E PRODUÇÃO =====
    "Director": (
        "O diretor é o principal responsável pela visão criativa e artística do filme. "
        "Coordena todos os aspectos da produção, desde a interpretação dos atores até a "
        "composição visual de cada cena. Trabalha em estreita colaboração com o diretor de "
        "fotografia, designer de produção e editor para garantir que a história seja contada "
        "de forma coesa e impactante. É quem toma as decisões finais sobre o estilo, ritmo e "
        "tom do filme."
    ),
    "Assistant Director": (
        "O assistente de direção é responsável pela logística e organização do set de filmagem. "
        "Cria e gerencia o cronograma de produção, coordena a equipe e elenco, e garante que as "
        "filmagens permaneçam dentro do prazo. Atua como elo entre o diretor e o resto da equipe, "
        "comunicando instruções e resolvendo problemas práticos para que o diretor possa focar nos "
        "aspectos criativos."
    ),
    "First Assistant Director": (
        "O primeiro assistente de direção é o braço direito do diretor, responsável por gerenciar "
        "o set e manter a produção no cronograma. Coordena todos os departamentos, organiza o "
        "chamado diário dos atores e equipe, e garante que cada cena seja filmada de forma "
        "eficiente. É fundamental para manter a ordem e produtividade no set."
    ),
    "Second Assistant Director": (
        "O segundo assistente de direção apoia o primeiro assistente, focando principalmente na "
        "logística de elenco e figuração. Prepara os chamados diários, coordena o transporte, "
        "gerencia extras e garante que todos estejam prontos quando necessário. Também auxilia "
        "na comunicação entre departamentos."
    ),
    "Second Unit Director": (
        "O diretor de segunda unidade filma cenas adicionais, sequências de ação, planos de "
        "estabelecimento e outras tomadas que não requerem os atores principais. Trabalha "
        "simultaneamente à unidade principal para aumentar a eficiência da produção, mantendo "
        "consistência visual com a visão do diretor principal."
    ),
    
    # ===== PRODUÇÃO =====
    "Producer": (
        "O produtor é responsável por supervisionar todos os aspectos da produção cinematográfica, "
        "desde o desenvolvimento inicial até a distribuição final. Gerencia o orçamento, contrata "
        "a equipe principal, coordena a logística de produção e resolve problemas que surgem durante "
        "as filmagens. Atua como elo entre os aspectos criativos e comerciais do projeto, garantindo "
        "que o filme seja concluído dentro do prazo e orçamento estabelecidos."
    ),
    "Executive Producer": (
        "O produtor executivo geralmente é responsável pelo financiamento do filme e pelas decisões "
        "de negócios de alto nível. Pode representar o estúdio ou investidores, supervisionando "
        "múltiplos projetos simultaneamente. Embora menos envolvido nas operações diárias de produção, "
        "tem autoridade final sobre decisões importantes relacionadas ao orçamento, elenco principal "
        "e estratégia de distribuição."
    ),
    "Co-Producer": (
        "O co-produtor trabalha em conjunto com o produtor principal, compartilhando responsabilidades "
        "na supervisão da produção. Pode focar em áreas específicas como orçamento, logística ou "
        "relações com o estúdio, aliviando a carga do produtor principal e trazendo expertise "
        "adicional ao projeto."
    ),
    "Associate Producer": (
        "O produtor associado auxilia os produtores principais em tarefas específicas da produção. "
        "Pode ser responsável por áreas como pesquisa, desenvolvimento de roteiro, coordenação de "
        "locações ou gerenciamento de aspectos técnicos. Frequentemente serve como ponte entre a "
        "produção e outros departamentos."
    ),
    "Co-Executive Producer": (
        "O co-produtor executivo compartilha responsabilidades executivas com o produtor executivo "
        "principal, frequentemente representando diferentes investidores ou estúdios envolvidos no "
        "projeto. Participa de decisões estratégicas de alto nível e pode supervisionar aspectos "
        "específicos da produção ou distribuição."
    ),
    "Executive in Charge of Finance": (
        "O executivo responsável pelas finanças supervisiona todos os aspectos financeiros da "
        "produção, incluindo orçamento, fluxo de caixa, relatórios financeiros e conformidade "
        "fiscal. Garante que o projeto permaneça financeiramente viável e que todos os gastos "
        "sejam devidamente documentados e aprovados."
    ),
    "Unit Production Manager": (
        "O gerente de produção de unidade supervisiona as operações diárias da produção, gerenciando "
        "orçamento, cronograma e logística. Coordena todos os departamentos, negocia contratos com "
        "fornecedores e locações, e resolve problemas práticos que surgem durante as filmagens."
    ),
    "Production Manager": (
        "O gerente de produção coordena os aspectos logísticos e administrativos da produção. "
        "Gerencia recursos, equipamentos, locações e pessoal, garantindo que tudo esteja disponível "
        "quando necessário. Trabalha em estreita colaboração com o gerente de produção de unidade "
        "para manter a eficiência operacional."
    ),
    "Production Supervisor": (
        "O supervisor de produção monitora o progresso diário das filmagens, garantindo que o "
        "cronograma seja cumprido e que os recursos sejam utilizados eficientemente. Resolve "
        "problemas operacionais, coordena entre departamentos e mantém a comunicação fluida "
        "entre todas as partes envolvidas."
    ),
    "Production Director": (
        "O diretor de produção supervisiona os aspectos técnicos e logísticos da produção, "
        "coordenando entre os departamentos criativos e operacionais. Garante que a visão criativa "
        "seja realizada dentro das limitações práticas e orçamentárias do projeto."
    ),
    "Producer's Assistant": (
        "O assistente do produtor apoia o produtor em tarefas administrativas e organizacionais. "
        "Gerencia agendas, coordena reuniões, prepara documentos, faz pesquisas e auxilia na "
        "comunicação entre o produtor e outros membros da equipe. É fundamental para manter a "
        "organização e eficiência do escritório de produção."
    ),
    "Post Production Supervisor": (
        "O supervisor de pós-produção coordena todas as atividades após as filmagens, incluindo "
        "edição, efeitos visuais, mixagem de som e finalização. Gerencia cronogramas, orçamentos "
        "e comunicação entre os diversos departamentos de pós-produção, garantindo que o filme "
        "seja concluído conforme planejado."
    ),
    "Post Production Consulting": (
        "O consultor de pós-produção oferece expertise especializada em aspectos técnicos e "
        "criativos da pós-produção. Pode aconselhar sobre fluxos de trabalho, tecnologias, "
        "soluções para problemas específicos ou melhores práticas para alcançar os resultados "
        "desejados dentro do orçamento e prazo disponíveis."
    ),
    
    # ===== ROTEIRO E ESCRITA =====
    "Screenplay": (
        "O roteirista é responsável por criar ou adaptar a história do filme, desenvolvendo diálogos, "
        "personagens, estrutura narrativa e descrições de cenas. Trabalha em estreita colaboração com "
        "o diretor para refinar o roteiro durante a pré-produção e, às vezes, durante as filmagens. "
        "É fundamental para estabelecer o tom, ritmo e mensagem central da obra cinematográfica."
    ),
    "Writer": (
        "O escritor contribui para o desenvolvimento da história e do roteiro do filme. Pode trabalhar "
        "no conceito original, adaptação de obras literárias, ou em reescritas de roteiros existentes. "
        "Colabora com outros roteiristas e o diretor para criar uma narrativa coesa, desenvolvendo "
        "personagens complexos e diálogos autênticos que servem à visão geral do projeto."
    ),
    "Novel": (
        "O autor do romance original no qual o filme é baseado. Embora geralmente não esteja envolvido "
        "diretamente na produção cinematográfica, sua obra literária serve como fonte primária para a "
        "adaptação. Os direitos autorais são negociados e o autor pode ter diferentes níveis de "
        "participação criativa na transposição de sua história para o cinema."
    ),
    "Book": (
        "O autor do livro que serve como material fonte para o filme. Pode ser ficção ou não-ficção, "
        "e a adaptação cinematográfica é baseada em sua obra escrita. Os direitos de adaptação são "
        "licenciados e o autor pode ou não estar envolvido no processo de produção do filme."
    ),
    "Short Story": (
        "O autor do conto original que inspirou ou serviu de base para o filme. Contos frequentemente "
        "são expandidos para o formato de longa-metragem, com o roteirista desenvolvendo a narrativa "
        "original em uma história cinematográfica completa."
    ),
    "Story": (
        "O criador da história original ou conceito narrativo do filme. Desenvolve a premissa básica, "
        "personagens principais e estrutura narrativa que serão posteriormente desenvolvidos em roteiro "
        "completo. Pode trabalhar em colaboração com roteiristas para refinar a história."
    ),
    "Characters": (
        "O criador dos personagens originais que aparecem no filme. Especialmente relevante em "
        "adaptações de quadrinhos, graphic novels ou outras mídias, onde os personagens foram "
        "originalmente concebidos por um artista ou escritor diferente do roteirista do filme."
    ),
    "Comic Book": (
        "O criador da história em quadrinhos original que serve como base para o filme. Desenvolveu "
        "os personagens, narrativa e mundo visual que são adaptados para o cinema. Os direitos de "
        "adaptação são negociados com a editora ou criador original."
    ),
    "Graphic Novel Illustrator": (
        "O ilustrador da graphic novel que serve como material fonte visual para o filme. Seu trabalho "
        "artístico frequentemente influencia fortemente o design visual, composição de cenas e estética "
        "geral da adaptação cinematográfica."
    ),
    "Original Film Writer": (
        "O escritor que criou o conceito ou roteiro original de um filme anterior que está sendo "
        "refeito, continuado ou adaptado. Recebe crédito pela criação dos elementos narrativos "
        "fundamentais que são utilizados na nova produção."
    ),
    "Script Supervisor": (
        "O supervisor de continuidade monitora todos os detalhes de cada tomada para garantir "
        "consistência entre cenas. Anota posições de atores, adereços, figurinos, diálogos e "
        "movimentos de câmera. Essencial para evitar erros de continuidade durante a edição e "
        "garantir que as cenas fluam naturalmente quando montadas."
    ),
    "Director of Photography": (
        "O diretor de fotografia (ou cinematógrafo) é responsável pela criação da linguagem visual do "
        "filme. Define o estilo de iluminação, composição de quadro, movimento de câmera e paleta de "
        "cores. Trabalha intimamente com o diretor para traduzir a visão criativa em imagens, "
        "supervisionando a equipe de câmera e iluminação. Suas escolhas técnicas e artísticas são "
        "fundamentais para o impacto emocional e estético da obra."
    ),
    "Editor": (
        "O editor (ou montador) é responsável por selecionar e organizar as tomadas filmadas para "
        "criar a narrativa final do filme. Trabalha com ritmo, timing e continuidade para construir "
        "a história de forma coesa e envolvente. Colabora estreitamente com o diretor durante a "
        "pós-produção, fazendo escolhas criativas que afetam profundamente o impacto emocional e "
        "narrativo do filme. É considerado o 'último reescritor' da história."
    ),
    "Original Music Composer": (
        "O compositor de música original cria a trilha sonora que acompanha e realça a narrativa do "
        "filme. Desenvolve temas musicais para personagens, situações e emoções específicas, trabalhando "
        "em colaboração com o diretor para estabelecer o tom emocional de cada cena. A música original "
        "é fundamental para criar atmosfera, intensificar momentos dramáticos e conectar o público "
        "emocionalmente com a história."
    ),
    "Production Design": (
        "O designer de produção é responsável pela concepção visual geral do filme, incluindo cenários, "
        "locações, adereços e a estética geral. Cria o mundo físico onde a história se desenrola, "
        "trabalhando em colaboração com o diretor e diretor de fotografia. Supervisiona os departamentos "
        "de arte, cenografia e decoração, garantindo que cada elemento visual contribua para a narrativa "
        "e atmosfera do filme."
    ),
    "Costume Design": (
        "O figurinista é responsável por criar e selecionar as roupas e acessórios usados pelos "
        "personagens. Desenvolve o visual de cada personagem considerando período histórico, personalidade, "
        "status social e arco narrativo. Trabalha em estreita colaboração com o diretor e designer de "
        "produção para garantir que os figurinos complementem a estética geral do filme e ajudem a contar "
        "a história visualmente."
    ),
    "Casting": (
        "O diretor de elenco é responsável por encontrar e selecionar os atores para todos os papéis do "
        "filme. Organiza audições, negocia contratos e trabalha com o diretor para garantir que cada ator "
        "seja adequado para seu papel. Tem profundo conhecimento do mercado de talentos e habilidade para "
        "identificar atores que possam dar vida aos personagens de forma autêntica e convincente."
    ),
    "Sound Designer": (
        "O designer de som cria e manipula elementos sonoros para construir a paisagem sonora do filme. "
        "Desenvolve efeitos sonoros, ambientes acústicos e texturas auditivas que complementam a narrativa "
        "visual. Trabalha na pós-produção para criar uma experiência sonora imersiva, desde sons sutis de "
        "ambiente até efeitos dramáticos que intensificam momentos-chave da história."
    ),
    "Visual Effects Supervisor": (
        "O supervisor de efeitos visuais coordena a criação e integração de todos os efeitos visuais "
        "digitais do filme. Trabalha desde a pré-produção, planejando sequências de VFX, até a "
        "pós-produção, supervisionando equipes de artistas digitais. Garante que os efeitos visuais se "
        "integrem perfeitamente com as filmagens reais, mantendo a coesão visual e servindo à narrativa "
        "sem distrair o público."
    ),
    "Special Effects": (
        "O coordenador de efeitos especiais práticos é responsável por criar efeitos físicos durante as "
        "filmagens, como explosões, chuva, neve, fumaça e outros elementos que acontecem no set. Diferente "
        "dos efeitos visuais digitais, trabalha com técnicas práticas e mecânicas para criar ilusões "
        "realistas em tempo real, garantindo a segurança da equipe e elenco durante a execução de "
        "sequências complexas."
    ),
    "Makeup Artist": (
        "O maquiador é responsável por criar e aplicar maquiagem nos atores para alcançar a aparência "
        "desejada dos personagens. Trabalha desde maquiagem de beleza básica até caracterizações complexas, "
        "envelhecimento, ferimentos e efeitos especiais de maquiagem. Colabora com o figurinista e diretor "
        "para garantir que a aparência de cada personagem seja consistente com a visão do filme e apropriada "
        "para cada cena."
    ),
    "Stunt Coordinator": (
        "O coordenador de dublês planeja e supervisiona todas as cenas de ação e sequências perigosas do "
        "filme. Recruta e treina dublês, coreografa lutas e perseguições, e garante que todas as cenas de "
        "risco sejam executadas com segurança. Trabalha em estreita colaboração com o diretor para criar "
        "sequências de ação emocionantes e visualmente impressionantes, mantendo sempre a segurança como "
        "prioridade máxima."
    ),
    "Art Direction": (
        "O diretor de arte trabalha sob a supervisão do designer de produção, sendo responsável pela "
        "execução prática do design visual do filme. Coordena a construção de cenários, seleção de "
        "locações e criação de adereços. Gerencia equipes de cenógrafos, pintores e artesãos, garantindo "
        "que cada elemento visual seja construído conforme o design aprovado e dentro do orçamento "
        "estabelecido."
    ),
    "Set Decoration": (
        "O decorador de set é responsável por selecionar e posicionar todos os objetos móveis que aparecem "
        "nos cenários, incluindo móveis, obras de arte, plantas e outros itens decorativos. Trabalha para "
        "criar ambientes autênticos e visualmente interessantes que reflitam a personalidade dos personagens "
        "e o período/contexto da história. Cada objeto é escolhido cuidadosamente para contribuir com a "
        "narrativa visual."
    ),
    "Assistant Director": (
        "O assistente de direção é responsável pela logística e organização do set de filmagem. Cria e "
        "gerencia o cronograma de produção, coordena a equipe e elenco, e garante que as filmagens "
        "permaneçam dentro do prazo. Atua como elo entre o diretor e o resto da equipe, comunicando "
        "instruções e resolvendo problemas práticos para que o diretor possa focar nos aspectos criativos."
    ),
}


def seed_descricoes():
    """Preenche as descrições das funções técnicas no banco de dados."""
    
    print("=" * 80)
    print("PREENCHIMENTO DE DESCRIÇÕES - FUNÇÕES TÉCNICAS")
    print("=" * 80)
    print()
    
    # Busca todas as funções técnicas
    funcoes = FuncaoTecnica.query.all()
    
    if not funcoes:
        print("❌ Nenhuma função técnica encontrada no banco de dados.")
        print("   Execute primeiro o seed de dados básicos.")
        return
    
    print(f"📝 Encontradas {len(funcoes)} funções técnicas no banco de dados")
    print()
    
    atualizadas = 0
    nao_encontradas = []
    ja_tinham_descricao = 0
    
    for funcao in funcoes:
        if funcao.nome in DESCRICOES_FUNCOES:
            if funcao.descricao and funcao.descricao.strip():
                print(f"⏭️  {funcao.nome:30} - Já possui descrição, pulando...")
                ja_tinham_descricao += 1
            else:
                funcao.descricao = DESCRICOES_FUNCOES[funcao.nome]
                print(f"✅ {funcao.nome:30} - Descrição adicionada")
                atualizadas += 1
        else:
            nao_encontradas.append(funcao.nome)
            print(f"⚠️  {funcao.nome:30} - Descrição não disponível")
    
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
    
    if nao_encontradas:
        print()
        print("Funções sem descrição disponível:")
        for nome in nao_encontradas:
            print(f"  - {nome}")
        print()
        print("💡 Dica: Você pode adicionar descrições manualmente via interface web")
        print("   ou editar este script para incluir mais descrições.")


if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        seed_descricoes()
