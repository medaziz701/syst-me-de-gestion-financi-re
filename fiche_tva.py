import tkinter as tk
from tkinter import messagebox
from database import connecter

def open_fiche_tva_window():
    win = tk.Toplevel()
    win.title('Fiche TVA')
    win.geometry('300x180')
    tk.Label(win, text='Entrer le taux de TVA (%) :', font=('Arial', 12)).pack(pady=10)
    taux_entry = tk.Entry(win, font=('Arial', 12))
    taux_entry.pack(pady=5)

    def enregistrer_tva():
        try:
            taux = float(taux_entry.get())
            conn = connecter()
            cur = conn.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS tva (id INTEGER PRIMARY KEY, taux REAL)')
            cur.execute('DELETE FROM tva')
            cur.execute('INSERT INTO tva (taux) VALUES (?)', (taux,))
            conn.commit()
            conn.close()
            messagebox.showinfo('Succès', f'Taux TVA enregistré : {taux:.2f}%')
            win.destroy()
        except ValueError:
            messagebox.showerror('Erreur', 'Veuillez entrer un taux valide.')
    tk.Button(win, text='Enregistrer', command=enregistrer_tva, font=('Arial', 12)).pack(pady=10)