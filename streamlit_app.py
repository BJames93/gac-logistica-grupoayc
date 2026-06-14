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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🚗 Alta de Conductores", "🚛 Control de Unidades", "📋 Registro de Operación","🔍 Consulta Integral","🔄 Actualización de Expedientes","📊 Verificación de Captura"])

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
                
                # Opciones con espacio en blanco al inicio [""]
                sel_conductor = st.selectbox("Seleccione el Conductor asignado *", options=[""] + list(dict_conductores.keys()))
                sel_unidad = st.selectbox("Seleccione las Placas del Vehículo *", options=[""] + list(dict_unidades.keys()))
                status_operacion = st.selectbox("Estatus del Servicio", options=["En ruta", "Cancelacion", "No show"])
                
                # --- CAMPOS BOOLEANOS (CHECKBOXES) ---
                es_ambulancia = st.checkbox("¿Realizó Ambulancia?")
                es_costal = st.checkbox("¿Es Costal?") # <-- NUEVO CAMPO AGREGADO
            
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
            
            # Botones dentro del form
            c_btn1, c_btn2 = st.columns([1, 4])
            with c_btn1:
                limpiar = st.form_submit_button("Limpiar")
            with c_btn2:
                enviar_operacion = st.form_submit_button("Cerrar y Despachar Operación")
            
            # --- FEEDBACK VISUAL DEL BOTÓN LIMPIAR ---
            if limpiar:
                st.info("🧹 Formulario reiniciado a sus valores por defecto.")
            
            # --- LÓGICA DE ENVÍO CON VALIDACIÓN ---
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
                        "costal": es_costal # <-- NUEVO CAMPO AGREGADO AL DICCIONARIO
                    }
                    
                    try:
                        supabase.table("registro_operacion").insert(datos_operacion).execute()
                        st.success(f"¡Viaje de {tipo_cliente} despachado correctamente! (Ambulancia: {'Sí' if es_ambulancia else 'No'} | Costal: {'Sí' if es_costal else 'No'})")
                    except Exception as e:
                        st.error(f"Error al registrar la operación en base de datos: {e}")

        # =======================================================
        # MÓDULO 2: REGISTRO DE DEVOLUCIONES
        # =======================================================
        st.write("---")
        st.subheader("📦 Registro de Devoluciones")
        st.write("Captura de paquetes retornados asociando la operación a un conductor y unidad.")

        with st.form("form_devoluciones", clear_on_submit=True):
            col_dev1, col_dev2 = st.columns(2)
            
            with col_dev1:
                dev_cliente = st.selectbox("Tipo de Cliente (Devolución) *", options=["", "Mercado Libre", "Amazon"])
                # Agregamos 'key' únicas para no generar conflictos con los selectbox del formulario de arriba
                dev_conductor = st.selectbox("Conductor asignado *", options=[""] + list(dict_conductores.keys()), key="dev_cond")
                dev_unidad = st.selectbox("Placas del Vehículo *", options=[""] + list(dict_unidades.keys()), key="dev_unid")
            
            with col_dev2:
                # --- NUEVO CAMPO: FECHA DE DEVOLUCIÓN ---
                dev_fecha = st.date_input("Fecha de Devolución *")
                dev_paquetes = st.number_input("Cantidad de Paquetes Devueltos *", min_value=1, step=1, value=1)
            
            enviar_devolucion = st.form_submit_button("Registrar Devolución")
            
            if enviar_devolucion:
                if not dev_cliente or not dev_conductor or not dev_unidad:
                    st.error("⚠️ Por favor selecciona el Cliente, Conductor y Placas para registrar la devolución.")
                else:
                    # Preparamos los datos para la NUEVA tabla
                    datos_devolucion = {
                        "fecha_devolucion": dev_fecha.isoformat(), # Convertimos la fecha a formato ISO
                        "tipo_cliente": dev_cliente,
                        "conductor_id": dict_conductores[dev_conductor],
                        "unidad_id": dict_unidades[dev_unidad],
                        "paquetes_devueltos": int(dev_paquetes)
                        # "creado_por": usuario_id_activo  # Descomenta esto si también llevas control de quién lo capturó
                    }
                    
                    try:
                        # Hacemos el insert apuntando a la tabla 'devoluciones'
                        supabase.table("devoluciones").insert(datos_devolucion).execute()
                        st.success(f"✅ ¡Devolución de {dev_paquetes} paquete(s) de {dev_cliente} registrada correctamente para la fecha {dev_fecha}!")
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
with tab6:
    st.header("📊 Verificación de Captura")
    st.write("Consulta, verifica y edita los registros operativos y devoluciones del sistema.")

    # --- SELECCIÓN DE MÓDULO ---
    modulo_consulta = st.radio(
        "¿Qué registros deseas consultar?", 
        ["Despachos Operativos", "Devoluciones"], 
        horizontal=True
    )

    # --- FILTROS DE FECHA ---
    c_ini, c_fin = st.columns(2)
    with c_ini:
        fecha_inicio = st.date_input("Fecha de Inicio")
    with c_fin:
        fecha_fin = st.date_input("Fecha de Término")

    if st.button("Buscar Capturas"):
        try:
            # Descargamos los catálogos base (sirven para ambos módulos)
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
            m1, m2, m3 = st.columns(3)
            m1.metric("Total de Viajes", len(df_filtrado))
            m2.metric("Paquetes Procesados", int(df_filtrado["paquetes_cargados"].sum()))
            m3.metric("Paradas Planificadas", int(df_filtrado["paradas"].sum()))
            st.write("---")

            columnas_mostrar = ["hora_llegada_hub_str", "Conductor", "Placas", "Tipo Unidad", "tipo_cliente", "status_operacion", "ambulancia"]
            if "costal" in df_filtrado.columns:
                columnas_mostrar.append("costal")
            columnas_mostrar.extend(["paquetes_cargados", "paradas"])

            df_mostrar = df_filtrado[columnas_mostrar].rename(columns={
                "hora_llegada_hub_str": "Hora de Arribo",
                "tipo_cliente": "Cliente",
                "status_operacion": "Condición",
                "paquetes_cargados": "Paquetes",
                "paradas": "Paradas"
            })
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

            st.write("---")
            st.subheader("✏️ Modificar o Eliminar Despacho")
            df_filtrado["_label"] = (
                df_filtrado["hora_llegada_hub_str"].astype(str) + " | " +
                df_filtrado["Conductor"].fillna("Sin conductor") + " | " +
                df_filtrado["Placas"].fillna("Sin placas")
            )
            opciones = df_filtrado["_label"].tolist()
            # Ojo: la tabla operaciones usa id_operacion, o id dependiendo de tu base. 
            # Asegúrate que el nombre de columna de ID aquí coincida con tu base. Usaré 'id_operacion' según tu código anterior.
            col_id_op = "id_operacion" if "id_operacion" in df_filtrado.columns else "id"
            ids = df_filtrado[col_id_op].tolist()

            seleccion = st.selectbox("Selecciona el despacho a modificar:", opciones)
            idx_sel = opciones.index(seleccion)
            id_sel = ids[idx_sel]
            fila = df_filtrado.iloc[idx_sel]

            with st.form("form_edicion_op"):
                fe1, fe2 = st.columns(2)
                with fe1:
                    hora_actual = fila["hora_llegada_hub_raw"]
                    nueva_fecha = st.date_input("Fecha de Arribo", value=hora_actual.date())
                    nueva_hora = st.time_input("Hora de Arribo", value=hora_actual.time())

                    nombres_cond = list(map_cond.values())
                    ids_cond = list(map_cond.keys())
                    cond_actual = map_cond.get(fila["conductor_id"], nombres_cond[0])
                    cond_idx = nombres_cond.index(cond_actual) if cond_actual in nombres_cond else 0
                    nuevo_cond = st.selectbox("Conductor", nombres_cond, index=cond_idx)
                    nuevo_cond_id = ids_cond[nombres_cond.index(nuevo_cond)]

                    placas_list = list(map_unid.values())
                    ids_unid = list(map_unid.keys())
                    placa_actual = map_unid.get(fila["unidad_id"], placas_list[0])
                    unid_idx = placas_list.index(placa_actual) if placa_actual in placas_list else 0
                    nueva_placa = st.selectbox("Placas / Unidad", placas_list, index=unid_idx)
                    nueva_unid_id = ids_unid[placas_list.index(nueva_placa)]

                with fe2:
                    st.text_input("Tipo de Unidad", value=map_tipo_unid.get(nueva_unid_id, "N/A"), disabled=True)
                    clientes_opts = ["Mercado Libre", "Amazon"]
                    cli_actual = fila["tipo_cliente"] if fila["tipo_cliente"] in clientes_opts else clientes_opts[0]
                    nuevo_cliente = st.selectbox("Cliente", clientes_opts, index=clientes_opts.index(cli_actual))

                    condiciones_opts = ["En ruta", "Cancelacion", "No show"]
                    cond_status = fila["status_operacion"] if fila["status_operacion"] in condiciones_opts else condiciones_opts[0]
                    nueva_condicion = st.selectbox("Condición", condiciones_opts, index=condiciones_opts.index(cond_status))

                    c_box1, c_box2 = st.columns(2)
                    with c_box1:
                        amb_actual = str(fila["ambulancia"]).upper() in ["SÍ", "SI", "TRUE", "1"]
                        nueva_ambulancia = st.checkbox("¿Realizó Ambulancia?", value=amb_actual)
                    with c_box2:
                        costal_actual = str(fila.get("costal", False)).upper() in ["SÍ", "SI", "TRUE", "1"]
                        nuevo_costal = st.checkbox("¿Es Costal?", value=costal_actual)

                fe3, fe4 = st.columns(2)
                with fe3:
                    nuevos_paquetes = st.number_input("Paquetes", min_value=0, value=int(fila["paquetes_cargados"]))
                with fe4:
                    nuevas_paradas = st.number_input("Paradas", min_value=0, value=int(fila["paradas"]))

                col_guardar, col_borrar = st.columns([3, 1])
                guardar = col_guardar.form_submit_button("💾 Guardar Cambios Operación", use_container_width=True)
                borrar = col_borrar.form_submit_button("🗑️ Eliminar Registro", use_container_width=True, type="secondary")

            if guardar:
                try:
                    payload = {
                        "hora_llegada_hub": datetime.combine(nueva_fecha, nueva_hora).isoformat(),
                        "conductor_id": nuevo_cond_id, "unidad_id": nueva_unid_id,
                        "tipo_cliente": nuevo_cliente, "status_operacion": nueva_condicion,
                        "ambulancia": nueva_ambulancia, "costal": nuevo_costal,
                        "paquetes_cargados": nuevos_paquetes, "paradas": nuevas_paradas,
                    }
                    supabase.table("registro_operacion").update(payload).eq(col_id_op, id_sel).execute()
                    st.success("✅ Registro actualizado correctamente. Vuelve a buscar para ver los cambios.")
                    st.session_state.pop("tab6_df", None)
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

            if borrar:
                try:
                    supabase.table("registro_operacion").delete().eq(col_id_op, id_sel).execute()
                    st.warning("🗑️ Registro eliminado de la base de datos.")
                    st.session_state.pop("tab6_df", None)
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")

        # -------------------------------------------------------
        # ESCENARIO B: DEVOLUCIONES
        # -------------------------------------------------------
        elif modulo_activo == "Devoluciones":
            m1, m2 = st.columns(2)
            m1.metric("Total de Devoluciones", len(df_filtrado))
            m2.metric("Total Paquetes Devueltos", int(df_filtrado["paquetes_devueltos"].sum()))
            st.write("---")

            cols_dev = ["fecha_dev_str", "Conductor", "Placas", "tipo_cliente", "paquetes_devueltos"]
            if "costal" in df_filtrado.columns:
                cols_dev.append("costal")

            df_mostrar_dev = df_filtrado[cols_dev].rename(columns={
                "fecha_dev_str": "Fecha",
                "tipo_cliente": "Cliente",
                "paquetes_devueltos": "Paquetes Devueltos"
            })
            st.dataframe(df_mostrar_dev, use_container_width=True, hide_index=True)

            st.write("---")
            st.subheader("✏️ Modificar o Eliminar Devolución")
            df_filtrado["_label"] = (
                df_filtrado["fecha_dev_str"] + " | " + 
                df_filtrado["Conductor"].fillna("Sin conductor") + " | " + 
                df_filtrado["tipo_cliente"]
            )
            opciones_dev = df_filtrado["_label"].tolist()
            # En el script SQL la llave de devoluciones la llamamos 'id'
            ids_dev = df_filtrado["id"].tolist()

            sel_dev = st.selectbox("Selecciona la devolución a modificar:", opciones_dev)
            idx_dev = opciones_dev.index(sel_dev)
            id_sel_dev = ids_dev[idx_dev]
            fila_dev = df_filtrado.iloc[idx_dev]

            with st.form("form_edicion_dev"):
                fd1, fd2 = st.columns(2)
                with fd1:
                    fecha_act = fila_dev["fecha_dev_raw"]
                    nueva_fecha_d = st.date_input("Fecha de Devolución", value=fecha_act)

                    nombres_cond = list(map_cond.values())
                    ids_cond = list(map_cond.keys())
                    cond_act = map_cond.get(fila_dev["conductor_id"], nombres_cond[0])
                    nuevo_cond_d = st.selectbox("Conductor", nombres_cond, index=nombres_cond.index(cond_act))
                    nuevo_cond_id_d = ids_cond[nombres_cond.index(nuevo_cond_d)]

                    placas_list = list(map_unid.values())
                    ids_unid = list(map_unid.keys())
                    placa_act = map_unid.get(fila_dev["unidad_id"], placas_list[0])
                    nueva_placa_d = st.selectbox("Placas", placas_list, index=placas_list.index(placa_act))
                    nueva_unid_id_d = ids_unid[placas_list.index(nueva_placa_d)]

                with fd2:
                    clientes_opts = ["Mercado Libre", "Amazon"]
                    cli_act = fila_dev["tipo_cliente"] if fila_dev["tipo_cliente"] in clientes_opts else clientes_opts[0]
                    nuevo_cliente_d = st.selectbox("Cliente", clientes_opts, index=clientes_opts.index(cli_act))
                    
                    nuevos_paquetes_d = st.number_input("Paquetes Devueltos", min_value=1, value=int(fila_dev["paquetes_devueltos"]))
                    
                    # Checkbox de Costal para devoluciones
                    costal_act_d = str(fila_dev.get("costal", False)).upper() in ["SÍ", "SI", "TRUE", "1"]
                    nuevo_costal_d = st.checkbox("¿Ruta de Costales?", value=costal_act_d)

                col_g_dev, col_b_dev = st.columns([3, 1])
                guardar_dev = col_g_dev.form_submit_button("💾 Guardar Cambios Devolución", use_container_width=True)
                borrar_dev = col_b_dev.form_submit_button("🗑️ Eliminar Registro", use_container_width=True, type="secondary")

            if guardar_dev:
                try:
                    payload_dev = {
                        "fecha_devolucion": nueva_fecha_d.isoformat(),
                        "conductor_id": nuevo_cond_id_d,
                        "unidad_id": nueva_unid_id_d,
                        "tipo_cliente": nuevo_cliente_d,
                        "paquetes_devueltos": nuevos_paquetes_d,
                        "costal": nuevo_costal_d
                    }
                    supabase.table("devoluciones").update(payload_dev).eq("id", id_sel_dev).execute()
                    st.success("✅ Devolución actualizada correctamente. Vuelve a buscar para ver los cambios.")
                    st.session_state.pop("tab6_df", None)
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

            if borrar_dev:
                try:
                    supabase.table("devoluciones").delete().eq("id", id_sel_dev).execute()
                    st.warning("🗑️ Devolución eliminada de la base de datos.")
                    st.session_state.pop("tab6_df", None)
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
