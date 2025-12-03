from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

import io
import matplotlib
matplotlib.use('Agg')  # Para usar matplotlib sin interfaz gráfica
import matplotlib.pyplot as plt
from fpdf import FPDF

app = Flask(__name__)
app.config['SECRET_KEY'] = 'unapec-caja-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///caja_unapec.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

# Roles del sistema
ROLES = {
    'ADMIN': 'Administrador',
    'CAJERO': 'Cajero',
    'CONSULTA': 'Consulta',
    'GERENTE': 'Gerente'
}

# Clase PDF personalizada
class PDFReport(FPDF):
    def header(self):
        # Logo o título
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'SISTEMA DE CAJA UNAPEC', 0, 1, 'C')
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'REPORTE DE MOVIMIENTOS', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        # Pie de página
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()} - Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')
    
    def chapter_title(self, title):
        # Título de capítulo
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)
    
    def chapter_body(self, body):
        # Cuerpo del texto
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 8, body)
        self.ln()

# Modelos de Seguridad
class Rol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    usuarios = db.relationship('Usuario', backref='rol', lazy=True)

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    empleado_id = db.Column(db.Integer, db.ForeignKey('empleado.id'))
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)
    ultimo_acceso = db.Column(db.DateTime)

# Modelos de Negocio (Actualizados)
class TipoDocumento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='tipo_documento', lazy=True, cascade='all, delete-orphan')

class Servicio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='servicio', lazy=True, cascade='all, delete-orphan')

class FormaPago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='forma_pago', lazy=True, cascade='all, delete-orphan')

class ModalidadPago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    numero_cuotas = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='modalidad_pago', lazy=True, cascade='all, delete-orphan')

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False, default='Cédula')
    numero_documento = db.Column(db.String(20), nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    tipo_cliente = db.Column(db.String(20), nullable=False)
    carrera = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=datetime.now)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='cliente', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('tipo_documento', 'numero_documento', name='uq_cliente_documento'),
    )

class Empleado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False, default='Cédula')
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    numero_documento = db.Column(db.String(20), nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    tanda_labor = db.Column(db.String(50), nullable=False)
    fecha_ingreso = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='empleado', lazy=True, cascade='all, delete-orphan')
    usuarios = db.relationship('Usuario', backref='empleado', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('tipo_documento', 'numero_documento', name='uq_empleado_documento'),
    )

class MovimientoCaja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empleado_id = db.Column(db.Integer, db.ForeignKey('empleado.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicio.id'), nullable=False)
    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipo_documento.id'), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('forma_pago.id'), nullable=False)
    modalidad_pago_id = db.Column(db.Integer, db.ForeignKey('modalidad_pago.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, nullable=False, default=datetime.now)
    monto = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='Activo')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Sistema de Validaciones MEJORADO con algoritmos oficiales
class Validator:
    @staticmethod
    def validar_texto(texto, campo, min_len=1, max_len=200):
        if not texto or not texto.strip():
            return False, f"{campo} no puede estar vacío"
        if len(texto.strip()) < min_len:
            return False, f"{campo} debe tener al menos {min_len} caracteres"
        if len(texto.strip()) > max_len:
            return False, f"{campo} no puede tener más de {max_len} caracteres"
        return True, "OK"
    
    @staticmethod
    def validar_numero(numero, campo, min_val=0, max_val=999999):
        try:
            num = float(numero)
            if num < min_val:
                return False, f"{campo} no puede ser menor a {min_val}"
            if num > max_val:
                return False, f"{campo} no puede ser mayor a {max_val}"
            return True, "OK"
        except (ValueError, TypeError):
            return False, f"{campo} debe ser un número válido"
    
    @staticmethod
    def validar_fecha(fecha_str, campo):
        try:
            datetime.strptime(fecha_str, '%Y-%m-%d')
            return True, "OK"
        except ValueError:
            return False, f"{campo} debe tener formato YYYY-MM-DD"
    
    @staticmethod
    def validar_cedula(cedula):
        """
        Valida cédula dominicana - Algoritmo adaptado del código C#
        Formato: 001-1234567-8 o 00112345678
        """
        if not cedula or not cedula.strip():
            return False, "La cédula no puede estar vacía"
        
        # Limpiar guiones y espacios
        vcCedula = cedula.replace('-', '').replace(' ', '')
        pLongCed = len(vcCedula.strip())
        
        # Validar longitud
        if pLongCed != 11:
            return False, "La cédula debe tener 11 dígitos"
        
        # Validar que sean solo números
        if not vcCedula.isdigit():
            return False, "La cédula debe contener solo números"
        
        # Algoritmo de validación
        vnTotal = 0
        digitoMult = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1]
        
        for vDig in range(1, pLongCed + 1):
            vCalculo = int(vcCedula[vDig - 1]) * digitoMult[vDig - 1]
            if vCalculo < 10:
                vnTotal += vCalculo
            else:
                vCalculo_str = str(vCalculo)
                vnTotal += int(vCalculo_str[0]) + int(vCalculo_str[1])
        
        if vnTotal % 10 == 0:
            return True, "OK"
        else:
            return False, "Cédula inválida - verificación fallida"
    
    @staticmethod
    def validar_ruc(ruc):
        """
        Valida RUC dominicano - Algoritmo adaptado del código C#
        Formato: 130000000 o 1-30-00000-8
        """
        if not ruc or not ruc.strip():
            return False, "El RUC no puede estar vacío"
        
        # Limpiar guiones y espacios
        ruc_limpio = ruc.replace('-', '').replace(' ', '')
        
        # Validar longitud
        if len(ruc_limpio) != 9:
            return False, "El RUC debe tener 9 dígitos"
        
        # Validar que sean solo números
        if not ruc_limpio.isdigit():
            return False, "El RUC debe contener solo números"
        
        # Algoritmo de validación RNC
        peso = [7, 9, 8, 6, 5, 4, 3, 2]
        suma = 0
        
        # Verificar que los primeros 8 caracteres sean dígitos
        for i in range(8):
            if not ruc_limpio[i].isdigit():
                return False, "RUC inválido - formato incorrecto"
            
            suma += int(ruc_limpio[i]) * peso[i]
        
        division = suma // 11
        resto = suma - (division * 11)
        digito = 0
        
        if resto == 0:
            digito = 2
        elif resto == 1:
            digito = 1
        else:
            digito = 11 - resto
        
        if digito != int(ruc_limpio[8]):
            return False, "RUC inválido - dígito verificador incorrecto"
        
        return True, "OK"
    
    @staticmethod
    def validar_pasaporte(pasaporte):
        """
        Valida formato básico de pasaporte
        """
        if not pasaporte or not pasaporte.strip():
            return False, "El pasaporte no puede estar vacío"
        
        pasaporte_limpio = pasaporte.strip().upper()
        
        # Longitud típica de pasaportes
        if len(pasaporte_limpio) < 6 or len(pasaporte_limpio) > 9:
            return False, "El pasaporte debe tener entre 6 y 9 caracteres"
        
        # Debe empezar con letra y contener letras/números
        if not pasaporte_limpio[0].isalpha():
            return False, "El pasaporte debe empezar con una letra"
        
        # Validar caracteres alfanuméricos
        if not pasaporte_limpio.isalnum():
            return False, "El pasaporte solo puede contener letras y números"
        
        return True, "OK"
    
    @staticmethod
    def validar_ncf(ncf):
        """
        Valida NCF (Número de Comprobante Fiscal) dominicano
        Formato: E310000000005
        """
        if not ncf or not ncf.strip():
            return False, "El NCF no puede estar vacío"
        
        ncf_limpio = ncf.strip().upper()
        
        # Longitud fija
        if len(ncf_limpio) != 13:
            return False, "El NCF debe tener 13 caracteres"
        
        # Validar estructura: Letra + 2 dígitos + 9 dígitos + letra
        if (not ncf_limpio[0].isalpha() or 
            not ncf_limpio[1:3].isdigit() or 
            not ncf_limpio[3:12].isdigit() or 
            not ncf_limpio[12].isalpha()):
            return False, "Formato de NCF inválido"
        
        # Validar tipo de comprobante (primera letra)
        tipos_validos = ['B', 'E', 'F', 'C']  # Facturas, Gastos, etc.
        if ncf_limpio[0] not in tipos_validos:
            return False, "Tipo de comprobante fiscal inválido"
        
        return True, "OK"
    
    @staticmethod
    def validar_documento_por_tipo(tipo_documento, numero_documento):
        """
        Valida cualquier documento según su tipo
        """
        if tipo_documento == "Cédula":
            return Validator.validar_cedula(numero_documento)
        elif tipo_documento == "RUC":
            return Validator.validar_ruc(numero_documento)
        elif tipo_documento == "Pasaporte":
            return Validator.validar_pasaporte(numero_documento)
        elif tipo_documento in ["NCF", "Comprobante Fiscal"]:
            return Validator.validar_ncf(numero_documento)
        else:
            # Para otros tipos de documentos, validación básica
            return Validator.validar_texto(numero_documento, "Documento", 2, 50)
    
    @staticmethod
    def validar_email(email):
        if not email:
            return True, "OK"  # Email es opcional
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, "OK"
        return False, "El formato del email no es válido"

