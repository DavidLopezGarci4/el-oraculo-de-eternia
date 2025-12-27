# 🌌 El Oráculo de Eternia

**Plataforma de Inteligencia y Vigilancia de Tesoros de Eternia (Grado Industrial)**

El Oráculo es un sistema avanzado de monitorización, análisis y gestión de coleccionables de "Masters of the Universe". Diseñado bajo principios de Clean Architecture y reforzado mediante una Auditoría de Grado Industrial por el Consejo de Sabios, el Oráculo garantiza la captura, validación y alerta proactiva de ofertas en el mercado más competitivo.

---

## 🏛️ Arquitectura del Sistema (Los Pilares)

El Oráculo se divide en cinco componentes fundamentales, cada uno blindado para la resiliencia y la precisión:

1.  **Motor de Exploración (Scrapers)**: Flota de robots especializados (ActionToys, Pixelatoy, Fantasia, Electropolis, Frikiverso) que patrullan las tiendas. Blindados contra bloqueos anti-bot y pop-ups.
2.  **Pipeline de Inteligencia (SmartMatcher)**: Motor de enlace algorítmico que utiliza huellas digitales (EAN-13) y análisis semántico Jaccard para vincular ofertas al catálogo maestro.
3.  **El Purgatorio (Consola de Administración)**: Interfaz de gestión para ítems no identificados, con herramientas de vinculación manual, descarte y la **Gema del Tiempo (Undo)**.
4.  **El Centinela (Sistema de Alertas)**: Vigilancia 24/7 que notifica vía Telegram bajadas de precio críticas y mínimos históricos, protegido por un **Cortafuegos de Alertas (Rate-Limit)**.
5.  **La Cámara de Grayskull (Búnker)**: Sistema de recuperación total de datos mediante Snapshots diarios y Bóvedas de base de datos cifradas.

---

## 🛡️ Auditoría del Consejo de Sabios (Mejoras SRE/QA)

El sistema ha sido auditado y optimizado en cuatro frentes críticos:

*   **Audit SRE (Resiliencia)**: Detección proactiva de bloqueos (403/429) con alertas de Telegram. Implementación de Rate-Limiting para evitar spam y asegurar la continuidad del servicio.
*   **Audit QA (Precisión)**: Validación estricta de EAN-13, ponderación negativa para variantes de productos y un sistema de **Deshacer (Undo) Atómico** que garantiza la limpieza total de datos vinculados por error.
*   **Audit Performance (Velocidad)**: Inserción de datos por ráfagas (Batch Processing) que reduce la latencia con Supabase en un 80%. Uso de `st.fragment` y caché de sugerencias $O(n^2)$ para una UI instantánea.
*   **Inclusividad del Dato**: Filosofía de "Frontera Abierta": el EAN es un ayudante, no un portero. El sistema acepta EANs nulos y recurre a la inteligencia semántica para no perder ninguna oferta.

---

## 🎮 Guía de Operación

### 1. El Ritual de Scraping
El Oráculo patrulla Eternia mediante tres métodos:
-   **Escaneo Diario**: Ejecutado automáticamente por GitHub Actions.
-   **Deep Harvest**: Escaneo profundo que visita la ficha técnica de cada producto para extraer el EAN/Fingerprint.
-   **Escaneo Manual**: Lanzado desde la interfaz de administración para una actualización inmediata de tiendas específicas.

### 2. Gestión en el Purgatorio
Cuando el Oráculo no tiene la certeza absoluta (confianza < 70%), envía el alma del ítem al Purgatorio:
-   **Vincular**: Elige el producto del catálogo y confirma el vínculo.
-   **Descartar**: Si es un ítem irrelevante, exílialo a la lista negra.
-   **⏪ Deshacer**: Si te equivocas, usa la Gema del Tiempo para devolver el ítem al Purgatorio y limpiar el catálogo.

### 3. El Búnker de Eternia
En la sección **La Cámara de Grayskull**, puedes:
-   Crear Bóvedas (backups) manuales en JSON.
-   Restaurar el sistema a un punto de control anterior con doble confirmación de seguridad.
-   Consultar el historial de recuperación y la integridad de los snapshots.

---

## 🛠️ Stack Tecnológico
-   **Core**: Python 3.10+ con Clean Architecture.
-   **Base de Datos**: PostgreSQL / Supabase con SQLAlchemy.
-   **Exploración**: Playwright (Headless/Stealth) + BeautifulSoup4.
-   **Interfaz**: Streamlit (Reflejada con `st.fragment`).
-   **Vigilancia**: Telegram Bot API con Rate-Limiting.
-   **Infraestructura**: GitHub Actions (CI/CD & Automation).

---

## 🚀 Instalación y Despliegue

1.  **Clonar el repositorio** y crear un entorno virtual.
2.  **Instalar dependencias**: `pip install -r requirements.txt`.
3.  **Configurar `.env`** con las credenciales de Supabase y Telegram:
    ```env
    DATABASE_URL=postgresql://user:pass@host:port/db
    TELEGRAM_BOT_TOKEN=your_token
    TELEGRAM_CHAT_ID=your_id
    ```
4.  **Inicializar la DB**: `python -m src.init_db`.
5.  **Ejecutar el Oráculo**: `streamlit run app.py`.

---

## 🧪 Validación: El Ritual de Humo
Para validar las protecciones industriales, el sistema cuenta con un script de Smoke Test dedicado:
```bash
$env:PYTHONPATH="."; python src/jobs/smoke_test.py
```
Este ritual confirma que el Rate-Limit y el Undo Atómico operan a pleno rendimiento.

---
*Que la sabiduría de Grayskull guíe tus capturas.* 🏰✨
