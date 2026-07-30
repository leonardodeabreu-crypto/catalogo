import re
from bs4 import BeautifulSoup
import requests
import streamlit as st

# --- CABEÇALHOS HTTP NECESSÁRIOS ---
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


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

            # 3. Busca imagem no modal de foto ampliada
            try:
                url_modal = f"https://www.fornecimentodireto.com.br/FotoProdutoAmpliar/{cod_real}"
                headers_modal = HEADERS.copy()
                headers_modal["X-Requested-With"] = "XMLHttpRequest"

                res_hd = requests.get(
                    url_modal, headers=headers_modal, timeout=5
                )
                if res_hd.status_code == 200:
                    soup_hd = BeautifulSoup(res_hd.content, "html.parser")
                    img_hd = soup_hd.find("img", class_="img-produto-ampliada")
                    if img_hd:
                        dados["img_url"] = img_hd.get("data-src") or img_hd.get(
                            "src"
                        )
            except Exception:
                pass

            # 4. Fallback: URL direta de foto em alta resolução (/2.jpg)
            if not dados["img_url"]:
                dados["img_url"] = (
                    f"https://www.mercadoagora.com/arquivos/produtos/{cod_real}/2.jpg"
                )

            return dados
    except Exception as e:
        st.error(f"Erro ao buscar produto {codigo_busca}: {e}")

    return dados


# --- INTERFACE STREAMLIT ---
st.title("Consulta de Produtos")

codigo_input = st.text_input(
    "Digite o código do produto:", placeholder="Ex: 27728"
)

if st.button("Buscar"):
    if codigo_input:
        with st.spinner("Buscando informações..."):
            info = buscar_dados_produto(codigo_input)

            st.subheader(info["titulo"])
            st.write(f"**Código:** {info['codigo']}")

            if info["img_url"]:
                st.image(
                    info["img_url"],
                    caption=f"Foto Ampliada - Código {info['codigo']}",
                    use_container_width=True,
                )
            else:
                st.warning("Imagem não encontrada.")
    else:
        st.warning("Por favor, informe um código.")
