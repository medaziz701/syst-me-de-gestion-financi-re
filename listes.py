import tkinter as tk
from tkinter import ttk
from database import connecter
from utils_codes import generate_unique_article_code

def _add_minimize_to_dock_button(win: tk.Toplevel):
    """Ajoute un bouton en haut de la fenêtre pour la réduire dans le dock de la fenêtre principale.
    Fonctionne même si l'utilisateur n'utilise pas le bouton système de minimisation."""
    try:
        bar = tk.Frame(win, bg='#eef2f5')
        bar.pack(fill='x', side='top')

        def _minimize():
            try:
                win.iconify()
            except Exception:
                pass
            try:
                win.withdraw()
            except Exception:
                pass
            try:
                win.event_generate('<<Iconify>>')
            except Exception:
                pass
        tk.Button(bar, text='Réduire dans le dock', command=_minimize, bg='#dfe6ee').pack(anchor='e', padx=6, pady=4)
    except Exception:
        pass

def afficher_liste(table, colonnes, titres):
    """Fonction générique pour afficher une liste"""
    win = tk.Toplevel()
    win.title(f'Liste des {table}')
    win.geometry('800x500')
    _add_minimize_to_dock_button(win)
    tree = ttk.Treeview(win, columns=colonnes, show='headings')
    for col, titre in zip(colonnes, titres):
        tree.heading(col, text=titre)
        tree.column(col, width=150, anchor='center')
    conn = connecter()
    cur = conn.cursor()
    cur.execute(f"SELECT {','.join(colonnes)} FROM {table}")
    for row in cur.fetchall():
        tree.insert('', 'end', values=row)
    conn.close()
    scrollbar = ttk.Scrollbar(win, orient='vertical', command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(expand=True, fill='both', padx=10, pady=10)
    btn_export = tk.Button(win, text='Exporter vers Excel', command=lambda: exporter_excel(table, colonnes))
    btn_export.pack(pady=10)

def exporter_excel(table, colonnes):
    """Exporter les données vers Excel"""
    import pandas as pd
    from tkinter import filedialog
    conn = connecter()
    df = pd.read_sql(f"SELECT {','.join(colonnes)} FROM {table}", conn)
    conn.close()
    filepath = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel files', '*.xlsx'), ('All files', '*.*')])
    if filepath:
        df.to_excel(filepath, index=False)
        tk.messagebox.showinfo('Succès', 'Exportation réussie!')

def open_liste_articles():

    def gestion_articles():
        win = tk.Toplevel()
        win.title('Gestion des articles')
        win.geometry('1100x560')
        _add_minimize_to_dock_button(win)
        conn0 = connecter()
        cur0 = conn0.cursor()
        try:
            cur0.execute('PRAGMA table_info(articles)')
            cols = [r[1] for r in cur0.fetchall()]
            has_cat = 'categorie' in cols
        finally:
            conn0.close()

        def _load_categories():
            cats = []
            try:
                conn = connecter()
                c = conn.cursor()
                c.execute('SELECT nom FROM categories ORDER BY nom')
                cats = [r[0] for r in c.fetchall()]
                conn.close()
            except Exception:
                cats = []
            return cats
        if has_cat:
            colonnes = ['code', 'nom', 'categorie', 'prix_unitaire', 'prix_vente', 'quantite']
            titres = ['Code', 'Nom', 'Catégorie', 'Prix Achat', 'Prix Vente', 'Quantité']
        else:
            colonnes = ['code', 'nom', 'prix_unitaire', 'prix_vente', 'quantite']
            titres = ['Code', 'Nom', 'Prix Achat', 'Prix Vente', 'Quantité']
        filters = tk.Frame(win)
        filters.pack(fill='x', padx=10, pady=(10, 4))
        tk.Label(filters, text='Filtrer par lettre:').pack(side='left')
        letter_var = tk.StringVar(value='ALL')

        def set_letter(l):
            letter_var.set(l)
            charger()
        letters_frame = tk.Frame(filters)
        letters_frame.pack(side='left', padx=6)
        btn_all = tk.Button(letters_frame, text='Tout', command=lambda: set_letter('ALL'), width=4)
        btn_all.pack(side='left', padx=1)
        btn_num = tk.Button(letters_frame, text='0-9', command=lambda: set_letter('NUM'), width=4)
        btn_num.pack(side='left', padx=1)
        for ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            tk.Button(letters_frame, text=ch, command=lambda c=ch: set_letter(c), width=3).pack(side='left', padx=1)
        cat_var = tk.StringVar(value='Toutes')

        def on_cat_change(_=None):
            charger()
        if has_cat:
            tk.Label(filters, text='   Catégorie:').pack(side='left', padx=(10, 0))
            combo_cat = ttk.Combobox(filters, textvariable=cat_var, width=24, state='readonly')
            try:
                connc = connecter()
                curc = connc.cursor()
                curc.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
                if curc.fetchone():
                    curc.execute('SELECT nom FROM categories ORDER BY nom ASC')
                    cats = [r[0] for r in curc.fetchall()]
                else:
                    curc.execute("SELECT DISTINCT COALESCE(categorie,'') FROM articles WHERE COALESCE(categorie,'')<>'' ORDER BY 1 ASC")
                    cats = [r[0] for r in curc.fetchall()]
                connc.close()
            except Exception:
                cats = []
            combo_cat['values'] = ['Toutes'] + cats
            combo_cat.current(0)
            combo_cat.pack(side='left', padx=6)
            combo_cat.bind('<<ComboboxSelected>>', on_cat_change)
        search_frame = tk.Frame(win)
        search_frame.pack(fill='x', padx=10, pady=(0, 4))
        search_var = tk.StringVar()
        tk.Label(search_frame, text='Recherche:').pack(side='left')
        ent_search = ttk.Entry(search_frame, textvariable=search_var, width=40)
        ent_search.pack(side='left', padx=6)

        def do_search(*_):
            charger()

        def clear_search():
            search_var.set('')
            charger()
        ttk.Button(search_frame, text='Rechercher', command=do_search).pack(side='left', padx=4)
        ttk.Button(search_frame, text='Effacer', command=clear_search).pack(side='left', padx=4)
        ent_search.bind('<KeyRelease>', do_search)
        tree = ttk.Treeview(win, columns=colonnes, show='headings')
        for col, titre in zip(colonnes, titres):
            tree.heading(col, text=titre)
            tree.column(col, width=160 if col in ('nom', 'categorie') else 120, anchor='center')

        def charger():
            for i in tree.get_children():
                tree.delete(i)
            conn = connecter()
            cur = conn.cursor()
            where = ['1=1']
            params = []
            L = letter_var.get()
            if L and L != 'ALL':
                if L == 'NUM':
                    where.append("nom GLOB '[0-9]*'")
                else:
                    where.append('UPPER(nom) LIKE ?')
                    params.append(L + '%')
            if has_cat and cat_var.get() and (cat_var.get() != 'Toutes'):
                where.append("COALESCE(categorie,'') = ?")
                params.append(cat_var.get())
            q = (search_var.get() or '').strip()
            if q:
                if has_cat:
                    where.append("(code LIKE ? OR nom LIKE ? OR COALESCE(categorie,'') LIKE ?)")
                    params.extend([f'%{q}%', f'%{q}%', f'%{q}%'])
                else:
                    where.append('(code LIKE ? OR nom LIKE ?)')
                    params.extend([f'%{q}%', f'%{q}%'])
            query = f"SELECT {','.join(colonnes)} FROM articles WHERE {' AND '.join(where)} ORDER BY UPPER(nom) ASC"
            cur.execute(query, params)
            rows = cur.fetchall()
            for row in rows:
                tree.insert('', 'end', values=row)
            conn.close()
        charger()
        tree.pack(expand=True, fill='both', padx=10, pady=10)

        def ajouter():
            form = tk.Toplevel(win)
            form.title('Ajouter un article')
            if has_cat:
                labels = ['Code', 'Nom', 'Catégorie', 'Prix Achat', 'Prix Vente', 'Quantité']
            else:
                labels = ['Code', 'Nom', 'Prix Achat', 'Prix Vente', 'Quantité']
            entries = []
            cat_combo = None
            for i, lab in enumerate(labels):
                tk.Label(form, text=lab + ' :').grid(row=i, column=0, padx=5, pady=5, sticky='e')
                if lab == 'Catégorie':
                    cat_var = tk.StringVar()
                    cat_combo = ttk.Combobox(form, textvariable=cat_var, values=_load_categories(), state='readonly', width=24)
                    cat_combo.grid(row=i, column=1, padx=5, pady=5, sticky='w')
                    entries.append(cat_combo)
                    tk.Button(form, text='Actualiser catégories', command=lambda: cat_combo.config(values=_load_categories())).grid(row=i, column=2, padx=5)
                elif lab == 'Code':
                    ent = tk.Entry(form)
                    ent.grid(row=i, column=1, padx=5, pady=5)
                    try:
                        ent.insert(0, generate_unique_article_code())
                    except Exception:
                        pass
                    entries.append(ent)
                else:
                    ent = tk.Entry(form)
                    ent.grid(row=i, column=1, padx=5, pady=5)
                    entries.append(ent)

            def valider():
                vals = [e.get() for e in entries]
                if not vals[0] or not vals[1]:
                    tk.messagebox.showwarning('Champs manquants', 'Code et nom obligatoires.')
                    return
                try:
                    conn = connecter()
                    cur = conn.cursor()
                    if has_cat:
                        cur.execute('INSERT INTO articles (code, nom, categorie, prix_unitaire, prix_vente, quantite) VALUES (?, ?, ?, ?, ?, ?)', (vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]))
                    else:
                        cur.execute('INSERT INTO articles (code, nom, prix_unitaire, prix_vente, quantite) VALUES (?, ?, ?, ?, ?)', (vals[0], vals[1], vals[2], vals[3], vals[4]))
                    conn.commit()
                    conn.close()
                    form.destroy()
                    charger()
                except Exception as e:
                    tk.messagebox.showerror('Erreur', str(e))
            tk.Button(form, text='Valider', command=valider, bg='#44bd32', fg='white').grid(row=len(labels), column=0, columnspan=2, pady=10)

        def modifier():
            sel = tree.selection()
            if not sel:
                tk.messagebox.showwarning('Sélection', 'Sélectionnez un article à modifier.')
                return
            vals = tree.item(sel[0])['values']
            form = tk.Toplevel(win)
            form.title("Modifier l'article")
            if has_cat:
                labels = ['Code', 'Nom', 'Catégorie', 'Prix Achat', 'Prix Vente', 'Quantité']
            else:
                labels = ['Code', 'Nom', 'Prix Achat', 'Prix Vente', 'Quantité']
            entries = []
            cat_combo = None
            for i, lab in enumerate(labels):
                tk.Label(form, text=lab + ' :').grid(row=i, column=0, padx=5, pady=5, sticky='e')
                if lab == 'Catégorie':
                    cat_var = tk.StringVar()
                    cat_combo = ttk.Combobox(form, textvariable=cat_var, values=_load_categories(), state='readonly', width=24)
                    cat_combo.grid(row=i, column=1, padx=5, pady=5, sticky='w')
                    cat_combo.set(vals[2] if len(vals) > 2 else '')
                    entries.append(cat_combo)
                    tk.Button(form, text='Actualiser catégories', command=lambda: cat_combo.config(values=_load_categories())).grid(row=i, column=2, padx=5)
                else:
                    ent = tk.Entry(form)
                    ent.grid(row=i, column=1, padx=5, pady=5)
                    if has_cat:
                        ent.insert(0, vals[i if i < 2 else i])
                    else:
                        ent.insert(0, vals[i])
                    if i == 0:
                        ent.config(state='readonly')
                    entries.append(ent)

            def valider():
                new_vals = [e.get() for e in entries]
                try:
                    conn = connecter()
                    cur = conn.cursor()
                    if has_cat:
                        cur.execute('UPDATE articles SET nom=?, categorie=?, prix_unitaire=?, prix_vente=?, quantite=? WHERE code=?', (new_vals[1], new_vals[2], new_vals[3], new_vals[4], new_vals[5], new_vals[0]))
                    else:
                        cur.execute('UPDATE articles SET nom=?, prix_unitaire=?, prix_vente=?, quantite=? WHERE code=?', (new_vals[1], new_vals[2], new_vals[3], new_vals[4], new_vals[0]))
                    conn.commit()
                    conn.close()
                    form.destroy()
                    charger()
                except Exception as e:
                    tk.messagebox.showerror('Erreur', str(e))
            tk.Button(form, text='Valider', command=valider, bg='#273c75', fg='white').grid(row=len(labels), column=0, columnspan=2, pady=10)

        def supprimer():
            sel = tree.selection()
            if not sel:
                tk.messagebox.showwarning('Sélection', 'Sélectionnez un article à supprimer.')
                return
            code = tree.item(sel[0])['values'][0]
            if tk.messagebox.askyesno('Confirmation', 'Supprimer cet article ?'):
                try:
                    conn = connecter()
                    cur = conn.cursor()
                    cur.execute('DELETE FROM articles WHERE code=?', (code,))
                    conn.commit()
                    conn.close()
                    charger()
                except Exception as e:
                    tk.messagebox.showerror('Erreur', str(e))
        frm_btns = tk.Frame(win)
        frm_btns.pack(pady=10)
        tk.Button(frm_btns, text='Ajouter', command=ajouter, bg='#44bd32', fg='white', width=12).pack(side='left', padx=5)
        tk.Button(frm_btns, text='Modifier', command=modifier, bg='#fbc531', fg='black', width=12).pack(side='left', padx=5)
        tk.Button(frm_btns, text='Supprimer', command=supprimer, bg='#e84118', fg='white', width=12).pack(side='left', padx=5)
    gestion_articles()

