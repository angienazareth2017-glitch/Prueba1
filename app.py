import streamlit as st
import pandas as pd
from rapidfuzz import fuzz

st.set_page_config(page_title="Agente de Conciliación Bancaria", layout="wide")

st.title("🏦 Agente de Conciliación Bancaria Inteligente")
st.write("Sube tus archivos de extracto bancario y libro mayor para emparejar transacciones automáticamente.")

# --- BARRA LATERAL: Configuración de Reglas ---
st.sidebar.header("⚙️ Configuración del Motor")
tolerancia_dias = st.sidebar.slider("Tolerancia de fechas (días)", 0, 7, 3)
umbral_similitud = st.sidebar.slider("Umbral de similitud de texto (%)", 50, 100, 80)
tolerancia_monto = st.sidebar.number_input("Tolerancia en monto ($ / local)", min_value=0.0, value=0.0, step=0.01)

# --- CARGA DE ARCHIVOS ---
col_up1, col_up2 = st.columns(2)

with col_up1:
    archivo_banco = st.file_uploader("Cargar Extracto Bancario (CSV o Excel)", type=["csv", "xlsx"])

with col_up2:
    archivo_libro = st.file_uploader("Cargar Libro Mayor Interno (CSV o Excel)", type=["csv", "xlsx"])

def cargar_datos(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# --- LÓGICA DEL MOTOR DE EMPAREJAMIENTO ---
def procesar_conciliacion(df_banco, df_libro):
    # Estandarizar nombres de columnas a minúsculas
    df_banco.columns = [c.lower().strip() for c in df_banco.columns]
    df_libro.columns = [c.lower().strip() for c in df_libro.columns]
    
    # Asegurar formato de fechas y montos
    df_banco['fecha'] = pd.to_datetime(df_banco['fecha'])
    df_libro['fecha'] = pd.to_datetime(df_libro['fecha'])
    df_banco['monto'] = df_banco['monto'].astype(float)
    df_libro['monto'] = df_libro['monto'].astype(float)
    
    df_libro['conciliado'] = False
    coincidencias = []
    
    for idx_b, row_b in df_banco.iterrows():
        match_encontrado = False
        
        # Filtrar candidatos por monto dentro de la tolerancia
        candidatos = df_libro[
            (abs(df_libro['monto'] - row_b['monto']) <= tolerancia_monto) & 
            (~df_libro['conciliado'])
        ]
        
        for idx_l, row_l in candidatos.iterrows():
            diferencia_dias = abs((row_b['fecha'] - row_l['fecha']).days)
            
            if diferencia_dias <= tolerancia_dias:
                text_b = str(row_b.get('descripcion', ''))
                text_l = str(row_l.get('descripcion', ''))
                score = fuzz.token_sort_ratio(text_b, text_l)
                
                # Criterio de Coincidencia Exacta o Fuzzy Match
                if score >= umbral_similitud:
                    coincidencias.append({
                        "ID Banco": row_b.get('id', idx_b),
                        "Fecha Banco": row_b['fecha'].strftime('%Y-%m-%d'),
                        "Descripción Banco": text_b,
                        "Monto": row_b['monto'],
                        "ID Libro": row_l.get('id', idx_l),
                        "Fecha Libro": row_l['fecha'].strftime('%Y-%m-%d'),
                        "Descripción Libro": text_l,
                        "Similitud Texto (%)": score,
                        "Desfase (Días)": diferencia_dias,
                        "Estado": "Conciliado Automático"
                    })
                    df_libro.loc[idx_l, 'conciliado'] = True
                    match_encontrado = True
                    break
        
        if not match_encontrado:
            coincidencias.append({
                "ID Banco": row_b.get('id', idx_b),
                "Fecha Banco": row_b['fecha'].strftime('%Y-%m-%d'),
                "Descripción Banco": str(row_b.get('descripcion', '')),
                "Monto": row_b['monto'],
                "ID Libro": None,
                "Fecha Libro": None,
                "Descripción Libro": None,
                "Similitud Texto (%)": 0,
                "Desfase (Días)": None,
                "Estado": "Pendiente de Revisión"
            })
            
    return pd.DataFrame(coincidencias)

# --- EJECUCIÓN Y VISUALIZACIÓN ---
if archivo_banco and archivo_libro:
    df_b = cargar_datos(archivo_banco)
    df_l = cargar_datos(archivo_libro)
    
    st.success("Archivos cargados correctamente.")
    
    if st.button("🚀 Ejecutar Conciliación"):
        res_df = procesar_conciliacion(df_b, df_l)
        
        # Métricas rápidas
        total = len(res_df)
        conciliados = len(res_df[res_df["Estado"] == "Conciliado Automático"])
        pendientes = total - conciliados
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Transacciones Banco", total)
        m2.metric("Conciliadas Automáticamente", conciliados, delta=f"{(conciliados/total)*100:.1f}%")
        m3.metric("Pendientes / Excepciones", pendientes, delta_color="inverse")
        
        st.subheader("Resultados de la Conciliación")
        st.dataframe(res_df, use_container_width=True)
        
        # Descarga de Resultados
        csv_data = res_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte en CSV",
            data=csv_data,
            file_name="reporte_conciliacion.csv",
            mime="text/csv"
        )
else:
    st.info("Por favor, sube ambos archivos para iniciar el proceso. Asegúrate de que contengan las columnas mínimas: `id`, `fecha`, `monto` y `descripcion`.")