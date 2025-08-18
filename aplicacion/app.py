# app.py
# Este archivo contiene la lógica del servidor para la aplicación.
# Confirma que tienes instalado web.py: pip install web.py

import web
import os
import json
import sqlite3
import hashlib
import datetime

web.config.debug = True  # FIX: Habilitado para depuración
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
render = web.template.render(template_dir, globals={'static': '/static'})

# --- Rutas de la aplicación (URLS) ---
urls = (
    '/', 'Welcome',
    '/login', 'Login',
    '/logout', 'Logout',
    '/administrador', 'AdminArea',
    '/administrador_registrar_usuario', 'RegistroUsuario',
    '/enfermeras', 'EnfermerasArea',
    '/registro_citas', 'RegistroCitas',
    '/registro_lactantes', 'RegistroLactantes',
    '/reportes', 'ReportesArea',
    '/reportes_generales', 'ReportesGenerales',
    '/reportes_por_lactante', 'ReportesPorLactante',
    '/visualizacion_citas', 'VisualizacionCitas',
    '/visualizacion_lactantes', 'VisualizacionLactantes',
    '/visualizacion_usuarios', 'VisualizacionUsuarios',
    '/api/generate_report', 'ReportesAPI',
    '/static/(.*)', 'Static',
    r'/eliminar_lactante/(\d+)', 'EliminarLactante'
)

# --- Manejador de Archivos Estáticos ---
class Static:
    def GET(self, file):
        try:
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            with open(os.path.join(static_dir, file), 'rb') as f:
                return f.read()
        except IOError:
            raise web.notfound()

# --- Conexión y Configuración de la Base de Datos ---
DB_FILE = 'vinculo_de_vida.db'

def get_db():
    """Establece y devuelve una conexión a la base de datos."""
    db = getattr(web.ctx, '_db', None)
    if db is None:
        db = web.ctx._db = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row
    return db

