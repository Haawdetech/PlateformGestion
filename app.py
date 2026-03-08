from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
import socket
import json
import platform
import threading
import time
import urllib.request
import subprocess

# Fix: résolution DNS lente sur macOS / Python 3.14
socket.getfqdn = lambda name='': 'localhost'

# ── Chemins : mode normal vs exécutable PyInstaller ──────────────────
if getattr(sys, 'frozen', False):
    # Dans l'exécutable PyInstaller, les ressources sont dans sys._MEIPASS
    BASE_DIR = sys._MEIPASS
    # La base de données est stockée dans ~/BoutikManager (hors du bundle)
    DATA_DIR = os.path.join(os.path.expanduser('~'), 'BoutikManager')
    os.makedirs(DATA_DIR, exist_ok=True)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR

DATABASE = os.path.join(DATA_DIR, 'boutique.db')

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = 'boutikmanager-secret-2024-xk9p'

# Version actuelle de l'application (à incrémenter à chaque update)
APP_VERSION = '1.3'


# ══════════════════════════ DB HELPERS ══════════════════════════════

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            full_name     TEXT,
            role          TEXT    DEFAULT 'user',
            active        INTEGER DEFAULT 1,
            created_at    TEXT    DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT,
            price       REAL    NOT NULL,
            stock       INTEGER,
            created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT    UNIQUE NOT NULL,
            client_name    TEXT,
            client_email   TEXT,
            client_address TEXT,
            client_phone   TEXT,
            notes          TEXT,
            total          REAL    NOT NULL DEFAULT 0,
            created_at     TEXT    DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS invoice_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id   INTEGER NOT NULL,
            product_id   INTEGER,
            product_name TEXT    NOT NULL,
            description  TEXT,
            unit_price   REAL    NOT NULL,
            quantity     INTEGER NOT NULL DEFAULT 1,
            subtotal     REAL    NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    ''')

    defaults = [
        ('shop_name',    'Mon Entreprise'),
        ('shop_address', '123 Rue Principale, Ville'),
        ('shop_phone',   '+212 6XX-XXXXXX'),
        ('shop_email',   'contact@monentreprise.ma'),
        ('shop_ice',     ''),
        ('currency',     'DH'),
        ('github_repo',  ''),   # ex: monnom/BoutikManager
    ]
    for key, val in defaults:
        conn.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))

    # Créer admin par défaut si aucun utilisateur
    if not conn.execute('SELECT id FROM users LIMIT 1').fetchone():
        conn.execute(
            'INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
            ('admin', generate_password_hash('admin123'), 'Administrateur', 'admin')
        )
        print('\n  ⚠️  Compte admin créé  →  login: admin  /  mdp: admin123')
        print('     Changez le mot de passe dans Mon Compte !\n')

    conn.commit()
    conn.close()


def get_settings():
    conn = get_db()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}


def generate_invoice_number():
    conn = get_db()
    year = datetime.now().year
    row  = conn.execute(
        "SELECT COUNT(*) AS cnt FROM invoices WHERE invoice_number LIKE ?",
        (f'FACT-{year}-%',)
    ).fetchone()
    conn.close()
    return f'FACT-{year}-{(row["cnt"] + 1):04d}'


def parse_invoice_items():
    """Parse les articles du formulaire. Retourne (items, total)."""
    names  = request.form.getlist('item_name[]')
    descs  = request.form.getlist('item_description[]')
    pids   = request.form.getlist('item_product_id[]')
    prices = request.form.getlist('item_price[]')
    qtys   = request.form.getlist('item_quantity[]')

    items = []
    total = 0.0

    for i, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        try:
            price    = float((prices[i] if i < len(prices) else '0').replace(',', '.'))
            qty      = max(1, int(qtys[i] if i < len(qtys) else '1'))
            subtotal = round(price * qty, 2)
            total   += subtotal
            items.append({
                'product_id':   int(pids[i]) if i < len(pids) and pids[i] else None,
                'product_name': name,
                'description':  descs[i].strip() if i < len(descs) else '',
                'unit_price':   price,
                'quantity':     qty,
                'subtotal':     subtotal,
            })
        except (ValueError, IndexError):
            continue

    return items, round(total, 2)


# ══════════════════════════ AUTH ════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute(
        'SELECT id, username, full_name, role FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    return user


# ══════════════════════════ JINJA2 GLOBALS ══════════════════════════

@app.context_processor
def inject_globals():
    s = get_settings()
    return {
        'now':          datetime.now(),
        'settings':     s,
        'currency':     s.get('currency', 'DH'),
        'current_user': get_current_user(),
        'app_version':  APP_VERSION,
        'github_repo':  s.get('github_repo', ''),
    }


@app.template_filter('fmt_date')
def fmt_date(value):
    if not value:
        return ''
    try:
        return datetime.strptime(str(value)[:19], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(value)[:10]


@app.template_filter('fmt_date_short')
def fmt_date_short(value):
    if not value:
        return ''
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        return str(value)[:10]


@app.template_filter('fmt_price')
def fmt_price(value):
    try:
        return f'{float(value):,.2f}'.replace(',', ' ').replace('.', ',')
    except Exception:
        return '0,00'


# ══════════════════════════ HOME ════════════════════════════════════

@app.route('/')
@login_required
def index():
    return redirect(url_for('products'))


# ══════════════════════════ AUTH ROUTES ═════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND active = 1', (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id']   = user['id']
            session['username']  = user['username']
            session['full_name'] = user['full_name'] or user['username']
            session['role']      = user['role']
            return redirect(request.args.get('next', url_for('index')))

        flash('Identifiant ou mot de passe incorrect.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ══════════════════════════ USERS (ADMIN) ═══════════════════════════

@app.route('/utilisateurs')
@admin_required
def users_list():
    conn  = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY role DESC, username').fetchall()
    conn.close()
    return render_template('users.html', users=users)


@app.route('/utilisateurs/ajouter', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username  = request.form.get('username', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password  = request.form.get('password', '')
        role      = request.form.get('role', 'user')

        errors = []
        if not username:
            errors.append("Le nom d'utilisateur est obligatoire.")
        if len(password) < 4:
            errors.append("Le mot de passe doit faire au moins 4 caractères.")

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('user_form.html', user=None, action='Ajouter')

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
                (username, generate_password_hash(password), full_name or username, role)
            )
            conn.commit()
            flash(f'Utilisateur « {username} » créé !', 'success')
        except sqlite3.IntegrityError:
            flash(f'Le nom « {username} » est déjà utilisé.', 'danger')
            conn.close()
            return render_template('user_form.html', user=None, action='Ajouter')
        conn.close()
        return redirect(url_for('users_list'))

    return render_template('user_form.html', user=None, action='Ajouter')


@app.route('/utilisateurs/<int:uid>/modifier', methods=['GET', 'POST'])
@admin_required
def edit_user(uid):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    conn.close()

    if not user:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for('users_list'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        role      = request.form.get('role', 'user')
        password  = request.form.get('password', '')
        active    = 1 if request.form.get('active') else 0

        if user['role'] == 'admin' and (role != 'admin' or not active):
            conn2 = get_db()
            cnt   = conn2.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role='admin' AND active=1"
            ).fetchone()['c']
            conn2.close()
            if cnt <= 1:
                flash('Il doit rester au moins un administrateur actif.', 'danger')
                return redirect(url_for('users_list'))

        conn = get_db()
        if password and len(password) >= 4:
            conn.execute(
                'UPDATE users SET full_name=?, role=?, active=?, password_hash=? WHERE id=?',
                (full_name, role, active, generate_password_hash(password), uid)
            )
        else:
            conn.execute(
                'UPDATE users SET full_name=?, role=?, active=? WHERE id=?',
                (full_name, role, active, uid)
            )
        conn.commit()
        conn.close()
        flash('Utilisateur modifié !', 'success')
        return redirect(url_for('users_list'))

    return render_template('user_form.html', user=user, action='Modifier')


@app.route('/utilisateurs/<int:uid>/supprimer', methods=['POST'])
@admin_required
def delete_user(uid):
    if uid == session.get('user_id'):
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('users_list'))

    conn = get_db()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (uid,)).fetchone()
    if user:
        conn.execute('DELETE FROM users WHERE id = ?', (uid,))
        conn.commit()
        flash(f'Utilisateur « {user["username"]} » supprimé.', 'warning')
    conn.close()
    return redirect(url_for('users_list'))


# ══════════════════════════ MON COMPTE ══════════════════════════════

@app.route('/mon-compte', methods=['GET', 'POST'])
@login_required
def my_account():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw     = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not check_password_hash(user['password_hash'], current_pw):
            flash('Mot de passe actuel incorrect.', 'danger')
        elif new_pw != confirm_pw:
            flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
        elif len(new_pw) < 4:
            flash('Le nouveau mot de passe doit faire au moins 4 caractères.', 'danger')
        else:
            conn.execute(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                (generate_password_hash(new_pw), session['user_id'])
            )
            conn.commit()
            flash('Mot de passe modifié avec succès !', 'success')
        conn.close()

    return render_template('my_account.html')


# ══════════════════════════ PRODUCTS ════════════════════════════════

@app.route('/produits')
@login_required
def products():
    conn  = get_db()
    prods = conn.execute('SELECT * FROM products ORDER BY name COLLATE NOCASE').fetchall()
    conn.close()
    return render_template('products.html', products=prods)


@app.route('/produits/ajouter', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name      = request.form.get('name', '').strip()
        desc      = request.form.get('description', '').strip()
        price_raw = request.form.get('price', '').strip().replace(',', '.')
        stock_raw = request.form.get('stock', '').strip()

        errors = []
        if not name:
            errors.append('Le nom est obligatoire.')
        price_val = None
        if not price_raw:
            errors.append('Le prix est obligatoire.')
        else:
            try:
                price_val = float(price_raw)
                if price_val < 0:
                    errors.append('Le prix doit être positif.')
            except ValueError:
                errors.append('Prix invalide.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('product_form.html', product=None, action='Ajouter')

        conn = get_db()
        conn.execute(
            'INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)',
            (name, desc or None, price_val, int(stock_raw) if stock_raw.isdigit() else None)
        )
        conn.commit()
        conn.close()
        flash(f'Produit « {name} » ajouté !', 'success')
        return redirect(url_for('products'))

    return render_template('product_form.html', product=None, action='Ajouter')


@app.route('/produits/<int:pid>/modifier', methods=['GET', 'POST'])
@login_required
def edit_product(pid):
    conn    = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
    conn.close()

    if not product:
        flash('Produit introuvable.', 'danger')
        return redirect(url_for('products'))

    if request.method == 'POST':
        name      = request.form.get('name', '').strip()
        desc      = request.form.get('description', '').strip()
        price_raw = request.form.get('price', '').strip().replace(',', '.')
        stock_raw = request.form.get('stock', '').strip()

        errors = []
        if not name:
            errors.append('Le nom est obligatoire.')
        price_val = None
        if not price_raw:
            errors.append('Le prix est obligatoire.')
        else:
            try:
                price_val = float(price_raw)
            except ValueError:
                errors.append('Prix invalide.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('product_form.html', product=product, action='Modifier')

        conn = get_db()
        conn.execute(
            'UPDATE products SET name=?, description=?, price=?, stock=? WHERE id=?',
            (name, desc or None, price_val, int(stock_raw) if stock_raw.isdigit() else None, pid)
        )
        conn.commit()
        conn.close()
        flash(f'Produit « {name} » modifié !', 'success')
        return redirect(url_for('products'))

    return render_template('product_form.html', product=product, action='Modifier')


@app.route('/produits/<int:pid>/supprimer', methods=['POST'])
@login_required
def delete_product(pid):
    conn    = get_db()
    product = conn.execute('SELECT name FROM products WHERE id = ?', (pid,)).fetchone()
    if product:
        conn.execute('DELETE FROM products WHERE id = ?', (pid,))
        conn.commit()
        flash(f'Produit « {product["name"]} » supprimé.', 'warning')
    conn.close()
    return redirect(url_for('products'))


@app.route('/api/produits')
@login_required
def api_products():
    conn  = get_db()
    prods = conn.execute('SELECT * FROM products ORDER BY name COLLATE NOCASE').fetchall()
    conn.close()
    return jsonify([dict(p) for p in prods])


# ══════════════════════════ INVOICES ════════════════════════════════

@app.route('/factures')
@login_required
def invoices():
    conn          = get_db()
    invs          = conn.execute('SELECT * FROM invoices ORDER BY created_at DESC').fetchall()
    total_revenue = sum(i['total'] for i in invs)
    conn.close()
    return render_template('invoices.html', invoices=invs, total_revenue=total_revenue)


@app.route('/factures/creer', methods=['GET', 'POST'])
@login_required
def create_invoice():
    if request.method == 'POST':
        items, total = parse_invoice_items()

        if not items:
            flash('Veuillez ajouter au moins un article.', 'danger')
            conn  = get_db()
            prods = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            conn.close()
            return render_template('create_invoice.html', products=prods)

        invoice_number = generate_invoice_number()
        conn = get_db()
        cur  = conn.execute(
            '''INSERT INTO invoices
               (invoice_number, client_name, client_email, client_address, client_phone, notes, total)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (invoice_number,
             request.form.get('client_name', '').strip() or None,
             request.form.get('client_email', '').strip() or None,
             request.form.get('client_address', '').strip() or None,
             request.form.get('client_phone', '').strip() or None,
             request.form.get('notes', '').strip() or None,
             total)
        )
        iid = cur.lastrowid
        for item in items:
            conn.execute(
                '''INSERT INTO invoice_items
                   (invoice_id, product_id, product_name, description, unit_price, quantity, subtotal)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (iid, item['product_id'], item['product_name'], item['description'],
                 item['unit_price'], item['quantity'], item['subtotal'])
            )
        conn.commit()
        conn.close()
        flash(f'Facture {invoice_number} créée avec succès !', 'success')
        return redirect(url_for('invoice_detail', iid=iid))

    conn  = get_db()
    prods = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
    conn.close()
    return render_template('create_invoice.html', products=prods)


@app.route('/factures/<int:iid>/modifier', methods=['GET', 'POST'])
@login_required
def edit_invoice(iid):
    conn    = get_db()
    invoice = conn.execute('SELECT * FROM invoices WHERE id = ?', (iid,)).fetchone()

    if not invoice:
        flash('Facture introuvable.', 'danger')
        conn.close()
        return redirect(url_for('invoices'))

    if request.method == 'POST':
        items, total = parse_invoice_items()

        if not items:
            flash('Veuillez ajouter au moins un article.', 'danger')
            prods       = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            exist_items = conn.execute(
                'SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id', (iid,)
            ).fetchall()
            conn.close()
            return render_template('edit_invoice.html', invoice=invoice,
                                   products=prods, items_list=[dict(i) for i in exist_items])

        conn.execute(
            '''UPDATE invoices
               SET client_name=?, client_email=?, client_address=?, client_phone=?, notes=?, total=?
               WHERE id=?''',
            (request.form.get('client_name', '').strip() or None,
             request.form.get('client_email', '').strip() or None,
             request.form.get('client_address', '').strip() or None,
             request.form.get('client_phone', '').strip() or None,
             request.form.get('notes', '').strip() or None,
             total, iid)
        )
        conn.execute('DELETE FROM invoice_items WHERE invoice_id = ?', (iid,))
        for item in items:
            conn.execute(
                '''INSERT INTO invoice_items
                   (invoice_id, product_id, product_name, description, unit_price, quantity, subtotal)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (iid, item['product_id'], item['product_name'], item['description'],
                 item['unit_price'], item['quantity'], item['subtotal'])
            )
        conn.commit()
        conn.close()
        flash(f'Facture {invoice["invoice_number"]} modifiée avec succès !', 'success')
        return redirect(url_for('invoice_detail', iid=iid))

    exist_items = conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id', (iid,)
    ).fetchall()
    prods = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
    conn.close()
    return render_template('edit_invoice.html', invoice=invoice,
                           products=prods, items_list=[dict(i) for i in exist_items])


