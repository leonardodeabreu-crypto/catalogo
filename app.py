import concurrent.futures
import io
import json
import os
import re
import textwrap
import time
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import streamlit as st

# ==========================================
# CONFIGURAÇÃO DA PÁGINA (DEVE SER O PRIMEIRO ST)
# ==========================================
st.set_page_config(
    page_title="Gerador de Catálogo Promocional",
    page_icon="🥩",
    layout="wide",
)

# Constantes e Configurações Globais
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}
ARQUIVO_CORES_JSON = "cores_banners.json"

# ==========================================
# FUNÇÕES DE SUPORTE E BANCO DE DADOS LOCAL
# ==========================================
def carregar_cores_banners():
    if os.path.exists(ARQUIVO_CORES_JSON):
        try:
            with open(ARQUIVO_CORES_JSON, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if not conteudo:
                    return {}
                return json.loads(conteudo)
        except Exception as e:
            print(f"[LOG AVISO] Erro ao carregar JSON de cores: {e}")
            return {}
    return {}

def salvar_cores_banners(cores_dict):
    try:
        with open(ARQUIVO_CORES_JSON, "w", encoding="utf-8") as f:
            json.dump(cores_dict, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[LOG AVISO] Erro ao salvar JSON de cores: {e}")

# ==========================================
# WEB SCRAPING - BUSCA DE PRODUTOS
# ==========================================
def buscar_dados_produto(codigo_busca):
    url = f"https://www.fornecimentodireto.com.br/?busca={codigo_busca}"
    dados = {
        "codigo": codigo_busca,
        "titulo": f"PRODUTO {codigo_busca}",
        "img_url": None,
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")

            # Busca código do produto
            codigo_tag = soup.find("p", class_="card-text small")
            if codigo_tag:
                numeros = re.findall(r"\d+", codigo_tag.get_text(strip=True))
                if numeros:
                    dados["codigo"] = numeros[0]

            # Busca título do produto
            titulo_tag = soup.find("h6", class_="card-title")
            if titulo_tag:
                dados["titulo"] = titulo_tag.get_text(strip=True).upper()

            cod_real = dados["codigo"]

            # LÓGICA ORIGINAL E SEGURA DE BUSCA DA IMAGEM
            card = soup.find("div", class_="card") or soup
            img_tag = card.find("img")

            if img_tag:
                url_encontrada = img_tag.get("src") or img_tag.get("data-src")
                
                # Garante que não estamos pegando ícones ou selos de marcas
                palavras_bloqueadas = ["logo", "icon", "banner", "loader", "marca", "brand", "selo", "flag"]
                
                if url_encontrada and not any(p in url_encontrada.lower() for p in palavras_bloqueadas):
                    url_limpa = re.sub(r"\?(width|height|w|h|dim)=\d+.*$", "", url_encontrada)
                    url_limpa = re.sub(r"/(120|270)x(120|270)/", "/", url_limpa)

                    if not url_limpa.startswith("http"):
                        url_limpa = (
                            "https://www.fornecimentodireto.com.br/"
                            + url_limpa.lstrip("/")
                        )

                    dados["img_url"] = url_limpa

            # Fallback seguro direto pelo CDN do fornecedor
            if not dados["img_url"]:
                dados["img_url"] = (
                    f"https://www.mercadoagora.com/arquivos/produtos/{cod_real}/1.jpg"
                )

    except Exception as e:
        # Usa print para evitar interrupções ou congelamento do Streamlit Cloud
        print(f"[LOG AVISO] Erro ao buscar produto {codigo_busca}: {e}")

    return dados

# ==========================================
# UTILITÁRIOS DE IMAGEM
# ==========================================
def baixar_imagem(url):
    if not url:
        return None
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"[LOG AVISO] Erro ao baixar imagem ({url}): {e}")
    return None

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# ==========================================
# PROCESSAMENTO DE CARD / PRODUTO INDIVIDUAL
# ==========================================
def gerar_card_produto(prod, cor_hex="#1E3A8A"):
    # Dimensões padrão do card do produto
    width, height = 400, 500
    card = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)

    cor_rgb = hex_to_rgb(cor_hex)

    # Borda decorativa do card
    draw.rectangle([5, 5, width - 5, height - 5], outline=cor_rgb, width=3)

    # Título do Produto
    try:
        font_titulo = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        font_preco = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        font_sub = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        font_titulo = ImageFont.load_default()
        font_preco = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Desenha Imagem do Produto
    img_prod = baixar_imagem(prod.get("img_url"))
    if img_prod:
        img_prod.thumbnail((260, 260))
        pos_x = (width - img_prod.width) // 2
        card.paste(img_prod, (pos_x, 80), img_prod if img_prod.mode == 'RGBA' else None)
    else:
        draw.text((width // 2, 180), "Sem Imagem", fill=(150, 150, 150), font=font_sub, anchor="mm")

    # Nome/Título do Produto
    titulo = prod.get("titulo", "PRODUTO SEM NOME")
    lines = textwrap.wrap(titulo, width=28)
    y_text = 360
    for line in lines[:2]:
        draw.text((width // 2, y_text), line, fill=(30, 30, 30), font=font_titulo, anchor="mm")
        y_text += 22

    # Bloco do Preço
    preco_de = prod.get("preco_de")
    preco_por = prod.get("preco_por", "0,00")

    if preco_de:
        draw.text((width // 2, 415), f"De: R$ {preco_de}", fill=(120, 120, 120), font=font_sub, anchor="mm")
        # Risca o preço antigo
        draw.line([(width // 2 - 40, 415), (width // 2 + 40, 415)], fill=(200, 0, 0), width=2)

    draw.text((width // 2, 455), f"R$ {preco_por}", fill=cor_rgb, font=font_preco, anchor="mm")

    return card

# ==========================================
# INTERFACE STREAMLIT PRINCIPAL
# ==========================================
def main():
    st.title("🥩 Gerador de Catálogo Promocional")
    st.markdown("Crie encartes e banners promocionais automaticamente a partir dos códigos dos produtos.")

    # Carrega preferências salvas
    cores_salvas = carregar_cores_banners()

    st.sidebar.header("⚙️ Configurações do Catálogo")
    cor_tema = st.sidebar.color_picker("Cor Principal dos Banners", "#1E3A8A")

    # Área de entrada dos produtos
    st.subheader("1. Inserir Códigos dos Produtos")
    codigos_input = st.text_area(
        "Digite os códigos dos produtos (um por linha ou separados por vírgula):",
        height=120,
        placeholder="Exemplo:\n12345\n67890\n11223"
    )

    if st.button("🔍 Buscar e Carregar Produtos", type="primary"):
        if not codigos_input.strip():
            st.warning("Por favor, digite ao menos um código de produto.")
            return

        # Extrai os códigos
        codigos = [c.strip() for c in re.split(r'[\n,]+', codigos_input) if c.strip()]
        
        st.info(f"Buscando dados para {len(codigos)} produtos em paralelo...")
        
        # Executa busca paralela (sem st.warning dentro para não congelar o servidor)
        produtos_encontrados = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            resultados = list(executor.map(buscar_dados_produto, codigos))
            produtos_encontrados = [r for r in resultados if r]

        st.session_state["produtos"] = produtos_encontrados
        st.success(f"{len(produtos_encontrados)} produtos carregados com sucesso!")

    # Exibição e Edição dos Produtos
    if "produtos" in st.session_state and st.session_state["produtos"]:
        st.divider()
        st.subheader("2. Ajustar Detalhes e Preços")

        prods_editados = []
        cols = st.columns(3)

        for idx, prod in enumerate(st.session_state["produtos"]):
            col = cols[idx % 3]
            with col:
                st.markdown(f"**Produto #{idx+1} (Cód: {prod['codigo']})**")
                
                # Imagem miniatura na interface
                if prod.get("img_url"):
                    st.image(prod["img_url"], width=120)
                else:
                    st.caption("Sem imagem")

                titulo = st.text_input(f"Título", value=prod.get("titulo", ""), key=f"tit_{idx}")
                p_de = st.text_input(f"Preço 'De' (opcional)", value="", key=f"pde_{idx}")
                p_por = st.text_input(f"Preço 'Por'", value="0,00", key=f"ppor_{idx}")

                prods_editados.append({
                    "codigo": prod["codigo"],
                    "titulo": titulo,
                    "img_url": prod.get("img_url"),
                    "preco_de": p_de,
                    "preco_por": p_por
                })

        st.divider()
        st.subheader("3. Gerar Imagens dos Cards")

        if st.button("🖼️ Gerar Imagens dos Produtos", type="primary"):
            st.info("Gerando imagens...")
            
            grid_cols = st.columns(3)
            for idx, prod in enumerate(prods_editados):
                card_img = gerar_card_produto(prod, cor_hex=cor_tema)
                
                # Converte para Bytes para Download
                buf = io.BytesIO()
                card_img.save(buf, format="PNG")
                byte_im = buf.getvalue()

                with grid_cols[idx % 3]:
                    st.image(byte_im, use_container_width=True)
                    st.download_button(
                        label=f"⬇️ Baixar #{prod['codigo']}",
                        data=byte_im,
                        file_name=f"card_produto_{prod['codigo']}.png",
                        mime="image/png",
                        key=f"dl_{idx}"
                    )

if __name__ == "__main__":
    main()
