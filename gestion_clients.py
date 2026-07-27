import sqlite3
from database import connecter
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

def ajouter_client(nom, telephone, adresse, email, identifiant_fiscal=None, solde_credit=0):
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('PRAGMA table_info(clients)')
        cols = [r[1] for r in cur.fetchall()]
        if 'identifiant_fiscal' not in cols:
            try:
                cur.execute('ALTER TABLE clients ADD COLUMN identifiant_fiscal TEXT')
                conn.commit()
            except Exception:
                pass
        cur.execute('\n            INSERT INTO clients (nom, telephone, adresse, email, identifiant_fiscal, solde_credit)\n            VALUES (?, ?, ?, ?, ?, ?)\n        ', (nom, telephone, adresse, email, identifiant_fiscal, solde_credit))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def supprimer_client(client_id):
    conn = connecter()
    cur = conn.cursor()
    cur.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()

def modifier_client(client_id, nom=None, telephone=None, adresse=None, email=None, identifiant_fiscal=None, solde_credit=None, montant_paye=None, date_dernier_paiement=None):
    conn = connecter()
    cur = conn.cursor()
    champs = []
    valeurs = []
    if nom:
        champs.append('nom = ?')
        valeurs.append(nom)
    if telephone:
        champs.append('telephone = ?')
        valeurs.append(telephone)
    if adresse:
        champs.append('adresse = ?')
        valeurs.append(adresse)
    if email:
        champs.append('email = ?')
        valeurs.append(email)
    if identifiant_fiscal is not None:
        try:
            cur.execute('PRAGMA table_info(clients)')
            cols = [r[1] for r in cur.fetchall()]
            if 'identifiant_fiscal' not in cols:
                try:
                    cur.execute('ALTER TABLE clients ADD COLUMN identifiant_fiscal TEXT')
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass
        champs.append('identifiant_fiscal = ?')
        valeurs.append(identifiant_fiscal)
    if solde_credit is not None:
        champs.append('solde_credit = ?')
        valeurs.append(solde_credit)
    if montant_paye is not None:
        champs.append('montant_paye = ?')
        valeurs.append(montant_paye)
    if date_dernier_paiement is not None:
        champs.append('date_dernier_paiement = ?')
        valeurs.append(date_dernier_paiement)
    if not champs:
        return False
    valeurs.append(client_id)
    cur.execute(f"UPDATE clients SET {', '.join(champs)} WHERE id = ?", valeurs)
    conn.commit()
    conn.close()
    return True

def lister_clients():
    conn = connecter()
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(clients)')
    columns = [row[1] for row in cur.fetchall()]
    if 'montant_paye' not in columns:
        cur.execute('ALTER TABLE clients ADD COLUMN montant_paye REAL DEFAULT 0')
    if 'date_dernier_paiement' not in columns:
        cur.execute('ALTER TABLE clients ADD COLUMN date_dernier_paiement TEXT')
    if 'identifiant_fiscal' not in columns:
        try:
            cur.execute('ALTER TABLE clients ADD COLUMN identifiant_fiscal TEXT')
        except Exception:
            pass
    conn.commit()
    cur.execute('SELECT id, nom, telephone, adresse, email, solde_credit, identifiant_fiscal, montant_paye, date_dernier_paiement FROM clients')
    clients = cur.fetchall()
    conn.close()
    return clients

def _compute_client_credit_and_totals(client_id: int) -> tuple[float, float, float]:
    """Retourne (total_ventes, total_reglements, reste) pour un client.
    S'adapte au schéma présent (colonnes v.total/v.prix/v.quantite) et évite les erreurs.
    NOTE: On ignore désormais tout "solde_credit" saisi manuellement pour éviter les doublons.
    """
    total_ventes = 0.0
    total_reglements = 0.0
    solde_init = 0.0
    with connecter() as conn:
        try:
            conn.execute('PRAGMA busy_timeout = 5000')
        except Exception:
            pass
        cur = conn.cursor()
        solde_init = 0.0
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ventes'")
            has_ventes = cur.fetchone() is not None
        except Exception:
            has_ventes = False
        if has_ventes:
            try:
                cur.execute('PRAGMA table_info(ventes)')
                ventes_cols = {r[1] for r in cur.fetchall()}
            except Exception:
                ventes_cols = set()
            has_col_prix = 'prix' in ventes_cols
            has_col_total = 'total' in ventes_cols
            prix_expr = 'COALESCE(v.prix, 0)' if has_col_prix else 'ROUND(CASE WHEN COALESCE(v.quantite,0)=0 THEN 0 ELSE COALESCE(v.total,0)/COALESCE(v.quantite,1) END, 2)'
            if has_col_total:
                try:
                    cur.execute('SELECT COALESCE(SUM(total),0) FROM ventes WHERE client_id=?', (client_id,))
                    total_ventes = cur.fetchone()[0] or 0.0
                except Exception:
                    total_ventes = 0.0
            else:
                try:
                    cur.execute(f'SELECT COALESCE(SUM(COALESCE(quantite,0) * ({prix_expr})),0) FROM ventes WHERE client_id=?', (client_id,))
                    total_ventes = cur.fetchone()[0] or 0.0
                except Exception:
                    total_ventes = 0.0
        try:
            cur.execute('SELECT COALESCE(SUM(montant),0) FROM reglement_client WHERE client_id=?', (client_id,))
            total_reglements = cur.fetchone()[0] or 0.0
        except Exception:
            total_reglements = 0.0
    reste = (solde_init or 0.0) + (total_ventes or 0.0) - (total_reglements or 0.0)
    return (total_ventes, total_reglements, reste)

def ajouter_reglement_client(client_id, date, montant):
    conn = connecter()
    cur = conn.cursor()
    cur.execute('\n        CREATE TABLE IF NOT EXISTS reglement_client (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            client_id INTEGER,\n            date TEXT,\n            montant REAL\n        )\n    ')
    cur.execute('INSERT INTO reglement_client (client_id, date, montant) VALUES (?, ?, ?)', (client_id, date, montant))
    conn.commit()
    conn.close()
    return True

def lister_reglements_client(client_id):
    conn = connecter()
    cur = conn.cursor()
    cur.execute('\n        CREATE TABLE IF NOT EXISTS reglement_client (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            client_id INTEGER,\n            date TEXT,\n            montant REAL\n        )\n    ')
    cur.execute('PRAGMA table_info(reglement_client)')
    columns = [row[1] for row in cur.fetchall()]
    if 'client_id' not in columns:
        cur.execute('DROP TABLE IF EXISTS reglement_client')
        cur.execute('\n            CREATE TABLE reglement_client (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                client_id INTEGER,\n                date TEXT,\n                montant REAL\n            )\n        ')
        conn.commit()
    cur.execute('SELECT id, date, montant FROM reglement_client WHERE client_id = ? ORDER BY date DESC', (client_id,))
    reglements = cur.fetchall()
    conn.close()
    return reglements

