import tkinter as tk
from tkinter import ttk, messagebox
from database import connecter

def afficher_fournisseurs(tree):
    for row in tree.get_children():
        tree.delete(row)
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, nom, email, telephone, adresse FROM fournisseurs')
        for row in cur.fetchall():
            tree.insert('', 'end', values=row)
    except Exception as e:
        messagebox.showerror('Erreur', f'Erreur de lecture: {e}')
    finally:
        conn.close()

def open_fournisseurs_window():
    win = tk.Toplevel()
    win.title('Gestion des Fournisseurs')
    win.geometry('900x600')
    form_frame = tk.Frame(win, padx=10, pady=10)
    form_frame.pack(fill=tk.X)
    tk.Label(form_frame, text='Nom:').grid(row=0, column=0, sticky='e')
    nom_entry = tk.Entry(form_frame, width=30)
    nom_entry.grid(row=0, column=1, pady=5)
    tk.Label(form_frame, text='Email:').grid(row=1, column=0, sticky='e')
    email_entry = tk.Entry(form_frame, width=30)
    email_entry.grid(row=1, column=1, pady=5)
    tk.Label(form_frame, text='Téléphone:').grid(row=2, column=0, sticky='e')
    tel_entry = tk.Entry(form_frame, width=30)
    tel_entry.grid(row=2, column=1, pady=5)
    tk.Label(form_frame, text='Adresse:').grid(row=3, column=0, sticky='e')
    adresse_entry = tk.Entry(form_frame, width=30)
    adresse_entry.grid(row=3, column=1, pady=5)

    def submit():
        conn = connecter()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO fournisseurs (nom, email, telephone, adresse) VALUES (?, ?, ?, ?)', (nom_entry.get(), email_entry.get(), tel_entry.get(), adresse_entry.get()))
            conn.commit()
            afficher_fournisseurs(tree)
            nom_entry.delete(0, tk.END)
            email_entry.delete(0, tk.END)
            tel_entry.delete(0, tk.END)
            adresse_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror('Erreur', f'Erreur: {e}')
        finally:
            conn.close()
    btn_ajouter = tk.Button(form_frame, text='Ajouter Fournisseur', command=submit)
    btn_ajouter.grid(row=4, column=1, pady=10)
    tree_frame = tk.Frame(win)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    tree = ttk.Treeview(tree_frame, columns=('ID', 'Nom', 'Email', 'Téléphone', 'Adresse'), show='headings')
    for col in tree['columns']:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(fill=tk.BOTH, expand=True)

    def supprimer_fournisseur():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un fournisseur à supprimer.')
            return
        item = tree.item(selected[0])
        fournisseur_id = item['values'][0]
        if messagebox.askyesno('Confirmation', 'Supprimer ce fournisseur ?'):
            conn = connecter()
            cur = conn.cursor()
            cur.execute('DELETE FROM fournisseurs WHERE id = ?', (fournisseur_id,))
            conn.commit()
            conn.close()
            afficher_fournisseurs(tree)

    def modifier_fournisseur():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un fournisseur à modifier.')
            return
        item = tree.item(selected[0])
        fournisseur_id, nom, email, telephone, adresse = item['values']
        modif_win = tk.Toplevel(win)
        modif_win.title('Modifier Fournisseur')
        tk.Label(modif_win, text='Nom:').grid(row=0, column=0)
        nom_entry_mod = tk.Entry(modif_win)
        nom_entry_mod.insert(0, nom)
        nom_entry_mod.grid(row=0, column=1)
        tk.Label(modif_win, text='Email:').grid(row=1, column=0)
        email_entry_mod = tk.Entry(modif_win)
        email_entry_mod.insert(0, email)
        email_entry_mod.grid(row=1, column=1)
        tk.Label(modif_win, text='Téléphone:').grid(row=2, column=0)
        tel_entry_mod = tk.Entry(modif_win)
        tel_entry_mod.insert(0, telephone)
        tel_entry_mod.grid(row=2, column=1)
        tk.Label(modif_win, text='Adresse:').grid(row=3, column=0)
        adresse_entry_mod = tk.Entry(modif_win)
        adresse_entry_mod.insert(0, adresse)
        adresse_entry_mod.grid(row=3, column=1)

        def valider_modif():
            conn = connecter()
            cur = conn.cursor()
            cur.execute('UPDATE fournisseurs SET nom=?, email=?, telephone=?, adresse=? WHERE id=?', (nom_entry_mod.get(), email_entry_mod.get(), tel_entry_mod.get(), adresse_entry_mod.get(), fournisseur_id))
            conn.commit()
            conn.close()
            afficher_fournisseurs(tree)
            modif_win.destroy()
        tk.Button(modif_win, text='Valider', command=valider_modif).grid(row=4, column=0, columnspan=2)
    btns_frame = tk.Frame(win)
    btns_frame.pack(pady=5)
    tk.Button(btns_frame, text='Modifier Fournisseur', command=modifier_fournisseur).pack(side='left', padx=5)
    tk.Button(btns_frame, text='Supprimer Fournisseur', command=supprimer_fournisseur).pack(side='left', padx=5)
    afficher_fournisseurs(tree)