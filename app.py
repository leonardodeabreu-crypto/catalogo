import io
import os
import re
import time
import textwrap
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Gerador de Catálogo Promocional",
    page_icon="🥩",
    layout="wide",
)

st.title("🥩 Gerador de Catálogo Promocional")
st.write("Monte banners e catálogos profissionais com suporte a texturas e cabeçalhos em imagem.")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
LOGO_PATH = "logo_salvo.png"

OPCOES_CORES = {
    "Vermelho Oferta": "#D32F2F",
    "Amarelo Encarte": "#FBC02D",
    "Escuro Churrasco": "#1E1E1E",
    "Verde": "#2E7D32",
    "Azul": "#1976D2",
    "Laranja": "#E65100",
    "Cinza Claro": "#F0F2F5",
    "Branco": "#FFFFFF",
}


# ==========================================
# FUNÇÕES DE SCRAPING E UTILITÁRIOS
# ==========================================
def buscar_dados_produto(codigo_busca):
    url = f"https://www.fornecimentodireto.com.br/?busca={codigo_busca}"
    dados = {
        "codigo": codigo_busca,
        "titulo": f"PRODUTO {codigo_busca}",
        "img_url": None,
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")

            codigo_tag = soup.find("p", class_="card-text small")
            if codigo_tag:
                numeros = re.findall(r"\d+", codigo_tag.get_text(strip=True))
                if numeros:
                    dados["codigo"] = numeros[0]

            titulo_tag = soup.find("h6", class_="card-title")
            if titulo_tag:
                dados["titulo"] = titulo_tag.get_text(strip=True)

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

            return dados
    except Exception as e:
        st.error(f"Erro ao buscar código {codigo_busca}: {e}")

    return dados


def baixar_imagem(url):
    if not url:
        return None
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception:
        pass
    return None


def redimensionar_proporcional(img, max_w, max_h, fator_zoom=1.0):
    """Redimensiona mantendo a proporção exata, permitindo zoom controlado."""
    w_orig, h_orig = img.size
    fator_base = min(max_w / w_orig, max_h / h_orig)
    fator_final = fator_base * fator_zoom

    novo_w = int(w_orig * fator_final)
    novo_h = int(h_orig * fator_final)
    return img.resize((novo_w, novo_h), Image.Resampling.LANCZOS)


def desenhar_selo_no_card(draw, texto_desconto, card_x2, card_y1, cor_fundo="#E53935", cor_texto="white"):
    """Desenha a flag de desconto no canto superior direito do BOX BRANCO."""
    if not texto_desconto:
        return

    try:
        fonte_selo = ImageFont.truetype("arial.ttf", 13)
    except IOError:
        fonte_selo = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), texto_desconto, font=fonte_selo)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding_h = 8
    padding_v = 4
    selo_w = text_w + (padding_h * 2)
    selo_h = text_h + (padding_v * 2)

    margem_direita = 12
    margem_topo = 12

    x1 = card_x2 - margem_direita
    x0 = x1 - selo_w
    y0 = card_y1 + margem_topo
    y1 = y0 + selo_h

    draw.rectangle([x0, y0, x1, y1], fill=cor_fundo)
    draw.text((x0 + padding_h, y0 + padding_v - 1), texto_desconto, fill=cor_texto, font=fonte_selo)


def desenhar_texto_alinhado(draw, texto, y, cor, tamanho, alinhamento, x_inicio=270, x_fim=1170):
    if not texto.strip():
        return y

    try:
        fonte = ImageFont.truetype("arial.ttf", tamanho)
    except IOError:
        fonte = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), texto, font=fonte)
    largura_texto = bbox[2] - bbox[0]

    if alinhamento == "Esquerda":
        x = x_inicio
    elif alinhamento == "Centro":
        x = x_inicio + ((x_fim - x_inicio) - largura_texto) // 2
    else:  # Direita
        x = x_fim - largura_texto

    draw.text((x, y), texto, fill=cor, font=fonte)
    return y + (bbox[3] - bbox[1]) + 8


