# app.py
# Este archivo contiene la lógica del servidor para la aplicación.
# Confirma que tienes instalado web.py: pip install web.py

import web
import os
import json
import sqlite3
import hashlib
import datetime

# --- 1. Configuración de la base de datos SQLite3 ---
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
            "INSERT OR IGNORE INTO Area (nombre, tipo_de_area) VALUES ('Enfermería 1', 'Médica');",
            "INSERT OR IGNORE INTO Area (nombre, tipo_de_area) VALUES ('Pediatría', 'Médica');",
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
                (SELECT id_area FROM Area WHERE nombre = 'Enfermería 1'),
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

web.config.debug = False
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
render = web.template.render(template_dir)

# 2. Definición de URLs y Mapeo de Clases 
urls = (
    '/', 'Welcome',
    '/login', 'Login',
    '/logout', 'Logout',
    '/administrador', 'AdministradorArea',
    '/administrador_registrar_usuario', 'AdministradorRegistrarUsuario',
    '/visualizacion_usuarios', 'AdministradorVerUsuarios',
    '/visualizacion_citas', 'AdministradorVerCitas',
    '/visualizacion_lactantes', 'AdministradorVerLactantes',
    '/enfermeras', 'EnfermerasArea',
    '/registro_lactantes', 'RegistroLactantes',
    '/registro_citas', 'RegistroCitas',
    '/reportes', 'ReportesArea',
    '/reportes_generales', 'ReportesGenerales',
    '/reportes_por_lactante', 'ReportesPorLactante',
    '/api/generate_report', 'ReportesAPI',
)

# Decorador para requerir un rol específico 
def rol_requerido(*roles_permitidos):
    def decorator(func):
        def wrapper(*args, **kwargs):
            rol_usuario = web.ctx.session.get('rol_id')
            if rol_usuario in roles_permitidos:
                return func(*args, **kwargs)
            else:
                raise web.seeother('/login')
        return wrapper
    return decorator

# Clases del Manejador de Solicitudes (Lógica de la Aplicación) 
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

        query = "SELECT id_usuario, id_rol, contraseña FROM Usuarios WHERE nombre = ?;"
        user = cursor.execute(query, (username,)).fetchone()
        
        if user:
            if password_hash == user['contraseña']:
                web.ctx.session.loggedin = True
                web.ctx.session.rol_id = user['id_rol']
                
                if user['id_rol'] == 1:
                    raise web.seeother('/administrador')
                elif user['id_rol'] == 2:
                    raise web.seeother('/enfermeras')
            else:
                return render.inicio_sesion(message="Nombre de usuario o contraseña incorrectos.")
        else:
            return render.inicio_sesion(message="Nombre de usuario o contraseña incorrectos.")

class Logout:
    def GET(self):
        web.ctx.session.kill()
        raise web.seeother('/login')

class AdministradorArea:
    @rol_requerido(1)
    def GET(self):
        return render.administrador_area()

class AdministradorRegistrarUsuario:
    @rol_requerido(1)
    def GET(self):
        return render.administrador_registrar_usuario()

class AdministradorVerUsuarios:
    @rol_requerido(1)
    def GET(self):
        print("INFO: Se intentó acceder a la vista de visualización de usuarios.")
        conn = web.ctx._db
        cursor = conn.cursor()
        
        # Realizamos una consulta JOIN para obtener el nombre del rol.
        query = """
        SELECT
            T1.id_usuario,
            T1.nombre,
            T1.num_telefono,
            T2.nombre AS rol
        FROM
            Usuarios AS T1
        JOIN
            Rol AS T2 ON T1.id_rol = T2.id_rol;
        """
        usuarios_data = cursor.execute(query).fetchall()

        # Comprobación de depuración para ver si el archivo de plantilla existe.
        template_path = os.path.join(template_dir, 'visualizacion_usuarios.html')
        print(f"INFO: Intentando renderizar la plantilla: {template_path}")
        if not os.path.exists(template_path):
            print(f"ERROR: La plantilla no se encuentra en la ruta: {template_path}")
            return "Error interno: La plantilla 'visualizacion_usuarios.html' no se encontró."

        # Renderizamos la plantilla HTML y le pasamos los datos.
        return render.visualizacion_usuarios(usuarios=usuarios_data)

