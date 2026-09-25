"""Extrae los íconos del OCI Architecture Diagram Toolkit de Oracle a un SVG por ícono y arma el catálogo.

Segmenta la página «Icons» por posición (formas que se tocan = un pictograma; el texto justo
debajo = su etiqueta; el encabezado más cercano por encima = su categoría), exporta cada
pictograma con el CLI de draw.io, lo adelgaza con `optimizar.py` y toma los contenedores de la
leyenda de la página «Physical». Escribe `svg/`, `catalogo.json` y `catalogo.md`.

Uso: extraer.py   (toolkit en la variable OCI_TOOLKIT; exige /Applications/draw.io.app y npx)
"""
import re,zlib,base64,urllib.parse,html,collections,json,sys
import xml.etree.ElementTree as ET
import os,sys
TK=os.environ.get("OCI_TOOLKIT","/Volumes/cribonSSD/CTH/projects/OCI Style Guide for Drawio/OCI Architecture Diagram Toolkit v24.2.drawio")
def inflate(s):
    try: return urllib.parse.unquote(zlib.decompress(base64.b64decode(s),-15).decode())
    except Exception: return s
def pagina(nombre):
    s=open(TK,encoding='utf-8').read()
    a,b=[d for d in re.findall(r'<diagram([^>]*)>(.*?)</diagram>',s,re.S) if f'name="{nombre}"' in d[0]][0]
    return ET.fromstring(b if b.strip().startswith('<') else inflate(b.strip()))
def texto(v):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',html.unescape(v or '')))).strip()
def normalizar(root):
    """Devuelve celdas con id, parent, style, value y geometría, resolviendo los envoltorios
    <object>/<UserObject>, que llevan el id y la etiqueta fuera de la mxCell."""
    out=[]
    for el in root.iter():
        if el.tag in ('object','UserObject'):
            c=el.find('mxCell')
            if c is None: continue
            d=dict(c.attrib); d['id']=el.get('id'); d['value']=el.get('label',el.get('value',''))
            out.append((d,c))
        elif el.tag=='mxCell' and el.get('id') is not None:
            out.append((dict(el.attrib),el))
    return out
class _C:
    def __init__(self,d,el): self.d=d; self.el=el
    def get(self,k,default=None): return self.d.get(k,default)
    def find(self,t): return self.el.find(t)
def celdas(root):
    cells=[_C(d,el) for d,el in normalizar(root)]; by={c.get('id'):c for c in cells}
    def geo(c):
        g=c.find('mxGeometry'); 
        if g is None: return None
        return [float(g.get(k,0)) for k in ('x','y','width','height')]
    def absxy(c):
        x=y=0.0; p=c
        while p is not None and p.get('parent') not in (None,'0','1'):
            par=by.get(p.get('parent')); 
            if par is None: break
            g=geo(par); 
            if g: x+=g[0]; y+=g[1]
            p=par
        return x,y
    out=[]
    for c in cells:
        if c.get('vertex')!='1': continue
        st=c.get('style') or ''
        if st.startswith('group'): continue
        g=geo(c); 
        if not g: continue
        ox,oy=absxy(c)
        out.append(dict(id=c.get('id'),x=g[0]+ox,y=g[1]+oy,w=g[2],h=g[3],style=st,txt=texto(c.get('value')),cell=c))
    return out