def setup_database():
    """Crea las tablas y inserta los datos iniciales si la base de datos no existe."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        create_tables_sql = """
            CREATE TABLE IF NOT EXISTS Rol (id_rol INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, permiso TEXT);
            CREATE TABLE IF NOT EXISTS Usuarios (id_usuario INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, num_telefono TEXT UNIQUE, contraseña TEXT NOT NULL, id_rol INTEGER, FOREIGN KEY (id_rol) REFERENCES Rol(id_rol));
            CREATE TABLE IF NOT EXISTS Auditoria (id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER, accion TEXT NOT NULL, tabla_afectada TEXT NOT NULL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario));
            CREATE TABLE IF NOT EXISTS Reportes (id_reportes INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER, tipo TEXT NOT NULL, fecha_generado TIMESTAMP DEFAULT CURRENT_TIMESTAMP, contenido TEXT, FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario));
            CREATE TABLE IF NOT EXISTS Motivo (id_motivo INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, tipo_de_motivo TEXT);
            CREATE TABLE IF NOT EXISTS Madres (id_madre INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, apellido_paterno TEXT NOT NULL, apellido_materno TEXT, discapacidad TEXT, id_motivo INTEGER, FOREIGN KEY (id_motivo) REFERENCES Motivo(id_motivo));
            CREATE TABLE IF NOT EXISTS Area (id_area INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, tipo_de_area TEXT);
            CREATE TABLE IF NOT EXISTS Lactantes (id_lactantes INTEGER PRIMARY KEY AUTOINCREMENT, id_madres INTEGER, id_area INTEGER, apellido_paterno TEXT NOT NULL, apellido_materno TEXT, fecha_nacimiento DATE, genero TEXT, estado TEXT, discapacidad TEXT, peso REAL, FOREIGN KEY (id_madres) REFERENCES Madres(id_madre), FOREIGN KEY (id_area) REFERENCES Area(id_area));
            CREATE TABLE IF NOT EXISTS Citas (id_citas INTEGER PRIMARY KEY AUTOINCREMENT, id_lactantes INTEGER, id_motivo INTEGER, atendido_por_id_usuario INTEGER, fecha_cita TEXT NOT NULL, subsecuente INTEGER, justificacion TEXT, hora_de_entrada TEXT, FOREIGN KEY (id_lactantes) REFERENCES Lactantes(id_lactantes) ON DELETE CASCADE, FOREIGN KEY (id_motivo) REFERENCES Motivo(id_motivo), FOREIGN KEY (atendido_por_id_usuario) REFERENCES Usuarios(id_usuario));
            CREATE TABLE IF NOT EXISTS Controles (id_controles INTEGER PRIMARY KEY AUTOINCREMENT, id_lactantes INTEGER, peso REAL, talla REAL, edad_meses INTEGER, estado_general TEXT, fecha_control TIMESTAMP DEFAULT CURRENT_TIMESTAMP, observaciones TEXT, FOREIGN KEY (id_lactantes) REFERENCES Lactantes(id_lactantes) ON DELETE CASCADE);
        """
        cursor.executescript(create_tables_sql)
        conn.commit()
        
        # --- Inserción robusta de datos iniciales ---
        cursor.execute("SELECT COUNT(id_rol) FROM Rol")
        if cursor.fetchone()[0] == 0:
            print("Insertando datos iniciales...")
            contrasena_admin_hash = hashlib.sha256("12345".encode('utf-8')).hexdigest()
            contrasena_enfermera_hash = hashlib.sha256("pass123".encode('utf-8')).hexdigest()
            
            initial_data = [
                "INSERT INTO Rol (nombre, permiso) VALUES ('Administrador', 'all'), ('Enfermera', 'read_write_patients');",
                "INSERT INTO Motivo (nombre, tipo_de_motivo) VALUES ('Chequeo de rutina', 'Control'), ('Donación de leche', 'Lactancia Materna'), ('Lactancia Materna', 'Apoyo');",
                "INSERT INTO Area (nombre, tipo_de_area) VALUES ('UCIN', 'Médica'), ('UTIN', 'Médica'), ('Crecimiento y desarrollo', 'Médica'), ('Foraneos', 'No Médica');",
                "INSERT INTO Madres (nombre, apellido_paterno, id_motivo) VALUES ('Desconocida', 'Desconocido', 1);",
                f"INSERT INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES ('Admin', '555-0000', '{contrasena_admin_hash}', (SELECT id_rol FROM Rol WHERE nombre = 'Administrador'));",
                f"INSERT INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES ('María López', '555-1234', '{contrasena_enfermera_hash}', (SELECT id_rol FROM Rol WHERE nombre = 'Enfermera'));",
                f"INSERT INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES ('Ana Pérez', '555-5678', '{contrasena_enfermera_hash}', (SELECT id_rol FROM Rol WHERE nombre = 'Enfermera'));"
            ]
            
            for statement in initial_data:
                cursor.execute(statement)
            conn.commit()
            print("Datos iniciales insertados.")

    except sqlite3.Error as e:
        print(f"Error de base de datos durante la configuración: {e}")
        raise
    finally:
        if conn:
            conn.close()

def log_auditoria(accion, tabla_afectada):
    try:
        conn = web.ctx._db
        id_usuario = web.ctx.session.get('user_id')
        if id_usuario:
            conn.execute("INSERT INTO Auditoria (id_usuario, accion, tabla_afectada) VALUES (?, ?, ?)",
                         (id_usuario, accion, tabla_afectada))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error al registrar en auditoría: {e}")

def rol_requerido(*roles_permitidos):
    def decorator(func):
        def wrapper(*args, **kwargs):
            rol_usuario = web.ctx.session.get('rol_nombre')
            if rol_usuario in roles_permitidos:
                return func(*args, **kwargs)
            
            if not web.ctx.session.get('loggedin'):
                raise web.seeother('/login')
            elif rol_usuario == 'Administrador':
                raise web.seeother('/administrador')
            else:
                raise web.seeother('/enfermeras')
        return wrapper
    return decorator

# --- Clases del Manejador de Solicitudes (GET y POST) ---
class Welcome:
    def GET(self):
        return render.index()

class Login:
    def GET(self):
        return render.inicio_sesion(message="")
    
    def POST(self):
        data = web.input()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return render.inicio_sesion(message="Usuario y contraseña son requeridos.")
        
        conn = web.ctx._db
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        query = "SELECT u.id_usuario, r.nombre as rol_nombre, u.contraseña FROM Usuarios u JOIN Rol r ON u.id_rol = r.id_rol WHERE u.nombre = ?;"
        user = conn.execute(query, (username,)).fetchone()
        
        if user and password_hash == user['contraseña']:
            web.ctx.session.loggedin = True
            web.ctx.session.rol_nombre = user['rol_nombre']
            web.ctx.session.user_id = user['id_usuario']
            
            if user['rol_nombre'] == 'Administrador':
                raise web.seeother('/administrador')
            else:
                raise web.seeother('/enfermeras')
        else:
            return render.inicio_sesion(message="Credenciales incorrectas.")

class Logout:
    def GET(self):
        web.ctx.session.kill()
        raise web.seeother('/login')

class AdminArea:
    @rol_requerido('Administrador')
    def GET(self):
        return render.administrador_area()

class RegistroUsuario:
    @rol_requerido('Administrador')
    def GET(self):
        roles = get_db().execute("SELECT id_rol, nombre FROM Rol").fetchall()
        return render.administrador_registrar_usuario(roles=roles, message="")

    @rol_requerido('Administrador')
    def POST(self):
        data = web.input(nombre=None, num_telefono=None, contrasena=None, id_rol=None)
        conn = get_db()
        roles = conn.execute("SELECT id_rol, nombre FROM Rol").fetchall()
        if not all([data.nombre, data.num_telefono, data.contrasena, data.id_rol]):
            return render.administrador_registrar_usuario(roles=roles, message="Todos los campos son obligatorios.")
        try:
            password_hash = hashlib.sha256(data.contrasena.encode('utf-8')).hexdigest()
            conn.execute("INSERT INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES (?, ?, ?, ?)",
                         (data.nombre, data.num_telefono, password_hash, data.id_rol))
            conn.commit()
            log_auditoria("Registro de nuevo usuario", "Usuarios")
            raise web.seeother('/visualizacion_usuarios')
        except sqlite3.IntegrityError:
            return render.administrador_registrar_usuario(roles=roles, message="El número de teléfono ya está registrado.")
        except sqlite3.Error as e:
            return render.administrador_registrar_usuario(roles=roles, message=f"Error inesperado: {e}")

class EnfermerasArea:
    @rol_requerido('Enfermera')
    def GET(self):
        return render.enfermeras_area()

# --- FIX: Lógica mejorada para el registro de lactantes y madres ---
class RegistroLactantes:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        areas = get_db().execute("SELECT id_area, nombre FROM Area").fetchall()
        return_url = '/administrador' if web.ctx.session.get('rol_nombre') == 'Administrador' else '/enfermeras'
        return render.registro_lactantes(return_url=return_url, error_message="", areas=areas)
    
    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        data = web.input()
        conn = get_db()
        try:
            # 1. Obtener datos del lactante
            paterno_lactante = data.get('apellido_paterno_lactante', '').strip()
            fecha_nac = data.get('fecha_nacimiento_lactante', '').strip()
            genero = data.get('genero_lactante', '').strip()
            area_nombre = data.get('area_lactante', '').strip()
            
            # 2. Validar campos obligatorios del lactante
            if not all([paterno_lactante, fecha_nac, genero, area_nombre]):
                raise ValueError("Los campos de apellido paterno, fecha, género y servicio del lactante son obligatorios.")

            # 3. Validar y obtener el ID del área
            area_id_row = conn.execute("SELECT id_area FROM Area WHERE nombre = ?", (area_nombre,)).fetchone()
            if not area_id_row:
                raise ValueError(f"El área '{area_nombre}' no existe.")
            id_area = area_id_row['id_area']

            # 4. Procesar datos de la madre (buscar o crear)
            nombre_madre = data.get('nombre_madre', '').strip()
            paterno_madre = data.get('apellido_paterno_madre', '').strip()
            
            id_madre = None
            if nombre_madre and paterno_madre:
                # Buscar si la madre ya existe
                madre_existente = conn.execute("SELECT id_madre FROM Madres WHERE nombre = ? AND apellido_paterno = ?", (nombre_madre, paterno_madre)).fetchone()
                if madre_existente:
                    id_madre = madre_existente['id_madre']
                else:
                    # Crear nueva madre si no existe
                    conn.execute("INSERT INTO Madres (nombre, apellido_paterno, apellido_materno, discapacidad, id_motivo) VALUES (?, ?, ?, ?, 1)",
                                 (nombre_madre, paterno_madre, data.get('apellido_materno_madre', ''), data.get('discapacidad_madre', '')))
                    id_madre = conn.lastrowid
                    log_auditoria("Registro de nueva madre", "Madres")
            else:
                # Usar madre 'Desconocida' si no se proporciona información
                id_madre_row = conn.execute("SELECT id_madre FROM Madres WHERE nombre = 'Desconocida'").fetchone()
                id_madre = id_madre_row['id_madre']

            # 5. Insertar el nuevo lactante
            conn.execute("""
                INSERT INTO Lactantes (id_madres, id_area, apellido_paterno, apellido_materno, fecha_nacimiento, genero, estado, discapacidad, peso)  
                VALUES (?, ?, ?, ?, ?, ?, 'Activo', ?, ?);
            """, (id_madre, id_area, paterno_lactante, data.get('apellido_materno_lactante', ''), fecha_nac, genero, data.get('discapacidad_lactante', 'Ninguna'), data.get('peso_lactante')))
            
            conn.commit()
            log_auditoria("Registro de nuevo lactante", "Lactantes")
            raise web.seeother('/visualizacion_lactantes')
        
        except (sqlite3.Error, ValueError) as e:
            conn.rollback()
            areas = conn.execute("SELECT id_area, nombre FROM Area").fetchall()
            return_url = '/administrador' if web.ctx.session.get('rol_nombre') == 'Administrador' else '/enfermeras'
            return render.registro_lactantes(return_url=return_url, error_message=f"Error al registrar: {e}", areas=areas)

# --- FIX: Lógica mejorada para el registro de citas ---
class RegistroCitas:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        # En la página de citas, necesitamos los lactantes para que el usuario pueda seleccionarlos
        lactantes = get_db().execute("SELECT id_lactantes, apellido_paterno, apellido_materno FROM Lactantes ORDER BY apellido_paterno").fetchall()
        return render.registro_citas(message="", lactantes=lactantes)
    
    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        data = web.input()
        conn = get_db()

        try:
            # Obtener datos del formulario
            id_lactante = data.get('id_lactante')
            hora_llegada = data.get('hora_llegada')
            justificacion = data.get('justificacion')
            subsecuente = 1 if data.get('subsecuente_checkbox') == 'on' else 0

            # Validar campos obligatorios
            if not all([id_lactante, hora_llegada, justificacion]):
                raise ValueError("Los campos de lactante, hora de llegada y justificación son obligatorios.")

            # Agendar la cita
            atendido_por_id_usuario = web.ctx.session.get('user_id')
            fecha_actual = datetime.date.today().isoformat()
            
            # Usamos un motivo por defecto ("Chequeo de rutina", ID 1)
            id_motivo_defecto = 1

            conn.execute("""
                INSERT INTO Citas (id_lactantes, id_motivo, atendido_por_id_usuario, fecha_cita, subsecuente, justificacion, hora_de_entrada)  
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (id_lactante, id_motivo_defecto, atendido_por_id_usuario, fecha_actual, subsecuente, justificacion, hora_llegada))
            
            conn.commit()
            log_auditoria(f"Registro de nueva cita para lactante ID {id_lactante}", "Citas")
            
            raise web.seeother('/visualizacion_citas')

        except (ValueError, sqlite3.Error) as e:
            conn.rollback()
            print(f"Error al registrar cita: {e}")
            lactantes = conn.execute("SELECT id_lactantes, apellido_paterno, apellido_materno FROM Lactantes ORDER BY apellido_paterno").fetchall()
            return render.registro_citas(message=f"Error al registrar la cita: {e}", lactantes=lactantes)

