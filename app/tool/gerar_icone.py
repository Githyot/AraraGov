#!/usr/bin/env python3
"""Gera o ícone do AraraGov: a cabeça da Arara (mascote do Reelhouse, mesmo
criador) no centro da bandeira do Brasil.

    python3 app/tool/gerar_icone.py

Lê a cabeça de app/assets/mascote/arara-logo.svg e escreve
app/assets/icone/araragov.svg (quadrado, para iOS/Android) e
app/assets/icone/araragov-arredondado.svg (cantos arredondados, desktop).
Os PNGs são gerados a partir desses SVGs (ver app/tool/rasterizar.js).
"""

import copy
import os
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
AQUI = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(AQUI, "..", "assets")

# Cores oficiais da bandeira (Lei 5.700/71, valores RGB usuais)
VERDE, AMARELO, AZUL, BRANCO = "#009C3B", "#FFDF00", "#002776", "#FFFFFF"


def cabeca_e_gradientes():
    raiz = ET.parse(os.path.join(ASSETS, "mascote", "arara-logo.svg")).getroot()
    defs = [copy.deepcopy(d) for d in raiz.iter(f"{{{NS}}}defs")]
    cabeca = next(g for g in raiz.iter(f"{{{NS}}}g") if g.get("id") == "head")
    return defs, copy.deepcopy(cabeca)


def icone(arredondado: bool) -> str:
    defs, cabeca = cabeca_e_gradientes()
    svg = ET.Element(f"{{{NS}}}svg", {"viewBox": "0 0 512 512", "width": "512", "height": "512"})
    ET.SubElement(svg, f"{{{NS}}}title").text = "AraraGov"
    for d in defs:
        svg.append(d)
    rx = "112" if arredondado else "0"
    ET.SubElement(svg, f"{{{NS}}}rect", {"width": "512", "height": "512", "rx": rx, "fill": VERDE})
    ET.SubElement(
        svg, f"{{{NS}}}polygon", {"points": "40,256 256,96 472,256 256,416", "fill": AMARELO}
    )
    ET.SubElement(svg, f"{{{NS}}}circle", {"cx": "256", "cy": "268", "r": "128", "fill": AZUL})
    ET.SubElement(svg, f"{{{NS}}}circle", {"cx": "256", "cy": "268", "r": "128", "fill": "none",
                                           "stroke": BRANCO, "stroke-width": "10"})
    # A cabeça original tem centro em (128, 106) e ~136 px de largura.
    grupo = ET.SubElement(svg, f"{{{NS}}}g", {"transform": "translate(256 262) scale(1.55) translate(-128 -106)"})
    grupo.append(cabeca)
    return ET.tostring(svg, encoding="unicode")


if __name__ == "__main__":
    for nome, arred in (("araragov.svg", False), ("araragov-arredondado.svg", True)):
        caminho = os.path.join(ASSETS, "icone", nome)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(icone(arred))
        print("escrito", caminho)