class GestionClientsApp:

    def __init__(self, master=None):
        self.master = master if master else tk.Toplevel()
        self.master.title('Gestion des Clients')
        self.master.geometry('900x500')
        self.selected_clients = {}
        self.create_widgets()
        self.refresh_table()
        try:
            self._init_search_placeholder()
            self.master.after(150, self._focus_client_search)
        except Exception:
            pass
        try:
            self.master.bind('<Control-f>', lambda e: self._focus_client_search())
            self.master.bind('<Control-F>', lambda e: self._focus_client_search())
            self.master.bind('<Control-l>', lambda e: self._clear_client_search())
            self.master.bind('<Control-L>', lambda e: self._clear_client_search())
        except Exception:
            pass

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill='both', expand=True)
        self.tab_clients = tk.Frame(self.notebook)
        self.notebook.add(self.tab_clients, text='Clients')
        search_frm = tk.LabelFrame(self.tab_clients, text='Recherche rapide', padx=8, pady=6)
        search_frm.pack(fill='x', padx=10, pady=(10, 0))
        tk.Label(search_frm, text='🔎 Rechercher (Ctrl+F):', font=('Arial', 10, 'bold')).pack(side='left')
        self.entry_search_clients = tk.Entry(search_frm, width=42)
        self.entry_search_clients.pack(side='left', padx=(6, 6))
        self.entry_search_clients.bind('<KeyRelease>', lambda e: self.refresh_table())
        self.entry_search_clients.bind('<Return>', lambda e: self.refresh_table())
        self.entry_search_clients.bind('<FocusIn>', self._on_search_focus_in)
        self.entry_search_clients.bind('<FocusOut>', self._on_search_focus_out)
        tk.Button(search_frm, text='🔎 Rechercher', command=self.refresh_table, bg='#0984e3', fg='white', font=('Arial', 10, 'bold'), padx=8, pady=2).pack(side='left', padx=(0, 4))
        tk.Button(search_frm, text='Effacer', command=lambda: self._clear_client_search()).pack(side='left')
        columns = ('Sélection', 'ID', 'Nom', 'Téléphone', 'Adresse', 'Email', 'Montant payé', 'Date dernier paiement')
        self.tree = ttk.Treeview(self.tab_clients, columns=columns, show='headings', height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            if col == 'Sélection':
                self.tree.column(col, anchor='center', width=50)
            elif col == 'ID':
                self.tree.column(col, anchor='center', width=70)
            elif col in ('Nom', 'Adresse'):
                self.tree.column(col, anchor='center', width=160)
            else:
                self.tree.column(col, anchor='center', width=130)
        self.tree_scroll = ttk.Scrollbar(self.tab_clients, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        table_container = tk.Frame(self.tab_clients)
        table_container.pack(fill='both', expand=True, padx=10, pady=10)
        self.tree.pack(in_=table_container, side='left', fill='both', expand=True)
        self.tree_scroll.pack(in_=table_container, side='right', fill='y')
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        self.tree.bind('<<TreeviewSelect>>', lambda e: self._on_tree_select())
        self.tree.bind('<Button-1>', self._on_tree_click)
        self.status_clients = tk.Label(self.tab_clients, text='', anchor='w')
        self.status_clients.pack(fill='x', padx=10, pady=(0, 6))
        frm = tk.Frame(self.tab_clients)
        frm.pack(fill='x', padx=10, pady=5)
        tk.Label(frm, text='Nom:').grid(row=0, column=0)
        self.entry_nom = tk.Entry(frm, width=18)
        self.entry_nom.grid(row=0, column=1)
        tk.Label(frm, text='Téléphone:').grid(row=0, column=2)
        self.entry_tel = tk.Entry(frm, width=18)
        self.entry_tel.grid(row=0, column=3)
        tk.Label(frm, text='Adresse:').grid(row=0, column=4)
        self.entry_adr = tk.Entry(frm, width=18)
        self.entry_adr.grid(row=0, column=5)
        tk.Label(frm, text='Email:').grid(row=0, column=6)
        self.entry_email = tk.Entry(frm, width=18)
        self.entry_email.grid(row=0, column=7)
        tk.Label(frm, text='Matricule fiscale:').grid(row=0, column=8)
        self.entry_mf = tk.Entry(frm, width=18)
        self.entry_mf.grid(row=0, column=9)
        tk.Label(frm, text='Solde crédit:').grid(row=0, column=10)
        self.entry_solde = tk.Entry(frm, width=18)
        self.entry_solde.grid(row=0, column=11)
        btns = tk.Frame(self.tab_clients)
        btns.pack(fill='x', padx=10, pady=5)
        tk.Button(btns, text='Ajouter', command=self.ajouter_client, bg='#44bd32', fg='white').pack(side='left', padx=5)
        tk.Button(btns, text='Modifier', command=self.modifier_client, bg='#273c75', fg='white').pack(side='left', padx=5)
        tk.Button(btns, text='Supprimer', command=self.supprimer_client, bg='#e84118', fg='white').pack(side='left', padx=5)
        tk.Button(btns, text='Voir règlements', command=self.open_reglements_tab, bg='#0097e6', fg='white').pack(side='left', padx=5)
        tk.Button(btns, text='Fermer', command=self.master.destroy, bg='#718093', fg='white').pack(side='right', padx=5)
        self.tab_reglements = tk.Frame(self.notebook)
        self.notebook.add(self.tab_reglements, text='Règlements client')
        self.tree_reglements = ttk.Treeview(self.tab_reglements, columns=('ID', 'Date', 'Montant', 'Commentaire'), show='headings', height=12)
        for col in ('ID', 'Date', 'Montant', 'Commentaire'):
            self.tree_reglements.heading(col, text=col)
            self.tree_reglements.column(col, anchor='center', width=120)
        self.tree_reglements.pack(fill='both', expand=True, padx=10, pady=10)
        frm_reg = tk.Frame(self.tab_reglements)
        frm_reg.pack(fill='x', padx=10, pady=5)
        tk.Label(frm_reg, text='Date:').grid(row=0, column=0)
        self.entry_date = tk.Entry(frm_reg, width=12)
        self.entry_date.grid(row=0, column=1)
        try:
            if not self.entry_date.get().strip():
                self.entry_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        except Exception:
            pass
        tk.Label(frm_reg, text='Montant:').grid(row=0, column=2)
        self.entry_montant = tk.Entry(frm_reg, width=12)
        self.entry_montant.grid(row=0, column=3)
        tk.Label(frm_reg, text='DT').grid(row=0, column=4)
        tk.Button(frm_reg, text='Ajouter règlement', command=self.ajouter_reglement, bg='#44bd32', fg='white').grid(row=0, column=5, padx=5)
        tk.Button(frm_reg, text='Fermer', command=self.master.destroy, bg='#718093', fg='white').grid(row=0, column=6, padx=5)
        self.info_client = tk.Label(self.master, text='', font=('Arial', 10), anchor='w', justify='left')
        self.info_client.pack(fill='x', padx=10, pady=(0, 5))
        self.info_reste = tk.Label(self.master, text='', font=('Arial', 10, 'bold'), fg='#2d3436', anchor='w', justify='left')
        self.info_reste.pack(fill='x', padx=10, pady=(0, 8))

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.selected_clients.clear()
        clients = lister_clients()
        q = ''
        try:
            q = (self.entry_search_clients.get() or '').strip().lower()
        except Exception:
            q = ''
        if q:
            filtered = []
            for c in clients:
                try:
                    cid = str(c[0])
                    nom = (c[1] or '').lower()
                    tel = (c[2] or '').lower()
                    adr = (c[3] or '').lower()
                    email = (c[4] or '').lower()
                except Exception:
                    continue
                if q in cid or q in nom or q in tel or (q in adr) or (q in email):
                    filtered.append(c)
            clients = filtered
        for client in clients:
            item_id = self.tree.insert('', 'end', values=('☐', client[0], client[1], client[2], client[3], client[4], client[6], client[7]))
            self.selected_clients[item_id] = client[0]
        try:
            self.status_clients.config(text=f'Clients affichés: {len(clients)}')
        except Exception:
            pass

    def _focus_client_search(self):
        try:
            self.entry_search_clients.focus_set()
            self.entry_search_clients.select_range(0, tk.END)
        except Exception:
            pass

    def _clear_client_search(self):
        try:
            self.entry_search_clients.delete(0, tk.END)
        except Exception:
            pass
        try:
            self.refresh_table()
        except Exception:
            pass

    def _init_search_placeholder(self):
        try:
            self._search_placeholder = 'Tapez un nom, téléphone, email ou ID...'
            self._search_entry_fg_default = self.entry_search_clients.cget('fg')
            if not (self.entry_search_clients.get() or '').strip():
                self.entry_search_clients.insert(0, self._search_placeholder)
                self.entry_search_clients.config(fg='#888')
        except Exception:
            pass

    def _on_search_focus_in(self, event=None):
        try:
            txt = self.entry_search_clients.get()
            if txt == getattr(self, '_search_placeholder', None):
                self.entry_search_clients.delete(0, tk.END)
                self.entry_search_clients.config(fg=self._search_entry_fg_default)
        except Exception:
            pass

    def _on_search_focus_out(self, event=None):
        try:
            txt = (self.entry_search_clients.get() or '').strip()
            if not txt:
                self.entry_search_clients.insert(0, getattr(self, '_search_placeholder', ''))
                self.entry_search_clients.config(fg='#888')
        except Exception:
            pass

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.tree.identify_column(event.x)
            if column == '#1':
                item = self.tree.identify_row(event.y)
                if item:
                    vals = self.tree.item(item).get('values', [])
                    if vals:
                        current = vals[0]
                        new_val = '☑' if current == '☐' else '☐'
                        new_vals = list(vals)
                        new_vals[0] = new_val
                        self.tree.item(item, values=new_vals)

    def _on_tree_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.tree.identify_column(event.x)
            if column != '#1':
                self.open_fiche_client()

    def _on_tree_select(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0]).get('values', [])
        if not vals:
            return
        try:
            self.entry_nom.delete(0, tk.END)
            self.entry_nom.insert(0, vals[2])
            self.entry_tel.delete(0, tk.END)
            self.entry_tel.insert(0, vals[3])
            self.entry_adr.delete(0, tk.END)
            self.entry_adr.insert(0, vals[4])
            self.entry_email.delete(0, tk.END)
            self.entry_email.insert(0, vals[5])
            try:
                cid = int(vals[1])
                conn = connecter()
                cur = conn.cursor()
                cur.execute('PRAGMA table_info(clients)')
                cols = [r[1] for r in cur.fetchall()]
                mf_val = ''
                if 'identifiant_fiscal' in cols:
                    cur.execute('SELECT identifiant_fiscal FROM clients WHERE id=?', (cid,))
                    r = cur.fetchone()
                    mf_val = (r[0] if r else '') or ''
                conn.close()
                try:
                    self.entry_mf.delete(0, tk.END)
                    self.entry_mf.insert(0, mf_val)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    def ajouter_client(self):
        nom = self.entry_nom.get().strip()
        tel = self.entry_tel.get().strip()
        adr = self.entry_adr.get().strip()
        email = self.entry_email.get().strip()
        if not nom:
            messagebox.showwarning('Champs manquants', 'Le nom est obligatoire.')
            return
        mf = self.entry_mf.get().strip() or None
        if ajouter_client(nom, tel, adr, email, mf):
            self.refresh_table()
            self.entry_nom.delete(0, tk.END)
            self.entry_tel.delete(0, tk.END)
            self.entry_adr.delete(0, tk.END)
            self.entry_email.delete(0, tk.END)
            try:
                self.entry_mf.delete(0, tk.END)
            except Exception:
                pass
            messagebox.showinfo('Ajout', 'Client ajouté.')
        else:
            messagebox.showerror('Erreur', "Erreur lors de l'ajout (nom ou email déjà utilisé ?)")

    def supprimer_client(self):
        selected_ids = []
        for item in self.tree.get_children():
            vals = self.tree.item(item).get('values', [])
            if vals and vals[0] == '☑':
                selected_ids.append(vals[1])
        if not selected_ids:
            messagebox.showwarning('Sélection', 'Sélectionnez au moins un client à supprimer en cochant la case.')
            return
        if messagebox.askyesno('Confirmation', f'Supprimer {len(selected_ids)} client(s) ?'):
            conn = connecter()
            cur = conn.cursor()
            try:
                for client_id in selected_ids:
                    cur.execute('DELETE FROM clients WHERE id = ?', (client_id,))
                conn.commit()
                self.refresh_table()
                messagebox.showinfo('Suppression', f'{len(selected_ids)} client(s) supprimé(s).')
            except Exception as e:
                messagebox.showerror('Erreur', f'Erreur lors de la suppression: {e}')
            finally:
                conn.close()

    def modifier_client(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un client à modifier.')
            return
        item = self.tree.item(selected[0])
        client_id = item['values'][1]
        nom = self.entry_nom.get().strip()
        tel = self.entry_tel.get().strip()
        adr = self.entry_adr.get().strip()
        email = self.entry_email.get().strip()
        if not nom and (not tel) and (not adr) and (not email) and (not self.entry_mf.get().strip()):
            messagebox.showwarning('Champs manquants', 'Renseignez au moins un champ à modifier.')
            return
        mf = self.entry_mf.get().strip()
        if modifier_client(client_id, nom or None, tel or None, adr or None, email or None, mf or None):
            self.refresh_table()
            messagebox.showinfo('Modification', 'Client modifié.')
        else:
            messagebox.showerror('Erreur', 'Aucune modification effectuée.')

    def open_reglements_tab(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un client pour voir ses règlements.')
            return
        item = self.tree.item(selected[0])
        client_id = item['values'][1]
        self.selected_client_id = client_id
        self.notebook.select(self.tab_reglements)
        self.refresh_reglements_table()

    def refresh_reglements_table(self):
        for row in self.tree_reglements.get_children():
            self.tree_reglements.delete(row)
        if hasattr(self, 'selected_client_id'):
            for reg in lister_reglements_client(self.selected_client_id):
                self.tree_reglements.insert('', 'end', values=reg)

    def open_fiche_client(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un client à consulter.')
            return
        item = self.tree.item(selected[0])
        client_id = item['values'][1]
        client = [c for c in lister_clients() if c[0] == client_id][0]
        try:
            _, total_reglements, reste = _compute_client_credit_and_totals(client_id)
        except Exception:
            total_reglements, reste = (0.0, 0.0)
        win = tk.Toplevel(self.master)
        win.title(f'Fiche client : {client[1]}')
        win.geometry('420x300')
        labels = [('Nom', client[1]), ('Téléphone', client[2]), ('Adresse', client[3]), ('Email', client[4]), ('Solde crédit (calculé)', f'{max(reste, 0.0):.2f}'), ('Total payé', f'{total_reglements or 0.0:.2f}'), ('Date dernier paiement', client[7] if client[7] else '-')]
        for i, (lbl, val) in enumerate(labels):
            tk.Label(win, text=lbl + ' :', font=('Arial', 10, 'bold')).grid(row=i, column=0, sticky='e', padx=10, pady=5)
            tk.Label(win, text=val, font=('Arial', 10)).grid(row=i, column=1, sticky='w', padx=10, pady=5)
        tk.Button(win, text='Fermer', command=win.destroy, bg='#718093', fg='white').grid(row=len(labels), column=0, columnspan=2, pady=15)

class ReglementClientApp:

    def __init__(self, master=None):
        self.master = master if master else tk.Toplevel()
        self.master.title('Règlements des Clients')
        self.master.geometry('700x500')
        self.create_widgets()

    def create_widgets(self):
        self._build_search_ui()
        client_cols = ('ID', 'Nom', 'Téléphone', 'Email', 'Crédit')
        self.tree_clients = ttk.Treeview(self.master, columns=client_cols, show='headings', height=6)
        for col in client_cols:
            self.tree_clients.heading(col, text=col)
            self.tree_clients.column(col, anchor='center', width=120)
        self.tree_clients.pack(fill='x', expand=False, padx=10, pady=(10, 4))
        self.tree_clients.bind('<<TreeviewSelect>>', self._on_client_changed)
        try:
            self.tree_clients.tag_configure('ok', background='#d4edda', foreground='#155724')
            self.tree_clients.tag_configure('warn', background='#FFF59D', foreground='#5D4037')
            self.tree_clients.tag_configure('late', background='#f8d7da', foreground='#721c24')
            style = ttk.Style()
            style.map('Treeview', background=[('selected', 'black')], foreground=[('selected', 'white')])
        except Exception:
            pass
        self.clients_all = lister_clients()
        self.clients = list(self.clients_all)
        self.refresh_clients_list()
        columns = ('ID', 'Nom', 'Date', 'Montant')
        self.tree = ttk.Treeview(self.master, columns=columns, show='headings', height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=120)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
        frm = tk.Frame(self.master)
        frm.pack(fill='x', padx=10, pady=5)
        tk.Label(frm, text='Date:').grid(row=0, column=0)
        self.entry_date = tk.Entry(frm, width=12)
        self.entry_date.grid(row=0, column=1)
        try:
            if not self.entry_date.get().strip():
                self.entry_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        except Exception:
            pass
        tk.Label(frm, text='Montant:').grid(row=0, column=2)
        self.entry_montant = tk.Entry(frm, width=12)
        self.entry_montant.grid(row=0, column=3)
        tk.Button(frm, text='Ajouter règlement', command=self.ajouter_reglement, bg='#44bd32', fg='white').grid(row=0, column=4, padx=5)
        tk.Button(frm, text='Régler tout le crédit', command=self.remplir_montant_credit, bg='#e84118', fg='white').grid(row=0, column=5, padx=5)
        tk.Button(frm, text='Voir détail crédit', command=self.voir_detail_credit_client, bg='#8c7ae6', fg='white').grid(row=0, column=6, padx=5)
        tk.Button(frm, text='Voir détails', command=self.voir_details_reglement, bg='#00a8ff', fg='white').grid(row=0, column=7, padx=5)
        tk.Button(frm, text='Fermer', command=self.master.destroy, bg='#718093', fg='white').grid(row=0, column=8, padx=5)
        self.info_client = tk.Label(self.master, text='', font=('Arial', 10), anchor='w', justify='left')
        self.info_client.pack(fill='x', padx=10, pady=(-5, 0))
        self.entry_montant.bind('<KeyRelease>', self._update_reste_apres_paiement)
        self.entry_montant.bind('<FocusOut>', self._update_reste_apres_paiement)
        self._select_first_client()
        self.refresh_table()
        self.afficher_infos_client()
        self._update_reste_apres_paiement()

    def _on_client_changed(self, event=None):
        try:
            self.refresh_table()
        except Exception:
            pass
        try:
            self.afficher_infos_client()
        except Exception:
            pass
        try:
            self._update_reste_apres_paiement()
        except Exception:
            pass

    def _select_first_client(self):
        try:
            children = self.tree_clients.get_children()
            if children:
                self.tree_clients.selection_set(children[0])
                self.tree_clients.focus(children[0])
        except Exception:
            pass

    def refresh_clients_list(self):
        for row in self.tree_clients.get_children():
            self.tree_clients.delete(row)
        if not hasattr(self, 'clients'):
            try:
                self.clients_all = lister_clients()
            except Exception:
                self.clients_all = []
            self.clients = list(self.clients_all)
        for c in self.clients:
            try:
                _, _, reste = _compute_client_credit_and_totals(c[0])
            except Exception:
                reste = 0.0
            reste_val = max(reste or 0.0, 0.0)
            tag_tuple = tuple()
            try:
                if reste_val <= 0:
                    tag_tuple = ('ok',)
                else:
                    date_str = None
                    try:
                        date_str = c[7] if len(c) > 7 else None
                    except Exception:
                        date_str = None
                    days = None
                    if date_str:
                        ds = str(date_str).strip()
                        fmts = ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y')
                        for fmt in fmts:
                            try:
                                d = datetime.strptime(ds[:10], fmt).date()
                                days = (datetime.now().date() - d).days
                                break
                            except Exception:
                                continue
                    if days is None:
                        tag_tuple = ('late',)
                    elif days > 7:
                        tag_tuple = ('late',)
                    else:
                        tag_tuple = tuple()
            except Exception:
                tag_tuple = tuple()
            self.tree_clients.insert('', 'end', values=(c[0], c[1], c[2], c[4], f'{reste_val:.2f}'), tags=tag_tuple)

    def _build_search_ui(self):
        frm_search = tk.Frame(self.master)
        frm_search.pack(fill='x', padx=10, pady=(8, 0))
        tk.Label(frm_search, text='Recherche client:').pack(side='left')
        self.entry_search = tk.Entry(frm_search, width=30)
        self.entry_search.pack(side='left', padx=(6, 6))
        self.entry_search.bind('<KeyRelease>', self._on_search_change)
        tk.Button(frm_search, text='Effacer', command=self._clear_search).pack(side='left')

    def _clear_search(self):
        try:
            self.entry_search.delete(0, tk.END)
        except Exception:
            pass
        self.apply_client_filter('')

    def _on_search_change(self, event=None):
        txt = (self.entry_search.get() or '').strip()
        self.apply_client_filter(txt)

    def apply_client_filter(self, query: str):
        try:
            base = list(self.clients_all)
        except Exception:
            base = []
        q = query.lower()
        if q:
            filtered = []
            for c in base:
                try:
                    cid = str(c[0])
                    nom = (c[1] or '').lower()
                    tel = (c[2] or '').lower()
                    email = (c[4] or '').lower()
                except Exception:
                    continue
                if q in cid or q in nom or q in tel or (q in email):
                    filtered.append(c)
            self.clients = filtered
        else:
            self.clients = base
        sel_id, _ = self._get_selected_client() if hasattr(self, '_get_selected_client') else (None, None)
        self.refresh_clients_list()
        if sel_id:
            self._select_client_row_by_id(sel_id)

    def _get_selected_client(self):
        sel = self.tree_clients.selection()
        if not sel:
            return (None, None)
        item = self.tree_clients.item(sel[0])
        vals = item.get('values', [])
        if not vals:
            return (None, None)
        cid = vals[0]
        for c in self.clients:
            if c[0] == cid:
                return (cid, c)
        return (cid, None)

    def _status_dot(self, client_id: int) -> str:
        try:
            _, _, reste = _compute_client_credit_and_totals(client_id)
            return '[Crédit]' if (reste or 0) > 0 else '[Payé]'
        except Exception:
            return '[Payé]'

    def _client_display_values(self) -> list[str]:
        vals = []
        for c in self.clients:
            cid = c[0]
            dot = self._status_dot(cid)
            vals.append(f'{dot} {c[1]} (ID {cid})')
        return vals

    def _select_client_by_id(self, client_id: int):
        try:
            for i, c in enumerate(self.clients):
                if c[0] == client_id:
                    self.combo_client.current(i)
                    break
        except Exception:
            pass

    def refresh_table(self, event=None):
        for row in self.tree.get_children():
            self.tree.delete(row)
        client_id, client = self._get_selected_client()
        if not client_id:
            return
        nom = client[1] if client else '-'
        for reg in lister_reglements_client(client_id):
            self.tree.insert('', 'end', values=(reg[0], nom, reg[1], reg[2]))

    def afficher_infos_client(self, event=None):
        client_id, client = self._get_selected_client()
        if not client_id or not client:
            self.info_client.config(text='')
            return
        total_ventes, total_reglements, reste = _compute_client_credit_and_totals(client_id)
        txt = (self.entry_montant.get() or '').strip()
        try:
            montant = float(txt) if txt else 0.0
        except Exception:
            montant = 0.0
        reste_apres = max(reste or 0.0, 0.0) - (montant or 0.0)
        if reste_apres < 0:
            reste_apres = 0.0
        info = f'Téléphone : {client[2]}    Email : {client[4]}    Solde crédit (calculé) : {reste:.2f}    Total payé : {total_reglements:.2f}    Reste après paiement : {reste_apres:.2f}'
        self.info_client.config(text=info)

    def _update_reste_apres_paiement(self, event=None):
        """Met à jour l'affichage du reste après paiement en appelant afficher_infos_client."""
        try:
            self.afficher_infos_client()
        except Exception:
            pass

    def remplir_montant_credit(self):
        client_id, _ = self._get_selected_client()
        if not client_id:
            messagebox.showwarning('Sélection', 'Sélectionnez un client.')
            return
        _, _, reste = _compute_client_credit_and_totals(client_id)
        reste = max(reste or 0.0, 0.0)
        self.entry_montant.delete(0, tk.END)
        self.entry_montant.insert(0, f'{reste:.2f}')
        if not self.entry_date.get().strip():
            self.entry_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.afficher_infos_client()
        self._update_reste_apres_paiement()

    def voir_details_reglement(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un règlement pour voir ses détails.')
            return
        item = self.tree.item(selected[0])
        values = item.get('values', [])
        if not values:
            messagebox.showwarning('Sélection', 'Sélection invalide.')
            return
        reglement_id = values[0]
        conn = connecter()
        cur = conn.cursor()
        cur.execute('\n            CREATE TABLE IF NOT EXISTS reglement_client_details (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                reglement_id INTEGER NOT NULL,\n                article_code TEXT,\n                article_nom TEXT,\n                quantite REAL,\n                montant_applique REAL NOT NULL,\n                vente_id INTEGER,\n                notes TEXT,\n                FOREIGN KEY(reglement_id) REFERENCES reglement_client(id)\n            )\n            ')
        conn.commit()
        cur.execute("\n            SELECT COALESCE(article_nom,''), COALESCE(quantite,''), COALESCE(montant_applique,0),\n                   COALESCE(vente_id,''), COALESCE(notes,'')\n            FROM reglement_client_details\n            WHERE reglement_id=?\n            ORDER BY id\n            ", (reglement_id,))
        rows = cur.fetchall()
        conn.close()
        dlg = tk.Toplevel(self.master)
        dlg.title(f'Détails du règlement #{reglement_id}')
        dlg.geometry('720x360')
        columns = ('Article', 'Quantité', 'Montant appliqué', 'Vente ID', 'Notes')
        tree = ttk.Treeview(dlg, columns=columns, show='headings', height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', width=130)
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        if not rows:
            tk.Label(dlg, text='Aucun détail enregistré pour ce règlement.', fg='#555').pack(pady=(0, 10))
        else:
            for r in rows:
                tree.insert('', 'end', values=r)
        tk.Button(dlg, text='Fermer', command=dlg.destroy).pack(pady=6)

    def _select_client_row_by_id(self, client_id: int):
        try:
            for iid in self.tree_clients.get_children():
                item = self.tree_clients.item(iid)
                vals = item.get('values', [])
                if vals and vals[0] == client_id:
                    self.tree_clients.selection_set(iid)
                    self.tree_clients.focus(iid)
                    self.tree_clients.see(iid)
                    break
        except Exception:
            pass

    def ajouter_reglement(self):
        client_id, _ = self._get_selected_client()
        if not client_id:
            messagebox.showwarning('Sélection', 'Sélectionnez un client.')
            return
        date = self.entry_date.get().strip()
        montant = self.entry_montant.get().strip()
        try:
            montant_val = float(montant)
        except Exception:
            messagebox.showerror('Erreur', 'Montant invalide.')
            return
        if not date or not montant:
            messagebox.showwarning('Champs manquants', 'Date et montant sont obligatoires.')
            return
        ajouter_reglement_client(client_id, date, montant_val)
        total_ventes, total_reglements, reste = _compute_client_credit_and_totals(client_id)
        try:
            modifier_client(client_id, montant_paye=total_reglements, date_dernier_paiement=date)
        except Exception:
            pass
        self.refresh_clients_list()
        self._select_client_row_by_id(client_id)
        self.afficher_infos_client()
        try:
            self._update_reste_apres_paiement()
        except Exception:
            pass
        self.entry_montant.delete(0, tk.END)
        self.refresh_table()

    def voir_detail_credit_client(self):
        client_id, client = self._get_selected_client()
        if not client_id:
            messagebox.showwarning('Sélection', 'Sélectionnez un client.')
            return
        client_nom = client[1] if client else 'Client'
        conn = connecter()
        cur = conn.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ventes'")
            has_ventes = cur.fetchone() is not None
        except Exception:
            has_ventes = False
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
            has_articles = cur.fetchone() is not None
        except Exception:
            has_articles = False
        ventes_cols = set()
        if has_ventes:
            try:
                cur.execute('PRAGMA table_info(ventes)')
                ventes_cols = {r[1] for r in cur.fetchall()}
            except Exception:
                ventes_cols = set()
        has_col_prix = 'prix' in ventes_cols
        has_col_total = 'total' in ventes_cols
        prix_expr = 'COALESCE(v.prix, 0)' if has_col_prix else 'ROUND(CASE WHEN COALESCE(v.quantite,0)=0 THEN 0 ELSE COALESCE(v.total,0)/COALESCE(v.quantite,1) END, 2)'
        total_expr = 'COALESCE(v.total, 0)' if has_col_total else f'ROUND(COALESCE(v.quantite,0) * ({prix_expr}), 2)'
        rows = []
        if has_ventes:
            if has_articles:
                query = f"\n                    SELECT v.id,\n                           COALESCE(v.date,''),\n                           COALESCE(a.nom,''),\n                           COALESCE(v.quantite,0),\n                           {prix_expr} as prix,\n                           {total_expr} as total\n                    FROM ventes v\n                    JOIN articles a ON a.code = v.produit_id\n                    WHERE v.client_id = ?\n                    ORDER BY v.date DESC, v.id DESC\n                "
            else:
                query = f"\n                    SELECT v.id,\n                           COALESCE(v.date,''),\n                           COALESCE(v.produit_id,''),\n                           COALESCE(v.quantite,0),\n                           {prix_expr} as prix,\n                           {total_expr} as total\n                    FROM ventes v\n                    WHERE v.client_id = ?\n                    ORDER BY v.date DESC, v.id DESC\n                "
            cur.execute(query, (client_id,))
            rows = cur.fetchall()
        if has_ventes:
            if has_col_total:
                try:
                    cur.execute('SELECT COALESCE(SUM(total),0) FROM ventes WHERE client_id= ?', (client_id,))
                    total_ventes = cur.fetchone()[0] or 0.0
                except Exception:
                    total_ventes = 0.0
            else:
                try:
                    cur.execute(f'SELECT COALESCE(SUM(COALESCE(quantite,0) * ({prix_expr})),0) FROM ventes WHERE client_id= ?', (client_id,))
                    total_ventes = cur.fetchone()[0] or 0.0
                except Exception:
                    total_ventes = 0.0
        else:
            total_ventes = 0.0
        try:
            cur.execute('SELECT COALESCE(SUM(montant),0) FROM reglement_client WHERE client_id= ?', (client_id,))
            total_reglements = cur.fetchone()[0] or 0.0
        except Exception:
            total_reglements = 0.0
        conn.close()
        reste_theorique = (total_ventes or 0.0) - (total_reglements or 0.0)
        dlg = tk.Toplevel(self.master)
        dlg.title(f'Crédit du client — {client_nom} (ID {client_id})')
        dlg.geometry('860x420')
        header = tk.Label(dlg, text=f'Total ventes: {total_ventes:.2f}    Total règlements: {total_reglements:.2f}    Solde/Crédit: {reste_theorique:.2f}', font=('Arial', 11, 'bold'))
        header.pack(pady=(10, 4))
        columns = ('ID Vente', 'Date', 'Article', 'Quantité', 'Prix', 'Total')
        tree = ttk.Treeview(dlg, columns=columns, show='headings', height=14)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', width=130)
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        if not rows:
            tk.Label(dlg, text='Aucune vente trouvée pour ce client.', fg='#555').pack(pady=(0, 10))
        else:
            for r in rows:
                tree.insert('', 'end', values=r)

        def ouvrir_dialog_impression(type_doc):
            if not rows:
                messagebox.showwarning('Vide', 'Aucune vente à imprimer.', parent=dlg)
                return
            conf_dlg = tk.Toplevel(dlg)
            conf_dlg.title(f'Imprimer {type_doc.upper()}')
            conf_dlg.geometry('300x320')
            conf_dlg.grab_set()
            premier_id = tree.item(tree.get_children()[0])['values'][0] if tree.get_children() else '1'
            tk.Label(conf_dlg, text='Numéro:').pack(pady=(5, 0))
            ent_num = tk.Entry(conf_dlg)
            ent_num.insert(0, f'FAC-{premier_id}' if type_doc == 'facture' else f'BL-{premier_id}')
            ent_num.pack()
            tk.Label(conf_dlg, text='Date:').pack(pady=(5, 0))
            ent_date = tk.Entry(conf_dlg)
            ent_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
            ent_date.pack()
            tk.Label(conf_dlg, text='TVA (%):').pack(pady=(5, 0))
            ent_tva = tk.Entry(conf_dlg)
            ent_tva.insert(0, '0')
            ent_tva.pack()
            tk.Label(conf_dlg, text='Timbre (Dinars):').pack(pady=(5, 0))
            ent_timbre = tk.Entry(conf_dlg)
            ent_timbre.insert(0, '1.000')
            ent_timbre.pack()

            def valider():
                num = ent_num.get().strip()
                d = ent_date.get().strip()
                try:
                    tva_pct = float(ent_tva.get().strip() or 0)
                except ValueError:
                    tva_pct = 0.0
                try:
                    timbre_val = float(ent_timbre.get().strip().replace(',', '.') or 0)
                except ValueError:
                    timbre_val = 0.0
                lignes_pdf = []
                total_global = 0.0
                for child in tree.get_children():
                    vals = tree.item(child)['values']
                    article = vals[2]
                    quantite = vals[3]
                    prix = float(vals[4]) / 1000.0
                    total = float(vals[5]) / 1000.0
                    lignes_pdf.append({'code_article': '', 'designation': article, 'quantite': quantite, 'prix_unitaire': prix, 'total': total})
                    total_global += total
                societe_info = {'nom': '', 'adresse': '', 'telephone': '', 'email': '', 'identifiant_fiscal': '', 'logo_path': '', 'code_postal': '', 'ville': ''}
                try:
                    conn2 = connecter()
                    cur2 = conn2.cursor()
                    cur2.execute('SELECT nom, adresse, telephone, email, identifiant_fiscal, logo_path, code_postal, ville FROM etablissement LIMIT 1')
                    etab = cur2.fetchone()
                    conn2.close()
                    if etab:
                        societe_info = {'nom': etab[0] or '', 'adresse': etab[1] or '', 'telephone': etab[2] or '', 'email': etab[3] or '', 'identifiant_fiscal': etab[4] or '', 'logo_path': etab[5] or '', 'code_postal': etab[6] or '', 'ville': etab[7] or ''}
                except Exception:
                    pass
                conf_dlg.destroy()
                ttc_base = total_global
                base_ht = ttc_base / (1 + tva_pct / 100) if tva_pct > 0 else ttc_base
                tva_val = ttc_base - base_ht
                ttc_final = ttc_base + timbre_val
                try:
                    import tempfile, os, sys
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    legacy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py.bak')
                    env = {}
                    with open(legacy_path, 'r', encoding='utf-8', errors='ignore') as f:
                        exec(compile(f.read(), legacy_path, 'exec'), env)
                    gen_func = env.get(f'generate_{type_doc}_pdf')
                    if not gen_func:
                        raise Exception(f'Fonction generate_{type_doc}_pdf introuvable')
                    data = {'societe': societe_info, 'client': {'nom': client_nom, 'adresse': '', 'telephone': '', 'email': '', 'identifiant_fiscal': ''}, 'lignes': lignes_pdf, 'totaux': {'sous_total': float(ttc_base), 'remise': 0.0, 'base_ht': float(base_ht), 'tva_pourcent': float(tva_pct), 'tva': float(tva_val), 'timbre': float(timbre_val), 'ht': float(base_ht), 'ttc': float(ttc_final), 'total_ht': float(base_ht), 'total_ttc': float(ttc_final)}, 'paiement': {'mode': '', 'avance': 0.0, 'reste': 0.0}}
                    if type_doc == 'facture':
                        data['facture'] = {'numero': num, 'date': d}
                    else:
                        data['bl'] = {'numero': num, 'date': d}
                    tmp = tempfile.mktemp(suffix='.pdf')
                    if gen_func(data, tmp):
                        if os.name == 'nt':
                            os.startfile(tmp)
                        else:
                            import subprocess
                            subprocess.Popen(['xdg-open', tmp])
                except Exception as e:
                    messagebox.showerror(f'Erreur {type_doc.upper()}', f'Impossible de générer le document:\n{e}', parent=dlg)
            tk.Button(conf_dlg, text='🖨 Générer PDF', command=valider, bg='#2c3e50', fg='white', font=('Arial', 10, 'bold'), padx=10).pack(pady=15)

        def imprimer_facture():
            ouvrir_dialog_impression('facture')

        def imprimer_bl():
            ouvrir_dialog_impression('bl')

        def get_selected_vente():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning('Sélection', 'Sélectionnez une vente dans le tableau pour la supprimer.', parent=dlg)
                return None
            return tree.item(sel[0])['values']

        def supprimer_vente():
            vals = get_selected_vente()
            if not vals:
                return
            vente_id = vals[0]
            article = vals[2]
            if not messagebox.askyesno('Supprimer vente', f'Supprimer la vente #{vente_id} ({article}) ?\nCette action est irréversible.', parent=dlg):
                return
            try:
                conn2 = connecter()
                cur2 = conn2.cursor()
                cur2.execute('DELETE FROM ventes WHERE id=?', (vente_id,))
                conn2.commit()
                conn2.close()
                for iid in tree.selection():
                    tree.delete(iid)
                messagebox.showinfo('Supprimé', f'Vente #{vente_id} supprimée.', parent=dlg)
                try:
                    self.refresh_clients_list()
                    self._select_client_row_by_id(client_id)
                    self.afficher_infos_client()
                    self.refresh_table()
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror('Erreur', f'Impossible de supprimer la vente:\n{e}', parent=dlg)
        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text='🖨 Imprimer Facture', command=imprimer_facture, bg='#1e88e5', fg='white', font=('Arial', 10, 'bold'), padx=8).pack(side='left', padx=5)
        tk.Button(btn_frame, text='📄 Imprimer BL', command=imprimer_bl, bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'), padx=8).pack(side='left', padx=5)
        tk.Button(btn_frame, text='🗑 Supprimer vente', command=supprimer_vente, bg='#e53935', fg='white', font=('Arial', 10, 'bold'), padx=8).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Fermer', command=dlg.destroy, padx=8).pack(side='left', padx=5)

    def voir_details_reglement(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un règlement pour voir ses détails.')
            return
        item = self.tree.item(selected[0])
        values = item.get('values', [])
        if not values:
            messagebox.showwarning('Sélection', 'Sélection invalide.')
            return
        reglement_id = values[0]
        conn = connecter()
        cur = conn.cursor()
        cur.execute('\n            CREATE TABLE IF NOT EXISTS reglement_client_details (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                reglement_id INTEGER NOT NULL,\n                article_code TEXT,\n                article_nom TEXT,\n                quantite REAL,\n                montant_applique REAL NOT NULL,\n                vente_id INTEGER,\n                notes TEXT,\n                FOREIGN KEY(reglement_id) REFERENCES reglement_client(id)\n            )\n            ')
        conn.commit()
        cur.execute("\n            SELECT COALESCE(article_nom,''), COALESCE(quantite,''), COALESCE(montant_applique,0),\n                   COALESCE(vente_id,''), COALESCE(notes,'')\n            FROM reglement_client_details\n            WHERE reglement_id=?\n            ORDER BY id\n            ", (reglement_id,))
        rows = cur.fetchall()
        conn.close()
        dlg = tk.Toplevel(self.master)
        dlg.title(f'Détails du règlement #{reglement_id}')
        dlg.geometry('720x360')
        columns = ('Article', 'Quantité', 'Montant appliqué', 'Vente ID', 'Notes')
        tree = ttk.Treeview(dlg, columns=columns, show='headings', height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', width=130)
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        if not rows:
            tk.Label(dlg, text='Aucun détail enregistré pour ce règlement.', fg='#555').pack(pady=(0, 10))
        else:
            for r in rows:
                tree.insert('', 'end', values=r)
        tk.Button(dlg, text='Fermer', command=dlg.destroy).pack(pady=6)

    def ajouter_reglement(self):
        client_id, _ = self._get_selected_client()
        if not client_id:
            messagebox.showwarning('Sélection', 'Sélectionnez un client.')
            return
        date = self.entry_date.get().strip()
        montant = self.entry_montant.get().strip()
        try:
            montant_val = float(montant)
        except Exception:
            messagebox.showerror('Erreur', 'Montant invalide.')
            return
        if not date or not montant:
            messagebox.showwarning('Champs manquants', 'Date et montant sont obligatoires.')
            return
        ajouter_reglement_client(client_id, date, montant_val)
        total_ventes, total_reglements, reste = _compute_client_credit_and_totals(client_id)
        try:
            modifier_client(client_id, montant_paye=total_reglements, date_dernier_paiement=date)
        except Exception:
            pass
        self.refresh_clients_list()
        self._select_client_row_by_id(client_id)
        self.afficher_infos_client()
        try:
            self._update_reste_apres_paiement()
        except Exception:
            pass
        self.entry_montant.delete(0, tk.END)
        self.refresh_table()

    def voir_detail_credit_client(self):
        client_id, client = self._get_selected_client()
        if not client_id:
            messagebox.showwarning('Sélection', 'Sélectionnez un client.')
            return
        client_nom = client[1] if client else 'Client'
        conn = connecter()
        cur = conn.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ventes'")
            has_ventes = cur.fetchone() is not None
        except Exception:
            has_ventes = False
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
            has_articles = cur.fetchone() is not None
        except Exception:
            has_articles = False
        ventes_cols = set()
        if has_ventes:
            try:
                cur.execute('PRAGMA table_info(ventes)')
                ventes_cols = {r[1] for r in cur.fetchall()}
            except Exception:
                ventes_cols = set()
        has_col_prix = 'prix' in ventes_cols
        has_col_total = 'total' in ventes_cols
        prix_expr = 'COALESCE(v.prix, 0)' if has_col_prix else 'ROUND(CASE WHEN COALESCE(v.quantite,0)=0 THEN 0 ELSE COALESCE(v.total,0)/COALESCE(v.quantite,1) END, 2)'
        total_expr = 'COALESCE(v.total, 0)' if has_col_total else f'ROUND(COALESCE(v.quantite,0) * ({prix_expr}), 2)'
        rows = []
        if has_ventes:
            if has_articles:
                query = f"\n                    SELECT v.id,\n                           COALESCE(v.date,''),\n                           COALESCE(a.nom,''),\n                           COALESCE(v.quantite,0),\n                           {prix_expr} as prix,\n                           {total_expr} as total\n                    FROM ventes v\n                    JOIN articles a ON a.code = v.produit_id\n                    WHERE v.client_id = ?\n                    ORDER BY v.date DESC, v.id DESC\n                "
            else:
                query = f"\n                    SELECT v.id,\n                           COALESCE(v.date,''),\n                           COALESCE(v.produit_id,''),\n                           COALESCE(v.quantite,0),\n                           {prix_expr} as prix,\n                           {total_expr} as total\n                    FROM ventes v\n                    WHERE v.client_id = ?\n                    ORDER BY v.date DESC, v.id DESC\n                "
            cur.execute(query, (client_id,))
            rows = cur.fetchall()
        if has_ventes:
            if has_col_total:
                try:
                    cur.execute('SELECT COALESCE(SUM(total),0) FROM ventes WHERE client_id=?', (client_id,))
                    total_ventes = cur.fetchone()[0] or 0.0
                except Exception:
                    total_ventes = 0.0
            else:
                try:
                    cur.execute(f'SELECT COALESCE(SUM(COALESCE(quantite,0) * ({prix_expr})),0) FROM ventes WHERE client_id=?', (client_id,))
                    total_ventes = cur.fetchone()[0] or 0.0
                except Exception:
                    total_ventes = 0.0
        else:
            total_ventes = 0.0
        try:
            cur.execute('SELECT COALESCE(SUM(montant),0) FROM reglement_client WHERE client_id=?', (client_id,))
            total_reglements = cur.fetchone()[0] or 0.0
        except Exception:
            total_reglements = 0.0
        conn.close()
        reste_theorique = (total_ventes or 0.0) - (total_reglements or 0.0)
        dlg = tk.Toplevel(self.master)
        dlg.title(f'Crédit du client — {client_nom} (ID {client_id})')
        dlg.geometry('860x420')
        header = tk.Label(dlg, text=f'Total ventes: {total_ventes:.2f}    Total règlements: {total_reglements:.2f}    Solde/Crédit: {reste_theorique:.2f}', font=('Arial', 11, 'bold'))
        header.pack(pady=(10, 4))
        columns = ('ID Vente', 'Date', 'Article', 'Quantité', 'Prix', 'Total')
        tree = ttk.Treeview(dlg, columns=columns, show='headings', height=14)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', width=130)
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        if not rows:
            tk.Label(dlg, text='Aucune vente trouvée pour ce client.', fg='#555').pack(pady=(0, 10))
        else:
            for r in rows:
                tree.insert('', 'end', values=r)

        def ouvrir_dialog_impression(type_doc):
            if not rows:
                messagebox.showwarning('Vide', 'Aucune vente à imprimer.', parent=dlg)
                return
            conf_dlg = tk.Toplevel(dlg)
            conf_dlg.title(f'Imprimer {type_doc.upper()}')
            conf_dlg.geometry('300x320')
            conf_dlg.grab_set()
            premier_id = tree.item(tree.get_children()[0])['values'][0] if tree.get_children() else '1'
            tk.Label(conf_dlg, text='Numéro:').pack(pady=(5, 0))
            ent_num = tk.Entry(conf_dlg)
            ent_num.insert(0, f'FAC-{premier_id}' if type_doc == 'facture' else f'BL-{premier_id}')
            ent_num.pack()
            tk.Label(conf_dlg, text='Date:').pack(pady=(5, 0))
            ent_date = tk.Entry(conf_dlg)
            ent_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
            ent_date.pack()
            tk.Label(conf_dlg, text='TVA (%):').pack(pady=(5, 0))
            ent_tva = tk.Entry(conf_dlg)
            ent_tva.insert(0, '0')
            ent_tva.pack()
            tk.Label(conf_dlg, text='Timbre (Dinars):').pack(pady=(5, 0))
            ent_timbre = tk.Entry(conf_dlg)
            ent_timbre.insert(0, '1.000')
            ent_timbre.pack()

            def valider():
                num = ent_num.get().strip()
                d = ent_date.get().strip()
                try:
                    tva_pct = float(ent_tva.get().strip() or 0)
                except ValueError:
                    tva_pct = 0.0
                try:
                    timbre_val = float(ent_timbre.get().strip().replace(',', '.') or 0)
                except ValueError:
                    timbre_val = 0.0
                lignes_pdf = []
                total_global = 0.0
                for child in tree.get_children():
                    vals = tree.item(child)['values']
                    article = vals[2]
                    quantite = vals[3]
                    prix = float(vals[4]) / 1000.0
                    total = float(vals[5]) / 1000.0
                    lignes_pdf.append({'code_article': '', 'designation': article, 'quantite': quantite, 'prix_unitaire': prix, 'total': total})
                    total_global += total
                societe_info = {'nom': '', 'adresse': '', 'telephone': '', 'email': '', 'identifiant_fiscal': '', 'logo_path': '', 'code_postal': '', 'ville': ''}
                try:
                    conn2 = connecter()
                    cur2 = conn2.cursor()
                    cur2.execute('SELECT nom, adresse, telephone, email, identifiant_fiscal, logo_path, code_postal, ville FROM etablissement LIMIT 1')
                    etab = cur2.fetchone()
                    conn2.close()
                    if etab:
                        societe_info = {'nom': etab[0] or '', 'adresse': etab[1] or '', 'telephone': etab[2] or '', 'email': etab[3] or '', 'identifiant_fiscal': etab[4] or '', 'logo_path': etab[5] or '', 'code_postal': etab[6] or '', 'ville': etab[7] or ''}
                except Exception:
                    pass
                conf_dlg.destroy()
                ttc_base = total_global
                base_ht = ttc_base / (1 + tva_pct / 100) if tva_pct > 0 else ttc_base
                tva_val = ttc_base - base_ht
                ttc_final = ttc_base + timbre_val
                try:
                    import tempfile, os, sys
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    legacy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py.bak')
                    env = {}
                    with open(legacy_path, 'r', encoding='utf-8', errors='ignore') as f:
                        exec(compile(f.read(), legacy_path, 'exec'), env)
                    gen_func = env.get(f'generate_{type_doc}_pdf')
                    if not gen_func:
                        raise Exception(f'Fonction generate_{type_doc}_pdf introuvable')
                    data = {'societe': societe_info, 'client': {'nom': client_nom, 'adresse': '', 'telephone': '', 'email': '', 'identifiant_fiscal': ''}, 'lignes': lignes_pdf, 'totaux': {'sous_total': float(ttc_base), 'remise': 0.0, 'base_ht': float(base_ht), 'tva_pourcent': float(tva_pct), 'tva': float(tva_val), 'timbre': float(timbre_val), 'ht': float(base_ht), 'ttc': float(ttc_final), 'total_ht': float(base_ht), 'total_ttc': float(ttc_final)}, 'paiement': {'mode': '', 'avance': 0.0, 'reste': 0.0}}
                    if type_doc == 'facture':
                        data['facture'] = {'numero': num, 'date': d}
                    else:
                        data['bl'] = {'numero': num, 'date': d}
                    tmp = tempfile.mktemp(suffix='.pdf')
                    if gen_func(data, tmp):
                        if os.name == 'nt':
                            os.startfile(tmp)
                        else:
                            import subprocess
                            subprocess.Popen(['xdg-open', tmp])
                except Exception as e:
                    messagebox.showerror(f'Erreur {type_doc.upper()}', f'Impossible de générer le document:\n{e}', parent=dlg)
            tk.Button(conf_dlg, text='🖨 Générer PDF', command=valider, bg='#2c3e50', fg='white', font=('Arial', 10, 'bold'), padx=10).pack(pady=15)

        def imprimer_facture():
            ouvrir_dialog_impression('facture')

        def imprimer_bl():
            ouvrir_dialog_impression('bl')

        def get_selected_vente():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning('Sélection', 'Sélectionnez une vente dans le tableau pour la supprimer.', parent=dlg)
                return None
            return tree.item(sel[0])['values']

        def supprimer_vente():
            vals = get_selected_vente()
            if not vals:
                return
            vente_id = vals[0]
            article = vals[2]
            if not messagebox.askyesno('Supprimer vente', f'Supprimer la vente #{vente_id} ({article}) ?\nCette action est irréversible.', parent=dlg):
                return
            try:
                conn2 = connecter()
                cur2 = conn2.cursor()
                cur2.execute('DELETE FROM ventes WHERE id=?', (vente_id,))
                conn2.commit()
                conn2.close()
                for iid in tree.selection():
                    tree.delete(iid)
                messagebox.showinfo('Supprimé', f'Vente #{vente_id} supprimée.', parent=dlg)
                try:
                    self.refresh_clients_list()
                    self._select_client_row_by_id(client_id)
                    self.afficher_infos_client()
                    self.refresh_table()
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror('Erreur', f'Impossible de supprimer la vente:\n{e}', parent=dlg)
        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text='🖨 Imprimer Facture', command=imprimer_facture, bg='#1e88e5', fg='white', font=('Arial', 10, 'bold'), padx=8).pack(side='left', padx=5)
        tk.Button(btn_frame, text='📄 Imprimer BL', command=imprimer_bl, bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'), padx=8).pack(side='left', padx=5)
        tk.Button(btn_frame, text='🗑 Supprimer vente', command=supprimer_vente, bg='#e53935', fg='white', font=('Arial', 10, 'bold'), padx=8).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Fermer', command=dlg.destroy, padx=8).pack(side='left', padx=5)