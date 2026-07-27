import sqlite3
from database import connecter
import tkinter as tk
from tkinter import ttk, messagebox

def ajouter_client(nom, telephone, adresse, email, solde_credit=0):
    conn = connecter()
    cur = conn.cursor()
    try:
        cur.execute('\n            INSERT INTO clients (nom, telephone, adresse, email, solde_credit)\n            VALUES (?, ?, ?, ?, ?)\n        ', (nom, telephone, adresse, email, solde_credit))
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

def modifier_client(client_id, nom=None, telephone=None, adresse=None, email=None, solde_credit=None):
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
    if solde_credit is not None:
        champs.append('solde_credit = ?')
        valeurs.append(solde_credit)
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
    cur.execute('SELECT id, nom, telephone, adresse, email, solde_credit FROM clients')
    clients = cur.fetchall()
    conn.close()
    return clients

class GestionClientsApp:

    def __init__(self, master=None):
        self.master = master if master else tk.Toplevel()
        self.master.title('Gestion des Clients')
        self.master.geometry('800x450')
        self.create_widgets()
        self.refresh_table()

    def create_widgets(self):
        columns = ('ID', 'Nom', 'Téléphone', 'Adresse', 'Email', 'Solde crédit')
        self.tree = ttk.Treeview(self.master, columns=columns, show='headings', height=14)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=120)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
        frm = tk.Frame(self.master)
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
        tk.Label(frm, text='Solde crédit:').grid(row=0, column=8)
        self.entry_solde = tk.Entry(frm, width=10)
        self.entry_solde.grid(row=0, column=9)
        btns = tk.Frame(self.master)
        btns.pack(fill='x', padx=10, pady=5)
        tk.Button(btns, text='Ajouter', command=self.ajouter_client, bg='#44bd32', fg='white').pack(side='left', padx=5)
        tk.Button(btns, text='Modifier', command=self.modifier_client, bg='#273c75', fg='white').pack(side='left', padx=5)
        tk.Button(btns, text='Supprimer', command=self.supprimer_client, bg='#e84118', fg='white').pack(side='left', padx=5)
        tk.Button(btns, text='Fermer', command=self.master.destroy, bg='#718093', fg='white').pack(side='right', padx=5)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for client in lister_clients():
            self.tree.insert('', 'end', values=client)

    def ajouter_client(self):
        nom = self.entry_nom.get().strip()
        tel = self.entry_tel.get().strip()
        adr = self.entry_adr.get().strip()
        email = self.entry_email.get().strip()
        solde = self.entry_solde.get().strip()
        try:
            solde_val = float(solde) if solde else 0
        except Exception:
            messagebox.showerror('Erreur', 'Solde crédit invalide.')
            return
        if not nom:
            messagebox.showwarning('Champs manquants', 'Le nom est obligatoire.')
            return
        if ajouter_client(nom, tel, adr, email, solde_val):
            self.refresh_table()
            self.entry_nom.delete(0, tk.END)
            self.entry_tel.delete(0, tk.END)
            self.entry_adr.delete(0, tk.END)
            self.entry_email.delete(0, tk.END)
            self.entry_solde.delete(0, tk.END)
            messagebox.showinfo('Ajout', 'Client ajouté.')
        else:
            messagebox.showerror('Erreur', "Erreur lors de l'ajout (nom ou email déjà utilisé ?)")

    def supprimer_client(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un client à supprimer.')
            return
        item = self.tree.item(selected[0])
        client_id = item['values'][0]
        supprimer_client(client_id)
        self.refresh_table()
        messagebox.showinfo('Suppression', 'Client supprimé.')

    def modifier_client(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Sélection', 'Sélectionnez un client à modifier.')
            return
        item = self.tree.item(selected[0])
        client_id = item['values'][0]
        nom = self.entry_nom.get().strip()
        tel = self.entry_tel.get().strip()
        adr = self.entry_adr.get().strip()
        email = self.entry_email.get().strip()
        solde = self.entry_solde.get().strip()
        try:
            solde_val = float(solde) if solde else None
        except Exception:
            messagebox.showerror('Erreur', 'Solde crédit invalide.')
            return
        if not nom and (not tel) and (not adr) and (not email) and (solde_val is None):
            messagebox.showwarning('Champs manquants', 'Renseignez au moins un champ à modifier.')
            return
        if modifier_client(client_id, nom or None, tel or None, adr or None, email or None, solde_val):
            self.refresh_table()
            messagebox.showinfo('Modification', 'Client modifié.')
        else:
            messagebox.showerror('Erreur', 'Aucune modification effectuée.')