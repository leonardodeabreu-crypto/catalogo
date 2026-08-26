import io
import json
import os
import re
import time
import urllib3
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import requests
import streamlit as st

# Desativa avisos de requisições HTTPS não verificadas (SSL)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Gerador de Catálogo Promocional",
    page_icon="🥩",
    layout="wide",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

SENHA_USUARIO = "2244"
SENHA_ADM = "9988"
ARQUIVO_CORES_JSON = "cores_banners.json"

# ==========================================
# GERENCIAMENTO DE CORES DOS BANNERS (ADM)
# ==========================================
def carregar_cores_banners():
    if os.path.exists(ARQUIVO_CORES_JSON):
        try:
            with open(ARQUIVO_CORES_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salvar_cores_banners(dict_cores):
    try:
        with open(ARQUIVO_CORES_JSON, "w", encoding="utf-8") as f:
            json.dump(dict_cores, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Erro ao salvar cores do ADM: {e}")

dict_cores_banners = carregar_cores_banners()

# ==========================================
# INICIALIZAÇÃO DA SESSÃO ISOLADA
# ==========================================
if "logo_bytes" not in st.session_state:
    st.session_state["logo_bytes"] = None

if "autenticado" not in st.session_state:
    if st.query_params.get("auth") == "ok":
        st.session_state["autenticado"] = True
    else:
        st.session_state["autenticado"] = False

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito")
    st.write("Digite a senha de acesso para utilizar o gerador de catálogos.")

    senha_digitada = st.text_input(
        "Senha de Acesso", type="password", max_chars=4
    )

    if st.button("Entrar"):
        if senha_digitada == SENHA_USUARIO or senha_digitada == SENHA_ADM:
            st.session_state["autenticado"] = True
            st.query_params["auth"] = "ok"
            st.success("Acesso liberado!")
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")

    st.stop()

# ==========================================
# GERENCIAMENTO DE FONTES
# ==========================================
OPCOES_FONTES = {
    "Impact (Encarte Forte)": [
        "Impact.ttf",
        "impact.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "Padrão Negrito (Liberation / Arial)": [
        "LiberationSans-Bold.ttf",
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ],
    "Moderna (Liberation Light / Arial)": [
        "LiberationSans-Regular.ttf",
        "arial.ttf",
        "DejaVuSans.ttf",
    ],
    "Condensada / Estreita": [
        "LiberationSansNarrow-Bold.ttf",
        "DejaVuSansCondensed-Bold.ttf",
    ],
}

def carregar_fonte(estilo_escolhido, tamanho):
    lista_fontes = OPCOES_FONTES.get(
        estilo_escolhido,
        ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"],
    )

    lista_fontes.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "arial.ttf",
    ])

    for nome_fonte in lista_fontes:
        try:
            return ImageFont.truetype(nome_fonte, int(tamanho))
        except (IOError, OSError):
            continue

    return ImageFont.load_default()

