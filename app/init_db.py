from database import Base, engine
from models import User, Event, EventPermission, EventVersion, Changelog, EventConflict, TokenBlacklist

def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!") 