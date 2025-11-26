# Guia de Commits Convencionais

Todos os commits neste projeto devem seguir o seguinte formato:

```
<tipo> (<escopo>): <resumo curto>
<linha em branco>
[descrição mais longa opcional]
<linha em branco>
[BREAKING CHANGE opcional: descreva a mudança crítica]
```
## Tipos de commits

- **feat**: Introdução de uma nova funcionalidade.
- **fix**: Correção de um bug.
- **docs**: Alterações apenas na documentação.
- **style**: Mudanças de formatação ou estilo que **não** afetam o funcionamento do código  
  (ex.: espaçamento, vírgulas, ponto e vírgula, indentação).
- **refactor**: Alterações no código que **não corrigem bugs** nem **adicionam funcionalidades**  
  (ex.: melhoria na organização do código).
- **perf**: Mudanças que melhoram o desempenho.
- **test**: Adição ou correção de testes.
- **build**: Alterações que afetam o sistema de build ou dependências externas.
- **ci**: Alterações nos arquivos ou scripts de integração contínua (CI).
- **chore**: Alterações que **não afetam** código de produção  
  (ex.: atualização de dependências, ajustes em scripts internos).
- **revert**: Reversão de um commit anterior.

## Como escrever um bom resumo

- Seja curto e objetivo (máximo de 72 caracteres).
- Use verbos no infinitivo: “adicionar”, “corrigir”, “atualizar” etc.
- Sempre descreva **o que** foi alterado, **onde** e, se necessário, **por que**.

## Exemplos

```bash
feat (parser): adicionar suporte para parsing de arrays
fix (ui): corrigir alinhamento do botão
docs: atualizar README com instruções de uso
refactor: melhorar performance do processamento de dados
chore: atualizar dependências do projeto
feat!: enviar e-mail ao registrar usuário

BREAKING CHANGE: agora é necessário configurar um serviço de e-mail
