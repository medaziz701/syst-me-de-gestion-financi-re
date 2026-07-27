import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database import connecter
from datetime import datetime
import sqlite3
import random
import string
import os
import json

def add_to_pending_file(client_id: int, items: list[dict], avance: float | None=None, total: float | None=None) -> bool:
    try:
        if client_id is None:
            return False
        cleaned = []
        for it in items or []:
            try:
                cleaned.append({'id': it.get('id'), 'nom': it.get('nom'), 'quantite': float(it.get('quantite') or 0), 'prix': float(it.get('prix') or 0), 'remise_pct': float(it.get('remise_pct') or 0)})
            except Exception:
                continue
        base = os.path.dirname(__file__) if '__file__' in globals() else os.getcwd()
        fp = os.path.join(base, 'pending_state.json')
        data = {}
        if os.path.exists(fp):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
        key = str(int(client_id))
        existing = data.get(key)
        if isinstance(existing, list):
            existing = {'items': existing, 'info': {}}
        elif not isinstance(existing, dict) or 'items' not in (existing or {}):
            existing = {'items': [], 'info': {}}
        existing['items'].extend(cleaned)
        try:
            if avance is not None:
                av = float(avance)
                ttl = float(total or 0)
                reste = max(0.0, ttl - av) if ttl else None
                existing['info'] = {'avance': av, 'reste': reste if reste is not None else None, 'updated_at': datetime.now().isoformat(timespec='seconds')}
        except Exception:
            pass
        data[key] = existing
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
_LAST_SALES_VIEW = {'tree': None, 'total_label': None, 'date_getter': None}

def fmt_money(val) -> str:
    try:
        if val is None:
            num = 0.0
        elif isinstance(val, (int, float)):
            num = float(val)
        else:
            num = float(str(val).replace(' ', '').replace(',', '.'))
    except Exception:
        num = 0.0
    if abs(num - round(num)) < 1e-09:
        s = f'{int(round(num)):,}'.replace(',', ' ')
    else:
        s = f'{num:,.3f}'.rstrip('0').rstrip('.')
        s = s.replace(',', ' ').replace('.', ',')
    return s

def _normalize_nom(s: str) -> str:
    """Normalise un nom d'article pour comparaison:
    - trim
    - casse insensible (lower)
    - supprime espaces, tirets et underscores pour la comparaison
    - compacte les espaces multiples
    """
    if not isinstance(s, str):
        return ''
    s2 = ' '.join(s.strip().split())
    s2 = s2.lower()
    return s2.replace(' ', '').replace('-', '').replace('_', '')

def _generate_unique_article_code(prefix: str='A', length: int=6) -> str:
    """Génère un code aléatoire unique pour un article (non présent dans la table articles).
    Format par défaut: 'A' + 6 caractères alphanumériques.
    """
    chars = string.ascii_uppercase + string.digits
    attempt = 0
    while True:
        attempt += 1
        candidate = prefix + ''.join((random.choice(chars) for _ in range(length)))
        try:
            with connecter() as conn:
                cur = conn.cursor()
                cur.execute('SELECT 1 FROM articles WHERE code = ?', (candidate,))
                if cur.fetchone() is None:
                    return candidate
        except Exception:
            return candidate
        if attempt > 1000:
            return candidate

def _ensure_ventes_statut_schema():
    """Assure la présence de la colonne statut dans la table ventes."""
    try:
        conn = connecter()
        cur = conn.cursor()
        cur.execute('PRAGMA table_info(ventes)')
        cols = [r[1] for r in cur.fetchall()]
        if 'statut' not in cols:
            try:
                cur.execute("ALTER TABLE ventes ADD COLUMN statut TEXT DEFAULT 'payee'")
                conn.commit()
            except Exception:
                pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def register_sales_view(tree, total_label, date_getter):
    """Enregistre les widgets de la vue des ventes courante afin de pouvoir
    déclencher un rafraîchissement depuis d'autres modules (ex: facture).
    """
    global _LAST_SALES_VIEW
    _LAST_SALES_VIEW['tree'] = tree
    _LAST_SALES_VIEW['total_label'] = total_label
    _LAST_SALES_VIEW['date_getter'] = date_getter

def refresh_sales_view():
    """Rafraîchit la liste des ventes si une vue est enregistrée et toujours valide."""
    try:
        tree = _LAST_SALES_VIEW.get('tree')
        total_label = _LAST_SALES_VIEW.get('total_label')
        date_getter = _LAST_SALES_VIEW.get('date_getter')
        if tree is None or total_label is None:
            return
        date_filter = None
        if callable(date_getter):
            try:
                date_filter = date_getter()
            except Exception:
                date_filter = None
        afficher_ventes_et_total(tree, total_label, date_filter)
    except Exception:
        pass

def ensure_categories_schema():
    try:
        conn = connecter()
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT UNIQUE NOT NULL)')
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def ensure_article_category_schema():
    try:
        conn = connecter()
        cur = conn.cursor()
        cur.execute('PRAGMA table_info(articles)')
        cols = [r[1] for r in cur.fetchall()]
        if 'categorie' not in cols:
            try:
                cur.execute('ALTER TABLE articles ADD COLUMN categorie TEXT')
                conn.commit()
            except Exception:
                pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def list_categories():
    ensure_categories_schema()
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('SELECT nom FROM categories ORDER BY nom ASC')
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

def _ensure_reglement_table(cur: sqlite3.Cursor):
    try:
        cur.execute('\n            CREATE TABLE IF NOT EXISTS reglement_client (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                client_id INTEGER,\n                date TEXT,\n                montant REAL\n            )\n            ')
    except Exception:
        pass

def _enregistrer_avance_client(client_id: int, date_iso: str, montant: float):
    if not client_id or not montant or montant <= 0:
        return
    try:
        with connecter() as conn:
            cur = conn.cursor()
            _ensure_reglement_table(cur)
            cur.execute('INSERT INTO reglement_client (client_id, date, montant) VALUES (?,?,?)', (int(client_id), date_iso, float(montant)))
            conn.commit()
    except Exception:
        pass

def add_category(nom):
    if not nom:
        return
    ensure_categories_schema()
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR IGNORE INTO categories (nom) VALUES (?)', (nom.strip(),))
        conn.commit()
    finally:
        conn.close()

def ajouter_vente(article_code, client_id, quantite, refresh_callback, date_for_list: str | None=None, silent: bool=False, statut: str='payee', total_override: float | None=None):
    conn = None
    try:
        conn = connecter()
        cur = conn.cursor()
        try:
            cur.execute('PRAGMA table_info(ventes)')
            cols = [r[1] for r in cur.fetchall()]
            if 'statut' not in cols:
                try:
                    cur.execute("ALTER TABLE ventes ADD COLUMN statut TEXT DEFAULT 'payee'")
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass
        cur.execute('SELECT prix_vente, quantite FROM articles WHERE code = ?', (article_code,))
        prix_vente, stock = cur.fetchone()
        if quantite <= 0:
            raise ValueError('Quantité doit être positive')
        if quantite > stock:
            raise ValueError(f'Stock insuffisant. Disponible: {stock}')
        if total_override is not None:
            try:
                total = float(total_override)
            except Exception:
                total = prix_vente * quantite
        else:
            total = prix_vente * quantite
        if date_for_list:
            date_val = f"{date_for_list} {datetime.now().strftime('%H:%M:%S')}"
        else:
            date_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute('INSERT INTO ventes \n               (produit_id, client_id, quantite, date, total, statut) \n               VALUES (?, ?, ?, ?, ?, ?)', (article_code, client_id, quantite, date_val, total, statut))
        cur.execute('UPDATE articles SET quantite = quantite - ? WHERE code = ?', (quantite, article_code))
        conn.commit()
        try:
            refresh_callback()
        except Exception:
            pass
    except Exception as e:
        messagebox.showerror('Erreur', str(e))
    finally:
        if conn:
            conn.close()
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database import connecter
from datetime import datetime
import sqlite3
import random
import string
import os
import json

def add_to_pending_file(client_id: int, items: list[dict], avance: float | None=None, total: float | None=None) -> bool:
    try:
        if client_id is None:
            return False
        cleaned = []
        for it in items or []:
            try:
                cleaned.append({'id': it.get('id'), 'nom': it.get('nom'), 'quantite': float(it.get('quantite') or 0), 'prix': float(it.get('prix') or 0), 'remise_pct': float(it.get('remise_pct') or 0)})
            except Exception:
                continue
        base = os.path.dirname(__file__) if '__file__' in globals() else os.getcwd()
        fp = os.path.join(base, 'pending_state.json')
        data = {}
        if os.path.exists(fp):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
        key = str(int(client_id))
        existing = data.get(key)
        if isinstance(existing, list):
            existing = {'items': existing, 'info': {}}
        elif not isinstance(existing, dict) or 'items' not in (existing or {}):
            existing = {'items': [], 'info': {}}
        existing['items'].extend(cleaned)
        try:
            if avance is not None:
                av = float(avance)
                ttl = float(total or 0)
                reste = max(0.0, ttl - av) if ttl else None
                existing['info'] = {'avance': av, 'reste': reste if reste is not None else None, 'updated_at': datetime.now().isoformat(timespec='seconds')}
        except Exception:
            pass
        data[key] = existing
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
_LAST_SALES_VIEW = {'tree': None, 'total_label': None, 'date_getter': None}

def fmt_money(val) -> str:
    try:
        if val is None:
            num = 0.0
        elif isinstance(val, (int, float)):
            num = float(val)
        else:
            num = float(str(val).replace(' ', '').replace(',', '.'))
    except Exception:
        num = 0.0
    if abs(num - round(num)) < 1e-09:
        s = f'{int(round(num)):,}'.replace(',', ' ')
    else:
        s = f'{num:,.3f}'.rstrip('0').rstrip('.')
        s = s.replace(',', ' ').replace('.', ',')
    return s

def _normalize_nom(s: str) -> str:
    """Normalise un nom d'article pour comparaison:
    - trim
    - casse insensible (lower)
    - supprime espaces, tirets et underscores pour la comparaison
    - compacte les espaces multiples
    """
    if not isinstance(s, str):
        return ''
    s2 = ' '.join(s.strip().split())
    s2 = s2.lower()
    return s2.replace(' ', '').replace('-', '').replace('_', '')