# Funciones de validación completas
def validar_empleado_completo(data):
    """Valida todos los campos de un empleado"""
    validaciones = [
        Validator.validar_texto(data.get('nombre'), 'Nombre', 2, 200),
        Validator.validar_texto(data.get('tipo_documento'), 'Tipo de documento', 2, 20),
        Validator.validar_documento_por_tipo(data.get('tipo_documento'), data.get('numero_documento')),
        Validator.validar_texto(data.get('tanda_labor'), 'Tanda labor', 2, 50),
        Validator.validar_fecha(data.get('fecha_ingreso'), 'Fecha de ingreso')
    ]
    
    # Validar email si está presente
    email = data.get('email')
    if email and email.strip():
        val_email = Validator.validar_email(email)
        if not val_email[0]:
            return False, val_email[1]
    
    for es_valido, mensaje in validaciones:
        if not es_valido:
            return False, mensaje
    
    return True, "Empleado válido"

def validar_cliente_completo(data):
    """Valida todos los campos de un cliente"""
    validaciones = [
        Validator.validar_texto(data.get('nombre'), 'Nombre', 2, 200),
        Validator.validar_texto(data.get('tipo_documento'), 'Tipo de documento', 2, 20),
        Validator.validar_documento_por_tipo(data.get('tipo_documento'), data.get('numero_documento')),
        Validator.validar_texto(data.get('carrera'), 'Carrera/Departamento', 2, 100)
    ]
    
    # Validar tipo de cliente
    tipo_cliente = data.get('tipo_cliente')
    if tipo_cliente not in ['Estudiante', 'Empleado', 'Externo']:
        return False, "Tipo de cliente inválido"
    
    # Validar email si está presente
    email = data.get('email')
    if email and email.strip():
        val_email = Validator.validar_email(email)
        if not val_email[0]:
            return False, val_email[1]
    
    for es_valido, mensaje in validaciones:
        if not es_valido:
            return False, mensaje
    
    return True, "Cliente válido"

# Función para validar movimientos
def validar_movimiento(data):
    validaciones = [
        Validator.validar_numero(data.get('monto'), 'Monto', 0.01, 1000000),
        Validator.validar_numero(data.get('empleado_id'), 'Empleado', 1),
        Validator.validar_numero(data.get('cliente_id'), 'Cliente', 1),
        Validator.validar_numero(data.get('servicio_id'), 'Servicio', 1),
        Validator.validar_numero(data.get('tipo_documento_id'), 'Tipo de Documento', 1),
        Validator.validar_numero(data.get('forma_pago_id'), 'Forma de Pago', 1),
        Validator.validar_numero(data.get('modalidad_pago_id'), 'Modalidad de Pago', 1)
    ]
    
    for es_valido, mensaje in validaciones:
        if not es_valido:
            return False, mensaje
    
    return True, "Movimiento válido"

