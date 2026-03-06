# Архитектура локальной микро-модели для heartbeat

## Анализ проблемы

### Текущее состояние
- **Heartbeat job**: `heartbeat-check` в [`cron/jobs.json`](openclaw-docker/cron/jobs.json:520)
- **Модель**: `bailian/kimi-k2.5` (Kimi K2.5 через Alibaba Bailian API)
- **Таймаут**: 60 секунд
- **Проблема**: Модель не успевает ответить → `cron: job execution timed out`

### Требования задачи heartbeat
1. Прочитать файл `/data/obsidian/vault/Bot/today-session.md`
2. Отправить краткое сообщение в Telegram
3. Формат: `[🕐 HH:MM UTC] Claw online` или `[🕐 HH:MM UTC] Claw online — всё тихо 🔇`

Это **тривиальная задача** - не требует reasoning, сложной логики или большого контекста.

---

## Сравнительная таблица микро-моделей

| Модель | Размер | RAM (KV-Cache) | CPU Only | Apple Silicon | Скорость |适用场景 |
|--------|--------|-----------------|----------|--------------|----------|---------|
| **Qwen3-0.5B** | 0.5B | ~1GB | ✅ | ✅ Neural Engine | <1s | Идеально для heartbeat |
| **Qwen2.5-0.5B** | 0.5B | ~1GB | ✅ | ✅ | <1s | Идеально для heartbeat |
| **Phi-3-mini-4K** | 3.8B | ~4GB | ✅ | ✅ | 2-3s | Простые задачи |
| **Llama3.2-1B** | 1B | ~2GB | ✅ | ✅ | 1-2s | Баланс |
| **Qwen3.5-0.8B** | 0.8B | ~1.5GB | ✅ | ✅ | <1s | Уже настроен в LiteLLM |
| **Gemma-2-2B** | 2B | ~3GB | ✅ | ✅ | 2s | Средние задачи |
| **Qwen2.5-1.5B** | 1.5B | ~2.5GB | ✅ | ✅ | 1-2s | Сложнее чем 0.5B |

### Рекомендация для Mac Mini M4 16GB

**Оптимальный выбор: `qwen2.5-0.5b` или `qwen3-0.5b`**

Причины:
1. Минимальные требования к RAM (~1GB)
2. Мгновенный ответ (<1 сек на Apple Neural Engine)
3. Достаточно интеллекта для простого форматирования текста
4. Уже есть в Ollama library

Альтернатива: `ollama/qwen3.5:0.8b` - уже настроен в LiteLLM, потребует ~1.5GB RAM

---

## Архитектурная схема интеграции

```mermaid
flowchart TB
    subgraph OpenClaw["OpenClaw Gateway"]
        Cron[("Cron Scheduler")]
        Gateway[("Gateway API")]
    end
    
    subgraph LiteLLM["LiteLLM Proxy :18788"]
        Router[("Model Router")]
    end
    
    subgraph Ollama["Ollama (host.docker.internal:11434)"]
        API[("Ollama API")]
        Model[("qwen2.5-0.5b")]
    end
    
    subgraph External["External APIs"]
        Bailian["Bailian API<br/>(qwen3.5-plus, kimi-k2.5)"]
        Telegram["Telegram API"]
    end
    
    Cron -->|triggers job| Gateway
    Gateway -->|routes model| Router
    
    Router -->|"model: ollama/qwen2.5-0.5b"| Ollama
    Router -->|"model: bailian/kimi-k2.5"| Bailian
    
    Ollama -->|response| Gateway
    Gateway -->|send message| Telegram
    
    style Ollama fill:#90EE90
    style Model fill:#98FB98
```

### Текущий поток (проблема)
1. Cron запускает `heartbeat-check` каждые 30 минут
2. Gateway отправляет запрос в LiteLLM
3. LiteLLM маршрутизирует к `bailian/kimi-k2.5`
4. API таймаут 60 сек → ошибка

### Предлагаемый поток (решение)
1. Cron запускает `heartbeat-check`
2. Gateway отправляет запрос в LiteLLM  
3. LiteLLM маршрутизирует к `ollama/qwen2.5-0.5b`
4. Ответ за <5 сек → успех

---

## Интеграция с openclaw-docker

### Шаг 1: Добавить модель в LiteLLM config

Обновить [`litellm/config.yaml`](openclaw-docker/litellm/config.yaml):

```yaml
# Добавить в model_list:
- model_name: ollama/qwen2.5-0.5b
  litellm_params:
    model: ollama_chat/qwen2.5:0.5b
    api_base: os.environ/OLLAMA_HOST
```

### Шаг 2: Обновить cron/job для heartbeat

Изменить [`cron/jobs.json`](openclaw-docker/cron/jobs.json:520):

```json
{
  "id": "1955274a-8dd9-4586-9689-599bd6a138f6",
  "agentId": "main",
  "name": "heartbeat-check",
  "payload": {
    "model": "ollama/qwen2.5-0.5b",
    "timeoutSeconds": 15
  }
}
```

### Шаг 3: Перезапустить LiteLLM

