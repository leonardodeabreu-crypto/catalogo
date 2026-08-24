import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib3

# Desativa os avisos vermelhos de "Unverified HTTPS request" no console
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def buscar_produto(codigo_produto):
    url = f"https://www.fornecimentodireto.com.br/?busca={codigo_produto}"
    
    # Cabeçalhos para simular um navegador comum e evitar bloqueios simples
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # A chave principal: verify=False ignora o erro de certificado SSL
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # --- INSIRA AQUI A SUA LÓGICA DE EXTRAÇÃO DOS DADOS DO PRODUTO ---
        # Exemplo hipotético de raspagem:
        # titulo = soup.find("h1", class_="product-title").text.strip()
        # imagem = soup.find("img", class_="product-img")["src"]
        
        return {
            "status": "sucesso",
            "html_parsed": soup
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "erro",
            "mensagem": f"Erro ao buscar produto {codigo_produto}: {str(e)}"
        }

# --- INTERFACE STREAMLIT ---
st.title("Gerador de Catalogo")

codigo = st.text_input("Código do Produto:", value="23702")

if st.button("🚀 Gerar Catálogo Final", type="primary"):
    with st.spinner("Buscando dados do produto..."):
        resultado = buscar_produto(codigo)
        
        if resultado["status"] == "sucesso":
            st.success("Produto encontrado com sucesso!")
            # Renderize seus produtos/banners aqui
        else:
            st.error(resultado["mensagem"])
