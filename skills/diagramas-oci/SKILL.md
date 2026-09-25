---
name: diagramas-oci
description: Diagramas de arquitectura OCI en draw.io con los íconos oficiales de Oracle, vía el MCP de draw.io. Úsala siempre que pidan diagramar o dibujar una arquitectura en OCI.
---

# Diagramas de arquitectura OCI con los íconos oficiales

Los íconos son los del **OCI Architecture Diagram Toolkit v24.2** de Oracle, publicados en el
repositorio `CTH-SOLUCIONES/cth-oci-drawio-icons`. En el XML que va al MCP van **en línea, como
stencils** de draw.io (`shape=stencil(…)`): vectoriales, comprimidos y sin imagen externa. Por URL
no se ven, porque el visor del chat solo carga imágenes de diagrams.net. Antes de entregar se
**embeben siempre** con el script, que los deja canónicos. Nunca uses formas genéricas ni el set
«OCI Icons» que trae el propio servicio de draw.io, porque no son los oficiales.

Esta skill trae consigo el catálogo, con los 232 íconos como stencil, y los scripts. Las rutas son
relativas a la carpeta de esta skill, así que funciona sin red y sin clonar nada.

## 1. Buscar los íconos y los contenedores

No leas `catalogo.json` entero (pesa 700 KB). Búscalo:

```bash
python3 scripts/buscar.py kubernetes          # slug | etiqueta | categoría | ancho x alto
python3 scripts/buscar.py --estilo vault waf  # estilo en línea, listo para pegar, y lo que suma
python3 scripts/buscar.py --contenedores      # región, AD, VCN, subnet… con su estilo
```

Las búsquedas van en inglés, que es el idioma de las etiquetas oficiales. No adivines el slug.
Estos son los más usados:

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

Hay diez contenedores: `region`, `availability-domain`, `fault-domain`, `tenancy`,
`compartment`, `vcn`, `subnet`, `oke-cluster`, `on-premises` e `internet`.

Si un servicio no tiene ícono en el catálogo, dilo. Todo lo que no es OCI (otra nube, el teléfono
del usuario, un sistema del cliente) va con una forma neutra y su nombre.

## 2. Construir el diagrama en el MCP de draw.io

- Usa `create_diagram` en formato `xml`, con `routing: "libavoid"`.
- **Ícono.** Se escribe como `<mxCell value="<etiqueta>" style="<estilo>" vertex="1" parent="1">`,
  con el `width` y el `height` del catálogo. La etiqueta va en `value` y el estilo ya la pone
  debajo del ícono.
- **Copia el estilo de `--estilo` completo y sin tocarlo**, incluida la clave `ociIcon=<slug>`,
  con la que el script identifica el ícono al embeber. Pide el estilo una vez por servicio y
  repítelo en cada celda que lo use.
- **Presupuesto: el XML completo, bajo 30.000 caracteres.** `create_diagram` devuelve el XML
  entero, y el cliente corta los resultados de más de 25.000 tokens. Con unos 50 KB, el visor
  recibió el aviso de error en vez del diagrama. Los íconos más usados pesan 1,4 KB de mediana, y
  una vista física de 9 íconos quedó en 24.000 caracteres. `--estilo` suma lo que pediste y avisa
  si no cabe; cada celda que repite un ícono suma otra vez.
- **Si no cabe**, parte el diagrama en vistas (física y lógica, o por capa) o usa `--url` para los
  íconos. `--url` pesa unos 300 caracteres por ícono, pero el visor muestra el ícono vacío: avísale
  a la persona que lo verá al abrir el archivo en draw.io, y embebe igual antes de entregar.
- **Contenedor.** Lleva su estilo y la etiqueta en `value`. Escribe los contenedores **antes**
  que los íconos para que queden detrás, en este orden: región → VCN → subnet.
- Las páginas «Logical» y «Physical» del toolkit fijan la convención. La vista física lleva
  región, AD, VCN y subnets. La lógica lleva capas y flujos, sin topología de red.
- Si el MCP de draw.io no está conectado, dilo antes de seguir. Después escribe el `.drawio`
  directamente con los mismos estilos y reglas.

## 3. Reglas de diagramación

El visor del chat aplica el `libavoid`, pero **el XML guardado queda con el enrutado por
defecto de draw.io**. El diagrama tiene que verse bien también así. Estas reglas se verificaron
renderizando con ese enrutado por defecto:

- **El flujo va de izquierda a derecha.** La entrada (usuario, internet, WAF) queda a la
  izquierda y los datos y servicios a la derecha. Usa una grilla de 10. Deja al menos 200 px
  entre columnas de íconos y 90 px entre filas, para que quepan la etiqueta y el tronco de las
  flechas.
- **Cada flecha declara por dónde sale y por dónde entra.** Sale por la derecha y entra por la
  izquierda. Si no lo declaras, draw.io entra a los destinos por arriba o por abajo, junta
  varias flechas en una línea que atraviesa íconos y sale por debajo del ícono, encima de su
  etiqueta. Este es el estilo:
  `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#312D2A;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;`
- **Alinea los centros de cada fila** con `y = centro_de_fila − alto/2`. Como los íconos no
  miden lo mismo, alinear solo el borde superior hace que las flechas horizontales tengan un
  escalón.
- **Si un nodo reparte a varios, apila los destinos en una columna.** Con los puertos de arriba,
  draw.io arma un tronco vertical entre las dos columnas sin tocar ningún ícono.
- **Nada sale por abajo de un ícono**, porque ahí está su etiqueta. Tampoco debe bajar ninguna
  flecha a través de la etiqueta de un contenedor, que va arriba a la izquierda.
- **El margen inferior de un contenedor debe contar la etiqueta del ícono.** Deja al menos 60 px
  entre el borde inferior del ícono más bajo y el borde del contenedor. Los demás márgenes son de
  40 px.
- Pon texto en una flecha solo cuando aclare el protocolo o el flujo.

## 4. Guardar y entregar

1. Guarda el XML como `.drawio`, envuelto en `<mxfile><diagram name="…">…</diagram></mxfile>`.
   Va en la carpeta del proyecto o, en claude.ai, como archivo descargable.
2. **Embebe siempre** con `python3 scripts/embeber.py diagrama.drawio`, aunque los íconos ya
   vayan en línea. El script pone en cada celda con `ociIcon` el stencil canónico del catálogo,
   sin red, y deja un `.bak`. Conserva lo demás que tenga la celda, como el tamaño de letra. Así
   corrige cualquier copia mal transcrita y cambia las URLs por el stencil, y el entregable queda
   autocontenido.
3. **Revisa el resultado antes de entregarlo.**
   - Si está draw.io de escritorio, renderiza y abre el PNG. En macOS es
     `/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -s 2 -o revision.png diagrama.drawio`,
     y en Linux es el mismo comando con `drawio`.
   - Sin draw.io de escritorio, la revisión es el visor del MCP.
   - Si una flecha cruza una etiqueta o un ícono, corrige la posición según §3.

## Propiedad

Los íconos son © Oracle, publicados para dibujar diagramas de implementaciones de OCI. Úsalos
solo para eso. El repositorio no concede ninguna licencia sobre ellos; ver su `NOTICE.md`.
