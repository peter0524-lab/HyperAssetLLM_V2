-- 주식 분석 서비스 완전 데이터베이스 스키마
-- 모든 서비스에서 사용하는 테이블들을 포함

-- 1. 뉴스 관련 테이블
CREATE TABLE IF NOT EXISTS news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    summary TEXT,
    url VARCHAR(1000),
    source VARCHAR(100),
    impact_score DECIMAL(3,2) DEFAULT 0.00,
    keywords TEXT,
    similar_cases TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_impact_score (impact_score),
    INDEX idx_created_at (created_at),
    INDEX idx_processed_at (processed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 공시 관련 테이블
CREATE TABLE disclosure_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rcept_no VARCHAR(20) NOT NULL,
    corp_name VARCHAR(200) NOT NULL,
    corp_code VARCHAR(200) NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    report_nm VARCHAR(500) NOT NULL,
    flr_nm VARCHAR(200),
    rcept_dt DATE NOT NULL,
    rm TEXT,
    summary TEXT,
    impact_score DECIMAL(3,2) DEFAULT 0.00,
    sentiment  VARCHAR(20),
    sentiment_reason TEXT,
    expected_impact VARCHAR(20),
    impact_duration VARCHAR(20),
    keywords TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_rcept_no (rcept_no),
    INDEX idx_stock_code (stock_code),
    INDEX idx_impact_score (impact_score),
    INDEX idx_rcept_dt (rcept_dt),
    INDEX report_nm (report_nm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; 

-- 3. 차트 분석 관련 테이블
CREATE TABLE IF NOT EXISTS chart_conditions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    condition_name VARCHAR(100) NOT NULL,
    condition_result BOOLEAN NOT NULL,
    condition_data JSON,
    price DECIMAL(10,2),
    volume BIGINT,
    trigger_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_condition_name (condition_name),
    INDEX idx_trigger_time (trigger_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chart_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    adj_close DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stock_code_date (stock_code, date),
    UNIQUE KEY unique_stock_date (stock_code, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 주간 보고서 관련 테이블
CREATE TABLE IF NOT EXISTS weekly_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    report_title VARCHAR(500) NOT NULL,
    report_content TEXT,
    summary TEXT,
    key_keywords TEXT,
    recommendation VARCHAR(50),
    target_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    pdf_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_report_date (report_date),
    INDEX idx_stock_code (stock_code),
    UNIQUE KEY unique_report (report_date, stock_code, report_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS weekly_keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    keywords TEXT NOT NULL,
    keyword_scores JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_week_start (week_start),
    INDEX idx_stock_code (stock_code),
    UNIQUE KEY unique_week_stock (week_start, stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 주가 원인 분석 테이블
CREATE TABLE IF NOT EXISTS price_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    analysis_date DATE NOT NULL,
    price_before DECIMAL(10,2) NOT NULL,
    price_after DECIMAL(10,2) NOT NULL,
    change_rate DECIMAL(5,2) NOT NULL,
    volume BIGINT NOT NULL,
    analysis_type VARCHAR(20) NOT NULL,
    analysis_result TEXT,
    related_news TEXT,
    related_disclosures TEXT,
    similar_cases TEXT,
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_analysis_date (analysis_date),
    INDEX idx_change_rate (change_rate),
    INDEX idx_volume (volume)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 서비스 모니터링 테이블
CREATE TABLE IF NOT EXISTS service_monitoring (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    service_status VARCHAR(20) NOT NULL,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    restart_count INT DEFAULT 0,
    memory_usage DECIMAL(5,2),
    cpu_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_service_name (service_name),
    INDEX idx_service_status (service_status),
    INDEX idx_last_heartbeat (last_heartbeat)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 알림 로그 테이블
CREATE TABLE IF NOT EXISTS notification_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    stock_code VARCHAR(10),
    message TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent',
    error_message TEXT,
    INDEX idx_service_name (service_name),
    INDEX idx_notification_type (notification_type),
    INDEX idx_stock_code (stock_code),
    INDEX idx_sent_at (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 시스템 설정 테이블
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) DEFAULT 'string',
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. 종목 정보 테이블
CREATE TABLE IF NOT EXISTS stock_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL UNIQUE,
    company_name VARCHAR(200) NOT NULL,
    sector VARCHAR(100),
    market_cap BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_company_name (company_name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기본 설정 데이터 삽입
INSERT INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
('news_crawl_interval_market', '300', 'integer', '장중 뉴스 크롤링 간격(초)'),
('news_crawl_interval_after', '3600', 'integer', '장외 뉴스 크롤링 간격(초)'),
('news_impact_threshold', '0.7', 'float', '뉴스 영향력 임계값'),
('disclosure_check_interval', '3600', 'integer', '공시 확인 간격(초)'),
('chart_analysis_interval', '600', 'integer', '차트 분석 간격(초)'),
('price_change_threshold', '0.1', 'float', '주가 변동 임계값'),
('volume_threshold', '10000000', 'integer', '거래량 임계값'),
('telegram_enabled', 'true', 'boolean', '텔레그램 알림 활성화'),
('service_auto_restart', 'true', 'boolean', '서비스 자동 재시작 활성화')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);

-- 인덱스 최적화
OPTIMIZE TABLE news, disclosure_data, chart_conditions, chart_data, weekly_reports, weekly_keywords, price_analysis, service_monitoring, notification_logs, system_settings, stock_info; 