class AdministradorVerCitas:
    @rol_requerido(1, 2)
    def GET(self):
        conn = web.ctx._db
        cursor = conn.cursor()
        query = """
        SELECT
            T1.fecha_cita,
            T1.hora_de_entrada,
            T1.subsecuente,
            T2.apellido_paterno AS apellido_paterno_lactante,
            T2.apellido_materno AS apellido_materno_lactante,
            T3.nombre AS nombre_madre,
            T3.apellido_paterno AS apellido_paterno_madre,
            T4.nombre AS motivo
        FROM
            Citas AS T1
        JOIN
            Lactantes AS T2 ON T1.id_lactantes = T2.id_lactantes
        JOIN
            Madres AS T3 ON T2.id_madres = T3.id_madre
        JOIN
            Motivo AS T4 ON T1.id_motivo = T4.id_motivo;
        """
        citas_data = cursor.execute(query).fetchall()
        return render.visualizacion_citas(citas=citas_data)

class AdministradorVerLactantes:
    @rol_requerido(1, 2)
    def GET(self):
        conn = web.ctx._db
        cursor = conn.cursor()
        query = """
        SELECT
            T1.id_lactantes,
            T1.apellido_paterno AS primer_apellido,
            T1.apellido_materno AS segundo_apellido,
            T1.fecha_nacimiento,
            T1.genero,
            T1.estado,
            T1.discapacidad,
            T2.nombre AS nombre_madre,
            T2.apellido_paterno AS apellido_madre
        FROM
            Lactantes AS T1
        JOIN
            Madres AS T2 ON T1.id_madres = T2.id_madre;
        """
        raw_data = cursor.execute(query).fetchall()
        # Convertir los objetos sqlite3.Row a diccionarios para que la plantilla los maneje correctamente
        lactantes_data = [dict(row) for row in raw_data]
        return render.visualizacion_lactantes(lactantes=lactantes_data)

class EnfermerasArea:
    @rol_requerido(1, 2)
    def GET(self):
        return render.enfermeras_area()

class RegistroLactantes:
    @rol_requerido(1, 2)
    def GET(self):
        return render.registro_lactantes()

class RegistroCitas:
    @rol_requerido(1, 2)
    def GET(self):
        return render.registro_citas()

class ReportesArea:
    @rol_requerido(1, 2)
    def GET(self):
        return render.reportes()

class ReportesGenerales:
    @rol_requerido(1, 2)
    def GET(self):
        return render.reportes_generales()

class ReportesPorLactante:
    @rol_requerido(1, 2)
    def GET(self):
        return render.reportes_por_lactante()

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


if __name__ == "__main__":
    setup_database()
    app = web.application(urls, globals())
    session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'loggedin': False, 'rol_id': None})
    
    def db_processor(handler):
        web.ctx._db = get_db()
        try:
            return handler()
        finally:
            if hasattr(web.ctx, '_db'):
                web.ctx._db.close()
    
    def session_processor(handler):
        web.ctx.session = session
        return handler()

    app.add_processor(db_processor)
    app.add_processor(session_processor)
    print("Servidor web.py iniciado. Accede a http://localhost:8080/visualizacion_usuarios")
    app.run()
else:
    setup_database()
    app = web.application(urls, globals())
    session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'loggedin': False, 'rol_id': None})
    
    def db_processor(handler):
        web.ctx._db = get_db()
        try:
            return handler()
        finally:
            if hasattr(web.ctx, '_db'):
                web.ctx._db.close()

    def session_processor(handler):
        web.ctx.session = session
        return handler()

    app.add_processor(db_processor)
    app.add_processor(session_processor)
    application = app.wsgifunc()