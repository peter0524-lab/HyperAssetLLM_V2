-- 뉴스 테이블 확장 스키마 (SkillStack 통합)
-- news 테이블에 고도화된 분석 기능을 위한 컬럼 추가

-- 기존 news 테이블에 새로운 컬럼들 추가
ALTER TABLE news 
ADD COLUMN IF NOT EXISTS duration_score INT DEFAULT 5 COMMENT '영향 지속시간 (0-10 스케일)',
ADD COLUMN IF NOT EXISTS market_impact TEXT COMMENT '시장 영향 분석 결과',
ADD COLUMN IF NOT EXISTS push_content TEXT COMMENT '푸시알림 내용',
ADD COLUMN IF NOT EXISTS relevance_score DECIMAL(3,2) DEFAULT 0.50 COMMENT '종목 관련성 점수 (0.0-1.0)',
ADD COLUMN IF NOT EXISTS similarity_checked BOOLEAN DEFAULT FALSE COMMENT '유사도 검사 완료 여부',
ADD COLUMN IF NOT EXISTS published_at TIMESTAMP NULL COMMENT '뉴스 발행 시간',
ADD COLUMN IF NOT EXISTS reasoning TEXT COMMENT '영향도 평가 근거';

-- 새로운 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_news_duration_score ON news (duration_score);
CREATE INDEX IF NOT EXISTS idx_news_relevance_score ON news (relevance_score);
CREATE INDEX IF NOT EXISTS idx_news_similarity_checked ON news (similarity_checked);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news (published_at);

-- 기존 컬럼 타입 최적화
ALTER TABLE news 
MODIFY COLUMN impact_score DECIMAL(3,2) DEFAULT 0.00 COMMENT '영향도 점수 (0-10 스케일, 기존 0-1에서 확장)',
MODIFY COLUMN title VARCHAR(1000) NOT NULL COMMENT '뉴스 제목 (길이 확장)',
MODIFY COLUMN url VARCHAR(1500) COMMENT 'URL 길이 확장';

-- 뉴스 처리 로그 테이블 생성 (새로운 테이블)
CREATE TABLE IF NOT EXISTS news_processing_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    news_title VARCHAR(1000) NOT NULL,
    news_url VARCHAR(1500),
    processing_stage VARCHAR(50) NOT NULL COMMENT 'simhash/relevance/similarity/impact/complete',
    processing_result VARCHAR(20) NOT NULL COMMENT 'pass/filter/error',
    processing_details JSON COMMENT '처리 상세 정보 (점수, 근거 등)',
    error_message TEXT,
    processing_time DECIMAL(8,3) COMMENT '처리 시간 (초)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_processing_stage (processing_stage),
    INDEX idx_processing_result (processing_result),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='뉴스 처리 과정 로그 테이블';

-- 시스템 성능 모니터링을 위한 뷰 생성
CREATE VIEW IF NOT EXISTS news_processing_summary AS
SELECT 
    DATE(created_at) as processing_date,
    stock_code,
    processing_stage,
    processing_result,
    COUNT(*) as count,
    AVG(processing_time) as avg_processing_time,
    MAX(processing_time) as max_processing_time
FROM news_processing_log 
GROUP BY DATE(created_at), stock_code, processing_stage, processing_result; 

-- 뉴스 테이블에 누락된 컬럼들 추가
-- relevance_score: 종목 관련성 점수 (0.0-1.0)
-- similarity_checked: 유사도 검사 완료 여부

ALTER TABLE news 
ADD COLUMN IF NOT EXISTS relevance_score DECIMAL(3,2) DEFAULT 1.00 COMMENT '종목 관련성 점수 (0.0-1.0)',
ADD COLUMN IF NOT EXISTS similarity_checked BOOLEAN DEFAULT TRUE COMMENT '유사도 검사 완료 여부';

-- 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_relevance_score ON news(relevance_score);
CREATE INDEX IF NOT EXISTS idx_similarity_checked ON news(similarity_checked);

-- 컬럼 추가 확인용 쿼리
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'HyperAsset' 
  AND TABLE_NAME = 'news' 
  AND COLUMN_NAME IN ('relevance_score', 'similarity_checked'); 