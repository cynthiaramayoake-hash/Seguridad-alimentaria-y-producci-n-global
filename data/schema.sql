-- Esquema PostgreSQL (Supabase) - Dashboard seguridad alimentaria
CREATE TABLE paises (
  iso3        CHAR(3) PRIMARY KEY,
  pais        TEXT NOT NULL,
  continente  TEXT NOT NULL,
  subregion   TEXT
);

CREATE TABLE produccion (
  iso3              CHAR(3) REFERENCES paises(iso3),
  grupo             TEXT    NOT NULL,      -- Cereales, Frutas, Verduras, Raíces y tubérculos, Carne, Leche, Huevos
  anio              SMALLINT NOT NULL,
  toneladas         NUMERIC NOT NULL CHECK (toneladas >= 0),
  simbolo           CHAR(1),               -- A oficial, E estimado, X fuente externa
  variacion_atipica BOOLEAN DEFAULT FALSE, -- cambio > 50% vs año anterior
  PRIMARY KEY (iso3, grupo, anio)
);

CREATE TABLE balance_alimentario (
  iso3      CHAR(3) REFERENCES paises(iso3),
  grupo     TEXT     NOT NULL,             -- incluye Total general, Productos vegetales/animales, Población
  elemento  TEXT     NOT NULL,             -- Producción, Importación, Exportación, Alimento, Piensos, kcal/cápita/día...
  anio      SMALLINT NOT NULL,
  valor     NUMERIC  NOT NULL,             -- puede ser negativo en Variación de existencias y Residuales
  unidad    TEXT     NOT NULL,             -- t, kcal/cap/d, kg/cap, personas
  simbolo   CHAR(1),                       -- E estimado, I imputado, X fuente externa
  PRIMARY KEY (iso3, grupo, elemento, anio)
);

CREATE INDEX idx_prod_anio ON produccion (anio, grupo);
CREATE INDEX idx_bal_elem  ON balance_alimentario (elemento, anio);

-- Vista para el KPI de producción por continente
CREATE VIEW v_produccion_continente AS
SELECT pa.continente, p.grupo, p.anio, SUM(p.toneladas) AS toneladas
FROM produccion p JOIN paises pa USING (iso3)
GROUP BY pa.continente, p.grupo, p.anio;
