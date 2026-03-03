-- finance.db схема для PFM с поддержкой трансферов и LLM классификации

-- Таблица счетов (справочник)
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,      -- "HUMO", "Visa", "Cash", "Bybit"
  type TEXT DEFAULT 'card',       -- card | cash | crypto | bank
  is_mine BOOLEAN DEFAULT 1,      -- свои счета (трансферы) vs внешние
  currency TEXT DEFAULT 'UZS',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Свои счета (для трансферов)
INSERT OR IGNORE INTO accounts (name, type, is_mine) VALUES
  ('HUMO', 'card', 1),
  ('Visa', 'card', 1),
  ('Cash', 'cash', 1),
  ('Bybit', 'crypto', 1);

-- Таблица транзакций
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  
  -- Основные поля
  date TEXT NOT NULL,
  time TEXT,
  amount REAL NOT NULL,
  currency TEXT DEFAULT 'UZS',
  category TEXT,
  merchant TEXT,
  
  -- Источник
  source TEXT,                    -- "HUMO", "Uzum", "Kapital"
  card_last4 TEXT,
  sms_text TEXT,
  
  -- Классификация
  type TEXT DEFAULT 'expense',    -- expense | income | transfer
  sms_class TEXT,                 -- transaction | transfer | promotional | informational
  confidence REAL,                -- уверенность LLM (0.0-1.0)
  
  -- Для трансферов
  is_transfer BOOLEAN DEFAULT 0,
  from_account TEXT,              -- счёт с которого (для transfer)
  to_account TEXT,                -- счёт на который (для transfer)
  matched_transfer_id INTEGER,    -- связь с парной транзакцией
  
  -- Actual Budget sync
  actual_budget_id TEXT,          -- ID в Actual Budget
  synced_at DATETIME,
  
  -- Мета
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_sms_class ON transactions(sms_class);
CREATE INDEX IF NOT EXISTS idx_transactions_source ON transactions(source);

-- Таблица для хранения состояния (аналог .sms_state.json)
CREATE TABLE IF NOT EXISTS state (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Таблица логов классификации
CREATE TABLE IF NOT EXISTS classification_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sms_text TEXT NOT NULL,
  predicted_class TEXT,
  confidence REAL,
  duration_ms INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
