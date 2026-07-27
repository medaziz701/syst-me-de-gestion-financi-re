import sqlite3
import os

def connecter():
    """Établit une connexion à la base de données"""
    return sqlite3.connect('data.db')

def initialiser_bdd():
    """Initialise toutes les tables nécessaires avec leurs relations"""
    conn = connecter()
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = OFF')
    schemas = ["CREATE TABLE IF NOT EXISTS etablissement (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            nom TEXT NOT NULL,\n            adresse TEXT,\n            code_postal TEXT,\n            ville TEXT,\n            pays TEXT DEFAULT 'Maroc',\n            telephone TEXT,\n            email TEXT,\n            registre_commerce TEXT,\n            identifiant_fiscal TEXT,\n            cnss TEXT,\n            ice TEXT,\n            logo_path TEXT,\n            date_creation TEXT\n        )", "CREATE TABLE IF NOT EXISTS utilisateurs (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            nom TEXT NOT NULL,\n            email TEXT UNIQUE NOT NULL,\n            mot_de_passe TEXT NOT NULL,\n            role TEXT DEFAULT 'utilisateur'\n        )", 'CREATE TABLE IF NOT EXISTS clients (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            nom TEXT NOT NULL,\n            email TEXT,\n            telephone TEXT,\n            adresse TEXT,\n            identifiant_fiscal TEXT,\n            solde_credit REAL DEFAULT 0\n        )', 'CREATE TABLE IF NOT EXISTS fournisseurs (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            nom TEXT NOT NULL,\n            email TEXT,\n            telephone TEXT,\n            adresse TEXT\n        )', 'CREATE TABLE IF NOT EXISTS bon_livraison (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            date TEXT,\n            code_fournisseur TEXT,\n            nom_fournisseur TEXT,\n            id_produit INTEGER,\n            nom_produit TEXT,\n            quantite INTEGER,\n            prix_unitaire REAL,\n            remise REAL,\n            total REAL\n        )', 'CREATE TABLE IF NOT EXISTS ventes (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            produit_id INTEGER,\n            client_id INTEGER,\n            quantite INTEGER,\n            date TEXT,\n            total REAL,\n            FOREIGN KEY(produit_id) REFERENCES articles(code),\n            FOREIGN KEY(client_id) REFERENCES clients(id)\n        )']
    for schema in schemas:
        try:
            cur.execute(schema)
        except sqlite3.Error as e:
            print(f'Erreur création table: {e}')
    cur.execute('PRAGMA foreign_keys = ON')
    conn.commit()
    conn.close()

def creer_etablissement(nom, adresse, code_postal, ville, telephone, email, identifiant_fiscal='', logo_path=None, **kwargs):
    """Crée un nouvel établissement dans la base de données"""
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM etablissement')
        cur.execute("\n            INSERT INTO etablissement (\n                nom, adresse, code_postal, ville, telephone, email, \n                identifiant_fiscal, logo_path, date_creation\n            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, date('now'))\n        ", (nom, adresse, code_postal, ville, telephone, email, identifiant_fiscal, logo_path))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Erreur lors de la création de l'établissement: {e}")
        return None
    finally:
        conn.close()

def get_etablissement():
    """Récupère les informations de l'établissement sous forme de dict.
    Clés: id, nom, adresse, code_postal, ville, telephone, email, pays,
          date_creation, identifiant_fiscal, logo_path
    """
    conn = connecter()
    try:
        import sqlite3 as _sqlite3
        conn.row_factory = _sqlite3.Row
        cur = conn.cursor()
        cur.execute('\n            SELECT \n                id, nom, adresse, code_postal, ville, telephone, email, \n                pays, date_creation, identifiant_fiscal, logo_path\n            FROM etablissement \n            LIMIT 1\n            ')
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Erreur lors de la récupération de l'établissement: {e}")
        return None
    finally:
        conn.close()

def verifier_et_mettre_a_jour_schema():
    """Vérifie et met à jour le schéma de la base de données"""
    conn = connecter()
    cur = conn.cursor()
    try:
        tables_requises = {'clients', 'articles', 'fournisseurs', 'ventes'}
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_existantes = {row[0] for row in cur.fetchall()}
        if not tables_requises.issubset(tables_existantes):
            print('Tables manquantes, recréation de la base...')
            conn.close()
            os.remove('data.db')
            initialiser_bdd()
            return
        cur.execute('PRAGMA table_info(clients)')
        colonnes_clients = [col[1] for col in cur.fetchall()]
        for col in ('adresse', 'identifiant_fiscal', 'solde_credit'):
            if col not in colonnes_clients:
                print(f'Ajout de la colonne {col} à la table clients...')
                cur.execute(f'ALTER TABLE clients ADD COLUMN {col} TEXT')
        cur.execute('PRAGMA table_info(ventes)')
        colonnes_ventes = [col[1] for col in cur.fetchall()]
        if 'total' not in colonnes_ventes:
            print('Ajout de la colonne total à la table ventes...')
            cur.execute('ALTER TABLE ventes ADD COLUMN total REAL')
            cur.execute('\n                UPDATE ventes \n                SET total = (\n                    SELECT a.prix_vente * ventes.quantite \n                    FROM articles a \n                    WHERE a.code = ventes.produit_id\n                )\n                WHERE total IS NULL\n            ')
            conn.commit()
            print('Mise à jour du schéma terminée')
    except sqlite3.Error as e:
        print(f'Erreur lors de la vérification: {e}')
    finally:
        conn.close()
if __name__ == '__main__':
    if not os.path.exists('data.db'):
        print("Création d'une nouvelle base de données...")
        initialiser_bdd()
    else:
        print('Vérification du schéma existant...')
        verifier_et_mettre_a_jour_schema()