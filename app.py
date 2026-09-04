import os
import io
import re
import requests
from bs4 import BeautifulSoup
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# Tenta carregar o Cropper para o ajuste estilo LinkedIn
try:
    from streamlit_cropper import st_cropper
    HAS_CROPPER = True
except ImportError:
    HAS_CROPPER = False

# ==============================================================================
# CONFIGURAÇÕES INICIAIS E DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Sistema Integrado de Imagens: Catálogo & E-commerce",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

SENHA_ECOMMERCE = "5588"
SENHA_ADM = "5588"
ARQUIVO_BARRA_PADRAO = "barra_institucional_foto_lote_ecommerce.jpg"

if "auth_ecom" not in st.session_state:
    st.session_state["auth_ecom"] = False

# ==============================================================================
# FUNÇÕES AUXILIARES DE FONTES E IMAGENS
# ==============================================================================
def carregar_fonte(nome_fonte, tamanho):
    """Carrega fontes do sistema com fallback seguro."""
    caminhos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arialbd.ttf", "arial.ttf"
    ]
    for c in caminhos:
        try:
            return ImageFont.truetype(c, int(tamanho))
        except (OSError, IOError):
            continue
    return ImageFont.load_default()

def encaixar_e_centralizar(img, largura_alvo, altura_alvo, cor_fundo="#FFFFFF"):
    """Centraliza a imagem ajustando sua dimensão."""
    resample_filter = getattr(Image.Resampling, 'LANCZOS', getattr(Image, 'LANCZOS', Image.BICUBIC))
    img = img.convert("RGBA")
    
    larg_orig, alt_orig = img.size
    ratio_orig = larg_orig / alt_orig
    ratio_alvo = largura_alvo / altura_alvo

    if ratio_orig > ratio_alvo:
        nova_alt = altura_alvo
        nova_larg = int(nova_alt * ratio_orig)
    else:
        nova_larg = largura_alvo
        nova_alt = int(nova_larg / ratio_orig)

    img_res = img.resize((nova_larg, nova_alt), resample_filter)

    left = (nova_larg - largura_alvo) // 2
    top = (nova_alt - altura_alvo) // 2
    right = left + largura_alvo
    bottom = top + altura_alvo

    return img_res.crop((left, top, right, bottom))

def quebrar_texto_por_largura(draw_ctx, texto, fonte, largura_maxima):
    """Quebra o texto em linhas para que não passe da margem."""
    palavras = texto.split()
    linhas = []
    linha_atual = []

    for palavra in palavras:
        teste = " ".join(linha_atual + [palavra])
        try:
            bbox = draw_ctx.textbbox((0, 0), teste, font=fonte)
            largura_teste = bbox[2] - bbox[0]
        except AttributeError:
            largura_teste = draw_ctx.textlength(teste, font=fonte)

        if largura_teste <= largura_maxima:
            linha_atual.append(palavra)
        else:
            if linha_atual:
                linhas.append(" ".join(linha_atual))
            linha_atual = [palavra]

    if linha_atual:
        linhas.append(" ".join(linha_atual))

    return linhas

def buscar_dados_produto(codigo):
    """Realiza o scraping no e-commerce buscando o título real do produto."""
    codigo_limpo = str(codigo).strip()
    if not codigo_limpo:
        return {"titulo": "PRODUTO SEM CÓDIGO", "codigo": "0000"}

    url = f"https://www.exemplo.com.br/busca?q={codigo_limpo}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            tag_titulo = (
                soup.find("h1", class_=re.compile(r"product|nome|titulo|name", re.I)) or 
                soup.find("h1") or 
                soup.find("title")
            )
            if tag_titulo:
                texto_bruto = tag_titulo.get_text().strip()
                nome_formatado = re.split(r"[-|–|]", texto_bruto)[0].strip().upper()
                if len(nome_formatado) > 3 and "BUSCA" not in nome_formatado:
                    return {"titulo": nome_formatado, "codigo": codigo_limpo}
    except Exception:
        pass

    return {"titulo": f"PRODUTO {codigo_limpo}", "codigo": codigo_limpo}

# ==============================================================================
# PAINEL LATERAL DE NAVEGAÇÃO
# ==============================================================================
st.sidebar.title("📌 Navegação")
modulo_selecionado = st.sidebar.radio(
    "Selecione o Módulo:",
    ["📚 Catálogo", "🖼️ Conversão de Fotos E-commerce"],
    index=1
)
st.sidebar.markdown("---")