@app.route('/factures/<int:iid>')
@login_required
def invoice_detail(iid):
    conn    = get_db()
    invoice = conn.execute('SELECT * FROM invoices WHERE id = ?', (iid,)).fetchone()
    if not invoice:
        flash('Facture introuvable.', 'danger')
        conn.close()
        return redirect(url_for('invoices'))
    items = conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY id', (iid,)
    ).fetchall()
    conn.close()
    return render_template('invoice_detail.html', invoice=invoice, items=items)


@app.route('/factures/<int:iid>/imprimer')
@login_required
def print_invoice(iid):
    conn    = get_db()
    invoice = conn.execute('SELECT * FROM invoices WHERE id = ?', (iid,)).fetchone()
    if not invoice:
        conn.close()
        return 'Facture introuvable', 404
    items = conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY id', (iid,)
    ).fetchall()
    conn.close()
    return render_template('invoice_print.html', invoice=invoice, items=items)


@app.route('/factures/<int:iid>/supprimer', methods=['POST'])
@login_required
def delete_invoice(iid):
    conn    = get_db()
    invoice = conn.execute('SELECT invoice_number FROM invoices WHERE id = ?', (iid,)).fetchone()
    if invoice:
        conn.execute('DELETE FROM invoice_items WHERE invoice_id = ?', (iid,))
        conn.execute('DELETE FROM invoices WHERE id = ?', (iid,))
        conn.commit()
        flash(f'Facture {invoice["invoice_number"]} supprimée.', 'warning')
    conn.close()
    return redirect(url_for('invoices'))


