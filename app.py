# ==========================================
# PAINEL LATERAL (CONTROLES)
# ==========================================

# Busca imagens de banners tanto na RAIZ do repositório quanto dentro de uma pasta 'banners'
arquivos_banners = []

# 1. Procurar arquivos que começam com "banner" na raiz (Ex: banner_dia_dos_pais.png)
for f in os.listdir("."):
    if f.lower().startswith("banner") and f.lower().endswith(
        (".png", ".jpg", ".jpeg")
    ):
        arquivos_banners.append(f)

# 2. Procurar dentro de uma pasta 'banners' (se existir)
if os.path.exists("banners") and os.path.isdir("banners"):
    for f in os.listdir("banners"):
        if f.lower().endswith((".png", ".jpg", ".jpeg")):
            arquivos_banners.append(os.path.join("banners", f))

# Remove duplicados e ordena
arquivos_banners = sorted(list(set(arquivos_banners)))

st.sidebar.header("🖼️ 1. Cabeçalho (Topo do Catálogo)")

opcoes_cabecalho = ["Nenhum (Usar Logo e Frases)", "📤 Upload Manual de Banner"]
if arquivos_banners:
    opcoes_cabecalho.extend(
        [f"📁 {os.path.basename(b)}" for b in arquivos_banners]
    )

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
        st.sidebar.image(
            banner_imagem_ativa,
            caption="🔍 Pré-visualização do Banner",
            use_container_width=True,
        )

elif opcao_banner_selecionada.startswith("📁 "):
    nome_banner_atual = opcao_banner_selecionada.replace("📁 ", "")

    # Procura o caminho real do arquivo selecionado
    caminho_banner = None
    for b_path in arquivos_banners:
        if os.path.basename(b_path) == nome_banner_atual:
            caminho_banner = b_path
            break

    if caminho_banner and os.path.exists(caminho_banner):
        banner_imagem_ativa = Image.open(caminho_banner).convert("RGBA")
        st.sidebar.image(
            banner_imagem_ativa,
            caption=f"Banner: {nome_banner_atual}",
            use_container_width=True,
        )
