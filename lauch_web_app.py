from front.app import app
from front.store import services
from data_handling.database_service import DatabaseService

if __name__ == "__main__":
    services.add_db_service(DatabaseService())
    app.run_server(debug=True)
