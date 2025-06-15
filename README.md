# Техническое задание: Event-Driven Интернет-Магазин (аналог ROZETKA, но  ODETKA)

## 1. Модуль: Товары (catalog-service)

### Назначение

Централизованное управление всеми товарами, их доступностью и данными.

### База данных

- **Товары (Products):**
    - ID
    - Название
    - Описание
    - Цена
    - Артикул (SKU)
    - Категория ID
    - Бренд ID
    - Рейтинг (вычисляемое поле)
    - Флаг "Активен"

- **Категории (Categories):**
    - ID
    - Название
    - Родительская категория ID (для иерархии)
    - Описание
    - Изображение

- **Бренды (Brands):**
    - ID
    - Название
    - Логотип
    - Описание

- **Характеристики (Specifications):**
    - ID
    - Название характеристики
    - Тип данных (текст, число, булев)

- **Характеристики_Товаров (Product_Specs):**
    - Товар ID
    - Характеристика ID
    - Значение

- **Остатки (Inventory):**
    - Товар ID
    - Склад ID (если несколько)
    - Количество
  > Примечание: Уровни остатков синхронизируются с событиями из order-service.

- **Медиа (Media):**
    - ID
    - Товар ID
    - Тип (изображение, видео)
    - URL
    - Порядок отображения

### API Методы (HTTP/REST)

- `GET /products`: Поиск/фильтрация (по названию, категории, бренду, цене, характеристикам), сортировка (цена, рейтинг,
  новизна), пагинация. Не возвращает неактивные или отсутствующие товары.
- `GET /products/{id}`: Получение полной карточки товара (включая характеристики, медиа, отзывы через вызов
  review-service).
- `POST /products`: Добавление нового товара (админ). Публикует событие product_created.
- `PUT /products/{id}`: Редактирование товара (админ). Публикует событие product_updated.
- `DELETE /products/{id}`: Деактивация товара (админ). Публикует событие product_deactivated. (Физическое удаление
  редко).
- `GET /categories`, `GET /brands`, `GET /specs`: Управление справочниками.

### События Kafka

#### Публикует:

- `product_created`: {product_id, name, category_id, price, sku}
- `product_updated`: {product_id, changes (object with updated fields)}
- `inventory_low`: {product_id, current_quantity} 
- `product_deactivated`: {product_id}
- `inventory_updated`: {product_id, new_quantity} (Генерируется при резерве/освобождении склада)

#### Подписывается/Обрабатывает:

- `order_created` (от order-service): Резервирует товары на складе, обновляет остатки, публикует inventory_updated.
- `order_cancelled` (от order-service): Возвращает товары на склад, обновляет остатки, публикует inventory_updated.
- `review_rating_updated` (от review-service): Обновляет рейтинг товара на основе среднего.

## 2. Модуль: Корзина (cart-service)

### Назначение

Управление временными корзинами пользователей, расчет стоимости.

### База данных

- **Корзины (Carts):**
    - ID (сессия или user_id)
    - Дата создания
    - Дата последнего обновления

- **Позиции_Корзины (Cart_Items):**
    - Корзина ID
    - Товар ID
    - Количество
    - Цена на момент добавления (фиксируется)

### API Методы (HTTP/REST)

- `GET /cart`: Получение текущей корзины пользователя (по сессии или user_id)
- `POST /cart/items`: Добавление товара в корзину. Проверяет доступность через catalog-service (синхронно). Публикует
  item_added_to_cart.
- `PUT /cart/items/{product_id}`: Изменение количества товара в корзине.
- `DELETE /cart/items/{product_id}`: Удаление товара из корзины.
- `POST /cart/checkout`: Инициирует оформление заказа. Передает данные в order-service, очищает корзину после успеха.

### События Kafka

#### Публикует:

- `item_added_to_cart`: {user_id/session_id, product_id, quantity, price_at_add}
- `cart_updated`: {user_id/session_id, changes (added/removed items)} (Опционально, для аналитики)
- `cart_checkout_initiated`: {user_id/session_id, cart_contents (list of items)}

#### Подписывается/Обрабатывает:

- `product_updated` (от catalog-service): Обновляет цену в активных корзинах, если товар еще там. Уведомляет
  пользователя через notification-service (если цена упала/выросла значительно).
