CREATE TABLE IF NOT EXISTS chart_analysis_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    
    date DATE NOT NULL,              -- 분석 날짜
    time TIME NOT NULL,              -- 분석 시간
    
    close_price FLOAT DEFAULT NULL,  -- 저장 당시 주가
    volume BIGINT DEFAULT NULL,      -- 저장 당시 거래량

    -- 조건 만족 여부
    golden_cross BOOLEAN DEFAULT FALSE,
    dead_cross BOOLEAN DEFAULT FALSE,
    bollinger_touch BOOLEAN DEFAULT FALSE,
    ma20_touch BOOLEAN DEFAULT FALSE,
    rsi_condition BOOLEAN DEFAULT FALSE,
    volume_surge BOOLEAN DEFAULT FALSE,
    macd_golden_cross BOOLEAN DEFAULT FALSE,
    support_resistance_break BOOLEAN DEFAULT FALSE,

    details JSON,

    INDEX idx_stock_date (stock_code, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; 