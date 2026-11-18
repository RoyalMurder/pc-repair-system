DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS repair_orders CASCADE;
DROP TABLE IF EXISTS services CASCADE;
DROP TABLE IF EXISTS masters CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(60) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role VARCHAR(40) NOT NULL DEFAULT 'client',
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(25) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE masters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    full_name VARCHAR(120) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    phone VARCHAR(25) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    base_price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE repair_orders (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    master_id INTEGER REFERENCES masters(id) ON DELETE SET NULL,
    request_type VARCHAR(50) NOT NULL DEFAULT 'Ремонт', 
    device_type VARCHAR(60) NOT NULL,
    brand_model VARCHAR(120) NOT NULL,
    issue_description TEXT NOT NULL,
    master_comment TEXT, 
    status VARCHAR(40) NOT NULL DEFAULT 'Новая заявка',
    estimated_cost NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES repair_orders(id) ON DELETE CASCADE,
    recipient VARCHAR(120) NOT NULL,
    channel VARCHAR(30) NOT NULL DEFAULT 'System',
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, full_name, role, password_hash) VALUES
('admin', 'Администратор Системы', 'admin', '12345'),
('manager', 'Менеджер Приемки', 'manager', '12345'),
('master', 'Старший Инженер', 'master', '12345'),
('client', 'Тестовый Клиент', 'client', '12345');

INSERT INTO clients (user_id, full_name, phone, email) VALUES
(4, 'Тестовый Клиент', '+7 (999) 000-00-00', 'client@test.ru');

INSERT INTO masters (user_id, full_name, specialization, phone) VALUES
(3, 'Старший Инженер', 'Ремонт и пайка', '+7 (999) 111-22-33');

INSERT INTO services (title, base_price) VALUES
('Комплексная диагностика', 800.00),
('Чистка от пыли и замена термопасты', 2000.00),
('Установка ОС и драйверов', 1500.00);
