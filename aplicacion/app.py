# app.py
# Este archivo contiene la lógica del servidor para la aplicación.
# Confirma que tienes instalado web.py: pip install web.py

import web
import os
import json
import sqlite3
import hashlib
import datetime

web.config.debug = False
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
render = web.template.render(template_dir)

# --- 1. Definición de URLs y Mapeo de Clases ---
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
)

# --- 2. Configuración de la base de datos SQLite3 ---
DB_FILE = 'vinculo_de_vida.db'

def get_db():
    """Establece y devuelve una conexión a la base de datos."""
    db = getattr(web.ctx, '_db', None)
    if db is None:
        db = web.ctx._db = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row
    return db

def setup_database():
    """
    Crea las tablas y inserta los datos iniciales si la base de datos no existe.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        create_tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS Rol (
                id_rol INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                permiso TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Usuarios (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                num_telefono TEXT UNIQUE,
                contraseña TEXT NOT NULL,
                id_rol INTEGER,
                FOREIGN KEY (id_rol) REFERENCES Rol(id_rol)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Auditoria (
                id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT,
                id_usuario INTEGER,
                accion TEXT NOT NULL,
                tabla_afectada TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Reportes (
                id_reportes INTEGER PRIMARY KEY AUTOINCREMENT,
                id_usuario INTEGER,
                tipo TEXT NOT NULL,
                fecha_generado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                contenido TEXT,
                FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Motivo (
                id_motivo INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                tipo_de_motivo TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Madres (
                id_madre INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellido_paterno TEXT NOT NULL,
                apellido_materno TEXT,
                discapacidad TEXT, 
                id_motivo INTEGER,
                FOREIGN KEY (id_motivo) REFERENCES Motivo(id_motivo)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Area (
                id_area INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                tipo_de_area TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Lactantes (
                id_lactantes INTEGER PRIMARY KEY AUTOINCREMENT,
                id_madres INTEGER,
                id_area INTEGER,
                apellido_paterno TEXT NOT NULL,
                apellido_materno TEXT,
                fecha_nacimiento DATE, 
                genero TEXT,
                estado TEXT,
                discapacidad TEXT, 
                FOREIGN KEY (id_madres) REFERENCES Madres(id_madre),
                FOREIGN KEY (id_area) REFERENCES Area(id_area)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Citas (
                id_citas INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lactantes INTEGER,
                id_motivo INTEGER,
                atendido_por_id_usuario INTEGER,
                fecha_cita TEXT NOT NULL,
                subsecuente INTEGER,
                justificacion TEXT,
                hora_de_entrada TEXT,
                FOREIGN KEY (id_lactantes) REFERENCES Lactantes(id_lactantes),
                FOREIGN KEY (id_motivo) REFERENCES Motivo(id_motivo),
                FOREIGN KEY (atendido_por_id_usuario) REFERENCES Usuarios(id_usuario)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Controles (
                id_controles INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lactantes INTEGER,
                peso REAL,
                talla REAL,
                edad_meses INTEGER,
                estado_general TEXT,
                fecha_control TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                observaciones TEXT,
                FOREIGN KEY (id_lactantes) REFERENCES Lactantes(id_lactantes)
            );
            """
        ]

        contrasena_admin_hash = hashlib.sha256("12345".encode('utf-8')).hexdigest()
        contrasena_enfermera_hash = hashlib.sha256("pass123".encode('utf-8')).hexdigest()

        initial_data_sql = [
            "INSERT OR IGNORE INTO Rol (nombre, permiso) VALUES ('Administrador', 'all');",
            "INSERT OR IGNORE INTO Rol (nombre, permiso) VALUES ('Enfermera', 'read_write_patients');",
            "INSERT OR IGNORE INTO Motivo (nombre, tipo_de_motivo) VALUES ('Chequeo de rutina', 'Control');",
            "INSERT OR IGNORE INTO Motivo (nombre, tipo_de_motivo) VALUES ('Donación de leche', 'Lactancia Materna');",
            "INSERT OR IGNORE INTO Motivo (nombre, tipo_de_motivo) VALUES ('Lactancia Materna', 'Apoyo');",
            "INSERT OR IGNORE INTO Area (nombre, tipo_de_area) VALUES ('UCIN', 'Médica');",
            "INSERT OR IGNORE INTO Area (nombre, tipo_de_area) VALUES ('UTIN', 'Médica');",
            "INSERT OR IGNORE INTO Area (nombre, tipo_de_area) VALUES ('Crecimiento y desarrollo', 'Médica');",
            "INSERT OR IGNORE INTO Area (nombre, tipo_de_area) VALUES ('Foraneos', 'No Médica');",
            "INSERT OR IGNORE INTO Madres (nombre, apellido_paterno, apellido_materno, discapacidad, id_motivo) VALUES ('Desconocida', 'Desconocido', 'Desconocido', 'Ninguna', 1);",
            f"""
            INSERT OR IGNORE INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES (
                'Admin', '555-0000', '{contrasena_admin_hash}', (SELECT id_rol FROM Rol WHERE nombre = 'Administrador')
            );
            """,
            f"""
            INSERT OR IGNORE INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES (
                'María López', '555-1234', '{contrasena_enfermera_hash}', (SELECT id_rol FROM Rol WHERE nombre = 'Enfermera')
            );
            """,
            f"""
            INSERT OR IGNORE INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES (
                'Ana Pérez', '555-5678', '{contrasena_enfermera_hash}', (SELECT id_rol FROM Rol WHERE nombre = 'Enfermera')
            );
            """,
            """
            INSERT OR IGNORE INTO Madres (nombre, apellido_paterno, apellido_materno, discapacidad, id_motivo) VALUES (
                'Juana', 'Pérez', 'Gómez', 'Ninguna', (SELECT id_motivo FROM Motivo WHERE nombre = 'Chequeo de rutina')
            );
            """,
            """
            INSERT OR IGNORE INTO Lactantes (id_madres, id_area, apellido_paterno, apellido_materno, fecha_nacimiento, genero, estado, discapacidad) VALUES (
                (SELECT id_madre FROM Madres WHERE nombre = 'Juana'), 
                (SELECT id_area FROM Area WHERE nombre = 'UCIN'),
                'Pérez',
                'Gómez',
                '2024-01-15', 
                'Masculino', 
                'Activo',
                'Ninguna'
            );
            """,
            """
            INSERT OR IGNORE INTO Citas (id_lactantes, id_motivo, atendido_por_id_usuario, fecha_cita, subsecuente, justificacion, hora_de_entrada) VALUES (
                (SELECT id_lactantes FROM Lactantes WHERE apellido_paterno = 'Pérez'), 
                (SELECT id_motivo FROM Motivo WHERE nombre = 'Chequeo de rutina'), 
                (SELECT id_usuario FROM Usuarios WHERE nombre = 'María López'),
                '2025-08-10',
                0,
                'Control de peso y talla',
                '09:30'
            );
            """
        ]

        print("Creando tablas...")
        for table_sql in create_tables_sql:
            cursor.execute(table_sql)
        print("Tablas creadas con éxito.")

        print("Insertando datos de ejemplo...")
        for insert_sql in initial_data_sql:
            cursor.execute(insert_sql)
        
        conn.commit()
        print("Datos de ejemplo insertados con éxito.")

    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}")
    finally:
        if conn:
            conn.close()
            print("Conexión de configuración cerrada.")

