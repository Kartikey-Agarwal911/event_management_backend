from sqlalchemy.orm import Session
from contextlib import contextmanager
from typing import Generator
import logging

logger = logging.getLogger(__name__)

@contextmanager
def transaction(db: Session) -> Generator[Session, None, None]:
    """
    Context manager for database transactions.
    Ensures atomic operations by rolling back on error.
    """
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed: {str(e)}")
        raise
    finally:
        db.close()

def atomic_operation(db: Session, operation_func):
    """
    Decorator for atomic database operations.
    Usage:
        @atomic_operation(db)
        def create_event(event_data):
            # Your operation here
            pass
    """
    def wrapper(*args, **kwargs):
        with transaction(db):
            return operation_func(*args, **kwargs)
    return wrapper 