def _generate_unique_article_code(prefix: str='A', length: int=6) -> str:
    """Génère un code aléatoire unique pour un article (non présent dans la table articles).
    Format par défaut: 'A' + 6 caractères alphanumériques.
    """
    chars = string.ascii_uppercase + string.digits
    attempt = 0
    while True:
        attempt += 1
        candidate = prefix + ''.join((random.choice(chars) for _ in range(length)))
        try:
            with connecter() as conn:
                cur = conn.cursor()
                cur.execute('SELECT 1 FROM articles WHERE code = ?', (candidate,))
                if cur.fetchone() is None:
                    return candidate
        except Exception:
            return candidate
        if attempt > 1000:
            return candidate

def _ensure_ventes_statut_schema():
    """Assure la présence de la colonne statut dans la table ventes."""
    try:
        conn = connecter()
        cur = conn.cursor()
        cur.execute('PRAGMA table_info(ventes)')
        cols = [r[1] for r in cur.fetchall()]
        if 'statut' not in cols:
            try:
                cur.execute("ALTER TABLE ventes ADD COLUMN statut TEXT DEFAULT 'payee'")
                conn.commit()
            except Exception:
                pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def register_sales_view(tree, total_label, date_getter):
    """Enregistre les widgets de la vue des ventes courante afin de pouvoir
    déclencher un rafraîchissement depuis d'autres modules (ex: facture).
    """
    global _LAST_SALES_VIEW
    _LAST_SALES_VIEW['tree'] = tree
    _LAST_SALES_VIEW['total_label'] = total_label
    _LAST_SALES_VIEW['date_getter'] = date_getter

def refresh_sales_view():
    """Rafraîchit la liste des ventes si une vue est enregistrée et toujours valide."""
    try:
        tree = _LAST_SALES_VIEW.get('tree')
        total_label = _LAST_SALES_VIEW.get('total_label')
        date_getter = _LAST_SALES_VIEW.get('date_getter')
        if tree is None or total_label is None:
            return
        date_filter = None
        if callable(date_getter):
            try:
                date_filter = date_getter()
            except Exception:
                date_filter = None
        afficher_ventes_et_total(tree, total_label, date_filter)
    except Exception:
        pass

def ensure_categories_schema():
    try:
        conn = connecter()
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT UNIQUE NOT NULL)')
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def ensure_article_category_schema():
    try:
        conn = connecter()
        cur = conn.cursor()
        cur.execute('PRAGMA table_info(articles)')
        cols = [r[1] for r in cur.fetchall()]
        if 'categorie' not in cols:
            try:
                cur.execute('ALTER TABLE articles ADD COLUMN categorie TEXT')
                conn.commit()
            except Exception:
                pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def list_categories():
    ensure_categories_schema()
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('SELECT nom FROM categories ORDER BY nom ASC')
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

def _ensure_reglement_table(cur: sqlite3.Cursor):
    try:
        cur.execute('\n            CREATE TABLE IF NOT EXISTS reglement_client (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                client_id INTEGER,\n                date TEXT,\n                montant REAL\n            )\n            ')
    except Exception:
        pass

def _enregistrer_avance_client(client_id: int, date_iso: str, montant: float):
    if not client_id or not montant or montant <= 0:
        return
    try:
        with connecter() as conn:
            cur = conn.cursor()
            _ensure_reglement_table(cur)
            cur.execute('INSERT INTO reglement_client (client_id, date, montant) VALUES (?,?,?)', (int(client_id), date_iso, float(montant)))
            conn.commit()
    except Exception:
        pass

def add_category(nom):
    if not nom:
        return
    ensure_categories_schema()
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR IGNORE INTO categories (nom) VALUES (?)', (nom.strip(),))
        conn.commit()
    finally:
        conn.close()

def ajouter_vente(article_code, client_id, quantite, refresh_callback, date_for_list: str | None=None, silent: bool=False, statut: str='payee', total_override: float | None=None):
    conn = None
    try:
        conn = connecter()
        cur = conn.cursor()
        try:
            cur.execute('PRAGMA table_info(ventes)')
            cols = [r[1] for r in cur.fetchall()]
            if 'statut' not in cols:
                try:
                    cur.execute("ALTER TABLE ventes ADD COLUMN statut TEXT DEFAULT 'payee'")
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass
        cur.execute('SELECT prix_vente, quantite FROM articles WHERE code = ?', (article_code,))
        prix_vente, stock = cur.fetchone()
        if quantite <= 0:
            raise ValueError('Quantité doit être positive')
        if quantite > stock:
            raise ValueError(f'Stock insuffisant. Disponible: {stock}')
        if total_override is not None:
            try:
                total = float(total_override)
            except Exception:
                total = prix_vente * quantite
        else:
            total = prix_vente * quantite
        if date_for_list:
            date_val = f"{date_for_list} {datetime.now().strftime('%H:%M:%S')}"
        else:
            date_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute('INSERT INTO ventes \n               (produit_id, client_id, quantite, date, total, statut) \n               VALUES (?, ?, ?, ?, ?, ?)', (article_code, client_id, quantite, date_val, total, statut))
        cur.execute('UPDATE articles SET quantite = quantite - ? WHERE code = ?', (quantite, article_code))
        conn.commit()
        try:
            refresh_callback()
        except Exception:
            pass
    except Exception as e:
        messagebox.showerror('Erreur', str(e))
    finally:
        if conn:
            conn.close()

def afficher_ventes_et_total(tree, total_label, date_filter: str | None=None):

    def _to_float(x):
        try:
            if x is None:
                return 0.0
            if isinstance(x, (int, float)):
                return float(x)
            return float(str(x).replace(' ', '').replace(',', '.'))
        except Exception:
            return 0.0
    for row in tree.get_children():
        tree.delete(row)
    conn = connecter()
    cur = conn.cursor()
    if date_filter:
        cur.execute("\n            SELECT v.id,\n                   a.nom,\n                   COALESCE(c.nom, 'Sans client') AS client_nom,\n                   v.quantite,\n                   a.prix_vente,\n                   a.prix_unitaire,\n                   (v.quantite * a.prix_vente) AS total,\n                   v.date,\n                   COALESCE(v.statut, 'payee') AS statut,\n                   COALESCE(a.categorie, '') AS categorie\n            FROM ventes v\n            JOIN articles a ON v.produit_id = a.code\n            LEFT JOIN clients c ON v.client_id = c.id\n            WHERE v.date LIKE ?\n            ORDER BY v.date DESC\n            ", (f'{date_filter}%',))
    else:
        cur.execute("\n            SELECT v.id,\n                   a.nom,\n                   COALESCE(c.nom, 'Sans client') AS client_nom,\n                   v.quantite,\n                   a.prix_vente,\n                   a.prix_unitaire,\n                   (v.quantite * a.prix_vente) AS total,\n                   v.date,\n                   COALESCE(v.statut, 'payee') AS statut,\n                   COALESCE(a.categorie, '') AS categorie\n            FROM ventes v\n            JOIN articles a ON v.produit_id = a.code\n            LEFT JOIN clients c ON v.client_id = c.id\n            ORDER BY v.date DESC\n            ")
    ventes = cur.fetchall()
    total_general = 0.0
    total_ciment = 0.0
    total_autre = 0.0
    for i, row in enumerate(ventes):
        q_val = _to_float(row[3])
        pv_val = _to_float(row[4])
        pu_val = _to_float(row[5])
        total_val = _to_float(row[6])
        total_general += total_val
        if len(row) > 9 and row[9]:
            categorie_str = str(row[9]).strip().upper()
            if categorie_str == 'CIMENT':
                total_ciment += total_val
            else:
                total_autre += total_val
        else:
            total_autre += total_val
        total_formatted = fmt_money(total_val)
        prix_unit_formatted = fmt_money(pv_val)
        statut_val = row[8] or 'payee'
        statut_is_payee = statut_val == 'payee'
        if statut_val == 'payee':
            statut_label = 'Payée'
        elif statut_val == 'credit':
            statut_label = 'Crédit'
        elif statut_val == 'attente':
            statut_label = 'Attente'
        else:
            statut_label = statut_val.capitalize()
        marge_nette = q_val * (pv_val - pu_val) if statut_is_payee else 0.0
        marge_formatted = fmt_money(marge_nette)
        formatted_row = (row[0], row[1], row[2], q_val, prix_unit_formatted, total_formatted, marge_formatted, row[7], statut_label)
        tag = 'even' if i % 2 == 0 else 'odd'
        tree.insert('', 'end', values=formatted_row, tags=(tag,))
    txt = f'Total des ventes : {fmt_money(total_general)}   |   Ciment : {fmt_money(total_ciment)}   |   Autres : {fmt_money(total_autre)}'
    total_label.config(text=txt)
    conn.close()

def afficher_totaux_par_statut(date_filter: str | None) -> tuple[float, float]:
    """Retourne (total_payee, total_credit) pour la date (YYYY-MM-DD) donnée ou pour aujourd'hui si None."""
    conn = connecter()
    cur = conn.cursor()
    try:
        if not date_filter:
            date_filter = datetime.now().strftime('%Y-%m-%d')
        cur.execute("\n            SELECT\n                SUM(CASE WHEN COALESCE(statut,'payee') = 'payee' THEN COALESCE(total,0) ELSE 0 END) AS total_payee,\n                SUM(CASE WHEN COALESCE(statut,'payee') = 'credit' THEN COALESCE(total,0) ELSE 0 END) AS total_credit\n            FROM ventes\n            WHERE date LIKE ?\n            ", (f'{date_filter}%',))
        row = cur.fetchone() or (0.0, 0.0)
        return (row[0] or 0.0, row[1] or 0.0)
    finally:
        conn.close()

def get_produit_index_by_nom(nom_recherche, produits_list):
    for i, p in enumerate(produits_list):
        if p[1].lower() == nom_recherche.lower():
            return i
    return -1

