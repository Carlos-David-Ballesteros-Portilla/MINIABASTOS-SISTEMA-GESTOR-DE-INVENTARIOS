# MINIABASTOS – Sistema de control de inventario

Prototipo de escritorio para llevar el inventario de una tienda de barrio: productos, existencias,
entradas y ajustes, ventas con varios productos, anulaciones, alertas de stock y reportes.

Tecnologías: **Python + Tkinter + SQLite (`sqlite3`)**, arquitectura **MVC** con capa de servicios y pruebas con **`unittest`**.
No usa dependencias externas ni frameworks web.

## Requisitos

- **Python 3** con **Tkinter** incluido. Desarrollado y probado con Python 3.12 y 3.13.
- En Windows y macOS, Tkinter viene con el instalador oficial de Python.
- En Linux (Debian/Ubuntu) puede requerir: `sudo apt install python3-tk`.

## Instalación

No hay nada que instalar. `requirements.txt` existe por convención y no lista paquetes.

```bash
cd miniabastos
```

## Cómo iniciar el programa

```bash
python main.py            # usa la base de datos real: miniabastos.db
python main.py --demo     # usa miniabastos_demo.db (separada) con datos de ejemplo
python main.py --db RUTA  # usa una base de datos en otra ubicación
```

La primera vez que se ejecuta, la base de datos y su esquema se crean automáticamente.
(En algunos sistemas el comando es `python3`.)

## Cómo ejecutar las pruebas

Desde la carpeta `miniabastos`:

```bash
python -m unittest            # descubre y ejecuta todas las pruebas
python -m unittest -v         # con detalle
```

Cada prueba crea una base de datos **temporal** y la elimina al terminar: nunca toca `miniabastos.db`.

## Dónde se almacena la base de datos

- Por defecto: `miniabastos.db`, en la carpeta del proyecto (junto a `main.py`).
- Se puede cambiar con `--db RUTA` o con la variable de entorno `MINIABASTOS_DB`.
- Datos de demostración: `miniabastos_demo.db` (solo con `--demo`; nunca se mezclan con los reales).
- Para respaldar la información basta copiar el archivo `.db` con la aplicación cerrada.

## Estructura

```
miniabastos/
├── main.py                  Punto de entrada (arma controladores y abre la ventana)
├── demo_data.py             Datos de demostración opcionales (solo con --demo)
├── database/
│   ├── connection.py        Conexión SQLite (claves foráneas ON) y transacciones
│   ├── schema.sql           Esquema: tablas, restricciones, índices y triggers
│   └── initialization.py    Creación automática de la base de datos
├── models/                  Acceso a datos (SQL parametrizado)
├── services/                Operaciones transaccionales (inventario, ventas, anulaciones)
├── controllers/             Validan la entrada, coordinan y devuelven resultados
├── views/                   Interfaz Tkinter/ttk (sin SQL ni reglas de negocio)
├── utils/                   Validadores, formateadores, cálculos y errores de negocio
└── tests/                   Pruebas unittest
```

Responsabilidades: las **vistas** solo muestran y capturan; los **controladores** validan y coordinan;
los **servicios** concentran las reglas que tocan varias tablas (el único código que modifica
`stock_actual` es `InventarioService`); los **modelos** ejecutan el SQL.

## Cantidades y dinero

- **Cantidades**: enteros escalados ×1000 (1 unidad = 1000; 0,5 kg = 500; 1,250 kg = 1250), convertidos con `Decimal`.
  La interfaz nunca muestra el valor escalado. Nunca se usa `float`.
- **Dinero**: enteros en pesos colombianos (COP).
- **Criterio de redondeo monetario**: `subtotal = redondear(cantidad_decimal × precio_unitario)`,
  una sola vez por línea, a pesos enteros, con `Decimal` y `ROUND_HALF_UP` (12,5 → 13).
  El total de la venta es la **suma de los subtotales ya redondeados**.
- El precio aplicado se guarda en `detalle_venta` y no cambia si el precio del producto se modifica después.

### Cómo se escriben los datos en los formularios

- **Cantidades**: hasta 3 decimales; la coma o el punto son separador decimal (`0,5`, `1.250` = 1,25). No se usan separadores de miles.
- **Precios**: enteros en COP: `2500` o `$2.500` (el punto solo se acepta como separador de miles).
- **Fechas de filtros**: `AAAA-MM-DD`.

## Integridad de datos

Además de validar en los controladores, la propia base de datos impone las reglas (`schema.sql`):
precios/existencias/stock mínimo no negativos, códigos y nombres de categoría únicos (sin distinguir mayúsculas),
cantidades de movimientos positivas, `stock_posterior` coherente con el tipo de movimiento, ajustes con observación,
una salida solo puede originarse en una venta y el detalle referenciado debe ser del mismo producto (clave foránea compuesta),
los movimientos no pueden modificarse ni borrarse (triggers) y una venta anulada no puede volver a confirmarse.
Confirmar y anular ventas se ejecutan en **una sola transacción**: si algo falla, no queda nada a medias.

## Decisiones tomadas ante ambigüedades

El documento de requisitos pedía explicar y proponer las ambigüedades. Estas son las decisiones adoptadas;
conviene confirmarlas con quien define las reglas del negocio:

1. **Cantidades fraccionarias en todos los productos.** No hay un campo que distinga productos enteros de fraccionarios, así que cualquier producto admite hasta 3 decimales.
2. **"Stock bajo" y "agotado" no se solapan.** Agotado: existencias = 0. Stock bajo: 0 < existencias ≤ mínimo. Las alertas muestran ambos grupos; los contadores del panel los cuentan por separado. Solo se consideran productos activos.
3. **Producto repetido en una venta**: se acumula la cantidad en una sola línea y se aplica el precio indicado en la última adición.
4. **Las existencias iniciales se registran como una entrada** (crear un producto lo deja en 0), para que todo cambio de stock tenga su movimiento.
5. **Una `SALIDA` solo puede venir de una venta.** Las reducciones manuales son `AJUSTE_NEGATIVO`.
6. **Se añadió "Reactivar" producto** (no estaba especificado) para poder deshacer una desactivación hecha por error. Si no se desea, basta quitar el botón.
7. **Entradas y ajustes sobre productos desactivados**: el servicio no lo impide, pero la pantalla de Inventario solo lista productos activos.

## Limitaciones conocidas

- Sin autenticación ni roles (no requerido).
- Pensado para un solo equipo y una sola ventana; no hay sincronización entre varios equipos.
- La búsqueda de texto no distingue mayúsculas solo para letras sin tilde (comportamiento de `LIKE` en SQLite): "fríjol" no encuentra "FRÍJOL".
- Los filtros de fecha se escriben a mano (`AAAA-MM-DD`); no hay selector de calendario para no añadir dependencias.
- No hay exportación a Excel/PDF ni impresión de tiquetes (no especificados).
- La interfaz se verificó con una prueba automática de recorrido sobre un servidor de pantalla virtual (Linux); no se probó visualmente en Windows ni macOS.
