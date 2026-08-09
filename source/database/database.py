#base de camiones: guarda únicamente los ids de los camiones registrados
truck_db = {}

#base donde se guarda la ubicación actual de cada camión -> {truck_id: Location}
current_location_db = {}

#listado histórico de ubicaciones de cada camion (a futuro, con timestamp)
history_db = []