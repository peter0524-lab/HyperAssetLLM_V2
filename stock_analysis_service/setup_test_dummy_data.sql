-- 미래에셋 증권 사용자 테스트 더미 데이터 생성
-- 사용자 ID: mirae_user_001

-- 1. 사용자 프로필 생성
INSERT INTO HyperAsset.user_profiles (
    user_id, 
    username, 
    phone_number, 
    news_similarity_threshold, 
    news_impact_threshold,
    created_at,
    updated_at
) VALUES (
    'mirae_user_001',
    '미래에셋_테스트_사용자',
    '01012345678',
    0.7,
    0.8,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    username = VALUES(username),
    phone_number = VALUES(phone_number),
    news_similarity_threshold = VALUES(news_similarity_threshold),
    news_impact_threshold = VALUES(news_impact_threshold),
    updated_at = NOW();

-- 2. 사용자 종목 설정 (미래에셋증권)
INSERT INTO HyperAsset.user_stocks (
    user_id,
    stock_code,
    stock_name,
    enabled,
    created_at,
    updated_at
) VALUES (
    'mirae_user_001',
    '006800',
    '미래에셋증권',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    stock_name = VALUES(stock_name),
    enabled = VALUES(enabled),
    updated_at = NOW();

-- 3. 사용자 모델 설정
INSERT INTO HyperAsset.user_model (
    user_id,
    model_type,
    created_at,
    updated_at
) VALUES (
    'mirae_user_001',
    'hyperclova',
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    model_type = VALUES(model_type),
    updated_at = NOW();

-- 4. 사용자 원하는 서비스 설정 (모든 서비스 활성화)
INSERT INTO HyperAsset.user_wanted_service (
    user_id,
    phone_number,
    news_service,
    disclosure_service,
    report_service,
    chart_service,
    flow_service,
    created_at,
    updated_at
) VALUES (
    'mirae_user_001',
    '01012345678',
    1,  -- 뉴스 서비스 활성화
    1,  -- 공시 서비스 활성화
    1,  -- 리포트 서비스 활성화
    1,  -- 차트 서비스 활성화
    1,  -- 수급 분석 서비스 활성화
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    phone_number = VALUES(phone_number),
    news_service = VALUES(news_service),
    disclosure_service = VALUES(disclosure_service),
    report_service = VALUES(report_service),
    chart_service = VALUES(chart_service),
    flow_service = VALUES(flow_service),
    updated_at = NOW();

-- 5. 알림 히스토리 테이블 생성 (없는 경우)
CREATE TABLE IF NOT EXISTS HyperAsset.notification_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,
    level VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    recipient VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    INDEX idx_notification_type (notification_type),
    INDEX idx_level (level),
    INDEX idx_sent_at (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 알림 설정 테이블 생성 (없는 경우)
CREATE TABLE IF NOT EXISTS HyperAsset.notification_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    min_level VARCHAR(20) DEFAULT 'medium',
    schedule_settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_type (user_id, notification_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 미래에셋증권 알림 설정 추가
INSERT INTO HyperAsset.notification_settings (
    user_id,
    notification_type,
    enabled,
    min_level,
    created_at,
    updated_at
) VALUES 
    ('mirae_user_001', 'news_alert', 1, 'medium', NOW(), NOW()),
    ('mirae_user_001', 'disclosure_alert', 1, 'high', NOW(), NOW()),
    ('mirae_user_001', 'chart_alert', 1, 'medium', NOW(), NOW()),
    ('mirae_user_001', 'weekly_report', 1, 'low', NOW(), NOW()),
    ('mirae_user_001', 'analysis_alert', 1, 'high', NOW(), NOW())
ON DUPLICATE KEY UPDATE
    enabled = VALUES(enabled),
    min_level = VALUES(min_level),
    updated_at = NOW();

-- 확인 쿼리
SELECT '사용자 프로필' as table_name, COUNT(*) as count FROM HyperAsset.user_profiles WHERE user_id = 'mirae_user_001'
UNION ALL
SELECT '사용자 종목' as table_name, COUNT(*) as count FROM HyperAsset.user_stocks WHERE user_id = 'mirae_user_001'
UNION ALL
SELECT '사용자 모델' as table_name, COUNT(*) as count FROM HyperAsset.user_model WHERE user_id = 'mirae_user_001'
UNION ALL
SELECT '사용자 서비스' as table_name, COUNT(*) as count FROM HyperAsset.user_wanted_service WHERE user_id = 'mirae_user_001'
UNION ALL
SELECT '알림 설정' as table_name, COUNT(*) as count FROM HyperAsset.notification_settings WHERE user_id = 'mirae_user_001'; 