# --- 3. Decorador para requerir un rol específico (refactorizado para usar nombres) ---
def rol_requerido(*roles_permitidos):
    def decorator(func):
        def wrapper(*args, **kwargs):
            rol_usuario = web.ctx.session.get('rol_nombre')
            if rol_usuario in roles_permitidos:
                return func(*args, **kwargs)
            else:
                # Si no está logeado, redirigir al login
                if not web.ctx.session.get('loggedin'):
                    raise web.seeother('/login')
                # Si está logeado pero no tiene el rol, redirigir al área apropiada
                elif rol_usuario == 'Administrador':
                    raise web.seeother('/administrador')
                elif rol_usuario == 'Enfermera':
                    raise web.seeother('/enfermeras')
                else:
                    raise web.seeother('/login')
        return wrapper
    return decorator

# --- 4. Clases del Manejador de Solicitudes (Lógica de la Aplicación) ---
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
            return render.inicio_sesion(message="El nombre de usuario y la contraseña no pueden estar vacíos.")
        
        conn = web.ctx._db
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # Se obtiene el nombre del rol en lugar del ID
        query = """
            SELECT T1.id_usuario, T2.nombre as rol_nombre, T1.contraseña
            FROM Usuarios AS T1
            JOIN Rol AS T2 ON T1.id_rol = T2.id_rol
            WHERE T1.nombre = ?;
        """
        user = cursor.execute(query, (username,)).fetchone()
        
        if user and password_hash == user['contraseña']:
            web.ctx.session.loggedin = True
            web.ctx.session.rol_nombre = user['rol_nombre']
            web.ctx.session.user_id = user['id_usuario']
            
            if user['rol_nombre'] == 'Administrador':
                raise web.seeother('/administrador')
            elif user['rol_nombre'] == 'Enfermera':
                raise web.seeother('/enfermeras')
        else:
            return render.inicio_sesion(message="Nombre de usuario o contraseña incorrectos.")

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
        conn = web.ctx._db
        roles = conn.execute("SELECT id_rol, nombre FROM Rol").fetchall()
        return render.administrador_registrar_usuario(roles=roles, message="")

    @rol_requerido('Administrador')
    def POST(self):
        conn = web.ctx._db
        cursor = conn.cursor()
        data = web.input()
        
        nombre = data.get('nombre')
        num_telefono = data.get('num_telefono')
        contrasena = data.get('contrasena')
        id_rol = data.get('id_rol')
        
        if not all([nombre, num_telefono, contrasena, id_rol]):
            roles = cursor.execute("SELECT id_rol, nombre FROM Rol").fetchall()
            return render.administrador_registrar_usuario(roles=roles, message="Todos los campos son obligatorios.")

        try:
            password_hash = hashlib.sha256(contrasena.encode('utf-8')).hexdigest()
            cursor.execute("INSERT INTO Usuarios (nombre, num_telefono, contraseña, id_rol) VALUES (?, ?, ?, ?)",
                           (nombre, num_telefono, password_hash, id_rol))
            conn.commit()
            raise web.seeother('/visualizacion_usuarios')
        except sqlite3.IntegrityError:
            roles = cursor.execute("SELECT id_rol, nombre FROM Rol").fetchall()
            return render.administrador_registrar_usuario(roles=roles, message="El número de teléfono ya está registrado.")
        except sqlite3.Error as e:
            print(f"Error al registrar usuario: {e}")
            roles = cursor.execute("SELECT id_rol, nombre FROM Rol").fetchall()
            return render.administrador_registrar_usuario(roles=roles, message=f"Error: {e}")

