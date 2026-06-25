import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
import unicodedata # <--- Importante para limpiar acentos
import io
import zipfile
import requests

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN DE CREDENCIALES ---
SUPABASE_URL = "https://wfdhuzlohwcemfjeudrl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZGh1emxvaHdjZW1mamV1ZHJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyNDM0NDEsImV4cCI6MjA5NDgxOTQ0MX0.ecnOCJnMDxHpYHuZmAvR5Fy95utOsFZ1Xjg3Xzyj8UM"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "documentos_operacion"

# Función para limpiar caracteres especiales (acentos, ñ, espacios)
def limpiar_texto(texto):
    # Elimina acentos (ej: á -> a)
    nfkd_form = unicodedata.normalize('NFKD', texto)
    solo_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Cambia espacios y caracteres raros por guiones bajos, quita ñ
    return solo_ascii.replace(" ", "_").replace("ñ", "n").replace("Ñ", "N")

# Función mejorada para subir a Storage
def procesar_archivo(archivo, carpeta, identificador):
    if archivo is not None:
        try:
            # Limpiamos nombres para evitar error InvalidKey
            nombre_limpio = limpiar_texto(archivo.name)
            carpeta_limpia = limpiar_texto(carpeta)
            
            ruta = f"{carpeta_limpia}/{identificador}_{nombre_limpio}"
            
            # Subimos con upsert="true" para evitar el error de archivo duplicado
            supabase.storage.from_(BUCKET_NAME).upload(
                path=ruta, 
                file=archivo.getvalue(), 
                file_options={"content-type": archivo.type, "upsert": "true"}
            )
            return supabase.storage.from_(BUCKET_NAME).get_public_url(ruta)
            
        except Exception as e:
            st.error(f"Error en {archivo.name}: {e}")
            return None
    return None

# --- INTERFAZ ---
st.set_page_config(page_title="Grupo AyC",page_icon=":truck:",layout="wide")
st.title("📊 Sistema Centralizado Grupo AyC")
# ==========================================
# CREACIÓN DINÁMICA DE PESTAÑAS (TABS SECRETO)
# ==========================================
# Detectamos si en la URL está la palabra secreta
es_admin = st.query_params.get("admin") == "AyC2026"

if es_admin:
    # Si la URL tiene ?admin=AyC2026, dibuja 7 pestañas (6 normales + 1 secreta)
    tab1, tab2, tab3, tab4, tab5, tab6, tab_reporte = st.tabs([
        "🚗 Alta de Conductores", "🚛 Control de Unidades", "📋 Registro de Operación",
        "🔍 Consulta Integral", "🔄 Actualización de Expedientes", "📊 Verificación de Captura", 
        "📈 Conciliación"
    ])
else:
    # Si es la URL normal, solo dibuja 6 (para proveedores)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🚗 Alta de Conductores", "🚛 Control de Unidades", "📋 Registro de Operación",
        "🔍 Consulta Integral", "🔄 Actualización de Expedientes", "📊 Verificación de Captura"
    ])

