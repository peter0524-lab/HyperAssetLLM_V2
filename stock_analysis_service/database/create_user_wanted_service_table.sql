-- HyperAsset.user_wanted_service 테이블 생성
-- 사용자별 원하는 서비스 활성화 상태 관리

CREATE TABLE IF NOT EXISTS HyperAsset.user_wanted_service (
  user_id            VARCHAR(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  phone_number       VARCHAR(20) COLLATE utf8mb4_unicode_ci,
  news_service       TINYINT NOT NULL DEFAULT 0,
  disclosure_service TINYINT NOT NULL DEFAULT 0,
  report_service     TINYINT NOT NULL DEFAULT 0,
  chart_service      TINYINT NOT NULL DEFAULT 0,
  flow_service       TINYINT NOT NULL DEFAULT 0,
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  CONSTRAINT fk_user_profiles_wanted
    FOREIGN KEY (user_id)
    REFERENCES HyperAsset.user_profiles(user_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CHECK (news_service       IN (0,1)),
  CHECK (disclosure_service IN (0,1)),
  CHECK (report_service     IN (0,1)),
  CHECK (chart_service      IN (0,1)),
  CHECK (flow_service       IN (0,1))
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='사용자별 원하는 서비스 활성화 설정';

-- 인덱스 생성
CREATE INDEX idx_user_wanted_service_phone ON HyperAsset.user_wanted_service(phone_number);
CREATE INDEX idx_user_wanted_service_updated ON HyperAsset.user_wanted_service(updated_at); 