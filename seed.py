from app.database import init_database, reset_database, seed_database


if __name__ == "__main__":
    reset_database()
    init_database()
    seed_database()
    print("Banco recriado com sucesso em data/eventos.db")

