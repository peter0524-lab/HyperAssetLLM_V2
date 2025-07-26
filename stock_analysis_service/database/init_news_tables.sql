-- 뉴스 테이블 생성
CREATE TABLE IF NOT EXISTS news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    title VARCHAR(1000) NOT NULL,
    content TEXT NOT NULL,
    url VARCHAR(1000) NOT NULL,
    source VARCHAR(100) NOT NULL,
    published_at DATETIME NOT NULL,
    impact_score DECIMAL(3,2) DEFAULT 0.00,
    reasoning TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_created_at (created_at),
    INDEX idx_impact_score (impact_score),
    INDEX idx_published_at (published_at),
    UNIQUE KEY unique_url (url(255))
);

-- 주간 키워드 테이블 생성
CREATE TABLE IF NOT EXISTS weekly_keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    keywords JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_week_start (week_start_date),
    UNIQUE KEY unique_stock_week (stock_code, week_start_date)
); 