def segmentar(root):
    cs=celdas(root)
    def invisible(c):
        st=c['style']
        return ('fillColor=none' in st or 'fillColor' not in st) and ('strokeColor=none' in st)
    textos=[c for c in cs if c['txt']]
    formas=[c for c in cs if not c['txt'] and not invisible(c) and c['w']<=150 and c['h']<=150]
    # unir formas que se tocan (tolerancia 2 px)
    padre=list(range(len(formas)))
    def f(i):
        while padre[i]!=i: padre[i]=padre[padre[i]]; i=padre[i]
        return i
    orden=sorted(range(len(formas)),key=lambda i:formas[i]['x'])
    for a in range(len(orden)):
        i=orden[a]; A=formas[i]
        for b in range(a+1,len(orden)):
            j=orden[b]; B=formas[j]
            if B['x']>A['x']+A['w']+2: break
            if not (B['y']>A['y']+A['h']+2 or A['y']>B['y']+B['h']+2): padre[f(i)]=f(j)
    grupos=collections.defaultdict(list)
    for i,c in enumerate(formas): grupos[f(i)].append(c)
    iconos=[]
    for g in grupos.values():
        x0=min(c['x'] for c in g); y0=min(c['y'] for c in g); x1=max(c['x']+c['w'] for c in g); y1=max(c['y']+c['h'] for c in g)
        iconos.append(dict(partes=g,x=x0,y=y0,w=x1-x0,h=y1-y0))
    # etiqueta: textos cuyo borde superior cae hasta 40 px bajo el pictograma y cuyo centro horizontal cae dentro de su ancho ampliado
    for ic in iconos:
        cx=ic['x']+ic['w']/2
        cand=[t for t in textos if 0<=t['y']-(ic['y']+ic['h'])<=40 and abs((t['x']+t['w']/2)-cx)<=max(ic['w'],t['w'])/2+5]
        cand.sort(key=lambda t:(t['y'],t['x']))
        ic['etiqueta']=' '.join(t['txt'] for t in cand).strip()
    return iconos,textos
import os,xml.sax.saxutils as su
def slug(t):
    import unicodedata
    t=unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower()
    t=re.sub(r'^oci\s+','',t); t=re.sub(r'[^a-z0-9]+','-',t).strip('-')
    return t
