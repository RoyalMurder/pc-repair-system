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
    role VARCHAR(40) NOT NULL DEFAULT 'Менеджер',
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(25) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE masters (
    id SERIAL PRIMARY KEY,
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
    issue_description TEXT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Принят',
    total_cost NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_services (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES repair_orders(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES repair_orders(id) ON DELETE CASCADE,
    recipient VARCHAR(120) NOT NULL,
    channel VARCHAR(30) NOT NULL DEFAULT 'SMS / Email',
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, full_name, role, password_hash) VALUES
('admin', 'Пасечник Б.Е.', 'Администратор', '12345'),
('manager', 'Мурадов М.Р.', 'Менеджер приемки', '12345'),
('engineer', 'Шулбаев К.Е.', 'Старший инженер', '12345');

INSERT INTO clients (full_name, phone, email) VALUES
('Соколов Алексей Викторович', '+7 (916) 450-12-89', 'sokolov.av@mail.ru'),
('Морозова Елена Сергеевна', '+7 (926) 811-34-56', 'morozova.elena@yandex.ru'),
('Кузнецов Дмитрий Игоревич', '+7 (903) 229-78-10', 'd.kuznetsov@gmail.com'),
('Волкова Анна Павловна', '+7 (915) 604-55-21', 'volkova.ap@mail.ru');

INSERT INTO masters (full_name, specialization, phone) VALUES
('Смирнов Артем Олегович', 'Ремонт ноутбуков и пайка BGA', '+7 (999) 112-33-44'),
('Козлов Максим Денисович', 'Сборка ПК и диагностика комплектующих', '+7 (999) 245-67-89'),
('Новиков Илья Андреевич', 'Восстановление данных и настройка ОС', '+7 (999) 533-90-12');

INSERT INTO services (title, base_price) VALUES
('Комплексная диагностика устройства', 800.00),
('Чистка системы охлаждения с заменой термопасты', 2200.00),
('Установка и настройка ОС Windows + драйверы', 1800.00),
('Замена матрицы ноутбука (без учета детали)', 2500.00),
('Ремонт цепей питания материнской платы', 4500.00),
('Восстановление данных с накопителя', 3500.00);

INSERT INTO repair_orders (client_id, master_id, device_type, brand_model, serial_number, issue_description, status, total_cost) VALUES
(1, 1, 'Ноутбук', 'ASUS TUF Gaming F15', 'SN-ASU8849201', 'Сильно греется под нагрузкой, выключается через 15 минут игры', 'В работе', 2200.00),
(2, 3, 'Ноутбук', 'Lenovo IdeaPad 5 Pro', 'SN-LEN1920442', 'Не загружается система после обновления, синий экран', 'Готов к выдаче', 1800.00),
(3, 2, 'Системный блок', 'Кастомная сборка i5-12400F / RTX 3060', 'Б/Н', 'Нет изображения на мониторе при включении, вентиляторы крутятся', 'Диагностика', 800.00),
(4, 1, 'Моноблок', 'HP Pavilion 24', 'SN-HP4491023', 'Разъем питания расшатан, зарядка идет только под углом', 'Принят', 4500.00);

INSERT INTO notifications (order_id, recipient, channel, message, is_read) VALUES
(2, 'Морозова Е.С. (+7 (926) 811-34-56)', 'SMS', 'Ваш заказ #2 (Lenovo IdeaPad 5 Pro) переведен в статус «Готов к выдаче». К оплате: 1800 руб.', FALSE),
(1, 'Соколов А.В. (sokolov.av@mail.ru)', 'Email', 'Заказ #1 (ASUS TUF Gaming F15) передан в работу мастеру Смирнову А.О.', TRUE),
(4, 'Волкова А.П. (+7 (915) 604-55-21)', 'SMS', 'Заявка #4 принята в сервисный центр ТехСервис. Ожидайте результатов диагностики.', FALSE);
