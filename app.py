import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="BiciDatos", page_icon="🚲", layout="wide")

URL_UCI = "https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset"
REFERENCIA = ("Fanaee-T, H. (2013). Bike Sharing [Conjunto de datos]. "
              "UCI Machine Learning Repository. "
              "https://doi.org/10.24432/C5W894. Licencia CC BY 4.0.")

COLUMNA_USUARIO = {
    "Todos": "alquileres_total",
    "Ocasionales": "alquileres_ocasionales",
    "Registrados": "alquileres_registrados",
}


# ---------------------------------------------------------------- utilidades
def formato_entero(n):
    """3292679 -> '3.292.679'"""
    return f"{n:,.0f}".replace(",", ".")


def formato_decimal(x, decimales=1):
    """189.46 -> '189,5'"""
    texto = f"{x:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def hay_datos():
    return "datos" in st.session_state


def filtrar_datos():
    """Aplica los tres filtros de la barra lateral y añade la columna
    auxiliar 'alquileres' (según el tipo de usuario elegido)."""
    df = st.session_state["datos"]
    usuario = st.session_state["filtro_usuario"]
    tipo_dia = st.session_state["filtro_tipo_dia"]
    hora_min, hora_max = st.session_state["filtro_horas"]

    filtrado = df[(df["hora"] >= hora_min) & (df["hora"] <= hora_max)]
    if tipo_dia != "Todos":
        filtrado = filtrado[filtrado["tipo_dia"] == tipo_dia]

    filtrado = filtrado.copy()
    filtrado["alquileres"] = filtrado[COLUMNA_USUARIO[usuario]]
    return filtrado


# ------------------------------------------------- Página 1: Explorar (R1,R4,R5)
def pagina_explorar():
    st.title("Explorar los datos")

    # R1: carga del archivo
    archivo = st.file_uploader("Selecciona bicicletas_listas.csv", type="csv")

    if st.button("Cargar datos", type="primary"):
        if archivo is None:
            st.warning("Primero selecciona el archivo CSV.")
        else:
            st.session_state["datos"] = pd.read_csv(
                archivo, encoding="utf-8-sig", parse_dates=["fecha"]
            )

    if not hay_datos():
        st.info("Para comenzar, selecciona `bicicletas_listas.csv` y pulsa "
                "**Cargar datos**.")
        st.stop()  # no se calcula nada hasta cargar el archivo

    st.success(f"{formato_entero(len(st.session_state['datos']))} "
               "registros cargados.")

    datos = filtrar_datos()
    if datos.empty:
        st.warning("No hay registros que cumplan los filtros seleccionados.")
        st.stop()

    # R4: indicadores
    col1, col2 = st.columns(2)
    col1.metric("Total de alquileres", formato_entero(datos["alquileres"].sum()))
    col2.metric("Promedio por hora observada",
                formato_decimal(datos["alquileres"].mean()))

    tab_grafico, tab_datos = st.tabs(["Gráfico diario", "Datos"])

    with tab_grafico:
        diario = datos.groupby("fecha", as_index=False)["alquileres"].sum()
        grafico = (
            alt.Chart(diario)
            .mark_line(color="#197A8D")
            .encode(
                x=alt.X("fecha:T", title="Fecha"),
                y=alt.Y("alquileres:Q", title="Alquileres por día"),
                tooltip=[alt.Tooltip("fecha:T", title="Fecha"),
                         alt.Tooltip("alquileres:Q", title="Alquileres")],
            )
        )
        st.altair_chart(grafico)
        st.caption("Cada total incluye las horas que conservan los filtros.")

    # R5: tabla, descarga y fuente
    with tab_datos:
        st.dataframe(datos, hide_index=True)
        st.download_button(
            "Descargar datos filtrados",
            data=datos.to_csv(index=False).encode("utf-8-sig"),
            file_name="bicicletas_filtradas.csv",
            mime="text/csv",
        )
        st.caption(REFERENCIA)
        st.link_button("Consultar la fuente en UCI", URL_UCI)


# ------------------------------------------------- Página 2: Comparar (R6, R7)
def pagina_comparar():
    st.title("Comparar horarios")

    if not hay_datos():
        st.info("Para comenzar, ve a **Explorar los datos**, selecciona "
                "`bicicletas_listas.csv` y pulsa **Cargar datos**.")
        st.stop()

    datos = filtrar_datos()
    if datos.empty:
        st.warning("No hay registros que cumplan los filtros seleccionados.")
        st.stop()

    # R6: promedio por hora
    promedios = (datos.groupby("hora", as_index=False)["alquileres"].mean()
                 .rename(columns={"alquileres": "promedio"}))

    color = st.color_picker("Color de las barras", "#197A8D")

    grafico = (
        alt.Chart(promedios)
        .mark_bar(color=color)
        .encode(
            x=alt.X("hora:O", title="Hora del día", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("promedio:Q", title="Alquileres por hora observada"),
            tooltip=[alt.Tooltip("hora:O", title="Hora"),
                     alt.Tooltip("promedio:Q", title="Promedio", format=".1f")],
        )
    )
    st.altair_chart(grafico)

    if st.checkbox("Mostrar tabla de promedios"):
        st.dataframe(promedios.round(1), hide_index=True)

    # R7: límite de alquileres
    limite = st.number_input("Límite de alquileres por hora", min_value=0,
                             value=250, step=10)

    superan = promedios[promedios["promedio"] > limite]  # estrictamente mayor
    st.metric("Horarios con promedio mayor que el límite",
              f"{len(superan)}/{len(promedios)}")

    if superan.empty:
        st.write("Ningún horario supera el límite.")
    else:
        horas = ", ".join(f"{h:02d}:00" for h in superan["hora"])
        st.write(f"Horarios: {horas}.")


# -------------------------------------------- Navegación y filtros (R2, R3)
navegacion = st.navigation([
    st.Page(pagina_explorar, title="Explorar los datos", icon="🔎",
            url_path="explorar", default=True),
    st.Page(pagina_comparar, title="Comparar horarios", icon="📊",
            url_path="comparar"),
])

# Filtros compartidos: se definen fuera de las páginas y con 'key'
# para que se conserven al navegar.
st.sidebar.title("BiciDatos")
st.sidebar.selectbox("Tipo de usuario", ["Todos", "Ocasionales", "Registrados"],
                     key="filtro_usuario")
st.sidebar.radio("Tipo de día", ["Todos", "Laborable", "No laborable"],
                 key="filtro_tipo_dia")
st.sidebar.slider("Horas del día", min_value=0, max_value=23, value=(0, 23),
                  key="filtro_horas")

navegacion.run()