# --- Clases de visualización (Sin cambios relevantes) ---
class VisualizacionLactantes:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = get_db()
        areas = conn.execute("SELECT id_area, nombre FROM Area").fetchall()
        lactantes = conn.execute("""
            SELECT l.*, m.nombre AS nombre_madre, a.nombre AS area_nombre
            FROM Lactantes l
            LEFT JOIN Madres m ON l.id_madres = m.id_madre
            LEFT JOIN Area a ON l.id_area = a.id_area
            ORDER BY l.apellido_paterno;
        """).fetchall()
        return render.visualizacion_lactantes(lactantes=lactantes, areas=areas)

    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        data = web.input()
        conn = get_db()
        try:
            area_row = conn.execute("SELECT id_area FROM Area WHERE nombre = ?", (data.area_nombre,)).fetchone()
            if not area_row:
                raise ValueError(f"El área '{data.area_nombre}' no es válida.")
            
            conn.execute("""
                UPDATE Lactantes SET
                    apellido_paterno = ?, apellido_materno = ?, fecha_nacimiento = ?,
                    genero = ?, discapacidad = ?, peso = ?, id_area = ?
                WHERE id_lactantes = ?
            """, (data.apellido_paterno, data.apellido_materno, data.fecha_nacimiento, data.genero, data.discapacidad, data.peso, area_row['id_area'], data.id_lactantes))
            conn.commit()
            log_auditoria(f"Actualización lactante ID {data.id_lactantes}", "Lactantes")
        except (sqlite3.Error, ValueError) as e:
            conn.rollback()
            print(f"Error al actualizar lactante: {e}")
        raise web.seeother('/visualizacion_lactantes')

