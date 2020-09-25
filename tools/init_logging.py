# -*- coding: utf-8 -*-
"""
This module defines helper classes for logging initialisation
"""
import logging.config

import yaml


def load_logging_configuration(logging_config_file_name):
    """
    Load the logging configuration from a file
    Args:
        logging_config_file_namee (str): the name of a YAML config file
    """
    print("====== loading logging configuration {0}".format(logging_config_file_name))
    try:
        with open(logging_config_file_name, 'r') as logging_config_file:
            logging_config = yaml.safe_load(logging_config_file)
            logging.config.dictConfig(logging_config)
        #fileConfig(logging_config_file, disable_existing_loggers=False)
    except Exception as err:
        print("logger not initialized - file {0}".format(logging_config_file))
        message = 'Logging initialisation failed - file:%s reason:%s'
        raise Exception(message, logging_config_file, str(err))
    print("====== logging configuration loaded from {0}".format(logging_config_file))