- `product_deactivated` // Для удаления товаров
- `inventory_updated` // Проверка доступности

## 3. Модуль: Заказы (order-service)

### Назначение

Оформление, оплата, отслеживание и управление жизненным циклом заказов.

### База данных

- **Заказы (Orders):**
    - ID
    - Пользователь ID
    - Статус (created, awaiting_payment, paid, processing, shipped, delivered, cancelled)
    - Дата создания
    - Общая сумма
    - Адрес доставки
    - Способ оплаты
    - Трек-номер

- **Позиции_Заказа (Order_Items):**
    - Заказ ID
    - Товар ID
    - Количество
    - Цена покупки (фиксируется)
    - Название товара на момент покупки (фиксируется)

- **Платежи (Payments):**
    - ID
    - Заказ ID
    - Сумма
    - Статус (pending, succeeded, failed)
    - Дата/время
    - ID транзакции (внешней системы)

### API Методы (HTTP/REST)

- `POST /orders`: Создание заказа из корзины (принимает данные из cart_checkout_initiated). Резервирует товары через
  catalog-service (синхронно). Публикует order_created.
- `GET /orders/{id}`: Получение информации о заказе (для пользователя и админа).
- `POST /orders/{id}/pay`: Инициирует процесс оплаты (интеграция с платежным шлюзом). При успехе меняет статус на paid,
  публикует order_paid.
- `PUT /orders/{id}/status` (админ): Обновление статуса заказа (например, shipped, delivered, cancelled). Публикует
  order_status_updated.

### События Kafka

#### Публикует:

- `order_created`: {order_id, user_id, items: [{product_id, quantity, price}], total_amount}
- `order_paid`: {order_id}
- `order_status_updated`: {order_id, new_status}
- `order_cancelled`: {order_id, reason} (Генерируется при PUT статуса cancelled)

#### Подписывается/Обрабатывает:

- `cart_checkout_initiated` (от cart-service): Запускает процесс создания заказа.
- `payment_succeeded` (от внешней платежной системы через webhook): Обновляет статус заказа на paid, публикует
  order_paid.
- `payment_failed` (от внешней платежной системы): Обновляет статус заказа, уведомляет пользователя через
  notification-service.
- `inventory_low` (от catalog-service): Может влиять на отображение доступности при создании заказа.

## 4. Модуль: Пользователи (user-service)

### Назначение

Управление учетными записями, аутентификация, авторизация, профили.

### База данных

- **Пользователи (Users):**
    - ID
    - Email (логин)
    - Хэш пароля
    - Имя
    - Фамилия
    - Телефон
    - Роль (customer, admin)
    - Дата регистрации
    - Флаг "Активен"

- **Адреса (Addresses):**
    - ID
    - Пользователь ID
    - Тип (shipping, billing)
    - Адрес (страна, город, улица, дом, квартира, индекс)

- **Сессии (Sessions):**
    - ID (токен)
    - Пользователь ID
    - Дата создания
    - Дата истечения

### API Методы (HTTP/REST - Auth)

- `POST /register`: Регистрация. Проверка уникальности email. Публикует user_registered.
- `POST /login`: Аутентификация. Возвращает токен сессии.
- `POST /logout`: Инвалидация сессии.
- `GET /profile`: Получение профиля пользователя (аутентиф.).
- `PUT /profile`: Обновление профиля (аутентиф.). Публикует profile_updated.
- `GET /addresses`, `POST /addresses`, `PUT /addresses/{id}`, `DELETE /addresses/{id}`: Управление адресами.
- (Админ) `GET /users`, `PUT /users/{id}/status`: Управление пользователями.

### События Kafka

#### Публикует:

- `user_registered`: {user_id, email, name}
- `user_logged_in`: {user_id} (Опционально, для аналитики)
- `profile_updated`: {user_id, changes (email, name, phone?)}
- `address_updated`: {user_id, address_id, type}

#### Подписывается/Обрабатывает:

В основном источник событий для других сервисов. Сам подписывается редко (например, на order_placed для обновления
истории заказов в профиле).

## 5. Модуль: Уведомления (notification-service)

### Назначение

Отправка уведомлений пользователям по различным каналам (email, SMS, push) на основе событий.

### База данных (Для очереди/истории/шаблонов)

