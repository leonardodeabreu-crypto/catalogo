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
            # Procura pela tag de imagem dentro do card do produto
            card = soup.find("div", class_="card") or soup
            img_tag = card.find("img")

            if img_tag:
                url_encontrada = img_tag.get("src") or img_tag.get("data-src")
                
                # Garante que não estamos pegando ícones ou selos de marcas
                palavras_bloqueadas = ["logo", "icon", "banner", "loader", "marca", "brand", "selo", "flag"]
                
                if url_encontrada and not any(p in url_encontrada.lower() for p in palavras_bloqueadas):
                    # Limpa parâmetros de miniatura/redimensionamento para pegar a imagem cheia
                    url_limpa = re.sub(r"\?(width|height|w|h|dim)=\d+.*$", "", url_encontrada)
                    url_limpa = re.sub(r"/(120|270)x(120|270)/", "/", url_limpa)

                    if not url_limpa.startswith("http"):
                        url_limpa = (
                            "https://www.fornecimentodireto.com.br/"
                            + url_limpa.lstrip("/")
                        )

                    dados["img_url"] = url_limpa

            # Fallback seguro direto pelo CDN do fornecedor (usando o código do produto)
            if not dados["img_url"]:
                dados["img_url"] = (
                    f"https://www.mercadoagora.com/arquivos/produtos/{cod_real}/1.jpg"
                )

    except Exception as e:
        st.warning(f"Aviso ao buscar produto {codigo_busca}: {e}")

    return dados
