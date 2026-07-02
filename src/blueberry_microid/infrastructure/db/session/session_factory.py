from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to `engine`.

    `expire_on_commit=False` so DTOs/entities can be built from ORM objects
    right after a repository commits, without triggering a second SELECT.
    """

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
