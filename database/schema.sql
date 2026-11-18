-- Esquema de MINIABASTOS (SQLite).
-- Todo el script se ejecuta en una sola transacción y es idempotente
-- (IF NOT EXISTS), por lo que puede ejecutarse en cada arranque.
--
-- Convenciones:
--   * Cantidades (stock_actual, stock_minimo, cantidad): INTEGER escalado x1000.
--   * Dinero (precio_venta, precio_unitario, subtotal, total): INTEGER en COP.
--   * Fechas: TEXT 'AAAA-MM-DD HH:MM:SS' (hora local).

BEGIN;

CREATE TABLE IF NOT EXISTS categorias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(nombre)) > 0),
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS productos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo        TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(codigo)) > 0),
    nombre        TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    descripcion   TEXT,
    unidad_medida TEXT NOT NULL CHECK (length(trim(unidad_medida)) > 0),
    categoria_id  INTEGER NOT NULL
                  REFERENCES categorias (id) ON UPDATE CASCADE ON DELETE RESTRICT,
    precio_venta  INTEGER NOT NULL DEFAULT 0 CHECK (precio_venta >= 0),
    stock_actual  INTEGER NOT NULL DEFAULT 0 CHECK (stock_actual >= 0),
    stock_minimo  INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    activo        INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ventas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha         TEXT NOT NULL,
    total         INTEGER NOT NULL CHECK (total >= 0),
    estado        TEXT NOT NULL DEFAULT 'CONFIRMADA'
                  CHECK (estado IN ('CONFIRMADA', 'ANULADA')),
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS detalle_venta (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id        INTEGER NOT NULL
                    REFERENCES ventas (id) ON UPDATE CASCADE ON DELETE RESTRICT,
    producto_id     INTEGER NOT NULL
                    REFERENCES productos (id) ON UPDATE CASCADE ON DELETE RESTRICT,
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario INTEGER NOT NULL CHECK (precio_unitario >= 0),
    subtotal        INTEGER NOT NULL CHECK (subtotal >= 0),
    -- Un producto no se repite dentro de una misma venta.
    UNIQUE (venta_id, producto_id),
    -- Clave alterna necesaria para la clave foránea compuesta de movimientos.
    UNIQUE (id, producto_id)
);

CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id      INTEGER NOT NULL
                     REFERENCES productos (id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo             TEXT NOT NULL
                     CHECK (tipo IN ('ENTRADA', 'SALIDA', 'AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO')),
    cantidad         INTEGER NOT NULL CHECK (cantidad > 0),   -- siempre magnitud positiva
    stock_anterior   INTEGER NOT NULL CHECK (stock_anterior >= 0),
    stock_posterior  INTEGER NOT NULL CHECK (stock_posterior >= 0),
    detalle_venta_id INTEGER,                                  -- único origen posible: una línea de venta
    fecha            TEXT NOT NULL,
    observacion      TEXT,

    -- La dirección del movimiento determina cómo cambia el stock.
    CHECK (
        (tipo IN ('ENTRADA', 'AJUSTE_POSITIVO') AND stock_posterior = stock_anterior + cantidad)
        OR
        (tipo IN ('SALIDA', 'AJUSTE_NEGATIVO') AND stock_posterior = stock_anterior - cantidad)
    ),
    -- Los ajustes exigen observación.
    CHECK (
        tipo NOT IN ('AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO')
        OR (observacion IS NOT NULL AND length(trim(observacion)) > 0)
    ),
    -- Una venta solo origina SALIDA (venta) o ENTRADA (reversión por anulación);
    -- y toda SALIDA debe provenir de una venta.
    CHECK (detalle_venta_id IS NULL OR tipo IN ('ENTRADA', 'SALIDA')),
    CHECK (tipo <> 'SALIDA' OR detalle_venta_id IS NOT NULL),

    -- Clave foránea compuesta: el detalle referenciado debe corresponder al
    -- mismo producto del movimiento (si detalle_venta_id es NULL no se evalúa).
    FOREIGN KEY (detalle_venta_id, producto_id)
        REFERENCES detalle_venta (id, producto_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Índices -------------------------------------------------------------------
-- El código ya está indexado por su restricción UNIQUE (autoíndice de SQLite).
CREATE INDEX IF NOT EXISTS idx_productos_nombre
    ON productos (nombre COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_productos_categoria
    ON productos (categoria_id);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha
    ON ventas (fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_estado
    ON ventas (estado);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto_fecha
    ON movimientos_inventario (producto_id, fecha);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha
    ON movimientos_inventario (fecha);
CREATE INDEX IF NOT EXISTS idx_movimientos_detalle
    ON movimientos_inventario (detalle_venta_id);

-- Inmutabilidad ---------------------------------------------------------------
-- Los movimientos confirmados no se modifican ni se borran: las correcciones
-- se hacen con nuevos movimientos.
CREATE TRIGGER IF NOT EXISTS trg_movimientos_no_update
BEFORE UPDATE ON movimientos_inventario
BEGIN
    SELECT RAISE(ABORT, 'Los movimientos de inventario no se pueden modificar.');
END;

CREATE TRIGGER IF NOT EXISTS trg_movimientos_no_delete
BEFORE DELETE ON movimientos_inventario
BEGIN
    SELECT RAISE(ABORT, 'Los movimientos de inventario no se pueden eliminar.');
END;

-- Una venta anulada no puede volver a ser confirmada (ni anularse dos veces
-- afectando el inventario).
CREATE TRIGGER IF NOT EXISTS trg_ventas_no_reactivar
BEFORE UPDATE OF estado ON ventas
WHEN OLD.estado = 'ANULADA' AND NEW.estado <> 'ANULADA'
BEGIN
    SELECT RAISE(ABORT, 'Una venta anulada no puede volver a confirmarse.');
END;

PRAGMA user_version = 1;

COMMIT;