class EnfermerasArea:
    @rol_requerido('Enfermera')
    def GET(self):
        return render.enfermeras_area()

class RegistroCitas:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = web.ctx._db
        lactantes = conn.execute("SELECT id_lactantes, apellido_paterno FROM Lactantes ORDER BY apellido_paterno").fetchall()
        motivos = conn.execute("SELECT id_motivo, nombre FROM Motivo ORDER BY nombre").fetchall()
        return render.registro_citas(lactantes=lactantes, motivos=motivos, message="")

    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        conn = web.ctx._db
        cursor = conn.cursor()
        data = web.input()
        
        id_lactantes = data.get('id_lactantes')
        id_motivo = data.get('id_motivo')
        fecha_cita = data.get('fecha_cita')
        hora_entrada = data.get('hora_de_entrada')
        justificacion = data.get('justificacion')
        subsecuente = 1 if data.get('subsecuente') == 'on' else 0
        
        if not all([id_lactantes, id_motivo, fecha_cita]):
            lactantes = cursor.execute("SELECT id_lactantes, apellido_paterno FROM Lactantes").fetchall()
            motivos = cursor.execute("SELECT id_motivo, nombre FROM Motivo").fetchall()
            return render.registro_citas(lactantes=lactantes, motivos=motivos, message="Los campos de lactante, motivo y fecha son obligatorios.")

        try:
            atendido_por_id_usuario = web.ctx.session.get('user_id')
            cursor.execute("""
                INSERT INTO Citas (id_lactantes, id_motivo, atendido_por_id_usuario, fecha_cita, subsecuente, justificacion, hora_de_entrada) 
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (id_lactantes, id_motivo, atendido_por_id_usuario, fecha_cita, subsecuente, justificacion, hora_entrada))
            conn.commit()
            raise web.seeother('/visualizacion_citas')
        except sqlite3.Error as e:
            conn.rollback()
            lactantes = cursor.execute("SELECT id_lactantes, apellido_paterno FROM Lactantes").fetchall()
            motivos = cursor.execute("SELECT id_motivo, nombre FROM Motivo").fetchall()
            return render.registro_citas(lactantes=lactantes, motivos=motivos, message=f"Error al registrar cita: {e}")

class RegistroLactantes:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = web.ctx._db
        areas = conn.execute("SELECT id_area, nombre FROM Area").fetchall()
        if web.ctx.session.get('rol_nombre') == 'Administrador':
            return render.registro_lactantes(return_url='/administrador', error_message="", areas=areas)
        else:
            return render.registro_lactantes(return_url='/enfermeras', error_message="", areas=areas)
    
    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        data = web.input()
        conn = web.ctx._db
        cursor = conn.cursor()
        
        try:
            # --- Obtener y validar datos del formulario del lactante ---
            apellido_paterno_lactante = data.get('apellido_paterno_lactante', '').strip()
            apellido_materno_lactante = data.get('apellido_materno_lactante', '').strip()
            fecha_nacimiento_str = data.get('fecha_nacimiento_lactante', '').strip()
            genero_lactante = data.get('genero_lactante', '').strip()
            discapacidad_lactante = data.get('discapacidad_lactante', '').strip()
            area_lactante_nombre = data.get('area_lactante', '').strip()
            
            # Validación de campos obligatorios
            if not all([apellido_paterno_lactante, fecha_nacimiento_str, genero_lactante, area_lactante_nombre]):
                error_msg = "Los campos de apellido paterno, fecha, género y servicio del lactante son obligatorios."
                areas = cursor.execute("SELECT id_area, nombre FROM Area").fetchall()
                if web.ctx.session.get('rol_nombre') == 'Administrador':
                    return render.registro_lactantes(return_url='/administrador', error_message=error_msg, areas=areas)
                else:
                    return render.registro_lactantes(return_url='/enfermeras', error_message=error_msg, areas=areas)
            
            # --- Lógica de la madre (buscar o crear) ---
            nombre_madre = data.get('nombre_madre', '').strip()
            apellido_paterno_madre = data.get('apellido_paterno_madre', '').strip()
            
            if nombre_madre and apellido_paterno_madre:
                # Si se proporcionan datos de la madre, se registra una nueva
                cursor.execute("INSERT INTO Madres (nombre, apellido_paterno, apellido_materno, discapacidad, id_motivo) VALUES (?, ?, ?, ?, ?)",
                               (nombre_madre, apellido_paterno_madre, data.get('apellido_materno_madre', ''), data.get('discapacidad_madre', ''), 1))
                id_madre = cursor.lastrowid
            else:
                # Si no se proporcionan datos de la madre, se usa la madre "desconocida"
                id_madre_row = cursor.execute("SELECT id_madre FROM Madres WHERE nombre = 'Desconocida'").fetchone()
                if not id_madre_row:
                    cursor.execute("INSERT INTO Madres (nombre, apellido_paterno, apellido_materno, discapacidad, id_motivo) VALUES ('Desconocida', 'Desconocido', 'Desconocido', 'Ninguna', 1);")
                    id_madre = cursor.lastrowid
                else:
                    id_madre = id_madre_row['id_madre']

            # Buscar el ID del área para el lactante
            area_id_row = cursor.execute("SELECT id_area FROM Area WHERE nombre = ?", (area_lactante_nombre,)).fetchone()
            if not area_id_row:
                error_msg = f"Error: El área '{area_lactante_nombre}' no existe en la base de datos."
                areas = cursor.execute("SELECT id_area, nombre FROM Area").fetchall()
                if web.ctx.session.get('rol_nombre') == 'Administrador':
                    return render.registro_lactantes(return_url='/administrador', error_message=error_msg, areas=areas)
                else:
                    return render.registro_lactantes(return_url='/enfermeras', error_message=error_msg, areas=areas)
            id_area = area_id_row['id_area']

            # Insertar al lactante
            cursor.execute("""
                INSERT INTO Lactantes (id_madres, id_area, apellido_paterno, apellido_materno, fecha_nacimiento, genero, estado, discapacidad) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                id_madre, 
                id_area,
                apellido_paterno_lactante, 
                apellido_materno_lactante if apellido_materno_lactante else "Ninguno",
                fecha_nacimiento_str, 
                genero_lactante, 
                "Activo",
                discapacidad_lactante if discapacidad_lactante else "Ninguna"
            ))
            
            conn.commit()
            raise web.seeother('/visualizacion_lactantes')
        
        except sqlite3.Error as e:
            conn.rollback()
            error_msg = f"Error al registrar: {e}"
            areas = cursor.execute("SELECT id_area, nombre FROM Area").fetchall()
            if web.ctx.session.get('rol_nombre') == 'Administrador':
                return render.registro_lactantes(return_url='/administrador', error_message=error_msg, areas=areas)
            else:
                return render.registro_lactantes(return_url='/enfermeras', error_message=error_msg, areas=areas)

