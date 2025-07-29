-- 실제 봇 토큰으로 업데이트하는 스크립트
-- ※ BotFather에서 받은 실제 토큰으로 교체하세요!

UPDATE telegram_channels 
SET 
    bot_token = '7888091225:AAHMqbCQV4_so7VqDeLqbWaiGTvVyQ698-M',  -- miraeaibot 토큰으로 업데이트
    channel_url = 'https://t.me/HypperAssetAlerts',  -- 실제 채널 URL
    updated_at = NOW()
WHERE channel_id = 1;