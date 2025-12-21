import streamlit as st

st.title("Link Test")

url = "https://actiontoys.es/figura-de-accion/masters-of-the-universe-origins-hordak-masters-del-universo-origenes-hordak-figura-de-accion-mattel-gvw64-motu-origins/"

st.write(f"Testing URL: {url}")

st.link_button("Go to ActionToys (Hardcoded)", url)

st.markdown(f'<a href="{url}" target="_blank">HTML Anchor (Hardcoded)</a>', unsafe_allow_html=True)
