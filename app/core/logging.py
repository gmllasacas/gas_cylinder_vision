import logging
import sys

class SuppressNoTracksFilter(logging.Filter):
    """Filters out noisy 'No tracks found' warnings from Ultralytics."""
    def filter(self, record: logging.LogRecord) -> bool:
        return "No tracks found" not in record.getMessage()

def setup_logger(name: str = "gas_stream", level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a standardized application logger."""
    # Suppress noisy Ultralytics warnings
    ultra_logger = logging.getLogger("ultralytics")
    ultra_filter = SuppressNoTracksFilter()
    ultra_logger.addFilter(ultra_filter)
    for h in ultra_logger.handlers:
        h.addFilter(ultra_filter)
    ultra_logger.setLevel(logging.ERROR)

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()

