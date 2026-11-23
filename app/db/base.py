"""
Módulo base para la definición de modelos ORM con SQLAlchemy v2.
Proporciona la clase DeclarativeBase que heredan todas las entidades.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base declarativa para la creación de tablas en la base de datos."""
    
    pass