def drawio_de(ic):
    x0,y0=ic['x'],ic['y']; celdas=[]
    for k,p in enumerate(ic['partes']):
        st=su.escape(p['style'],{'"':'&quot;'})
        celdas.append(f'<mxCell id="c{k}" value="" style="{st}" vertex="1" parent="1"><mxGeometry x="{p["x"]-x0:.3f}" y="{p["y"]-y0:.3f}" width="{p["w"]:.3f}" height="{p["h"]:.3f}" as="geometry"/></mxCell>')
    return ('<mxfile><diagram name="icono" id="i"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + ''.join(celdas) + '</root></mxGraphModel></diagram></mxfile>')
def categorias(iconos,textos,etiquetas_usadas):
    heads=[t for t in textos if t['txt'] not in etiquetas_usadas and ('fontStyle=1' in t['style'] or 'font-weight' in (t['cell'].get('value') or '') or 'bold' in (t['cell'].get('value') or '').lower())]
    for ic in iconos:
        arriba=[h for h in heads if h['y']<ic['y'] and h['x']-20<=ic['x']<=h['x']+1600]
        ic['categoria']=max(arriba,key=lambda h:h['y'])['txt'] if arriba else ''
    return heads

# ----------------------------------------------------------------------------- catálogo
REPO = "CTH-SOLUCIONES/cth-oci-drawio-icons"
VERSION = "v24.2.2"  # toolkit 24.2 de Oracle; el último dígito es la revisión de este repo
BASE_URL = f"https://cdn.jsdelivr.net/gh/{REPO}@{VERSION}/svg"
ESTILO_ICONO = ("shape=image;html=1;verticalLabelPosition=bottom;verticalAlign=top;labelBackgroundColor=none;"
                "imageAspect=0;aspect=fixed;fontFamily=Oracle Sans;fontSize=11;fontColor=#312D2A;ociIcon={slug};image={url}")
# `ociIcon` no es de draw.io, que conserva las claves que no conoce: identifica el ícono aunque la
# imagen vaya en línea, para que `embeber.py` la reemplace por la canónica.
CONTENEDORES = {  # tipo -> etiqueta que lo identifica en la leyenda de la página Physical
    "region": "OCI Region", "availability-domain": "Availability Domain", "fault-domain": "Fault Domain",
    "tenancy": "Tenancy", "compartment": "Compartment A", "vcn": "VCN", "subnet": "Subnet 0.0.0.0/00",
    "oke-cluster": "Container Engine for Kubernetes Cluster", "on-premises": "On-Premises", "internet": "Internet",
}
def contenedores():
    cs = celdas(pagina("Physical")); out = []
    for tipo, etiqueta in CONTENEDORES.items():
        cand = [c for c in cs if c["txt"].startswith(etiqueta) and c["w"] > 80 and c["h"] > 40]
        cand.sort(key=lambda c: (c["w"] * c["h"]))  # la muestra de la leyenda es la más chica
        if cand:
            c = cand[0]
            out.append(dict(tipo=tipo, etiqueta=etiqueta, estilo=c["style"], ancho=round(c["w"]), alto=round(c["h"])))
    return out


def main():
    import json, shutil, subprocess, tempfile, collections
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    iconos, textos = segmentar(pagina("Icons"))
    usados = set()
    for ic in iconos:
        cx = ic["x"] + ic["w"] / 2
        for t in textos:
            if 0 <= t["y"] - (ic["y"] + ic["h"]) <= 40 and abs((t["x"] + t["w"] / 2) - cx) <= max(ic["w"], t["w"]) / 2 + 5:
                usados.add(t["id"])
    encabezados = sorted([t for t in textos if t["id"] not in usados], key=lambda t: t["y"])
    for ic in iconos:
        arriba = [h for h in encabezados if h["y"] <= ic["y"]]
        ic["categoria"] = arriba[-1]["txt"] if arriba else "Other"
    iconos.sort(key=lambda i: (i["y"], i["x"]))
    cuenta, cat = collections.Counter(), []
    tmp = tempfile.mkdtemp()
    for ic in iconos:
        base = slug(ic["etiqueta"]) or "icono"; cuenta[base] += 1
        s = base if cuenta[base] == 1 else f"{base}-{cuenta[base]}"
        open(os.path.join(tmp, s + ".drawio"), "w").write(drawio_de(ic))
        cat.append(dict(slug=s, etiqueta=ic["etiqueta"], categoria=ic["categoria"], ancho=round(ic["w"]), alto=round(ic["h"]),
                        archivo=f"svg/{s}.svg", estilo=ESTILO_ICONO.format(slug=s, url=f"{BASE_URL}/{s}.svg")))
    os.makedirs(os.path.join(raiz, "svg"), exist_ok=True)
    # `--theme light`: sin él, draw.io exporta colores adaptativos (light-dark) y en un visor oscuro el
    # interior blanco de los íconos sale negro.
    subprocess.run(["/Applications/draw.io.app/Contents/MacOS/draw.io", "-x", "-f", "svg", "-b", "0", "--theme", "light",
                    "-o", os.path.join(raiz, "svg"), tmp], check=True, capture_output=True)
    shutil.rmtree(tmp)
    subprocess.run([sys.executable, os.path.join(raiz, "scripts", "optimizar.py"), os.path.join(raiz, "svg")], check=True)
    json.dump(dict(fuente=f"OCI Architecture Diagram Toolkit {VERSION} (Oracle), página Icons y leyenda de la página Physical",
                   version=VERSION, base_url=BASE_URL, iconos=cat, contenedores=contenedores()),
              open(os.path.join(raiz, "catalogo.json"), "w"), ensure_ascii=False, indent=1)
    escribir_md(cat, contenedores(), os.path.join(raiz, "catalogo.md"))
    print(f"{len(cat)} íconos exportados a svg/ y catálogo escrito")


def escribir_md(cat, conts, ruta):
    lineas = ["# Catálogo de íconos OCI para draw.io", "",
              f"Toolkit v24.2 (revisión {VERSION}). Estilo base de cada ícono en `catalogo.json`; "
              f"URL: `{BASE_URL}/<slug>.svg`.", ""]
    for categoria in sorted({i["categoria"] for i in cat}):
        lineas += [f"## {categoria}", "", "| slug | Etiqueta oficial | Tamaño |", "|---|---|---|"]
        lineas += [f"| `{i['slug']}` | {i['etiqueta']} | {i['ancho']}×{i['alto']} |" for i in cat if i["categoria"] == categoria]
        lineas.append("")
    lineas += ["## Contenedores (vista física)", "", "| tipo | Etiqueta en el toolkit | Tamaño de referencia |", "|---|---|---|"]
    lineas += [f"| `{c['tipo']}` | {c['etiqueta']} | {c['ancho']}×{c['alto']} |" for c in conts]
    open(ruta, "w", encoding="utf-8").write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    main()