# ==========================================
# PESTAÑA 1: ALTA DE CONDUCTOR
# ==========================================
with tab1:
    with st.form("form_conductor", clear_on_submit=True):
        
        st.subheader("📝 Datos Generales")
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo *")
            # max_chars=13 impide físicamente escribir más caracteres
            rfc = st.text_input("RFC *", max_chars=13, help="El RFC para personas físicas debe tener exactamente 13 caracteres.")
            correo = st.text_input("Correo")
        with col2:
            celular = st.text_input("Celular")
            # --- NUEVOS CAMPOS BANCARIOS CON CONTROL DE CARACTERES ---
            banco = st.text_input("Nombre Banco")
            # max_chars=18 impide físicamente que se escriban más de 18 dígitos
            clabe = st.text_input("Clabe Interbancaria", max_chars=18, help="La CLABE debe tener exactamente 18 dígitos numéricos.")
        
        st.divider() # Línea divisoria elegante
        
        st.subheader("📁 Expediente Digital")
        # Reorganización para equilibrar el espacio visual
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### Identidad")
            f_foto = st.file_uploader("Foto")
            f_acta = st.file_uploader("Acta")
            f_curp = st.file_uploader("CURP")
        with c2:
            st.markdown("#### Operación y Control")
            f_nss = st.file_uploader("NSS")
            f_ine = st.file_uploader("INE")
            f_fis = st.file_uploader("Constancia Fiscal")
        with c3:
            st.markdown("#### Fiscal y Bancario")
            f_lic = st.file_uploader("Licencia")
            f_dom = st.file_uploader("Domicilio")
            f_ban = st.file_uploader("Banco (Archivo)") 
        
        # Nueva fila o sección inferior para los restantes
        c4, c5, c6 = st.columns(3)
        with c4:
            f_tox = st.file_uploader("Toxicológico")
        with c5:
            f_est = st.file_uploader("Comprobante de Estudios")
        with c6:
            f_ref = st.file_uploader("Carta de Referencia")
            
        enviar = st.form_submit_button("Guardar Conductor")
        if enviar:
            if not nombre or not rfc:
                st.error("Por favor completa los campos obligatorios (Nombre y RFC)")
            
            # --- VALIDACIÓN PARA EL RFC ---
            elif len(rfc) < 13:
                st.error(f"El RFC está incompleto. Ingresaste {len(rfc)} caracteres de los 13 requeridos.")
            
            # --- VALIDACIONES PARA LA CLABE INTERBANCARIA ---
            elif clabe and len(clabe) < 18:
                st.error(f"La CLABE Interbancaria está incompleta. Ingresaste {len(clabe)} dígitos de los 18 requeridos.")
            elif clabe and not clabe.isdigit():
                st.error("La CLABE Interbancaria solo debe contener caracteres numéricos (números del 0 al 9).")
                
            else:
                datos = {
                    "nombre_driver": nombre, 
                    "rfc": rfc.upper(), 
                    "correo": correo, 
                    "celular": celular,
                    "nombre_banco": banco,            
                    "clabe_interbancaria": clabe,    
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
                    "url_carta_referencia": procesar_archivo(f_ref, "conductores/referencias", rfc)
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
        
        tipo = st.selectbox("Tipo de Unidad", ["Sedan", "Small", "Large"])
        mod = st.number_input("Modelo", 1990, 2030, 2026)
        
        # Nuevos campos de carga
        f_circ = st.file_uploader("Tarjeta Circulación")
        f_seg = st.file_uploader("Seguro")
        f_vin = st.file_uploader("Fotografía VIN")
        f_plac = st.file_uploader("Fotografía Placas")
        
        enviar_u = st.form_submit_button("Registrar Unidad")
        if enviar_u:
            if not p:
                st.error("Las placas son obligatorias.")
            else:
                datos_u = {
                    "placas": p.upper(), 
                    "modelo": int(mod), 
                    "marca": m, 
                    "submarca": sm,
                    "tipo_unidad": tipo,
                    "url_tarjeta_circulacion": procesar_archivo(f_circ, "unidades/tarjetas", p),
                    "url_poliza_seguro": procesar_archivo(f_seg, "unidades/polizas", p),
                    "url_vin": procesar_archivo(f_vin, "unidades/vin", p),
                    "url_placa": procesar_archivo(f_plac, "unidades/placas", p)
                }
                try:
                    supabase.table("unidades").insert(datos_u).execute()
                    st.success("Unidad registrada exitosamente")
                except Exception as e:
                    st.error(f"Error al registrar la unidad: {e}")


# ==========================================
# PESTAÑA 3: REGISTRO DE OPERACIÓN
# ==========================================
with tab3:
    st.header("Captura Dinámica de Despacho Operativo")
    st.write("Módulo relacional. Permite enlazar los conductores y unidades activos en sistema.")
    
    # 1. Definimos variables vacías por defecto para prevenir NameError
    dict_conductores = {}
    dict_unidades = {}
    
    # 2. Intentamos cargar datos desde la base de datos
    try:
        conductores_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver").execute().data
        unidades_db = supabase.table("unidades").select("id_unidad, placas").execute().data
        
        # Mapeo seguro
        dict_conductores = {c["nombre_driver"]: c["id_conductor"] for c in conductores_db}
        dict_unidades = {u["placas"]: u["id_unidad"] for u in unidades_db}
    except Exception as e:
        st.error(f"Error de sincronización con Supabase: {e}")

    # 3. Verificamos que existan datos antes de mostrar el formulario
    if not dict_conductores or not dict_unidades:
        st.warning("⚠️ Atención: Debes tener conductores y unidades registrados para operar.")
    else:
        # =======================================================
        # MÓDULO 1: REGISTRO DE OPERACIÓN (DESPACHO)
        # =======================================================
        with st.form("form_operacion", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                # --- CAMPO: Tipo de Cliente ---
                tipo_cliente = st.selectbox("Tipo de Cliente *", options=["", "Mercado Libre", "Amazon"])
                
                sel_conductor = st.selectbox("Seleccione el Conductor asignado *", options=[""] + list(dict_conductores.keys()))
                sel_unidad = st.selectbox("Seleccione las Placas del Vehículo *", options=[""] + list(dict_unidades.keys()))
                status_operacion = st.selectbox("Estatus del Servicio", options=["En ruta", "Cancelacion", "No show"])
                
                # --- CAMPOS BOOLEANOS Y COSTO ---
                es_ambulancia = st.checkbox("¿Realizó Ambulancia?")
                es_costal = st.checkbox("¿Es Costal?")
                monto_ambulancia = st.number_input("Costo Ambulancia ($)", min_value=0.0, value=0.0, step=100.0)
            
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
            
            c_btn1, c_btn2 = st.columns([1, 4])
            with c_btn1:
                limpiar = st.form_submit_button("Limpiar")
            with c_btn2:
                enviar_operacion = st.form_submit_button("Cerrar y Despachar Operación")
            
            if limpiar:
                st.info("🧹 Formulario reiniciado a sus valores por defecto.")
            
            if enviar_operacion:
                if not tipo_cliente or not sel_conductor or not sel_unidad:
                    st.error("Por favor selecciona el Tipo de Cliente, el Conductor y el Vehículo válidos para despachar.")
                else:
                    iso_llegada = datetime.combine(fecha_llegada, hora_llegada).isoformat()
                    iso_salida = datetime.combine(fecha_salida, hora_salida).isoformat()
                    
                    datos_operacion = {
                        "tipo_cliente": tipo_cliente,
                        "conductor_id": dict_conductores[sel_conductor],
                        "unidad_id": dict_unidades[sel_unidad],
                        "status_operacion": status_operacion,
                        "hora_llegada_hub": iso_llegada,
                        "hora_salida_hub": iso_salida,
                        "paquetes_cargados": int(paquetes),
                        "paradas": int(paradas),
                        "ambulancia": es_ambulancia,
                        "costal": es_costal,
                        "costo_ambulancia_variable": float(monto_ambulancia)
                    }
                    
                    try:
                        supabase.table("registro_operacion").insert(datos_operacion).execute()
                        st.success(f"¡Viaje despachado! (Ambulancia: {'Sí' if es_ambulancia else 'No'} | Costo: ${monto_ambulancia:,.2f})")
                    except Exception as e:
                        st.error(f"Error al registrar la operación en base de datos: {e}")

        # =======================================================
        # MÓDULO 2: REGISTRO DE DEVOLUCIONES (Ya NO está duplicado)
        # =======================================================
        st.write("---")
        st.subheader("📦 Registro de Devoluciones")
        st.write("Captura de paquetes retornados asociando la operación a un conductor y unidad.")

        with st.form("form_devoluciones", clear_on_submit=True):
            col_dev1, col_dev2 = st.columns(2)
            
            with col_dev1:
                dev_cliente = st.selectbox("Tipo de Cliente (Devolución) *", options=["", "Mercado Libre", "Amazon"])
                dev_conductor = st.selectbox("Conductor asignado *", options=[""] + list(dict_conductores.keys()), key="dev_cond")
                dev_unidad = st.selectbox("Placas del Vehículo *", options=[""] + list(dict_unidades.keys()), key="dev_unid")
            
            with col_dev2:
                dev_fecha = st.date_input("Fecha de Devolución *")
                dev_paquetes = st.number_input("Cantidad de Paquetes Devueltos *", min_value=1, step=1, value=1)
            
            enviar_devolucion = st.form_submit_button("Registrar Devolución")
            
            if enviar_devolucion:
                if not dev_cliente or not dev_conductor or not dev_unidad:
                    st.error("⚠️ Por favor selecciona el Cliente, Conductor y Placas para registrar la devolución.")
                else:
                    datos_devolucion = {
                        "fecha_devolucion": dev_fecha.isoformat(),
                        "tipo_cliente": dev_cliente,
                        "conductor_id": dict_conductores[dev_conductor],
                        "unidad_id": dict_unidades[dev_unidad],
                        "paquetes_devueltos": int(dev_paquetes)
                    }
                    
                    try:
                        supabase.table("devoluciones").insert(datos_devolucion).execute()
                        st.success(f"✅ ¡Devolución de {dev_paquetes} paquete(s) de {dev_cliente} registrada correctamente!")
                    except Exception as e:
                        st.error(f"Error al registrar la devolución en la base de datos: {e}")
# ==========================================
# NUEVA PESTAÑA 4: CONSULTA DE EXPEDIENTES
# ==========================================
# (Asegúrate de agregar "🔍 Consulta" a tu lista de st.tabs arriba)
with tab4:
    st.header("🔍 Consulta Integral de Expedientes")
    tipo_consulta = st.radio("¿Qué desea consultar?", ["Conductores", "Unidades"], horizontal=True)
    
    # Función de apoyo para crear el archivo ZIP en memoria
    def generar_zip(diccionario_documentos):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for nombre, url in diccionario_documentos.items():
                try:
                    respuesta = requests.get(url)
                    if respuesta.status_code == 200:
                        # Extraemos la extensión del archivo (pdf, jpg, etc.)
                        ext = url.split('.')[-1]
                        if len(ext) > 4 or not ext.isalnum():
                            ext = "pdf" # Extensión por defecto si no es clara
                        zip_file.writestr(f"{nombre}.{ext}", respuesta.content)
                except Exception:
                    pass # Si un archivo falla al descargar, simplemente lo omite
        return zip_buffer.getvalue()

    if tipo_consulta == "Conductores":
        try:
            res = supabase.table("alta_conductor").select("*").execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                df['nombre_driver'] = df['nombre_driver'].fillna("").astype(str)
                sel = st.selectbox("Seleccione Conductor:", [""] + df['nombre_driver'].tolist())
                
                if sel:
                    fila = df[df['nombre_driver'] == sel]
                    if not fila.empty:
                        reg = fila.iloc[0].to_dict()
                        st.subheader(f"Expediente de: {sel}")
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.write(f"**RFC:** {reg.get('rfc', 'N/A')}")
                            st.write(f"**Correo:** {reg.get('correo', 'N/A')}")
                            st.write(f"**Celular:** {reg.get('celular', 'N/A')}")
                            # --- NUEVOS CAMPOS BANCARIOS ---
                            st.write(f"**Banco:** {reg.get('nombre_banco', 'N/A') or 'N/A'}")
                            st.write(f"**CLABE:** {reg.get('clabe_interbancaria', 'N/A') or 'N/A'}")
                            
                            foto = reg.get('url_fotografia')
                            if foto and isinstance(foto, str):
                                st.image(foto, width=200, caption="Foto de Perfil")
                        with c2:
                            st.write("### Documentación Digital")
                            docs = {
                                "Acta de Nacimiento": "url_acta_nacimiento", "CURP": "url_curp",
                                "Seguro Social (NSS)": "url_seguro_social", "INE": "url_ine",
                                "Constancia Fiscal": "url_constancia_fiscal", "Licencia de Conducir": "url_licencia",
                                "Comprobante Domicilio": "url_comprobante_domicilio", "Carátula Bancaria": "url_caratula_bancaria",
                                "Examen Toxicológico": "url_toxicologico", "Comprobante de Estudios": "url_comprobante_estudios",
                                "Carta de Referencia": "url_carta_referencia"
                            }
                            
                            # Diccionario para almacenar solo los enlaces válidos
                            documentos_validos = {}
                            
                            for nombre, key in docs.items():
                                url = reg.get(key)
                                if url and isinstance(url, str) and url.startswith("http"):
                                    st.link_button(f"📄 Ver {nombre}", url)
                                    documentos_validos[nombre] = url # Guardamos para el ZIP
                                else:
                                    st.caption(f"❌ {nombre}: No cargado")
                            
                            # --- BOTÓN DE DESCARGA MASIVA ---
                            if documentos_validos:
                                st.write("---")
                                st.download_button(
                                    label="📦 Descargar Expediente en ZIP",
                                    data=generar_zip(documentos_validos),
                                    file_name=f"Expediente_{sel.replace(' ', '_')}.zip",
                                    mime="application/zip"
                                )
        except Exception as e:
            st.error(f"Error cargando conductores: {e}")

    else: # --- LÓGICA DE UNIDADES ---
        try:
            res = supabase.table("unidades").select("*").execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                df['placas'] = df['placas'].fillna("").astype(str)
                sel = st.selectbox("Seleccione Placas de la Unidad:", [""] + df['placas'].tolist())
                
                if sel:
                    fila = df[df['placas'] == sel]
                    if not fila.empty:
                        reg = fila.iloc[0].to_dict()
                        st.subheader(f"Unidad Placas: {sel}")
                        st.write(f"**Marca:** {reg.get('marca', 'N/A')} | **Submarca:** {reg.get('submarca', 'N/A')} | **Modelo:** {reg.get('modelo', 'N/A')}")
                        st.write(f"**Tipo de Unidad:** {reg.get('tipo_unidad', 'N/A')}")
                        
                        st.write("### Documentación de Unidad")
                        docs_u = {
                            "Tarjeta de Circulación": "url_tarjeta_circulacion",
                            "Póliza de Seguro": "url_poliza_seguro",
                            "Fotografía VIN": "url_vin",
                            "Fotografía Placas": "url_placa"
                        }
                        
                        documentos_u_validos = {}
                        
                        for nombre, key in docs_u.items():
                            url = reg.get(key)
                            if url and isinstance(url, str) and url.startswith("http"):
                                st.link_button(f"📄 Ver {nombre}", url)
                                documentos_u_validos[nombre] = url # Guardamos para el ZIP
                            else:
                                st.caption(f"❌ {nombre}: No cargado")
                                
                        # --- BOTÓN DE DESCARGA MASIVA ---
                        if documentos_u_validos:
                            st.write("---")
                            st.download_button(
                                label="📦 Descargar Documentos en ZIP",
                                data=generar_zip(documentos_u_validos),
                                file_name=f"Unidad_{sel.replace(' ', '_')}.zip",
                                mime="application/zip"
                            )
        except Exception as e:
            st.error(f"Error cargando unidades: {e}")

# ===============================================
# NUEVA PESTAÑA 5: ACTUALIZACION DE EXPEDIENTES
# ===============================================
with tab5:
    st.header("🔄 Actualización de Expedientes")
    st.info("Utiliza esta sección para subir documentos faltantes, renovaciones o actualizar datos de contacto y bancarios.")
    
    rfc_busqueda = st.text_input("Ingresa el RFC del conductor para actualizar:")
    
    if rfc_busqueda:
        res = supabase.table("alta_conductor").select("*").eq("rfc", rfc_busqueda.upper()).execute()
        
        if res.data:
            reg = res.data[0]
            st.write(f"Conductor encontrado: **{reg['nombre_driver']}**")
            st.write(f"Celular actual: **{reg.get('celular', 'No registrado')}**")
            # --- MOSTRAMOS LOS DATOS BANCARIOS ACTUALES ---
            banco_actual = reg.get('nombre_banco') or 'No registrado'
            clabe_actual = reg.get('clabe_interbancaria') or 'No registrado'
            st.write(f"Banco actual: **{banco_actual}** | CLABE actual: **{clabe_actual}**")
            
            # --- AYUDA VISUAL PARA EL USUARIO ---
            st.write("---")
            st.write("Estado de documentos actuales:")
            docs_map = {
                "Acta de Nacimiento": "url_acta_nacimiento", "CURP": "url_curp",
                "Seguro Social (NSS)": "url_seguro_social", "INE": "url_ine",
                "Constancia Fiscal": "url_constancia_fiscal", "Licencia de Conducir": "url_licencia",
                "Comprobante Domicilio": "url_comprobante_domicilio", "Carátula Bancaria": "url_caratula_bancaria",
                "Examen Toxicológico": "url_toxicologico", "Comprobante de Estudios": "url_comprobante_estudios",
                "Carta de Referencia": "url_carta_referencia"
            }
            cols = st.columns(3)
            for i, (nombre, key) in enumerate(docs_map.items()):
                status = "✅" if reg.get(key) else "❌"
                cols[i % 3].write(f"{status} {nombre}")
            st.write("---")
            
            # --- SELECTOR EXTENDIDO CON DATOS BANCARIOS ---
            opcion = st.selectbox("¿Qué deseas actualizar?", [""] + list(docs_map.keys()) + ["Actualizar Número de Celular", "Actualizar Datos Bancarios"])
            
            if opcion == "Actualizar Número de Celular":
                # Mostramos el valor actual en la caja de texto para que sea más fácil editar
                nuevo_celular = st.text_input("Nuevo número de celular:", value=reg.get('celular') or "")
                if st.button("Guardar nuevo celular"):
                    supabase.table("alta_conductor").update({"celular": nuevo_celular}).eq("rfc", rfc_busqueda.upper()).execute()
                    st.success("¡Celular actualizado correctamente! Recarga la página para ver el cambio.")
            
            # --- NUEVA LÓGICA PARA ACTUALIZAR BANCO Y CLABE ---
            elif opcion == "Actualizar Datos Bancarios":
                nuevo_banco = st.text_input("Nuevo Nombre del Banco:", value=reg.get('nombre_banco') or "")
                # Bloqueo físico de 18 caracteres
                nueva_clabe = st.text_input("Nueva CLABE Interbancaria:", max_chars=18, value=reg.get('clabe_interbancaria') or "")
                
                if st.button("Guardar datos bancarios"):
                    # Validaciones de la CLABE (igual que en el alta)
                    if nueva_clabe and len(nueva_clabe) < 18:
                        st.error(f"La CLABE está incompleta. Ingresaste {len(nueva_clabe)} dígitos de los 18 requeridos.")
                    elif nueva_clabe and not nueva_clabe.isdigit():
                        st.error("La CLABE solo debe contener números.")
                    else:
                        supabase.table("alta_conductor").update({
                            "nombre_banco": nuevo_banco,
                            "clabe_interbancaria": nueva_clabe
                        }).eq("rfc", rfc_busqueda.upper()).execute()
                        st.success("¡Datos bancarios actualizados correctamente! Recarga la página para ver el cambio.")
            
            # --- LÓGICA PARA ARCHIVOS ---
            elif opcion in docs_map:
                archivo_nuevo = st.file_uploader(f"Cargar nuevo archivo de {opcion}")
                if st.button("Guardar actualización"):
                    if archivo_nuevo:
                        columna_db = docs_map[opcion]
                        nombre_carpeta = opcion.lower().replace(" ", "_")
                        ruta_storage = f"conductores/{nombre_carpeta}s"
                        
                        nueva_url = procesar_archivo(archivo_nuevo, ruta_storage, rfc_busqueda.upper())
                        
                        supabase.table("alta_conductor").update({columna_db: nueva_url}).eq("rfc", rfc_busqueda.upper()).execute()
                        st.success(f"¡{opcion} actualizado correctamente! Recarga la página para ver el cambio.")
                    else:
                        st.warning("Por favor selecciona un archivo.")
        else:
            st.error("No se encontró ningún conductor con ese RFC.")


# ===============================================
# NUEVA PESTAÑA 6: VERIFICACION DE CAPTURA
# ===============================================
# ===============================================
# NUEVA PESTAÑA 6: VERIFICACION DE CAPTURA
# ===============================================
with tab6:
    st.header("📊 Verificación de Captura")
    st.write("Consulta, verifica y edita los registros operativos y devoluciones del sistema.")

    # --- SELECCIÓN DE MÓDULO ---
    modulo_consulta = st.radio("¿Qué registros deseas consultar?", ["Despachos Operativos", "Devoluciones"], horizontal=True)

    # --- FILTROS DE FECHA ---
    c_ini, c_fin = st.columns(2)
    with c_ini:
        fecha_inicio = st.date_input("Fecha de Inicio")
    with c_fin:
        fecha_fin = st.date_input("Fecha de Término")

    if st.button("Buscar Capturas"):
        try:
            # Descargamos los catálogos base
            cond_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver").execute().data
            unid_db = supabase.table("unidades").select("id_unidad, placas, tipo_unidad").execute().data

            map_cond = {c["id_conductor"]: c["nombre_driver"] for c in cond_db}
            map_unid = {u["id_unidad"]: u["placas"] for u in unid_db}
            map_tipo_unid = {u["id_unidad"]: u.get("tipo_unidad", "N/A") for u in unid_db}

            st.session_state["tab6_map_cond"] = map_cond
            st.session_state["tab6_map_unid"] = map_unid
            st.session_state["tab6_map_tipo"] = map_tipo_unid
            st.session_state["tab6_modulo_activo"] = modulo_consulta

            if modulo_consulta == "Despachos Operativos":
                res_op = supabase.table("registro_operacion").select("*").execute()
                df_op = pd.DataFrame(res_op.data)

                if not df_op.empty:
                    df_op["Conductor"] = df_op["conductor_id"].map(map_cond)
                    df_op["Placas"] = df_op["unidad_id"].map(map_unid)
                    df_op["Tipo Unidad"] = df_op["unidad_id"].map(map_tipo_unid)
                    df_op["hora_llegada_hub_raw"] = pd.to_datetime(df_op["hora_llegada_hub"]).dt.tz_localize(None)
                    df_op["fecha_match"] = df_op["hora_llegada_hub_raw"].dt.date

                    # --- CRUCE DE DEVOLUCIONES ---
                    res_dev = supabase.table("devoluciones").select("fecha_devolucion, conductor_id, unidad_id, paquetes_devueltos").execute()
                    df_dev = pd.DataFrame(res_dev.data)
                    
                    if not df_dev.empty:
                        df_dev["fecha_match"] = pd.to_datetime(df_dev["fecha_devolucion"]).dt.date
                        df_dev_agg = df_dev.groupby(["fecha_match", "conductor_id", "unidad_id"])["paquetes_devueltos"].sum().reset_index()
                        df_op = pd.merge(df_op, df_dev_agg, on=["fecha_match", "conductor_id", "unidad_id"], how="left")
                    else:
                        df_op["paquetes_devueltos"] = 0
                        
                    df_op["paquetes_devueltos"] = df_op["paquetes_devueltos"].fillna(0).astype(int)

                    mascara = (df_op["hora_llegada_hub_raw"].dt.date >= fecha_inicio) & (df_op["hora_llegada_hub_raw"].dt.date <= fecha_fin)
                    df_filtrado = df_op.loc[mascara].copy()

                    if not df_filtrado.empty:
                        df_filtrado["hora_llegada_hub_str"] = df_filtrado["hora_llegada_hub_raw"].dt.strftime('%Y-%m-%d %H:%M')
                        st.session_state["tab6_df"] = df_filtrado
                    else:
                        st.warning(f"No se encontraron despachos operativos entre {fecha_inicio} y {fecha_fin}.")
                        st.session_state.pop("tab6_df", None)
                else:
                    st.info("Aún no hay registros de operaciones.")
                    st.session_state.pop("tab6_df", None)

            elif modulo_consulta == "Devoluciones":
                res_dev = supabase.table("devoluciones").select("*").execute()
                df_dev = pd.DataFrame(res_dev.data)

                if not df_dev.empty:
                    df_dev["Conductor"] = df_dev["conductor_id"].map(map_cond)
                    df_dev["Placas"] = df_dev["unidad_id"].map(map_unid)
                    df_dev["fecha_dev_raw"] = pd.to_datetime(df_dev["fecha_devolucion"]).dt.date

                    mascara = (df_dev["fecha_dev_raw"] >= fecha_inicio) & (df_dev["fecha_dev_raw"] <= fecha_fin)
                    df_filtrado = df_dev.loc[mascara].copy()

                    if not df_filtrado.empty:
                        df_filtrado["fecha_dev_str"] = df_filtrado["fecha_dev_raw"].astype(str)
                        st.session_state["tab6_df"] = df_filtrado
                    else:
                        st.warning(f"No se encontraron devoluciones entre {fecha_inicio} y {fecha_fin}.")
                        st.session_state.pop("tab6_df", None)
                else:
                    st.info("Aún no hay devoluciones registradas.")
                    st.session_state.pop("tab6_df", None)

        except Exception as e:
            st.error(f"Error al generar la consulta: {e}")

    # =======================================================
    # VISTA Y EDICIÓN PERSISTENTE
    # =======================================================
    if "tab6_df" in st.session_state and "tab6_modulo_activo" in st.session_state:
        df_filtrado = st.session_state["tab6_df"]
        modulo_activo = st.session_state["tab6_modulo_activo"]
        map_cond = st.session_state["tab6_map_cond"]
        map_unid = st.session_state["tab6_map_unid"]
        map_tipo_unid = st.session_state["tab6_map_tipo"]

        st.write("---")

        # -------------------------------------------------------
        # ESCENARIO A: DESPACHOS OPERATIVOS
        # -------------------------------------------------------
        if modulo_activo == "Despachos Operativos":
            columnas_mostrar = ["hora_llegada_hub_str", "Conductor", "Placas", "Tipo Unidad", "tipo_cliente", "status_operacion", "ambulancia", "costo_ambulancia_variable"]
            if "costal" in df_filtrado.columns: columnas_mostrar.append("costal")
            if "paquetes_devueltos" in df_filtrado.columns: columnas_mostrar.append("paquetes_devueltos")
            columnas_mostrar.extend(["paquetes_cargados", "paradas"])
            columnas_existentes = [c for c in columnas_mostrar if c in df_filtrado.columns]
            
            df_mostrar = df_filtrado[columnas_existentes].rename(columns={
                "hora_llegada_hub_str": "Hora de Arribo", "tipo_cliente": "Cliente",
                "status_operacion": "Condición", "paquetes_cargados": "Paquetes",
                "paquetes_devueltos": "Devols.", "paradas": "Paradas", "costo_ambulancia_variable": "Costo Amb."
            })

            # Performance y Llenado seguro de Costo (Por si hay NaN en BD)
            if "Costo Amb." in df_mostrar.columns:
                df_mostrar["Costo Amb."] = df_mostrar["Costo Amb."].fillna(0.0)
                
            if "Paquetes" in df_mostrar.columns and "Devols." in df_mostrar.columns:
                df_mostrar["Performance %"] = df_mostrar.apply(lambda x: ((x["Paquetes"] - x["Devols."]) / x["Paquetes"] * 100) if x["Paquetes"] > 0 else 0, axis=1)

            configuracion_columnas = {
                "Cliente": st.column_config.TextColumn("Cliente", width="small"),
                "Condición": st.column_config.TextColumn("Condición", width="small"),
                "ambulancia": st.column_config.CheckboxColumn("Ambulancia", width="small"),
                "Costo Amb.": st.column_config.NumberColumn("Costo Amb.", format="$ %.2f"),
                "costal": st.column_config.CheckboxColumn("Costal", width="small"),
                "Paquetes": st.column_config.NumberColumn("Paquetes", width="small"),
                "Devols.": st.column_config.NumberColumn("Devols.", width="small"),
                "Paradas": st.column_config.NumberColumn("Paradas", width="small"),
                "Performance %": st.column_config.NumberColumn("Performance %", format="%.1f %%", width="small")
            }
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True, column_config=configuracion_columnas)

            # --- EDICIÓN OPERACIONES ---
            st.write("---")
            st.subheader("✏️ Modificar o Eliminar Despacho")
            df_filtrado["_label"] = df_filtrado["hora_llegada_hub_str"].astype(str) + " | " + df_filtrado["Conductor"].fillna("Sin conductor")
            opciones = df_filtrado["_label"].tolist()
            col_id_op = "id_operacion" if "id_operacion" in df_filtrado.columns else "id"
            ids = df_filtrado[col_id_op].tolist()

            seleccion = st.selectbox("Selecciona el despacho a modificar:", opciones)
            idx_sel = opciones.index(seleccion)
            id_sel = ids[idx_sel]
            fila = df_filtrado.iloc[idx_sel]

            with st.form("form_edicion_op"):
                fe1, fe2 = st.columns(2)
                with fe1:
                    nueva_fecha = st.date_input("Fecha de Arribo", value=fila["hora_llegada_hub_raw"].date())
                    nueva_hora = st.time_input("Hora de Arribo", value=fila["hora_llegada_hub_raw"].time())
                    nombres_cond = list(map_cond.values()); ids_cond = list(map_cond.keys())
                    nuevo_cond = st.selectbox("Conductor", nombres_cond, index=nombres_cond.index(map_cond.get(fila["conductor_id"], nombres_cond[0])))
                    nuevo_cond_id = ids_cond[nombres_cond.index(nuevo_cond)]
                    placas_list = list(map_unid.values()); ids_unid = list(map_unid.keys())
                    nueva_placa = st.selectbox("Placas / Unidad", placas_list, index=placas_list.index(map_unid.get(fila["unidad_id"], placas_list[0])))
                    nueva_unid_id = ids_unid[placas_list.index(nueva_placa)]
                with fe2:
                    st.text_input("Tipo de Unidad", value=map_tipo_unid.get(nueva_unid_id, "N/A"), disabled=True)
                    nuevo_cliente = st.selectbox("Cliente", ["Mercado Libre", "Amazon"], index=["Mercado Libre", "Amazon"].index(fila["tipo_cliente"] if fila["tipo_cliente"] in ["Mercado Libre", "Amazon"] else "Mercado Libre"))
                    nueva_condicion = st.selectbox("Condición", ["En ruta", "Cancelacion", "No show"], index=["En ruta", "Cancelacion", "No show"].index(fila["status_operacion"] if fila["status_operacion"] in ["En ruta", "Cancelacion", "No show"] else "En ruta"))
                    
                    c_box1, c_box2 = st.columns(2)
                    nueva_ambulancia = c_box1.checkbox("¿Realizó Ambulancia?", value=str(fila["ambulancia"]).upper() in ["SÍ", "SI", "TRUE", "1"])
                    nuevo_costal = c_box2.checkbox("¿Es Costal?", value=str(fila.get("costal", False)).upper() in ["SÍ", "SI", "TRUE", "1"])

                fe3, fe4 = st.columns(2)
                
                # --- SOLUCIÓN AL TYPE_ERROR DE PANDAS/NULL ---
                val_costo = fila.get("costo_ambulancia_variable", 0.0)
                if pd.isna(val_costo) or val_costo is None or val_costo == "": 
                    val_costo = 0.0
                    
                nuevo_monto_ambulancia = fe3.number_input("Costo Ambulancia ($)", min_value=0.0, value=float(val_costo))
                nuevos_paquetes = fe4.number_input("Paquetes Cargados", min_value=0, value=int(fila["paquetes_cargados"]))
                nuevas_paradas = fe4.number_input("Paradas", min_value=0, value=int(fila["paradas"]))

                # --- SOLUCIÓN AL MISSING SUBMIT BUTTON ---
                # 1. Se declaran los botones DENTRO del form, a nivel raíz del form
                col_guardar, col_borrar = st.columns([3, 1])
                btn_guardar_op = col_guardar.form_submit_button("💾 Guardar Cambios Operación")
                btn_borrar_op = col_borrar.form_submit_button("🗑️ Eliminar")

                # 2. Se evalúa la acción de los botones después de declararlos
                if btn_guardar_op:
                    supabase.table("registro_operacion").update({
                        "hora_llegada_hub": datetime.combine(nueva_fecha, nueva_hora).isoformat(),
                        "conductor_id": nuevo_cond_id, "unidad_id": nueva_unid_id, "tipo_cliente": nuevo_cliente,
                        "status_operacion": nueva_condicion, "ambulancia": nueva_ambulancia, "costal": nuevo_costal,
                        "costo_ambulancia_variable": float(nuevo_monto_ambulancia),
                        "paquetes_cargados": nuevos_paquetes, "paradas": nuevas_paradas
                    }).eq(col_id_op, id_sel).execute()
                    st.success("✅ Registro actualizado correctamente."); st.session_state.pop("tab6_df", None); st.rerun()
                
                if btn_borrar_op:
                    supabase.table("registro_operacion").delete().eq(col_id_op, id_sel).execute()
                    st.warning("🗑️ Registro eliminado."); st.session_state.pop("tab6_df", None); st.rerun()

        # -------------------------------------------------------
        # ESCENARIO B: DEVOLUCIONES
        # -------------------------------------------------------
        elif modulo_activo == "Devoluciones":
            m1, m2 = st.columns(2)
            m1.metric("Total Devoluciones", len(df_filtrado))
            m2.metric("Total Paquetes", int(df_filtrado["paquetes_devueltos"].sum()))
            
            df_mostrar_dev = df_filtrado[["fecha_dev_str", "Conductor", "Placas", "tipo_cliente", "paquetes_devueltos"]].rename(columns={"fecha_dev_str": "Fecha", "tipo_cliente": "Cliente", "paquetes_devueltos": "Paquetes Devueltos"})
            st.dataframe(df_mostrar_dev, use_container_width=True, hide_index=True)

            st.write("---")
            st.subheader("✏️ Modificar o Eliminar Devolución")
            df_filtrado["_label"] = df_filtrado["fecha_dev_str"] + " | " + df_filtrado["Conductor"].fillna("Sin conductor") + " | " + df_filtrado["tipo_cliente"]
            opciones_dev = df_filtrado["_label"].tolist()
            sel_dev = st.selectbox("Selecciona devolución a modificar:", opciones_dev)
            idx_dev = opciones_dev.index(sel_dev)
            id_sel_dev = df_filtrado.iloc[idx_dev]["id"]
            fila_dev = df_filtrado.iloc[idx_dev]

            with st.form("form_edicion_dev"):
                fd1, fd2 = st.columns(2)
                nueva_fecha_d = fd1.date_input("Fecha", value=fila_dev["fecha_dev_raw"])
                nuevo_cond_d = fd1.selectbox("Conductor", list(map_cond.values()), index=list(map_cond.values()).index(map_cond.get(fila_dev["conductor_id"], list(map_cond.values())[0])))
                nueva_placa_d = fd1.selectbox("Placas", list(map_unid.values()), index=list(map_unid.values()).index(map_unid.get(fila_dev["unidad_id"], list(map_unid.values())[0])))
                
                nuevo_cliente_d = fd2.selectbox("Cliente", ["Mercado Libre", "Amazon"], index=["Mercado Libre", "Amazon"].index(fila_dev["tipo_cliente"] if fila_dev["tipo_cliente"] in ["Mercado Libre", "Amazon"] else "Mercado Libre"))
                nuevos_paquetes_d = fd2.number_input("Paquetes Devueltos", min_value=1, value=int(fila_dev["paquetes_devueltos"]))
                nuevo_costal_d = fd2.checkbox("¿Ruta de Costales?", value=str(fila_dev.get("costal", False)).upper() in ["SÍ", "SI", "TRUE", "1"])
                
                # --- SOLUCIÓN AL MISSING SUBMIT BUTTON PARA DEVOLUCIONES ---
                col_g, col_b = st.columns([3, 1])
                btn_guardar_dev = col_g.form_submit_button("💾 Guardar Cambios")
                btn_borrar_dev = col_b.form_submit_button("🗑️ Eliminar")

                if btn_guardar_dev:
                    supabase.table("devoluciones").update({
                        "fecha_devolucion": nueva_fecha_d.isoformat(), "conductor_id": list(map_cond.keys())[list(map_cond.values()).index(nuevo_cond_d)],
                        "unidad_id": list(map_unid.keys())[list(map_unid.values()).index(nueva_placa_d)], "tipo_cliente": nuevo_cliente_d,
                        "paquetes_devueltos": nuevos_paquetes_d, "costal": nuevo_costal_d
                    }).eq("id", id_sel_dev).execute()
                    st.success("✅ Actualizado."); st.session_state.pop("tab6_df", None); st.rerun()
                
                if btn_borrar_dev:
                    supabase.table("devoluciones").delete().eq("id", id_sel_dev).execute()
                    st.warning("🗑️ Eliminado."); st.session_state.pop("tab6_df", None); st.rerun()

# ===============================================
# NUEVA PESTAÑA: REPORTE DE CONCILIACIÓN (SECRETA)
# ===============================================
if es_admin:
    with tab_reporte: 
        st.header("📊 Reporte de Conciliación y Facturación")
        st.info("Esta pestaña es privada mediante URL.")
        
        # Parámetros del reporte
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha_ini = st.date_input("Fecha Inicio de Corte")
        with c2:
            fecha_fin = st.date_input("Fecha Fin de Corte")
        with c3:
            semana_corte = st.number_input("Número de Semana (Ej. 24)", min_value=1, step=1, value=24)
            
        if st.button("Generar Conciliación"):
            try:
                res_reporte = supabase.table("registro_operacion").select("*").execute()
                df_rep = pd.DataFrame(res_reporte.data)
                
                if not df_rep.empty:
                    df_rep["fecha_raw"] = pd.to_datetime(df_rep["hora_llegada_hub"]).dt.tz_localize(None).dt.date
                    mascara_fechas = (df_rep["fecha_raw"] >= fecha_ini) & (df_rep["fecha_raw"] <= fecha_fin)
                    df_periodo = df_rep.loc[mascara_fechas].copy()
                    
                    if not df_periodo.empty:
                        # 2. CÁLCULOS FINANCIEROS RESICO
                        if "monto_final_unidad" not in df_periodo.columns:
                            df_periodo["monto_final_unidad"] = 1750.00 
                            
                        df_periodo["Subtotal"] = df_periodo["monto_final_unidad"]
                        df_periodo["IVA"] = df_periodo["Subtotal"] * 0.16
                        # Retención exclusiva para régimen RESICO (1.25% ISR)
                        df_periodo["Retencion"] = df_periodo["Subtotal"] * 0.0125
                        df_periodo["Total"] = df_periodo["Subtotal"] + df_periodo["IVA"] - df_periodo["Retencion"]
                        
                        dia_ini = fecha_ini.strftime('%d')
                        dia_fin = fecha_fin.strftime('%d')
                        meses = ["", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
                        mes_texto = meses[fecha_fin.month]
                        
                        st.divider()
                        
                        # --- SECCIÓN 1: AMAZON ---
                        st.subheader(f"CORTE {dia_ini} AL {dia_fin} DE {mes_texto} SEMANA {semana_corte} AMAZON")
                        df_amazon = df_periodo[df_periodo["tipo_cliente"] == "Amazon"].copy()
                        
                        if not df_amazon.empty:
                            st.dataframe(df_amazon, use_container_width=True)
                            
                            st.write("**Resumen Financiero - Amazon**")
                            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                            col_a1.metric("Subtotal", f"${df_amazon['Subtotal'].sum():,.2f}")
                            col_a2.metric("IVA (16%)", f"${df_amazon['IVA'].sum():,.2f}")
                            col_a3.metric("Retención (1.25%)", f"${df_amazon['Retencion'].sum():,.2f}")
                            col_a4.metric("Total Final", f"${df_amazon['Total'].sum():,.2f}")
                        else:
                            st.info("No hay registros de Amazon para este periodo.")
                            
                        st.divider()
                        
                        # --- SECCIÓN 2: MERCADO LIBRE ---
                        st.subheader(f"CORTE {dia_ini} AL {dia_fin} DE {mes_texto} SEMANA {semana_corte} MERCADO LIBRE")
                        df_ml = df_periodo[df_periodo["tipo_cliente"] == "Mercado Libre"].copy()
                        
                        if not df_ml.empty:
                            st.dataframe(df_ml, use_container_width=True)
                            
                            st.write("**Resumen Financiero - Mercado Libre**")
                            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                            col_m1.metric("Subtotal", f"${df_ml['Subtotal'].sum():,.2f}")
                            col_m2.metric("IVA (16%)", f"${df_ml['IVA'].sum():,.2f}")
                            col_m3.metric("Retención (1.25%)", f"${df_ml['Retencion'].sum():,.2f}")
                            col_m4.metric("Total Final", f"${df_ml['Total'].sum():,.2f}")
                        else:
                            st.info("No hay registros de Mercado Libre para este periodo.")
                            
                        st.divider()
                        
                        # --- GRAN TOTAL GRUPO AYC ---
                        st.subheader("Gran Total del Periodo (Todos los Clientes)")
                        t_sub = df_periodo['Subtotal'].sum()
                        t_iva = df_periodo['IVA'].sum()
                        t_ret = df_periodo['Retencion'].sum()
                        t_tot = df_periodo['Total'].sum()
                        
                        st.markdown(f"""
                        * **SUBTOTAL:** ${t_sub:,.2f}
                        * **IVA:** ${t_iva:,.2f}
                        * **RETENCIÓN (1.25%):** ${t_ret:,.2f}
                        * **TOTAL FINAL:** **${t_tot:,.2f}**
                        """)
                    else:
                        st.warning("No se encontraron viajes capturados en las fechas seleccionadas.")
            except Exception as e:
                st.error(f"Error al generar el reporte: {e}")
