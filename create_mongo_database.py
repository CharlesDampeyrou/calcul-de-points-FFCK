# -*- coding: utf-8 -*-
"""
Created on Tue Dec  7 10:08:56 2021

@author: charl
"""

from tools.init_logging import load_logging_configuration
from data_handling.csv_data_service import CsvDataService
from data_handling.database_management_service import DatabaseManagementService

if __name__ == "__main__":
    load_logging_configuration("tools/logging.yml")
    csv_data_service = CsvDataService()
    db_management_service = DatabaseManagementService()
    
    db_management_service.create_indexes() #Insertions plus rapides si les indexes sont déjà créés
    csv_data_service.save_csv_files_in_database()
    db_management_service.clean_database()
    
