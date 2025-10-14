import os
from app import app, db

with app.app_context():
    # Eliminar todas las tablas
    db.drop_all()
    # Crear todas las tablas con la nueva estructura
    db.create_all()
    print("Base de datos resetead exitosamente!")

if __name__ == '__main__':
    # Buscar y eliminar el archivo de la base de datos
    if os.path.exists('caja_unapec.db'):
        os.remove('caja_unapec.db')
        print("Archivo de base de datos eliminado")