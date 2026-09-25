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
| `skills/diagramas-oci/` | Skill para agentes: cómo buscar los íconos, armar el diagrama en el MCP, las reglas de diagramación verificadas y la entrega |

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

Para que un agente lo haga siempre igual: `npx skills@latest add CTH-SOLUCIONES/cth-oci-drawio-icons -g -y`.
Queda disponible para Claude Code y los demás agentes que gestiona la CLI `skills`; en Claude
Desktop se sube como skill desde la configuración.

## Propiedad de los íconos

Los íconos son **de Oracle** (© Oracle y/o sus afiliadas) y vienen del toolkit que Oracle publica
en su [documentación](https://docs.oracle.com/en-us/iaas/Content/General/Reference/graphicsfordiagrams.htm)
para «draw custom architecture diagrams for your OCI implementation». Este repositorio **no concede
ninguna licencia** sobre ellos: solo los reorganiza para ese uso. Ver `NOTICE.md`.
