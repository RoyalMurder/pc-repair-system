DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS order_services CASCADE;
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
    device_type VARCHAR(60) NOT NULL,
    brand_model VARCHAR(120) NOT NULL,
    serial_number VARCHAR(80),
    cpu_spec VARCHAR(100),
    gpu_spec VARCHAR(100),
    ram_spec VARCHAR(50),
    storage_spec VARCHAR(100),
    issue_description TEXT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Принят',
    total_cost NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES repair_orders(id) ON DELETE CASCADE,
    recipient VARCHAR(120) NOT NULL,
    channel VARCHAR(30) NOT NULL DEFAULT 'SMS',
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, full_name, role, password_hash) VALUES
('admin', 'Пасечник Б.Е.', 'admin', '12345'),
('manager', 'Мурадов М.Р.', 'manager', '12345'),
('master', 'Шулбаев К.Е.', 'master', '12345'),
('client', 'Соколов Алексей', 'client', '12345');

INSERT INTO clients (user_id, full_name, phone, email) VALUES
(4, 'Соколов Алексей Викторович', '+7 (916) 450-12-89', 'sokolov.av@mail.ru'),
(NULL, 'Морозова Елена Сергеевна', '+7 (926) 811-34-56', 'morozova.elena@yandex.ru');

INSERT INTO masters (user_id, full_name, specialization, phone) VALUES
(3, 'Шулбаев К.Е. (Старший инженер)', 'Ремонт ноутбуков и пайка BGA', '+7 (999) 112-33-44'),
(NULL, 'Козлов Максим Денисович', 'Сборка ПК и диагностика комплектующих', '+7 (999) 245-67-89');

INSERT INTO services (title, base_price) VALUES
('Комплексная диагностика устройства', 800.00),
('Чистка системы охлаждения с заменой термопасты', 2200.00),
('Установка и настройка ОС Windows + драйверы', 1800.00),
('Замена матрицы ноутбука', 2500.00),
('Ремонт цепей питания платы', 4500.00),
('Восстановление данных с накопителя', 3500.00);

INSERT INTO repair_orders (client_id, master_id, device_type, brand_model, serial_number, cpu_spec, gpu_spec, ram_spec, storage_spec, issue_description, status, total_cost) VALUES
(1, 1, 'Ноутбук', 'ASUS TUF Gaming F15', 'SN-ASU8849201', 'Intel Core i7-12700H', 'NVIDIA GeForce RTX 3060', '16 ГБ DDR4', 'SSD 512 ГБ NVMe', 'Сильно греется под нагрузкой, выключается', 'В работе', 2200.00),
(2, 1, 'Ноутбук', 'Lenovo IdeaPad 5 Pro', 'SN-LEN1920442', 'AMD Ryzen 7 5800H', 'AMD Radeon Graphics', '16 ГБ LPDDR4X', 'SSD 1 ТБ', 'Синий экран после обновления системы', 'Готов к выдаче', 1800.00);
