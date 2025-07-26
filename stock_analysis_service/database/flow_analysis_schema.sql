-- 수급 분석 서비스 데이터베이스 스키마
-- 기관/외국인/개인 + 프로그램 매매 데이터 처리용

-- 1. 일별 수급 데이터 (EOD: End of Day)
CREATE TABLE IF NOT EXISTS eod_flows (
    id INT AUTO_INCREMENT,
    trade_date DATE NOT NULL,
    ticker VARCHAR(6) NOT NULL,
    inst_net BIGINT NOT NULL COMMENT '기관 순매수(+)/순매도(-)',
    foreign_net BIGINT NOT NULL COMMENT '외국인 순매수(+)/순매도(-)',
    individ_net BIGINT NOT NULL COMMENT '개인 순매수(+)/순매도(-)',
    total_value BIGINT NULL COMMENT '총 거래대금',
    close_price DECIMAL(10,2) NULL COMMENT '종가',
    volume BIGINT NULL COMMENT '거래량',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ticker),
    INDEX idx_id (id),
    INDEX idx_trade_date (trade_date),
    INDEX idx_ticker (ticker),
    INDEX idx_inst_net (inst_net),
    INDEX idx_foreign_net (foreign_net),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='일별 기관/외국인/개인 수급 데이터';

-- 2. 실시간 프로그램 매매 데이터
CREATE TABLE IF NOT EXISTS program_flows (
    id INT AUTO_INCREMENT,
    ts TIMESTAMP NOT NULL,
    ticker VARCHAR(6) NOT NULL,
    net_volume BIGINT NOT NULL COMMENT '+ 매수, - 매도',
    net_value BIGINT NULL COMMENT '프로그램 매매 금액',
    side CHAR(4) NULL COMMENT 'BUY/SELL',
    price DECIMAL(10,2) NULL COMMENT '현재가',
    total_volume BIGINT NULL COMMENT '총 거래량',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts, ticker),
    INDEX idx_id (id),
    INDEX idx_ts (ts),
    INDEX idx_ticker (ticker),
    INDEX idx_net_volume (net_volume),
    INDEX idx_side (side),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='실시간 프로그램 매매 데이터';

-- 3. 패턴 신호 저장 테이블
CREATE TABLE IF NOT EXISTS pattern_signals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ref_time TIMESTAMP NOT NULL,
    ticker VARCHAR(6) NOT NULL,
    daily_inst_strong BOOLEAN DEFAULT FALSE COMMENT '일별 기관 강매수 신호',
    rt_prog_strong BOOLEAN DEFAULT FALSE COMMENT '실시간 프로그램 강매수 신호',
    composite_strong BOOLEAN GENERATED ALWAYS AS (daily_inst_strong AND rt_prog_strong) STORED COMMENT '복합 신호',
    inst_buy_days INT NULL COMMENT '최근 5일 중 기관 순매수일',
    prog_volume BIGINT NULL COMMENT '프로그램 매매량',
    prog_ratio DECIMAL(5,2) NULL COMMENT '프로그램 매매 비율(30일 평균 대비)',
    trigger_data JSON NULL COMMENT '트리거 발생 상세 데이터',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ref_time (ref_time),
    INDEX idx_ticker (ticker),
    INDEX idx_daily_inst_strong (daily_inst_strong),
    INDEX idx_rt_prog_strong (rt_prog_strong),
    INDEX idx_composite_strong (composite_strong),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='수급 패턴 신호 저장';

-- 4. 데이터 정리를 위한 파티셔닝 (선택사항)
-- program_flows 테이블의 경우 데이터가 많이 쌓일 수 있으므로 월별 파티셔닝 고려
-- ALTER TABLE program_flows PARTITION BY RANGE (YEAR(ts)*100 + MONTH(ts)) (
--     PARTITION p202501 VALUES LESS THAN (202502),
--     PARTITION p202502 VALUES LESS THAN (202503),
--     PARTITION p202503 VALUES LESS THAN (202504),
--     PARTITION p202504 VALUES LESS THAN (202505),
--     PARTITION p202505 VALUES LESS THAN (202506),
--     PARTITION p202506 VALUES LESS THAN (202507),
--     PARTITION p202507 VALUES LESS THAN (202508),
--     PARTITION p202508 VALUES LESS THAN (202509),
--     PARTITION p202509 VALUES LESS THAN (202510),
--     PARTITION p202510 VALUES LESS THAN (202511),
--     PARTITION p202511 VALUES LESS THAN (202512),
--     PARTITION p202512 VALUES LESS THAN (202601),
--     PARTITION pmax VALUES LESS THAN MAXVALUE
-- ); 