class EliminarLactante:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self, id_lactante):
        conn = get_db()
        try:
            conn.execute("DELETE FROM Lactantes WHERE id_lactantes = ?", (id_lactante,))
            conn.commit()
            log_auditoria(f"Eliminación lactante ID {id_lactante}", "Lactantes")
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error al eliminar lactante: {e}")
        raise web.seeother('/visualizacion_lactantes')

class VisualizacionCitas:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        citas = get_db().execute("""
            SELECT c.id_citas, c.fecha_cita, c.hora_de_entrada, l.apellido_paterno AS lactante_apellido,
                   m.nombre AS motivo_nombre, u.nombre AS atendido_por
            FROM Citas c
            JOIN Lactantes l ON c.id_lactantes = l.id_lactantes
            JOIN Motivo m ON c.id_motivo = m.id_motivo
            JOIN Usuarios u ON c.atendido_por_id_usuario = u.id_usuario
            ORDER BY c.fecha_cita DESC;
        """).fetchall()
        return render.visualizacion_citas(citas=citas)

class VisualizacionUsuarios:
    @rol_requerido('Administrador')
    def GET(self):
        usuarios = get_db().execute("""
            SELECT u.id_usuario, u.nombre, u.num_telefono, r.nombre AS rol_nombre
            FROM Usuarios u JOIN Rol r ON u.id_rol = r.id_rol ORDER BY r.nombre;
        """).fetchall()
        return render.visualizacion_usuarios(usuarios=usuarios)

