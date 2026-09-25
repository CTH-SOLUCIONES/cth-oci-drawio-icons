# cth-oci-drawio-icons

Los íconos oficiales de OCI, del **OCI Architecture Diagram Toolkit v24.2** de Oracle, convertidos
a un SVG por ícono para usarlos por URL con el servidor MCP de draw.io.

## Por qué existe

Los íconos del toolkit son grupos de formas vectoriales de 5 a 20 KB cada uno. Metidos en el XML
de un diagrama, una vista física real pesa 150–200 KB, demasiado para escribirla en una llamada al
MCP. Referenciados por URL, cada ícono ocupa unos 260 caracteres y el diagrama entero cabe en una
llamada, se ve en el chat y se ajusta ahí mismo. El set «OCI Icons» que trae el propio servicio de
draw.io no sirve: son glifos genéricos en negro, no los íconos oficiales.

**Para quién:** quien diagrame arquitecturas de OCI en CTH Soluciones, sea una persona o un agente.

## Qué hay

| Ruta | Contenido |
|---|---|
| `svg/<slug>.svg` | 232 íconos, exportados con draw.io desde la página «Icons» del toolkit, sin redibujar |
| `catalogo.json` | Por ícono: slug, etiqueta oficial, categoría, tamaño y el estilo listo para pegar; y 10 contenedores de la vista física (región, AD, fault domain, tenancy, compartment, VCN, subnet, clúster OKE, on-premises, internet) con el estilo de la leyenda del toolkit |
| `catalogo.md` | La misma lista, legible, por categoría |
| `scripts/extraer.py` | Regenera todo desde el `.drawio` del toolkit cuando Oracle publique una versión nueva |
| `scripts/embeber.py` | Reemplaza las URLs por los SVG en línea para el entregable |
| `scripts/buscar.py` | Busca en el catálogo por slug, etiqueta o categoría, sin cargarlo entero |
| `scripts/empaquetar.py` | Copia íconos, catálogo y scripts a la skill y arma `dist/diagramas-oci.zip` |
| `skills/diagramas-oci/` | Skill para agentes, autocontenida: cómo buscar los íconos, armar el diagrama en el MCP, las reglas de diagramación verificadas y la entrega |

## Cómo se usa

1. **Diseñar con el MCP de draw.io.** Cada ícono es una celda con el `estilo` del catálogo y la
   etiqueta en `value`; cada contenedor, una celda con su estilo. URL de un ícono:
   `https://cdn.jsdelivr.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@v24.2.1/svg/<slug>.svg`.
2. **Guardar el XML** que devuelve el MCP como `.drawio` en la carpeta del proyecto.
3. **Embeber antes de entregar**, siempre: `python3 scripts/embeber.py diagrama.drawio`. El
   entregable queda autocontenido: no depende de este repositorio ni de la red.

La URL fija la versión (`@v24.2.1`: toolkit 24.2 de Oracle, revisión 1 de este repositorio): cuando llegue otra, los diagramas viejos siguen apuntando a la
suya.

## La skill

La skill `diagramas-oci` hace que un agente lo haga siempre igual. Lleva su propia copia de los
íconos, del catálogo y de los scripts, porque en claude.ai el entorno de ejecución solo sale por
defecto a gestores de paquetes y no alcanzaría el CDN para embeber. Los íconos van juntos en
`iconos.json` y no uno por archivo, porque la subida de skills en claude.ai rechaza zips de más de
200 archivos. La fuente de verdad es la raíz
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
