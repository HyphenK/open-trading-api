"""
Logging setup for Samsung auto trader.
"""
import logging
import sys
from datetime import datetime
import config

class KSTFormatter(logging.Formatter):
    """Custom formatter that uses KST timezone."""
    
    def formatTime(self, record, datefmt=None):
        """Format time in KST."""
        ct = datetime.fromtimestamp(record.created, tz=config.KST)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime("%Y-%m-%d %H:%M:%S")
        return s

def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with both file and console handlers.
    
    Args:
        name: logger name
        
    Returns:
        configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)
    
    # Formatter with KST
    formatter = KSTFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create logger."""
    return logging.getLogger(name)
