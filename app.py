import re  # <--- CERTIFIQUE-SE DE QUE ESTA LINHA ESTÁ NO TOPO DO APP.PY
import requests
from bs4 import BeautifulSoup
import streamlit as st


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

            # 1. Código do produto
            codigo_tag = soup.find("p", class_="card-text small")
            if codigo_tag:
                numeros = re.findall(r"\d+", codigo_tag.get_text(strip=True))
                if numeros:
                    dados["codigo"] = numeros[0]

            # 2. Título
            titulo_tag = soup.find("h6", class_="card-title")
            if titulo_tag:
                dados["titulo"] = titulo_tag.get_text(strip=True)

            cod_real = dados["codigo"]

            # 3. Tenta pegar a foto ampliada no Modal
            try:
                url_modal = f"https://www.fornecimentodireto.com.br/FotoProdutoAmpliar/{cod_real}"
                res_hd = requests.get(
                    url_modal,
                    headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
                    timeout=5,
                )
                if res_hd.status_code == 200:
                    soup_hd = BeautifulSoup(res_hd.content, "html.parser")
                    img_hd = soup_hd.find("img", class_="img-produto-ampliada")
                    if img_hd:
                        # Pega data-src ou src
                        dados["img_url"] = img_hd.get("data-src") or img_hd.get(
                            "src"
                        )
            except Exception:
                pass

            # 4. Fallback: Se não veio do modal, usa o padrão /produtos/{cod}/2.jpg diretamente
            if not dados["img_url"]:
                dados["img_url"] = (
                    f"https://www.mercadoagora.com/arquivos/produtos/{cod_real}/2.jpg"
                )

            return dados
    except Exception as e:
        st.error(f"Erro ao buscar código {codigo_busca}: {e}")

    return dados
