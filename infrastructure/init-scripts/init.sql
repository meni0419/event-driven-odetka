-- Создаем схемы для каждого сервиса
CREATE SCHEMA IF NOT EXISTS cart_service;
CREATE SCHEMA IF NOT EXISTS order_service;
CREATE SCHEMA IF NOT EXISTS auth_service;
CREATE SCHEMA IF NOT EXISTS catalog_service;

-- Создаем пользователей для каждого сервиса (по желанию)
-- CREATE USER cart_user WITH PASSWORD 'cart_pass';
-- GRANT ALL PRIVILEGES ON SCHEMA cart_service TO cart_user;