- **Шаблоны (Templates):**
    - ID
    - Тип (email_welcome, sms_order_placed, push_cart_reminder)
    - Канал
    - Тема
    - Текст (с плейсхолдерами)

- **Очередь_Уведомлений (Notifications_Queue):**
    - ID
    - Пользователь ID
    - Шаблон ID
    - Данные (JSON для плейсхолдеров)
    - Статус (pending, sent, failed)
    - Канал
    - Дата создания
    - Попытки

- **История_Уведомлений (Notifications_Log):**
    - (Архив из Очереди после отправки/окончания попыток)

### API Методы

Минимум. В основном внутренний. Возможен `POST /notify` для принудительной отправки (админ).

### События Kafka

#### Публикует:

Нет (или notification_failed для алертинга админов).

#### Подписывается/Обрабатывает (ОСНОВНОЕ!):

- `user_registered` (от user-service): Отправляет приветственное письмо/пуш (email подтверждения).
- `item_added_to_cart` (от cart-service): Отправляет напоминание о корзине через N часов/дней (если заказ не оформлен).
- `order_created` (от order-service): Отправляет письмо "Заказ №X создан, ожидает оплаты".
- `order_paid` (от order-service): Отправляет письмо "Заказ №X оплачен".
- `order_status_updated` (от order-service): Отправляет уведомление при смене статуса (shipped -> трек-номер,
  delivered -> спасибо).
- `review_submitted` (от review-service): Отправляет благодарность за отзыв или уведомление модератору (если нужна
  премодерация).
- `payment_failed` (от order-service): Уведомляет пользователя о проблеме с оплатой.

## 6. Модуль: Отзывы (review-service)

### Назначение

Управление отзывами и рейтингами о товарах, модерация.

### База данных

- **Отзывы (Reviews):**
    - ID
    - Товар ID
    - Пользователь ID
    - Рейтинг (1-5)
    - Текст отзыва
    - Дата
    - Статус (pending, approved, rejected)

- **Рейтинги (Ratings_Agg):**
    - Товар ID
    - Кол-во отзывов
    - Средний рейтинг
  > Вычисляется триггером или джобой

### API Методы (HTTP/REST)

- `POST /reviews`: Добавление отзыва. Проверяет, что пользователь делал заказ этого товара (синхронный вызов к
  order-service). Публикует review_submitted.
- `GET /reviews/product/{product_id}`: Получение одобренных отзывов по товару (с пагинацией).
- (Админ) `GET /reviews/pending`, `PUT /reviews/{id}/status`: Модерация отзывов (approve/reject). При approve публикует
  review_approved и пересчитывает рейтинг.

### События Kafka

#### Публикует:

- `review_submitted`: {review_id, product_id, user_id, rating, text} (Статус pending)
- `review_approved`: {review_id, product_id, user_id, rating, text}
- `review_rejected`: {review_id, reason}
- `review_rating_updated`: {product_id, new_avg_rating, new_review_count}

#### Подписывается/Обрабатывает:

- `order_delivered` (от order-service): Может использоваться для разрешения оставления отзыва (если политика "только
  купившие").
- `product_deactivated` (от catalog-service): Прекращает прием отзывов на товар.

## Общие требования по архитектуре

### Связь

Все взаимодействия между микросервисами — только через события Kafka (асинхронно). Синхронные вызовы допустимы только
между Frontend/API Gateway и сервисом, или для критически важных проверок при обработке запроса (например, проверка
наличия товара при добавлении в корзину).

### Базы данных

Каждый сервис имеет свою независимую БД (SQL или NoSQL, оптимальную для его задач). Прямой доступ к БД одного сервиса из
другого запрещен.

### События Kafka

- **Формат:** JSON или Avro (с Schema Registry)
- **Обязательные поля в каждом событии:**
    - event_id (UUID)
    - event_type
    - event_timestamp
    - producer_service
    - payload (основные данные)
- **Стратегия доставки:** "At Least Once" (минимум однократная доставка)

### Resilience

Сервисы должны быть идемпотентными при обработке событий (на случай повторной доставки). Использовать механизмы
повтора (retry) и запасных очередей (DLQ - Dead Letter Queue) для неудачно обработанных событий.

### Наблюдаемость

Централизованный сбор логов (ELK/Grafana Loki), метрик (Prometheus/Grafana), трейсинга (Jaeger/Zipkin).