# Documento de Definición Técnica: Plataforma de Business Planning (Plan Breeding Arándanos)

**Descripción General:** Plataforma analítica e interactiva para la simulación de escenarios de negocios agrícolas (plantación, recambio y terceros) basados en parámetros de rendimiento varietal, acuerdos de royalties y planes de expansión. 

---

## 1. Flujo de Datos

La arquitectura de datos sigue un modelo reactivo donde las entradas del usuario actualizan en cascada los cálculos derivados.

* **Fuentes de Datos (Inputs):**
    * **Tablas Predeterminadas / Globales:** * `[Tabla Base]`: Escenario financiero macro por temporadas (T2627 a T3132).
        * `[Reglas / Definiciones]`: Variables macroeconómicas y de contrato (Royaltie FOB, Costo Plantines, Financiamiento, Interés).
    * **Tablas Personalizadas (Por Usuario):**
        * `[Tabla Datos Usuario Variedad]`: Parámetros agronómicos y comerciales ingresados estrictamente por cada variedad (Productividad, Densidad, Precio, % Recaudación).
        * `[Tabla Nuevos Proyectos]`: Ingreso de hectáreas (ha) planificadas por temporada para diferentes iniciativas (Crecimiento, Recambio, Terceros).
* **Procesamiento Intermedio (Tablas Ocultas / Backend):**
    * `[Tabla Cálculos Variedades]`: Derivación matricial de Productividad y Ganancias por tipo de productor (Interno, Terceros HF, Terceros Externo).
    * `[Tablas Subyacentes Proyectos]`: Matrices temporales que calculan el desfase (lag) fenológico donde las hectáreas plantadas en el año $T$ comienzan su año 1 de producción en $T+1$.
* **Salidas (Outputs):**
    * `[Dashboard Totales]`: Sumatorias dinámicas separadas por matriz (Hortifrut vs. Terceros) que muestran Toneladas Totales y Ganancias Totales proyectadas.

---

## 2. Interfaz (UI/UX)

La plataforma se compondrá de **1 Pantalla Maestra** interactiva (Single Page Application dashboard) dividida en las siguientes secciones:

1.  **Cabecera:** Título del proyecto y controles de guardado global.
2.  **Sección 1: Escenario Financiero (Tabla Base):** Tabla estática/obligatoria de proyecciones por temporada. No permite avanzar sin su confirmación.
3.  **Sección 2: Panel de Variedades (Panel Derecho/Superior):**
    * Vista principal: Tabla de la variedad en edición actual.
    * Controles: Botón `[Agregar Variedad]`, Filtro/Selector de variedades guardadas.
    * Validación estricta: Botón `[Hecho]` solo se activa si no hay campos vacíos (NaN/Null). Al guardar, la tabla se pliega.
4.  **Sección 3: Parámetros Globales (Reglas / Definiciones):** Tabla pequeña y editable para variables macro (Ej. Royaltie al 12%, Financiamiento 5 años).
5.  **Sección 4: Nuevos Proyectos (Core Dashboard):**
    * Selector para filtrar cálculos por Variedad.
    * Grilla de edición interactiva: Celdas resaltadas (ej. color ciruela) para el ingreso manual de hectáreas (ha) en proyectos (CHAO, OLMOS, Talsa, etc.).
    * *Debounce de Cálculo:* Retraso intencional de 1 a 2 segundos tras la edición de una celda antes de disparar el re-cálculo masivo para evitar sobrecarga del frontend.
6.  **Sección 5: Totales:** Tabla inferior de solo lectura, calculada en tiempo real mostrando los KPI finales consolidados.

---

## 3. Criterios Necesarios del Negocio (Lógica Matemática)

*Nota: Las fórmulas han sido corregidas dimensionalmente basadas en análisis de consistencia de los datos aportados.*

### 3.1. [Tabla Cálculos Variedades] (Cálculo por Año y Variedad)
* **Hortifrut Producción Interna:**
    * `Productividad (Kg/ha)` = $Productividad \times Densidad$
    * `Ganancia FOB (FOB/ha)` = $Precio\_estimado \times Productividad\_Interna\_(Kg/ha)$
* **Hortifrut Producción Terceros:**
    * `Productividad (Kg/ha)` = $Productividad\_Interna\_(Kg/ha) \times \%Recaudación$
    * `Ganancia Royaltie FOB - Venta Propia` = $Productividad\_Terceros\_(Kg/ha) \times Precio\_estimado \times Royaltie\_FOB$
    * `Ganancia Royaltie FOB - Venta Productor` = $Productividad\_Externa\_(Kg/ha) \times Precio\_estimado \times Royaltie\_FOB$
* **Terceros (Externa):**
    * `Productividad (Kg/ha)` = $Productividad\_Interna\_(Kg/ha) \times (1 - \%Recaudación)$
    * `Ganancia FOB - Venta HF` = $Precio\_estimado \times Productividad\_Terceros\_(Kg/ha) \times (1 - Royaltie\_FOB)$
    * `Ganancia FOB - Venta Propia` = $Precio\_estimado \times Productividad\_Externa\_(Kg/ha) \times (1 - Royaltie\_FOB)$

