import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN DE CREDENCIALES ---
SUPABASE_URL = "https://wfdhuzlohwcemfjeudrl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZGh1emxvaHdjZW1mamV1ZHJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyNDM0NDEsImV4cCI6MjA5NDgxOTQ0MX0.ecnOCJnMDxHpYHuZmAvR5Fy95utOsFZ1Xjg3Xzyj8UM"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME="documentos_operacion"

# Función para subir a Storage
def procesar_archivo(archivo, carpeta, identificador):
    if archivo is not None:
        try:
            ruta = f"{carpeta}/{identificador}_{archivo.name.replace(' ', '_')}"
            supabase.storage.from_(BUCKET_NAME).upload(path=ruta, file=archivo.getvalue(), file_options={"content-type": archivo.type})
            return supabase.storage.from_(BUCKET_NAME).get_public_url(ruta)
        except Exception as e:
            st.error(f"Error en {archivo.name}: {e}")
            return None
    return None

# --- INTERFAZ ---
st.set_page_config(layout="wide")
st.title("📊 Sistema Centralizado Grupo AyC")
tab1, tab2, tab3, tab4 = st.tabs(["🚗 Alta de Conductores", "🚛 Control de Unidades", "📋 Registro de Operación","🔍 Consulta Integral"])

# ==========================================
# PESTAÑA 1: ALTA DE CONDUCTOR
# ==========================================
with tab1:
    with st.form("form_conductor", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo *")
            rfc = st.text_input("RFC *")
            correo = st.text_input("Correo")
        with col2:
            celular = st.text_input("Celular")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            f_foto = st.file_uploader("Foto")
            f_acta = st.file_uploader("Acta")
            f_curp = st.file_uploader("CURP")
            f_nss = st.file_uploader("NSS")
        with c2:
            f_ine = st.file_uploader("INE")
            f_fis = st.file_uploader("Constancia Fiscal")
            f_lic = st.file_uploader("Licencia")
        with c3:
            f_dom = st.file_uploader("Domicilio")
            f_ban = st.file_uploader("Banco")
            f_tox = st.file_uploader("Toxicológico")
            f_est = st.file_uploader("Comprobante de Estudios")
            f_ref = st.file_uploader("Carta de Referencia") # <-- Nuevo campo
            
        enviar = st.form_submit_button("Guardar Conductor")
        if enviar:
            if not nombre or not rfc:
                st.error("Por favor completa los campos obligatorios (Nombre y RFC)")
            else:
                datos = {
                    "nombre_driver": nombre, 
                    "rfc": rfc.upper(), 
                    "correo": correo, 
                    "celular": celular,
                    "url_fotografia": procesar_archivo(f_foto, "conductores/fotos", rfc),
                    "url_acta_nacimiento": procesar_archivo(f_acta, "conductores/actas", rfc),
                    "url_curp": procesar_archivo(f_curp, "conductores/curps", rfc),
                    "url_seguro_social": procesar_archivo(f_nss, "conductores/nss", rfc),
                    "url_ine": procesar_archivo(f_ine, "conductores/ines", rfc),
                    "url_constancia_fiscal": procesar_archivo(f_fis, "conductores/fiscal", rfc),
                    "url_licencia": procesar_archivo(f_lic, "conductores/licencias", rfc),
                    "url_comprobante_domicilio": procesar_archivo(f_dom, "conductores/domicilios", rfc),
                    "url_caratula_bancaria": procesar_archivo(f_ban, "conductores/bancos", rfc),
                    "url_toxicologico": procesar_archivo(f_tox, "conductores/toxicologicos", rfc),
                    "url_comprobante_estudios": procesar_archivo(f_est, "conductores/estudios", rfc),
                    "url_carta_referencia": procesar_archivo(f_ref, "conductores/referencias", rfc) # <-- Nueva ruta
                }
                try:
                    supabase.table("alta_conductor").insert(datos).execute()
                    st.success("Conductor registrado exitosamente")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==========================================
# PESTAÑA 2: UNIDADES
# ==========================================
with tab2:
    with st.form("form_unidades", clear_on_submit=True):
        p = st.text_input("Placas")
        m = st.text_input("Marca")
        sm = st.text_input("Submarca")
        mod = st.number_input("Modelo", 1990, 2030, 2026)
        f_circ = st.file_uploader("Tarjeta Circulación")
        f_seg = st.file_uploader("Seguro")
        
        enviar_u = st.form_submit_button("Registrar Unidad")
        if enviar_u:
            datos_u = {
                "placas": p.upper(), "modelo": int(mod), "marca": m, "submarca": sm,
                "url_tarjeta_circulacion": procesar_archivo(f_circ, "unidades/tarjetas", p),
                "url_poliza_seguro": procesar_archivo(f_seg, "unidades/polizas", p)
            }
            supabase.table("unidades").insert(datos_u).execute()
            st.success("Unidad registrada")

# ==========================================
# PESTAÑA 3: REGISTRO DE OPERACIÓN
# ==========================================
with tab3:
    st.header("Captura Dinámica de Despacho Operativo")
    st.write("Módulo relacional. Permite enlazar los conductores y unidades activos en sistema.")
    
    # Consulta en tiempo real de registros para alimentar menús desplegables
    try:
        conductores_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver").execute().data
        unidades_db = supabase.table("unidades").select("id_unidad, placas").execute().data
    except Exception as e:
        conductores_db, unidades_db = [], []
        st.error(f"Error de sincronización de llaves foráneas: {e}")

    # Estructuración de diccionarios de mapeo analítico (Nombre visible -> ID oculto UUID)
    dict_conductores = {c["nombre_driver"]: c["id_conductor"] for c in conductores_db}
    dict_unidades = {u["placas"]: u["id_unidad"] for u in unidades_db}
    
    if not dict_conductores or not dict_unidades:
        st.warning("⚠️ Atención: Para realizar capturas operativas, primero debe registrar al menos un conductor y una unidad en las pestañas anteriores.")
    
    with st.form("form_operacion", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sel_conductor = st.selectbox("Seleccione el Conductor asignado *", options=list(dict_conductores.keys()))
            sel_unidad = st.selectbox("Seleccione las Placas del Vehículo *", options=list(dict_unidades.keys()))
            status_operacion = st.selectbox("Estatus del Servicio", options=["En ruta", "Cancelacion", "No show"])
        
        with col2:
            paquetes = st.number_input("Cantidad de Paquetes Cargados", min_value=0, step=1, value=0)
            paradas = st.number_input("Número de Paradas Planificadas (Ruta)", min_value=0, step=1, value=0)
            
        st.subheader("⏱️ Tiempos de Estancia en Hub")
        t1, t2 = st.columns(2)
        with t1:
            fecha_llegada = st.date_input("Fecha de Llegada al Hub")
            hora_llegada = st.time_input("Hora de Entrada (Hub)")
        with t2:
            fecha_salida = st.date_input("Fecha de Salida del Hub")
            hora_salida = st.time_input("Hora de Despacho (Hub)")
            
        enviar_operacion = st.form_submit_button("Cerrar y Despachar Operación")
        
        if enviar_operacion:
            if not sel_conductor or not sel_unidad:
                st.error("No se puede generar un registro de operación sin asociar un conductor y vehículo válidos.")
            else:
                # Combinamos fecha e ingresos de hora en formato ISO string compatible con TIMESTAMP WITH TIME ZONE
                iso_llegada = datetime.combine(fecha_llegada, hora_llegada).isoformat()
                iso_salida = datetime.combine(fecha_salida, hora_salida).isoformat()
                
                datos_operacion = {
                    "conductor_id": dict_conductores[sel_conductor],
                    "unidad_id": dict_unidades[sel_unidad],
                    "status_operacion": status_operacion,
                    "hora_llegada_hub": iso_llegada,
                    "hora_salida_hub": iso_salida,
                    "paquetes_cargados": int(paquetes),
                    "paradas": int(paradas)
                }
                
                supabase.table("registro_operacion").insert(datos_operacion).execute()
                st.success(f"¡Viaje despachado correctamente! Operador asignado: {sel_conductor} | Estatus: {status_operacion}")

# ==========================================
# NUEVA PESTAÑA 4: CONSULTA DE EXPEDIENTES
# ==========================================
# (Asegúrate de agregar "🔍 Consulta" a tu lista de st.tabs arriba)
with tab4:
    st.header("🔍 Consulta Integral de Expedientes")
    tipo_consulta = st.radio("¿Qué desea consultar?", ["Conductores", "Unidades"], horizontal=True)
    
    if tipo_consulta == "Conductores":
        try:
            res = supabase.table("alta_conductor").select("*").execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                sel = st.selectbox("Seleccione Conductor:", [""] + df['nombre_driver'].astype(str).tolist())
                if sel:
                    reg = df[df['nombre_driver'] == sel].iloc[0]
                    st.subheader(f"Expediente de: {sel}")
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.write(f"**RFC:** {reg.get('rfc', 'N/A')}")
                        st.write(f"**Correo:** {reg.get('correo', 'N/A')}")
                        st.write(f"**Celular:** {reg.get('celular', 'N/A')}")
                        if reg.get('url_fotografia'):
                            st.image(reg['url_fotografia'], width=200, caption="Foto de Perfil")
                    
                    with c2:
                        st.write("### Documentación Digital")
                        # Mapeo actualizado con Carta de Referencia
                        docs = {
                            "Acta de Nacimiento": "url_acta_nacimiento",
                            "CURP": "url_curp",
                            "Seguro Social (NSS)": "url_seguro_social",
                            "INE": "url_ine",
                            "Constancia Fiscal": "url_constancia_fiscal",
                            "Licencia de Conducir": "url_licencia",
                            "Comprobante Domicilio": "url_comprobante_domicilio",
                            "Carátula Bancaria": "url_caratula_bancaria",
                            "Examen Toxicológico": "url_toxicologico",
                            "Comprobante de Estudios": "url_comprobante_estudios",
                            "Carta de Referencia": "url_carta_referencia" # <-- Campo agregado
                        }
                        # Generación dinámica de botones
                        for nombre, key in docs.items():
                            url = reg.get(key)
                            if url:
                                st.link_button(f"📄 Ver {nombre}", url)
                            else:
                                st.caption(f"❌ {nombre}: No cargado")
        except Exception as e:
            st.error(f"Error cargando conductores: {e}")

    else: # Consulta Unidades
        try:
            res = supabase.table("unidades").select("*").execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                sel = st.selectbox("Seleccione Placas de la Unidad:", [""] + df['placas'].astype(str).tolist())
                if sel:
                    reg = df[df['placas'] == sel].iloc[0]
                    st.subheader(f"Unidad Placas: {sel}")
                    st.write(f"**Marca:** {reg.get('marca', 'N/A')} | **Submarca:** {reg.get('submarca', 'N/A')} | **Modelo:** {reg.get('modelo', 'N/A')}")
                    
                    st.write("### Documentación de Unidad")
                    if reg.get('url_tarjeta_circulacion'): 
                        st.link_button("📄 Ver Tarjeta de Circulación", reg['url_tarjeta_circulacion'])
                    else:
                        st.caption("Tarjeta de Circulación: No cargado")
                        
                    if reg.get('url_poliza_seguro'): 
                        st.link_button("📄 Ver Póliza de Seguro", reg['url_poliza_seguro'])
                    else:
                        st.caption("Póliza de Seguro: No cargado")
        except Exception as e:
            st.error(f"Error cargando unidades: {e}")
