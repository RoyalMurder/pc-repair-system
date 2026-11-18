from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
from datetime import datetime

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
            # Запоминаем куда хотел попасть пользователь
            session['next_url'] = request.url
            flash('Для оформления заявки необходимо войти в систему или зарегистрироваться.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') not in roles:
                flash('У вас нет доступа к этой странице.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function  # <--- Была опечатка на этой строке
    return decorator

@app.context_processor
def inject_globals():
    if 'user_id' not in session:
        return {'unread_count': 0}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if session.get('role') == 'client':
            # Для клиента считаем уведомления по его заявкам, если бы они были привязаны к user_id, 
            # но пока просто возвращаем 0, так как notifications привязаны к строке recipient.
             cur.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE recipient LIKE %s AND is_read = FALSE", (f"%{session.get('full_name')}%",))
        else:
             cur.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE is_read = FALSE")
        cnt = cur.fetchone()['cnt']
        cur.close()
        conn.close()
        return {'unread_count': cnt}
    except Exception:
        return {'unread_count': 0}

@app.route('/')
def index():
    # Главная страница (Landing page) - доступна всем
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

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
                
                next_url = session.pop('next_url', None)
                if next_url:
                    return redirect(next_url)
                return redirect(url_for('dashboard'))
            else:
                flash('Неверный логин или пароль', 'danger')

        elif action == 'register':
            username = request.form.get('reg_username', '').strip()
            full_name = request.form.get('reg_fullname', '').strip()
            phone = request.form.get('reg_phone', '').strip()
            password = request.form.get('reg_password', '').strip()

            if not username or not full_name or not password or not phone:
                flash('Заполните все обязательные поля для регистрации', 'warning')
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
                "INSERT INTO clients (user_id, full_name, phone) VALUES (%s, %s, %s)",
                (new_user_id, full_name, phone)
            )
            conn.commit()
            cur.close()
            conn.close()

            session['user_id'] = new_user_id
            session['username'] = username
            session['full_name'] = full_name
            session['role'] = 'client'
            
            next_url = session.pop('next_url', None)
            if next_url:
                 return redirect(next_url)
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    role = session.get('role')
    user_id = session.get('user_id')

    if role == 'client':
        cur.execute("SELECT id FROM clients WHERE user_id = %s", (user_id,))
        client_rec = cur.fetchone()
        client_id = client_rec['id'] if client_rec else 0
        
        cur.execute('''
            SELECT r.*, c.full_name AS client_name, m.full_name AS master_name
            FROM repair_orders r
            JOIN clients c ON r.client_id = c.id
            LEFT JOIN masters m ON r.master_id = m.id
            WHERE r.client_id = %s
            ORDER BY r.created_at DESC
        ''', (client_id,))
        orders = cur.fetchall()
        
        cur.close()
        conn.close()
        return render_template('dashboard_client.html', orders=orders)
        
    elif role == 'master':
        cur.execute("SELECT id FROM masters WHERE user_id = %s", (user_id,))
        master_rec = cur.fetchone()
        master_id = master_rec['id'] if master_rec else 0
        
        # Мастер видит только назначенные ему заявки
        cur.execute('''
            SELECT r.*, c.full_name AS client_name, c.phone AS client_phone
            FROM repair_orders r
            JOIN clients c ON r.client_id = c.id
            WHERE r.master_id = %s
            ORDER BY r.created_at DESC
        ''', (master_id,))
        orders = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('dashboard_master.html', orders=orders)

    else: # admin, manager
        # Менеджер видит все заявки
        cur.execute('''
            SELECT r.*, c.full_name AS client_name, c.phone AS client_phone,
                   m.full_name AS master_name, m.id as m_id
            FROM repair_orders r
            JOIN clients c ON r.client_id = c.id
            LEFT JOIN masters m ON r.master_id = m.id
            ORDER BY r.created_at DESC
        ''')
        orders = cur.fetchall()
        
        cur.execute("SELECT * FROM masters WHERE is_active = TRUE")
        masters = cur.fetchall()

        cur.execute("SELECT COUNT(*) AS total FROM repair_orders")
        total_orders = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) AS new_orders FROM repair_orders WHERE status = 'Новая заявка'")
        new_orders = cur.fetchone()['new_orders']

        cur.execute("SELECT COUNT(*) AS in_work FROM repair_orders WHERE status IN ('В работе', 'Диагностика')")
        active_orders = cur.fetchone()['in_work']

        cur.close()
        conn.close()

        stats = {
            'total': total_orders,
            'new': new_orders,
            'active': active_orders
        }
        return render_template('dashboard_manager.html', orders=orders, stats=stats, masters=masters)


@app.route('/order/new/<request_type>', methods=['GET', 'POST'])
@login_required
def new_order(request_type):
    # request_type может быть 'diagnostic' или 'repair'
    req_type_ru = 'Диагностика' if request_type == 'diagnostic' else 'Ремонт'
    
    if request.method == 'POST':
        user_id = session.get('user_id')
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Получаем ID клиента
        cur.execute("SELECT id FROM clients WHERE user_id = %s", (user_id,))
        client_rec = cur.fetchone()
        
        if not client_rec:
            # Если клиент как-то попал сюда без записи в clients
             cur.execute("INSERT INTO clients (user_id, full_name, phone) VALUES (%s, %s, %s) RETURNING id",
                            (user_id, session.get('full_name'), '+7 (000) 000-00-00'))
             client_id = cur.fetchone()['id']
        else:
             client_id = client_rec['id']

        device_type = request.form.get('device_type')
        brand_model = request.form.get('brand_model', '').strip()
        issue_description = request.form.get('issue_description', '').strip()
        
        # Заявка по умолчанию "Новая заявка", без мастера, без цены
        cur.execute('''
            INSERT INTO repair_orders
            (client_id, request_type, device_type, brand_model, issue_description, status)
            VALUES (%s, %s, %s, %s, %s, 'Новая заявка') RETURNING id
        ''', (client_id, req_type_ru, device_type, brand_model, issue_description))
        
        order_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        
        flash(f'Заявка #{order_id} на {req_type_ru.lower()} успешно отправлена! Менеджер скоро свяжется с вами.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('new_order.html', request_type=req_type_ru)

# --- Действия Менеджера ---
@app.route('/api/order/<int:order_id>/assign', methods=['POST'])
@role_required('admin', 'manager')
def assign_master(order_id):
    data = request.get_json()
    master_id = data.get('master_id')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE repair_orders SET master_id = %s, status = 'Назначен мастер' WHERE id = %s", (master_id, order_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

# --- Действия Мастера ---
@app.route('/api/order/<int:order_id>/master_update', methods=['POST'])
@role_required('master')
def update_by_master(order_id):
    data = request.get_json()
    status = data.get('status')
    comment = data.get('comment')
    cost = data.get('cost')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Проверка, что заказ принадлежит этому мастеру
    cur.execute("SELECT id FROM masters WHERE user_id = %s", (session.get('user_id'),))
    master_rec = cur.fetchone()
    if not master_rec:
         return jsonify({'success': False, 'error': 'Мастер не найден'}), 403
         
    cur.execute("SELECT master_id FROM repair_orders WHERE id = %s", (order_id,))
    order_rec = cur.fetchone()
    if order_rec['master_id'] != master_rec['id']:
        return jsonify({'success': False, 'error': 'Это не ваша заявка'}), 403

    cur.execute('''
        UPDATE repair_orders 
        SET status = %s, master_comment = %s, estimated_cost = %s
        WHERE id = %s
    ''', (status, comment, cost, order_id))
    
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