class ReportesArea:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        return render.reportes()

class ReportesGenerales:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        return render.reportes_generales()

    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        data = web.input()
        print("Datos del formulario de reportes generales recibidos:", data)
        # Lógica para generar y procesar el reporte (ejemplo)
        raise web.seeother('/reportes_generales')

class ReportesPorLactante:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = web.ctx._db
        lactantes = conn.execute("SELECT id_lactantes, apellido_paterno FROM Lactantes ORDER BY apellido_paterno").fetchall()
        return render.reportes_por_lactante(lactantes=lactantes, reporte_data=None)

    @rol_requerido('Administrador', 'Enfermera')
    def POST(self):
        conn = web.ctx._db
        cursor = conn.cursor()
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
            reporte_data = cursor.execute(query, (id_lactante,)).fetchall()
            reporte = [dict(row) for row in reporte_data]
            
        lactantes = cursor.execute("SELECT id_lactantes, apellido_paterno FROM Lactantes ORDER BY apellido_paterno").fetchall()
        return render.reportes_por_lactante(lactantes=lactantes, reporte_data=reporte)

class VisualizacionCitas:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = web.ctx._db
        query = """
            SELECT 
                T1.id_citas, 
                T1.fecha_cita, 
                T1.hora_de_entrada,
                T2.apellido_paterno AS lactante_apellido,
                T3.nombre AS motivo_nombre,
                T4.nombre AS atendido_por
            FROM Citas AS T1
            JOIN Lactantes AS T2 ON T1.id_lactantes = T2.id_lactantes
            JOIN Motivo AS T3 ON T1.id_motivo = T3.id_motivo
            JOIN Usuarios AS T4 ON T1.atendido_por_id_usuario = T4.id_usuario
            ORDER BY T1.fecha_cita DESC;
        """
        citas = conn.execute(query).fetchall()
        return render.visualizacion_citas(citas=citas)

