import os
import io
import re
import requests
from bs4 import BeautifulSoup
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# CONFIGURAÇÕES INICIAIS E CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Sistema Integrado de Imagens: Catálogo & E-commerce",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes globais e credenciais
SENHA_ECOMMERCE = "5588"
SENHA_ADM = "5588"
ARQUIVO_BARRA_PADRAO = "barra_institucional_foto_lote_ecommerce.jpg"

# Inicialização de variáveis globais de sessão
if "auth_ecom" not in st.session_state:
    st.session_state["auth_ecom"] = False

# ==============================================================================
# MÓDULO DE FONTES E RECURSOS DE SISTEMA
# ==============================================================================
def carregar_fonte(nome_fonte, tamanho):
    """
    Carrega fontes do sistema com fallback seguro para Linux/Windows/macOS.
    """
    caminhos_fontes = [
        # Linux (Geralmente no Streamlit Cloud / Debian)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        # Windows
        "arialbd.ttf",
        "arial.ttf",
        "calibrib.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    ]
    
    for caminho in caminhos_fontes:
        try:
            return ImageFont.truetype(caminho, int(tamanho))
        except (OSError, IOError):
            continue
            
    # Fallback caso nenhuma fonte TTF do sistema seja encontrada
    return ImageFont.load_default()

# ==============================================================================
# MÓDULO DE BUSCA E SCRAPING DE PRODUTOS
# ==============================================================================
def buscar_dados_produto(codigo):
    """
    Realiza scraping no site para resgatar o título e código sanitizado do produto.
    """
    codigo_limpo = str(codigo).strip()
    if not codigo_limpo:
        return {"titulo": "PRODUTO SEM CÓDIGO", "codigo": "0000"}

    # Exemplo de requisição configurada para scraping
    url = f"https://www.exemplo.com.br/busca?q={codigo_limpo}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Buscando por seletores comuns do e-commerce
            tag_titulo = soup.find("h1", class_=re.compile(r"product.*title|nome.*produto", re.I)) or soup.find("title")
            
            if tag_titulo:
                texto_bruto = tag_titulo.get_text().strip()
                # Limpa sufixos do título como " - Nome da Loja"
                nome_formatado = re.split(r"[-|–]", texto_bruto)[0].strip().upper()
                return {"titulo": nome_formatado, "codigo": codigo_limpo}
    except Exception:
        pass

    # Fallback genérico caso o site esteja offline ou o produto não seja encontrado
    return {"titulo": f"PRODUTO CÓDIGO {codigo_limpo}", "codigo": codigo_limpo}

# ==============================================================================
# MÓDULO DE PROCESSAMENTO AVANÇADO DE IMAGENS
# ==============================================================================
def encaixar_e_centralizar(img, largura_alvo, altura_alvo, cor_fundo="#FFFFFF"):
    """
    Ajusta a proporção da imagem (Crop/Cover) mantendo a centralização perfeita.
    """
    # Trata suporte para versões recentes e antigas do Pillow (LANCZOS)
    resample_filter = getattr(Image.Resampling, 'LANCZOS', getattr(Image, 'LANCZOS', Image.BICUBIC))

    # Converte imagem de entrada para RGBA
    img = img.convert("RGBA")
    
    largura_orig, altura_orig = img.size
    proporcao_orig = largura_orig / altura_orig
    proporcao_alvo = largura_alvo / altura_alvo

    if proporcao_orig > proporcao_alvo:
        nova_altura = altura_alvo
        nova_largura = int(nova_altura * proporcao_orig)
    else:
        nova_largura = largura_alvo
        nova_altura = int(nova_largura / proporcao_orig)

    img_redimensionada = img.resize((nova_largura, nova_altura), resample_filter)

    # Calculo do corte central
    left = (nova_largura - largura_alvo) // 2
    top = (nova_altura - altura_alvo) // 2
    right = left + largura_alvo
    bottom = top + altura_alvo

    return img_redimensionada.crop((left, top, right, bottom))

def quebrar_texto_por_largura(draw_ctx, texto, fonte, largura_maxima):
    """
    Divide o texto em várias linhas dinamicamente para não ultrapassar a margem.
    """
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

# ==============================================================================
# MENU LATERAL - NAVEGAÇÃO E REGRAS DE INTERFACE
# ==============================================================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/868/868206.png", width=80)
st.sidebar.title("Gerenciador Visual")
st.sidebar.markdown("---")

modulo_selecionado = st.sidebar.radio(
    "Selecione o Módulo de Trabalho:",
    ["📚 Módulo Catálogo", "🖼️ Conversão de Fotos E-commerce"],
    index=1
)

st.sidebar.markdown("---")

# ==============================================================================
# MÓDULO 1: CATÁLOGO DE PRODUTOS
# ==============================================================================
if modulo_selecionado == "📚 Módulo Catálogo":
    st.title("📚 Processamento de Fotos para Catálogo")
    st.write("Padronização individual e ajuste de resolução para catálogo impresso/digital.")

    st.sidebar.header("⚙️ Opções do Catálogo")
    cod_cat = st.sidebar.text_input("Código de Referência", value="CAT-001")
    fundo_cat = st.sidebar.color_picker("Cor do fundo da moldura", "#FFFFFF")
    tamanho_final = st.sidebar.select_slider(
        "Dimensão do Quadrado (px):",
        options=[600, 800, 1000, 1200],
        value=1000
    )

    file_cat = st.file_uploader("Selecione a Imagem do Produto", type=["jpg", "jpeg", "png"], key="upl_cat")

    if file_cat is not None:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Original Uploaded")
            img_original = Image.open(file_cat)
            st.image(img_original, use_container_width=True)

        with col2:
            st.subheader("Prévia do Processamento")
            img_processada = encaixar_e_centralizar(img_original, tamanho_final, tamanho_final, fundo_cat)
            st.image(img_processada, use_container_width=True)

            # Preparação de Download
            buf = io.BytesIO()
            img_processada.convert("RGB").save(buf, format="JPEG", quality=95)
            
            st.download_button(
                label=f"📥 Baixar Foto do Catálogo ({tamanho_final}x{tamanho_final})",
                data=buf.getvalue(),
                file_name=f"CATALOGO_{cod_cat}.jpg",
                mime="image/jpeg",
                type="primary"
            )

# ==============================================================================
# MÓDULO 2: E-COMMERCE (COMPOSIÇÃO EM LOTE - 3 FOTOS + BARRA)
# ==============================================================================
elif modulo_selecionado == "🖼️ Conversão de Fotos E-commerce":
    st.title("🖼️ Composição de Fotos E-commerce")
    st.write("Gera artes de produto compostas por 3 imagens e banner institucional informativo.")

    # --------------------------------------------------------------------------
    # VALIDAÇÃO DE AUTENTICAÇÃO
    # --------------------------------------------------------------------------
    if not st.session_state.get("auth_ecom", False):
        st.warning("🔒 Este módulo está protegido por senha de liberação.")
        col_sec1, col_sec2 = st.columns([2, 1])
        with col_sec1:
            pwd_ecom = st.text_input("Insira a senha do módulo (5588):", type="password", key="pwd_ecom_input")
        with col_sec2:
            st.write(" ")
            st.write(" ")
            if st.button("Autenticar Módulo", type="primary"):
                if pwd_ecom in [SENHA_ECOMMERCE, SENHA_ADM]:
                    st.session_state["auth_ecom"] = True
                    st.success("Módulo liberado com sucesso!")
                    st.rerun()
                else:
                    st.error("Senha inválida!")
        st.stop()

    # --------------------------------------------------------------------------
    # CONTROLES DO PAINEL LATERAL
    # --------------------------------------------------------------------------
    st.sidebar.header("⚙️ Configurações da Composição")
    cod_ecom = st.sidebar.text_input(
        "Código do Produto *", 
        help="Informe o código do item para buscar o título no banco do site."
    )

    st.sidebar.subheader("🎨 Customização de Cores e Fontes")
    bg_ecom_color = st.sidebar.color_picker("Cor de Fundo da Arte", "#FFFFFF")
    cor_texto_banner = st.sidebar.color_picker("Cor das Letras no Banner", "#1E1E1E")
    tam_fonte_banner = st.sidebar.slider("Tamanho da Fonte do Nome", 12, 32, 18)

    st.sidebar.subheader("📏 Divisórias e Bordas")
    exibir_linhas = st.sidebar.checkbox("Exibir Linhas Divisórias", value=True)
    cor_linha = st.sidebar.color_picker("Cor das Divisórias", "#D0D0D0")

    # --------------------------------------------------------------------------
    # CARREGAMENTO DE ARQUIVOS DE FOTO
    # --------------------------------------------------------------------------
    st.markdown("### 📤 Upload das Fotos do Produto")
    col_up1, col_up2, col_up3 = st.columns(3)

    with col_up1:
        st.markdown("**1. Foto Principal** *(Esquerda / Destaque)*")
        file_f1 = st.file_uploader("Upload Foto 1", type=["png", "jpg", "jpeg"], key="ecom_f1")
        
    with col_up2:
        st.markdown("**2. Foto Secundária** *(Topo Direito)*")
        file_f2 = st.file_uploader("Upload Foto 2", type=["png", "jpg", "jpeg"], key="ecom_f2")
        
    with col_up3:
        st.markdown("**3. Foto Detalhe** *(Meio Direito)*")
        file_f3 = st.file_uploader("Upload Foto 3", type=["png", "jpg", "jpeg"], key="ecom_f3")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # BOTÃO E RENDERIZAÇÃO DA ART
    # --------------------------------------------------------------------------
    if st.button("✨ Gerar Composição E-commerce", type="primary", use_container_width=True):
        if not file_f1 or not file_f2 or not file_f3:
            st.error("⚠️ É obrigatório enviar as 3 imagens para montar a composição.")
        elif not cod_ecom.strip():
            st.error("⚠️ Informe o Código do Produto no painel à esquerda.")
        else:
            with st.spinner("Consultando dados do produto e renderizando imagem em alta qualidade..."):
                # 1. Scraping dos dados
                dados_prod = buscar_dados_produto(cod_ecom.strip())
                nome_produto = dados_prod.get("titulo", f"PRODUTO {cod_ecom}").upper()
                codigo_produto = dados_prod.get("codigo", cod_ecom)

                # 2. Definição das Dimensões da Composição (Proporção HD 16:9)
                CANVAS_W = 1200
                CANVAS_H = 675
                HALF_W = CANVAS_W // 2  # 600px
                
                # Proporções da Coluna Direita (30% / 50% / 20%)
                H_RED = int(CANVAS_H * 0.30)          # 202px
                H_BLUE = int(CANVAS_H * 0.50)         # 338px
                H_YELLOW = CANVAS_H - H_RED - H_BLUE  # 135px (Barra do Rodapé)

                # 3. Tela Base (Canvas)
                ecom_canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), bg_ecom_color)

                # 4. Processamento da Foto 1 (Esquerda)
                img1 = Image.open(file_f1)
                box_f1 = encaixar_e_centralizar(img1, HALF_W, CANVAS_H, bg_ecom_color)
                ecom_canvas.paste(box_f1, (0, 0), box_f1)

                # 5. Processamento da Foto 2 (Topo Direito)
                img2 = Image.open(file_f2)
                box_f2 = encaixar_e_centralizar(img2, HALF_W, H_RED, bg_ecom_color)
                ecom_canvas.paste(box_f2, (HALF_W, 0), box_f2)

                # 6. Processamento da Foto 3 (Meio Direito)
                img3 = Image.open(file_f3)
                box_f3 = encaixar_e_centralizar(img3, HALF_W, H_BLUE, bg_ecom_color)
                ecom_canvas.paste(box_f3, (HALF_W, H_RED), box_f3)

                # 7. Montagem do Banner Institucional
                banner_y_pos = H_RED + H_BLUE
                resample_filter = getattr(Image.Resampling, 'LANCZOS', getattr(Image, 'LANCZOS', Image.BICUBIC))

                if os.path.exists(ARQUIVO_BARRA_PADRAO):
                    img_barra = Image.open(ARQUIVO_BARRA_PADRAO).convert("RGBA")
                    img_barra = img_barra.resize((HALF_W, H_YELLOW), resample_filter)
                else:
                    # Fallback com cor sólida amarela institucional
                    img_barra = Image.new("RGBA", (HALF_W, H_YELLOW), "#FBC02D")

                # Desenhar textos sobre o banner
                draw_barra = ImageDraw.Draw(img_barra)
                fonte_nome = carregar_fonte("bold", tam_fonte_banner)
                fonte_cod = carregar_fonte("bold", max(11, int(tam_fonte_banner * 0.75)))

                margem_x = 15
                largura_util = HALF_W - (margem_x * 2)
                
                # Quebra o nome em até 2 linhas
                linhas_nome = quebrar_texto_por_largura(draw_barra, nome_produto, fonte_nome, largura_util)[:2]

                y_texto = 12
                for linha in linhas_nome:
                    try:
                        bbox_l = draw_barra.textbbox((0, 0), linha, font=fonte_nome)
                        h_linha = bbox_l[3] - bbox_l[1]
                    except AttributeError:
                        h_linha = 15

                    draw_barra.text((margem_x, y_texto), linha, fill=cor_texto_banner, font=fonte_nome)
                    y_texto += h_linha + 4

                # Escreve o código
                txt_codigo_final = f"CÓDIGO: {codigo_produto}"
                draw_barra.text((margem_x, y_texto + 2), txt_codigo_final, fill=cor_texto_banner, font=fonte_cod)

                # Cole o banner na composição
                ecom_canvas.paste(img_barra, (HALF_W, banner_y_pos), img_barra)

                # 8. Linhas Divisórias de Acabamento (Opcional)
                if exibir_linhas:
                    draw_ecom = ImageDraw.Draw(ecom_canvas)
                    draw_ecom.line([(HALF_W, 0), (HALF_W, CANVAS_H)], fill=cor_linha, width=2)
                    draw_ecom.line([(HALF_W, H_RED), (CANVAS_W, H_RED)], fill=cor_linha, width=2)
                    draw_ecom.line([(HALF_W, banner_y_pos), (CANVAS_W, banner_y_pos)], fill=cor_linha, width=2)

                # --------------------------------------------------------------
                # EXIBIÇÃO E EXPORTAÇÃO DA IMAGEM FINAL
                # --------------------------------------------------------------
                st.subheader("📸 Resultado da Arte Finalizada")
                st.image(ecom_canvas, caption=f"Arte Gerada: {nome_produto} ({codigo_produto})", use_container_width=True)

                buffer_saida = io.BytesIO()
                ecom_canvas.convert("RGB").save(buffer_saida, format="JPEG", quality=95)

                st.download_button(
                    label="📥 Baixar Arte E-commerce (JPG HD)",
                    data=buffer_saida.getvalue(),
                    file_name=f"ECOM_{codigo_produto}.jpg",
                    mime="image/jpeg",
                    type="primary",
                    use_container_width=True
                )