# ==========================================
# PAINEL LATERAL (CONTROLES)
# ==========================================
st.sidebar.header("🎨 1. Fundo do Catálogo (Background)")
tipo_fundo = st.sidebar.radio(
    "Escolha o Tipo de Fundo",
    ["Cor Sólida", "Imagem / Textura Personalizada (Madeira, etc.)"]
)

bg_custom_file = None
cor_fundo_catalogo = "#F0F2F5"

if tipo_fundo == "Cor Sólida":
    nome_cor = st.sidebar.selectbox("Cor do Fundo", list(OPCOES_CORES.keys()), index=6)
    cor_fundo_catalogo = OPCOES_CORES[nome_cor]
else:
    bg_custom_file = st.sidebar.file_uploader(
        "Upload de Textura/Imagem de Fundo",
        type=["png", "jpg", "jpeg"],
        help="Envie uma imagem de madeira, pedra ou textura para o fundo."
    )

st.sidebar.markdown("---")
st.sidebar.header("🖼️ 2. Cabeçalho (Topo do Catálogo)")

usar_banner_imagem = st.sidebar.checkbox(
    "Usar Imagem/Banner Pronto no Cabeçalho",
    value=False,
    help="Marque para enviar uma arte completa que substituirá o Logo e as Frases do Topo."
)

banner_header_file = None
frase_1, frase_2 = "", ""
alinh_1, cor_1, tam_1 = "Esquerda", "#D32F2F", 32
alinh_2, cor_2, tam_2 = "Esquerda", "#1E1E1E", 20

if usar_banner_imagem:
    banner_header_file = st.sidebar.file_uploader(
        "Upload do Banner do Cabeçalho",
        type=["png", "jpg", "jpeg"],
        help="Recomendado: Imagem retangular (ex: 1200x220px)."
    )
else:
    st.sidebar.subheader("Logotipo")
    logo_uploaded = st.sidebar.file_uploader("Enviar novo Logo", type=["png", "jpg", "jpeg"])

    if logo_uploaded:
        img_temp = Image.open(logo_uploaded)
        img_temp.save(LOGO_PATH)
        st.sidebar.success("✅ Novo logo salvo com sucesso!")

    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, width=100, caption="Logo Ativo")

    st.sidebar.subheader("Textos do Topo")
    frase_1 = st.sidebar.text_input("Frase Principal", "OFERTAS DA SEMANA")
    col_a, col_b, col_c = st.sidebar.columns(3)
    with col_a:
        alinh_1 = st.selectbox("Alinhamento #1", ["Esquerda", "Centro", "Direita"], index=0)
    with col_b:
        cor_1 = OPCOES_CORES[st.selectbox("Cor #1", list(OPCOES_CORES.keys()), index=0)]
    with col_c:
        tam_1 = st.slider("Tam #1", 16, 50, 32)

    frase_2 = st.sidebar.text_input("Slogan", "Preços Imbatíveis e Qualidade Garantida!")
    col_d, col_e, col_f = st.sidebar.columns(3)
    with col_d:
        alinh_2 = st.selectbox("Alinhamento #2", ["Esquerda", "Centro", "Direita"], index=0)
    with col_e:
        cor_2 = OPCOES_CORES[st.selectbox("Cor #2", list(OPCOES_CORES.keys()), index=2)]
    with col_f:
        tam_2 = st.slider("Tam #2", 12, 40, 20)

st.sidebar.markdown("---")
st.sidebar.header("📝 3. Rodapé")
frase_rodape = st.sidebar.text_input("Frase Rodapé", "Ofertas válidas enquanto durarem os estoques.")
col_g, col_h, col_i = st.sidebar.columns(3)
with col_g:
    alinh_r = st.selectbox("Alinhamento Rodapé", ["Esquerda", "Centro", "Direita"], index=1)
with col_h:
    cor_r = OPCOES_CORES[st.selectbox("Cor Rodapé", list(OPCOES_CORES.keys()), index=2)]
with col_i:
    tam_r = st.slider("Tam Rodapé", 12, 30, 16)

st.sidebar.markdown("---")
st.sidebar.header("🛒 4. Cadastro de Produtos")

