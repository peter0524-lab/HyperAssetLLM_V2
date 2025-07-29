-- 텔레그램 채널 설정 테이블
CREATE TABLE IF NOT EXISTS telegram_channels (
    channel_id INT AUTO_INCREMENT PRIMARY KEY,
    channel_name VARCHAR(100) NOT NULL UNIQUE,
    channel_username VARCHAR(100) NOT NULL UNIQUE,
    channel_url VARCHAR(255) NOT NULL,
    bot_token VARCHAR(255) NOT NULL,
    bot_username VARCHAR(100) NOT NULL,
    channel_description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 사용자별 알림 구독 설정 테이블
CREATE TABLE IF NOT EXISTS user_telegram_subscriptions (
    user_id VARCHAR(50) COLLATE utf8mb4_unicode_ci NOT NULL,
    channel_id INT NOT NULL,
    news_alerts BOOLEAN DEFAULT TRUE,
    disclosure_alerts BOOLEAN DEFAULT TRUE,
    chart_alerts BOOLEAN DEFAULT TRUE,
    price_alerts BOOLEAN DEFAULT TRUE,
    weekly_reports BOOLEAN DEFAULT FALSE,
    error_alerts BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, channel_id),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES telegram_channels(channel_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 텔레그램 알림 로그 테이블
CREATE TABLE IF NOT EXISTS telegram_notification_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_id INT NOT NULL,
    notification_type ENUM('news', 'disclosure', 'chart', 'price', 'weekly_report', 'error') NOT NULL,
    message_content TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('sent', 'failed', 'pending') DEFAULT 'pending',
    error_message TEXT,
    FOREIGN KEY (channel_id) REFERENCES telegram_channels(channel_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 인덱스 생성
CREATE INDEX idx_telegram_subscriptions_user_id ON user_telegram_subscriptions(user_id);
CREATE INDEX idx_telegram_subscriptions_channel_id ON user_telegram_subscriptions(channel_id);
CREATE INDEX idx_telegram_logs_channel_id ON telegram_notification_logs(channel_id);
CREATE INDEX idx_telegram_logs_sent_at ON telegram_notification_logs(sent_at);
CREATE INDEX idx_telegram_logs_status ON telegram_notification_logs(status);

-- 초기 채널 데이터 삽입 (※ YOUR_BOT_TOKEN_HERE 부분 꼭 진짜 토큰으로 교체!)
INSERT INTO telegram_channels (
    channel_name, 
    channel_username, 
    channel_url, 
    bot_token, 
    bot_username, 
    channel_description
) VALUES (
    'HyperAsset 주식 알림',
    'HypperAssetAlerts',
    'https://t.me/HypperAssetAlerts',
    '7888091225:AAHMqbCQV4_so7VqDeLqbWaiGTvVyQ698-M',
    'miraeaibot',
    '실시간 주식 알림 채널입니다. 뉴스, 공시, 차트 패턴 등 중요한 정보를 실시간으로 받아보세요!'
) ON DUPLICATE KEY UPDATE
    channel_description = VALUES(channel_description);