def open_ventes_window():
    """Ouvre la fenêtre complète de gestion des ventes"""
    win = tk.Toplevel()
    win.title('Gestion des Ventes')
    win.geometry('1100x750')
    style = ttk.Style()
    style.configure('Treeview', rowheight=25, font=('Arial', 10))
    style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
    container = tk.Frame(win)
    container.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(container, highlightthickness=0)
    vscroll = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    vscroll.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    main_frame = tk.Frame(canvas, padx=15, pady=15)
    canvas_window = canvas.create_window((0, 0), window=main_frame, anchor='nw')

    def _on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox('all'))
        try:
            canvas.itemconfigure(canvas_window, width=canvas.winfo_width())
        except Exception:
            pass

    def _on_canvas_configure(event):
        try:
            canvas.itemconfigure(canvas_window, width=event.width)
        except Exception:
            pass
    main_frame.bind('<Configure>', _on_frame_configure)
    canvas.bind('<Configure>', _on_canvas_configure)

    def _on_mousewheel(event):
        canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')
    canvas.bind_all('<MouseWheel>', _on_mousewheel)
    _ensure_ventes_statut_schema()
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('SELECT code, nom, prix_vente, quantite FROM articles ORDER BY nom')
        produits = cur.fetchall()
        cur.execute('SELECT id, nom FROM clients ORDER BY nom')
        clients = cur.fetchall()
    except Exception as e:
        messagebox.showerror('Erreur', str(e))
        produits = []
        clients = []
    finally:
        conn.close()
    form_frame = tk.LabelFrame(main_frame, text='Nouvelle Vente', padx=10, pady=10)
    form_frame.pack(fill=tk.X, pady=(0, 15))
    articles_a_vendre = []
    produit_var = tk.StringVar()
    quantite_var = tk.StringVar()
    mode_var = tk.StringVar(value='Pièce')
    poids_val_var = tk.StringVar(value='')
    poids_unit_var = tk.StringVar(value='g')
    client_var = tk.StringVar()
    tk.Label(form_frame, text='Article:').grid(row=0, column=0, padx=5, pady=5)
    produit_entry = tk.Entry(form_frame, textvariable=produit_var, width=30)
    produit_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

    def open_article_picker():
        picker = tk.Toplevel(win)
        picker.title('Choisir un article')
        picker.geometry('700x500')
        frm = tk.Frame(picker, padx=10, pady=10)
        frm.pack(fill=tk.BOTH, expand=True)
        tk.Label(frm, text='Catégorie:').grid(row=0, column=0, sticky='e')
        cat_var2 = tk.StringVar(value='Toutes')
        try:
            cats = ['Toutes'] + list_categories()
        except Exception:
            cats = ['Toutes']
        cat_combo2 = ttk.Combobox(frm, textvariable=cat_var2, values=cats, width=30, state='readonly')
        cat_combo2.grid(row=0, column=1, sticky='w')
        tk.Label(frm, text='Recherche:').grid(row=0, column=2, padx=(10, 4))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(frm, textvariable=search_var, width=20)
        search_entry.grid(row=0, column=3, sticky='w')
        alpha_frame = tk.Frame(frm)
        alpha_frame.grid(row=1, column=0, columnspan=4, pady=(8, 6), sticky='w')

        def set_letter(l):
            nonlocal current_letter
            current_letter = l
            refresh_list()
        letters = ['Tous'] + [chr(ord('A') + i) for i in range(26)]
        current_letter = 'Tous'
        for i, l in enumerate(letters):
            tk.Button(alpha_frame, text=l, width=3, command=lambda x=l: set_letter(x)).grid(row=0, column=i, padx=1)
        tree2 = ttk.Treeview(frm, columns=('code', 'nom', 'categorie', 'prix_vente', 'stock'), show='headings', height=15)
        for c, w in [('code', 100), ('nom', 260), ('categorie', 130), ('prix_vente', 90), ('stock', 70)]:
            tree2.heading(c, text=c.capitalize())
            tree2.column(c, width=w)
        tree2.grid(row=2, column=0, columnspan=4, sticky='nsew')
        frm.rowconfigure(2, weight=1)
        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(3, weight=1)
        sb = ttk.Scrollbar(frm, orient='vertical', command=tree2.yview)
        sb.grid(row=2, column=4, sticky='ns')
        tree2.configure(yscrollcommand=sb.set)

        def refresh_list(*_):
            for iid in tree2.get_children():
                tree2.delete(iid)
            conn = connecter()
            cur = conn.cursor()
            try:
                try:
                    cur.execute('PRAGMA table_info(articles)')
                    cols = [r[1] for r in cur.fetchall()]
                    has_cat = 'categorie' in cols
                except Exception:
                    has_cat = False
                base = 'SELECT code, nom, prix_vente, quantite' + (', categorie' if has_cat else ', NULL as categorie') + ' FROM articles'
                where = []
                params = []
                if cat_var2.get() and cat_var2.get() != 'Toutes' and has_cat:
                    where.append('categorie = ?')
                    params.append(cat_var2.get())
                if current_letter and current_letter != 'Tous':
                    where.append('UPPER(SUBSTR(nom,1,1)) = ?')
                    params.append(current_letter)
                if search_var.get().strip():
                    where.append('LOWER(nom) LIKE ?')
                    params.append('%' + search_var.get().strip().lower() + '%')
                sql = base + (' WHERE ' + ' AND '.join(where) if where else '') + ' ORDER BY nom ASC'
                cur.execute(sql, tuple(params))
                for code, nom, prix_vente, stock, cat in cur.fetchall():
                    tree2.insert('', 'end', values=(code, nom, cat, prix_vente, stock))
            finally:
                conn.close()
        cat_combo2.bind('<<ComboboxSelected>>', refresh_list)
        search_entry.bind('<KeyRelease>', refresh_list)
        refresh_list()

        def choose_and_close(*_):
            sel = tree2.selection()
            if not sel:
                messagebox.showwarning('Sélection', 'Choisissez un article')
                return
            it = tree2.item(sel[0])
            vals = it.get('values', [])
            if not vals:
                return
            produit_var.set(vals[1])
            picker.destroy()
            produit_entry.focus_set()
        ttk.Button(frm, text='Valider', command=choose_and_close).grid(row=3, column=0, pady=8, sticky='w')
        tree2.bind('<Double-1>', choose_and_close)
    ttk.Button(form_frame, text='Choisir...', command=open_article_picker).grid(row=0, column=1, padx=(230, 0), sticky='w')
    tk.Label(form_frame, text='Quantité:').grid(row=0, column=2, padx=5, pady=5)
    quantite_entry = tk.Entry(form_frame, textvariable=quantite_var, width=8)
    quantite_entry.grid(row=0, column=3, padx=5, pady=5)
    tk.Label(form_frame, text='Mode:').grid(row=0, column=4, padx=5, pady=5)
    mode_combo = ttk.Combobox(form_frame, textvariable=mode_var, values=['Pièce', 'Poids'], state='readonly', width=8)
    mode_combo.grid(row=0, column=5, padx=5, pady=5)
    poids_frame = tk.Frame(form_frame)
    poids_frame.grid(row=0, column=6, padx=5, pady=5, sticky='w')
    poids_entry = tk.Entry(poids_frame, textvariable=poids_val_var, width=8, state='disabled')
    poids_entry.grid(row=0, column=0, padx=(0, 4))
    poids_unit_combo = ttk.Combobox(poids_frame, textvariable=poids_unit_var, values=['g', 'kg'], width=4, state='disabled')
    poids_unit_combo.grid(row=0, column=1)

    def _on_mode_change(*_):
        if mode_var.get() == 'Poids':
            quantite_entry.configure(state='disabled')
            poids_entry.configure(state='normal')
            poids_unit_combo.configure(state='readonly')
        else:
            quantite_entry.configure(state='normal')
            poids_entry.configure(state='disabled')
            poids_unit_combo.configure(state='disabled')
    mode_combo.bind('<<ComboboxSelected>>', _on_mode_change)
    _on_mode_change()
    tk.Label(form_frame, text='Client:').grid(row=1, column=0, padx=5, pady=5, sticky='e')
    client_combo = ttk.Combobox(form_frame, textvariable=client_var, values=[c[1] for c in clients], state='readonly', width=30, font=('Arial', 10))
    client_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='w')

    def open_client_picker():
        picker = tk.Toplevel(win)
        picker.title('Rechercher un client')
        picker.geometry('700x520')
        frm = tk.Frame(picker, padx=10, pady=10)
        frm.pack(fill=tk.BOTH, expand=True)
        tk.Label(frm, text='Recherche:').grid(row=0, column=0, sticky='e')
        search_var = tk.StringVar()
        search_entry = ttk.Entry(frm, textvariable=search_var, width=28)
        search_entry.grid(row=0, column=1, sticky='w')
        cols = ('id', 'nom', 'telephone', 'email')
        tree = ttk.Treeview(frm, columns=cols, show='headings', height=12)
        for c_name, w in [('id', 60), ('nom', 220), ('telephone', 140), ('email', 220)]:
            tree.heading(c_name, text=c_name.capitalize())
            tree.column(c_name, width=w, anchor='w')
        tree.grid(row=1, column=0, columnspan=4, sticky='nsew', pady=(8, 6))
        frm.rowconfigure(1, weight=1)
        frm.columnconfigure(1, weight=1)
        sb = ttk.Scrollbar(frm, orient='vertical', command=tree.yview)
        sb.grid(row=1, column=4, sticky='ns')
        tree.configure(yscrollcommand=sb.set)

        def load_clients(filter_text: str=''):
            for iid in tree.get_children():
                tree.delete(iid)
            conn = connecter()
            cur = conn.cursor()
            try:
                if filter_text.strip():
                    q = f'%{filter_text.strip().lower()}%'
                    cur.execute("\n                        SELECT id, nom, COALESCE(telephone,''), COALESCE(email,'')\n                        FROM clients\n                        WHERE LOWER(COALESCE(nom,'')) LIKE ?\n                           OR LOWER(COALESCE(telephone,'')) LIKE ?\n                           OR LOWER(COALESCE(email,'')) LIKE ?\n                        ORDER BY nom ASC\n                        ", (q, q, q))
                else:
                    cur.execute("SELECT id, nom, COALESCE(telephone,''), COALESCE(email,'') FROM clients ORDER BY nom ASC")
                for r in cur.fetchall():
                    tree.insert('', 'end', values=r)
            finally:
                conn.close()

        def on_search_change(event=None):
            load_clients(search_var.get())
        search_entry.bind('<KeyRelease>', on_search_change)
        load_clients()

        def choose_and_close(*_):
            sel = tree.selection()
            if not sel:
                messagebox.showwarning('Sélection', 'Choisissez un client')
                return
            vals = tree.item(sel[0]).get('values', [])
            if not vals:
                return
            client_var.set(vals[1])
            picker.destroy()

        def add_new_client_inline():

            def _save_new():
                nom = (new_nom_var.get() or '').strip()
                tel = (new_tel_var.get() or '').strip() or None
                email = (new_email_var.get() or '').strip() or None
                if not nom:
                    messagebox.showwarning('Client', 'Nom obligatoire')
                    return
                conn = connecter()
                cur = conn.cursor()
                try:
                    try:
                        cur.execute('PRAGMA table_info(clients)')
                        cols = {r[1] for r in cur.fetchall()}
                    except Exception:
                        cols = set()
                    if 'adresse' in cols and 'solde_credit' in cols and ('montant_paye' in cols) and ('date_dernier_paiement' in cols):
                        cur.execute('INSERT INTO clients (nom, telephone, adresse, email, solde_credit, montant_paye, date_dernier_paiement) VALUES (?,?,?,?,0,0,NULL)', (nom, tel, None, email))
                    elif 'adresse' in cols:
                        cur.execute('INSERT INTO clients (nom, telephone, adresse, email) VALUES (?,?,?,?)', (nom, tel, None, email))
                    else:
                        cur.execute('INSERT INTO clients (nom, email, telephone) VALUES (?,?,?)', (nom, email, tel))
                    conn.commit()
                    new_id = cur.lastrowid
                except Exception as e:
                    messagebox.showerror('Client', f"Erreur d'ajout: {e}")
                    return
                finally:
                    conn.close()
                try:
                    clients.append((new_id, nom))
                except Exception:
                    pass
                try:
                    client_combo['values'] = [c[1] for c in clients]
                    client_var.set(nom)
                except Exception:
                    pass
                picker.destroy()
            add_frame = tk.Toplevel(picker)
            add_frame.title('Ajouter un client')
            tk.Label(add_frame, text='Nom :').grid(row=0, column=0, sticky='e', padx=6, pady=6)
            new_nom_var = tk.StringVar(value=(search_var.get() or '').strip())
            tk.Entry(add_frame, textvariable=new_nom_var, width=30).grid(row=0, column=1, padx=6, pady=6)
            tk.Label(add_frame, text='Téléphone :').grid(row=1, column=0, sticky='e', padx=6, pady=6)
            new_tel_var = tk.StringVar()
            tk.Entry(add_frame, textvariable=new_tel_var, width=30).grid(row=1, column=1, padx=6, pady=6)
            tk.Label(add_frame, text='Email :').grid(row=2, column=0, sticky='e', padx=6, pady=6)
            new_email_var = tk.StringVar()
            tk.Entry(add_frame, textvariable=new_email_var, width=30).grid(row=2, column=1, padx=6, pady=6)
            tk.Button(add_frame, text='Créer et sélectionner', command=_save_new, bg='#4CAF50', fg='white').grid(row=3, column=0, columnspan=2, pady=10)
        btns = tk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=4, sticky='w', pady=(4, 0))
        ttk.Button(btns, text='Valider', command=choose_and_close).pack(side='left', padx=(0, 6))
        ttk.Button(btns, text='Ajouter ce client...', command=add_new_client_inline).pack(side='left')
        tree.bind('<Double-1>', choose_and_close)
        search_entry.focus_set()
    btn_search_client = tk.Button(form_frame, text='Rechercher client...', command=open_client_picker, bg='#9C27B0', fg='white', font=('Arial', 10), padx=10)
    btn_search_client.grid(row=1, column=5, padx=5, pady=5)

    def select_client_divers():
        nom_target = 'Client passager'
        found_loc = False
        for c in clients:
            if (c[1] or '').strip().lower() == nom_target.lower():
                found_loc = True
                break
        cid = None
        try:
            with connecter() as connc:
                cur = connc.cursor()
                cur.execute('SELECT id FROM clients WHERE lower(nom)=lower(?) LIMIT 1', (nom_target,))
                row = cur.fetchone()
                if row:
                    cid = row[0]
                else:
                    cur.execute('INSERT INTO clients (nom) VALUES (?)', (nom_target,))
                    connc.commit()
                    cid = cur.lastrowid
        except Exception:
            pass
        if not found_loc and cid is not None:
            try:
                clients.append((cid, nom_target))
            except Exception:
                pass
        try:
            client_combo['values'] = [c[1] for c in clients]
            client_var.set(nom_target)
        except Exception:
            pass
    btn_client_divers = tk.Button(form_frame, text='Client passager', command=select_client_divers, bg='#607D8B', fg='white', font=('Arial', 10), padx=10)
    btn_client_divers.grid(row=1, column=6, padx=5, pady=5)

    def add_client():

        def save_new_client():
            nom = new_client_var.get().strip()
            if not nom:
                messagebox.showwarning('Attention', 'Nom du client obligatoire')
                return
            conn = connecter()
            cur = conn.cursor()
            cur.execute('INSERT INTO clients (nom) VALUES (?)', (nom,))
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            clients.append((new_id, nom))
            client_combo['values'] = [c[1] for c in clients]
            client_var.set(nom)
            add_win.destroy()
        add_win = tk.Toplevel(win)
        add_win.title('Ajouter un client')
        tk.Label(add_win, text='Nom du client :').pack(pady=10)
        new_client_var = tk.StringVar()
        tk.Entry(add_win, textvariable=new_client_var).pack(pady=5)
        tk.Button(add_win, text='Valider', command=save_new_client, bg='#4CAF50', fg='white').pack(pady=10)
    btn_add_client = tk.Button(form_frame, text='Ajouter client', command=add_client, bg='#2196F3', fg='white', font=('Arial', 10), padx=10)
    btn_add_client.grid(row=1, column=3, padx=5, pady=5)

    def edit_client():
        cid = None
        sel_name = client_var.get().strip()
        for c in clients:
            if c[1] == sel_name:
                cid = c[0]
                break
        if cid is None:
            messagebox.showwarning('Client', 'Sélectionnez un client à modifier.')
            return
        nom_init, adr_init, tel_init = (sel_name, None, None)
        try:
            with connecter() as connc:
                cur = connc.cursor()
                cur.execute('PRAGMA table_info(clients)')
                cols = [r[1] for r in cur.fetchall()]
                if 'adresse' not in cols:
                    try:
                        cur.execute('ALTER TABLE clients ADD COLUMN adresse TEXT')
                    except Exception:
                        pass
                if 'telephone' not in cols:
                    try:
                        cur.execute('ALTER TABLE clients ADD COLUMN telephone TEXT')
                    except Exception:
                        pass
                connc.commit()
                cur.execute('SELECT nom, adresse, telephone FROM clients WHERE id=?', (cid,))
                row = cur.fetchone()
                if row:
                    nom_init, adr_init, tel_init = (row[0], row[1], row[2])
        except Exception:
            pass
        ew = tk.Toplevel(win)
        ew.title('Modifier client')
        tk.Label(ew, text='Nom :').grid(row=0, column=0, sticky='e', padx=6, pady=6)
        name_var = tk.StringVar(value=nom_init or '')
        tk.Entry(ew, textvariable=name_var, width=32).grid(row=0, column=1, padx=6, pady=6)
        tk.Label(ew, text='Adresse :').grid(row=1, column=0, sticky='e', padx=6, pady=6)
        adr_var = tk.StringVar(value=adr_init or '')
        tk.Entry(ew, textvariable=adr_var, width=32).grid(row=1, column=1, padx=6, pady=6)
        tk.Label(ew, text='Téléphone :').grid(row=2, column=0, sticky='e', padx=6, pady=6)
        tel_var = tk.StringVar(value=tel_init or '')
        tk.Entry(ew, textvariable=tel_var, width=32).grid(row=2, column=1, padx=6, pady=6)

        def save_edit():
            new_name = name_var.get().strip()
            new_adr = adr_var.get().strip() or None
            new_tel = tel_var.get().strip() or None
            if not new_name:
                messagebox.showwarning('Client', 'Le nom est obligatoire')
                return
            try:
                with connecter() as connc:
                    cur = connc.cursor()
                    cur.execute('UPDATE clients SET nom=?, adresse=?, telephone=? WHERE id=?', (new_name, new_adr, new_tel, cid))
                    connc.commit()
                for i, c in enumerate(clients):
                    if c[0] == cid:
                        clients[i] = (cid, new_name)
                        break
                client_combo['values'] = [c[1] for c in clients]
                client_var.set(new_name)
                try:
                    if 'pending_client_id' in locals() and pending_client_id == cid:
                        _refresh_pending_summary()
                except Exception:
                    pass
                ew.destroy()
            except Exception as e:
                messagebox.showerror('Client', f'Erreur lors de la mise à jour: {e}')
        tk.Button(ew, text='Enregistrer', command=save_edit, bg='#4CAF50', fg='white').grid(row=3, column=0, columnspan=2, pady=10)
    btn_edit_client = tk.Button(form_frame, text='Modifier client (adresse/tél)', command=edit_client, bg='#795548', fg='white', font=('Arial', 10), padx=10)
    btn_edit_client.grid(row=1, column=4, padx=5, pady=5)
    listbox_frame = tk.Frame(form_frame)
    listbox_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')
    try:
        form_frame.grid_rowconfigure(2, weight=1)
        form_frame.grid_columnconfigure(0, weight=1)
    except Exception:
        pass
    articles_listbox = tk.Listbox(listbox_frame, width=60, height=7)
    articles_listbox.pack(side='left', fill='both', expand=True)
    lb_scroll = ttk.Scrollbar(listbox_frame, orient='vertical', command=articles_listbox.yview)
    lb_scroll.pack(side='right', fill='y')
    articles_listbox.configure(yscrollcommand=lb_scroll.set)
    tk.Label(form_frame, text='Remise %:').grid(row=2, column=4, padx=(10, 5), sticky='e')
    remise_var = tk.StringVar()
    remise_entry = tk.Entry(form_frame, textvariable=remise_var, width=6)
    remise_entry.grid(row=2, column=5, sticky='w')

    def _compute_net_unit_price(item: dict) -> float:
        try:
            prix = float(item.get('prix', 0))
        except Exception:
            prix = 0.0
        rp = item.get('remise_pct')
        try:
            rp = float(rp) if rp is not None else 0.0
        except Exception:
            rp = 0.0
        if rp < 0:
            rp = 0.0
        if rp > 100:
            rp = 100.0
        return max(0.0, prix * (1.0 - rp / 100.0))

    def _format_article_line(item: dict, display_qty: str | None=None) -> str:
        nom = item.get('nom', '')
        prix = float(item.get('prix', 0) or 0)
        rp = item.get('remise_pct') or 0
        try:
            rp = float(rp)
        except Exception:
            rp = 0.0
        net = _compute_net_unit_price(item)
        if not display_qty:
            q = item.get('quantite')
            try:
                if q is not None and abs(q - int(q)) < 1e-09:
                    display_qty = f'{int(q)}'
                else:
                    display_qty = fmt_money(q)
            except Exception:
                display_qty = str(q)
        if rp and rp > 0:
            return f'{nom} x{display_qty} - {fmt_money(prix)} (-{rp}%) = {fmt_money(net)}'
        else:
            return f'{nom} x{display_qty} - {fmt_money(prix)}'

    def _refresh_articles_listbox():
        try:
            articles_listbox.delete(0, tk.END)
        except Exception:
            pass
        for it in articles_a_vendre:
            articles_listbox.insert(tk.END, _format_article_line(it))
    pre_total_label = tk.Label(form_frame, text='Total avant vente : 0', anchor='w')
    pre_total_label.grid(row=3, column=0, columnspan=2, sticky='w', padx=5)

    def update_total_simple():
        total = 0
        for art in articles_a_vendre:
            try:
                total += float(art['quantite']) * float(_compute_net_unit_price(art))
            except Exception:
                pass
        try:
            total_label.config(text=f'Total provisoire : {fmt_money(total)}')
        except Exception:
            pass
        try:
            pre_total_label.config(text=f'Total avant vente : {fmt_money(total)}')
        except Exception:
            pass

    def apply_discount_selected():
        sel = articles_listbox.curselection()
        if not sel:
            messagebox.showwarning('Remise', 'Sélectionnez un article dans la liste')
            return
        try:
            rp = float(str(remise_var.get()).replace(',', '.'))
        except Exception:
            messagebox.showwarning('Remise', 'Remise % invalide')
            return
        if rp < 0:
            rp = 0.0
        if rp > 100:
            rp = 100.0
        idx = sel[0]
        try:
            articles_a_vendre[idx]['remise_pct'] = rp
        except Exception:
            return
        _refresh_articles_listbox()
        update_total_simple()

    def clear_discount_selected():
        sel = articles_listbox.curselection()
        if not sel:
            messagebox.showwarning('Remise', 'Sélectionnez un article dans la liste')
            return
        idx = sel[0]
        try:
            articles_a_vendre[idx].pop('remise_pct', None)
        except Exception:
            return
        _refresh_articles_listbox()
        update_total_simple()
    tk.Button(form_frame, text='Appliquer remise %', command=apply_discount_selected).grid(row=2, column=6, padx=5)
    tk.Button(form_frame, text='Effacer remise', command=clear_discount_selected).grid(row=2, column=7, padx=5)

    def remove_selected_article():
        sel = articles_listbox.curselection()
        if not sel:
            messagebox.showwarning('Suppression', 'Sélectionnez un article dans la liste')
            return
        idx = sel[0]
        try:
            articles_a_vendre.pop(idx)
        except Exception:
            return
        _refresh_articles_listbox()
        update_total_simple()

    def clear_articles_list():
        if not articles_a_vendre:
            return
        if not messagebox.askyesno('Confirmation', 'Vider la liste des articles avant vente ?'):
            return
        try:
            articles_a_vendre.clear()
        except Exception:
            pass
        _refresh_articles_listbox()
        update_total_simple()
    tk.Button(form_frame, text='Retirer sélection', command=remove_selected_article).grid(row=2, column=8, padx=5)
    tk.Button(form_frame, text='Vider liste', command=clear_articles_list).grid(row=2, column=9, padx=5)

    def check_article_existence_simple(nom):
        conn = connecter()
        cur = conn.cursor()
        try:
            norm_expr = "replace(replace(replace(lower(nom),' ',''),'-',''),'_','')"
            cur.execute(f'SELECT code, nom, prix_vente, quantite FROM articles WHERE {norm_expr} = ? LIMIT 1', (_normalize_nom(nom),))
            article = cur.fetchone()
        finally:
            conn.close()
        return article

    def add_article():
        nom = produit_var.get().strip()
        q_effective = None
        display_qty = None
        if mode_var.get() == 'Poids':
            try:
                val = float(str(poids_val_var.get()).replace(',', '.'))
            except Exception:
                messagebox.showwarning('Attention', 'Poids invalide')
                return
            unit = poids_unit_var.get()
            if unit == 'kg':
                q_effective = val
                display_qty = f'{fmt_money(val)} kg'
            else:
                q_effective = val / 1000.0
                display_qty = f'{(int(val) if abs(val - int(val)) < 1e-09 else fmt_money(val))} g'
            if not nom or q_effective <= 0:
                messagebox.showwarning('Attention', "Saisir un nom d'article et un poids valide")
                return
        else:
            try:
                raw_q = str(quantite_var.get()).replace(',', '.').strip()
                if '/' in raw_q:
                    parts = raw_q.split('/')
                    quantite = round(float(parts[0]) / float(parts[1]), 3)
                else:
                    quantite = round(float(raw_q), 3)
            except Exception:
                messagebox.showwarning('Attention', 'Quantité invalide')
                return
            if not nom or quantite <= 0:
                messagebox.showwarning('Attention', "Saisir un nom d'article et une quantité valide puis cliquer sur 'Ajouter à la liste'")
                return
            q_effective = quantite
            display_qty = f'{(int(quantite) if abs(quantite - int(quantite)) < 1e-09 else fmt_money(quantite))}'
        for art in articles_a_vendre:
            if _normalize_nom(art['nom']) == _normalize_nom(nom):
                messagebox.showwarning('Attention', 'Cet article est déjà dans la liste à vendre.')
                return
        article = check_article_existence_simple(nom)
        if article:
            prix_vente = article[2]
            article_code = article[0]
            nom_db = article[1] or nom
            articles_a_vendre.append({'nom': nom_db, 'quantite': q_effective, 'prix': prix_vente, 'id': article_code, 'remise_pct': 0.0})
            _refresh_articles_listbox()
            update_total_simple()
            produit_var.set('')
            quantite_var.set('')
            poids_val_var.set('')
            produit_entry.focus_set()
        else:
            ensure_categories_schema()
            ensure_article_category_schema()

            def save_new_article():
                try:
                    prix_achat = float(prix_achat_var.get())
                except Exception:
                    messagebox.showwarning('Attention', "Prix d'achat invalide")
                    return
                try:
                    prix_vente = float(prix_vente_var.get())
                except Exception:
                    messagebox.showwarning('Attention', 'Prix de vente invalide')
                    return
                try:
                    stock = int(stock_var.get())
                except Exception:
                    messagebox.showwarning('Attention', 'Quantité en stock invalide')
                    return
                if stock < 0:
                    messagebox.showwarning('Attention', 'La quantité en stock doit être >= 0')
                    return
                categorie_choisie = None
                existing = check_article_existence_simple(nom)
                if existing:
                    prix_vente_ex = existing[2]
                    article_code_ex = existing[0]
                    nom_db_ex = existing[1] or nom
                    articles_a_vendre.append({'nom': nom_db_ex, 'quantite': q_effective, 'prix': prix_vente_ex, 'id': article_code_ex, 'remise_pct': 0.0})
                    _refresh_articles_listbox()
                    update_total_simple()
                    add_win.destroy()
                    produit_var.set('')
                    quantite_var.set('')
                    poids_val_var.set('')
                    produit_entry.focus_set()
                    return
                code_val = code_var.get().strip()
                cat_new = new_cat_var.get().strip()
                if cat_new:
                    add_category(cat_new)
                    categorie_choisie = cat_new
                else:
                    categorie_choisie = cat_var.get().strip() or None
                try:
                    with connecter() as conn:
                        try:
                            conn.execute('PRAGMA busy_timeout = 5000')
                        except Exception:
                            pass
                        cur = conn.cursor()
                        cur.execute('SELECT 1 FROM articles WHERE code = ?', (code_val,))
                        if cur.fetchone():
                            messagebox.showerror('Erreur', "Ce code d'article existe déjà. Choisissez un autre code.")
                            return
                        try:
                            cur.execute('INSERT INTO articles (code, nom, prix_unitaire, prix_vente, quantite, categorie) VALUES (?, ?, ?, ?, ?, ?)', (code_val, nom, prix_achat, prix_vente, stock, categorie_choisie))
                        except sqlite3.OperationalError:
                            cur.execute('INSERT INTO articles (code, nom, prix_unitaire, prix_vente, quantite) VALUES (?, ?, ?, ?, ?)', (code_val, nom, prix_achat, prix_vente, stock))
                        conn.commit()
                except sqlite3.IntegrityError:
                    messagebox.showerror('Erreur', "Ce code d'article existe déjà. Choisissez un autre code.")
                    return
                except sqlite3.OperationalError as e:
                    messagebox.showerror('Base de données verrouillée', f'La base est momentanément occupée. Réessayez dans un instant.\nDétail: {e}')
                    return
                produits.append((code_val, nom, prix_vente, stock))
                articles_a_vendre.append({'nom': nom, 'quantite': q_effective, 'prix': prix_vente, 'id': code_val, 'remise_pct': 0.0})
                _refresh_articles_listbox()
                update_total_simple()
                add_win.destroy()
                produit_var.set('')
                quantite_var.set('')
                poids_val_var.set('')
                produit_entry.focus_set()
            add_win = tk.Toplevel(win)
            add_win.title('Ajouter un nouvel article')
            tk.Label(add_win, text=f'Article inconnu : {nom}', font=('Arial', 12, 'bold'), fg='red').pack(pady=10)
            tk.Label(add_win, text='Code :').pack()
            code_var = tk.StringVar(value=_generate_unique_article_code())
            tk.Entry(add_win, textvariable=code_var).pack()
            tk.Label(add_win, text="Prix d'achat :").pack()
            prix_achat_var = tk.StringVar()
            tk.Entry(add_win, textvariable=prix_achat_var).pack()
            tk.Label(add_win, text='Prix de vente :').pack()
            prix_vente_var = tk.StringVar()
            tk.Entry(add_win, textvariable=prix_vente_var).pack()
            tk.Label(add_win, text='Quantité en stock :').pack()
            stock_var = tk.StringVar()
            tk.Entry(add_win, textvariable=stock_var).pack()
            frame_cat = tk.Frame(add_win)
            frame_cat.pack(pady=(8, 4))
            tk.Label(frame_cat, text='Catégorie :').grid(row=0, column=0, padx=4)
            cat_var = tk.StringVar()
            cat_combo = ttk.Combobox(frame_cat, textvariable=cat_var, values=list_categories(), width=30, state='readonly')
            cat_combo.grid(row=0, column=1, padx=4)
            tk.Label(frame_cat, text='ou nouvelle :').grid(row=1, column=0, padx=4, pady=(6, 0))
            new_cat_var = tk.StringVar()
            new_cat_entry = ttk.Entry(frame_cat, textvariable=new_cat_var, width=32)
            new_cat_entry.grid(row=1, column=1, padx=4, pady=(6, 0))

            def do_add_cat():
                nom_cat = new_cat_var.get().strip()
                if not nom_cat:
                    return
                add_category(nom_cat)
                cat_combo.configure(values=list_categories())
                cat_var.set(nom_cat)
            ttk.Button(frame_cat, text='Ajouter catégorie', command=do_add_cat).grid(row=1, column=2, padx=6)
            tk.Button(add_win, text='Valider', command=save_new_article, bg='#4CAF50', fg='white').pack(pady=10)
    btn_ajouter_article = tk.Button(form_frame, text='Ajouter à la liste', command=add_article, bg='#2196F3', fg='white', font=('Arial', 10, 'bold'), padx=10, pady=5)
    btn_ajouter_article.grid(row=0, column=4, padx=5, pady=5)
    pending_by_client: dict[int, dict] = {}

    def _resolve_selected_client_id():
        client_id = None
        selected_client = client_var.get().strip()
        for c in clients:
            if c[1] == selected_client:
                client_id = c[0]
                break
        if client_id is None:
            try:
                connx = connecter()
                curx = connx.cursor()
                curx.execute("SELECT id FROM clients WHERE lower(nom)=lower('Client passager') LIMIT 1")
                rowx = curx.fetchone()
                if rowx:
                    client_id = rowx[0]
                else:
                    curx.execute("INSERT INTO clients (nom) VALUES ('Client passager')")
                    connx.commit()
                    client_id = curx.lastrowid
            finally:
                try:
                    connx.close()
                except Exception:
                    pass
        return client_id

    def _fetch_client_details(cid: int):
        if cid is None:
            return (None, None, None)
        nom_val = None
        for c in clients:
            if c[0] == cid:
                nom_val = c[1]
                break
        adresse = None
        telephone = None
        try:
            with connecter() as cdb:
                cur = cdb.cursor()
                cur.execute('PRAGMA table_info(clients)')
                cols = [r[1] for r in cur.fetchall()]
                if 'adresse' in cols or 'telephone' in cols:
                    sel_cols = ['nom']
                    if 'adresse' in cols:
                        sel_cols.append('adresse')
                    if 'telephone' in cols:
                        sel_cols.append('telephone')
                    cur.execute(f"SELECT {', '.join(sel_cols)} FROM clients WHERE id = ?", (cid,))
                    row = cur.fetchone()
                    if row:
                        idx = 0
                        if 'nom' in sel_cols:
                            nom_val = row[idx]
                            idx += 1
                        if 'adresse' in sel_cols:
                            adresse = row[idx]
                            idx += 1
                        if 'telephone' in sel_cols:
                            telephone = row[idx]
        except Exception:
            pass
        return (nom_val, adresse, telephone)

    def _calc_group_total(cid: int) -> float:
        total = 0.0
        grp = pending_by_client.get(cid)
        if not grp:
            return 0.0
        for it in grp['items']:
            try:
                unit = _compute_net_unit_price(it)
                total += float(it['quantite']) * float(unit)
            except Exception:
                pass
        return total

    def _format_client_header_text(cid: int) -> str:
        nom_c, adr, tel = _fetch_client_details(cid)
        parts = []
        if nom_c:
            parts.append(f'Client: {nom_c}')
        if adr:
            parts.append(f'Adresse: {adr}')
        if tel:
            parts.append(f'Tél: {tel}')
        try:
            info = (pending_by_client.get(cid) or {}).get('info') or {}
            av = info.get('avance')
            rs = info.get('reste')
            if isinstance(av, (int, float)) and av > 0:
                av_txt = fmt_money(av)
                rs_txt = fmt_money(rs) if isinstance(rs, (int, float)) else fmt_money(max(0.0, _calc_group_total(cid) - float(av)))
                parts.append(f'Acompte: {av_txt} | Reste: {rs_txt}')
        except Exception:
            pass
        return '  |  '.join(parts) if parts else 'Client: (inconnu)'

    def _refresh_group_ui(cid: int):
        grp = pending_by_client.get(cid)
        if not grp:
            return
        grp['header_label'].config(text=_format_client_header_text(cid))
        grp['total_label'].config(text=f'Total: {fmt_money(_calc_group_total(cid))}')

    def _add_to_pending_from_form():
        sel_client_id = _resolve_selected_client_id()
        nom = produit_var.get().strip()
        if not nom:
            messagebox.showwarning('Attention', 'Choisissez un article')
            return
        if mode_var.get() == 'Poids':
            try:
                val = float(str(poids_val_var.get()).replace(',', '.'))
            except Exception:
                messagebox.showwarning('Attention', 'Poids invalide')
                return
            q_effective = val if poids_unit_var.get() == 'kg' else val / 1000.0
        else:
            try:
                raw_q = str(quantite_var.get()).replace(',', '.').strip()
                if '/' in raw_q:
                    parts = raw_q.split('/')
                    q_effective = round(float(parts[0]) / float(parts[1]), 3)
                else:
                    q_effective = round(float(raw_q), 3)
            except Exception:
                messagebox.showwarning('Attention', 'Quantité invalide')
                return
        if q_effective <= 0:
            messagebox.showwarning('Attention', 'La quantité doit être > 0')
            return
        art = check_article_existence_simple(nom)
        if not art:
            ensure_categories_schema()
            ensure_article_category_schema()

            def save_new_article():
                try:
                    prix_achat = float(prix_achat_var.get())
                except Exception:
                    messagebox.showwarning('Attention', "Prix d'achat invalide")
                    return
                try:
                    prix_vente_loc = float(prix_vente_var.get())
                except Exception:
                    messagebox.showwarning('Attention', 'Prix de vente invalide')
                    return
                try:
                    stock = int(stock_var.get())
                except Exception:
                    messagebox.showwarning('Attention', 'Quantité en stock invalide')
                    return
                if stock < 0:
                    messagebox.showwarning('Attention', 'La quantité en stock doit être >= 0')
                    return
                existing = check_article_existence_simple(nom)
                if existing:
                    code_ex, nom_db_ex, prix_vente_ex, _ = existing
                    item_ex = {'id': code_ex, 'nom': nom_db_ex or nom, 'quantite': q_effective, 'prix': float(prix_vente_ex), 'remise_pct': 0.0}
                    _ensure_group_exists(sel_client_id)
                    grp_ex = pending_by_client[sel_client_id]
                    grp_ex['items'].append(item_ex)
                    grp_ex['listbox'].insert(tk.END, _format_pending_line(item_ex))
                    _refresh_group_ui(sel_client_id)
                    try:
                        _save_pending_state_if_enabled()
                    except Exception:
                        pass
                    add_win.destroy()
                    produit_var.set('')
                    quantite_var.set('')
                    poids_val_var.set('')
                    produit_entry.focus_set()
                    return
                code_val = code_var.get().strip()
                cat_new = new_cat_var.get().strip()
                if cat_new:
                    add_category(cat_new)
                    categorie_choisie = cat_new
                else:
                    categorie_choisie = cat_var.get().strip() or None
                try:
                    with connecter() as conn:
                        try:
                            conn.execute('PRAGMA busy_timeout = 5000')
                        except Exception:
                            pass
                        cur = conn.cursor()
                        cur.execute('SELECT 1 FROM articles WHERE code = ?', (code_val,))
                        if cur.fetchone():
                            messagebox.showerror('Erreur', "Ce code d'article existe déjà. Choisissez un autre code.")
                            return
                        try:
                            cur.execute('INSERT INTO articles (code, nom, prix_unitaire, prix_vente, quantite, categorie) VALUES (?, ?, ?, ?, ?, ?)', (code_val, nom, prix_achat, prix_vente_loc, stock, categorie_choisie))
                        except sqlite3.OperationalError:
                            cur.execute('INSERT INTO articles (code, nom, prix_unitaire, prix_vente, quantite) VALUES (?, ?, ?, ?, ?)', (code_val, nom, prix_achat, prix_vente_loc, stock))
                        conn.commit()
                except sqlite3.IntegrityError:
                    messagebox.showerror('Erreur', "Ce code d'article existe déjà. Choisissez un autre code.")
                    return
                except sqlite3.OperationalError as e:
                    messagebox.showerror('Base de données verrouillée', f'La base est momentanément occupée. Réessayez dans un instant.\nDétail: {e}')
                    return
                _ensure_group_exists(sel_client_id)
                grp = pending_by_client[sel_client_id]
                new_item = {'id': code_val, 'nom': nom, 'quantite': q_effective, 'prix': float(prix_vente_loc), 'remise_pct': 0.0}
                grp['items'].append(new_item)
                grp['listbox'].insert(tk.END, _format_pending_line(new_item))
                _refresh_group_ui(sel_client_id)
                try:
                    _save_pending_state_if_enabled()
                except Exception:
                    pass
                add_win.destroy()
                produit_var.set('')
                quantite_var.set('')
                poids_val_var.set('')
                produit_entry.focus_set()
            add_win = tk.Toplevel(win)
            add_win.title('Ajouter un nouvel article')
            tk.Label(add_win, text=f'Article inconnu : {nom}', font=('Arial', 12, 'bold'), fg='red').pack(pady=10)
            tk.Label(add_win, text='Code :').pack()
            code_var = tk.StringVar(value=_generate_unique_article_code())
            tk.Entry(add_win, textvariable=code_var).pack()
            tk.Label(add_win, text="Prix d'achat :").pack()
            prix_achat_var = tk.StringVar()
            tk.Entry(add_win, textvariable=prix_achat_var).pack()
            tk.Label(add_win, text='Prix de vente :').pack()
            prix_vente_var = tk.StringVar()
            tk.Entry(add_win, textvariable=prix_vente_var).pack()
            tk.Label(add_win, text='Quantité en stock :').pack()
            stock_var = tk.StringVar()
            tk.Entry(add_win, textvariable=stock_var).pack()
            frame_cat = tk.Frame(add_win)
            frame_cat.pack(pady=(8, 4))
            tk.Label(frame_cat, text='Catégorie :').grid(row=0, column=0, padx=4)
            cat_var = tk.StringVar()
            cat_combo = ttk.Combobox(frame_cat, textvariable=cat_var, values=list_categories(), width=30, state='readonly')
            cat_combo.grid(row=0, column=1, padx=4)
            tk.Label(frame_cat, text='ou nouvelle :').grid(row=1, column=0, padx=4, pady=(6, 0))
            new_cat_var = tk.StringVar()
            new_cat_entry = ttk.Entry(frame_cat, textvariable=new_cat_var, width=32)
            new_cat_entry.grid(row=1, column=1, padx=4, pady=(6, 0))

            def do_add_cat():
                nom_cat = new_cat_var.get().strip()
                if not nom_cat:
                    return
                add_category(nom_cat)
                cat_combo.configure(values=list_categories())
                cat_var.set(nom_cat)
            ttk.Button(frame_cat, text='Ajouter catégorie', command=do_add_cat).grid(row=1, column=2, padx=6)
            tk.Button(add_win, text='Valider', command=save_new_article, bg='#4CAF50', fg='white').pack(pady=10)
            return
        code, nom_db, prix_vente, stock = art
        item = {'id': code, 'nom': nom_db, 'quantite': q_effective, 'prix': float(prix_vente), 'remise_pct': 0.0}
        _ensure_group_exists(sel_client_id)
        grp = pending_by_client[sel_client_id]
        grp['items'].append(item)
        grp['listbox'].insert(tk.END, _format_pending_line(item))
        _refresh_group_ui(sel_client_id)
        try:
            _save_pending_state_if_enabled()
        except Exception:
            pass
        produit_var.set('')
        quantite_var.set('')
        poids_val_var.set('')
        produit_entry.focus_set()
    btn_add_pending = tk.Button(form_frame, text="Ajouter à l'attente", command=_add_to_pending_from_form, bg='#607D8B', fg='white', font=('Arial', 10), padx=10, pady=5)
    btn_add_pending.grid(row=0, column=7, padx=5, pady=5)
    attente_frame = tk.LabelFrame(main_frame, text="Liste d'attente (par client)", padx=8, pady=6)
    attente_frame.pack(fill=tk.X, pady=(5, 10))
    pending_by_client = {}
    persist_pending_var = tk.BooleanVar(value=True)

    def _pending_state_file():
        try:
            base = os.path.dirname(__file__)
        except Exception:
            base = os.getcwd()
        return os.path.join(base, 'pending_state.json')

    def _save_pending_state_if_enabled():
        if not persist_pending_var.get():
            return
        try:
            data = {}
            for cid, grp in pending_by_client.items():
                items = grp.get('items', [])
                info = grp.get('info') or {}
                data[str(cid)] = {'items': [{'id': it.get('id'), 'nom': it.get('nom'), 'quantite': float(it.get('quantite') or 0), 'prix': float(it.get('prix') or 0), 'remise_pct': float(it.get('remise_pct') or 0)} for it in items], 'info': info}
            with open(_pending_state_file(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_pending_state_if_enabled():
        if not persist_pending_var.get():
            return
        try:
            fp = _pending_state_file()
            if not os.path.exists(fp):
                return
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, node in data.items():
                try:
                    cid = int(k)
                except Exception:
                    continue
                _ensure_group_exists(cid)
                grp = pending_by_client[cid]
                items = node if isinstance(node, list) else node.get('items') if isinstance(node, dict) else []
                for it in items or []:
                    try:
                        rec = {'id': it.get('id'), 'nom': it.get('nom'), 'quantite': float(it.get('quantite') or 0), 'prix': float(it.get('prix') or 0), 'remise_pct': float(it.get('remise_pct') or 0)}
                        grp['items'].append(rec)
                        grp['listbox'].insert(tk.END, _format_pending_line(rec))
                    except Exception:
                        continue
                try:
                    if isinstance(node, dict) and node.get('info'):
                        grp['info'] = dict(node['info'])
                except Exception:
                    pass
                _refresh_group_ui(cid)
        except Exception:
            pass

    def _on_toggle_persist():
        if persist_pending_var.get():
            _save_pending_state_if_enabled()
    tk.Checkbutton(attente_frame, text='Persistance de la liste (auto)', variable=persist_pending_var, command=_on_toggle_persist).pack(anchor='w')
    attente_groups_container = tk.Frame(attente_frame)
    attente_groups_container.pack(fill=tk.X)

    def _format_pending_line(item: dict) -> str:
        nom = item.get('nom', '')
        q = item.get('quantite')
        try:
            q_disp = fmt_money(q)
        except Exception:
            q_disp = str(q)
        prix = float(item.get('prix') or 0)
        rp = float(item.get('remise_pct') or 0)
        unit_net = _compute_net_unit_price(item)
        if rp > 0:
            return f'{nom} x{q_disp} - {fmt_money(prix)} (-{rp}%) = {fmt_money(unit_net)}'
        return f'{nom} x{q_disp} - {fmt_money(prix)}'

    def _ensure_group_exists(cid: int):
        if cid in pending_by_client:
            return
        grp_frame = tk.Frame(attente_groups_container, bd=1, relief='groove', padx=6, pady=6)
        grp_frame.pack(fill=tk.X, pady=4)
        header = tk.Label(grp_frame, text=_format_client_header_text(cid), anchor='w', font=('Arial', 10, 'bold'))
        header.pack(fill=tk.X)
        inner = tk.Frame(grp_frame)
        inner.pack(fill=tk.X, pady=(4, 2))
        lb = tk.Listbox(inner, height=4)
        lb.pack(side='left', fill=tk.X, expand=True)
        sb = ttk.Scrollbar(inner, orient='vertical', command=lb.yview)
        sb.pack(side='left', fill='y')
        lb.configure(yscrollcommand=sb.set)
        controls = tk.Frame(grp_frame)
        controls.pack(fill=tk.X, pady=(4, 0))
        total_lbl = tk.Label(controls, text='Total: 0', anchor='e', fg='#2e7d32', font=('Arial', 10, 'bold'))
        total_lbl.pack(side='right')
        tk.Label(controls, text='Remise %:').pack(side='left')
        remise_g_var = tk.StringVar()
        remise_g_entry = tk.Entry(controls, textvariable=remise_g_var, width=6)
        remise_g_entry.pack(side='left', padx=(4, 6))

        def _apply_grp_discount():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning('Remise', 'Sélectionnez un article du groupe')
                return
            try:
                rp = float(str(remise_g_var.get()).replace(',', '.'))
            except Exception:
                messagebox.showwarning('Remise', 'Remise % invalide')
                return
            if rp < 0:
                rp = 0.0
            if rp > 100:
                rp = 100.0
            idx = sel[0]
            try:
                pending_by_client[cid]['items'][idx]['remise_pct'] = rp
            except Exception:
                return
            try:
                lb.delete(idx)
                lb.insert(idx, _format_pending_line(pending_by_client[cid]['items'][idx]))
            except Exception:
                pass
            _refresh_group_ui(cid)
            _save_pending_state_if_enabled()

        def _clear_grp_discount():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning('Remise', 'Sélectionnez un article du groupe')
                return
            idx = sel[0]
            try:
                pending_by_client[cid]['items'][idx].pop('remise_pct', None)
            except Exception:
                return
            try:
                lb.delete(idx)
                lb.insert(idx, _format_pending_line(pending_by_client[cid]['items'][idx]))
            except Exception:
                pass
            _refresh_group_ui(cid)
            _save_pending_state_if_enabled()
        tk.Button(controls, text='Appliquer remise %', command=_apply_grp_discount).pack(side='left', padx=4)
        tk.Label(controls, text='Acompte:').pack(side='left', padx=(12, 2))
        acompte_var = tk.StringVar()
        acompte_entry = tk.Entry(controls, textvariable=acompte_var, width=10)
        acompte_entry.pack(side='left')

        def _valider_acompte():
            try:
                av = float(str(acompte_var.get()).replace(' ', '').replace(',', '.'))
                if av < 0:
                    av = 0.0
            except Exception:
                messagebox.showwarning('Acompte', 'Montant invalide')
                return
            rs = max(0.0, _calc_group_total(cid) - av)
            pending_by_client[cid]['info'] = {'avance': av, 'reste': rs, 'updated_at': datetime.now().isoformat(timespec='seconds')}
            _refresh_group_ui(cid)
            _save_pending_state_if_enabled()
        tk.Button(controls, text='Valider acompte', command=_valider_acompte).pack(side='left', padx=4)
        tk.Button(controls, text='Effacer remise', command=_clear_grp_discount).pack(side='left')

        def _remove_selected():
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            try:
                pending_by_client[cid]['items'].pop(idx)
                lb.delete(idx)
            except Exception:
                return
            if not pending_by_client[cid]['items']:
                try:
                    grp_frame.destroy()
                except Exception:
                    pass
                pending_by_client.pop(cid, None)
            else:
                _refresh_group_ui(cid)
            _save_pending_state_if_enabled()

        def _sell_selected(statut: str):
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning('Sélection', 'Sélectionnez un article dans le groupe')
                return
            idx = sel[0]
            it = pending_by_client[cid]['items'][idx]
            try:
                unit = _compute_net_unit_price(it)
                total_override = float(it['quantite']) * float(unit)
                if statut == 'credit':
                    try:
                        date_iso = current_list_date.get().strip() or datetime.now().strftime('%Y-%m-%d')
                    except Exception:
                        date_iso = datetime.now().strftime('%Y-%m-%d')
                    info = pending_by_client.get(cid, {}).get('info') or {}
                    av_grp = float(info.get('avance') or 0)
                    if av_grp > 0:
                        _enregistrer_avance_client(cid, date_iso, av_grp)
                        pending_by_client[cid]['info'] = {}
                        _save_pending_state_if_enabled()
                ajouter_vente(it['id'], cid, it['quantite'], lambda: None, current_list_date.get().strip(), silent=True, statut=statut, total_override=total_override)
            except Exception:
                return
            pending_by_client[cid]['items'].pop(idx)
            lb.delete(idx)
            if not pending_by_client[cid]['items']:
                try:
                    grp_frame.destroy()
                except Exception:
                    pass
                pending_by_client.pop(cid, None)
            else:
                _refresh_group_ui(cid)
            afficher_ventes_et_total(tree, total_label, current_list_date.get().strip())
            try:
                _refresh_tree_totals()
            except Exception:
                pass
            _save_pending_state_if_enabled()

        def _sell_all(statut: str):
            items = list(pending_by_client.get(cid, {}).get('items', []))
            if not items:
                messagebox.showwarning('Vente', 'Aucun article dans ce groupe.')
                return
            sold = 0
            group_total = 0.0
            if statut == 'credit':
                try:
                    for it in items:
                        unit_tmp = _compute_net_unit_price(it)
                        group_total += float(it['quantite']) * float(unit_tmp)
                except Exception:
                    group_total = 0.0
                try:
                    date_iso = current_list_date.get().strip() or datetime.now().strftime('%Y-%m-%d')
                except Exception:
                    date_iso = datetime.now().strftime('%Y-%m-%d')
                info = pending_by_client.get(cid, {}).get('info') or {}
                av_grp = float(info.get('avance') or 0)
                if av_grp > 0:
                    _enregistrer_avance_client(cid, date_iso, min(av_grp, group_total if group_total > 0 else av_grp))
                    pending_by_client[cid]['info'] = {}
                    _save_pending_state_if_enabled()
            for it in items:
                try:
                    unit = _compute_net_unit_price(it)
                    total_override = float(it['quantite']) * float(unit)
                    ajouter_vente(it['id'], cid, it['quantite'], lambda: None, current_list_date.get().strip(), silent=True, statut=statut, total_override=total_override)
                    sold += 1
                except Exception:
                    pass
            try:
                lb.delete(0, tk.END)
            except Exception:
                pass
            pending_by_client[cid]['items'].clear()
            try:
                grp_frame.destroy()
            except Exception:
                pass
            pending_by_client.pop(cid, None)
            afficher_ventes_et_total(tree, total_label, current_list_date.get().strip())
            try:
                _refresh_tree_totals()
            except Exception:
                pass
            _save_pending_state_if_enabled()

        def _clear_group():
            if not pending_by_client.get(cid, {}).get('items'):
                return
            if not messagebox.askyesno('Confirmation', 'Vider tous les articles de ce groupe ?'):
                return
            try:
                lb.delete(0, tk.END)
            except Exception:
                pass
            pending_by_client[cid]['items'].clear()
            try:
                grp_frame.destroy()
            except Exception:
                pass
            pending_by_client.pop(cid, None)
            _save_pending_state_if_enabled()
        btns = tk.Frame(grp_frame)
        btns.pack(fill=tk.X, pady=(4, 0))
        tk.Button(btns, text='Vendre Payée', command=lambda: _sell_selected('payee'), bg='#4CAF50', fg='white').pack(side='left', padx=2)
        tk.Button(btns, text='Vendre Crédit', command=lambda: _sell_selected('credit'), bg='#FF9800', fg='white').pack(side='left', padx=2)
        tk.Button(btns, text='Vendre tout Payée', command=lambda: _sell_all('payee'), bg='#2E7D32', fg='white').pack(side='left', padx=2)
        tk.Button(btns, text='Vendre tout Crédit', command=lambda: _sell_all('credit'), bg='#F57C00', fg='white').pack(side='left', padx=2)
        tk.Button(btns, text='Retirer', command=_remove_selected, bg='#9E9E9E', fg='white').pack(side='left', padx=2)
        tk.Button(btns, text='Vider le groupe', command=_clear_group, bg='#B71C1C', fg='white').pack(side='left', padx=2)
        pending_by_client[cid] = {'items': [], 'frame': grp_frame, 'header_label': header, 'listbox': lb, 'total_label': total_lbl, 'info': {}}
        _refresh_group_ui(cid)
    _load_pending_state_if_enabled()
    liste_frame = tk.Frame(main_frame)
    liste_frame.pack(fill=tk.X, pady=(0, 8))
    tk.Label(liste_frame, text='Date de liste (YYYY-MM-DD):').pack(side=tk.LEFT)
    current_list_date = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
    date_entry = tk.Entry(liste_frame, textvariable=current_list_date, width=12)
    date_entry.pack(side=tk.LEFT, padx=6)

    def ouvrir_liste():
        afficher_ventes_et_total(tree, total_label, current_list_date.get().strip())
        try:
            _refresh_tree_totals()
        except Exception:
            pass

    def nouvelle_liste():
        afficher_ventes_et_total(tree, total_label, current_list_date.get().strip())
        try:
            _refresh_tree_totals()
        except Exception:
            pass
        articles_a_vendre.clear()
        articles_listbox.delete(0, tk.END)
        update_total_simple()
    tk.Button(liste_frame, text='Ouvrir liste', command=ouvrir_liste, bg='#8e44ad', fg='white').pack(side=tk.LEFT, padx=5)
    tk.Button(liste_frame, text='Nouvelle liste', command=nouvelle_liste, bg='#16a085', fg='white').pack(side=tk.LEFT)

    def _enregistrer_ventes(statut: str):
        if not articles_a_vendre:
            messagebox.showwarning('Attention', "Aucun article à vendre. Ajoutez au moins un article à la liste avant d'enregistrer.")
            return
        client_id = None
        selected_client = client_var.get().strip()
        for c in clients:
            if c[1] == selected_client:
                client_id = c[0]
                break
        if client_id is None:
            try:
                conn = connecter()
                cur = conn.cursor()
                cur.execute("SELECT id FROM clients WHERE lower(nom)=lower('Client passager') LIMIT 1")
                row = cur.fetchone()
                if row:
                    client_id = row[0]
                else:
                    cur.execute("INSERT INTO clients (nom) VALUES ('Client passager')")
                    conn.commit()
                    client_id = cur.lastrowid
            except Exception as e:
                messagebox.showerror('Erreur', f"Impossible de récupérer/créer 'Client passager' : {e}")
                return
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        if statut == 'credit':
            try:
                total_list = 0.0
                for art in articles_a_vendre:
                    unit_tmp = _compute_net_unit_price(art)
                    total_list += float(art['quantite']) * float(unit_tmp)
            except Exception:
                total_list = 0.0
            if total_list > 0:
                try:
                    date_iso = current_list_date.get().strip() or datetime.now().strftime('%Y-%m-%d')
                except Exception:
                    date_iso = datetime.now().strftime('%Y-%m-%d')
                avance_all = simpledialog.askfloat('Avance', f"Montant d'avance pour cette vente à crédit (max {total_list:.2f}) :", minvalue=0.0, maxvalue=total_list, initialvalue=0.0, parent=win)
                if isinstance(avance_all, (int, float)) and avance_all > 0:
                    _enregistrer_avance_client(client_id, date_iso, min(float(avance_all), float(total_list)))
        for art in articles_a_vendre:
            try:
                unit = _compute_net_unit_price(art)
            except Exception:
                unit = float(art.get('prix') or 0)
            total_override = float(art['quantite']) * float(unit)
            ajouter_vente(art['id'], client_id, art['quantite'], lambda: None, current_list_date.get().strip(), statut=statut, total_override=total_override)
        afficher_ventes_et_total(tree, total_label, current_list_date.get().strip())
        try:
            _refresh_tree_totals()
        except Exception:
            pass
        articles_a_vendre.clear()
        articles_listbox.delete(0, tk.END)
        update_total_simple()
    btn_enregistrer_payee = tk.Button(form_frame, text='Vente payée', command=lambda: _enregistrer_ventes('payee'), bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'), padx=12, pady=5)
    btn_enregistrer_payee.grid(row=3, column=3, sticky='e', pady=10, padx=5)
    btn_enregistrer_credit = tk.Button(form_frame, text='Vente crédit', command=lambda: _enregistrer_ventes('credit'), bg='#FF9800', fg='white', font=('Arial', 10, 'bold'), padx=12, pady=5)
    btn_enregistrer_credit.grid(row=3, column=4, sticky='e', pady=10, padx=5)
    tree_frame = tk.Frame(main_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    tree = ttk.Treeview(tree_frame, columns=('ID', 'Produit', 'Client', 'Quantité', 'Prix Unitaire', 'Total', 'Marge nette (Payée)', 'Date', 'Statut'), height=12, show='headings', selectmode='browse')
    tree.heading('ID', text='ID')
    tree.heading('Produit', text='Produit')
    tree.heading('Client', text='Client')
    tree.heading('Quantité', text='Quantité')
    tree.heading('Prix Unitaire', text='Prix Unitaire')
    tree.heading('Total', text='Total')
    tree.heading('Marge nette (Payée)', text='Marge nette (Payée)')
    tree.heading('Date', text='Date')
    tree.heading('Statut', text='Statut')
    tree.column('ID', width=40, anchor='center')
    tree.column('Produit', width=150, anchor='w')
    tree.column('Client', width=150, anchor='w')
    tree.column('Quantité', width=80, anchor='center')
    tree.column('Prix Unitaire', width=100, anchor='e')
    tree.column('Total', width=100, anchor='e')
    tree.column('Marge nette (Payée)', width=120, anchor='e')
    tree.column('Date', width=100, anchor='center')
    tree.column('Statut', width=100, anchor='center')
    scrollbar_y = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.pack(side='right', fill='y')
    tree.pack(side='left', fill='both', expand=True)
    totaux_frame = tk.Frame(main_frame)
    totaux_frame.pack(fill='x', pady=10)
    total_label = tk.Label(totaux_frame, text='Total des ventes : 0', font=('Arial', 12, 'bold'))
    total_label.pack(side='left', padx=10)

    def supprimer_vente_selectionnee():
        from tkinter import messagebox
        import sqlite3
        selected = tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner une vente à supprimer.')
            return
        item = tree.item(selected[0])
        values = item['values']
        if not values:
            return
        vente_id = values[0]
        if not messagebox.askyesno('Confirmer', f"Voulez-vous vraiment supprimer la vente #{vente_id} ?\n\nCette action va :\n• Restaurer la quantité en stock\n• Restaurer le crédit client si c'était une vente crédit"):
            return
        try:
            conn = sqlite3.connect('data.db')
            cur = conn.cursor()
            cur.execute('SELECT produit_id, client_id, quantite, total, statut FROM ventes WHERE id = ?', (vente_id,))
            vente = cur.fetchone()
            if not vente:
                messagebox.showerror('Erreur', f'Vente #{vente_id} introuvable.')
                conn.close()
                return
            produit_id, client_id, quantite, total, statut = vente
            if produit_id:
                cur.execute('UPDATE articles SET quantite = quantite + ? WHERE code = ?', (quantite, produit_id))
            if statut and 'credit' in str(statut).lower() and client_id:
                cur.execute('UPDATE clients SET solde_credit = MAX(0, solde_credit - ?) WHERE id = ?', (total, client_id))
            cur.execute('DELETE FROM ventes WHERE id = ?', (vente_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo('Succès', f"Vente #{vente_id} supprimée avec succès.\n✓ Stock restauré.\n{('✓ Crédit client restauré.' if statut and chr(99) + 'redit' in str(statut).lower() else '')}")
            afficher_ventes_et_total(tree, total_label, current_list_date.get().strip())
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            messagebox.showerror('Erreur', f'Impossible de supprimer la vente:\n{e}')
    btn_supprimer = tk.Button(totaux_frame, text='🗑 Supprimer vente', command=supprimer_vente_selectionnee, bg='#e53935', fg='white', font=('Arial', 10, 'bold'), padx=10)
    btn_supprimer.pack(side='right', padx=5)
    btn_actualiser = tk.Button(totaux_frame, text='Actualiser', command=lambda: afficher_ventes_et_total(tree, total_label, current_list_date.get().strip()), bg='#2196F3', fg='white', font=('Arial', 10, 'bold'), padx=10)
    btn_actualiser.pack(side='right', padx=10)
    register_sales_view(tree, total_label, lambda: current_list_date.get().strip())
    afficher_ventes_et_total(tree, total_label, current_list_date.get().strip())