class VisualizacionLactantes:
    @rol_requerido('Administrador', 'Enfermera')
    def GET(self):
        conn = web.ctx._db
        query = """
            SELECT 
                T1.id_lactantes, 
                T1.apellido_paterno AS lactante_apellido, 
                T1.apellido_materno AS lactante_materno, 
                T1.fecha_nacimiento, 
                T1.genero,
                T2.nombre AS nombre_madre,
                T3.nombre AS area_nombre
            FROM Lactantes AS T1
            JOIN Madres AS T2 ON T1.id_madres = T2.id_madre
            JOIN Area AS T3 ON T1.id_area = T3.id_area
            ORDER BY T1.apellido_paterno;
        """
        lactantes = conn.execute(query).fetchall()
        return render.visualizacion_lactantes(lactantes=lactantes)

class VisualizacionUsuarios:
    @rol_requerido('Administrador')
    def GET(self):
        conn = web.ctx._db
        query = """
            SELECT 
                T1.id_usuario, 
                T1.nombre, 
                T1.num_telefono,
                T2.nombre AS rol_nombre
            FROM Usuarios AS T1
            JOIN Rol AS T2 ON T1.id_rol = T2.id_rol
            ORDER BY T2.nombre;
        """
        usuarios = conn.execute(query).fetchall()
        return render.visualizacion_usuarios(usuarios=usuarios)

