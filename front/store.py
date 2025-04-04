class ServiceStorage:
    def __init__(self):
        self.services = {}

    def add_db_service(self, db_service):
        self.services["db_service"] = db_service

    def get_db_service(self):
        return self.services.get("db_service")


services = ServiceStorage()
