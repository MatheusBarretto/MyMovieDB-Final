# Fonts Directory

Este diretório contém fontes TrueType (.ttf) usadas pela aplicação para geração de imagens.

## Fontes Suportadas

O `ImageProcessingService` procura por fontes neste diretório para uso em placeholders e outras imagens geradas dinamicamente.

### Arial (arial.ttf)

A fonte Arial é usada por padrão para gerar placeholders com texto.

**Onde obter:**
- Windows: Copie de `C:\Windows\Fonts\arial.ttf`
- Linux: Instale o pacote `ttf-mscorefonts-installer` ou copie de `/usr/share/fonts/`
- macOS: Copie de `/Library/Fonts/Arial.ttf`

**Como adicionar:**
```bash
# Windows
copy "C:\Windows\Fonts\arial.ttf" "app\static\fonts\arial.ttf"

# Linux/macOS
cp /usr/share/fonts/truetype/msttcorefonts/Arial.ttf app/static/fonts/arial.ttf
```

## Fallback

Se nenhuma fonte TrueType estiver disponível, a aplicação automaticamente fará fallback para a fonte padrão do PIL (`ImageFont.load_default()`).

## Licenciamento

**IMPORTANTE:** Certifique-se de ter a licença apropriada para incluir fontes em sua aplicação.

- Fontes do sistema (como Arial) são tipicamente protegidas por direitos autorais da Microsoft
- Para distribuição, considere usar fontes livres como:
  - **Roboto** (Apache License 2.0)
  - **Open Sans** (Apache License 2.0)
  - **Liberation Sans** (GPL + font exception)
  - **DejaVu Sans** (livre para uso)

## Adicionando Novas Fontes

Para usar outras fontes além de Arial:

1. Coloque o arquivo `.ttf` neste diretório
2. Atualize o código em `imageprocessing_service.py` para referenciar a nova fonte
3. Documente o uso e licença aqui

## .gitignore

Se você optar por **não** fazer commit das fontes (por questões de licenciamento), adicione ao `.gitignore`:

```
app/static/fonts/*.ttf
!app/static/fonts/README.md
```

E documente no README do projeto como os desenvolvedores devem obter as fontes necessárias.
