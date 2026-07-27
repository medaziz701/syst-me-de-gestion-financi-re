import tkinter as tk
from tkinter import ttk
import os
try:
    from ttkthemes import ThemedStyle
except Exception:
    ThemedStyle = None
from database import initialiser_bdd
from gestion_articles import open_articles_window
from gestion_fournisseurs import open_fournisseurs_window
from gestion_ventes import open_ventes_window
from gestion_clients import GestionClientsApp, ReglementClientApp
from listes import open_liste_articles, open_liste_clients, open_liste_fournisseurs

def configurer_style_treeview():
    style = ttk.Style()
    style.configure('Treeview', background='white', foreground='black', rowheight=25)
    style.map('Treeview', background=[('selected', 'black')], foreground=[('selected', 'white')])

def main():
    root = tk.Tk()
    root.title('Système de gestion financière')
    root.geometry('1000x640')
    if ThemedStyle is not None:
        try:
            style = ThemedStyle(root)
            style.set_theme('arc')
        except Exception:
            pass
    configurer_style_treeview()
    menubar = tk.Menu(root)
    menu_fichier = tk.Menu(menubar, tearoff=0)
    menu_fichier.add_command(label='Gestion des articles', command=open_articles_window)
    menu_fichier.add_command(label='Gestion des clients', command=lambda: GestionClientsApp(root))
    menu_fichier.add_command(label='Gestion des fournisseurs', command=open_fournisseurs_window)
    menu_fichier.add_command(label='Gestion des ventes', command=open_ventes_window)
    menu_fichier.add_separator()
    menu_fichier.add_command(label='Quitter', command=root.quit)
    menubar.add_cascade(label='Fichier', menu=menu_fichier)
    menu_listes = tk.Menu(menubar, tearoff=0)
    menu_listes.add_command(label='Liste articles', command=open_liste_articles)
    menu_listes.add_command(label='Liste clients', command=open_liste_clients)
    menu_listes.add_command(label='Liste fournisseurs', command=open_liste_fournisseurs)
    menubar.add_cascade(label='Listes', menu=menu_listes)
    menu_reglements = tk.Menu(menubar, tearoff=0)
    menu_reglements.add_command(label='Règlement client', command=lambda: ReglementClientApp())
    menubar.add_cascade(label='Règlements', menu=menu_reglements)
    root.config(menu=menubar)
    container = ttk.Frame(root, padding=16)
    container.pack(expand=True, fill=tk.BOTH)
    ttk.Label(container, text='Accueil', font=('Segoe UI', 16, 'bold')).pack(anchor='w', pady=(0, 12))
    actions = ttk.Frame(container)
    actions.pack(anchor='w')
    ttk.Button(actions, text='📦 Gérer les articles', command=open_articles_window).grid(row=0, column=0, padx=6, pady=6, sticky='w')
    ttk.Button(actions, text='👥 Gérer les clients', command=lambda: GestionClientsApp(root)).grid(row=0, column=1, padx=6, pady=6, sticky='w')
    ttk.Button(actions, text='🧾 Gérer les ventes', command=open_ventes_window).grid(row=0, column=2, padx=6, pady=6, sticky='w')
    ttk.Button(actions, text='🏭 Gérer les fournisseurs', command=open_fournisseurs_window).grid(row=0, column=3, padx=6, pady=6, sticky='w')
    try:
        root.bind('<Control-Shift-A>', lambda e: open_articles_window())
        root.bind('<Control-Shift-C>', lambda e: GestionClientsApp(root))
        root.bind('<Control-Shift-V>', lambda e: open_ventes_window())
        root.bind('<Control-Shift-F>', lambda e: open_fournisseurs_window())
    except Exception:
        pass
    ttk.Separator(container, orient='horizontal').pack(fill='x', pady=12)
    lists = ttk.Frame(container)
    lists.pack(anchor='w')
    ttk.Button(lists, text='Liste des articles', command=open_liste_articles).grid(row=0, column=0, padx=6, pady=6, sticky='w')
    ttk.Button(lists, text='Liste des clients', command=open_liste_clients).grid(row=0, column=1, padx=6, pady=6, sticky='w')
    ttk.Button(lists, text='Liste des fournisseurs', command=open_liste_fournisseurs).grid(row=0, column=2, padx=6, pady=6, sticky='w')
    root.mainloop()
if __name__ == '__main__':
    try:
        initialiser_bdd()
    except Exception:
        pass
    legacy_path = os.path.join(os.path.dirname(__file__), 'main.py.bak')
    ran_legacy = False
    if os.path.exists(legacy_path):
        try:
            env = {}
            with open(legacy_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            exec(compile(code, legacy_path, 'exec'), env, env)
            if callable(env.get('main')):
                env['initialiser_bdd']() if callable(env.get('initialiser_bdd')) else None
                env['main']()
                ran_legacy = True
        except Exception:
            ran_legacy = False
    if not ran_legacy:
        main()