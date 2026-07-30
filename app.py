import io
import os
import re
import glob
import time
import json
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

# Arquivo JSON para salvar o mapeamento de Cores dos Banners
ARQUIVO_CORES_BANNERS = "cores_banners.json"

def carregar_cores_banners():
    if os.path.exists(ARQUIVO_CORES_BANNERS):
        try:
            with open(ARQUIVO_CORES_BANNERS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salvar_cores_banners(dados):
    with open(ARQUIVO_CORES_BANNERS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

dict_cores_banners = carregar_cores_banners()

# ==========================================
# SISTEMA DE SENHA SIMPLES (4 DÍGITOS)
# ==========================================
SENHA_CORRETA = "2244"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito")
    st.write("Digite a senha de 4 dígitos para acessar o gerador de catálogos.")

    senha_digitada = st.text_input("Senha de Acesso", type="password", max_chars=4)

    if st.button("Entrar"):
        if senha_digitada == SENHA_CORRETA:
            st.session_state["autenticado"] = True
            st.success("Acesso liberado!")
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")

    st.stop()


# ==========================================
# GERENCIAMENTO DE FONTES ROBUSTO
# ==========================================
OPCOES_FONTES = {
    "Padrão Negrito (Liberation / Arial)": ["LiberationSans-Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "Moderna (Liberation Light / Arial)": ["LiberationSans-Regular.ttf", "arial.ttf", "DejaVuSans.ttf"],
    "Encarte Promocional (Impact / Serif)": ["Impact.ttf", "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"],
    "Condensada / Estreita": ["LiberationSansNarrow-Bold.ttf", "DejaVuSansCondensed-Bold.ttf"],
}

def carregar_fonte(estilo_escolhido, tamanho):
    """Procura e carrega a melhor fonte vetorial disponível no sistema."""
    lista_fontes = OPCOES_FONTES.get(estilo_escolhido, ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"])
    
    lista_fontes.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "arial.ttf"
    ])

    for nome_fonte in lista_fontes:
        try:
            return ImageFont.truetype(nome_fonte, tamanho)
        except (IOError, OSError):
            continue

    return ImageFont.load_default()


# ==========================================
# CÓDIGO PRINCIPAL DO SISTEMA
# ==========================================
st.title("🥩 Gerador de Catálogo Promocional")
st.write("Monte banners e catálogos profissionais com suporte a texturas, temas dinâmicos e fontes personalizadas.")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state["autenticado"] = False
    st.rerun()

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
# FUNÇÕES DE SCRAPING E DESENHO
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
    w_orig, h_orig = img.size
    fator_base = min(max_w / w_orig, max_h / h_orig)
    fator_final = fator_base * fator_zoom

    novo_w = int(w_orig * fator_final)
    novo_h = int(h_orig * fator_final)
    return img.resize((novo_w, novo_h), Image.Resampling.LANCZOS)


def desenhar_selo_no_card(draw, texto_desconto, card_x2, card_y1, cor_fundo="#E53935", cor_texto="white"):
    if not texto_desconto:
        return

    fonte_selo = carregar_fonte("Padrão Negrito (Liberation / Arial)", 13)

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


def desenhar_texto_alinhado(draw, texto, y, cor, tamanho, alinhamento, estilo_fonte="Padrão Negrito (Liberation / Arial)", x_inicio=270, x_fim=1170):
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


# ==========================================
# PAINEL LATERAL (CONTROLES)
# ==========================================

# --- BUSCA AUTOMÁTICA DE BANNERS COM 'banner_*' ---
arquivos_banners = sorted(
    glob.glob("banner_*.png") + glob.glob("banner_*.jpg") + glob.glob("banner_*.jpeg")
)

dicio_banners = {}
for caminho in arquivos_banners:
    nome_base = os.path.basename(caminho)
    nome_limpo = re.sub(r"^banner_", "", nome_base, flags=re.IGNORECASE)
    nome_limpo = os.path.splitext(nome_limpo)[0].replace("_", " ").title()
    dicio_banners[f"📁 {nome_limpo}"] = caminho

opcoes_cabecalho = ["Nenhum (Usar Logo e Frases)", "📤 Upload Manual de Banner"] + list(dicio_banners.keys())

# --- SELEÇÃO DE CABEÇALHO ---
st.sidebar.header("🖼️ 1. Cabeçalho (Topo do Catálogo)")

opcao_banner_selecionada = st.sidebar.selectbox(
    "Escolha o Modelo do Cabeçalho",
    opcoes_cabecalho,
    index=0
)

banner_imagem_ativa = None
arquivo_banner_ativo_nome = None

if opcao_banner_selecionada == "📤 Upload Manual de Banner":
    uploaded_banner = st.sidebar.file_uploader(
        "Upload do Banner do Cabeçalho",
        type=["png", "jpg", "jpeg"],
        help="Recomendado: Imagem retangular (ex: 1200x220px)."
    )
    if uploaded_banner:
        banner_imagem_ativa = Image.open(uploaded_banner).convert("RGBA")
        st.sidebar.image(banner_imagem_ativa, caption="🔍 Pré-visualização do Banner Manual", use_container_width=True)

elif opcao_banner_selecionada in dicio_banners:
    caminho_banner = dicio_banners[opcao_banner_selecionada]
    arquivo_banner_ativo_nome = os.path.basename(caminho_banner)
    if os.path.exists(caminho_banner):
        banner_imagem_ativa = Image.open(caminho_banner).convert("RGBA")
        st.sidebar.image(banner_imagem_ativa, caption="🔍 Pré-visualização do Banner Selecionado", use_container_width=True)

# Se NENHUM banner foi selecionado, exibe os controles de Logo e Textos
if banner_imagem_ativa is None:
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
    fonte_1 = st.sidebar.selectbox("Estilo Fonte Título", list(OPCOES_FONTES.keys()), index=0)
    col_a, col_b, col_c = st.sidebar.columns(3)
    with col_a:
        alinh_1 = st.selectbox("Alinhamento #1", ["Esquerda", "Centro", "Direita"], index=0)
    with col_b:
        cor_1 = OPCOES_CORES[st.selectbox("Cor #1", list(OPCOES_CORES.keys()), index=0)]
    with col_c:
        tam_1 = st.slider("Tam #1", 16, 60, 34)

    st.sidebar.markdown("---")
    frase_2 = st.sidebar.text_input("Slogan / Subtítulo", "Preços Imbatíveis e Qualidade Garantida!")
    fonte_2 = st.sidebar.selectbox("Estilo Fonte Slogan", list(OPCOES_FONTES.keys()), index=1)
    col_d, col_e, col_f = st.sidebar.columns(3)
    with col_d:
        alinh_2 = st.selectbox("Alinhamento #2", ["Esquerda", "Centro", "Direita"], index=0)
    with col_e:
        cor_2 = OPCOES_CORES[st.selectbox("Cor #2", list(OPCOES_CORES.keys()), index=2)]
    with col_f:
        tam_2 = st.slider("Tam #2", 12, 40, 20)

st.sidebar.markdown("---")

# --- CONTROLE DO BACKGROUND (VERIFICA COR VINCULADA AO BANNER) ---
st.sidebar.header("🎨 2. Fundo do Catálogo (Background)")

# Checa se o banner selecionado possui uma cor fixa cadastrada
cor_vinculada_ao_banner = dict_cores_banners.get(arquivo_banner_ativo_nome) if arquivo_banner_ativo_nome else None

tipo_fundo = st.sidebar.radio(
    "Escolha o Tipo de Fundo",
    ["Cor Sólida / Hexadecimal", "Imagem / Textura Personalizada (Madeira, etc.)"]
)

bg_custom_file = None
cor_fundo_catalogo = "#F0F2F5"

if tipo_fundo == "Cor Sólida / Hexadecimal":
    if cor_vinculada_ao_banner:
        st.sidebar.info(f"🔒 **Cor Vinculada ao Banner:** `{cor_vinculada_ao_banner}`")
        cor_fundo_catalogo = cor_vinculada_ao_banner
    else:
        cor_fundo_catalogo = st.sidebar.color_picker(
            "Escolha ou Cole a Cor Hexadecimal (#HEX)",
            value="#F0F2F5",
            help="Você pode digitar diretamente o código hexadecimal do marketing (Ex: #FF5733, #1A2B3C)."
        )
else:
    bg_custom_file = st.sidebar.file_uploader(
        "Upload de Textura/Imagem de Fundo",
        type=["png", "jpg", "jpeg"],
        help="Envie uma imagem de madeira, pedra ou textura para o fundo."
    )

st.sidebar.markdown("---")
st.sidebar.header("📝 3. Rodapé")
frase_rodape = st.sidebar.text_input("Frase Rodapé", "Ofertas válidas enquanto durarem os estoques.")
fonte_r = st.sidebar.selectbox("Estilo Fonte Rodapé", list(OPCOES_FONTES.keys()), index=0)
col_g, col_h, col_i = st.sidebar.columns(3)
with col_g:
    alinh_r = st.selectbox("Alinhamento Rodapé", ["Esquerda", "Centro", "Direita"], index=1)
with col_h:
    cor_r = OPCOES_CORES[st.selectbox("Cor Rodapé", list(OPCOES_CORES.keys()), index=2)]
with col_i:
    tam_r = st.slider("Tam Rodapé", 12, 30, 16)

st.sidebar.markdown("---")
st.sidebar.header("🛒 4. Cadastro de Produtos")

# --- ZOOM AJUSTADO PARA INICIAR EM 100 ---
zoom_porcentagem = st.sidebar.slider(
    "🔍 Zoom da Imagem do Produto",
    min_value=100,
    max_value=180,
    value=100,
    step=10,
    help="Aumenta proporcionalmente a imagem aproveitando o espaço em branco do card.",
)
fator_zoom = zoom_porcentagem / 100.0

OPCOES_QUANTIDADE = [3, 6, 9, 12, 16]
num_produtos = st.sidebar.selectbox(
    "Quantidade de Produtos",
    OPCOES_QUANTIDADE,
    index=2
)

produtos_inputs = []
for i in range(num_produtos):
    st.sidebar.markdown(f"**Produto #{i+1}**")
    col1, col2 = st.sidebar.columns([2, 2])
    with col1:
        cod = st.text_input(f"COD. #{i+1}", key=f"cod_{i}")
    with col2:
        desc = st.text_input(f"Selo Ex: 10% OFF", key=f"desc_{i}")

    val = st.sidebar.text_input(f"Validade Ex: val: 08/08/2026", key=f"val_{i}")

    if cod.strip():
        produtos_inputs.append({
            "codigo": cod.strip(),
            "desconto": desc.strip(),
            "validade": val.strip(),
            "cod_parana": ""
        })

# --- MODO PARANÁ ---
st.sidebar.markdown("---")
modo_parana = st.sidebar.checkbox(
    "🌲 Modo Paraná (Substituir Códigos)",
    value=False,
    help="Ative para exibir um campo manual onde você pode digitar o código do PR para aparecer na imagem final."
)

if modo_parana and produtos_inputs:
    st.sidebar.subheader("🔑 Códigos do Paraná (PR)")
    st.sidebar.caption("O sistema usará o código original para buscar a foto e o título no site, mas usará o código abaixo na arte final.")
    
    for idx, prod in enumerate(produtos_inputs):
        cod_pr = st.sidebar.text_input(
            f"Código PR p/ Prod #{idx+1} (Busca: {prod['codigo']})",
            key=f"cod_pr_{idx}",
            help=f"Código público usado para busca: {prod['codigo']}"
        )
        produtos_inputs[idx]["cod_parana"] = cod_pr.strip()


# --- GERENCIADOR: BANNERS CORES ---
st.sidebar.markdown("---")
with st.sidebar.expander("🎨 Configurar Cores dos Banners"):
    st.write("Vincule uma cor Hexadecimal a cada arquivo de banner para que ela seja aplicada automaticamente.")
    
    if arquivos_banners:
        banner_para_config = st.selectbox(
            "Selecione o Banner",
            [os.path.basename(b) for b in arquivos_banners],
            key="select_banner_cor"
        )
        
        cor_atual_salva = dict_cores_banners.get(banner_para_config, "#F0F2F5")
        
        cor_hex_input = st.text_input(
            "Cor Hexadecimal (#HEX)",
            value=cor_atual_salva,
            key="input_hex_banner"
        )
        
        if st.button("💾 Salvar Cor do Banner"):
            dict_cores_banners[banner_para_config] = cor_hex_input.strip().upper()
            salvar_cores_banners(dict_cores_banners)
            st.success(f"Cor {cor_hex_input} salva para o banner!")
            st.rerun()
            
        if dict_cores_banners:
            st.markdown("**Cores Atualmente Vinculadas:**")
            for b_name, b_color in dict_cores_banners.items():
                st.caption(f"• `{b_name}`: **{b_color}**")
    else:
        st.warning("Nenhum arquivo `banner_*.png` encontrado na pasta.")


# ==========================================
# MONTAGEM DA IMAGEM
# ==========================================
if st.button("🚀 Gerar Catálogo Final", type="primary"):
    if not produtos_inputs:
        st.warning("Por favor, insira pelo menos um código na barra lateral.")
    else:
        with st.spinner("Buscando dados e aplicando cabeçalho e fundo..."):
            produtos_carregados = []

            for item in produtos_inputs:
                dados = buscar_dados_produto(item["codigo"])
                img = baixar_imagem(dados["img_url"]) if dados else None

                if not img:
                    img = Image.new("RGBA", (300, 300), color=(230, 230, 230, 255))

                dados["imagem"] = img
                dados["desconto"] = item["desconto"]
                dados["validade"] = item["validade"]
                
                if modo_parana and item["cod_parana"]:
                    dados["codigo"] = item["cod_parana"]

                produtos_carregados.append(dados)
                time.sleep(0.1)

            total = len(produtos_carregados)

            if total <= 3:
                cols = 3
                linhas = 1
            elif total <= 6:
                cols = 3
                linhas = 2
            elif total <= 9:
                cols = 3
                linhas = 3
            elif total <= 12:
                cols = 4
                linhas = 3
            else:
                cols = 4
                linhas = 4

            LARGURA_MAX = 1200
            ALTURA_MAX = 1200
            ALTURA_CABECALHO = 220
            ALTURA_RODAPE = 60

            altura_area_produtos = ALTURA_MAX - ALTURA_CABECALHO - ALTURA_RODAPE

            largura_slot = LARGURA_MAX // cols
            altura_slot = altura_area_produtos // linhas

            # --- BASE DO CATÁLOGO (FUNDO) ---
            if "Personalizada" in tipo_fundo and bg_custom_file:
                bg_img = Image.open(bg_custom_file).convert("RGBA")
                catalogo = bg_img.resize((LARGURA_MAX, ALTURA_MAX), Image.Resampling.LANCZOS)
            else:
                catalogo = Image.new("RGBA", (LARGURA_MAX, ALTURA_MAX), color=cor_fundo_catalogo)

            draw = ImageDraw.Draw(catalogo)

            # --- 1. CABEÇALHO ---
            if banner_imagem_ativa:
                banner_resized = banner_imagem_ativa.resize((LARGURA_MAX, ALTURA_CABECALHO - 15), Image.Resampling.LANCZOS)
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

                y_texto = 45
                y_texto = desenhar_texto_alinhado(
                    draw, frase_1.upper(), y_texto, cor_1, tam_1, alinh_1, estilo_fonte=fonte_1, x_inicio=x_inicio_texto
                )
                desenhar_texto_alinhado(
                    draw, frase_2, y_texto + 5, cor_2, tam_2, alinh_2, estilo_fonte=fonte_2, x_inicio=x_inicio_texto
                )

            draw.line([(30, ALTURA_CABECALHO - 15), (1170, ALTURA_CABECALHO - 15)], fill="#CCCCCC", width=2)

            # --- 2. CARDS E PRODUTOS ---
            tamanho_fonte_tit = 11 if cols == 4 else 13
            tamanho_fonte_cod = 10 if cols == 4 else 11

            fonte_prod_titulo = carregar_fonte("Padrão Negrito (Liberation / Arial)", tamanho_fonte_tit)
            fonte_prod_codigo = carregar_fonte("Padrão Negrito (Liberation / Arial)", tamanho_fonte_cod)

            padding_card = 8 if cols == 4 else 12
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

                draw.rounded_rectangle(
                    [card_x1, card_y1, card_x2, card_y2],
                    radius=12 if cols == 4 else 14,
                    fill="white",
                    outline="#E0E0E0",
                    width=1,
                )

                char_limite = max(10, card_w // 10)
                titulos_wrapped = textwrap.wrap(prod["titulo"], width=char_limite)[:2]

                altura_titulos = len(titulos_wrapped) * (13 if cols == 4 else 15)
                y_texto_base = card_y2 - 10 - altura_titulos - 16
                y_cod = y_texto_base

                texto_cod = f"COD: {prod['codigo']}"
                if prod["validade"]:
                    texto_cod += f" - {prod['validade']}"

                bbox_cod = draw.textbbox((0, 0), texto_cod, font=fonte_prod_codigo)
                w_cod = bbox_cod[2] - bbox_cod[0]
                x_cod = card_x1 + (card_w - w_cod) // 2
                draw.text((x_cod, y_cod), texto_cod, fill="#222222", font=fonte_prod_codigo)

                y_t = y_cod + (bbox_cod[3] - bbox_cod[1]) + 3
                for t_linha in titulos_wrapped:
                    bbox_tit = draw.textbbox((0, 0), t_linha, font=fonte_prod_titulo)
                    w_tit = bbox_tit[2] - bbox_tit[0]
                    x_tit = card_x1 + (card_w - w_tit) // 2
                    draw.text((x_tit, y_t), t_linha, fill="#444444", font=fonte_prod_titulo)
                    y_t += (13 if cols == 4 else 15)

                area_foto_top = card_y1 + 8
                area_foto_bottom = y_cod - 6
                max_foto_h = area_foto_bottom - area_foto_top
                max_foto_w = card_w - 16

                img_p = redimensionar_proporcional(prod["imagem"], max_foto_w, max_foto_h, fator_zoom=fator_zoom)

                pos_x = card_x1 + (card_w - img_p.width) // 2
                pos_y = area_foto_top + (max_foto_h - img_p.height) // 2

                catalogo.paste(img_p, (pos_x, pos_y), img_p)

                if prod["desconto"]:
                    desenhar_selo_no_card(draw, prod["desconto"], card_x2, card_y1)

            # --- 3. RODAPÉ ---
            y_rodape = ALTURA_MAX - ALTURA_RODAPE + 10
            draw.line([(30, y_rodape - 5), (1170, y_rodape - 5)], fill="#CCCCCC", width=2)

            desenhar_texto_alinhado(
                draw, frase_rodape, y_rodape + 10, cor_r, tam_r, alinh_r, estilo_fonte=fonte_r, x_inicio=30, x_fim=1170
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
