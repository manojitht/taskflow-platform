from . import models  # noqa: F401  (registers the tables)
from .db import Base, engine


def main():
    Base.metadata.create_all(engine)
    print("Database tables ready")


if __name__ == "__main__":
    main()