# ══════════════════════════ SETTINGS ════════════════════════════════

@app.route('/parametres', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        conn = get_db()
        for field in ['shop_name', 'shop_address', 'shop_phone', 'shop_email', 'shop_ice', 'currency', 'github_repo']:
            conn.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (field, request.form.get(field, '').strip())
            )
        conn.commit()
        conn.close()
        flash('Paramètres enregistrés !', 'success')
        return redirect(url_for('settings'))

    s = get_settings()
    return render_template('settings.html', s=s)


# ══════════════════════════ AUTO-UPDATE ═════════════════════════════

@app.route('/api/auto-update')
@login_required
def auto_update():
    """Télécharge et installe automatiquement la nouvelle version."""
    if not getattr(sys, 'frozen', False):
        return jsonify({'error': 'Auto-update disponible uniquement sur l\'exécutable compilé.'}), 400

    s        = get_settings()
    repo     = s.get('github_repo', '').strip()
    if not repo:
        return jsonify({'error': 'Dépôt GitHub non configuré dans les paramètres.'}), 400

    try:
        # 1 — Récupérer l'URL de téléchargement depuis GitHub API
        req = urllib.request.Request(
            f'https://api.github.com/repos/{repo}/releases/latest',
            headers={'User-Agent': 'BoutikManager'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            release = json.loads(r.read())

        is_windows   = platform.system() == 'Windows'
        asset_name   = 'BoutikManager.exe' if is_windows else 'BoutikManager'
        download_url = None
        for asset in release.get('assets', []):
            if asset['name'] == asset_name:
                download_url = asset['browser_download_url']
                break

        if not download_url:
            return jsonify({'error': f'Fichier {asset_name} introuvable dans la release.'}), 404

        # 2 — Télécharger la nouvelle version
        current_exe = sys.executable
        new_exe     = current_exe + '.new'
        urllib.request.urlretrieve(download_url, new_exe)

        # 3 — Créer le script de remplacement + redémarrage
        if is_windows:
            script_path = current_exe + '_update.bat'
            script = (
                f'@echo off\r\n'
                f'timeout /t 2 /nobreak >nul\r\n'
                f'move /y "{new_exe}" "{current_exe}"\r\n'
                f'start "" "{current_exe}"\r\n'
                f'del "%~f0"\r\n'
            )
            with open(script_path, 'w') as f:
                f.write(script)
            subprocess.Popen(['cmd', '/c', script_path],
                             creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            script_path = current_exe + '_update.sh'
            script = (
                f'#!/bin/bash\n'
                f'sleep 2\n'
                f'mv "{new_exe}" "{current_exe}"\n'
                f'chmod +x "{current_exe}"\n'
                f'"{current_exe}" &\n'
                f'rm -- "$0"\n'
            )
            with open(script_path, 'w') as f:
                f.write(script)
            os.chmod(script_path, 0o755)
            subprocess.Popen(['/bin/bash', script_path])

        # 4 — Arrêter le serveur actuel après 1,5 s
        threading.Timer(1.5, lambda: os._exit(0)).start()
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════ MAIN ════════════════════════════════════

if __name__ == '__main__':
    init_db()
    print('\n' + '═' * 50)
    print('  🏪  BoutikManager est démarré !')
    print('  🌐  Ouvrir : http://localhost:5000')
    print('═' * 50 + '\n')
    app.run(debug=False, host='127.0.0.1', port=5000)