# ==========================================
# FUNÇÃO DE MARCA D'ÁGUA (PROTEÇÃO VAZAMENTO)
# ==========================================
def aplicar_marca_dagua(imagem_base, texto="PREÇO EXCLUSIVO COLABORADOR", opacidade=35, tamanho_fonte=28):
    largura, altura = imagem_base.size
    
    overlay = Image.new("RGBA", (largura * 2, altura * 2), (255, 255, 255, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    fonte = carregar_fonte("Impact (Encarte Forte)", tamanho_fonte)
    
    bbox = draw_overlay.textbbox((0, 0), texto, font=fonte)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    step_x = text_w + 80
    step_y = text_h + 60
    
    for y in range(0, altura * 2, step_y):
        for x in range(0, largura * 2, step_x):
            draw_overlay.text((x, y), texto, fill=(180, 0, 0, opacidade), font=fonte)
            
    overlay_rotacionado = overlay.rotate(30, expand=True)
    
    crop_x = (overlay_rotacionado.width - largura) // 2
    crop_y = (overlay_rotacionado.height - altura) // 2
    overlay_final = overlay_rotacionado.crop((crop_x, crop_y, crop_x + largura, crop_y + altura))
    
    return Image.alpha_composite(imagem_base.convert("RGBA"), overlay_final)

# ==========================================
# SCRAPING E AUXILIARES
# ==========================================
def buscar_dados_produto(codigo_busca):
    url = f"https://www.fornecimentodireto.com.br/?busca={codigo_busca}"
    dados = {
        "codigo": codigo_busca,
        "titulo": f"PRODUTO {codigo_busca}",
        "img_url": None,
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
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

            cod_real = dados["codigo"]

            img_tag = soup.find("img", class_="img-produto") or soup.find("img")
            if img_tag:
                url_encontrada = (
                    img_tag.get("data-src")
                    or img_tag.get("data-zoom-image")
                    or img_tag.get("src")
                )

                if url_encontrada and not url_encontrada.endswith("load.gif"):
                    url_limpa = re.sub(
                        r"\?(width|height|w|h|dim)=\d+.*$", "", url_encontrada
                    )
                    url_limpa = re.sub(r"/(120|270)x(120|270)/", "/", url_limpa)

                    if not url_limpa.startswith("http"):
                        url_limpa = (
                            "https://www.fornecimentodireto.com.br/"
                            + url_limpa.lstrip("/")
                        )

                    dados["img_url"] = url_limpa

            if not dados["img_url"]:
                dados["img_url"] = (
                    f"https://www.mercadoagora.com/arquivos/produtos/{cod_real}/1.jpg"
                )

            return dados
    except Exception as e:
        st.error(f"Erro ao buscar produto {codigo_busca}: {e}")

    return dados


def baixar_imagem(url):
    if not url:
        return None
    try:
        response = requests.get(url, headers=HEADERS, timeout=12, verify=False)
        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content))
            return img.convert("RGBA")
    except Exception:
        pass
    return None


def redimensionar_proporcional(img, max_w, max_h, fator_zoom=1.0):
    w_orig, h_orig = img.size
    fator_base = min(max_w / w_orig, max_h / h_orig)
    fator_final = fator_base * fator_zoom

    novo_w = max(1, int(w_orig * fator_final))
    novo_h = max(1, int(h_orig * fator_final))

    return img.resize((novo_w, novo_h), Image.Resampling.LANCZOS)


def criar_banner_com_blur(img_banner, larg_alvo, alt_alvo):
    bg_blur = img_banner.resize((larg_alvo, alt_alvo), Image.Resampling.LANCZOS)
    bg_blur = bg_blur.filter(ImageFilter.GaussianBlur(radius=25))

    img_fit = redimensionar_proporcional(img_banner, larg_alvo, alt_alvo)

    x_pos = (larg_alvo - img_fit.width) // 2
    y_pos = (alt_alvo - img_fit.height) // 2

    bg_blur.paste(img_fit, (x_pos, y_pos), img_fit)
    return bg_blur


def quebrar_texto_por_largura(draw, texto, fonte, largura_maxima):
    palavras = texto.split()
    if not palavras:
        return []

    linhas = []
    linha_atual = palavras[0]

    for palavra in palavras[1:]:
        test_line = linha_atual + " " + palavra
        bbox = draw.textbbox((0, 0), test_line, font=fonte)
        largura_teste = bbox[2] - bbox[0]
        if largura_teste <= largura_maxima:
            linha_atual = test_line
        else:
            linhas.append(linha_atual)
            linha_atual = palavra
    linhas.append(linha_atual)
    return linhas


def desenhar_selo_no_card(
    draw,
    texto_desconto,
    card_x2,
    card_y1,
    cor_fundo="#E53935",
    cor_texto="white",
    tam_fonte=13,
):
    if not texto_desconto:
        return

    tam_fonte_ampliado = int(tam_fonte * 1.30)
    fonte_selo = carregar_fonte("Padrão Negrito (Liberation / Arial)", tam_fonte_ampliado)

    bbox = draw.textbbox((0, 0), texto_desconto, font=fonte_selo)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding_h = max(10, int(tam_fonte_ampliado * 0.7))
    padding_v = max(5, int(tam_fonte_ampliado * 0.4))
    selo_w = text_w + (padding_h * 2)
    selo_h = text_h + (padding_v * 2)

    margem_direita = 12
    margem_topo = 12

    x1 = card_x2 - margem_direita
    x0 = x1 - selo_w
    y0 = card_y1 + margem_topo
    y1 = y0 + selo_h

    draw.rectangle([x0, y0, x1, y1], fill=cor_fundo)
    draw.text(
        (x0 + padding_h, y0 + padding_v - 1),
        texto_desconto,
        fill=cor_texto,
        font=fonte_selo,
    )


def desenhar_texto_alinhado(
    draw,
    texto,
    y,
    cor,
    tamanho,
    alinhamento,
    estilo_fonte="Padrão Negrito (Liberation / Arial)",
    x_inicio=270,
    x_fim=1170,
):
    if not texto.strip():
        return y

    fonte = carregar_fonte(estilo_fonte, tamanho)

    bbox = draw.textbbox((0, 0), texto, font=fonte)
    largura_texto = bbox[2] - bbox[0]

    if alinhamento == "Esquerda":
        x = x_inicio
    elif alinhamento == "Centro":
        x = x_inicio + ((x_fim - x_inicio) - largura_texto) // 2
    else:
        x = x_fim - largura_texto

    draw.text((x, y), texto, fill=cor, font=fonte)
    return y + (bbox[3] - bbox[1]) + 8

def tratar_e_desenhar_preco(
    draw, texto_preco, x_min, x_max, center_y, cor_preco, tamanho_base, estilo_fonte
):
    if not texto_preco or not texto_preco.strip():
        return

    val_limpo = texto_preco.strip().replace("R$", "").replace(" ", "").replace(".", ",")
    if "," in val_limpo:
        partes = val_limpo.split(",")
        inteiro = partes[0]
        centavos = partes[1][:2].ljust(2, "0")
    else:
        inteiro = val_limpo
        centavos = "00"

    txt_rs = "R$"
    txt_int = f" {inteiro},"
    txt_cent = centavos

    tam_rs = int(tamanho_base * 0.50)
    tam_int = int(tamanho_base)
    tam_cent = int(tamanho_base * 0.50)

    fonte_rs = carregar_fonte(estilo_fonte, tam_rs)
    fonte_int = carregar_fonte(estilo_fonte, tam_int)
    fonte_cent = carregar_fonte(estilo_fonte, tam_cent)

    bbox_rs = draw.textbbox((0, 0), txt_rs, font=fonte_rs)
    bbox_int = draw.textbbox((0, 0), txt_int, font=fonte_int)
    bbox_cent = draw.textbbox((0, 0), txt_cent, font=fonte_cent)

    w_rs = bbox_rs[2] - bbox_rs[0]
    w_int = bbox_int[2] - bbox_int[0]
    w_cent = bbox_cent[2] - bbox_cent[0]

    w_total = w_rs + w_int + w_cent
    largura_disponivel = x_max - x_min

    if w_total > largura_disponivel and tamanho_base > 10:
        fator_reducao = largura_disponivel / w_total
        novo_tam = max(8, int(tamanho_base * fator_reducao))
        return tratar_e_desenhar_preco(
            draw,
            texto_preco,
            x_min,
            x_max,
            center_y,
            cor_preco,
            novo_tam,
            estilo_fonte,
        )

    start_x = x_min + max(0, (largura_disponivel - w_total) // 2)

    h_int = bbox_int[3] - bbox_int[1]
    base_y = center_y + (h_int // 2)

    # R$
    y_rs = base_y - (bbox_rs[3] - bbox_rs[1]) - 2
    draw.text((start_x, y_rs), txt_rs, fill=cor_preco, font=fonte_rs)

    # Inteiro + Vírgula
    x_int = start_x + w_rs
    y_int = base_y - h_int
    draw.text((x_int, y_int), txt_int, fill=cor_preco, font=fonte_int)

    # Centavos
    x_cent = x_int + w_int
    y_cent = y_int + 2
    draw.text((x_cent, y_cent), txt_cent, fill=cor_preco, font=fonte_cent)

# ==========================================
# PAINEL LATERAL
# ==========================================
st.title("🥩 Gerador de Catálogo Promocional")
st.write("Monte banners e catálogos profissionais com fotos limpas dos produtos!")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state["autenticado"] = False
    if "auth" in st.query_params:
        del st.query_params["auth"]
    st.rerun()

arquivos_banners = []
for f in os.listdir("."):
    if f.lower().startswith("banner") and f.lower().endswith((".png", ".jpg", ".jpeg")):
        arquivos_banners.append(f)

if os.path.exists("banners") and os.path.isdir("banners"):
    for f in os.listdir("banners"):
        if f.lower().endswith((".png", ".jpg", ".jpeg")):
            arquivos_banners.append(os.path.join("banners", f))

arquivos_banners = sorted(list(set(arquivos_banners)))

st.sidebar.header("📐 Formato do Encarte")
opcao_formato = st.sidebar.selectbox(
    "Escolha a Proporção da Arte",
    ["Quadrado / Feed / A4 (1200x1200px)", "Stories / Celular (1080x1920px)"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Proteção & Marca D'água")

ativar_marca_dagua = st.sidebar.checkbox("Ativar Marca D'água Anti-Vazamento", value=True)
if ativar_marca_dagua:
    texto_marca_dagua = st.sidebar.text_input("Texto da Marca D'água", "PREÇO EXCLUSIVO COLABORADOR")
    opacidade_marca = st.sidebar.slider("Opacidade da Marca D'água", 10, 100, 35)
else:
    texto_marca_dagua = ""
    opacidade_marca = 35

st.sidebar.markdown("---")
st.sidebar.header("🖼️ 1. Cabeçalho (Topo do Catálogo)")

opcoes_cabecalho = ["Nenhum (Usar Logo e Frases)", "📤 Upload Manual de Banner"]
if arquivos_banners:
    opcoes_cabecalho.extend([f"📁 {os.path.basename(b)}" for b in arquivos_banners])

opcao_banner_selecionada = st.sidebar.selectbox(
    "Escolha o Modelo do Cabeçalho", opcoes_cabecalho, index=0
)

banner_imagem_ativa = None
nome_banner_atual = None

if opcao_banner_selecionada == "📤 Upload Manual de Banner":
    uploaded_banner = st.sidebar.file_uploader(
        "Upload do Banner do Cabeçalho",
        type=["png", "jpg", "jpeg"],
        help="Recomendado: Imagem retangular (ex: 1200x220px).",
    )
    if uploaded_banner:
        banner_imagem_ativa = Image.open(uploaded_banner).convert("RGBA")
        st.sidebar.image(banner_imagem_ativa, caption="🔍 Pré-visualização do Banner", use_container_width=True)

elif opcao_banner_selecionada.startswith("📁 "):
    nome_banner_atual = opcao_banner_selecionada.replace("📁 ", "")
    caminho_banner = None
    for b_path in arquivos_banners:
        if os.path.basename(b_path) == nome_banner_atual:
            caminho_banner = b_path
            break

    if caminho_banner and os.path.exists(caminho_banner):
        banner_imagem_ativa = Image.open(caminho_banner).convert("RGBA")
        st.sidebar.image(banner_imagem_ativa, caption=f"Banner: {nome_banner_atual}", use_container_width=True)

OPCOES_CORES = {
    "Azul": "#0038A8",
    "Vermelho Oferta": "#D32F2F",
    "Amarelo Encarte": "#FBC02D",
    "Escuro Churrasco": "#1E1E1E",
    "Verde": "#2E7D32",
    "Laranja": "#E65100",
    "Cinza Escuro": "#444444",
    "Cinza Claro": "#F0F2F5",
    "Branco": "#FFFFFF",
    "Transparente / Nenhum": "TRANSPARENTE",
    "🎨 Usar Hexadecimal Personalizado": "CUSTOM"
}

if banner_imagem_ativa is None:
    st.sidebar.subheader("Logotipo")
    logo_uploaded = st.sidebar.file_uploader("Enviar novo Logo", type=["png", "jpg", "jpeg"])
    if logo_uploaded:
        st.session_state["logo_bytes"] = logo_uploaded.getvalue()
        st.sidebar.success("✅ Novo logo salvo na sua sessão!")

    if st.session_state["logo_bytes"] is not None:
        st.sidebar.image(st.session_state["logo_bytes"], width=100, caption="Logo Ativo")

    st.sidebar.subheader("Textos do Topo")
    frase_1 = st.sidebar.text_input("Frase Principal", "OFERTAS DA SEMANA")
    fonte_1 = st.sidebar.selectbox("Estilo Fonte Título", list(OPCOES_FONTES.keys()), index=1)
    col_a, col_b, col_c = st.sidebar.columns(3)
    with col_a:
        alinh_1 = st.selectbox("Alinhamento #1", ["Esquerda", "Centro", "Direita"], index=0)
    with col_b:
        cor_1 = OPCOES_CORES[st.selectbox("Cor #1", list(OPCOES_CORES.keys()), index=0)]
    with col_c:
        tam_1 = st.slider("Tam #1", 16, 60, 34)

    st.sidebar.markdown("---")
    frase_2 = st.sidebar.text_input("Slogan / Subtítulo", "Preços Imbatíveis e Qualidade Garantida!")
    fonte_2 = st.sidebar.selectbox("Estilo Fonte Slogan", list(OPCOES_FONTES.keys()), index=2)
    col_d, col_e, col_f = st.sidebar.columns(3)
    with col_d:
        alinh_2 = st.selectbox("Alinhamento #2", ["Esquerda", "Centro", "Direita"], index=0)
    with col_e:
        cor_2 = OPCOES_CORES[st.selectbox("Cor #2", list(OPCOES_CORES.keys()), index=3)]
    with col_f:
        tam_2 = st.slider("Tam #2", 12, 40, 20)

st.sidebar.markdown("---")
st.sidebar.header("🎨 2. Fundo do Catálogo (Background)")
tipo_fundo = st.sidebar.radio("Escolha o Tipo de Fundo", ["Cor Sólida / Hexadecimal", "Imagem / Textura Personalizada (Madeira, etc.)"])
bg_custom_file = None

cor_padrao_adm = "#F0F2F5"
if nome_banner_atual and nome_banner_atual in dict_cores_banners:
    cor_padrao_adm = dict_cores_banners[nome_banner_atual]

if tipo_fundo == "Cor Sólida / Hexadecimal":
    cor_fundo_catalogo = st.sidebar.color_picker("Escolha ou Cole a Cor Hexadecimal (#HEX)", value=cor_padrao_adm)
else:
    bg_custom_file = st.sidebar.file_uploader("Upload de Textura/Imagem de Fundo", type=["png", "jpg", "jpeg"])

# AREA ADM
st.sidebar.markdown("---")
with st.sidebar.expander("🔑 Área do Administrador (Cores de Banners)"):
    senha_adm_input = st.text_input("Senha Mestra do ADM", type="password", key="input_senha_adm")
    if senha_adm_input == SENHA_ADM:
        st.success("🔓 Acesso ADM Liberado!")
        if arquivos_banners:
            banner_para_config = st.selectbox("Selecione o Banner para Fixar Cor", [os.path.basename(b) for b in arquivos_banners], key="select_banner_adm")
            cor_atual_adm = dict_cores_banners.get(banner_para_config, "#F0F2F5")
            nova_cor_hex = st.text_input("Cor Hexadecimal Fixa (#HEX)", value=cor_atual_adm, key="input_hex_adm")
            if st.button("💾 Salvar Cor Fixa no Servidor"):
                dict_cores_banners[banner_para_config] = nova_cor_hex.strip().upper()
                salvar_cores_banners(dict_cores_banners)
                st.success(f"Cor {nova_cor_hex} vinculada ao banner {banner_para_config}!")
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📝 3. Rodapé")
frase_rodape = st.sidebar.text_input("Frase Rodapé", "Ofertas válidas enquanto durarem os estoques.")
fonte_r = st.sidebar.selectbox("Estilo Fonte Rodapé", list(OPCOES_FONTES.keys()), index=1)
col_g, col_h, col_i = st.sidebar.columns(3)
with col_g:
    alinh_r = st.selectbox("Alinhamento Rodapé", ["Esquerda", "Centro", "Direita"], index=1)
with col_h:
    cor_r = OPCOES_CORES[st.selectbox("Cor Rodapé", list(OPCOES_CORES.keys()), index=3)]
with col_i:
    tam_r = st.slider("Tam Rodapé", 12, 30, 16)

st.sidebar.markdown("---")
st.sidebar.header("🏷️ Configurações Globais do Preço")

sel_cor_preco = st.sidebar.selectbox("Cor do Preço", list(OPCOES_CORES.keys()), index=0)
if OPCOES_CORES[sel_cor_preco] == "CUSTOM":
    cor_preco_final = st.sidebar.text_input("Hexadecimal da Cor do Preço (#HEX)", "#0038A8")
else:
    cor_preco_final = OPCOES_CORES[sel_cor_preco]

tamanho_preco_opcao = st.sidebar.select_slider("Tamanho do Preço", options=["Pequeno", "Médio", "Grande"], value="Grande")
fonte_preco = st.sidebar.selectbox("Estilo de Fonte do Preço", list(OPCOES_FONTES.keys()), index=0)

st.sidebar.markdown("---")
st.sidebar.header("🛒 4. Cadastro de Produtos")

tam_descricao_custom = st.sidebar.slider("🔤 Tamanho da Descrição do Produto", min_value=10, max_value=36, value=14, step=1)
formatar_caixa_alta = st.sidebar.checkbox("Usar Caixa Alta (MAIÚSCULAS)", value=True)

sel_cor_texto_desc = st.sidebar.selectbox("Cor do Texto da Descrição", list(OPCOES_CORES.keys()), index=8)
if OPCOES_CORES[sel_cor_texto_desc] == "CUSTOM":
    cor_texto_desc = st.sidebar.text_input("Hexadecimal da Cor do Texto (#HEX)", "#FFFFFF")
else:
    cor_texto_desc = OPCOES_CORES[sel_cor_texto_desc]

sel_cor_box_desc = st.sidebar.selectbox("Cor do Box da Descrição (Fundo)", list(OPCOES_CORES.keys()), index=0)
if OPCOES_CORES[sel_cor_box_desc] == "CUSTOM":
    cor_box_desc = st.sidebar.text_input("Hexadecimal do Box (#HEX)", "#0038A8")
else:
    cor_box_desc = OPCOES_CORES[sel_cor_box_desc]

col_pad1, col_pad2 = st.sidebar.columns(2)
with col_pad1:
    padding_h_desc = st.number_input("Padding Esq/Direita (px)", min_value=3, max_value=30, value=6)
with col_pad2:
    padding_v_desc = st.number_input("Padding Top/Base (px)", min_value=0, max_value=20, value=4)

zoom_porcentagem = st.sidebar.slider("🔍 Zoom da Imagem do Produto", min_value=100, max_value=200, value=100, step=10)
fator_zoom = zoom_porcentagem / 100.0

OPCOES_QUANTIDADE = [1, 2, 3, 6, 9, 12, 16]
num_produtos = st.sidebar.selectbox("Quantidade de Produtos", OPCOES_QUANTIDADE, index=3)

produtos_inputs = []
for i in range(num_produtos):
    st.sidebar.markdown(f"**Produto #{i+1}**")
    col1, col2 = st.sidebar.columns([2, 2])
    with col1:
        cod = st.text_input(f"COD. #{i+1}", key=f"cod_{i}")
    with col2:
        desc = st.text_input(f"Selo Ex: 10% OFF", key=f"desc_{i}")

    col3, col4 = st.sidebar.columns([2, 2])
    with col3:
        preco_val = st.text_input(f"Preço (ex: 57,90)", key=f"preco_{i}")
    with col4:
        val = st.text_input(f"Validade", key=f"val_{i}")

    if cod.strip():
        produtos_inputs.append({
            "codigo": cod.strip(),
            "desconto": desc.strip(),
            "validade": val.strip(),
            "preco": preco_val.strip(),
            "cod_parana": "",
        })

st.sidebar.markdown("---")
modo_parana = st.sidebar.checkbox("🌲 Modo Paraná (Substituir Códigos)", value=False)

if modo_parana and produtos_inputs:
    st.sidebar.subheader("🔑 Códigos do Paraná (PR)")
    for idx, prod in enumerate(produtos_inputs):
        cod_pr = st.sidebar.text_input(f"Código PR p/ Prod #{idx+1} (Busca: {prod['codigo']})", key=f"cod_pr_{idx}")
        produtos_inputs[idx]["cod_parana"] = cod_pr.strip()

# ==========================================
# MONTAGEM DA IMAGEM FINAL
# ==========================================
if st.button("🚀 Gerar Catálogo Final", type="primary"):
    if not produtos_inputs:
        st.warning("Por favor, insira pelo menos um código na barra lateral.")
    else:
        with st.spinner("Buscando imagens limpas dos produtos e gerando arte..."):
            produtos_carregados = []

            for item in produtos_inputs:
                dados = buscar_dados_produto(item["codigo"])
                img = baixar_imagem(dados["img_url"]) if dados else None

                if not img:
                    img = Image.new("RGBA", (300, 300), color=(230, 230, 230, 255))

                dados["imagem"] = img
                dados["desconto"] = item["desconto"]
                dados["validade"] = item["validade"]
                dados["preco"] = item["preco"]

                if modo_parana and item["cod_parana"]:
                    dados["codigo"] = item["cod_parana"]

                produtos_carregados.append(dados)
                time.sleep(0.1)

            total = len(produtos_carregados)

            if "Stories" in opcao_formato:
                LARGURA_MAX = 1080
                ALTURA_MAX = 1920
                ALTURA_CABECALHO = 280
                ALTURA_RODAPE = 80
            else:
                LARGURA_MAX = 1200
                ALTURA_MAX = 1200
                ALTURA_CABECALHO = 220
                ALTURA_RODAPE = 60

            if total == 1:
                cols, linhas = 1, 1
            elif total == 2:
                cols, linhas = 1, 2 if "Stories" in opcao_formato else (2, 1)
            elif total <= 3:
                cols, linhas = (1, 3) if "Stories" in opcao_formato else (3, 1)
            elif total <= 6:
                cols, linhas = 2, 3
            elif total <= 9:
                cols, linhas = 3, 3
            elif total <= 12:
                cols, linhas = 3, 4
            else:
                cols, linhas = 4, 4

            altura_area_produtos = ALTURA_MAX - ALTURA_CABECALHO - ALTURA_RODAPE
            largura_slot = LARGURA_MAX // cols
            altura_slot = altura_area_produtos // linhas

            if "Personalizada" in tipo_fundo and bg_custom_file:
                bg_img = Image.open(bg_custom_file).convert("RGBA")
                catalogo = bg_img.resize((LARGURA_MAX, ALTURA_MAX), Image.Resampling.LANCZOS)
            else:
                catalogo = Image.new("RGBA", (LARGURA_MAX, ALTURA_MAX), color=cor_fundo_catalogo)

            draw = ImageDraw.Draw(catalogo)

            # --- 1. CABEÇALHO ---
            if banner_imagem_ativa:
                alt_banner_alvo = ALTURA_CABECALHO - 15
                if "Stories" in opcao_formato:
                    banner_final = criar_banner_com_blur(banner_imagem_ativa, LARGURA_MAX, alt_banner_alvo)
                else:
                    banner_final = banner_imagem_ativa.resize((LARGURA_MAX, alt_banner_alvo), Image.Resampling.LANCZOS)

                catalogo.paste(banner_final, (0, 0), banner_final)
            else:
                x_inicio_texto = 40
                if st.session_state["logo_bytes"] is not None:
                    logo_img = Image.open(io.BytesIO(st.session_state["logo_bytes"])).convert("RGBA")
                    logo_img.thumbnail((220, ALTURA_CABECALHO - 40))
                    catalogo.paste(logo_img, (30, (ALTURA_CABECALHO - logo_img.height) // 2 - 10), logo_img)
                    x_inicio_texto = 270

                y_texto = 45
                y_texto = desenhar_texto_alinhado(
                    draw, frase_1.upper(), y_texto, cor_1, tam_1, alinh_1, estilo_fonte=fonte_1, x_inicio=x_inicio_texto, x_fim=LARGURA_MAX - 30
                )
                desenhar_texto_alinhado(
                    draw, frase_2, y_texto + 5, cor_2, tam_2, alinh_2, estilo_fonte=fonte_2, x_inicio=x_inicio_texto, x_fim=LARGURA_MAX - 30
                )

            draw.line([(30, ALTURA_CABECALHO - 15), (LARGURA_MAX - 30, ALTURA_CABECALHO - 15)], fill="#CCCCCC", width=2)

            # --- 2. CARDS E PRODUTOS (LAYOUT LADO A LADO) ---
            tamanho_fonte_tit = tam_descricao_custom
            tamanho_fonte_cod = max(10, int(tam_descricao_custom * 0.85))

            fonte_prod_titulo = carregar_fonte("Padrão Negrito (Liberation / Arial)", tamanho_fonte_tit)
            fonte_prod_codigo = carregar_fonte("Padrão Negrito (Liberation / Arial)", tamanho_fonte_cod)

            padding_card = 8 if cols == 4 else 12

            for idx, prod in enumerate(produtos_carregados):
                c = idx % cols
                l = idx // cols

                slot_x = c * largura_slot
                slot_y = ALTURA_CABECALHO + (l * altura_slot)

                card_w = largura_slot - (padding_card * 2)
                altura_max_ideal = int(card_w * 1.45)
                card_h = min(altura_slot - (padding_card * 2), altura_max_ideal)

                offset_y_centro = (altura_slot - card_h) // 2

                card_x1 = slot_x + padding_card
                card_y1 = slot_y + offset_y_centro
                card_x2 = card_x1 + card_w
                card_y2 = card_y1 + card_h
                card_radius = 12 if cols == 4 else 14

                draw.rounded_rectangle(
                    [card_x1, card_y1, card_x2, card_y2],
                    radius=card_radius,
                    fill="white",
                    outline="#E0E0E0",
                    width=1,
                )

                texto_titulo = prod["titulo"].upper() if formatar_caixa_alta else prod["titulo"]
                largura_util_texto = card_w - (padding_h_desc * 2)
                titulos_wrapped = quebrar_texto_por_largura(draw, texto_titulo, fonte_prod_titulo, largura_util_texto)[:2]

                espacamento_linha = int(tamanho_fonte_tit * 1.2)
                altura_titulos = len(titulos_wrapped) * espacamento_linha

                margin_bottom_cod = 6
                box_top_y = card_y2 - 10 - altura_titulos - (padding_v_desc * 2)
                y_cod = box_top_y - tamanho_fonte_cod - margin_bottom_cod

                texto_cod = f"COD: {prod['codigo']}"
                if prod["validade"]:
                    texto_cod += f" - {prod['validade']}"

                bbox_cod = draw.textbbox((0, 0), texto_cod, font=fonte_prod_codigo)
                w_cod = bbox_cod[2] - bbox_cod[0]
                x_cod = card_x1 + (card_w - w_cod) // 2
                draw.text((x_cod, y_cod), texto_cod, fill="#222222", font=fonte_prod_codigo)

                y_t = box_top_y + padding_v_desc

                if cor_box_desc != "TRANSPARENTE":
                    box_desc_x1 = card_x1 + padding_h_desc
                    box_desc_x2 = card_x2 - padding_h_desc
                    box_desc_y1 = box_top_y
                    box_desc_y2 = box_top_y + altura_titulos + (padding_v_desc * 2)

                    draw.rounded_rectangle(
                        [box_desc_x1, box_desc_y1, box_desc_x2, box_desc_y2],
                        radius=max(4, card_radius // 2),
                        fill=cor_box_desc
                    )

                for t_linha in titulos_wrapped:
                    bbox_tit = draw.textbbox((0, 0), t_linha, font=fonte_prod_titulo)
                    w_tit = bbox_tit[2] - bbox_tit[0]
                    x_tit = card_x1 + (card_w - w_tit) // 2
                    draw.text((x_tit, y_t), t_linha, fill=cor_texto_desc, font=fonte_prod_titulo)
                    y_t += espacamento_linha

                # --- COLUNAS INTERNAS (FOTO NA ESQUERDA, PREÇO NA DIREITA) ---
                metade_card_w = card_w // 2
                
                col_img_x1 = card_x1 + 8
                col_img_x2 = card_x1 + metade_card_w - 4
                max_w_img = col_img_x2 - col_img_x1
                
                col_preco_x1 = card_x1 + metade_card_w + 4
                col_preco_x2 = card_x2 - 8

                img_prod = prod["imagem"]
                max_h_img = y_cod - card_y1 - 20

                if max_h_img > 30 and max_w_img > 30:
                    img_fit = redimensionar_proporcional(img_prod, max_w_img, max_h_img, fator_zoom)
                    x_img = col_img_x1 + (max_w_img - img_fit.width) // 2
                    y_img = card_y1 + 10 + (max_h_img - img_fit.height) // 2
                    catalogo.paste(img_fit, (x_img, y_img), img_fit)

                if prod.get("preco"):
                    tam_base = 42 if tamanho_preco_opcao == "Grande" else (34 if tamanho_preco_opcao == "Médio" else 26)
                    centro_y_preco = card_y1 + 10 + (max_h_img // 2)
                    
                    tratar_e_desenhar_preco(
                        draw,
                        prod["preco"],
                        col_preco_x1,
                        col_preco_x2,
                        centro_y_preco,
                        cor_preco_final,
                        tam_base,
                        fonte_preco,
                    )

                if prod.get("desconto"):
                    desenhar_selo_no_card(draw, prod["desconto"], card_x2, card_y1)

            # --- 3. RODAPÉ ---
            y_rodape = ALTURA_MAX - ALTURA_RODAPE + 15
            desenhar_texto_alinhado(
                draw, frase_rodape, y_rodape, cor_r, tam_r, alinh_r, estilo_fonte=fonte_r, x_inicio=40, x_fim=LARGURA_MAX - 40
            )

            # --- 4. MARCA D'ÁGUA ---
            if ativar_marca_dagua and texto_marca_dagua:
                catalogo = aplicar_marca_dagua(catalogo, texto=texto_marca_dagua, opacidade=opacidade_marca)

            # --- EXIBIÇÃO E DOWNLOAD ---
            buf = io.BytesIO()
            catalogo.convert("RGB").save(buf, format="PNG")
            byte_im = buf.getvalue()

            st.image(byte_im, caption="🎨 Arte Gerada com Sucesso!", use_container_width=True)
            st.download_button(
                label="📥 Baixar Catálogo em Alta Resolução",
                data=byte_im,
                file_name="catalogo_promocional.png",
                mime="image/png",
            )
