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

            # 1. Captura o Código Real
            codigo_tag = soup.find("p", class_="card-text small")
            if codigo_tag:
                numeros = re.findall(r"\d+", codigo_tag.get_text(strip=True))
                if numeros:
                    dados["codigo"] = numeros[0]

            # 2. Captura o Título
            titulo_tag = soup.find("h6", class_="card-title")
            if titulo_tag:
                dados["titulo"] = titulo_tag.get_text(strip=True)

            cod_real = dados["codigo"]

            # --- ESTRATÉGIA A: TESTAR DIRETO A IMAGEM HD (/2.jpg no CDN) ---
            # Como vimos no seu exemplo, as fotos ampliadas usam a sequência /2.jpg
            # enquanto o thumbnail usa /1.jpg.
            url_hd_direta = f"https://www.mercadoagora.com/arquivos/produtos/{cod_real}/2.jpg"
            try:
                check_hd = requests.head(url_hd_direta, headers=HEADERS, timeout=4)
                if check_hd.status_code == 200:
                    dados["img_url"] = url_hd_direta
            except Exception:
                pass

            # --- ESTRATÉGIA B: MOCK DE REQUISIÇÃO AJAX DO MODAL ---
            if not dados["img_url"]:
                url_ampliada_modal = f"https://www.fornecimentodireto.com.br/FotoProdutoAmpliar/{cod_real}"
                headers_ajax = HEADERS.copy()
                headers_ajax["X-Requested-With"] = "XMLHttpRequest"

                try:
                    res_hd = requests.get(url_ampliada_modal, headers=headers_ajax, timeout=6)
                    if res_hd.status_code == 200:
                        soup_hd = BeautifulSoup(res_hd.content, "html.parser")
                        
                        # Busca especificamente pela classe img-produto-ampliada
                        img_hd_tag = soup_hd.find("img", class_="img-produto-ampliada") or soup_hd.find("img")
                        if img_hd_tag:
                            img_hd_url = (
                                img_hd_tag.get("data-src")
                                or img_hd_tag.get("src")
                            )
                            if img_hd_url and not img_hd_url.endswith("load.gif"):
                                if not img_hd_url.startswith("http"):
                                    img_hd_url = "https://www.fornecimentodireto.com.br/" + img_hd_url.lstrip("/")
                                dados["img_url"] = img_hd_url
                except Exception:
                    pass

            # --- ESTRATÉGIA C: FALLBACK PARA A IMAGEM DA BUSCA (E TENTATIVA DE TROCAR /1.jpg POR /2.jpg) ---
            if not dados["img_url"]:
                img_tag = soup.find("img", class_="img-produto")
                if img_tag:
                    img_url = (
                        img_tag.get("data-src")
                        or img_tag.get("data-zoom-image")
                        or img_tag.get("src")
                    )

                    if img_url and not img_url.endswith("load.gif"):
                        # Se achou a versão /1.jpg na busca, forçamos a conversão para /2.jpg (versão ampliada)
                        img_url_hd = re.sub(r"/1\.jpg", "/2.jpg", img_url)

                        if not img_url_hd.startswith("http"):
                            img_url_hd = "https://www.fornecimentodireto.com.br/" + img_url_hd.lstrip("/")
                            
                        dados["img_url"] = img_url_hd

            return dados
    except Exception as e:
        st.error(f"Erro ao buscar código {codigo_busca}: {e}")

    return dados
