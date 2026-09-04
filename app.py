# ==============================================================================
# MÓDULO 2: CONVERSÃO DE FOTOS E-COMMERCE (PROTEGIDO)
# ==============================================================================
elif modulo_selecionado == "🖼️ Conversão de Fotos E-commerce":
    st.title("🖼️ Conversão de Fotos E-commerce")
    st.write("Gere composições fotográficas padronizadas para o site.")

    # Validação de Senha do Módulo (5588)
    if not st.session_state["auth_ecom"]:
        st.subheader("🔒 Acesso Restrito ao Módulo")
        pwd_ecom = st.text_input("Digite a Senha do Módulo (5588)", type="password", key="pwd_ecom_input")
        if st.button("Liberar Módulo E-commerce"):
            if pwd_ecom == SENHA_ECOMMERCE or pwd_ecom == SENHA_ADM:
                st.session_state["auth_ecom"] = True
                st.success("Acesso autorizado!")
                st.rerun()
            else:
                st.error("Senha incorreta!")
        st.stop()

    # 1. ENTRADA DO CÓDIGO DO PRODUTO (Barra Lateral)
    st.sidebar.header("⚙️ Dados do Produto")
    cod_ecom = st.sidebar.text_input(
        "Código do Produto", 
        help="Digite o código do produto. O sistema buscará o nome no site e escreverá sobre a barra institucional."
    )

    bg_ecom_color = st.sidebar.color_picker("Cor de Fundo da Arte", "#FFFFFF")

    # Ajuste de cores dos textos sobre a barra
    st.sidebar.subheader("🎨 Estilo dos Textos no Banner")
    cor_texto_banner = st.sidebar.color_picker("Cor do Nome/Código", "#1E1E1E")
    tam_fonte_banner = st.sidebar.slider("Tamanho da Fonte do Nome", 12, 30, 18)

    st.markdown("### 📤 Upload das 3 Fotos do Produto")
    col_up1, col_up2, col_up3 = st.columns(3)

    with col_up1:
        file_f1 = st.file_uploader("1. Foto Principal (Preto - Esquerda)", type=["png", "jpg", "jpeg"], key="ecom_f1")
    with col_up2:
        file_f2 = st.file_uploader("2. Foto Lateral (Vermelho - Topo Dir.)", type=["png", "jpg", "jpeg"], key="ecom_f2")
    with col_up3:
        file_f3 = st.file_uploader("3. Foto Extra (Azul - Meio Dir.)", type=["png", "jpg", "jpeg"], key="ecom_f3")

    st.markdown("---")

    if st.button("✨ Criar Composição E-commerce", type="primary"):
        if not file_f1 or not file_f2 or not file_f3:
            st.error("Por favor, faça o upload das 3 fotos obrigatórias.")
        elif not cod_ecom.strip():
            st.error("Por favor, informe o Código do Produto na barra lateral.")
        else:
            with st.spinner("Buscando dados no site e montando a foto composta..."):
                # Busca nome e código do produto via scraping
                dados_prod = buscar_dados_produto(cod_ecom.strip())
                nome_produto = dados_prod.get("titulo", f"PRODUTO {cod_ecom}").upper()
                codigo_produto = dados_prod.get("codigo", cod_ecom)

                # Dimensões da Imagem Composta (1200x675 / Proporção 16:9)
                CANVAS_W = 1200
                CANVAS_H = 675
                HALF_W = CANVAS_W // 2  # 600px

                ecom_canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), bg_ecom_color)

                # -------------------------------------------------------------
                # 1. FOTO 1 (Área Preta: Esquerda Inteira)
                # -------------------------------------------------------------
                img1 = Image.open(file_f1).convert("RGBA")
                box_f1 = encaixar_e_centralizar(img1, HALF_W, CANVAS_H)
                ecom_canvas.paste(box_f1, (0, 0), box_f1)

                # Proporções da Coluna Direita (30% / 50% / 20%)
                H_RED = int(CANVAS_H * 0.30)        # 202px
                H_BLUE = int(CANVAS_H * 0.50)       # 338px
                H_YELLOW = CANVAS_H - H_RED - H_BLUE # 135px (Barra Institucional)

                # -------------------------------------------------------------
                # 2. FOTO 2 (Área Vermelha: Topo Direito)
                # -------------------------------------------------------------
                img2 = Image.open(file_f2).convert("RGBA")
                box_f2 = encaixar_e_centralizar(img2, HALF_W, H_RED)
                ecom_canvas.paste(box_f2, (HALF_W, 0), box_f2)

                # -------------------------------------------------------------
                # 3. FOTO 3 (Área Azul: Meio Direito)
                # -------------------------------------------------------------
                img3 = Image.open(file_f3).convert("RGBA")
                box_f3 = encaixar_e_centralizar(img3, HALF_W, H_BLUE)
                ecom_canvas.paste(box_f3, (HALF_W, H_RED), box_f3)

                # -------------------------------------------------------------
                # 4. BARRA INSTITUCIONAL (Área Amarela: Rodapé Direito)
                # -------------------------------------------------------------
                banner_y_pos = H_RED + H_BLUE
                NOME_ARQUIVO_BARRA = "barra_institucional_foto_lote_ecommerce.jpg"

                # Tenta carregar a imagem da barra que estará no servidor
                if os.path.exists(NOME_ARQUIVO_BARRA):
                    img_barra = Image.open(NOME_ARQUIVO_BARRA).convert("RGBA")
                    img_barra = img_barra.resize((HALF_W, H_YELLOW), Image.Resampling.LANCZOS)
                else:
                    # Fundo amarelo padrão de emergência caso o arquivo ainda não esteja no servidor
                    img_barra = Image.new("RGBA", (HALF_W, H_YELLOW), "#FBC02D")

                draw_barra = ImageDraw.Draw(img_barra)

                # Fontes para Nome e Código
                fonte_nome = carregar_fonte("Padrão Negrito (Liberation / Arial)", tam_fonte_banner)
                fonte_cod = carregar_fonte("Padrão Negrito (Liberation / Arial)", max(11, int(tam_fonte_banner * 0.75)))

                # Quebra o nome do produto se for muito longo para caber na largura da barra
                margem_x = 15
                largura_util = HALF_W - (margem_x * 2)
                linhas_nome = quebrar_texto_por_largura(draw_barra, nome_produto, fonte_nome, largura_util)[:2]

                y_texto = 12
                for linha in linhas_nome:
                    bbox_l = draw_barra.textbbox((0, 0), linha, font=fonte_nome)
                    # Escreve o nome do produto
                    draw_barra.text((margem_x, y_texto), linha, fill=cor_texto_banner, font=fonte_nome)
                    y_texto += (bbox_l[3] - bbox_l[1]) + 4

                # Escreve o código do produto na linha abaixo
                txt_codigo_final = f"CÓDIGO: {codigo_produto}"
                draw_barra.text((margem_x, y_texto + 2), txt_codigo_final, fill=cor_texto_banner, font=fonte_cod)

                # Cola a barra processada no canto inferior direito
                ecom_canvas.paste(img_barra, (HALF_W, banner_y_pos), img_barra)

                # Divisórias sutis
                draw_ecom = ImageDraw.Draw(ecom_canvas)
                draw_ecom.line([(HALF_W, 0), (HALF_W, CANVAS_H)], fill="#D0D0D0", width=2)
                draw_ecom.line([(HALF_W, H_RED), (CANVAS_W, H_RED)], fill="#D0D0D0", width=2)
                draw_ecom.line([(HALF_W, banner_y_pos), (CANVAS_W, banner_y_pos)], fill="#D0D0D0", width=2)

                # Exibição e Download
                st.image(ecom_canvas, caption=f"📸 Imagem Composta E-commerce - Prod. {codigo_produto}", use_container_width=True)

                out_bytes = io.BytesIO()
                ecom_canvas.convert("RGB").save(out_bytes, format="JPEG", quality=95)

                st.download_button(
                    label="📥 Baixar Imagem Composta E-commerce (JPG)",
                    data=out_bytes.getvalue(),
                    file_name=f"ecommerce_{codigo_produto}.jpg",
                    mime="image/jpeg",
                    type="primary",
                )
