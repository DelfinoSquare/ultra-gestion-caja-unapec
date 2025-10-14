from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'unapec-caja-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///caja_unapec.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos Actualizados con eliminación en cascada
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

# Crear tablas
with app.app_context():
    db.create_all()

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

# Ruta principal
@app.route('/')
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
def tipos_documentos():
    tipos = TipoDocumento.query.all()
    return render_template('tipos_documentos.html', tipos=tipos)

@app.route('/agregar_tipo_documento', methods=['POST'])
def agregar_tipo_documento():
    descripcion = request.form['descripcion']
    estado = request.form['estado']
    
    nuevo_tipo = TipoDocumento(descripcion=descripcion, estado=estado)
    db.session.add(nuevo_tipo)
    db.session.commit()
    flash('Tipo de documento agregado correctamente', 'success')
    return redirect(url_for('tipos_documentos'))

@app.route('/editar_tipo_documento/<int:id>', methods=['POST'])
def editar_tipo_documento(id):
    tipo = TipoDocumento.query.get_or_404(id)
    tipo.descripcion = request.form['descripcion']
    tipo.estado = request.form['estado']
    db.session.commit()
    flash('Tipo de documento actualizado correctamente', 'success')
    return redirect(url_for('tipos_documentos'))

@app.route('/eliminar_tipo_documento/<int:id>')
def eliminar_tipo_documento(id):
    success, message = safe_delete(TipoDocumento, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tipos_documentos'))

# CRUD Servicios
@app.route('/servicios')
def servicios():
    servicios_list = Servicio.query.all()
    return render_template('servicios.html', servicios=servicios_list)

@app.route('/agregar_servicio', methods=['POST'])
def agregar_servicio():
    descripcion = request.form['descripcion']
    estado = request.form['estado']
    
    nuevo_servicio = Servicio(descripcion=descripcion, estado=estado)
    db.session.add(nuevo_servicio)
    db.session.commit()
    flash('Servicio agregado correctamente', 'success')
    return redirect(url_for('servicios'))

@app.route('/editar_servicio/<int:id>', methods=['POST'])
def editar_servicio(id):
    servicio = Servicio.query.get_or_404(id)
    servicio.descripcion = request.form['descripcion']
    servicio.estado = request.form['estado']
    db.session.commit()
    flash('Servicio actualizado correctamente', 'success')
    return redirect(url_for('servicios'))

@app.route('/eliminar_servicio/<int:id>')
def eliminar_servicio(id):
    success, message = safe_delete(Servicio, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('servicios'))

# CRUD Formas de Pago
@app.route('/formas_pago')
def formas_pago():
    formas = FormaPago.query.all()
    return render_template('formas_pago.html', formas=formas)

@app.route('/agregar_forma_pago', methods=['POST'])
def agregar_forma_pago():
    descripcion = request.form['descripcion']
    estado = request.form['estado']
    
    nueva_forma = FormaPago(descripcion=descripcion, estado=estado)
    db.session.add(nueva_forma)
    db.session.commit()
    flash('Forma de pago agregada correctamente', 'success')
    return redirect(url_for('formas_pago'))

@app.route('/editar_forma_pago/<int:id>', methods=['POST'])
def editar_forma_pago(id):
    forma = FormaPago.query.get_or_404(id)
    forma.descripcion = request.form['descripcion']
    forma.estado = request.form['estado']
    db.session.commit()
    flash('Forma de pago actualizada correctamente', 'success')
    return redirect(url_for('formas_pago'))

@app.route('/eliminar_forma_pago/<int:id>')
def eliminar_forma_pago(id):
    success, message = safe_delete(FormaPago, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('formas_pago'))

# CRUD Modalidades de Pago
@app.route('/modalidades_pago')
def modalidades_pago():
    modalidades = ModalidadPago.query.all()
    return render_template('modalidades_pago.html', modalidades=modalidades)

@app.route('/agregar_modalidad_pago', methods=['POST'])
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
def editar_modalidad_pago(id):
    modalidad = ModalidadPago.query.get_or_404(id)
    modalidad.descripcion = request.form['descripcion']
    modalidad.numero_cuotas = int(request.form['numero_cuotas'])
    modalidad.estado = request.form['estado']
    db.session.commit()
    flash('Modalidad de pago actualizada correctamente', 'success')
    return redirect(url_for('modalidades_pago'))

@app.route('/eliminar_modalidad_pago/<int:id>')
def eliminar_modalidad_pago(id):
    success, message = safe_delete(ModalidadPago, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('modalidades_pago'))

# CRUD Clientes
@app.route('/clientes')
def clientes():
    clientes_list = Cliente.query.all()
    return render_template('clientes.html', clientes=clientes_list)

@app.route('/agregar_cliente', methods=['POST'])
def agregar_cliente():
    nombre = request.form['nombre']
    tipo_cliente = request.form['tipo_cliente']
    carrera = request.form['carrera']
    estado = request.form['estado']
    
    nuevo_cliente = Cliente(
        nombre=nombre,
        tipo_cliente=tipo_cliente,
        carrera=carrera,
        estado=estado,
        fecha_registro=datetime.now()
    )
    db.session.add(nuevo_cliente)
    db.session.commit()
    flash('Cliente agregado correctamente', 'success')
    return redirect(url_for('clientes'))

@app.route('/editar_cliente/<int:id>', methods=['POST'])
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
def eliminar_cliente(id):
    success, message = safe_delete(Cliente, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('clientes'))

# CRUD Empleados
@app.route('/empleados')
def empleados():
    empleados_list = Empleado.query.all()
    return render_template('empleados.html', empleados=empleados_list)

@app.route('/agregar_empleado', methods=['POST'])
def agregar_empleado():
    nombre = request.form['nombre']
    cedula = request.form['cedula']
    tanda_labor = request.form['tanda_labor']
    fecha_ingreso = datetime.strptime(request.form['fecha_ingreso'], '%Y-%m-%d')
    estado = request.form['estado']
    
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
def eliminar_empleado(id):
    success, message = safe_delete(Empleado, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('empleados'))

# Movimientos de Caja
@app.route('/movimientos')
def movimientos():
    movimientos_list = MovimientoCaja.query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
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
def agregar_movimiento():
    empleado_id = int(request.form['empleado_id'])
    cliente_id = int(request.form['cliente_id'])
    servicio_id = int(request.form['servicio_id'])
    tipo_documento_id = int(request.form['tipo_documento_id'])
    forma_pago_id = int(request.form['forma_pago_id'])
    modalidad_pago_id = int(request.form['modalidad_pago_id'])
    monto = float(request.form['monto'])
    estado = request.form['estado']
    
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
    return redirect(url_for('movimientos'))

@app.route('/eliminar_movimiento/<int:id>')
def eliminar_movimiento(id):
    success, message = safe_delete(MovimientoCaja, id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('movimientos'))

# Consultas
@app.route('/consulta')
def consulta():
    movimientos = []
    clientes = Cliente.query.all()
    servicios = Servicio.query.all()
    tipos_documentos = TipoDocumento.query.all()
    
    cliente_id = request.args.get('cliente_id', type=int)
    servicio_id = request.args.get('servicio_id', type=int)
    tipo_documento_id = request.args.get('tipo_documento_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    
    query = MovimientoCaja.query
    
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
        
    movimientos = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    return render_template('consulta.html', 
                         movimientos=movimientos,
                         clientes=clientes,
                         servicios=servicios,
                         tipos_documentos=tipos_documentos)

# Reportes
@app.route('/reporte')
def reporte():
    movimientos = []
    formas_pago = FormaPago.query.all()
    servicios = Servicio.query.all()
    modalidades_pago = ModalidadPago.query.all()
    
    forma_pago_id = request.args.get('forma_pago_id', type=int)
    servicio_id = request.args.get('servicio_id', type=int)
    modalidad_pago_id = request.args.get('modalidad_pago_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    
    query = MovimientoCaja.query
    
    if forma_pago_id:
        query = query.filter_by(forma_pago_id=forma_pago_id)
    if servicio_id:
        query = query.filter_by(servicio_id=servicio_id)
    if modalidad_pago_id:
        query = query.filter_by(modalidad_pago_id=modalidad_pago_id)
    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        query = query.filter(MovimientoCaja.fecha_movimiento <= fecha_hasta)
        
    movimientos = query.order_by(MovimientoCaja.fecha_movimiento.desc()).all()
    
    total = sum(m.monto for m in movimientos)
    
    return render_template('reporte.html', 
                         movimientos=movimientos,
                         formas_pago=formas_pago,
                         servicios=servicios,
                         modalidades_pago=modalidades_pago,
                         total=total)

if __name__ == '__main__':
    app.run(debug=True)