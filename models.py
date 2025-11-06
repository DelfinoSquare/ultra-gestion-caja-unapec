from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class TipoDocumento(db.Model):
    __tablename__ = 'tipos_documentos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    
    movimientos = db.relationship('MovimientoCaja', backref='tipo_documento', lazy=True)

class Servicio(db.Model):
    __tablename__ = 'servicios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    
    movimientos = db.relationship('MovimientoCaja', backref='servicio', lazy=True)

class FormaPago(db.Model):
    __tablename__ = 'formas_pago'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    
    movimientos = db.relationship('MovimientoCaja', backref='forma_pago', lazy=True)

class ModalidadPago(db.Model):
    __tablename__ = 'modalidades_pago'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    numero_cuotas = db.Column(db.Integer, nullable=False)
    
    movimientos = db.relationship('MovimientoCaja', backref='modalidad_pago', lazy=True)

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False, default='Cédula')
    numero_documento = db.Column(db.String(20), nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    tipo_cliente = db.Column(db.String(20), nullable=False)
    carrera = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=db.func.now())
    estado = db.Column(db.String(20), default='Activo')
    
    movimientos = db.relationship('MovimientoCaja', backref='cliente', lazy=True)

    # Índice único compuesto para evitar duplicados
    __table_args__ = (
        db.UniqueConstraint('tipo_documento', 'numero_documento', name='uq_cliente_documento'),
    )

class Empleado(db.Model):
    __tablename__ = 'empleados'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False, default='Cédula')
    cedula = db.Column(db.String(20), unique=True, nullable=False)  # Se mantiene por compatibilidad
    numero_documento = db.Column(db.String(20), nullable=False)  # Nuevo campo unificado
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    tanda_labor = db.Column(db.String(50), nullable=False)
    fecha_ingreso = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String(20), default='Activo')
    
    movimientos = db.relationship('MovimientoCaja', backref='empleado', lazy=True)
    usuarios = db.relationship('Usuario', backref='empleado', lazy=True)

    # Índice único compuesto
    __table_args__ = (
        db.UniqueConstraint('tipo_documento', 'numero_documento', name='uq_empleado_documento'),
    )

class MovimientoCaja(db.Model):
    __tablename__ = 'movimientos_caja'
    id = db.Column(db.Integer, primary_key=True)
    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipos_documentos.id'), nullable=False)
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicios.id'), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'), nullable=False)
    modalidad_pago_id = db.Column(db.Integer, db.ForeignKey('modalidades_pago.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    empleado_id = db.Column(db.Integer, db.ForeignKey('empleados.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.Text)
    fecha = db.Column(db.DateTime, nullable=False, default=db.func.now())
    estado = db.Column(db.String(20), default='Activo')