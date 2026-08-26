# --- 2. CARDS E PRODUTOS (PREÇO 2X MAIOR) ---
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

                    # --- COLUNAS (45% FOTO | 55% PREÇO EXPANDIDO) ---
                    largura_foto_area = int(card_w * 0.45)
                    
                    col_img_x1 = card_x1 + 6
                    col_img_x2 = card_x1 + largura_foto_area
                    max_w_img = col_img_x2 - col_img_x1
                    
                    col_preco_x1 = card_x1 + largura_foto_area + 2
                    col_preco_x2 = card_x2 - 6

                    img_prod = prod["imagem"]
                    max_h_img = y_cod - card_y1 - 20

                    if max_h_img > 30 and max_w_img > 30:
                        img_fit = redimensionar_proporcional(img_prod, max_w_img, max_h_img, fator_zoom)
                        x_img = col_img_x1 + (max_w_img - img_fit.width) // 2
                        y_img = card_y1 + 10 + (max_h_img - img_fit.height) // 2
                        catalogo.paste(img_fit, (x_img, y_img), img_fit)

                    if prod.get("preco"):
                        # Tamanhos duplicados para dar o impacto visual de encarte
                        tam_base = 85 if tamanho_preco_opcao == "Grande" else (65 if tamanho_preco_opcao == "Médio" else 50)
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
