import tkinter as tk
from tkinter import ttk, messagebox
from database import connecter
import sqlite3
from utils_codes import generate_unique_article_code

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

def delete_category(nom):
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM categories WHERE nom=?', (nom,))
        conn.commit()
    finally:
        conn.close()

def ajouter_article(code, nom, prix_unitaire, prix_vente, quantite, refresh_callback, categorie=None):
    conn = connecter()
    cur = conn.cursor()
    try:
        try:
            cur.execute('INSERT INTO articles (code, nom, prix_unitaire, prix_vente, quantite, categorie) VALUES (?, ?, ?, ?, ?, ?)', (code, nom, float(prix_unitaire or 0), float(prix_vente or 0), int(quantite or 0), categorie))
        except sqlite3.OperationalError:
            cur.execute('INSERT INTO articles (code, nom, prix_unitaire, prix_vente, quantite) VALUES (?, ?, ?, ?, ?)', (code, nom, float(prix_unitaire or 0), float(prix_vente or 0), int(quantite or 0)))
        conn.commit()
        refresh_callback()
    except (sqlite3.Error, ValueError) as e:
        messagebox.showerror('Erreur', f'Erreur: {e}')
    finally:
        conn.close()

def afficher_articles(tree, q: str | None=None):
    for row in tree.get_children():
        tree.delete(row)
    conn = connecter()
    cur = conn.cursor()
    try:
        q_norm = (q or '').strip()
        try:
            if q_norm:
                cur.execute("\n                    SELECT code, nom, categorie, prix_unitaire, prix_vente, quantite\n                    FROM articles\n                    WHERE code LIKE ? OR nom LIKE ? OR COALESCE(categorie,'') LIKE ?\n                    ORDER BY UPPER(nom) ASC\n                    ", (f'%{q_norm}%', f'%{q_norm}%', f'%{q_norm}%'))
            else:
                cur.execute('SELECT code, nom, categorie, prix_unitaire, prix_vente, quantite FROM articles ORDER BY UPPER(nom) ASC')
            for row in cur.fetchall():
                tree.insert('', 'end', values=row)
        except sqlite3.OperationalError:
            if q_norm:
                cur.execute('\n                    SELECT code, nom, NULL as categorie, prix_unitaire, prix_vente, quantite\n                    FROM articles\n                    WHERE code LIKE ? OR nom LIKE ?\n                    ORDER BY UPPER(nom) ASC\n                    ', (f'%{q_norm}%', f'%{q_norm}%'))
            else:
                cur.execute('SELECT code, nom, NULL as categorie, prix_unitaire, prix_vente, quantite FROM articles ORDER BY UPPER(nom) ASC')
            for row in cur.fetchall():
                tree.insert('', 'end', values=row)
    except sqlite3.Error as e:
        messagebox.showerror('Erreur', f'Erreur de lecture: {e}')
    finally:
        conn.close()

