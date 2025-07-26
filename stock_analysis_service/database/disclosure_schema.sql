DROP TABLE IF EXISTS disclosure_history;

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