### 3.2. Lógica de Desfase Fenológico (Nuevos Proyectos)
Toda hectárea ingresada en la temporada $t$ genera producción y ganancias a partir de la temporada $t+1$ (Año 1 biológico de la planta).
* **Crecimiento HF y Recambio Varietal:**
    * $Producción_{t+1}$ = $( \sum ha_t ) \times Productividad\_Interna\_Año1 \div 1000$
    * $Ganancia_{t+1}$ = $( \sum ha_t ) \times Ganancia\_FOB\_Interna\_Año1 \div 1000$
* **Nuevos Prod Terceros:**
    * $Producción_{t+1}$ = $( \sum ha_t ) \times Productividad\_Terceros\_Año1 \div 1000$
    * $Ganancia_{t+1}$ = $( \sum ha_t ) \times Ganancia\_FOB\_Terceros\_Año1 \div 1000$
* **Ganancia Plantines:**
    * $Ganancia\_Plantines_{t}$ = $[( \sum ha_t ) \times Densidad\_Año_t \times Costo\_Plantines] \div Financiamiento \div 1000$
    * *Condición futura:* Si $t > Financiamiento$, este valor pasa a 0. A futuro se integrará cálculo con interés compuesto (`Interés de financiamiento`).

---

## 4. Estructura de Carpetas (Monorepo)

```text
/hf-breeding-planner
├── /frontend               # Astro (Estructura y enrutamiento estático/isomórfico)
│   ├── /src
│   │   ├── /components     # Componentes UI (Layouts, modales, headers)
│   │   ├── /pages          # Rutas (Index, Dashboard)
│   │   └── /styles         # Tailwind o CSS global
├── /backend                # Starlette + Shiny for Python (Lógica reactiva y API)
│   ├── /api                # Starlette endpoints (Guardado de DB, validaciones)
│   ├── /shiny_app          # Aplicación Shiny (UI interactiva embebida, reactividad)
│   │   ├── app.py          # Entrypoint de Shiny
│   │   ├── modules/        # Módulos Shiny (Tablas editables, gráficos)
│   │   └── logic.py        # Funciones matemáticas puras (Pandas/Numpy)
│   ├── /models             # Modelos ORM (SQLAlchemy)
│   └── /db                 # Migraciones y conexión a BD
├── docker-compose.yml
└── README.md

```

---

## 5. Plan de Implementación

1. **Fase 1: Modelado de Base de Datos y Backend Core.** Definir esquemas relacionales en BD (PostgreSQL/SQLite) asegurando la integridad referencial (Una Variedad -> Muchos Años de Proyección). Construir endpoints en Starlette.
2. **Fase 2: Motor de Cálculo (Lógica de Negocio).** Implementar las lógicas de desfase temporal (lag) y derivación de KPIs en Python estricto (Pandas) antes de atarlo a la interfaz.
3. **Fase 3: Desarrollo de UI Reactiva (Shiny-Python).** Construir los DataFrames interactivos (DataGrids). Implementar la directiva de *debounce* (1.5s) en los inputs para recalcular matrices de "Nuevos Proyectos".
4. **Fase 4: Integración Frontend (Astro).** Empaquetar la aplicación Shiny dentro del shell de Astro (usando Web Components o Iframe seguro) para gestionar la autenticación, layout general y SEO interno si aplicase.
5. **Fase 5: Validaciones Estrictas.** Forzar bloqueos en UI (Ej: `disabled=True` en botones si faltan campos de variedad).
6. **Fase 6: Testing.** Pruebas unitarias de los cálculos financieros comparados contra las planillas maestras (Imágenes 6-10).

---

## 6. Technology Stack

* **Frontend Shell:** [Astro](https://astro.build/) (Rendimiento extremo, control de layout estático).
* **Backend & API Routing:** [Starlette](https://www.starlette.io/) (Asíncrono, ultraligero).
* **Dashboard Reactivo:** [Shiny for Python](https://shiny.posit.co/py/) (Manejo natural de estados reactivos en Python para ciencia de datos).
* **Data Processing:** `Pandas` y `NumPy` para cálculo matricial rápido de las temporalidades agronómicas.
* **Database:** PostgreSQL (recomendado para producción) con `SQLAlchemy` como ORM.
* **Styling:** Tailwind CSS (integrado nativamente con Astro y adaptable a componentes HTML de Shiny).

---

## 7. Consideraciones Finales

* **Patrón de Programación Reactiva (Rx):** Dada la naturaleza encadenada de los cálculos, Shiny manejará un grafo de dependencias reactivas. Es vital implementar `ui.input_action_button` o `reactive.event` con un `debounce` explícito para evitar bloqueos del hilo principal durante la digitación de hectáreas. *(Ref: Bainomugisha et al., "A Survey on Reactive Programming", ACM Computing Surveys).*
* **Cálculo de Amortización (Plantines):** Actualmente la división es lineal (`/ Financiamiento`). Para la implementación pendiente con la regla de `Interés de financiamiento`, se deberá programar la fórmula estándar de cuota fija de amortización de préstamos (Anualidad).
* **Manejo de Lags Temporales:** A nivel algorítmico, las matrices de producción deberán usar funciones de *shift* (desplazamiento) sobre los DataFrames de hectáreas para asegurar que la siembra del Año 0 no genere ingresos hasta el Año 1, previniendo errores de caja (cash flow) temprano.