import os
import re
import textwrap
from io import BytesIO
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw

# Lista com os códigos das carnes para fazer as requisições
CODIGOS = [
    "24903",
    "32020",
    "35125",
    "18232",
    "35595",
    "12587",
    "12258",
    "35558",
    "23609",
]

# Configurações do Layout do Catálogo
LARGURA_CARD = 300
ALTURA_CARD = 390  # 300px foto + 90px para código e título
COLUNAS = 3
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def buscar_dados_produto(codigo_busca):
    """Busca Imagem (class 'img-produto'), Título (class 'card-title') e Código (class 'card-text small')."""
    url = f"https://www.fornecimentodireto.com.br/?busca={codigo_busca}"
    print(f"🔍 Buscando dados do código {codigo_busca}...")

    dados = {
        "codigo": codigo_busca,  # Valor padrão de fallback
        "titulo": "PRODUTO SEM TÍTULO",
        "img_url": None,
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")

            # 1. Extrai o Código do Produto (<p class="card-text small">)
            codigo_tag = soup.find("p", class_="card-text small")
            if codigo_tag:
                texto_codigo = codigo_tag.get_text(strip=True)
                # Utiliza expressão regular para extrair apenas os números (ex: "Código: 24903" -> "24903")
                numeros = re.findall(r"\d+", texto_codigo)
                if numeros:
                    dados["codigo"] = numeros[0]

            # 2. Extrai o Título (<h6 class="card-title">)
            titulo_tag = soup.find("h6", class_="card-title")
            if titulo_tag:
                dados["titulo"] = titulo_tag.get_text(strip=True)

            # 3. Extrai a Imagem (<img class="img-produto">)
            img_tag = soup.find("img", class_="img-produto")
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("src")
                if img_url:
                    if not img_url.startswith("http"):
                        img_url = (
                            "https://www.fornecimentodireto.com.br/"
                            + img_url.lstrip("/")
                        )
                    dados["img_url"] = img_url

            print(
                f"  └─ 🎯 Encontrado | Cód: {dados['codigo']} | Item: {dados['titulo']}"
            )
            return dados
        else:
            print(f"  └─ ❌ Erro HTTP {response.status_code}")

    except Exception as e:
        print(f"  └─ ❌ Erro ao conectar: {e}")

    return None


def baixar_imagem(url):
    """Baixa a imagem diretamente para a memória."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)).convert("RGB")
    except Exception as e:
        print(f"  └─ ❌ Erro ao baixar imagem: {e}")
    return None


def criar_catalogo():
    produtos_processados = []

    print("--- INICIANDO RASPAGEM DE DADOS ---")
    for codigo in CODIGOS:
        dados = buscar_dados_produto(codigo)
        if dados and dados["img_url"]:
            img = baixar_imagem(dados["img_url"])
            if img:
                dados["imagem"] = img
                produtos_processados.append(dados)

    if not produtos_processados:
        print(
            "\n❌ Nenhuma imagem foi baixada. O catálogo não pôde ser gerado."
        )
        return

    print(
        f"\n📸 {len(produtos_processados)} de {len(CODIGOS)} produtos processados com sucesso!"
    )
    print("🎨 Gerando a imagem final do catálogo...")

    # Calcula dimensões gerais
    total_itens = len(produtos_processados)
    linhas = (total_itens + COLUNAS - 1) // COLUNAS

    largura_total = COLUNAS * LARGURA_CARD
    altura_total = linhas * ALTURA_CARD

    # Cria a imagem do catálogo (fundo branco)
    catalogo = Image.new("RGB", (largura_total, altura_total), color="white")
    draw = ImageDraw.Draw(catalogo)

    for index, item in enumerate(produtos_processados):
        col = index % COLUNAS
        lin = index // COLUNAS

        x = col * LARGURA_CARD
        y = lin * ALTURA_CARD

        # Redimensiona e cola a foto do produto
        img_redimensionada = item["imagem"].resize((LARGURA_CARD, 300))
        catalogo.paste(img_redimensionada, (x, y))

        # Desenha a legenda do Código extraído do HTML
        texto_codigo = f"CÓDIGO: {item['codigo']}"
        draw.text((x + 10, y + 305), texto_codigo, fill="black")

        # Desenha o Título do Produto (com quebra de linha se necessário)
        linhas_titulo = textwrap.wrap(item["titulo"], width=32)
        y_texto = y + 325

        for linha in linhas_titulo[:2]:
            draw.text((x + 10, y_texto), linha, fill="#333333")
            y_texto += 18

    # Salva o arquivo final
    nome_arquivo = "catalogo_produtos.png"
    catalogo.save(nome_arquivo)
    print(
        f"\n✅ SUCESSO CONCLUÍDO! O catálogo foi gerado e salvo como '{nome_arquivo}'."
    )


if __name__ == "__main__":
    criar_catalogo()