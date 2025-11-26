# Guia: Preencher Descrições das Funções Técnicas

Este guia explica como preencher as descrições das funções técnicas no banco de dados.

## 📋 Pré-requisitos

- Ambiente virtual ativado
- Banco de dados criado e migrations aplicadas
- Funções técnicas já cadastradas no banco

## 🚀 Como Executar

### 1. Ativar o ambiente virtual

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\activate.ps1
```

**Windows (CMD):**
```cmd
.\.venv\Scripts\activate
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### 2. Executar o script

```bash
python seeder/seed_funcao_tecnica_descriptions_manual.py
```

## 📝 O que o script faz

O script adiciona descrições detalhadas para as seguintes funções técnicas:

- **Director** - Diretor
- **Producer** - Produtor
- **Executive Producer** - Produtor Executivo
- **Screenplay** - Roteirista
- **Writer** - Escritor
- **Novel** - Autor do Romance Original
- **Director of Photography** - Diretor de Fotografia
- **Editor** - Editor/Montador
- **Original Music Composer** - Compositor de Música Original
- **Production Design** - Designer de Produção
- **Costume Design** - Figurinista
- **Casting** - Diretor de Elenco
- **Sound Designer** - Designer de Som
- **Visual Effects Supervisor** - Supervisor de Efeitos Visuais
- **Special Effects** - Efeitos Especiais Práticos
- **Makeup Artist** - Maquiador
- **Stunt Coordinator** - Coordenador de Dublês
- **Art Direction** - Diretor de Arte
- **Set Decoration** - Decorador de Set
- **Assistant Director** - Assistente de Direção

## ✅ Saída Esperada

```
================================================================================
PREENCHIMENTO DE DESCRIÇÕES - FUNÇÕES TÉCNICAS
================================================================================

📝 Encontradas 20 funções técnicas no banco de dados

✅ Director                      - Descrição adicionada
✅ Producer                      - Descrição adicionada
✅ Screenplay                    - Descrição adicionada
...

💾 15 descrições salvas no banco de dados com sucesso!

================================================================================
✅ PREENCHIMENTO CONCLUÍDO!
================================================================================
Resumo:
  • 15 descrições adicionadas
  • 0 já possuíam descrição
  • 5 sem descrição disponível
```

## 🔄 Comportamento do Script

- ✅ **Adiciona descrições** para funções que não têm
- ⏭️ **Pula funções** que já possuem descrição
- ⚠️ **Avisa** sobre funções sem descrição disponível
- 💾 **Salva tudo** em uma única transação

## 📝 Adicionar Mais Descrições

Para adicionar descrições de outras funções técnicas, edite o arquivo:

```
seeder/seed_funcao_tecnica_descriptions_manual.py
```

E adicione entradas no dicionário `DESCRICOES_FUNCOES`:

```python
DESCRICOES_FUNCOES = {
    "Nome da Função": (
        "Descrição detalhada da função técnica..."
    ),
    # Adicione mais aqui
}
```

## 🎯 Testar no Sistema

Após executar o script:

1. Acesse a página de detalhes de um filme
2. Clique em uma função técnica na seção "Equipe Técnica"
3. O modal abrirá mostrando a descrição

## 💡 Dicas

- Execute o script sempre que adicionar novas funções técnicas
- As descrições são em português brasileiro
- Você pode editar descrições manualmente via interface web em `/funcao_tecnica/<id>/edit`
- O script é seguro para executar múltiplas vezes (não duplica descrições)

## ⚠️ Solução de Problemas

### Erro: "Nenhuma função técnica encontrada"
- Execute primeiro o seed de dados: `python -m seeder.seed_data_into_app`

### Erro: "ModuleNotFoundError"
- Certifique-se de que o ambiente virtual está ativado
- Verifique se está no diretório raiz do projeto

### Erro ao salvar no banco
- Verifique se o banco de dados está acessível
- Confirme que as migrations foram aplicadas: `flask db upgrade`