def open_articles_window():
    win = tk.Toplevel()
    win.title('Gestion des Articles')
    win.geometry('900x600')
    win.configure(bg='#f5f6fa')

    def add_window_header(container, title):
        header = tk.Frame(container, bg='#f5f6fa')
        header.pack(fill='x', padx=10, pady=(10, 0))
        ttk.Label(header, text=title, font=('Segoe UI', 12, 'bold')).pack(side='left')
        ttk.Separator(container, orient='horizontal').pack(fill='x', padx=10, pady=(6, 6))

    def style_treeview_rows(tree):
        for idx, iid in enumerate(tree.get_children()):
            tags = ['even' if idx % 2 == 0 else 'odd']
            tree.item(iid, tags=tuple(tags))
        tree.tag_configure('even', background='#ffffff', foreground='black')
        tree.tag_configure('odd', background='#f9fbff', foreground='black')
        style = ttk.Style()
        style.map('Treeview', background=[('selected', 'black')], foreground=[('selected', 'white')])
    add_window_header(win, 'Gestion des Articles')
    form_frame = tk.Frame(win, padx=10, pady=10, bg='#f5f6fa')
    form_frame.pack(fill=tk.X)
    tk.Label(form_frame, text='Code:', bg='#f5f6fa').grid(row=0, column=0, sticky='e', padx=(0, 6), pady=4)
    code_entry = ttk.Entry(form_frame, width=30)
    code_entry.grid(row=0, column=1, pady=5)
    try:
        code_entry.delete(0, tk.END)
        code_entry.insert(0, generate_unique_article_code())
    except Exception:
        pass

    def regen_code():
        try:
            code_entry.delete(0, tk.END)
            code_entry.insert(0, generate_unique_article_code())
        except Exception:
            pass
    ttk.Button(form_frame, text='Générer code', command=regen_code).grid(row=0, column=2, padx=6)
    tk.Label(form_frame, text='Nom:', bg='#f5f6fa').grid(row=1, column=0, sticky='e', padx=(0, 6), pady=4)
    nom_entry = ttk.Entry(form_frame, width=30)
    nom_entry.grid(row=1, column=1, pady=5)
    tk.Label(form_frame, text='Prix Achat:', bg='#f5f6fa').grid(row=2, column=0, sticky='e', padx=(0, 6), pady=4)
    prix_unitaire_entry = ttk.Entry(form_frame, width=30)
    prix_unitaire_entry.grid(row=2, column=1, pady=5)
    tk.Label(form_frame, text='Prix Vente:', bg='#f5f6fa').grid(row=3, column=0, sticky='e', padx=(0, 6), pady=4)
    prix_vente_entry = ttk.Entry(form_frame, width=30)
    prix_vente_entry.grid(row=3, column=1, pady=5)
    tk.Label(form_frame, text='Quantité:', bg='#f5f6fa').grid(row=4, column=0, sticky='e', padx=(0, 6), pady=4)
    quantite_entry = ttk.Entry(form_frame, width=30)
    quantite_entry.grid(row=4, column=1, pady=5)
    ensure_categories_schema()
    ensure_article_category_schema()
    tk.Label(form_frame, text='Catégorie:', bg='#f5f6fa').grid(row=5, column=0, sticky='e', padx=(0, 6), pady=4)
    categorie_var = tk.StringVar()
    categorie_combo = ttk.Combobox(form_frame, textvariable=categorie_var, values=list_categories(), width=28, state='readonly')
    categorie_combo.grid(row=5, column=1, pady=5, sticky='w')

    def open_categories_manager():
        dlg = tk.Toplevel(win)
        dlg.title('Gérer Catégories')
        frame = tk.Frame(dlg, padx=10, pady=10)
        frame.pack(fill='both', expand=True)
        tk.Label(frame, text='Catégories existantes:').grid(row=0, column=0, sticky='w')
        lst = tk.Listbox(frame, height=8, width=32)
        lst.grid(row=1, column=0, columnspan=3, sticky='we', pady=6)

        def refresh_list():
            lst.delete(0, tk.END)
            for c in list_categories():
                lst.insert(tk.END, c)
        refresh_list()
        tk.Label(frame, text='Nouvelle catégorie:').grid(row=2, column=0, sticky='e')
        new_var = tk.StringVar()
        tk.Entry(frame, textvariable=new_var).grid(row=2, column=1, padx=6)

        def add_cat():
            add_category(new_var.get().strip())
            refresh_list()
            categorie_combo.configure(values=list_categories())

        def del_cat():
            sel = lst.curselection()
            if not sel:
                return
            delete_category(lst.get(sel[0]))
            refresh_list()
            categorie_combo.configure(values=list_categories())
        ttk.Button(frame, text='Ajouter', command=add_cat).grid(row=2, column=2)
        ttk.Button(frame, text='Supprimer', command=del_cat).grid(row=3, column=2, pady=6)
    ttk.Button(form_frame, text='Gérer Catégories', command=open_categories_manager).grid(row=5, column=2, padx=6)

    def submit():
        if not code_entry.get() or not nom_entry.get():
            messagebox.showwarning('Attention', 'Le code et le nom sont obligatoires')
            return
        if not categorie_var.get().strip():
            messagebox.showwarning('Attention', 'Veuillez choisir une catégorie')
            return
        try:
            ajouter_article(code_entry.get(), nom_entry.get(), prix_unitaire_entry.get(), prix_vente_entry.get(), quantite_entry.get(), lambda: None, categorie=categorie_var.get().strip())
            code_entry.delete(0, tk.END)
            nom_entry.delete(0, tk.END)
            prix_unitaire_entry.delete(0, tk.END)
            prix_vente_entry.delete(0, tk.END)
            quantite_entry.delete(0, tk.END)
            categorie_var.set('')
            try:
                refresh()
            except Exception:
                pass
        except ValueError:
            messagebox.showerror('Erreur', 'Valeurs numériques invalides')
    btn_ajouter = ttk.Button(form_frame, text='Ajouter Article', command=submit)
    btn_ajouter.grid(row=5, column=1, pady=10)
    search_frame = tk.Frame(win, bg='#f5f6fa')
    search_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
    tk.Label(search_frame, text='Recherche:', bg='#f5f6fa').pack(side='left')
    search_var = tk.StringVar()
    ent_search = ttk.Entry(search_frame, textvariable=search_var, width=36)
    ent_search.pack(side='left', padx=6)
    tree_frame = tk.Frame(win, bg='#f5f6fa')
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    tree = ttk.Treeview(tree_frame, columns=('Code', 'Nom', 'Catégorie', 'Prix Achat', 'Prix Vente', 'Quantité'), show='headings')
    for col in tree['columns']:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(fill=tk.BOTH, expand=True)
    style_treeview_rows(tree)
    tree.bind('<Double-1>', lambda e: modifier_article())

    def refresh():
        afficher_articles(tree, search_var.get())
        style_treeview_rows(tree)

    def do_search(*_):
        refresh()

    def clear_search():
        search_var.set('')
        refresh()
    ttk.Button(search_frame, text='Rechercher', command=do_search).pack(side='left', padx=4)
    ttk.Button(search_frame, text='Effacer', command=clear_search).pack(side='left', padx=4)
    ent_search.bind('<KeyRelease>', do_search)
    ttk.Button(win, text='Actualiser', command=refresh).pack(pady=5)

    def supprimer_article():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un article à supprimer.')
            return
        item = tree.item(selected[0])
        article_code = item['values'][0]
        if messagebox.askyesno('Confirmation', 'Supprimer cet article ?'):
            conn = connecter()
            cur = conn.cursor()
            cur.execute('DELETE FROM articles WHERE code = ?', (article_code,))
            conn.commit()
            conn.close()
            refresh()

    def modifier_article():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un article à modifier.')
            return
        item = tree.item(selected[0])
        vals = item['values']
        if len(vals) >= 1:
            article_code = vals[0]
        else:
            messagebox.showerror('Erreur', "Impossible d'identifier l'article sélectionné.")
            return

        def _fmt_num(v):
            try:
                f = float(str(v).replace(' ', '').replace(',', '.'))
            except Exception:
                return str(v or '')
            if abs(f - round(f)) < 1e-09:
                return str(int(round(f)))
            s = f'{f:.3f}'.rstrip('0').rstrip('.')
            return s.replace('.', ',')
        conn = connecter()
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('PRAGMA table_info(articles)')
            cols = [r[1] for r in cur.fetchall()]
            has_categorie = 'categorie' in cols
            if has_categorie:
                cur.execute('SELECT code, nom, categorie, CAST(prix_unitaire AS REAL) AS prix_unitaire, CAST(prix_vente AS REAL) AS prix_vente, CAST(quantite AS REAL) AS quantite FROM articles WHERE code=?', (article_code,))
            else:
                cur.execute('SELECT code, nom, CAST(prix_unitaire AS REAL) AS prix_unitaire, CAST(prix_vente AS REAL) AS prix_vente, CAST(quantite AS REAL) AS quantite FROM articles WHERE code=?', (article_code,))
            row = cur.fetchone()
            if not row:
                raise ValueError('Article introuvable')
            code_db = row['code'] if 'code' in row.keys() else article_code
            nom_db = row['nom'] if 'nom' in row.keys() else ''
            pa_db = row['prix_unitaire'] if 'prix_unitaire' in row.keys() else 0.0
            pv_db = row['prix_vente'] if 'prix_vente' in row.keys() else 0.0
            qte_db = row['quantite'] if 'quantite' in row.keys() else 0.0
            cat_db = row['categorie'] if has_categorie and 'categorie' in row.keys() else ''
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            messagebox.showerror('Erreur', f'Lecture article: {e}')
            return
        finally:
            try:
                conn.close()
            except Exception:
                pass
        modif_win = tk.Toplevel(win)
        modif_win.title('Modifier Article')
        tk.Label(modif_win, text='Code:').grid(row=0, column=0, sticky='e', padx=6, pady=6)
        code_var = tk.StringVar(value=str(code_db))
        code_entry = ttk.Entry(modif_win, textvariable=code_var, state='readonly')
        code_entry.grid(row=0, column=1, padx=6, pady=6)
        tk.Label(modif_win, text='Nom:').grid(row=1, column=0, sticky='e', padx=6, pady=6)
        nom_var = tk.StringVar(value=str(nom_db or ''))
        nom_entry = ttk.Entry(modif_win, textvariable=nom_var, width=30)
        nom_entry.grid(row=1, column=1, padx=6, pady=6)
        tk.Label(modif_win, text='Prix Achat:').grid(row=2, column=0, sticky='e', padx=6, pady=6)
        pa_var = tk.StringVar(value=_fmt_num(pa_db))
        pa_entry = ttk.Entry(modif_win, textvariable=pa_var, width=20)
        pa_entry.grid(row=2, column=1, padx=6, pady=6)
        tk.Label(modif_win, text='Prix Vente:').grid(row=3, column=0, sticky='e', padx=6, pady=6)
        pv_var = tk.StringVar(value=_fmt_num(pv_db))
        pv_entry = ttk.Entry(modif_win, textvariable=pv_var, width=20)
        pv_entry.grid(row=3, column=1, padx=6, pady=6)
        tk.Label(modif_win, text='Quantité:').grid(row=4, column=0, sticky='e', padx=6, pady=6)
        qte_var = tk.StringVar(value=_fmt_num(qte_db))
        qte_entry = ttk.Entry(modif_win, textvariable=qte_var, width=20)
        qte_entry.grid(row=4, column=1, padx=6, pady=6)
        tk.Label(modif_win, text='Catégorie:').grid(row=5, column=0, sticky='e', padx=6, pady=6)
        cat_var = tk.StringVar(value=str(cat_db or ''))
        cat_combo = ttk.Combobox(modif_win, textvariable=cat_var, values=list_categories(), width=28, state='readonly')
        cat_combo.grid(row=5, column=1, padx=6, pady=6, sticky='w')

        def open_categories_manager_modif():
            dlg = tk.Toplevel(modif_win)
            dlg.title('Gérer Catégories')
            frame = tk.Frame(dlg, padx=10, pady=10)
            frame.pack(fill='both', expand=True)
            tk.Label(frame, text='Catégories existantes:').grid(row=0, column=0, sticky='w')
            lst = tk.Listbox(frame, height=8, width=32)
            lst.grid(row=1, column=0, columnspan=3, sticky='we', pady=6)

            def refresh_list():
                lst.delete(0, tk.END)
                for c in list_categories():
                    lst.insert(tk.END, c)
            refresh_list()
            tk.Label(frame, text='Nouvelle catégorie:').grid(row=2, column=0, sticky='e')
            new_var = tk.StringVar()
            tk.Entry(frame, textvariable=new_var).grid(row=2, column=1, padx=6)

            def add_cat():
                add_category(new_var.get().strip())
                refresh_list()
                cat_combo.configure(values=list_categories())

            def del_cat():
                sel = lst.curselection()
                if not sel:
                    return
                delete_category(lst.get(sel[0]))
                refresh_list()
                cat_combo.configure(values=list_categories())
            ttk.Button(frame, text='Ajouter', command=add_cat).grid(row=2, column=2)
            ttk.Button(frame, text='Supprimer', command=del_cat).grid(row=3, column=2, pady=6)
        ttk.Button(modif_win, text='Gérer Catégories', command=open_categories_manager_modif).grid(row=5, column=2, padx=6)

        def valider_modif():
            try:
                pa_val = float(str(pa_var.get()).replace(' ', '').replace(',', '.'))
            except Exception:
                messagebox.showwarning('Validation', 'Prix Achat invalide')
                return
            try:
                pv_val = float(str(pv_var.get()).replace(' ', '').replace(',', '.'))
            except Exception:
                messagebox.showwarning('Validation', 'Prix Vente invalide')
                return
            try:
                qte_val = float(str(qte_var.get()).replace(' ', '').replace(',', '.'))
            except Exception:
                messagebox.showwarning('Validation', 'Quantité invalide')
                return
            if qte_val < 0:
                messagebox.showwarning('Validation', 'La quantité ne peut pas être négative')
                return
            nom_val = nom_var.get().strip()
            if not nom_val:
                messagebox.showwarning('Validation', 'Le nom est obligatoire')
                return
            if not cat_var.get().strip():
                messagebox.showwarning('Validation', 'Veuillez choisir une catégorie')
                return
            cat_val = cat_var.get().strip()
            conn2 = connecter()
            cur2 = conn2.cursor()
            try:
                try:
                    cur2.execute('UPDATE articles SET nom=?, prix_unitaire=?, prix_vente=?, quantite=?, categorie=? WHERE code=?', (nom_val, pa_val, pv_val, qte_val, cat_val, code_db))
                except sqlite3.OperationalError:
                    cur2.execute('UPDATE articles SET nom=?, prix_unitaire=?, prix_vente=?, quantite=? WHERE code=?', (nom_val, pa_val, pv_val, qte_val, code_db))
                conn2.commit()
            except Exception as e:
                messagebox.showerror('Erreur', f'Modification impossible: {e}')
                return
            finally:
                conn2.close()
            refresh()
            modif_win.destroy()
        ttk.Button(modif_win, text='Valider', command=valider_modif).grid(row=6, column=0, columnspan=2, pady=10)