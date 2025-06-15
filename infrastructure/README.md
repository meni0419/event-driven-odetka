
## 🚀 **Команды для запуска:**

```bash
# 1. Инфраструктура (один раз)
cd infrastructure
docker-compose up -d

# 2. Ваши сервисы
cd ../cart-service
docker-compose up -d

cd ../order-service  
docker-compose up -d

# 3. Проверка
curl http://localhost:8001/health
curl http://localhost:8002/health
```

**Этот подход позволит каждому работать независимо, но использовать общую инфраструктуру! Попробуем?** 🎯