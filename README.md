# cth-oci-drawio-icons

Los íconos oficiales de OCI, del **OCI Architecture Diagram Toolkit v24.2** de Oracle, convertidos
a stencils de draw.io y a SVG optimizados para usarlos con el servidor MCP de draw.io.

## Por qué existe

Los íconos del toolkit son grupos de formas vectoriales de 5 a 20 KB cada uno. Metidos en el XML
de un diagrama, una vista física real pesa 150–200 KB, demasiado para escribirla en una llamada al
MCP. Además, `create_diagram` devuelve el XML entero, y el cliente corta los resultados de más de
25.000 tokens: un XML de unos 50 KB le llegó al visor como aviso de error.

Hay dos formas de usarlos:

- **En línea, como stencil** (`shape=stencil(…)`, vectorial y comprimido): se ven en el visor del
  chat. Pesan 1,4 KB de mediana entre los más usados, y una vista física de 9 íconos queda en unos
  24.000 caracteres.
- **Por URL del CDN**: unos 300 caracteres por ícono, pero **el visor del chat no los muestra**.
  Su política de contenido solo deja cargar imágenes de diagrams.net o en línea. draw.io, en
  cambio, sí los abre.

El set «OCI Icons» que trae el propio servicio de draw.io no sirve: son glifos genéricos en negro,
no los íconos oficiales.

**Para quién:** quien diagrame arquitecturas de OCI en CTH Soluciones, sea una persona o un agente.

## Qué hay

| Ruta | Contenido |
|---|---|
| `svg/<slug>.svg` | 232 íconos, exportados con draw.io desde la página «Icons» del toolkit, sin redibujar, y optimizados con SVGO a 0,01 px |
| `catalogo.json` | Por ícono: slug, etiqueta oficial, categoría, tamaño, el estilo en línea (`estilo`, stencil) y el estilo por URL (`estilo_url`); y 10 contenedores de la vista física (región, AD, fault domain, tenancy, compartment, VCN, subnet, clúster OKE, on-premises, internet) con el estilo de la leyenda del toolkit |
| `catalogo.md` | La misma lista, legible, por categoría |
| `scripts/extraer.py` | Regenera todo desde el `.drawio` del toolkit cuando Oracle publique una versión nueva |
| `scripts/optimizar.py` | Adelgaza los SVG exportados. Lo llama `extraer.py` |
| `scripts/stencil.py` | Convierte cada SVG en stencil de draw.io, con coordenadas absolutas a 0,1 px. Lo llama `extraer.py` |
| `scripts/buscar.py` | Busca en el catálogo sin cargarlo entero, da el estilo en línea (`--estilo`) o por URL (`--url`) y suma contra el presupuesto de 30.000 caracteres |
| `scripts/embeber.py` | Deja en el entregable cada ícono como el stencil canónico, conservando el resto del estilo de la celda |
| `scripts/empaquetar.py` | Copia íconos, catálogo y scripts a la skill y arma `dist/diagramas-oci.zip` |
| `skills/diagramas-oci/` | Skill para agentes, autocontenida: cómo buscar los íconos, armar el diagrama en el MCP, las reglas de diagramación verificadas y la entrega |

## Cómo se usa

1. **Diseñar con el MCP de draw.io.** Cada ícono es una celda con el estilo que da
   `python3 scripts/buscar.py --estilo <slug>` y la etiqueta en `value`. Cada contenedor es una
   celda con su estilo. Todo estilo de ícono lleva `ociIcon=<slug>`, una clave que draw.io conserva
   y que identifica el ícono aunque la imagen vaya en línea.
2. **Guardar el XML** que devuelve el MCP como `.drawio` en la carpeta del proyecto.
3. **Embeber antes de entregar**, siempre: `python3 scripts/embeber.py diagrama.drawio`.
   - Pone en cada celda con `ociIcon` el stencil canónico, así corrige una copia mal transcrita y
     cambia las URLs por el stencil.
   - Los diagramas anteriores a `ociIcon` se reconocen por la URL del CDN.
   - El entregable queda autocontenido: no depende de este repositorio ni de la red.

La URL fija la versión: `@v24.2.3` es el toolkit 24.2 de Oracle en la revisión 3 de este
repositorio. Cuando llegue otra, los diagramas viejos siguen apuntando a la suya. Las revisiones
cambian la codificación, no el dibujo:
- se retiró la v24.2 por los colores adaptativos;
- la v24.2.1 son los SVG sin optimizar;
- la v24.2.2 embebía los SVG en base64 y desbordaba el resultado del MCP.

## La skill

La skill `diagramas-oci` hace que un agente lo haga siempre igual. Lleva su propia copia de los
íconos, del catálogo y de los scripts, porque en claude.ai el entorno de ejecución solo sale por
defecto a gestores de paquetes y no alcanzaría el CDN para embeber. Los íconos van dentro del
catálogo, como stencils, y no uno por archivo, porque la subida de skills en claude.ai rechaza zips
de más de 200 archivos. La fuente de verdad es la raíz
del repositorio, y `python3 scripts/empaquetar.py` sincroniza la copia y arma el `.zip`. Córrelo
antes de cada commit que toque `svg/`, el catálogo o los scripts.

**Para la organización en Claude:** el propietario sube `dist/diagramas-oci.zip` en
*Organization settings > Plugins & skills > Add > Upload a skill*. Con eso queda activa para
todos los miembros en claude.ai, Claude Desktop, Cowork y Claude Code con sesión de la
organización. Cada miembro puede apagarla, pero no borrarla. Requiere que la pestaña *Policy*
tenga activos *Cloud code execution and file creation* y *Skills*. Al diseñar, cada miembro necesita
además el conector de draw.io.

**Fuera de la organización, o en otros agentes** (Codex, Gemini CLI…):
`npx skills@latest add CTH-SOLUCIONES/cth-oci-drawio-icons -g -y`.

## Propiedad de los íconos

Los íconos son **de Oracle** (© Oracle y/o sus afiliadas) y vienen del toolkit que Oracle publica
en su [documentación](https://docs.oracle.com/en-us/iaas/Content/General/Reference/graphicsfordiagrams.htm)
para «draw custom architecture diagrams for your OCI implementation». Este repositorio **no concede
ninguna licencia** sobre ellos: solo los reorganiza para ese uso. Ver `NOTICE.md`.
