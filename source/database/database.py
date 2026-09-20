from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from source.database.config import settings

# engine que administra la conexión y comunicación con la base de datos
engine = create_engine(settings.database_url)

# fábrica utilizada para crear nuevas sesiones de conexión con la base de datos
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    trucks_db = SessionLocal()
    try:
        yield trucks_db
    finally:
        trucks_db.close()

#base de camiones: guarda únicamente los ids de los camiones registrados
truck_db = {}

#base donde se guarda la ubicación actual de cada camión -> {truck_id: Location}
current_location_db = {}

#listado histórico de ubicaciones de cada camion (a futuro, con timestamp)
history_db = []