class ReportesAPI:
    def POST(self):
        try:
            data = json.loads(web.data())
            report_type = data.get('reportType')
            
            conn = web.ctx._db
            cursor = conn.cursor()
            report_data = {}

            if report_type == "estadistica":
                query_madres = "SELECT COUNT(*) AS total_madres FROM Madres;"
                query_lactantes = "SELECT COUNT(*) AS total_lactantes FROM Lactantes;"
                
                total_madres = cursor.execute(query_madres).fetchone()['total_madres']
                total_lactantes = cursor.execute(query_lactantes).fetchone()['total_lactantes']

                report_data = {
                    "reporte": "Reporte de Estadísticas",
                    "resultados": {
                        "total_madres": total_madres,
                        "total_lactantes": total_lactantes
                    }
                }
            
            elif report_type == "alojamiento_conjunto":
                query = """
                SELECT
                    T1.nombre AS nombre_madre,
                    T1.apellido_paterno AS apellido_paterno_madre,
                    T2.apellido_paterno AS apellido_paterno_lactante,
                    T2.apellido_materno AS apellido_materno_lactante,
                    T2.fecha_nacimiento
                FROM
                    Madres AS T1
                JOIN
                    Lactantes AS T2 ON T1.id_madre = T2.id_madre;
                """
                alojamiento_data = cursor.execute(query).fetchall()

                report_data = {
                    "reporte": "Reporte de Alojamiento Conjunto",
                    "resultados": [dict(row) for row in alojamiento_data]
                }

            elif report_type == "federal":
                query_genero = "SELECT genero, COUNT(genero) AS total FROM Lactantes GROUP BY genero;"
                query_citas = "SELECT COUNT(*) AS total_citas FROM Citas;"

                genero_data = cursor.execute(query_genero).fetchall()
                total_citas = cursor.execute(query_citas).fetchone()['total_citas']

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

            web.header('Content-Type', 'application/json')
            return json.dumps(report_data)

        except Exception as e:
            web.header('Content-Type', 'application/json')
            web.ctx.status = '400 Bad Request'
            print(f"Error en ReportesAPI: {e}")
            return json.dumps({"error": "Ocurrió un error al generar el reporte."})

# --- 5. Lógica de inicio del servidor ---
if __name__ == "__main__":
    setup_database()
    app = web.application(urls, globals())
    session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'loggedin': False, 'rol_nombre': None})
    
    # Procesador para hacer la sesión accesible en web.ctx
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
    app.run()
else:
    setup_database()
    app = web.application(urls, globals())
    session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'loggedin': False, 'rol_nombre': None})
    
    # Procesador para hacer la sesión accesible en web.ctx
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

