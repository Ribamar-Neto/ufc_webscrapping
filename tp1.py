import time, requests, json
import pandas as pd
from bs4 import BeautifulSoup
from bs4.element import Tag
from urllib.parse import urljoin


URL_BASE = "https://ufcinova.ufc.br/pt/vitrinetecnologica/"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0"}


def analisar_pagina_inicial_lista(url: str) -> list[dict[str, str]]:
    """Analisa a página inicial e retorna uma lista de itens encontrados.

    Args:
        url (str): Url base do site.

    Returns:
        list[dict[str, str]]: Lista de dicionários com as informações dos itens encontrados.
    """
    print("Analisando página inicial:", url)
    print("-="*304)
    resposta = requests.get(url, headers=CABECALHOS, timeout=20)
    resposta.raise_for_status()
    parser = BeautifulSoup(resposta.text, "html.parser")
    itens = []

    for tag in parser.select("h5.fg-item-title a[href], .fg-item-title a[href]"):
        item = buscar_informacoes_itens(url, tag)
        if item and item["url"] not in vistos:
            item["titulo"] = ' '.join(item['titulo'].split())
            print("Categoria lida:", item["titulo"])
            itens.append(item)
            vistos.add(item["url"])

    return itens


def analisar_paginas_secundarias(categorias: list[dict[str, str]]) -> list[dict[str, str]]:
    """Analisa uma categoria completa com paginação em uma única passagem por página."""
    print("-=" * 20)
    itens = []

    for categoria in categorias:
        url_atual = categoria["url"]
        urls_visitadas = set()

        print(f"Processando categoria: {categoria['titulo']}")
        
        while url_atual and url_atual not in urls_visitadas:
            try:
                print("-"*60)
                print(f"Acessando página: {url_atual}")
                print("-"*60)
                resposta = requests.get(url_atual, headers=CABECALHOS, timeout=20)
                resposta.raise_for_status()
                parser = BeautifulSoup(resposta.text, "html.parser")

                for tag in parser.select("div.post.postcard a[href], .post.postcard a[href]"):
                    item = buscar_informacoes_itens(url_atual, tag)
                    if item and item["url"] not in vistos:
                        print("Item lido:", item["titulo"])
                        itens.append(item)
                        vistos.add(item["url"])

                urls_visitadas.add(url_atual)
                proxima_tag = parser.select_one("a.next.page-numbers[href]")
                url_atual = proxima_tag.get("href") if proxima_tag else None

            except requests.exceptions.RequestException as e:
                print(f"Erro ao acessar {url_atual}: {e}")
                break

    return itens


def buscar_informacoes_itens(url: str, link: Tag) -> dict[str, str]:
    """Monta o dicionário com as informações do item encontrado.

    Args:
        url (str): Url da página atual.
        link (Tag): Tag do BeautifulSoup com o link do item.

    Returns:
        dict[str, str]: Dicionário com as informações do item encontrado.
    """
    titulo = link.get_text(strip=True)
    url_encontrada = urljoin(url, link.get("href"))

    if titulo and url_encontrada:
        return {
            "titulo": titulo,
            "url": url_encontrada,
            "resumo": "",
            "lista_origem": url
        }


def analisar_artigo(informacoes_paginas: list[dict[str, str]]) -> list[dict[str, str]]:
    """Percorre todos os links de artigos dos itens secundários e extrai as informações detalhadas.

    Args:
        informacoes_paginas (list[dict[str, str]]): Categorias com as URLs dos artigos.

    Returns:
        list[dict[str, str]]: Lista de dicionários com as informações detalhadas dos artigos.
    """
    print("*"*60)
    itens = []

    for info_pagina in informacoes_paginas:
        resposta = requests.get(info_pagina["url"], headers=CABECALHOS, timeout=20)
        resposta.raise_for_status()
        parser = BeautifulSoup(resposta.text, "html.parser")

        titulo = parser.select_one("div.content h1")
        descricao = parser.select("div.elementor-widget-container p")
        beneficios = parser.select("h4.elementor-icon-box-title span:not(:-soup-contains('Status'))")
        status = parser.select_one("h4.elementor-icon-box-title span:-soup-contains('Status')")
        trl = parser.select_one("div.elementor-icon-box-title span")
        lista_de_inventores = parser.select("div.eael-team-content p")
        departamento = parser.select_one("p.eael-team-text:-soup-contains('Departamento'), p.eael-team-text:-soup-contains('Campus')") # OK
        fone = parser.select_one("p.eael-team-text:-soup-contains('Fone')")
        contato_departamento = parser.select_one("p.eael-team-text a[href]")
        email = parser.select_one("p.eael-team-text:-soup-contains('@')")

        if titulo:

            item = {
                "titulo": titulo.get_text(strip=True) if titulo else "",
                "descricao": " ".join([p.get_text(strip=True) for p in descricao]) if descricao else "",
                "beneficios": [b.get_text(strip=True) for b in beneficios] if beneficios else [],
                "status": status.get_text(strip=True).replace("Status:","").strip() if status else "",
                "trl": trl.get_text(strip=True).replace("TRL:","").strip() if trl else "",
                "lista_de_inventores": [p.get_text(strip=True) for p in lista_de_inventores] if lista_de_inventores else [],
                "departamento": departamento.get_text(strip=True).replace("Departamento:","").replace("Campus:","").strip() if departamento else "",
                "fone": fone.get_text(strip=True).replace("Fone:","").strip() if fone else "",
                "contato_departamento": contato_departamento.get("href") if contato_departamento else "",
                "email": email.get_text(strip=True).strip() if email else "",
                "url": info_pagina["url"]
            }

            print("Artigo lido:", item["titulo"])
            itens.append(item)

    return itens


# Programa principal
vistos = set()
categorias = analisar_pagina_inicial_lista(URL_BASE)
informacoes_paginas = analisar_paginas_secundarias(categorias)
artigos = analisar_artigo(informacoes_paginas)

json.dump(artigos, open("tp1_artigos.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
