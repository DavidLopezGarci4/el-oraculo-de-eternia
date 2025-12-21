# 📖 Manual de Operaciones: El Oráculo de Eternia

## 🔔 Configuración de Alertas (Telegram)

Para que el Oráculo te notifique de ofertas (>20% descuento) en tiempo real:

1.  **Crear el Bot**:
    *   Abre Telegram y busca a **@BotFather**.
    *   Envía el comando `/newbot`.
    *   Sigue las instrucciones (nombre y username del bot).
    *   Copia el **HTTP API Token** que te dará (ej: `123456789:ABCdefGHI...`).

2.  **Obtener tu Chat ID**:
    *   Busca en Telegram a **@userinfobot** (o cualquier bot de ID).
    *   Envía `/start` o cualquier mensaje.
    *   Copia el número que aparece como "Id" (ej: `12345678`).

3.  **Configurar en la App**:
    *   Abre *El Oráculo* (`streamlit run src/web/app.py`).
    *   Ve al menú **Configuración** -> Pestaña **🔔 Alertas**.
    *   Introduce el Token y el Chat ID.
    *   Pulsa **Guardar**.

4.  **Reiniciar**:
    *   Detén la aplicación en la terminal (`Ctrl+C`).
    *   Vuelve a lanzarla.

---

## ✅ Tareas de Validación Pendientes

- [ ] **Prueba de Fuego Telegram**: Forzar una bajada de precio manual en la DB y verificar que llega el mensaje.
- [ ] **Validación Móvil**: Verificar que la interfaz "Cazador" se ve bien en pantallas pequeñas (PWA).
- [ ] **Escaneo Completo**: Ejecutar "LANZAR ESCANEO DIARIO" y dejarlo terminar sin errores para confirmar estabilidad.
