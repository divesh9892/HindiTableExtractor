import logging
import os

def setup_logger(name="HindiExtractor", log_file="app.log"):
    """Sets up a robust enterprise logger."""
    logger = logging.getLogger(name)
    
    # Only configure if it doesn't already have handlers to prevent duplicate logs
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        
        # Console Handler (Prints to terminal)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File Handler (Saves to file)
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger

# Create a global logger instance to be imported by other files
log = setup_logger()