from stock_research.config.settings import Settings
from stock_research.db.session import build_engine, init_db


def main() -> None:
    engine = build_engine(Settings().database_url)
    try:
        init_db(engine)
        print("Database initialized successfully.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
