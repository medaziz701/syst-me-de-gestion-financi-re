import sqlite3
import os

def check_database():
    db_path = 'data.db'
    if not os.path.exists(db_path):
        print(f"Erreur: Le fichier {db_path} n'existe pas dans le répertoire courant.")
        print(f'Répertoire courant: {os.getcwd()}')
        return
    size = os.path.getsize(db_path)
    print(f'Taille de la base de données: {size} octets')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if not tables:
            print('Aucune table trouvée dans la base de données.')
            return
        print('\nTables trouvées dans la base de données:')
        for table in tables:
            table_name = table[0]
            print(f'\n--- Table: {table_name} ---')
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                print(f"Nombre d'entrées: {count}")
                if count > 0:
                    cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
                    rows = cursor.fetchall()
                    cursor.execute(f'PRAGMA table_info({table_name})')
                    columns = [col[1] for col in cursor.fetchall()]
                    print('Colonnes:', ', '.join(columns))
                    print('Premières lignes:')
                    for row in rows:
                        print(row)
            except sqlite3.Error as e:
                print(f"Erreur lors de l'accès à la table {table_name}: {e}")
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        if os.path.exists(backup_dir):
            print('\nSauvegardes disponibles:')
            for file in os.listdir(backup_dir):
                if file.endswith('.db') or file.endswith('.backup'):
                    path = os.path.join(backup_dir, file)
                    print(f'- {file} ({os.path.getsize(path)} octets, modifié le {os.path.getmtime(path)})')
    except sqlite3.Error as e:
        print(f'Erreur SQLite: {e}')
    finally:
        if 'conn' in locals():
            conn.close()
if __name__ == '__main__':
    print(f"Vérification de la base de données dans: {os.path.abspath('data.db')}")
    check_database()