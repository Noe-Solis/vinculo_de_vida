-- Tabla Rol
CREATE TABLE IF NOT EXISTS Rol (
id_rol INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT NOT NULL UNIQUE,
permiso TEXT
);

 -- Tabla Usuarios
 CREATE TABLE IF NOT EXISTS Usuarios (
id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT NOT NULL,
num_telefono TEXT UNIQUE,
contraseña TEXT NOT NULL,
id_rol INTEGER,
FOREIGN KEY (id_rol) REFERENCES Rol(id_rol)
);

-- Tabla Auditoria
CREATE TABLE IF NOT EXISTS Auditoria (
id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT,
id_usuario INTEGER,
accion TEXT NOT NULL,
tabla_afectada TEXT NOT NULL,
fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
);

-- Tabla Reportes
CREATE TABLE IF NOT EXISTS Reportes (
id_reportes INTEGER PRIMARY KEY AUTOINCREMENT,
id_usuario INTEGER,
tipo TEXT NOT NULL,
fecha_generado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
contenido TEXT,
FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)
);

-- Tabla Motiv
CREATE TABLE IF NOT EXISTS Motivo (
id_motivo INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT NOT NULL UNIQUE,
tipo_de_motivo TEXT
);

-- Tabla Madres
CREATE TABLE IF NOT EXISTS Madres (
id_madre INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT NOT NULL,
apellido_paterno TEXT NOT NULL,
apellido_materno TEXT,
discapacidad TEXT, 
id_motivo INTEGER,
FOREIGN KEY (id_motivo) REFERENCES Motivo(id_motivo)
);

-- Tabla Area
CREATE TABLE IF NOT EXISTS Area (
id_area INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT NOT NULL UNIQUE,
tipo_de_area TEXT
);

-- Tabla Lactantes
CREATE TABLE IF NOT EXISTS Lactantes (
    id_lactantes INTEGER PRIMARY KEY AUTOINCREMENT,
    id_madres INTEGER,
    id_area INTEGER,
    primer_apellido TEXT NOT NULL,
    segundo_apellido TEXT,
    fecha_nacimiento DATE, 
    genero TEXT,
    estado TEXT,
    peso DECIMAL,
    discapacidad TEXT, 
    FOREIGN KEY (id_madres) REFERENCES Madres(id_madre),
    FOREIGN KEY (id_area) REFERENCES Area(id_area)
);

-- Tabla Citas
CREATE TABLE IF NOT EXISTS Citas (
id_citas INTEGER PRIMARY KEY AUTOINCREMENT,
id_lactantes INTEGER,
id_motivo INTEGER,
atendido_por_id_usuario INTEGER,
fecha_cita TEXT NOT NULL, -- Considerar usar DATE o TIMESTAMP
subsecuente INTEGER, -- 0 para false, 1 para true
justificacion TEXT,
hora_de_entrada TEXT, -- Considerar usar TIME o TIMESTAMP
FOREIGN KEY (id_lactantes) REFERENCES Lactantes(id_lactantes),
FOREIGN KEY (id_motivo) REFERENCES Motivo(id_motivo),
FOREIGN KEY (atendido_por_id_usuario) REFERENCES Usuarios(id_usuario)
);

-- Tabla Controles
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

-- Inserta roles iniciales si no existen
INSERT OR IGNORE INTO Rol (nombre, permiso) VALUES ('Administrador', 'all');
INSERT OR IGNORE INTO Rol (nombre, permiso) VALUES ('Enfermera', 'read_write_patients');

SELECT c.id_citas, c.id_lactantes, l.apellido_paterno AS lactante_apellido, c.fecha_cita, c.hora_de_entrada, c.id_motivo, c.subsecuente, c.justificacion, c.atendido_por_id_usuario, u.nombre AS nombre_encargado FROM Citas c JOIN Lactantes l ON c.id_lactantes = l.id_lactantes LEFT JOIN Usuarios u ON c.atendido_por
_id_usuario = u.id_usuario WHERE c.id_citas = 1;