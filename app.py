from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

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

# Modelos de Negocio
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
    tipo_cliente = db.Column(db.String(20), nullable=False)
    carrera = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=datetime.now)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='cliente', lazy=True, cascade='all, delete-orphan')

class Empleado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    tanda_labor = db.Column(db.String(50), nullable=False)
    fecha_ingreso = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    movimientos = db.relationship('MovimientoCaja', backref='empleado', lazy=True, cascade='all, delete-orphan')
    usuarios = db.relationship('Usuario', backref='empleado', lazy=True)

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
    estado = db.Column(db.String(20), default='Activo')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Sistema de Validaciones
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
        if not cedula or not cedula.strip():
            return False, "La cédula no puede estar vacía"
        if len(cedula.strip()) < 11:
            return False, "La cédula debe tener al menos 11 caracteres"
        return True, "OK"
    
    @staticmethod
    def validar_email(email):
        if not email:
            return True, "OK"  # Email es opcional
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, "OK"
        return False, "El formato del email no es válido"

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
        'GERENTE': ['Ver todo', 'Crear', 'Editar', 'Generar reportes'],
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
            usuario.ultimo_acceso = datetime.now()  # ← datetime está importado al inicio
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
        
        # Validaciones
        if Usuario.query.filter_by(username=username).first():
            flash('Ya existe un usuario con ese nombre', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        nuevo_usuario = Usuario(
            username=username,
            password=generate_password_hash(password),
            email=email,
            empleado_id=empleado_id if empleado_id else None,
            rol_id=rol_id,
            estado=estado
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Usuario creado correctamente', 'success')
        
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

# CRUD Clientes
@app.route('/clientes')
@gerente_required
def clientes():
    clientes_list = Cliente.query.all()
    return render_template('clientes.html', clientes=clientes_list)

@app.route('/agregar_cliente', methods=['POST'])
@gerente_required
def agregar_cliente():
    nombre = request.form['nombre']
    tipo_cliente = request.form['tipo_cliente']
    carrera = request.form['carrera']
    estado = request.form['estado']
    
    # Validaciones
    val_nombre = Validator.validar_texto(nombre, 'Nombre', 2, 200)
    val_carrera = Validator.validar_texto(carrera, 'Carrera/Departamento', 2, 100)
    
    if not val_nombre[0]:
        flash(val_nombre[1], 'danger')
        return redirect(url_for('clientes'))
    
    if not val_carrera[0]:
        flash(val_carrera[1], 'danger')
        return redirect(url_for('clientes'))
    
    # Verificar si el cliente ya existe (por nombre)
    cliente_existente = Cliente.query.filter_by(nombre=nombre).first()
    if cliente_existente:
        flash('Ya existe un cliente con ese nombre', 'warning')
        return redirect(url_for('clientes'))
    
    nuevo_cliente = Cliente(
        nombre=nombre.strip(),
        tipo_cliente=tipo_cliente,
        carrera=carrera.strip(),
        estado=estado,
        fecha_registro=datetime.now()
    )
    
    try:
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
    cliente.nombre = request.form['nombre']
    cliente.tipo_cliente = request.form['tipo_cliente']
    cliente.carrera = request.form['carrera']
    cliente.estado = request.form['estado']
    db.session.commit()
    flash('Cliente actualizado correctamente', 'success')
    return redirect(url_for('clientes'))

@app.route('/eliminar_cliente/<int:id>')
@gerente_required
def eliminar_cliente(id):
    success, message = safe_delete(Cliente, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('clientes'))

# CRUD Empleados
@app.route('/empleados')
@gerente_required
def empleados():
    empleados_list = Empleado.query.all()
    return render_template('empleados.html', empleados=empleados_list)

@app.route('/agregar_empleado', methods=['POST'])
@gerente_required
def agregar_empleado():
    nombre = request.form['nombre']
    cedula = request.form['cedula']
    tanda_labor = request.form['tanda_labor']
    fecha_ingreso = datetime.strptime(request.form['fecha_ingreso'], '%Y-%m-%d')
    estado = request.form['estado']
    
    # Validaciones
    val_nombre = Validator.validar_texto(nombre, 'Nombre', 2, 200)
    val_cedula = Validator.validar_cedula(cedula)
    
    if not val_nombre[0]:
        flash(val_nombre[1], 'danger')
        return redirect(url_for('empleados'))
    
    if not val_cedula[0]:
        flash(val_cedula[1], 'danger')
        return redirect(url_for('empleados'))
    
    # Verificar si la cédula ya existe
    empleado_existente = Empleado.query.filter_by(cedula=cedula).first()
    if empleado_existente:
        flash('Ya existe un empleado con esa cédula', 'warning')
        return redirect(url_for('empleados'))
    
    nuevo_empleado = Empleado(
        nombre=nombre,
        cedula=cedula,
        tanda_labor=tanda_labor,
        fecha_ingreso=fecha_ingreso,
        estado=estado
    )
    db.session.add(nuevo_empleado)
    db.session.commit()
    flash('Empleado agregado correctamente', 'success')
    return redirect(url_for('empleados'))

@app.route('/editar_empleado/<int:id>', methods=['POST'])
@gerente_required
def editar_empleado(id):
    empleado = Empleado.query.get_or_404(id)
    empleado.nombre = request.form['nombre']
    empleado.cedula = request.form['cedula']
    empleado.tanda_labor = request.form['tanda_labor']
    empleado.fecha_ingreso = datetime.strptime(request.form['fecha_ingreso'], '%Y-%m-%d')
    empleado.estado = request.form['estado']
    db.session.commit()
    flash('Empleado actualizado correctamente', 'success')
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
    tipo_documento_id = request.args.get('tipo_documento_id', type=int)
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
    if tipo_documento_id:
        query = query.filter_by(tipo_documento_id=tipo_documento_id)
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta)
    
    # Obtener movimientos filtrados
    movimientos_list = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    # Obtener datos para los filtros
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
        # Recoger datos
        empleado_id = int(request.form['empleado_id'])
        cliente_id = int(request.form['cliente_id'])
        servicio_id = int(request.form['servicio_id'])
        tipo_documento_id = int(request.form['tipo_documento_id'])
        forma_pago_id = int(request.form['forma_pago_id'])
        modalidad_pago_id = int(request.form['modalidad_pago_id'])
        monto = float(request.form['monto'])
        estado = request.form['estado']
        
        # Validar movimiento
        datos_movimiento = {
            'empleado_id': empleado_id,
            'cliente_id': cliente_id,
            'servicio_id': servicio_id,
            'tipo_documento_id': tipo_documento_id,
            'forma_pago_id': forma_pago_id,
            'modalidad_pago_id': modalidad_pago_id,
            'monto': monto
        }
        
        es_valido, mensaje = validar_movimiento(datos_movimiento)
        if not es_valido:
            flash(mensaje, 'danger')
            return redirect(url_for('movimientos'))
        
        # Verificar que las referencias existan
        if not Empleado.query.get(empleado_id):
            flash('El empleado seleccionado no existe', 'danger')
            return redirect(url_for('movimientos'))
        
        if not Cliente.query.get(cliente_id):
            flash('El cliente seleccionado no existe', 'danger')
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
            estado=estado,
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

# Consultas
@app.route('/consulta')
@consulta_required
def consulta():
    movimientos = []
    clientes = Cliente.query.all()
    servicios = Servicio.query.all()
    tipos_documentos = TipoDocumento.query.all()
    formas_pago = FormaPago.query.all()
    empleados = Empleado.query.all()
    
    # Obtener todos los parámetros de filtro
    cliente_id = request.args.get('cliente_id', type=int)
    servicio_id = request.args.get('servicio_id', type=int)
    tipo_documento_id = request.args.get('tipo_documento_id', type=int)
    forma_pago_id = request.args.get('forma_pago_id', type=int)
    empleado_id = request.args.get('empleado_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    estado = request.args.get('estado')
    monto_min = request.args.get('monto_min', type=float)
    monto_max = request.args.get('monto_max', type=float)
    
    # Construir query base
    query = MovimientoCaja.query
    
    # Aplicar filtros de manera flexible
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    if servicio_id:
        query = query.filter_by(servicio_id=servicio_id)
    if tipo_documento_id:
        query = query.filter_by(tipo_documento_id=tipo_documento_id)
    if forma_pago_id:
        query = query.filter_by(forma_pago_id=forma_pago_id)
    if empleado_id:
        query = query.filter_by(empleado_id=empleado_id)
    if estado and estado != 'Todos':
        query = query.filter_by(estado=estado)
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta)
    if monto_min is not None:
        query = query.filter(MovimientoCaja.monto >= monto_min)
    if monto_max is not None:
        query = query.filter(MovimientoCaja.monto <= monto_max)
        
    movimientos = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    return render_template('consulta.html', 
                         movimientos=movimientos,
                         clientes=clientes,
                         servicios=servicios,
                         tipos_documentos=tipos_documentos,
                         formas_pago=formas_pago,
                         empleados=empleados)

# Reportes
@app.route('/reporte')
@consulta_required
def reporte():
    movimientos = []
    formas_pago = FormaPago.query.all()
    servicios = Servicio.query.all()
    modalidades_pago = ModalidadPago.query.all()
    tipos_documentos = TipoDocumento.query.all()
    clientes = Cliente.query.all()
    
    # Múltiples criterios de filtro
    forma_pago_id = request.args.get('forma_pago_id', type=int)
    servicio_id = request.args.get('servicio_id', type=int)
    modalidad_pago_id = request.args.get('modalidad_pago_id', type=int)
    tipo_documento_id = request.args.get('tipo_documento_id', type=int)
    cliente_id = request.args.get('cliente_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    agrupar_por = request.args.get('agrupar_por', 'servicio')
    
    query = MovimientoCaja.query
    
    if forma_pago_id:
        query = query.filter_by(forma_pago_id=forma_pago_id)
    if servicio_id:
        query = query.filter_by(servicio_id=servicio_id)
    if modalidad_pago_id:
        query = query.filter_by(modalidad_pago_id=modalidad_pago_id)
    if tipo_documento_id:
        query = query.filter_by(tipo_documento_id=tipo_documento_id)
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta)
        
    movimientos = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    # Cálculos estadísticos
    total = sum(m.monto for m in movimientos)
    promedio = total / len(movimientos) if movimientos else 0
    movimiento_max = max(movimientos, key=lambda x: x.monto) if movimientos else None
    movimiento_min = min(movimientos, key=lambda x: x.monto) if movimientos else None
    
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
                         agrupar_por=agrupar_por)

# Context processor para hacer datetime disponible en todos los templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

if __name__ == '__main__':
    app.run(debug=True)