def open_liste_clients():
    import sqlite3
    win = tk.Toplevel()
    win.title('Liste des clients')
    win.geometry('1000x500')
    _add_minimize_to_dock_button(win)
    colonnes = ['id', 'nom', 'email', 'telephone', 'adresse', 'solde_credit', 'montant_paye', 'date_dernier_paiement']
    titres = ['ID', 'Nom', 'Email', 'Téléphone', 'Adresse', 'Solde Crédit', 'Montant payé', 'Date dernier paiement']
    filters = tk.Frame(win)
    filters.pack(fill='x', padx=10, pady=(10, 4))
    tk.Label(filters, text='Recherche:').pack(side='left')
    search_var = tk.StringVar()
    ent_search = ttk.Entry(filters, textvariable=search_var, width=32)
    ent_search.pack(side='left', padx=6)

    def clear_search():
        search_var.set('')
        charger()
    ttk.Button(filters, text='Effacer', command=clear_search).pack(side='left', padx=4)
    tree = ttk.Treeview(win, columns=colonnes, show='headings')
    for col, titre in zip(colonnes, titres):
        tree.heading(col, text=titre)
        tree.column(col, width=140 if col in ('nom', 'adresse') else 120, anchor='center')

    def charger():
        for i in tree.get_children():
            tree.delete(i)
        conn = sqlite3.connect('data.db')
        cur = conn.cursor()
        where = ['1=1']
        params = []
        q = (search_var.get() or '').strip()
        if q:
            like = f'%{q}%'
            where.append('(nom LIKE ? OR email LIKE ? OR telephone LIKE ? OR adresse LIKE ? OR CAST(id AS TEXT) LIKE ?)')
            params.extend([like, like, like, like, like])
        cur.execute(f"SELECT id, nom, email, telephone, adresse, solde_credit FROM clients WHERE {' AND '.join(where)} ORDER BY UPPER(nom) ASC", params)
        clients = cur.fetchall()
        for c in clients:
            c_id, nom, email, tel, adr, solde = c
            try:
                cur.execute('SELECT COALESCE(SUM(montant),0), MAX(date) FROM reglement_client WHERE client_id = ?', (c_id,))
                res = cur.fetchone()
                montant_paye = res[0] if res else 0
                date_dernier = res[1] if res and res[1] else ''
            except Exception:
                montant_paye = 0
                date_dernier = ''
            tree.insert('', 'end', values=(c_id, nom, email, tel, adr, f'{solde:.2f}', f'{montant_paye:.2f}', date_dernier))
        conn.close()
    charger()
    ent_search.bind('<KeyRelease>', lambda *_: charger())
    scrollbar = ttk.Scrollbar(win, orient='vertical', command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(expand=True, fill='both', padx=10, pady=10)
    btn_export = tk.Button(win, text='Exporter vers Excel', command=lambda: exporter_excel('clients', ['id', 'nom', 'email', 'telephone', 'adresse', 'solde_credit']))
    btn_export.pack(pady=10)

def open_liste_fournisseurs():
    afficher_liste('fournisseurs', ['id', 'nom', 'email', 'telephone', 'adresse'], ['ID', 'Nom', 'Email', 'Téléphone', 'Adresse'])