# Funciones de utilidad para seguridad
def requiere_rol(roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.rol.nombre not in roles_permitidos:
                flash('No tienes permisos para acceder a esta página.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Decoradores de permisos específicos
def admin_required(f):
    return requiere_rol(['ADMIN'])(f)

def gerente_required(f):
    return requiere_rol(['ADMIN', 'GERENTE'])(f)

def cajero_required(f):
    return requiere_rol(['ADMIN', 'GERENTE', 'CAJERO'])(f)

def consulta_required(f):
    return requiere_rol(['ADMIN', 'GERENTE', 'CONSULTA'])(f)

# Funciones auxiliares para permisos
def obtener_modulos_permitidos(rol):
    permisos = {
        'ADMIN': ['Dashboard', 'Movimientos', 'Consulta', 'Reportes', 'Administración', 'Seguridad'],
        'GERENTE': ['Dashboard', 'Movimientos', 'Consulta', 'Reportes', 'Administración'],
        'CAJERO': ['Dashboard', 'Movimientos'],
        'CONSULTA': ['Dashboard', 'Consulta', 'Reportes']
    }
    return permisos.get(rol, [])

def obtener_acciones_permitidas(rol):
    acciones = {
        'ADMIN': ['Ver todo', 'Crear', 'Editar', 'Eliminar', 'Generar reportes', 'Administrar usuarios'],
        'GERENTE': ['Ver todo', 'Crear', 'Editar', 'Generar reportes',],
        'CAJERO': ['Ver movimientos', 'Crear movimientos'],
        'CONSULTA': ['Ver consultas', 'Generar reportes']
    }
    return acciones.get(rol, [])

# Función auxiliar para manejar eliminaciones
def safe_delete(model, id):
    try:
        registro = model.query.get_or_404(id)
        db.session.delete(registro)
        db.session.commit()
        return True, 'Registro eliminado correctamente'
    except Exception as e:
        db.session.rollback()
        return False, f'Error al eliminar: {str(e)}'

# Crear tablas y datos iniciales
with app.app_context():
    db.create_all()
    
    # Crear roles si no existen
    if Rol.query.count() == 0:
        roles = [
            Rol(nombre='ADMIN', descripcion='Administrador del sistema con acceso completo'),
            Rol(nombre='GERENTE', descripcion='Gerente con acceso a reportes y administración'),
            Rol(nombre='CAJERO', descripcion='Cajero con acceso a movimientos'),
            Rol(nombre='CONSULTA', descripcion='Usuario de solo consulta y reportes')
        ]
        for rol in roles:
            db.session.add(rol)
        
        # Crear usuario admin por defecto
        admin_rol = Rol.query.filter_by(nombre='ADMIN').first()
        if not Usuario.query.filter_by(username='admin').first():
            admin_user = Usuario(
                username='admin',
                password=generate_password_hash('admin123'),
                email='admin@unapec.edu.do',
                rol_id=admin_rol.id,
                estado='Activo'
            )
            db.session.add(admin_user)
        
        db.session.commit()

# Rutas de Autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        usuario = Usuario.query.filter_by(username=username, estado='Activo').first()
        
        if usuario and check_password_hash(usuario.password, password):
            login_user(usuario)
            usuario.ultimo_acceso = datetime.now()
            db.session.commit()
            
            flash(f'Bienvenido {usuario.username}!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html', 
                         obtener_modulos_permitidos=obtener_modulos_permitidos,
                         obtener_acciones_permitidas=obtener_acciones_permitidas)

# Gestión de Usuarios - Solo ADMIN
@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    usuarios = Usuario.query.all()
    empleados = Empleado.query.filter_by(estado='Activo').all()
    roles = Rol.query.all()
    return render_template('admin_usuarios.html', 
                         usuarios=usuarios, 
                         empleados=empleados, 
                         roles=roles)

@app.route('/admin/agregar_usuario', methods=['POST'])
@admin_required
def agregar_usuario():
    try:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        empleado_id = request.form.get('empleado_id', type=int)
        rol_id = request.form['rol_id']
        estado = request.form['estado']
        
        # Validaciones básicas
        if not username or not password or not email:
            flash('Todos los campos obligatorios deben ser completados', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first():
            flash('Ya existe un usuario con ese nombre', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        # Generar hash de la contraseña
        password_hash = generate_password_hash(password)
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            username=username,
            password=password_hash,
            email=email,
            empleado_id=empleado_id if empleado_id else None,
            rol_id=rol_id,
            estado=estado
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # Obtener el rol asignado para mostrar en el mensaje
        rol_asignado = Rol.query.get(rol_id)
        flash(f'Usuario {username} creado correctamente con rol {rol_asignado.nombre}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear usuario: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/editar_usuario/<int:id>', methods=['POST'])
@admin_required
def editar_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        usuario.email = request.form['email']
        usuario.empleado_id = request.form.get('empleado_id', type=int)
        usuario.rol_id = request.form['rol_id']
        usuario.estado = request.form['estado']
        
        # Si se proporciona nueva contraseña
        nueva_password = request.form.get('nueva_password')
        if nueva_password:
            usuario.password = generate_password_hash(nueva_password)
        
        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar usuario: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/eliminar_usuario/<int:id>')
@admin_required
def eliminar_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        
        # No permitir eliminar el propio usuario
        if usuario.id == current_user.id:
            flash('No puedes eliminar tu propio usuario', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))

# Gestión de Roles - Solo ADMIN
@app.route('/admin/roles')
@admin_required
def admin_roles():
    roles = Rol.query.all()
    return render_template('admin_roles.html', roles=roles)

@app.route('/admin/editar_rol/<int:id>', methods=['POST'])
@admin_required
def editar_rol(id):
    try:
        rol = Rol.query.get_or_404(id)
        rol.descripcion = request.form['descripcion']
        db.session.commit()
        flash('Rol actualizado correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar rol: {str(e)}', 'danger')
    
    return redirect(url_for('admin_roles'))

# Ruta principal
@app.route('/')
@login_required
def index():
    total_clientes = Cliente.query.count()
    total_movimientos = MovimientoCaja.query.count()
    total_ingresos = db.session.query(db.func.sum(MovimientoCaja.monto)).scalar() or 0
    
    return render_template('index.html', 
                         total_clientes=total_clientes,
                         total_movimientos=total_movimientos,
                         total_ingresos=total_ingresos)

# CRUD Tipos de Documentos
@app.route('/tipos_documentos')
@gerente_required
def tipos_documentos():
    tipos = TipoDocumento.query.all()
    return render_template('tipos_documentos.html', tipos=tipos)

@app.route('/agregar_tipo_documento', methods=['POST'])
@gerente_required
def agregar_tipo_documento():
    descripcion = request.form['descripcion']
    estado = request.form['estado']
    
    nuevo_tipo = TipoDocumento(descripcion=descripcion, estado=estado)
    db.session.add(nuevo_tipo)
    db.session.commit()
    flash('Tipo de documento agregado correctamente', 'success')
    return redirect(url_for('tipos_documentos'))

@app.route('/editar_tipo_documento/<int:id>', methods=['POST'])
@gerente_required
def editar_tipo_documento(id):
    tipo = TipoDocumento.query.get_or_404(id)
    tipo.descripcion = request.form['descripcion']
    tipo.estado = request.form['estado']
    db.session.commit()
    flash('Tipo de documento actualizado correctamente', 'success')
    return redirect(url_for('tipos_documentos'))

@app.route('/eliminar_tipo_documento/<int:id>')
@gerente_required
def eliminar_tipo_documento(id):
    success, message = safe_delete(TipoDocumento, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tipos_documentos'))

# CRUD Servicios
@app.route('/servicios')
@gerente_required
def servicios():
    servicios_list = Servicio.query.all()
    return render_template('servicios.html', servicios=servicios_list)

@app.route('/agregar_servicio', methods=['POST'])
@gerente_required
def agregar_servicio():
    descripcion = request.form['descripcion']
    estado = request.form['estado']
    
    nuevo_servicio = Servicio(descripcion=descripcion, estado=estado)
    db.session.add(nuevo_servicio)
    db.session.commit()
    flash('Servicio agregado correctamente', 'success')
    return redirect(url_for('servicios'))

@app.route('/editar_servicio/<int:id>', methods=['POST'])
@gerente_required
def editar_servicio(id):
    servicio = Servicio.query.get_or_404(id)
    servicio.descripcion = request.form['descripcion']
    servicio.estado = request.form['estado']
    db.session.commit()
    flash('Servicio actualizado correctamente', 'success')
    return redirect(url_for('servicios'))

@app.route('/eliminar_servicio/<int:id>')
@gerente_required
def eliminar_servicio(id):
    success, message = safe_delete(Servicio, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('servicios'))

# CRUD Formas de Pago
@app.route('/formas_pago')
@gerente_required
def formas_pago():
    formas = FormaPago.query.all()
    return render_template('formas_pago.html', formas=formas)

@app.route('/agregar_forma_pago', methods=['POST'])
@gerente_required
def agregar_forma_pago():
    descripcion = request.form['descripcion']
    estado = request.form['estado']
    
    nueva_forma = FormaPago(descripcion=descripcion, estado=estado)
    db.session.add(nueva_forma)
    db.session.commit()
    flash('Forma de pago agregada correctamente', 'success')
    return redirect(url_for('formas_pago'))

@app.route('/editar_forma_pago/<int:id>', methods=['POST'])
@gerente_required
def editar_forma_pago(id):
    forma = FormaPago.query.get_or_404(id)
    forma.descripcion = request.form['descripcion']
    forma.estado = request.form['estado']
    db.session.commit()
    flash('Forma de pago actualizada correctamente', 'success')
    return redirect(url_for('formas_pago'))

@app.route('/eliminar_forma_pago/<int:id>')
@gerente_required
def eliminar_forma_pago(id):
    success, message = safe_delete(FormaPago, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('formas_pago'))

# CRUD Modalidades de Pago
@app.route('/modalidades_pago')
@gerente_required
def modalidades_pago():
    modalidades = ModalidadPago.query.all()
    return render_template('modalidades_pago.html', modalidades=modalidades)

@app.route('/agregar_modalidad_pago', methods=['POST'])
@gerente_required
def agregar_modalidad_pago():
    descripcion = request.form['descripcion']
    numero_cuotas = int(request.form['numero_cuotas'])
    estado = request.form['estado']
    
    nueva_modalidad = ModalidadPago(
        descripcion=descripcion, 
        numero_cuotas=numero_cuotas,
        estado=estado
    )
    db.session.add(nueva_modalidad)
    db.session.commit()
    flash('Modalidad de pago agregada correctamente', 'success')
    return redirect(url_for('modalidades_pago'))

@app.route('/editar_modalidad_pago/<int:id>', methods=['POST'])
@gerente_required
def editar_modalidad_pago(id):
    modalidad = ModalidadPago.query.get_or_404(id)
    modalidad.descripcion = request.form['descripcion']
    modalidad.numero_cuotas = int(request.form['numero_cuotas'])
    modalidad.estado = request.form['estado']
    db.session.commit()
    flash('Modalidad de pago actualizada correctamente', 'success')
    return redirect(url_for('modalidades_pago'))

@app.route('/eliminar_modalidad_pago/<int:id>')
@gerente_required
def eliminar_modalidad_pago(id):
    success, message = safe_delete(ModalidadPago, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('modalidades_pago'))

# CRUD Clientes - ACTUALIZADO CON NUEVOS CAMPOS
@app.route('/clientes')
@gerente_required
def clientes():
    clientes_list = Cliente.query.all()
    return render_template('clientes.html', clientes=clientes_list)

@app.route('/agregar_cliente', methods=['POST'])
@gerente_required
def agregar_cliente():
    nombre = request.form['nombre']
    tipo_documento = request.form['tipo_documento']
    numero_documento = request.form['numero_documento']
    telefono = request.form.get('telefono', '')
    email = request.form.get('email', '')
    tipo_cliente = request.form['tipo_cliente']
    carrera = request.form['carrera']
    estado = request.form['estado']
    
    # Validaciones completas
    datos_cliente = {
        'nombre': nombre,
        'tipo_documento': tipo_documento,
        'numero_documento': numero_documento,
        'carrera': carrera,
        'tipo_cliente': tipo_cliente,
        'email': email
    }
    
    es_valido, mensaje = validar_cliente_completo(datos_cliente)
    if not es_valido:
        flash(mensaje, 'danger')
        return redirect(url_for('clientes'))
    
    # Verificar si el documento ya existe
    cliente_existente = Cliente.query.filter_by(
        tipo_documento=tipo_documento,
        numero_documento=numero_documento.replace('-', '').replace(' ', '')
    ).first()
    
    if cliente_existente:
        flash('Ya existe un cliente con ese documento', 'warning')
        return redirect(url_for('clientes'))
    
    try:
        nuevo_cliente = Cliente(
            nombre=nombre.strip(),
            tipo_documento=tipo_documento,
            numero_documento=numero_documento.replace('-', '').replace(' ', ''),
            telefono=telefono.strip(),
            email=email.strip(),
            tipo_cliente=tipo_cliente,
            carrera=carrera.strip(),
            estado=estado,
            fecha_registro=datetime.now()
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        flash('Cliente agregado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al guardar el cliente: {str(e)}', 'danger')
    
    return redirect(url_for('clientes'))

@app.route('/editar_cliente/<int:id>', methods=['POST'])
@gerente_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    nombre = request.form['nombre']
    tipo_documento = request.form['tipo_documento']
    numero_documento = request.form['numero_documento']
    telefono = request.form.get('telefono', '')
    email = request.form.get('email', '')
    tipo_cliente = request.form['tipo_cliente']
    carrera = request.form['carrera']
    estado = request.form['estado']
    
    # Validaciones completas
    datos_cliente = {
        'nombre': nombre,
        'tipo_documento': tipo_documento,
        'numero_documento': numero_documento,
        'carrera': carrera,
        'tipo_cliente': tipo_cliente,
        'email': email
    }
    
    es_valido, mensaje = validar_cliente_completo(datos_cliente)
    if not es_valido:
        flash(mensaje, 'danger')
        return redirect(url_for('clientes'))
    
    # Verificar si el documento ya existe (excluyendo el actual)
    cliente_existente = Cliente.query.filter(
        Cliente.tipo_documento == tipo_documento,
        Cliente.numero_documento == numero_documento.replace('-', '').replace(' ', ''),
        Cliente.id != id
    ).first()
    
    if cliente_existente:
        flash('Ya existe otro cliente con ese documento', 'warning')
        return redirect(url_for('clientes'))
    
    try:
        cliente.nombre = nombre.strip()
        cliente.tipo_documento = tipo_documento
        cliente.numero_documento = numero_documento.replace('-', '').replace(' ', '')
        cliente.telefono = telefono.strip()
        cliente.email = email.strip()
        cliente.tipo_cliente = tipo_cliente
        cliente.carrera = carrera.strip()
        cliente.estado = estado
        
        db.session.commit()
        flash('Cliente actualizado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar cliente: {str(e)}', 'danger')
    
    return redirect(url_for('clientes'))

@app.route('/eliminar_cliente/<int:id>')
@gerente_required
def eliminar_cliente(id):
    success, message = safe_delete(Cliente, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('clientes'))

# CRUD Empleados - ACTUALIZADO CON NUEVOS CAMPOS
@app.route('/empleados')
@gerente_required
def empleados():
    empleados_list = Empleado.query.all()
    return render_template('empleados.html', empleados=empleados_list)

@app.route('/agregar_empleado', methods=['POST'])
@gerente_required
def agregar_empleado():
    nombre = request.form['nombre']
    tipo_documento = request.form['tipo_documento']
    numero_documento = request.form['numero_documento']
    telefono = request.form.get('telefono', '')
    email = request.form.get('email', '')
    tanda_labor = request.form['tanda_labor']
    fecha_ingreso = request.form['fecha_ingreso']
    estado = request.form['estado']
    
    # Validaciones completas
    datos_empleado = {
        'nombre': nombre,
        'tipo_documento': tipo_documento,
        'numero_documento': numero_documento,
        'tanda_labor': tanda_labor,
        'fecha_ingreso': fecha_ingreso,
        'email': email
    }
    
    es_valido, mensaje = validar_empleado_completo(datos_empleado)
    if not es_valido:
        flash(mensaje, 'danger')
        return redirect(url_for('empleados'))
    
    # Verificar si el documento ya existe
    empleado_existente = Empleado.query.filter_by(
        tipo_documento=tipo_documento,
        numero_documento=numero_documento.replace('-', '').replace(' ', '')
    ).first()
    
    if empleado_existente:
        flash('Ya existe un empleado con ese documento', 'warning')
        return redirect(url_for('empleados'))
    
    try:
        nuevo_empleado = Empleado(
            nombre=nombre.strip(),
            tipo_documento=tipo_documento,
            cedula=numero_documento.replace('-', '').replace(' ', '') if tipo_documento == 'Cédula' else '',
            numero_documento=numero_documento.replace('-', '').replace(' ', ''),
            telefono=telefono.strip(),
            email=email.strip(),
            tanda_labor=tanda_labor,
            fecha_ingreso=datetime.strptime(fecha_ingreso, '%Y-%m-%d'),
            estado=estado
        )
        db.session.add(nuevo_empleado)
        db.session.commit()
        flash('Empleado agregado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al guardar el empleado: {str(e)}', 'danger')
    
    return redirect(url_for('empleados'))

@app.route('/editar_empleado/<int:id>', methods=['POST'])
@gerente_required
def editar_empleado(id):
    empleado = Empleado.query.get_or_404(id)
    
    nombre = request.form['nombre']
    tipo_documento = request.form['tipo_documento']
    numero_documento = request.form['numero_documento']
    telefono = request.form.get('telefono', '')
    email = request.form.get('email', '')
    tanda_labor = request.form['tanda_labor']
    fecha_ingreso = request.form['fecha_ingreso']
    estado = request.form['estado']
    
    # Validaciones completas
    datos_empleado = {
        'nombre': nombre,
        'tipo_documento': tipo_documento,
        'numero_documento': numero_documento,
        'tanda_labor': tanda_labor,
        'fecha_ingreso': fecha_ingreso,
        'email': email
    }
    
    es_valido, mensaje = validar_empleado_completo(datos_empleado)
    if not es_valido:
        flash(mensaje, 'danger')
        return redirect(url_for('empleados'))
    
    # Verificar si el documento ya existe (excluyendo el actual)
    empleado_existente = Empleado.query.filter(
        Empleado.tipo_documento == tipo_documento,
        Empleado.numero_documento == numero_documento.replace('-', '').replace(' ', ''),
        Empleado.id != id
    ).first()
    
    if empleado_existente:
        flash('Ya existe otro empleado con ese documento', 'warning')
        return redirect(url_for('empleados'))
    
    try:
        empleado.nombre = nombre.strip()
        empleado.tipo_documento = tipo_documento
        empleado.numero_documento = numero_documento.replace('-', '').replace(' ', '')
        if tipo_documento == 'Cédula':
            empleado.cedula = numero_documento.replace('-', '').replace(' ', '')
        empleado.telefono = telefono.strip()
        empleado.email = email.strip()
        empleado.tanda_labor = tanda_labor
        empleado.fecha_ingreso = datetime.strptime(fecha_ingreso, '%Y-%m-%d')
        empleado.estado = estado
        
        db.session.commit()
        flash('Empleado actualizado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar empleado: {str(e)}', 'danger')
    
    return redirect(url_for('empleados'))

@app.route('/eliminar_empleado/<int:id>')
@gerente_required
def eliminar_empleado(id):
    success, message = safe_delete(Empleado, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('empleados'))

# Movimientos de Caja
@app.route('/movimientos')
@cajero_required
def movimientos():
    # Obtener parámetros de filtro
    empleado_id = request.args.get('empleado_id', type=int)
    cliente_id = request.args.get('cliente_id', type=int)
    servicio_id = request.args.get('servicio_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    
    # Construir query base
    query = MovimientoCaja.query
    
    # Aplicar filtros
    if empleado_id:
        query = query.filter_by(empleado_id=empleado_id)
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    if servicio_id:
        query = query.filter_by(servicio_id=servicio_id)
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        fecha_hasta_completa = f"{fecha_hasta} 23:59:59"
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta_completa)
    
    # Obtener movimientos filtrados
    movimientos_list = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    # Obtener datos para los filtros y formulario
    tipos_documentos = TipoDocumento.query.filter_by(estado='Activo').all()
    servicios = Servicio.query.filter_by(estado='Activo').all()
    formas_pago = FormaPago.query.filter_by(estado='Activo').all()
    modalidades_pago = ModalidadPago.query.filter_by(estado='Activo').all()
    clientes = Cliente.query.filter_by(estado='Activo').all()
    empleados = Empleado.query.filter_by(estado='Activo').all()
    
    return render_template('movimientos.html', 
                         movimientos=movimientos_list,
                         tipos_documentos=tipos_documentos,
                         servicios=servicios,
                         formas_pago=formas_pago,
                         modalidades_pago=modalidades_pago,
                         clientes=clientes,
                         empleados=empleados)

@app.route('/agregar_movimiento', methods=['POST'])
@cajero_required
def agregar_movimiento():
    try:
        # Recoger datos del formulario
        empleado_id = int(request.form['empleado_id'])
        cliente_id = int(request.form['cliente_id'])
        servicio_id = int(request.form['servicio_id'])
        tipo_documento_id = int(request.form['tipo_documento_id'])
        forma_pago_id = int(request.form['forma_pago_id'])
        modalidad_pago_id = int(request.form['modalidad_pago_id'])
        monto = float(request.form['monto'])
        descripcion = request.form.get('descripcion', '')
        
        # Validar que las referencias existan
        if not Empleado.query.get(empleado_id):
            flash('El empleado seleccionado no existe', 'danger')
            return redirect(url_for('movimientos'))
        
        if not Cliente.query.get(cliente_id):
            flash('El cliente seleccionado no existe', 'danger')
            return redirect(url_for('movimientos'))
            
        if not Servicio.query.get(servicio_id):
            flash('El servicio seleccionado no existe', 'danger')
            return redirect(url_for('movimientos'))
        
        # Crear movimiento
        nuevo_movimiento = MovimientoCaja(
            empleado_id=empleado_id,
            cliente_id=cliente_id,
            servicio_id=servicio_id,
            tipo_documento_id=tipo_documento_id,
            forma_pago_id=forma_pago_id,
            modalidad_pago_id=modalidad_pago_id,
            monto=monto,
            descripcion=descripcion,
            estado='Activo',
            fecha_movimiento=datetime.now()
        )
        
        db.session.add(nuevo_movimiento)
        db.session.commit()
        
        flash('Movimiento registrado correctamente', 'success')
        
    except ValueError as e:
        flash('Error en los datos numéricos proporcionados', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar el movimiento: {str(e)}', 'danger')
    
    return redirect(url_for('movimientos'))

@app.route('/eliminar_movimiento/<int:id>')
@cajero_required
def eliminar_movimiento(id):
    success, message = safe_delete(MovimientoCaja, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('movimientos'))

# Consultas Simplificadas
@app.route('/consulta')
@consulta_required
def consulta():
    movimientos = []
    
    # Obtener parámetros de búsqueda simplificados
    nombre_cliente = request.args.get('nombre_cliente', '').strip()
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    
    # Construir query base
    query = MovimientoCaja.query
    
    # Aplicar filtros de manera flexible
    if nombre_cliente:
        # Buscar por nombre del cliente (búsqueda parcial)
        query = query.join(Cliente).filter(Cliente.nombre.ilike(f'%{nombre_cliente}%'))
    
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta)
        
    movimientos = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    return render_template('consulta.html', 
                         movimientos=movimientos,
                         nombre_cliente=nombre_cliente,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

# Búsqueda Unificada de Clientes y Empleados
@app.route('/busqueda')
@login_required
def busqueda():
    query = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '')
    
    resultados_clientes = []
    resultados_empleados = []
    
    if query:
        # Búsqueda en Clientes
        if not tipo or tipo == 'cliente':
            clientes_query = Cliente.query
            
            # Buscar en múltiples campos
            resultados_clientes = clientes_query.filter(
                db.or_(
                    Cliente.nombre.ilike(f'%{query}%'),
                    Cliente.numero_documento.ilike(f'%{query}%'),
                    Cliente.telefono.ilike(f'%{query}%'),
                    Cliente.email.ilike(f'%{query}%'),
                    Cliente.carrera.ilike(f'%{query}%')
                )
            ).order_by(Cliente.nombre).all()
        
        # Búsqueda en Empleados
        if not tipo or tipo == 'empleado':
            empleados_query = Empleado.query
            
            # Buscar en múltiples campos
            resultados_empleados = empleados_query.filter(
                db.or_(
                    Empleado.nombre.ilike(f'%{query}%'),
                    Empleado.numero_documento.ilike(f'%{query}%'),
                    Empleado.cedula.ilike(f'%{query}%'),
                    Empleado.telefono.ilike(f'%{query}%'),
                    Empleado.email.ilike(f'%{query}%'),
                    Empleado.tanda_labor.ilike(f'%{query}%')
                )
            ).order_by(Empleado.nombre).all()
    
    return render_template('busqueda.html',
                         resultados_clientes=resultados_clientes,
                         resultados_empleados=resultados_empleados,
                         query=query,
                         tipo=tipo)

# Función auxiliar para obtener movimientos filtrados
def obtener_movimientos_filtrados():
    forma_pago_id = request.args.get('forma_pago_id', type=int) or None
    servicio_id = request.args.get('servicio_id', type=int) or None
    modalidad_pago_id = request.args.get('modalidad_pago_id', type=int) or None
    tipo_documento_id = request.args.get('tipo_documento_id', type=int) or None
    cliente_id = request.args.get('cliente_id', type=int) or None
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    
    query = MovimientoCaja.query.join(Cliente).join(Servicio).join(FormaPago)
    
    if forma_pago_id:
        query = query.filter(MovimientoCaja.forma_pago_id == forma_pago_id)
    if servicio_id:
        query = query.filter(MovimientoCaja.servicio_id == servicio_id)
    if modalidad_pago_id:
        query = query.filter(MovimientoCaja.modalidad_pago_id == modalidad_pago_id)
    if tipo_documento_id:
        query = query.filter(MovimientoCaja.tipo_documento_id == tipo_documento_id)
    if cliente_id:
        query = query.filter(MovimientoCaja.cliente_id == cliente_id)
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        fecha_hasta_completa = f"{fecha_hasta} 23:59:59"
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta_completa)
        
    return query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()

# Exportar a PDF
@app.route('/exportar-pdf')
@consulta_required
def exportar_pdf():
    # Obtener movimientos filtrados
    movimientos = obtener_movimientos_filtrados()
    
    # Crear PDF
    pdf = PDFReport()
    pdf.add_page()
    
    # Información del reporte
    fecha_desde = request.args.get('fecha_desde', 'Inicio')
    fecha_hasta = request.args.get('fecha_hasta', 'Hoy')
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f'Período: {fecha_desde} hasta {fecha_hasta}', 0, 1)
    pdf.cell(0, 8, f'Total de movimientos: {len(movimientos)}', 0, 1)
    pdf.cell(0, 8, f'Ingreso total: ${sum(m.monto for m in movimientos):.2f}', 0, 1)
    pdf.ln(10)
    
    if movimientos:
        # Resumen estadístico
        pdf.chapter_title('RESUMEN ESTADÍSTICO')
        
        total = sum(m.monto for m in movimientos)
        promedio = total / len(movimientos) if movimientos else 0
        max_monto = max(m.monto for m in movimientos) if movimientos else 0
        
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f'- Total de movimientos: {len(movimientos)}', 0, 1)
        pdf.cell(0, 8, f'- Ingreso total: ${total:.2f}', 0, 1)
        pdf.cell(0, 8, f'- Promedio por movimiento: ${promedio:.2f}', 0, 1)
        pdf.cell(0, 8, f'- Movimiento más alto: ${max_monto:.2f}', 0, 1)
        pdf.ln(10)
        
        # Tabla de movimientos
        pdf.chapter_title('DETALLE DE MOVIMIENTOS')
        
        # Encabezados de la tabla
        pdf.set_fill_color(200, 200, 200)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(25, 10, 'Fecha', 1, 0, 'C', True)
        pdf.cell(50, 10, 'Cliente', 1, 0, 'C', True)
        pdf.cell(45, 10, 'Servicio', 1, 0, 'C', True)
        pdf.cell(40, 10, 'Forma Pago', 1, 0, 'C', True)
        pdf.cell(30, 10, 'Monto', 1, 1, 'C', True)
        
        # Datos de la tabla
        pdf.set_font('Arial', '', 9)
        fill = False
        for movimiento in movimientos:
            # Alternar colores para mejor legibilidad
            if fill:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            # Truncar nombres largos
            cliente_nombre = movimiento.cliente.nombre
            if len(cliente_nombre) > 30:
                cliente_nombre = cliente_nombre[:27] + "..."
            
            servicio_nombre = movimiento.servicio.descripcion
            if len(servicio_nombre) > 25:
                servicio_nombre = servicio_nombre[:22] + "..."
            
            forma_pago = movimiento.forma_pago.descripcion
            if len(forma_pago) > 20:
                forma_pago = forma_pago[:17] + "..."
            
            pdf.cell(25, 8, movimiento.fecha_movimiento.strftime('%d/%m/%Y'), 1, 0, 'C', fill)
            pdf.cell(50, 8, cliente_nombre, 1, 0, 'L', fill)
            pdf.cell(45, 8, servicio_nombre, 1, 0, 'L', fill)
            pdf.cell(40, 8, forma_pago, 1, 0, 'L', fill)
            pdf.cell(30, 8, f"${movimiento.monto:.2f}", 1, 1, 'R', fill)
            fill = not fill
            
            # Verificar si necesita nueva página
            if pdf.get_y() > 260:
                pdf.add_page()
                # Volver a poner encabezados en nueva página
                pdf.set_fill_color(200, 200, 200)
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(25, 10, 'Fecha', 1, 0, 'C', True)
                pdf.cell(50, 10, 'Cliente', 1, 0, 'C', True)
                pdf.cell(45, 10, 'Servicio', 1, 0, 'C', True)
                pdf.cell(40, 10, 'Forma Pago', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Monto', 1, 1, 'C', True)
                pdf.set_font('Arial', '', 9)
        
        pdf.ln(10)
        
    else:
        pdf.chapter_title('INFORMACIÓN')
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 8, 'No hay movimientos que coincidan con los criterios seleccionados.')
    
    # Guardar PDF en buffer
   # CORRECCIÓN SIMPLIFICADA - solo cambia estas líneas al final de la función:

    # Guardar PDF en buffer - VERSIÓN CORREGIDA
    pdf_buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S')  # 'S' para obtener como string
    
    # Verificar el tipo y manejarlo apropiadamente
    if isinstance(pdf_output, str):
        pdf_buffer.write(pdf_output.encode('latin1'))
    else:
        pdf_buffer.write(pdf_output)
    
    pdf_buffer.seek(0)
    
    return Response(
        pdf_buffer.getvalue(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename=reporte_movimientos_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        }
    )

# Generar gráfico de servicios
@app.route('/grafico/servicios')
@consulta_required
def grafico_servicios():
    # Obtener los mismos filtros que el reporte
    movimientos = obtener_movimientos_filtrados()
    
    # Agrupar por servicio
    servicios_data = {}
    for movimiento in movimientos:
        servicio_nombre = movimiento.servicio.descripcion
        if servicio_nombre not in servicios_data:
            servicios_data[servicio_nombre] = 0
        servicios_data[servicio_nombre] += movimiento.monto
    
    # Crear gráfico
    plt.figure(figsize=(8, 6))
    if servicios_data:
        # Usar colores pastel
        colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFD700', '#FFB6C1', '#C2C2F0']
        plt.pie(servicios_data.values(), 
                labels=servicios_data.keys(), 
                autopct='%1.1f%%', 
                startangle=90,
                colors=colors[:len(servicios_data)])
        plt.title('Distribución de Ingresos por Servicio', fontsize=14, fontweight='bold')
    else:
        plt.text(0.5, 0.5, 'No hay datos disponibles', 
                ha='center', va='center', transform=plt.gca().transAxes,
                fontsize=12, style='italic')
        plt.title('Distribución de Ingresos por Servicio', fontsize=14, fontweight='bold')
    
    # Guardar en buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    buf.seek(0)
    
    return Response(buf.getvalue(), mimetype='image/png')

# Generar gráfico de formas de pago
@app.route('/grafico/formas-pago')
@consulta_required
def grafico_formas_pago():
    # Obtener los mismos filtros que el reporte
    movimientos = obtener_movimientos_filtrados()
    
    # Agrupar por forma de pago
    formas_pago_data = {}
    for movimiento in movimientos:
        forma_pago_nombre = movimiento.forma_pago.descripcion
        if forma_pago_nombre not in formas_pago_data:
            formas_pago_data[forma_pago_nombre] = 0
        formas_pago_data[forma_pago_nombre] += movimiento.monto
    
    # Crear gráfico de barras
    plt.figure(figsize=(10, 6))
    if formas_pago_data:
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        bars = plt.bar(formas_pago_data.keys(), formas_pago_data.values(), 
                      color=colors[:len(formas_pago_data)])
        plt.title('Distribución de Ingresos por Forma de Pago', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Monto ($)', fontweight='bold')
        
        # Agregar valores en las barras
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:,.2f}',
                    ha='center', va='bottom', fontweight='bold')
    else:
        plt.text(0.5, 0.5, 'No hay datos disponibles', 
                ha='center', va='center', transform=plt.gca().transAxes,
                fontsize=12, style='italic')
        plt.title('Distribución de Ingresos por Forma de Pago', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # Guardar en buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    buf.seek(0)
    
    return Response(buf.getvalue(), mimetype='image/png')

# Reportes Corregidos
@app.route('/reporte')
@consulta_required
def reporte():
    # Obtener parámetros de filtro con valores por defecto
    forma_pago_id = request.args.get('forma_pago_id', type=int) or None
    servicio_id = request.args.get('servicio_id', type=int) or None
    modalidad_pago_id = request.args.get('modalidad_pago_id', type=int) or None
    tipo_documento_id = request.args.get('tipo_documento_id', type=int) or None
    cliente_id = request.args.get('cliente_id', type=int) or None
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    
    # Construir query base con joins para optimizar
    query = MovimientoCaja.query.join(Cliente).join(Servicio).join(FormaPago)
    
    # Aplicar filtros solo si tienen valor
    if forma_pago_id:
        query = query.filter(MovimientoCaja.forma_pago_id == forma_pago_id)
    if servicio_id:
        query = query.filter(MovimientoCaja.servicio_id == servicio_id)
    if modalidad_pago_id:
        query = query.filter(MovimientoCaja.modalidad_pago_id == modalidad_pago_id)
    if tipo_documento_id:
        query = query.filter(MovimientoCaja.tipo_documento_id == tipo_documento_id)
    if cliente_id:
        query = query.filter(MovimientoCaja.cliente_id == cliente_id)
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        # Agregar 23:59:59 a la fecha hasta para incluir todo el día
        fecha_hasta_completa = f"{fecha_hasta} 23:59:59"
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta_completa)
    
    # Ejecutar query
    movimientos = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    # Cálculos estadísticos
    total = sum(m.monto for m in movimientos) if movimientos else 0
    promedio = total / len(movimientos) if movimientos else 0
    movimiento_max = max(movimientos, key=lambda x: x.monto) if movimientos else None
    movimiento_min = min(movimientos, key=lambda x: x.monto) if movimientos else None
    
    # Obtener datos para los filtros
    formas_pago = FormaPago.query.filter_by(estado='Activo').all()
    servicios = Servicio.query.filter_by(estado='Activo').all()
    modalidades_pago = ModalidadPago.query.filter_by(estado='Activo').all()
    tipos_documentos = TipoDocumento.query.filter_by(estado='Activo').all()
    clientes = Cliente.query.filter_by(estado='Activo').all()
    
    return render_template('reporte.html', 
                         movimientos=movimientos,
                         formas_pago=formas_pago,
                         servicios=servicios,
                         modalidades_pago=modalidades_pago,
                         tipos_documentos=tipos_documentos,
                         clientes=clientes,
                         total=total,
                         promedio=promedio,
                         movimiento_max=movimiento_max,
                         movimiento_min=movimiento_min,
                         # Pasar los valores actuales de filtros para mantenerlos en el form
                         forma_pago_id=forma_pago_id,
                         servicio_id=servicio_id,
                         modalidad_pago_id=modalidad_pago_id,
                         tipo_documento_id=tipo_documento_id,
                         cliente_id=cliente_id,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

# Context processor para hacer datetime disponible en todos los templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

if __name__ == '__main__':
    app.run(debug=True)