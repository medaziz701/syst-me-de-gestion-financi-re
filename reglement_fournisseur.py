import tkinter as tk
from tkinter import ttk, messagebox
from database import connecter
import sqlite3

def open_saisie_reglement_fournisseur_window():
    win = tk.Toplevel()
    win.title('Saisie Règlement Fournisseur')
    win.geometry('400x350')
    labels = ['Date (YYYY-MM-DD)', 'Code Fournisseur', 'Nom Fournisseur', 'Montant', 'Mode de paiement']
    entries = []
    code_var = tk.StringVar()
    nom_var = tk.StringVar()
    for i, label in enumerate(labels):
        tk.Label(win, text=label + ' :', font=('Arial', 12)).grid(row=i, column=0, sticky='e', pady=5, padx=5)
        if label == 'Code Fournisseur':

            def choisir_fournisseur():
                sel_win = tk.Toplevel(win)
                sel_win.title('Choisir un fournisseur')
                sel_win.geometry('500x350')
                from tkinter import ttk
                columns = ('ID', 'Nom', 'Email', 'Téléphone', 'Adresse')
                tree = ttk.Treeview(sel_win, columns=columns, show='headings', height=10)
                for col in columns:
                    tree.heading(col, text=col)
                    tree.column(col, anchor='center', width=90)
                tree.pack(fill='both', expand=True, padx=10, pady=10)
                conn = connecter()
                cur = conn.cursor()
                cur.execute('SELECT id, nom, email, telephone, adresse FROM fournisseurs')
                for row in cur.fetchall():
                    tree.insert('', 'end', values=row)
                conn.close()

                def valider():
                    selected = tree.selection()
                    if not selected:
                        messagebox.showwarning('Sélection', 'Sélectionnez un fournisseur.')
                        return
                    values = tree.item(selected[0])['values']
                    code_var.set(str(values[0]))
                    nom_var.set(values[1])
                    entries[2].config(state='normal')
                    entries[2].delete(0, tk.END)
                    entries[2].insert(0, values[1])
                    entries[2].config(state='readonly')
                    sel_win.destroy()
                tk.Button(sel_win, text='Valider', command=valider, bg='#e84118', fg='white', font=('Arial', 12, 'bold')).pack(pady=8)
            btn = tk.Button(win, text='Choisir Fournisseur', command=choisir_fournisseur, bg='#e84118', fg='white', font=('Arial', 11, 'bold'))
            btn.grid(row=i, column=1, pady=5, padx=5, sticky='ew')
            entries.append(None)
        elif label == 'Nom Fournisseur':
            entry = tk.Entry(win, textvariable=nom_var, font=('Arial', 12), state='readonly')
            entry.grid(row=i, column=1, pady=5, padx=5)
            entries.append(entry)
        else:
            entry = tk.Entry(win, font=('Arial', 12))
            entry.grid(row=i, column=1, pady=5, padx=5)
            entries.append(entry)

    def enregistrer_reg():
        try:
            date = entries[0].get()
            code_f = code_var.get()
            nom_f = nom_var.get()
            montant = float(entries[3].get())
            mode = entries[4].get()
            if not code_f:
                messagebox.showwarning('Erreur', 'Veuillez sélectionner un fournisseur.')
                return
        except Exception:
            messagebox.showerror('Erreur', 'Veuillez remplir tous les champs correctement.')
            return
        conn = connecter()
        cur = conn.cursor()
        cur.execute('\n            CREATE TABLE IF NOT EXISTS reglements_fournisseur (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                date TEXT,\n                code_fournisseur TEXT,\n                nom_fournisseur TEXT,\n                montant REAL,\n                mode_paiement TEXT\n            )\n        ')
        cur.execute('INSERT INTO reglements_fournisseur (date, code_fournisseur, nom_fournisseur, montant, mode_paiement) VALUES (?, ?, ?, ?, ?)', (date, code_f, nom_f, montant, mode))
        conn.commit()
        conn.close()
        messagebox.showinfo('Succès', 'Règlement enregistré !')
        win.destroy()
    tk.Button(win, text='Enregistrer', command=enregistrer_reg, font=('Arial', 12)).grid(row=len(labels), column=0, columnspan=2, pady=20)

