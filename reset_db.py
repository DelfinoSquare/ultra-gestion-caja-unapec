from app import app, db
from datetime import datetime

def reset_database():
    with app.app_context():
        print("Eliminando tablas existentes...")
        db.drop_all()
        
        print("Creando nuevas tablas...")
        db.create_all()
        
        # Crear roles
        print("Creando roles...")
        from app import Rol, Usuario
        roles = [
            Rol(nombre='ADMIN', descripcion='Administrador del sistema con acceso completo'),
            Rol(nombre='GERENTE', descripcion='Gerente con acceso a reportes y administración'),
            Rol(nombre='CAJERO', descripcion='Cajero con acceso a movimientos'),
            Rol(nombre='CONSULTA', descripcion='Usuario de solo consulta y reportes')
        ]
        for rol in roles:
            db.session.add(rol)
        db.session.commit()
        
        # Crear usuario admin
        print("Creando usuario admin...")
        admin_rol = Rol.query.filter_by(nombre='ADMIN').first()
        admin_user = Usuario(
            username='admin',
            password='pbkdf2:sha256:260000$8N4jRlP3Q9aX7z2H$1234567890abcdef...',  # Esto se actualizará con hash real
            email='admin@unapec.edu.do',
            rol_id=admin_rol.id,
            estado='Activo'
        )
        db.session.add(admin_user)
        
        # Crear tipos de documento
        print("Creando tipos de documento...")
        from app import TipoDocumento
        tipos_documento = [
            TipoDocumento(descripcion='Recibo de Ingreso', estado='Activo'),
            TipoDocumento(descripcion='Factura', estado='Activo'),
            TipoDocumento(descripcion='Comprobante de Pago', estado='Activo'),
            TipoDocumento(descripcion='Nota de Crédito', estado='Activo'),
            TipoDocumento(descripcion='Nota de Débito', estado='Activo')
        ]
        for tipo in tipos_documento:
            db.session.add(tipo)
        
        # Crear servicios
        print("Creando servicios...")
        from app import Servicio
        servicios = [
            Servicio(descripcion='Matrícula', estado='Activo'),
            Servicio(descripcion='Colegiatura', estado='Activo'),
            Servicio(descripcion='Derecho de Grado', estado='Activo'),
            Servicio(descripcion='Traslado', estado='Activo'),
            Servicio(descripcion='Constancias', estado='Activo')
        ]
        for servicio in servicios:
            db.session.add(servicio)
        
        # Crear formas de pago
        print("Creando formas de pago...")
        from app import FormaPago
        formas_pago = [
            FormaPago(descripcion='Efectivo', estado='Activo'),
            FormaPago(descripcion='Tarjeta de Crédito', estado='Activo'),
            FormaPago(descripcion='Tarjeta de Débito', estado='Activo'),
            FormaPago(descripcion='Transferencia', estado='Activo'),
            FormaPago(descripcion='Cheque', estado='Activo')
        ]
        for forma in formas_pago:
            db.session.add(forma)
        
        # Crear modalidades de pago
        print("Creando modalidades de pago...")
        from app import ModalidadPago
        modalidades_pago = [
            ModalidadPago(descripcion='Contado', numero_cuotas=1, estado='Activo'),
            ModalidadPago(descripcion='2 Cuotas', numero_cuotas=2, estado='Activo'),
            ModalidadPago(descripcion='3 Cuotas', numero_cuotas=3, estado='Activo'),
            ModalidadPago(descripcion='6 Cuotas', numero_cuotas=6, estado='Activo')
        ]
        for modalidad in modalidades_pago:
            db.session.add(modalidad)
        
        # Crear empleados de ejemplo
        print("Creando empleados...")
        from app import Empleado
        empleados = [
            Empleado(
                nombre='Juan Pérez',
                tipo_documento='Cédula',
                cedula='00112345678',
                numero_documento='00112345678',
                telefono='809-555-0101',
                email='juan.perez@unapec.edu.do',
                tanda_labor='Matutina',
                fecha_ingreso=datetime(2020, 1, 15),
                estado='Activo'
            ),
            Empleado(
                nombre='María García',
                tipo_documento='Cédula',
                cedula='00112345679',
                numero_documento='00112345679',
                telefono='809-555-0102',
                email='maria.garcia@unapec.edu.do',
                tanda_labor='Vespertina',
                fecha_ingreso=datetime(2021, 3, 20),
                estado='Activo'
            )
        ]
        for empleado in empleados:
            db.session.add(empleado)
        
        # Crear clientes de ejemplo
        print("Creando clientes...")
        from app import Cliente
        clientes = [
            Cliente(
                nombre='Carlos Rodríguez',
                tipo_documento='Cédula',
                numero_documento='00112345680',
                telefono='809-555-0103',
                email='carlos@email.com',
                tipo_cliente='Estudiante',
                carrera='Ingeniería de Software',
                estado='Activo'
            ),
            Cliente(
                nombre='Ana Martínez',
                tipo_documento='Pasaporte',
                numero_documento='AB123456',
                telefono='809-555-0104',
                email='ana@email.com',
                tipo_cliente='Estudiante',
                carrera='Administración',
                estado='Activo'
            )
        ]
        for cliente in clientes:
            db.session.add(cliente)
        
        # Actualizar password del admin con hash real
        from werkzeug.security import generate_password_hash
        admin_user.password = generate_password_hash('admin123')
        
        db.session.commit()
        print("✅ Base de datos resetada exitosamente!")
        print("📊 Datos iniciales creados:")
        print(f"   - {len(roles)} roles")
        print(f"   - {len(tipos_documento)} tipos de documento")
        print(f"   - {len(servicios)} servicios")
        print(f"   - {len(formas_pago)} formas de pago")
        print(f"   - {len(modalidades_pago)} modalidades de pago")
        print(f"   - {len(empleados)} empleados")
        print(f"   - {len(clientes)} clientes")
        print("🔑 Usuario admin: admin / admin123")

if __name__ == '__main__':
    reset_database()