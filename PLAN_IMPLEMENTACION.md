# Plan de Implementación - El Oráculo de Eternia

## Descripción del Objetivo
Migrar el proyecto actual "motu-tracker" hacia una arquitectura profesional **Clean Architecture**, rebautizándolo oficialmente como **"El Oráculo de Eternia"**. El objetivo es establecer cimientos escalables, resilientes y gratuitos (Python, Streamlit, SQLite), integrando la lógica existente de inventario (`MOTU_scrap.py`) y web (`original_app.py`) en una estructura modular.

## Puntos de Revisión (User Review Required)
> [!IMPORTANT]
> - Confirmación para proceder con la reestructuración física de carpetas (Módulo 1).
> - Verificación de que el entorno Python 3.13.0 es el correcto.
> - Decisión futura sobre credenciales Cloudinary (se necesitará configurar `.env`).

## Cambios Propuestos

### Reestructuración de Directorios (Módulo 1)
Transformaremos la estructura plana actual en una arquitectura basada en `src/`.

- [ ] Crear estructura de directorios base:
  - `src/core`
  - `src/domain`
  - `src/infrastructure`
  - `src/scrapers`
  - `src/collectors`
  - `src/web`

### Componente: Core (`src/core`)
- [ ] **Mover y Refactorizar**: `logger.py` -> `src/core/logger.py`
- [ ] **Mover y Refactorizar**: `circuit_breaker.py` -> `src/core/circuit_breaker.py`
- [ ] **Acción**: Asegurar que sean módulos importables correctamente.

### Componente: Domain (`src/domain`)
- [ ] **Mover**: `models.py` -> `src/domain/models.py`
- [ ] **Actualizar**: Refinar modelos Pydantic si es necesario para validación estricta.

### Componente: Scrapers (`src/scrapers`)
- [ ] **Mover**: Todo el contenido de `scrapers/` -> `src/scrapers/`
- [ ] **Refactorizar**: Corregir rutas de importación en cada scraper.

### Componente: Web (`src/web`)
- [ ] **Mover**: `original_app.py` -> `src/web/app.py`
- [ ] **Refactorizar**: Adaptar importaciones para usar la nueva estructura `src.*`.

### Componente: Collectors (`src/collectors`)
- [ ] **Mover**: `MOTU_scrap.py` -> `src/collectors/personal_collection.py`
- [ ] **Integrar**: Asegurar que sigue funcionando como script autónomo o módulo.

## Plan de Verificación

### Pruebas Automatizadas
- [ ] Ejecutar `pip list` para verificar dependencias.
- [ ] Crear test simple de importación para verificar estructura `src`.

### Verificación Manual
- [ ] Validar visualmente el árbol de directorios.
- [ ] Ejecutar `streamlit run src/web/app.py` y verificar que carga la interfaz antigua correctamente.
- [ ] Ejecutar `python src/collectors/personal_collection.py` (modo dry-run si es posible) para verificar lógica de colección.
