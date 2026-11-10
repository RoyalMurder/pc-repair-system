from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

def get_db_connection():
    return psycopg2.connect(
        host=app.config['DB_HOST'],
        port=app.config['DB_PORT'],
        dbname=app.config['DB_NAME'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        cursor_factory=RealDictCursor
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    if 'user_id' not in session:
        return {'unread_count': 0}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
    "INSERT INTO users (username, full_name, role, password_hash) VALUES (%s, %s, 'client', %s) RETURNING id",
    (username, full_name, password)
)
        cnt = cur.fetchone()['cnt']
        cur.close()
        conn.close()
        return {'unread_count': cnt}
    except Exception:
        return {'unread_count': 0}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'login':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = %s AND password_hash = %s", (username, password))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['full_name'] = user['full_name']
                session['role'] = user['role']
                flash(f'Добро пожаловать, {user["full_name"]}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверный логин или пароль', 'danger')

        elif action == 'register':
            username = request.form.get('reg_username', '').strip()
            full_name = request.form.get('reg_fullname', '').strip()
            phone = request.form.get('reg_phone', '').strip()
            password = request.form.get('reg_password', '').strip()
            password_confirm = request.form.get('reg_password_confirm', '').strip()

            if not username or not full_name or not password or not phone:
                flash('Заполните все обязательные поля для регистрации', 'warning')
                return redirect(url_for('login'))

            if password != password_confirm:
                flash('Пароли не совпадают', 'danger')
                return redirect(url_for('login'))

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                flash('Пользователь с таким логином уже существует', 'warning')
                cur.close()
                conn.close()
                return redirect(url_for('login'))

            cur.execute(
                "INSERT INTO users (username, full_name, role, password_hash) VALUES (%s, %s, 'client', %s) RETURNING id",
                (username, full_name, password)
            )
            new_user_id = cur.fetchone()['id']

            cur.execute(
                "INSERT INTO clients (user_id, full_name, phone, email) VALUES (%s, %s, %s, %s)",
                (new_user_id, full_name, phone, f"{username}@techservice.local")
            )
            conn.commit()
            cur.close()
            conn.close()

            session['user_id'] = new_user_id
            session['username'] = username
            session['full_name'] = full_name
            session['role'] = 'client'
            flash('Регистрация прошла успешно! Добро пожаловать.', 'success')
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor()

    role = session.get('role')
    user_id = session.get('user_id')

    if role == 'client':
        cur.execute("SELECT id FROM clients WHERE user_id = %s", (user_id,))
        client_rec = cur.fetchone()
        client_id = client_rec['id'] if client_rec else 0
        
        cur.execute('''
            SELECT r.*, c.full_name AS client_name, c.phone AS client_phone,
                   m.full_name AS master_name
            FROM repair_orders r
            JOIN clients c ON r.client_id = c.id
            LEFT JOIN masters m ON r.master_id = m.id
            WHERE r.client_id = %s
            ORDER BY r.created_at DESC
        ''', (client_id,))
    else:
        cur.execute('''
            SELECT r.*, c.full_name AS client_name, c.phone AS client_phone,
                   m.full_name AS master_name
            FROM repair_orders r
            JOIN clients c ON r.client_id = c.id
            LEFT JOIN masters m ON r.master_id = m.id
            ORDER BY r.created_at DESC
        ''')
    orders = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS total FROM repair_orders")
    total_orders = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS in_work FROM repair_orders WHERE status IN ('В работе', 'Диагностика')")
    active_orders = cur.fetchone()['in_work']

    cur.execute("SELECT COUNT(*) AS ready FROM repair_orders WHERE status = 'Готов к выдаче'")
    ready_orders = cur.fetchone()['ready']

    cur.execute("SELECT COALESCE(SUM(total_cost), 0) AS revenue FROM repair_orders WHERE status IN ('Готов к выдаче', 'Выдан')")
    revenue = cur.fetchone()['revenue']

    cur.close()
    conn.close()

    stats = {
        'total': total_orders,
        'active': active_orders,
        'ready': ready_orders,
        'revenue': revenue
    }
    return render_template('index.html', orders=orders, stats=stats)

@app.route('/order/new', methods=['GET', 'POST'])
@login_required
def new_order():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        role = session.get('role')
        user_id = session.get('user_id')

        if role == 'client':
            cur.execute("SELECT id, full_name, phone FROM clients WHERE user_id = %s", (user_id,))
            client_rec = cur.fetchone()
            if client_rec:
                client_id = client_rec['id']
                recipient_info = f"{client_rec['full_name']} ({client_rec['phone']})"
            else:
                cur.execute("INSERT INTO clients (user_id, full_name, phone) VALUES (%s, %s, %s) RETURNING id, full_name, phone",
                            (user_id, session.get('full_name'), '+7 (900) 000-00-00'))
                client_rec = cur.fetchone()
                client_id = client_rec['id']
                recipient_info = f"{client_rec['full_name']} ({client_rec['phone']})"
        else:
            client_id = request.form.get('client_id')
            cur.execute("SELECT full_name, phone FROM clients WHERE id = %s", (client_id,))
            client_row = cur.fetchone()
            recipient_info = f"{client_row['full_name']} ({client_row['phone']})"

        master_id = request.form.get('master_id') or None
        device_type = request.form.get('device_type')
        brand_model = request.form.get('brand_model', '').strip()
        serial_number = request.form.get('serial_number', '').strip() or 'Б/Н'
        
        cpu_spec = request.form.get('cpu_spec', '').strip()
        gpu_spec = request.form.get('gpu_spec', '').strip()
        ram_spec = request.form.get('ram_spec', '').strip()
        storage_spec = request.form.get('storage_spec', '').strip()
        
        issue_description = request.form.get('issue_description', '').strip()
        total_cost = request.form.get('total_cost') or 0

        cur.execute('''
            INSERT INTO repair_orders
            (client_id, master_id, device_type, brand_model, serial_number, cpu_spec, gpu_spec, ram_spec, storage_spec, issue_description, status, total_cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Принят', %s) RETURNING id
        ''', (client_id, master_id, device_type, brand_model, serial_number, cpu_spec, gpu_spec, ram_spec, storage_spec, issue_description, total_cost))
        order_id = cur.fetchone()['id']

        notif_msg = f"Заявка #{order_id} ({brand_model}) зарегистрирована в системе."
        cur.execute('''
            INSERT INTO notifications (order_id, recipient, channel, message)
            VALUES (%s, %s, 'SMS', %s)
        ''', (order_id, recipient_info, notif_msg))

        conn.commit()
        cur.close()
        conn.close()
        flash('Заявка успешно оформлена!', 'success')
        return redirect(url_for('index'))

    cur.execute("SELECT * FROM clients ORDER BY full_name")
    clients = cur.fetchall()

    cur.execute("SELECT * FROM masters WHERE is_active = TRUE ORDER BY full_name")
    masters = cur.fetchall()

    cur.execute("SELECT * FROM services ORDER BY title")
    services = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('new_order.html', clients=clients, masters=masters, services=services)

@app.route('/api/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')
    allowed_statuses = ['Принят', 'Диагностика', 'В работе', 'Готов к выдаче', 'Выдан']

    if new_status not in allowed_statuses:
        return jsonify({'success': False, 'error': 'Некорректный статус'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE repair_orders SET status = %s WHERE id = %s", (new_status, order_id))

    cur.execute('''
        SELECT r.brand_model, c.full_name, c.phone
        FROM repair_orders r
        JOIN clients c ON r.client_id = c.id
        WHERE r.id = %s
    ''', (order_id,))
    order_info = cur.fetchone()

    if order_info:
        recipient = f"{order_info['full_name']} ({order_info['phone']})"
        msg = f"Статус заказа #{order_id} ({order_info['brand_model']}) изменен на «{new_status}»."
        cur.execute('''
            INSERT INTO notifications (order_id, recipient, channel, message)
            VALUES (%s, %s, 'SMS', %s)
        ''', (order_id, recipient, msg))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'status': new_status})

@app.route('/order/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order(order_id):
    if session.get('role') not in ['admin', 'manager']:
        flash('Недостаточно прав для удаления заявки', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM repair_orders WHERE id = %s", (order_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Заявка удалена', 'secondary')
    return redirect(url_for('index'))

@app.route('/clients', methods=['GET', 'POST'])
@login_required
def clients_list():
    if session.get('role') not in ['admin', 'manager']:
        flash('Доступ ограничен', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        if full_name and phone:
            cur.execute(
                "INSERT INTO clients (full_name, phone, email) VALUES (%s, %s, %s)",
                (full_name, phone, email)
            )
            conn.commit()
            flash('Клиент добавлен', 'success')
        return redirect(url_for('clients_list'))

    cur.execute('''
        SELECT c.*, COUNT(r.id) AS orders_count
        FROM clients c
        LEFT JOIN repair_orders r ON c.id = r.client_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    ''')
    clients = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('clients.html', clients=clients)

@app.route('/masters', methods=['GET', 'POST'])
@login_required
def masters_list():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST' and session.get('role') == 'admin':
        full_name = request.form.get('full_name', '').strip()
        specialization = request.form.get('specialization', '').strip()
        phone = request.form.get('phone', '').strip()
        if full_name and specialization:
            cur.execute(
                "INSERT INTO masters (full_name, specialization, phone) VALUES (%s, %s, %s)",
                (full_name, specialization, phone)
            )
            conn.commit()
            flash('Мастер добавлен', 'success')
        return redirect(url_for('masters_list'))

    cur.execute('''
        SELECT m.*, COUNT(r.id) AS active_orders
        FROM masters m
        LEFT JOIN repair_orders r ON m.id = r.master_id AND r.status IN ('Принят', 'Диагностика', 'В работе')
        GROUP BY m.id
        ORDER BY m.id
    ''')
    masters = cur.fetchall()

    cur.execute("SELECT * FROM services ORDER BY id")
    services = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('masters.html', masters=masters, services=services)

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if session.get('role') != 'admin':
        flash('Доступ только для администратора', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_user':
            username = request.form.get('username', '').strip()
            full_name = request.form.get('full_name', '').strip()
            role = request.form.get('role', 'client')
            password = request.form.get('password', '').strip()
            if username and full_name and password:
                cur.execute(
                    "INSERT INTO users (username, full_name, role, password_hash) VALUES (%s, %s, %s, %s)",
                    (username, full_name, role, password)
                )
                conn.commit()
                flash('Пользователь добавлен', 'success')
        elif action == 'delete_user':
            user_id = request.form.get('user_id')
            if int(user_id) != session.get('user_id'):
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                flash('Пользователь удален', 'secondary')
        return redirect(url_for('admin_users'))

    cur.execute("SELECT * FROM users ORDER BY id")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/notifications')
@login_required
def notifications_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notifications ORDER BY created_at DESC")
    notifications = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/read_all', methods=['POST'])
@login_required
def mark_notifications_read():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET is_read = TRUE WHERE is_read = FALSE")
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('notifications_list'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
