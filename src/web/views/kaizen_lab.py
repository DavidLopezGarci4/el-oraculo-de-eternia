import streamlit as st
from sqlalchemy.orm import Session
from src.domain.models import KaizenInsightModel
from datetime import datetime

def render(db: Session):
    st.title("🧪 Kaizen Lab: Memoria de Aprendizaje")
    st.markdown("""
    Bienvenidos al laboratorio de evolución del Oráculo. Aquí se registran los **hallazgos cualitativos** 
    detectados durante las audiciones de las webs. Estos logs son el motor para aplicar mejoras 
    mediante *prueba y error* de forma inteligente.
    """)

    # Filter/Stats
    insights = db.query(KaizenInsightModel).order_by(KaizenInsightModel.created_at.desc()).all()
    
    if not insights:
        st.info("Aún no hay hallazgos registrados. El agente aprenderá de la próxima audición.")
        return

    # Categories
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Hallazgos", len(insights))
    with col2:
        criticals = len([i for i in insights if i.severity == "critical"])
        st.metric("Críticos", criticals, delta_color="inverse")
    with col3:
        implemented = len([i for i in insights if i.status == "implemented"])
        st.metric("Mejoras Aplicadas", implemented)

    st.divider()

    # Insight Feed
    for insight in insights:
        with st.expander(f"[{insight.created_at.strftime('%H:%M')}] {insight.spider_name} - {insight.insight_type.upper()}", expanded=(insight.severity == "critical")):
            # Severity Badge
            badge_color = "red" if insight.severity == "critical" else "orange" if insight.severity == "warning" else "blue"
            st.markdown(f":{badge_color}[**Nivel: {insight.severity.upper()}**] | Status: `{insight.status.upper()}`")
            
            st.write(f"**Hallazgo:** {insight.content}")
            
            if insight.pattern_observed:
                st.info(f"**Patrón Detectado:** `{insight.pattern_observed}`")
            
            if insight.proposed_solution:
                st.success(f"**Propuesta del Agente:** {insight.proposed_solution}")
                
                if insight.status == "pending":
                    if st.button(f"Aprobar implementación para {insight.spider_name}", key=f"btn_{insight.id}"):
                        # Logic to mark as implemented (actual code change would follow in a new cycle)
                        insight.status = "implemented"
                        db.commit()
                        st.rerun()

    st.sidebar.markdown("""
    ### 🧠 Guía de Mejora
    1. **Audición:** El robot escanea.
    2. **Insight:** El robot detecta un patrón (ej: popup nuevo).
    3. **Propuesta:** El robot sugiere un bypass.
    4. **Decisión:** Tú apruebas el cambio.
    """)
