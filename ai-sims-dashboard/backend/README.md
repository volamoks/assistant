# AI Sims Dashboard - Backend

FastAPI приложение с WebSocket поддержкой для AI Sims Dashboard.

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd /data/bot/ai-sims-dashboard/backend
pip install -r requirements.txt
```

### 2. Запуск сервера

```bash
# Вариант 1: Через Python
python app.py

# Вариант 2: Через Uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Проверка работы

После запуска доступны:

| Endpoint | Описание |
|----------|----------|
| `http://localhost:8000/` | Корневой endpoint |
| `http://localhost:8000/api/health` | Health check |
| `http://localhost:8000/api/agents` | Список агентов (мок) |
| `http://localhost:8000/docs` | Swagger документация |
| `ws://localhost:8000/ws` | WebSocket эхо-сервер |

## 📡 WebSocket Тест

### Через браузерную консоль:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    console.log('Received:', JSON.parse(event.data));
};

ws.send(JSON.stringify({ message: 'Hello AI Sims!' }));
```

### Через wscat:

```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws
# Вводите сообщения...
```

## 🏗 Структура проекта

```
backend/
├── app.py           # Main FastAPI приложение
├── requirements.txt # Python зависимости
└── README.md        # Этот файл
```

## 🔌 API Endpoints

### GET /api/health
Health check сервиса.

**Response:**
```json
{
  "status": "healthy",
  "service": "ai-sims-dashboard-backend",
  "version": "0.1.0"
}
```

### GET /api/agents
Получить список всех агентов.

**Response:**
```json
{
  "agents": [
    {
      "id": "agent_1",
      "name": "Assistant Alpha",
      "role": "primary_assistant",
      "status": "active",
      "last_seen": "2026-02-28T18:45:00Z",
      "tasks_completed": 42
    }
  ],
  "total": 3
}
```

### WebSocket /ws
Эхо-сервер для тестирования WebSocket соединения.

**Отправка:**
```json
{ "message": "test" }
```

**Получение:**
```json
{
  "type": "echo",
  "original": { "message": "test" },
  "timestamp": 1234567890.123
}
```

## 🔧 Переменные окружения

Пока не требуются. Для продакшен добавить:
- `HOST` - хост для запуска (по умолчанию 0.0.0.0)
- `PORT` - порт (по умолчанию 8000)
- `CORS_ORIGINS` - разрешённые источники для CORS

## 📦 Зависимости

- **FastAPI** - веб-фреймворк
- **Uvicorn** - ASGI сервер
- **WebSockets** - WebSocket поддержка
- **httpx** - HTTP клиент для интеграции с OpenClaw
- **Pydantic** - валидация данных

## 🐳 Запуск в Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t ai-sims-backend .
docker run -p 8000:8000 ai-sims-backend
```

## 📝 TODO

- [ ] Подключить реальный OpenClaw API
- [ ] Добавить аутентификацию
- [ ] Реализовать управление агентами
- [ ] Добавить базу данных
- [ ] Настроить логирование