def open_consultation_reglement_fournisseur_window():
    win = tk.Toplevel()
    win.title('Consultation Règlements Fournisseur')
    win.geometry('800x400')
    columns = ('ID', 'Date', 'Code Fournisseur', 'Nom Fournisseur', 'Montant', 'Mode de paiement')
    tree = ttk.Treeview(win, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor='center')
    tree.pack(expand=True, fill='both', padx=10, pady=10)
    conn = connecter()
    cur = conn.cursor()
    cur.execute('\n        CREATE TABLE IF NOT EXISTS reglement_fournisseur_details (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            reglement_id INTEGER,\n            code_article TEXT,\n            nom_article TEXT,\n            quantite REAL,\n            montant REAL,\n            bon_id INTEGER,\n            ligne_id INTEGER,\n            notes TEXT\n        )\n        ')
    cur.execute('\n        CREATE TABLE IF NOT EXISTS reglements_fournisseur (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            date TEXT,\n            code_fournisseur TEXT,\n            nom_fournisseur TEXT,\n            montant REAL,\n            mode_paiement TEXT\n        )\n    ')
    cur.execute('\n        CREATE TABLE IF NOT EXISTS bons_commande (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            date TEXT,\n            code_fournisseur TEXT,\n            nom_fournisseur TEXT,\n            id_produit INTEGER,\n            nom_produit TEXT,\n            quantite INTEGER,\n            prix_unitaire REAL,\n            remise REAL,\n            montant_total REAL\n        )\n        ')
    cur.execute('SELECT id, date, code_fournisseur, nom_fournisseur, montant, mode_paiement FROM reglements_fournisseur ORDER BY date DESC')
    for row in cur.fetchall():
        tree.insert('', 'end', values=row)
    cur.execute('SELECT code_fournisseur, nom_fournisseur, SUM(montant_total) FROM bons_commande GROUP BY code_fournisseur, nom_fournisseur')
    totaux = {(code, nom): total for code, nom, total in cur.fetchall()}
    cur.execute('SELECT code_fournisseur, nom_fournisseur, SUM(montant) FROM reglements_fournisseur GROUP BY code_fournisseur, nom_fournisseur')
    regles = {(code, nom): total for code, nom, total in cur.fetchall()}
    infos = []
    for key in totaux:
        total = totaux[key] or 0
        regle = regles.get(key, 0) or 0
        reste = total - regle
        infos.append(f'Fournisseur {key[1]} (Code: {key[0]}) : Total à payer = {total:.2f} | Payé = {regle:.2f} | Reste = {reste:.2f}')
    if infos:
        tk.Label(win, text='\n'.join(infos), font=('Arial', 11, 'bold'), fg='#007700').pack(pady=10)
    conn.close()

    def supprimer_reg():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un règlement à supprimer.')
            return
        item = tree.item(selected[0])
        reg_id = item['values'][0]
        if messagebox.askyesno('Confirmation', 'Supprimer ce règlement ?'):
            conn = connecter()
            cur = conn.cursor()
            cur.execute('DELETE FROM reglements_fournisseur WHERE id = ?', (reg_id,))
            try:
                cur.execute('DELETE FROM reglement_fournisseur_details WHERE reglement_id = ?', (reg_id,))
            except Exception:
                pass
            conn.commit()
            conn.close()
            tree.delete(selected[0])

    def modifier_reg():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un règlement à modifier.')
            return
        item = tree.item(selected[0])
        values = item['values']
        modif_win = tk.Toplevel(win)
        modif_win.title('Modifier Règlement Fournisseur')
        labels = ['Date (YYYY-MM-DD)', 'Code Fournisseur', 'Nom Fournisseur', 'Montant', 'Mode de paiement']
        entries = []
        for i, label in enumerate(labels):
            tk.Label(modif_win, text=label + ' :', font=('Arial', 12)).grid(row=i, column=0, sticky='e', pady=5, padx=5)
            entry = tk.Entry(modif_win, font=('Arial', 12))
            entry.insert(0, str(values[i + 1]))
            entry.grid(row=i, column=1, pady=5, padx=5)
            entries.append(entry)

        def valider_modif():
            try:
                date, code_f, nom_f, montant, mode = [e.get() for e in entries]
                montant = float(montant)
            except Exception:
                messagebox.showerror('Erreur', 'Veuillez remplir tous les champs correctement.')
                return
            conn = connecter()
            cur = conn.cursor()
            cur.execute('UPDATE reglements_fournisseur SET date=?, code_fournisseur=?, nom_fournisseur=?, montant=?, mode_paiement=? WHERE id=?', (date, code_f, nom_f, montant, mode, values[0]))
            conn.commit()
            conn.close()
            tree.item(selected[0], values=(values[0], date, code_f, nom_f, montant, mode))
            modif_win.destroy()
            messagebox.showinfo('Succès', 'Règlement modifié !')

    def voir_details():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Sélectionnez un règlement.')
            return
        reg_values = tree.item(sel[0], 'values')
        reg_id = reg_values[0]
        dlg = tk.Toplevel(win)
        dlg.title(f'Détails du règlement #{reg_id}')
        dlg.geometry('780x420')
        cols = ('Code', 'Article', 'Quantité', 'Montant', 'Bon #', 'Ligne #', 'Notes')
        tv = ttk.Treeview(dlg, columns=cols, show='headings', height=14)
        for c in cols:
            tv.heading(c, text=c)
            width = 140 if c in ('Article', 'Notes') else 90
            tv.column(c, anchor='center', width=width)
        tv.pack(fill='both', expand=True, padx=10, pady=10)
        conn2 = connecter()
        cur2 = conn2.cursor()
        cur2.execute("SELECT code_article, nom_article, COALESCE(quantite,0), COALESCE(montant,0), COALESCE(bon_id,''), COALESCE(ligne_id,''), COALESCE(notes,'') FROM reglement_fournisseur_details WHERE reglement_id=? ORDER BY id", (reg_id,))
        for r in cur2.fetchall():
            tv.insert('', 'end', values=r)
        conn2.close()
        ttk.Button(dlg, text='Fermer', command=dlg.destroy).pack(pady=6)

    def ajouter_details():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Sélectionnez un règlement.')
            return
        reg_values = tree.item(sel[0], 'values')
        reg_id, _date, code_f, nom_f, montant, _mode = reg_values
        add = tk.Toplevel(win)
        add.title(f'Ajouter détails - Règlement #{reg_id} - {nom_f}')
        add.geometry('840x520')
        tk.Label(add, text=f'Fournisseur: {nom_f} (code {code_f})').pack(anchor='w', padx=10, pady=6)
        frame = tk.Frame(add)
        frame.pack(fill='both', expand=True, padx=10, pady=6)
        cols = ('Sel', 'Bon #', 'Ligne #', 'Code', 'Article', 'Quantité', 'PU', 'Montant à affecter')
        tv = ttk.Treeview(frame, columns=cols, show='headings', height=14, selectmode='none')
        for c in cols:
            tv.heading(c, text=c)
            w = 110
            if c in ('Article',):
                w = 180
            if c in ('Montant à affecter',):
                w = 140
            tv.column(c, anchor='center', width=w)
        tv.pack(side='left', fill='both', expand=True)
        vsb = ttk.Scrollbar(frame, orient='vertical', command=tv.yview)
        tv.configure(yscroll=vsb.set)
        vsb.pack(side='right', fill='y')
        conn2 = connecter()
        cur2 = conn2.cursor()

        def _table_exists(name):
            try:
                cur2.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
                return cur2.fetchone() is not None
            except Exception:
                return False
        rows = []
        try:
            if _table_exists('bon_commande_ligne') and _table_exists('bon_commande'):
                cur2.execute("\n                    SELECT l.rowid, b.id, l.code_produit, COALESCE(l.nom_produit,''), COALESCE(l.quantite,0), COALESCE(l.prix_unitaire,0)\n                    FROM bon_commande b JOIN bon_commande_ligne l ON l.bon_id=b.id\n                    WHERE COALESCE(b.code_fournisseur,'')=? OR COALESCE(b.nom_fournisseur,'')=?\n                    ORDER BY b.date DESC, b.id DESC\n                    ", (str(code_f), str(nom_f)))
                rows = cur2.fetchall()
            elif _table_exists('bons_commande'):
                cur2.execute("\n                    SELECT rowid, id, id_produit, COALESCE(nom_produit,''), COALESCE(quantite,0), COALESCE(prix_unitaire,0)\n                    FROM bons_commande\n                    WHERE COALESCE(code_fournisseur,'')=? OR COALESCE(nom_fournisseur,'')=?\n                    ORDER BY date DESC, id DESC\n                    ", (str(code_f), str(nom_f)))
                rows = cur2.fetchall()
        except Exception:
            rows = []
        finally:
            conn2.close()
        for rid, bon_id, code_a, nom_a, qte, pu in rows:
            iid = tv.insert('', 'end', values=(' ', bon_id, rid, code_a, nom_a, qte, pu, 0.0))
        edit = tk.Frame(add)
        edit.pack(fill='x', padx=10, pady=8)
        tk.Label(edit, text='Ligne #:').grid(row=0, column=0, sticky='e')
        e_ligne = ttk.Entry(edit, width=10)
        e_ligne.grid(row=0, column=1, padx=4)
        tk.Label(edit, text='Montant à affecter:').grid(row=0, column=2, sticky='e')
        e_montant = ttk.Entry(edit, width=12)
        e_montant.grid(row=0, column=3, padx=4)
        tk.Label(edit, text='Quantité:').grid(row=0, column=4, sticky='e')
        e_qte = ttk.Entry(edit, width=10)
        e_qte.grid(row=0, column=5, padx=4)
        tk.Label(edit, text='Notes:').grid(row=0, column=6, sticky='e')
        e_notes = ttk.Entry(edit, width=28)
        e_notes.grid(row=0, column=7, padx=4)

        def remplir_depuis_selection(event=None):
            sel_iid = tv.focus()
            if not sel_iid:
                return
            vals = tv.item(sel_iid, 'values')
            e_ligne.delete(0, tk.END)
            e_ligne.insert(0, str(vals[2]))
            e_qte.delete(0, tk.END)
            e_qte.insert(0, str(vals[5]))
        tv.bind('<<TreeviewSelect>>', remplir_depuis_selection)

        def enregistrer_affectation():
            try:
                ligne_id = int(e_ligne.get())
            except Exception:
                messagebox.showwarning('Saisie', 'Spécifiez la Ligne # (ID de ligne)')
                return
            try:
                montant_aff = float(e_montant.get() or 0)
            except Exception:
                montant_aff = 0.0
            try:
                qte_aff = float(e_qte.get() or 0)
            except Exception:
                qte_aff = 0.0
            note_txt = e_notes.get().strip()
            found = None
            for iid in tv.get_children():
                vals = tv.item(iid, 'values')
                try:
                    if int(vals[2]) == ligne_id:
                        found = vals
                        break
                except Exception:
                    continue
            if not found:
                messagebox.showwarning('Ligne', 'Ligne non trouvée dans la liste.')
                return
            bon_id = found[1]
            code_a = str(found[3] or '')
            nom_a = str(found[4] or '')
            conn3 = connecter()
            cur3 = conn3.cursor()
            cur3.execute('\n                INSERT INTO reglement_fournisseur_details\n                    (reglement_id, code_article, nom_article, quantite, montant, bon_id, ligne_id, notes)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                ', (reg_id, code_a, nom_a, qte_aff, montant_aff, bon_id, ligne_id, note_txt))
            conn3.commit()
            conn3.close()
            messagebox.showinfo('Détails', 'Ligne ajoutée au règlement.')
            e_ligne.delete(0, tk.END)
            e_montant.delete(0, tk.END)
            e_qte.delete(0, tk.END)
            e_notes.delete(0, tk.END)
        tk.Button(add, text="Enregistrer l'affectation", command=enregistrer_affectation, bg='#44bd32', fg='white').pack(pady=8)
        ttk.Button(add, text='Fermer', command=add.destroy).pack(pady=4)
    btns = tk.Frame(win)
    btns.pack(pady=10)
    tk.Button(btns, text='Voir détails', command=voir_details, bg='#00a8ff', fg='white').pack(side='left', padx=5)
    tk.Button(btns, text='Ajouter détails', command=ajouter_details, bg='#273c75', fg='white').pack(side='left', padx=5)
    tk.Button(btns, text='Modifier', command=modifier_reg, bg='#FFC107').pack(side='left', padx=5)
    tk.Button(btns, text='Supprimer', command=supprimer_reg, bg='#F44336', fg='white').pack(side='left', padx=5)