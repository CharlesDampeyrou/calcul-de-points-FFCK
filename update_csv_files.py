import logging

from data_handling.scrapper_sync import Scrappeur

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrapper = Scrappeur()
    scrapper.update_csv_database()