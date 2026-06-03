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