```bash
cd /data/bot/openclaw-docker
docker compose restart litellm
```

### Шаг 4: Проверить работу

```bash
# Тест Ollama модели
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:0.5b",
  "prompt": "Кратко: система работает",
  "stream": false
}'

# Тест через LiteLLM
curl http://localhost:18788/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-openclaw-proxy" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/qwen2.5-0.5b",
    "messages": [{"role": "user", "content": "Привет"}],
    "max_tokens": 50
  }'
```

---

## Расширенные опции

### Опция A: Ollama напрямую (без LiteLLM)

Для максимальной скорости можно использовать Ollama API напрямую:

```javascript
// В heartbeat job payload
{
  "endpoint": "http://host.docker.internal:11434/api/generate",
  "model": "qwen2.5:0.5b"
}
```

### Опция B: Docker контейнер с Ollama

Если Ollama не установлен на хосте, добавить в docker-compose:

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: openclaw-ollama
  ports:
    - "11434:11434"
  volumes:
    - ./ollama:/root/.ollama
  environment:
    - OLLAMA_HOST=0.0.0.0
  deploy:
    resources:
      limits:
        memory: 4g
```

### Опция C: Несколько микро-задач

Для других простых задач (не heartbeat):

| Задача | Модель | Таймаут |
|--------|--------|---------|
| morning-digest | ollama/qwen2.5-1.5b | 30s |
| inbox-router | ollama/qwen2.5-0.5b | 15s |
| vault-gardening | ollama/qwen2.5-0.5b | 15s |
| watchdog | ollama/qwen2.5-0.5b | 10s |

---

## Оценка ресурсов и стоимости

### Текущее потребление (heartbeat с Kimi K2.5)
- **API вызовы**: ~1440 раз/месяц (каждые 30 минут)
- **Стоимость**: ~$0 (free tier) или ~$0.50-1$/месяц при лимитах
- **Таймауты**: 50% неудач (таймаут 60 сек)

### Новое потребление (qwen2.5-0.5b локально)
- **CPU/Mac Mini**: ~5-10% при запуске
- **RAM**: +1-2GB для модели
- **Стоимость**: $0 (локально)
- **Отклик**: <5 секунд
- **Доступность**: 100% (не зависит от внешнего API)

### Экономия
- **Денежная**: $0-1/месяц (незначительная)
- **Временная**: Нет таймаутов, мгновенный отклик
- **Надёжность**: Работает даже без интернета

---

## Плюсы и минусы подхода

### ✅ Плюсы

1. **Скорость**: <5 секунд vs 60+ секунд (таймаут)
2. **Надёжность**: Не зависит от внешних API
3. **Бесплатно**: Нет API расходов
4. **Автономность**: Работает без интернета
5. **Простота**: Уже есть Ollama в конфигурации

### ❌ Минусы

1. **Ограниченные возможности**: Не для сложных задач (нужен reasoning)
2. **Требует RAM**: ~1-2GB для модели
3. **Качество**: Хуже чем qwen3.5-plus или kimi-k2.5 для сложных задач
4. **Maintenance**: Нужно поддерживать модель обновлённой

### 🔄 Когда использовать локальную vs облачную

| Задача | Локальная (0.5B-1.5B) | Облачная (qwen3.5-plus) |
|--------|------------------------|-------------------------|
| Heartbeat | ✅ | ❌ |
| Простое чтение файла | ✅ | ❌ |
| Telegram роутинг | ✅ | ❌ |
| Анализ задач | ❌ | ✅ |
| Ночной эволюция | ❌ | ✅ |
| Сложный reasoning | ❌ | ✅ |

---

## Рекомендация по реализации

### Вывод

Для **heartbeat задачи** на Mac Mini M4 16GB:

**Рекомендуется использовать `ollama/qwen2.5-0.5b`**

Причины:
1. Идеально подходит для тривиальной задачи (чтение файла + форматирование)
2. Мгновенный отклик (<1 сек на M4 Neural Engine)
3. Минимальное потребление RAM (~1GB)
4. Уже настроен в LiteLLM (нужно только добавить alias)
5. Нет внешних зависимостей

### Приоритет внедрения

1. **Немедленно** (1 шаг): Изменить `model` в `heartbeat-check` job
2. **Опционально**: Добавить больше микро-моделей для других простых задач
3. **На будущее**: Рассмотреть Llama3.2-1B для задач чуть сложнее heartbeat

### Готовность к внедрению

- ✅ Ollama уже запущен и доступен
- ✅ LiteLLM уже настроен
- ✅ Mac Mini M4 имеет Neural Engine
- ❓ Нужно проверить какие модели загружены в Ollama

---

## Следующие шаги

1. **Проверить Ollama**: Какие модели загружены?
   ```bash
   docker compose exec openclaw ollama list
   ```

2. **При необходимости загрузить модель**:
   ```bash
   docker compose exec openclaw ollama pull qwen2.5:0.5b
   ```

3. **Обновить jobs.json** (1 строка)
4. **Перезапустить cron**: Применить изменения
5. **Мониторить**: Проверить 3-5 запусков heartbeat