# ==============================================================================
# MÓDULO 1: CATÁLOGO
# ==============================================================================
if modulo_selecionado == "📚 Catálogo":
    st.title("📚 Módulo de Catálogo")
    st.write("Gere imagens formatadas e enquadradas para o catálogo de produtos.")

    st.sidebar.header("⚙️ Configurações do Catálogo")
    cod_catalogo = st.sidebar.text_input("Código do Produto", value="CAT-001")
    bg_cat_color = st.sidebar.color_picker("Cor de Fundo", "#FFFFFF")
    tamanho_final = st.sidebar.select_slider("Tamanho da Imagem Quadrada (px):", options=[600, 800, 1000, 1200], value=1000)

    file_cat = st.file_uploader("Upload da Imagem do Produto", type=["png", "jpg", "jpeg"], key="cat_f1")

    if file_cat is not None:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("Foto Original")
            img_cat_raw = Image.open(file_cat)
            st.image(img_cat_raw, use_container_width=True)

        with col_c2:
            st.subheader("Prévia Processada")
            canvas_cat = encaixar_e_centralizar(img_cat_raw, tamanho_final, tamanho_final, bg_cat_color)
            st.image(canvas_cat, use_container_width=True)

            out_bytes_cat = io.BytesIO()
            canvas_cat.convert("RGB").save(out_bytes_cat, format="JPEG", quality=95)

            st.download_button(
                label=f"📥 Baixar Foto do Catálogo ({tamanho_final}x{tamanho_final})",
                data=out_bytes_cat.getvalue(),
                file_name=f"catalogo_{cod_catalogo}.jpg",
                mime="image/jpeg",
                type="primary",
                use_container_width=True
            )