# --- Clases de Reportes y API ---
class ReportesArea:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        return render.reportes()
class ReportesGenerales:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = get_db()
        reports = conn.execute("SELECT tipo, fecha_generado FROM Reportes ORDER BY fecha_generado DESC").fetchall()
        return render.reportes_generales(reports=reports)

class ReportesPorLactante:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = get_db()
        lactantes = conn.execute("SELECT id_lactantes, apellido_paterno FROM Lactantes ORDER BY apellido_paterno").fetchall()
        return render.reportes_por_lactante(lactantes=lactantes, reporte_data=None)

    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        conn = get_db()
        data = web.input()
        
        id_lactante = data.get('id_lactante')
        
        reporte = None
        if id_lactante:
            query = """
                SELECT  
                    T1.id_citas, T2.nombre AS nombre_madre, T3.apellido_paterno AS lactante_apellido, T4.nombre AS motivo, T1.fecha_cita
                FROM Citas AS T1
                JOIN Lactantes AS T3 ON T1.id_lactantes = T3.id_lactantes
                JOIN Motivo AS T4 ON T1.id_motivo = T4.id_motivo
                LEFT JOIN Madres AS T2 ON T3.id_madres = T2.id_madre
                WHERE T1.id_lactantes = ?
                ORDER BY T1.fecha_cita DESC;
            """
            reporte_data = conn.execute(query, (id_lactante,)).fetchall()
            reporte = [dict(row) for row in reporte_data]
            
        lactantes = conn.execute("SELECT id_lactantes, apellido_paterno FROM Lactantes ORDER BY apellido_paterno").fetchall()
        return render.reportes_por_lactante(lactantes=lactantes, reporte_data=reporte)