zoom_porcentagem = st.sidebar.slider(
    "🔍 Zoom da Imagem do Produto",
    min_value=100,
    max_value=180,
    value=130,
    step=10,
    help="Aumenta proporcionalmente a imagem aproveitando o espaço em branco do card.",
)
fator_zoom = zoom_porcentagem / 100.0

num_produtos = st.sidebar.number_input("Quantidade de Produtos", min_value=1, max_value=15, value=9, step=1)

produtos_inputs = []
for i in range(num_produtos):
    col1, col2 = st.sidebar.columns([2, 2])
    with col1:
        cod = st.text_input(f"COD. #{i+1}", key=f"cod_{i}")
    with col2:
        desc = st.text_input(f"Selo Ex: 10% OFF", key=f"desc_{i}")

    if cod.strip():
        produtos_inputs.append({"codigo": cod.strip(), "desconto": desc.strip()})


# ==========================================
# MONTAGEM DA IMAGEM
# ==========================================
if st.button("🚀 Gerar Catálogo Final", type="primary"):
    if not produtos_inputs:
        st.warning("Por favor, insira pelo menos um código na barra lateral.")
    else:
        with st.spinner("Buscando dados e aplicando fundo e cabeçalho..."):
            produtos_carregados = []

            for item in produtos_inputs:
                dados = buscar_dados_produto(item["codigo"])
                img = baixar_imagem(dados["img_url"]) if dados else None

                if not img:
                    img = Image.new("RGBA", (300, 300), color=(230, 230, 230, 255))

                dados["imagem"] = img
                dados["desconto"] = item["desconto"]
                produtos_carregados.append(dados)
                time.sleep(0.1)

            total = len(produtos_carregados)

            cols = total if total <= 3 else 3
            linhas = (total + cols - 1) // cols

            LARGURA_MAX = 1200
            ALTURA_MAX = 1200
            ALTURA_CABECALHO = 220
            ALTURA_RODAPE = 60

            altura_area_produtos = ALTURA_MAX - ALTURA_CABECALHO - ALTURA_RODAPE

            largura_slot = LARGURA_MAX // cols
            altura_slot = altura_area_produtos // linhas

            # --- BASE DO CATÁLOGO (FUNDO / BACKGROUND) ---
            if "Personalizada" in tipo_fundo and bg_custom_file:
                bg_img = Image.open(bg_custom_file).convert("RGBA")
                catalogo = bg_img.resize((LARGURA_MAX, ALTURA_MAX), Image.Resampling.LANCZOS)
            else:
                catalogo = Image.new("RGBA", (LARGURA_MAX, ALTURA_MAX), color=cor_fundo_catalogo)

            draw = ImageDraw.Draw(catalogo)

            # --- 1. CABEÇALHO (MODO BANNER OU MODO TEXTO+LOGO) ---
            if usar_banner_imagem and banner_header_file:
                banner_img = Image.open(banner_header_file).convert("RGBA")
                banner_resized = banner_img.resize((LARGURA_MAX, ALTURA_CABECALHO - 15), Image.Resampling.LANCZOS)
                catalogo.paste(banner_resized, (0, 0), banner_resized)
            else:
                x_inicio_texto = 40
                if os.path.exists(LOGO_PATH):
                    logo_img = Image.open(LOGO_PATH).convert("RGBA")
                    logo_img.thumbnail((220, ALTURA_CABECALHO - 40))
                    catalogo.paste(
                        logo_img,
                        (30, (ALTURA_CABECALHO - logo_img.height) // 2 - 10),
                        logo_img,
                    )
                    x_inicio_texto = 270

                y_texto = 50
                y_texto = desenhar_texto_alinhado(
                    draw, frase_1.upper(), y_texto, cor_1, tam_1, alinh_1, x_inicio=x_inicio_texto
                )
                desenhar_texto_alinhado(
                    draw, frase_2, y_texto + 5, cor_2, tam_2, alinh_2, x_inicio=x_inicio_texto
                )

            draw.line([(30, ALTURA_CABECALHO - 15), (1170, ALTURA_CABECALHO - 15)], fill="#CCCCCC", width=2)

            # --- 2. CARDS ARREDONDADOS E PRODUTOS ---
            try:
                fonte_prod_titulo = ImageFont.truetype("arial.ttf", 13)
                fonte_prod_codigo = ImageFont.truetype("arial.ttf", 12)
            except IOError:
                fonte_prod_titulo = ImageFont.load_default()
                fonte_prod_codigo = ImageFont.load_default()

            padding_card = 12
            card_w = largura_slot - (padding_card * 2)
            card_h = altura_slot - (padding_card * 2)

            for idx, prod in enumerate(produtos_carregados):
                c = idx % cols
                l = idx // cols

                slot_x = c * largura_slot
                slot_y = ALTURA_CABECALHO + (l * altura_slot)

                card_x1 = slot_x + padding_card
                card_y1 = slot_y + padding_card
                card_x2 = card_x1 + card_w
                card_y2 = card_y1 + card_h

                # 1. Desenha o Card Branco
                draw.rounded_rectangle(
                    [card_x1, card_y1, card_x2, card_y2],
                    radius=14,
                    fill="white",
                    outline="#E0E0E0",
                    width=1,
                )

                # 2. CALCULAR TEXTOS DA PARTE INFERIOR
                char_limite = max(12, card_w // 11)
                titulos_wrapped = textwrap.wrap(prod["titulo"], width=char_limite)[:2]

                altura_titulos = len(titulos_wrapped) * 15
                y_texto_base = card_y2 - 14 - altura_titulos - 18
                y_cod = y_texto_base

                # Desenha Código
                texto_cod = f"COD: {prod['codigo']}"
                bbox_cod = draw.textbbox((0, 0), texto_cod, font=fonte_prod_codigo)
                w_cod = bbox_cod[2] - bbox_cod[0]
                x_cod = card_x1 + (card_w - w_cod) // 2
                draw.text((x_cod, y_cod), texto_cod, fill="#222222", font=fonte_prod_codigo)

                # Desenha Título
                y_t = y_cod + (bbox_cod[3] - bbox_cod[1]) + 4
                for t_linha in titulos_wrapped:
                    bbox_tit = draw.textbbox((0, 0), t_linha, font=fonte_prod_titulo)
                    w_tit = bbox_tit[2] - bbox_tit[0]
                    x_tit = card_x1 + (card_w - w_tit) // 2
                    draw.text((x_tit, y_t), t_linha, fill="#444444", font=fonte_prod_titulo)
                    y_t += 15

                # 3. REDIMENSIONAR E POSICIONAR A FOTO NA ÁREA RESTANTE
                area_foto_top = card_y1 + 10
                area_foto_bottom = y_cod - 8
                max_foto_h = area_foto_bottom - area_foto_top
                max_foto_w = card_w - 20

                img_p = redimensionar_proporcional(prod["imagem"], max_foto_w, max_foto_h, fator_zoom=fator_zoom)

                pos_x = card_x1 + (card_w - img_p.width) // 2
                pos_y = area_foto_top + (max_foto_h - img_p.height) // 2

                catalogo.paste(img_p, (pos_x, pos_y), img_p)

                # 4. DESENHA A FLAG DE DESCONTO NO CANTO SUPERIOR DIREITO DO CARD BRANCO
                if prod["desconto"]:
                    desenhar_selo_no_card(draw, prod["desconto"], card_x2, card_y1)

            # --- 3. RODAPÉ ---
            y_rodape = ALTURA_MAX - ALTURA_RODAPE + 10
            draw.line([(30, y_rodape - 5), (1170, y_rodape - 5)], fill="#CCCCCC", width=2)

            desenhar_texto_alinhado(
                draw, frase_rodape, y_rodape + 10, cor_r, tam_r, alinh_r, x_inicio=30, x_fim=1170
            )

            # --- EXIBIÇÃO FINAL ---
            catalogo_rgb = catalogo.convert("RGB")
            st.image(
                catalogo_rgb,
                caption="Resultado Final do Catálogo (1200x1200px)",
                use_container_width=True,
            )

            buf = io.BytesIO()
            catalogo_rgb.save(buf, format="PNG")
            byte_im = buf.getvalue()

            st.download_button(
                label="💾 Baixar Imagem Gerada (PNG)",
                data=byte_im,
                file_name="catalogo_promocional.png",
                mime="image/png",
            )