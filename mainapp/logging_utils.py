import os
import logging
from datetime import datetime


def create_log_file():
    """
    Create log file in 'logs' directory with current date and time.
    Return full name of created file.
    """
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    

    current_time = datetime.now()
    log_filename = current_time.strftime("%Y-%m-%d_%H-%M-%S.log")
    log_filepath = os.path.join(logs_dir, log_filename)
    

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'), #Log into file
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Log file created: {log_filename}")
    
    return log_filename


def get_logger(name=None):
    """
    return logger
    """
    return logging.getLogger(name or __name__)

def log_item(*values):
    """
    Accept any amount of values, convert them to strings and log as combined string with current timestamp.
    Format: [YYYY-MM-DD HH:MM:SS] Log message
    Uses existing logging configuration from create_log_file().
    """
    # Convert all values to strings and join them with spaces
    message = " ".join(str(value) for value in values)
    
    # Get current timestamp
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the log entry with timestamp in square brackets
    log_entry = f"[{timestamp}] {message}"
    
    # Get logger and log the message
    # This will append to the log file that was configured by create_log_file()
    logger = get_logger()
    logger.info(log_entry)