class ReportesAPI:
    def POST(self):
        try:
            data = json.loads(web.data())
            report_type = data.get('reportType')
            
            conn = get_db()
            report_data = {}

            if report_type == "estadistica":
                query_madres = "SELECT COUNT(*) AS total_madres FROM Madres;"
                query_lactantes = "SELECT COUNT(*) AS total_lactantes FROM Lactantes;"
                
                total_madres = conn.execute(query_madres).fetchone()['total_madres']
                total_lactantes = conn.execute(query_lactantes).fetchone()['total_lactantes']

                report_data = {
                    "reporte": "Reporte de Estadísticas",
                    "resultados": { "total_madres": total_madres, "total_lactantes": total_lactantes }
                }
            
            elif report_type == "alojamiento_conjunto":
                query = "SELECT T1.nombre AS nombre_madre, T1.apellido_paterno AS apellido_paterno_madre, T2.apellido_paterno AS apellido_paterno_lactante, T2.apellido_materno AS apellido_materno_lactante, T2.fecha_nacimiento FROM Madres AS T1 JOIN Lactantes AS T2 ON T1.id_madre = T2.id_madre;"
                alojamiento_data = conn.execute(query).fetchall()
                report_data = {
                    "reporte": "Reporte de Alojamiento Conjunto",
                    "resultados": [dict(row) for row in alojamiento_data]
                }

            elif report_type == "federal":
                query_genero = "SELECT genero, COUNT(genero) AS total FROM Lactantes GROUP BY genero;"
                query_citas = "SELECT COUNT(*) AS total_citas FROM Citas;"

                genero_data = conn.execute(query_genero).fetchall()
                total_citas = conn.execute(query_citas).fetchone()['total_citas']

                report_data = {
                    "reporte": "Reporte Federal",
                    "resultados": {
                        "total_citas": total_citas,
                        "distribucion_genero": [dict(row) for row in genero_data]
                    }
                }
            
            else:
                web.ctx.status = '400 Bad Request'
                return json.dumps({"error": "Tipo de reporte no válido."})

            id_usuario = web.ctx.session.get('user_id')
            contenido_json = json.dumps(report_data['resultados'])
            
            if id_usuario:
                conn.execute(
                    "INSERT INTO Reportes (id_usuario, tipo, contenido) VALUES (?, ?, ?)",
                    (id_usuario, report_data['reporte'], contenido_json)
                )
                conn.commit()
                log_auditoria(f"Generación de reporte: {report_data['reporte']}", "Reportes")

            web.header('Content-Type', 'application/json')
            return json.dumps(report_data)

        except Exception as e:
            web.header('Content-Type', 'application/json')
            web.ctx.status = '400 Bad Request'
            print(f"Error en ReportesAPI: {e}")
            return json.dumps({"error": "Ocurrió un error al generar el reporte."})

# --- Lógica de inicio del servidor ---
app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'loggedin': False, 'rol_nombre': None})

def session_processor(handler):
    web.ctx.session = session
    return handler()

app.add_processor(session_processor)

def db_processor(handler):
    web.ctx._db = get_db()
    try:
        return handler()
    finally:
        if hasattr(web.ctx, '_db'):
            web.ctx._db.close()

app.add_processor(db_processor)

application = app.wsgifunc()

if __name__ == "__main__":
    setup_database()
    app.run()
