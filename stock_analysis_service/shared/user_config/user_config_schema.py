"""
사용자 설정 MySQL 스키마 정의
"""

# 사용자 프로필 테이블 생성 쿼리
CREATE_USER_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    news_similarity_threshold FLOAT DEFAULT 0.7,
    news_impact_threshold FLOAT DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone_number (phone_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 사용자 종목 테이블 생성 쿼리
CREATE_USER_STOCKS_TABLE = """
CREATE TABLE IF NOT EXISTS user_stocks (
    user_id INT,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, stock_code),
    INDEX idx_user_enabled (user_id, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 사용자 모델 테이블 생성 쿼리
CREATE_USER_MODEL_TABLE = """
CREATE TABLE IF NOT EXISTS user_model (
    user_id INT,
    model_type ENUM('hyperclova', 'chatgpt', 'claude', 'grok', 'gemini') DEFAULT 'hyperclova',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 모든 테이블 생성 쿼리
CREATE_ALL_TABLES = [
    CREATE_USER_PROFILES_TABLE,
    CREATE_USER_STOCKS_TABLE,
    CREATE_USER_MODEL_TABLE
] 