# ==============================================================================
# MÓDULO 2: E-COMMERCE
# ==============================================================================
elif modulo_selecionado == "🖼️ Conversão de Fotos E-commerce":
    st.title("🖼️ Conversão de Fotos E-commerce")
    st.write("Monte a arte composta do produto com suporte a enquadramento/zoom manual.")

    if not st.session_state.get("auth_ecom", False):
        st.subheader("🔒 Acesso Restrito ao Módulo")
        pwd_ecom = st.text_input("Digite a Senha do Módulo (5588)", type="password", key="pwd_ecom_input")
        if st.button("Liberar Módulo E-commerce", type="primary"):
            if pwd_ecom in [SENHA_ECOMMERCE, SENHA_ADM]:
                st.session_state["auth_ecom"] = True
                st.success("Acesso autorizado!")
                st.rerun()
            else:
                st.error("Senha incorreta!")
        st.stop()

    st.sidebar.header("⚙️ Dados do Produto")
    cod_ecom = st.sidebar.text_input("Código do Produto *")
    bg_ecom_color = st.sidebar.color_picker("Cor de Fundo da Arte", "#FFFFFF")

    st.sidebar.subheader("🎨 Estilo do Banner")
    cor_texto_banner = st.sidebar.color_picker("Cor do Nome e Código", "#FFFFFF")
    tam_fonte_banner = st.sidebar.slider("Tamanho da Fonte", 12, 32, 18)

    st.markdown("### 📤 Upload e Ajuste de Zoom/Corte das Fotos")
    col_up1, col_up2, col_up3 = st.columns(3)

    img_cropped_1, img_cropped_2, img_cropped_3 = None, None, None

    with col_up1:
        st.markdown("**1. Foto Principal (Esquerda)**")
        f1 = st.file_uploader("Enviar Foto 1", type=["png", "jpg", "jpeg"], key="ecom_f1")
        if f1:
            img_raw_1 = Image.open(f1)
            if HAS_CROPPER:
                st.caption("Ajuste a caixa de corte (zoom/posição):")
                img_cropped_1 = st_cropper(img_raw_1, realtime_update=True, box_color="#00FF00", aspect_ratio=(600, 675), key="crop_f1")
            else:
                img_cropped_1 = img_raw_1

    with col_up2:
        st.markdown("**2. Foto Superior (Topo Dir.)**")
        f2 = st.file_uploader("Enviar Foto 2", type=["png", "jpg", "jpeg"], key="ecom_f2")
        if f2:
            img_raw_2 = Image.open(f2)
            if HAS_CROPPER:
                st.caption("Ajuste a caixa de corte (zoom/posição):")
                img_cropped_2 = st_cropper(img_raw_2, realtime_update=True, box_color="#00FF00", aspect_ratio=(600, 202), key="crop_f2")
            else:
                img_cropped_2 = img_raw_2

    with col_up3:
        st.markdown("**3. Foto Central (Meio Dir.)**")
        f3 = st.file_uploader("Enviar Foto 3", type=["png", "jpg", "jpeg"], key="ecom_f3")
        if f3:
            img_raw_3 = Image.open(f3)
            if HAS_CROPPER:
                st.caption("Ajuste a caixa de corte (zoom/posição):")
                img_cropped_3 = st_cropper(img_raw_3, realtime_update=True, box_color="#00FF00", aspect_ratio=(600, 338), key="crop_f3")
            else:
                img_cropped_3 = img_raw_3

    st.markdown("---")

    if st.button("✨ Criar Composição E-commerce", type="primary", use_container_width=True):
        if not img_cropped_1 or not img_cropped_2 or not img_cropped_3:
            st.error("Por favor, envie todas as 3 fotos antes de gerar.")
        elif not cod_ecom.strip():
            st.error("Informe o Código do Produto no painel lateral.")
        else:
            with st.spinner("Buscando dados e renderizando a composição..."):
                dados_prod = buscar_dados_produto(cod_ecom.strip())
                nome_produto = dados_prod.get("titulo", f"PRODUTO {cod_ecom}").upper()
                codigo_produto = dados_prod.get("codigo", cod_ecom)

                CANVAS_W = 1200
                CANVAS_H = 675
                HALF_W = CANVAS_W // 2

                ecom_canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), bg_ecom_color)

                box_f1 = encaixar_e_centralizar(img_cropped_1, HALF_W, CANVAS_H, bg_ecom_color)
                ecom_canvas.paste(box_f1, (0, 0), box_f1)

                H_RED = int(CANVAS_H * 0.30)
                H_BLUE = int(CANVAS_H * 0.50)
                H_YELLOW = CANVAS_H - H_RED - H_BLUE

                box_f2 = encaixar_e_centralizar(img_cropped_2, HALF_W, H_RED, bg_ecom_color)
                ecom_canvas.paste(box_f2, (HALF_W, 0), box_f2)

                box_f3 = encaixar_e_centralizar(img_cropped_3, HALF_W, H_BLUE, bg_ecom_color)
                ecom_canvas.paste(box_f3, (HALF_W, H_RED), box_f3)

                banner_y_pos = H_RED + H_BLUE
                resample_filter = getattr(Image.Resampling, 'LANCZOS', getattr(Image, 'LANCZOS', Image.BICUBIC))

                if os.path.exists(ARQUIVO_BARRA_PADRAO):
                    img_barra = Image.open(ARQUIVO_BARRA_PADRAO).convert("RGBA")
                    img_barra = img_barra.resize((HALF_W, H_YELLOW), resample_filter)
                else:
                    img_barra = Image.new("RGBA", (HALF_W, H_YELLOW), "#FBC02D")

                draw_barra = ImageDraw.Draw(img_barra)
                fonte_nome = carregar_fonte("bold", tam_fonte_banner)
                fonte_cod = carregar_fonte("bold", max(11, int(tam_fonte_banner * 0.75)))

                margem_x = 15
                largura_util = HALF_W - (margem_x * 2)
                linhas_nome = quebrar_texto_por_largura(draw_barra, nome_produto, fonte_nome, largura_util)[:2]

                y_texto = 35

                for linha in linhas_nome:
                    try:
                        bbox_l = draw_barra.textbbox((0, 0), linha, font=fonte_nome)
                        h_linha = bbox_l[3] - bbox_l[1]
                    except AttributeError:
                        h_linha = 15

                    draw_barra.text((margem_x, y_texto), linha, fill=cor_texto_banner, font=fonte_nome)
                    y_texto += h_linha + 4

                txt_codigo_final = f"CÓDIGO: {codigo_produto}"
                draw_barra.text((margem_x, y_texto + 2), txt_codigo_final, fill=cor_texto_banner, font=fonte_cod)

                ecom_canvas.paste(img_barra, (HALF_W, banner_y_pos), img_barra)

                st.subheader("📸 Imagem Gerada")
                st.image(ecom_canvas, caption=f"{nome_produto} - Código: {codigo_produto}", use_container_width=True)

                out_bytes = io.BytesIO()
                ecom_canvas.convert("RGB").save(out_bytes, format="JPEG", quality=95)

                st.download_button(
                    label="📥 Baixar Imagem Composta E-commerce (JPG)",
                    data=out_bytes.getvalue(),
                    file_name=f"ecommerce_{codigo_produto}.jpg",
                    mime="image/jpeg",
                    type="primary",
                    use_container_width=True
                )
