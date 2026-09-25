---
name: diagramas-oci
description: Diagramas de arquitectura de Oracle Cloud Infrastructure (OCI) en draw.io con los íconos oficiales del toolkit de Oracle, hechos con el servidor MCP de draw.io. Úsala siempre que pidan un diagrama, vista lógica o física, o dibujo de una arquitectura en OCI (OKE, Autonomous Database, VCN, subnets, Vault, Object Storage, OCI Generative AI…), aunque no nombren draw.io ni los íconos.
---

# Diagramas de arquitectura OCI con los íconos oficiales

Los íconos son los del **OCI Architecture Diagram Toolkit v24.2** de Oracle, un SVG por ícono, en
`CTH-SOLUCIONES/cth-oci-drawio-icons`. Se referencian por URL mientras se diseña (el XML queda
chico y cabe en una llamada al MCP) y se **embeben siempre** antes de entregar. Nunca se usan formas
genéricas ni el set «OCI Icons» que trae el propio servicio de draw.io: no son los oficiales.

## 1. Buscar los íconos y los contenedores

El catálogo trae, por ícono, `slug`, etiqueta oficial, categoría, `ancho`, `alto` y el `estilo` listo
para pegar, y 10 contenedores con el estilo de la leyenda del toolkit:

- En disco: `/Volumes/cribonSSD/CTH/projects/cth-oci-drawio-icons/catalogo.json` (y `catalogo.md`).
- Por red: `https://cdn.jsdelivr.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@v24.2.1/catalogo.json`.

Busca por slug o por etiqueta; no adivines el nombre del archivo. Los más usados:

| Servicio | slug | Servicio | slug |
|---|---|---|---|
| OKE | `container-engine-for-kubernetes` | Load Balancer | `load-balancer` |
| Container Registry | `container-registry` | API Gateway | `api-gateway` |
| Autonomous Database | `oracle-autonomous-database` | WAF | `waf` |
| Base Database | `oracle-base-database` | Bastion | `bastion` |
| Object Storage | `object-storage-buckets` | DRG | `drg` |
| Block / File Storage | `block-storage` / `file-storage` | Internet / NAT / Service Gateway | `internet-gateway` / `nat-gateway` / `service-gateway` |
| Vault | `vault` | NSG | `nsg` |
| Key Management | `key-management` | IAM | `iam` |
| Functions | `functions` | DNS | `dns` |
| Streaming / Queue | `streaming` / `queue` | Logging / Monitoring | `logging` / `monitoring` |
| Generative AI | `generative-ai` | Notifications / Events | `notifications` / `events` |
| Document Understanding | `document-understanding` | Vision | `vision` |
| VM | `virtual-machine` | Usuario | `user` |

Contenedores (`contenedores` del catálogo): `region`, `availability-domain`, `fault-domain`,
`tenancy`, `compartment`, `vcn`, `subnet`, `oke-cluster`, `on-premises`, `internet`.

Si un ícono no está, dilo. El respaldo es la librería de 2022 en
`/Volumes/cribonSSD/CTH/projects/OCI Style Guide for Drawio/OCI Library.xml`, avisando. Lo que no es
OCI (otra nube, el teléfono del usuario, un sistema del cliente) va con una forma neutra y su nombre.

## 2. Construir el diagrama en el MCP de draw.io

- Formato `xml` de `create_diagram`, con `routing: "libavoid"`.
- **Ícono:** `<mxCell value="<etiqueta>" style="<estilo del catálogo>" vertex="1" parent="1">` con
  `width`/`height` del catálogo. La etiqueta va en `value`; el estilo ya la pone debajo.
- **Contenedor:** su `estilo` del catálogo, con la etiqueta en `value`. Los contenedores se escriben
  **antes** que los íconos, para quedar detrás, en este orden: región → VCN → subnet.
- Las páginas «Logical» y «Physical» del toolkit fijan la convención: la vista física lleva región,
  AD, VCN y subnets; la lógica, capas y flujos sin topología de red.

## 3. Reglas de diagramación

El `libavoid` lo aplica el visor del chat; **el XML guardado queda con el enrutado por defecto de
draw.io**. El diagrama tiene que verse bien también así:

Reglas verificadas renderizando con el enrutado por defecto:

- **El flujo va de izquierda a derecha**: entrada (usuario, internet, WAF) a la izquierda, datos
  y servicios a la derecha. Grilla de 10; entre columnas de íconos, al menos 200 px; entre filas,
  al menos 90 px, para que quepan la etiqueta y el tronco de las flechas.
- **Cada flecha declara por dónde sale y por dónde entra**: sale por la derecha y entra por la
  izquierda. Sin eso, draw.io entra a los destinos por arriba o por abajo, junta varias flechas en
  una línea que atraviesa íconos y sale por debajo del ícono, sobre su etiqueta. Estilo:
  `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#312D2A;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;`
- **Alinea los centros de una fila**: `y = centro_de_fila − alto/2`. Si solo alineas el borde
  superior, las flechas horizontales hacen un escalón, porque los íconos no miden lo mismo.
- **Si un nodo reparte a varios, apila los destinos en una columna.** Con los puertos de arriba,
  draw.io arma un tronco vertical entre las dos columnas sin tocar ningún ícono.
- **Nada sale por abajo de un ícono**, porque ahí está su etiqueta, y ninguna flecha baja atravesando
  la etiqueta de un contenedor, que va arriba a la izquierda.
- **El margen inferior de un contenedor cuenta la etiqueta del ícono**: al menos 60 px entre el
  borde inferior del ícono más bajo y el borde del contenedor. Los demás márgenes, 40 px.
- Texto en una flecha solo cuando aclara el protocolo o el flujo.

## 4. Guardar y entregar

1. Guarda el XML que devolvió el MCP como `.drawio` en la carpeta del proyecto, envuelto en
   `<mxfile><diagram name="…">…</diagram></mxfile>`.
2. **Embebe siempre**: `python3 /Volumes/cribonSSD/CTH/projects/cth-oci-drawio-icons/scripts/embeber.py diagrama.drawio`.
   Sin el repo en disco: `curl -sL https://raw.githubusercontent.com/CTH-SOLUCIONES/cth-oci-drawio-icons/v24.2.1/scripts/embeber.py | python3 - diagrama.drawio`.
   El entregable queda autocontenido y no depende de la red.
3. **Mira el resultado antes de entregarlo**: `/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -s 2 -o revision.png diagrama.drawio`
   y abre el PNG. Si una flecha cruza una etiqueta o un ícono, corrige la posición según §3.

## Propiedad

Los íconos son © Oracle, publicados para dibujar diagramas de implementaciones de OCI. Úsalos solo
para eso; el repositorio no concede ninguna licencia sobre ellos (ver su `NOTICE.md`).
