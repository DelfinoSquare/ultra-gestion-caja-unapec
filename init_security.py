from app import app, db, Usuario, Rol, Empleado
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_security():
    with app.app_context():
        # Crear roles
        roles = [
            Rol(nombre='ADMIN', descripcion='Administrador del sistema con acceso completo'),
            Rol(nombre='GERENTE', descripcion='Gerente con acceso a reportes y administración'),
            Rol(nombre='CAJERO', descripcion='Cajero con acceso a movimientos'),
            Rol(nombre='CONSULTA', descripcion='Usuario de solo consulta y reportes')
        ]
        
        for rol in roles:
            if not Rol.query.filter_by(nombre=rol.nombre).first():
                db.session.add(rol)
        
        db.session.commit()
        
        # Crear usuario admin por defecto
        if not Usuario.query.filter_by(username='admin').first():
            admin_rol = Rol.query.filter_by(nombre='ADMIN').first()
            admin_user = Usuario(
                username='admin',
                password=generate_password_hash('admin123'),
                email='admin@unapec.edu.do',
                rol_id=admin_rol.id,
                estado='Activo'
            )
            db.session.add(admin_user)
        
        db.session.commit()
        print("Sistema de seguridad inicializado correctamente!")
        print("Usuario por defecto: admin / admin123")

if __name__ == '__main__':
    init_security()