def open_alerte_stock_window():
    win = tk.Toplevel()
    win.title('Gestion des alertes de stock')
    win.geometry('700x400')
    tk.Label(win, text='Définir une alerte de stock pour un produit', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(pady=10)
    tk.Label(frame, text='Recherche produit :').grid(row=0, column=0, padx=5, pady=5)
    search_var = tk.StringVar()
    search_entry = tk.Entry(frame, textvariable=search_var)
    search_entry.grid(row=0, column=1, padx=5, pady=5)
    result_var = tk.StringVar()
    tk.Label(frame, textvariable=result_var, fg='blue').grid(row=1, column=0, columnspan=3, pady=5)

    def rechercher():
        nom = search_var.get().strip()
        if not nom:
            result_var.set('Veuillez saisir un nom de produit.')
            return
        conn = connecter()
        cur = conn.cursor()
        cur.execute('SELECT code, nom, quantite FROM articles WHERE nom LIKE ?', (f'%{nom}%',))
        res = cur.fetchone()
        if res:
            pid = res[0]
            result_var.set(f'Produit trouvé : ID {res[0]}, {res[1]}, Stock actuel : {res[2]}')
            produit_id_var.set(res[0])
            produit_nom_var.set(res[1])
            stock_actuel_var.set(res[2])
            cur.execute('SELECT seuil FROM alertes_stock WHERE produit_id=?', (pid,))
            seuil = cur.fetchone()
            if seuil:
                seuil_var.set(str(seuil[0]))
                result_var.set(result_var.get() + f' | Alerte existante : seuil = {seuil[0]}')
            else:
                seuil_var.set('')
        else:
            result_var.set('Aucun produit trouvé.')
            produit_id_var.set('')
            produit_nom_var.set('')
            stock_actuel_var.set('')
            seuil_var.set('')
        conn.close()
    tk.Button(frame, text='Rechercher', command=rechercher).grid(row=0, column=2, padx=5)
    produit_id_var = tk.StringVar()
    produit_nom_var = tk.StringVar()
    stock_actuel_var = tk.StringVar()
    seuil_var = tk.StringVar()
    tk.Label(frame, text='Produit sélectionné :').grid(row=2, column=0, sticky='e', padx=5)
    tk.Label(frame, textvariable=produit_nom_var, fg='green').grid(row=2, column=1, sticky='w', padx=5)
    tk.Label(frame, text='Stock actuel :').grid(row=3, column=0, sticky='e', padx=5)
    tk.Label(frame, textvariable=stock_actuel_var).grid(row=3, column=1, sticky='w', padx=5)
    tk.Label(frame, text="Seuil d'alerte :").grid(row=4, column=0, sticky='e', padx=5)
    seuil_entry = tk.Entry(frame, textvariable=seuil_var)
    seuil_entry.grid(row=4, column=1, padx=5)

    def creer_table_alertes():
        conn = connecter()
        cur = conn.cursor()
        cur.execute('\n            CREATE TABLE IF NOT EXISTS alertes_stock (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                produit_id TEXT,\n                seuil INTEGER,\n                FOREIGN KEY(produit_id) REFERENCES articles(code)\n            )\n        ')
        conn.commit()
        conn.close()
    creer_table_alertes()

    def enregistrer_alerte():
        pid = produit_id_var.get()
        seuil = seuil_var.get()
        if not pid or not seuil.isdigit():
            result_var.set('Sélectionnez un produit et saisissez un seuil valide.')
            return
        conn = connecter()
        cur = conn.cursor()
        cur.execute('SELECT id FROM alertes_stock WHERE produit_id=?', (pid,))
        if cur.fetchone():
            cur.execute('UPDATE alertes_stock SET seuil=? WHERE produit_id=?', (seuil, pid))
        else:
            cur.execute('INSERT INTO alertes_stock (produit_id, seuil) VALUES (?, ?)', (pid, seuil))
        conn.commit()
        conn.close()
        result_var.set('Alerte enregistrée !')
    tk.Button(frame, text="Enregistrer l'alerte", command=enregistrer_alerte, bg='#007700', fg='white').grid(row=5, column=0, columnspan=3, pady=10)
    alertes_frame = tk.Frame(win)
    alertes_frame.pack(pady=10, fill='x')
    tk.Label(alertes_frame, text='Alertes de stock existantes', font=('Arial', 12, 'bold')).pack()
    columns = ('ID Produit', 'Nom Produit', "Seuil d'alerte", 'Stock actuel')
    tree = ttk.Treeview(alertes_frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor='center')
    tree.pack(fill='x')

    def charger_alertes():
        for i in tree.get_children():
            tree.delete(i)
        conn = connecter()
        cur = conn.cursor()
        cur.execute('\n            SELECT a.produit_id, p.nom, a.seuil, p.quantite\n            FROM alertes_stock a\n            JOIN articles p ON a.produit_id = p.code\n        ')
        for row in cur.fetchall():
            tree.insert('', 'end', values=row)
        conn.close()
    charger_alertes()

    def refresh_and_save():
        enregistrer_alerte()
        charger_alertes()
    tk.Button(frame, text='Enregistrer et voir alertes', command=refresh_and_save, bg='#0055aa', fg='white').grid(row=6, column=0, columnspan=3, pady=5)

def open_mouvement_article_client_window():
    win = tk.Toplevel()
    win.title('Mouvement des articles par client')
    win.geometry('950x500')
    tk.Label(win, text='Mouvements des articles par client', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('ID Client', 'Nom Client', 'Produit', 'Quantité achetée', 'Montant total')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=180, anchor='center')
    tree.pack(expand=True, fill='both')
    conn = connecter()
    cur = conn.cursor()
    cur.execute('SELECT id, nom FROM clients')
    clients = cur.fetchall()
    for client in clients:
        cid, nom = client
        cur.execute('\n            SELECT p.nom, SUM(v.quantite), SUM(v.total)\n            FROM ventes v\n            JOIN articles p ON v.produit_id = p.code\n            WHERE v.client_id=?\n            GROUP BY p.nom\n        ', (cid,))
        for prod, qte, montant in cur.fetchall():
            qte = qte or 0
            montant = montant or 0
            tree.insert('', 'end', values=(cid, nom, prod, qte, f'{montant:.2f}'))
    conn.close()

def open_mouvement_article_periode_window():
    win = tk.Toplevel()
    win.title('Mouvement des articles par période')
    win.geometry('1050x550')
    tk.Label(win, text='Mouvements des articles par période', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('Période', 'Produit', 'Quantité vendue', 'Montant total')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200, anchor='center')
    tree.pack(expand=True, fill='both')
    periode_frame = tk.Frame(win)
    periode_frame.pack(pady=5)
    tk.Label(periode_frame, text='Date début (YYYY-MM-DD):').pack(side='left')
    date_deb = tk.Entry(periode_frame)
    date_deb.pack(side='left', padx=5)
    tk.Label(periode_frame, text='Date fin (YYYY-MM-DD):').pack(side='left')
    date_fin = tk.Entry(periode_frame)
    date_fin.pack(side='left', padx=5)

    def calculer():
        for i in tree.get_children():
            tree.delete(i)
        deb = date_deb.get()
        fin = date_fin.get()
        conn = connecter()
        cur = conn.cursor()
        cur.execute('SELECT nom, code FROM articles')
        articles = cur.fetchall()
        for prod, pid in articles:
            cur.execute('\n                SELECT SUM(quantite), SUM(total) FROM ventes\n                WHERE produit_id=? AND date BETWEEN ? AND ?\n            ', (pid, deb, fin))
            qte, montant = cur.fetchone()
            qte = qte or 0
            montant = montant or 0
            tree.insert('', 'end', values=(f'{deb} à {fin}', prod, qte, f'{montant:.2f}'))
        conn.close()
    tk.Button(win, text='Calculer', command=calculer, font=('Arial', 12)).pack(pady=10)
import tkinter as tk
from tkinter import ttk, messagebox
from database import connecter

def open_saisie_inventaire_window():
    win = tk.Toplevel()
    win.title("Saisie d'Inventaire")
    win.geometry('700x500')
    tk.Label(win, text="Saisie d'inventaire", font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('Code Produit', 'Nom Produit', 'Quantité réelle', 'Quantité système', 'Écart')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor='center')
    tree.pack(expand=True, fill='both')
    conn = connecter()
    cur = conn.cursor()
    cur.execute('SELECT code, nom, quantite FROM articles')
    articles = cur.fetchall()
    for prod in articles:
        tree.insert('', 'end', values=(prod[0], prod[1], '', prod[2], ''))
    conn.close()

    def enregistrer_inventaire():
        conn = connecter()
        cur = conn.cursor()
        for item in tree.get_children():
            values = tree.item(item)['values']
            try:
                qte_reelle = float(values[2])
            except Exception:
                continue
            cur.execute('UPDATE articles SET quantite=? WHERE code=?', (qte_reelle, values[0]))
        conn.commit()
        conn.close()
        messagebox.showinfo('Succès', 'Inventaire enregistré et stock mis à jour !')
        win.destroy()

    def on_edit(event):
        item = tree.focus()
        col = tree.identify_column(event.x)
        if col == '#3':
            x, y, width, height = tree.bbox(item, 'Quantité réelle')
            entry = tk.Entry(tree)
            entry.place(x=x, y=y, width=width, height=height)

            def save_edit(event):
                val = entry.get()
                tree.set(item, 'Quantité réelle', val)
                qte_sys = tree.set(item, 'Quantité système')
                try:
                    ecart = int(val) - int(qte_sys)
                except Exception:
                    ecart = ''
                tree.set(item, 'Écart', ecart)
                entry.destroy()
            entry.bind('<Return>', save_edit)
            entry.focus()
    tree.bind('<Double-1>', on_edit)
    tk.Button(win, text="Enregistrer l'inventaire", command=enregistrer_inventaire, font=('Arial', 12)).pack(pady=15)

def open_cumul_sortie_client_window():
    win = tk.Toplevel()
    win.title('Cumul des Sorties par Client')
    win.geometry('800x400')
    tk.Label(win, text='Cumul des sorties par client', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('ID Client', 'Nom Client', 'Total Quantité Sortie', 'Total Montant')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor='center')
    tree.pack(expand=True, fill='both')
    conn = connecter()
    cur = conn.cursor()
    cur.execute('\n        SELECT c.id, c.nom, SUM(v.quantite), SUM(v.total)\n        FROM ventes v\n        JOIN clients c ON v.client_id = c.id\n        GROUP BY c.id, c.nom\n    ')
    for row in cur.fetchall():
        tree.insert('', 'end', values=row)
    conn.close()

def open_cout_de_revient_window():
    win = tk.Toplevel()
    win.title('Coût de Revient des Produits')
    win.geometry('800x400')
    tk.Label(win, text='Coût de revient par produit', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('ID Produit', 'Nom Produit', 'Prix Achat', 'Prix Vente', 'Coût de Revient')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor='center')
    tree.pack(expand=True, fill='both')
    conn = connecter()
    cur = conn.cursor()
    cur.execute('SELECT code, nom, prix_unitaire, prix_vente FROM articles')
    for row in cur.fetchall():
        tree.insert('', 'end', values=(row[0], row[1], row[2], row[3], row[2]))
    conn.close()

def open_etat_stock_window():
    win = tk.Toplevel()
    win.title('État du Stock')
    win.geometry('800x400')
    tk.Label(win, text='État du stock actuel', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('ID Produit', 'Nom Produit', 'Quantité en stock')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200, anchor='center')
    tree.pack(expand=True, fill='both')
    conn = connecter()
    cur = conn.cursor()
    cur.execute('SELECT code, nom, quantite FROM articles')
    for row in cur.fetchall():
        tree.insert('', 'end', values=row)
    conn.close()

def open_valeur_stock_window():
    win = tk.Toplevel()
    win.title('Valeur du Stock')
    win.geometry('800x400')
    tk.Label(win, text='Valeur totale du stock (prix achat)', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('ID Produit', 'Nom Produit', 'Quantité', 'Prix Achat', 'Valeur')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor='center')
    tree.pack(expand=True, fill='both')
    total = 0
    conn = connecter()
    cur = conn.cursor()
    cur.execute('SELECT code, nom, quantite, prix_unitaire FROM articles')
    for row in cur.fetchall():
        valeur = row[2] * row[3]
        total += valeur
        tree.insert('', 'end', values=(row[0], row[1], row[2], row[3], f'{valeur:.2f}'))
    conn.close()
    tk.Label(win, text=f'Valeur totale du stock : {total:.2f}', font=('Arial', 12, 'bold'), fg='#007700').pack(pady=10)

def open_valeur_stock_periode_window():
    win = tk.Toplevel()
    win.title('Valeur du Stock par Période')
    win.geometry('900x500')
    tk.Label(win, text='Valeur du stock par période (basé sur mouvements)', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('Date', 'ID Produit', 'Nom Produit', 'Entrées', 'Sorties', 'Stock final estimé')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=130, anchor='center')
    tree.pack(expand=True, fill='both')
    periode_frame = tk.Frame(win)
    periode_frame.pack(pady=5)
    tk.Label(periode_frame, text='Date début (YYYY-MM-DD):').pack(side='left')
    date_deb = tk.Entry(periode_frame)
    date_deb.pack(side='left', padx=5)
    tk.Label(periode_frame, text='Date fin (YYYY-MM-DD):').pack(side='left')
    date_fin = tk.Entry(periode_frame)
    date_fin.pack(side='left', padx=5)

    def calculer():
        for i in tree.get_children():
            tree.delete(i)
        deb = date_deb.get()
        fin = date_fin.get()
        conn = connecter()
        cur = conn.cursor()
        cur.execute('SELECT code, nom FROM articles')
        articles = cur.fetchall()
        for prod in articles:
            pid, nom = prod
            try:
                cur.execute('\n                    SELECT SUM(quantite) FROM bons_livraison\n                    WHERE id_produit=? AND date BETWEEN ? AND ?\n                ', (pid, deb, fin))
                entrees = cur.fetchone()[0] or 0
            except Exception:
                entrees = 0
            cur.execute('\n                SELECT SUM(quantite) FROM ventes\n                WHERE produit_id=? AND date BETWEEN ? AND ?\n            ', (pid, deb, fin))
            sorties = cur.fetchone()[0] or 0
            cur.execute('SELECT quantite FROM articles WHERE code=?', (pid,))
            stock_final = cur.fetchone()[0] or 0
            tree.insert('', 'end', values=(f'{deb} à {fin}', pid, nom, entrees, sorties, stock_final))
        conn.close()
    tk.Button(win, text='Calculer', command=calculer, font=('Arial', 12)).pack(pady=10)

def open_valeur_stock_par_client_window():
    win = tk.Toplevel()
    win.title('Valeur du stock par client')
    win.geometry('950x500')
    tk.Label(win, text='Valeur des ventes par client', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('ID Client', 'Nom Client', 'Quantité totale achetée', 'Montant total')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200, anchor='center')
    tree.pack(expand=True, fill='both')
    total_global = 0
    conn = connecter()
    cur = conn.cursor()
    cur.execute('SELECT id, nom FROM clients')
    clients = cur.fetchall()
    for client in clients:
        cid, nom = client
        cur.execute('SELECT SUM(quantite), SUM(total) FROM ventes WHERE client_id=?', (cid,))
        qte, montant = cur.fetchone()
        qte = qte or 0
        montant = montant or 0
        total_global += montant
        tree.insert('', 'end', values=(cid, nom, qte, f'{montant:.2f}'))
    conn.close()
    tk.Label(win, text=f'Montant total toutes ventes : {total_global:.2f}', font=('Arial', 12, 'bold'), fg='#007700').pack(pady=10)

def open_valeur_ventes_par_periode_window():
    win = tk.Toplevel()
    win.title('Valeur des ventes par période')
    win.geometry('950x500')
    tk.Label(win, text='Valeur des ventes par période', font=('Arial', 14, 'bold')).pack(pady=10)
    frame = tk.Frame(win)
    frame.pack(expand=True, fill='both', padx=10, pady=10)
    columns = ('Date', 'ID Client', 'Nom Client', 'Quantité vendue', 'Montant total')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=180, anchor='center')
    tree.pack(expand=True, fill='both')
    periode_frame = tk.Frame(win)
    periode_frame.pack(pady=5)
    tk.Label(periode_frame, text='Date début (YYYY-MM-DD):').pack(side='left')
    date_deb = tk.Entry(periode_frame)
    date_deb.pack(side='left', padx=5)
    tk.Label(periode_frame, text='Date fin (YYYY-MM-DD):').pack(side='left')
    date_fin = tk.Entry(periode_frame)
    date_fin.pack(side='left', padx=5)

    def calculer():
        for i in tree.get_children():
            tree.delete(i)
        deb = date_deb.get()
        fin = date_fin.get()
        conn = connecter()
        cur = conn.cursor()
        cur.execute('SELECT id, nom FROM clients')
        clients = cur.fetchall()
        total_periode = 0
        for client in clients:
            cid, nom = client
            cur.execute('\n                SELECT SUM(quantite), SUM(total) FROM ventes\n                WHERE client_id=? AND date BETWEEN ? AND ?\n            ', (cid, deb, fin))
            qte, montant = cur.fetchone()
            qte = qte or 0
            montant = montant or 0
            total_periode += montant
            tree.insert('', 'end', values=(f'{deb} à {fin}', cid, nom, qte, f'{montant:.2f}'))
        conn.close()
        tk.Label(win, text=f'Montant total sur la période : {total_periode:.2f}', font=('Arial', 12, 'bold'), fg='#007700').pack(pady=10)
    tk.Button(win, text='Calculer', command=calculer, font=('Arial', 12)).pack(pady=10)