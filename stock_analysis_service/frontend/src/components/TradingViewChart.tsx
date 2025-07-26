import React, { useEffect, useRef } from 'react';

// TradingView 위젯 타입 정의
declare global {
  interface Window {
    TradingView: any;
  }
}

interface TradingViewChartProps {
  symbol: string;
  theme?: 'light' | 'dark';
  width?: string | number;
  height?: string | number;
  locale?: string;
  timezone?: string;
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({
  symbol = "005930",
  theme = "light",
  width = "100%",
  height = "100%",
  locale = "ko",
  timezone = "Asia/Seoul"
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // TradingView 스크립트가 이미 로드되어 있는지 확인
    if (window.TradingView) {
      createWidget();
    } else {
      // TradingView 스크립트 동적 로드
      const script = document.createElement('script');
      script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
      script.type = 'text/javascript';
      script.async = true;
      script.onload = () => {
        createWidget();
      };
      document.head.appendChild(script);
    }

    return () => {
      // 컴포넌트 언마운트 시 정리
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [symbol, theme]);

  const createWidget = () => {
    if (!containerRef.current) return;

    // 기존 위젯 제거
    containerRef.current.innerHTML = '';

    // 한국 주식 심볼 형식으로 변환
    const tradingViewSymbol = `KRX:${symbol}`;

    // TradingView 위젯 설정
    const widgetConfig = {
      "autosize": true,
      "symbol": tradingViewSymbol,
      "interval": "D",
      "timezone": timezone,
      "theme": theme,
      "style": "1",
      "locale": locale,
      "toolbar_bg": "#f1f3f6",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": `tradingview_${symbol}_${Date.now()}`,
      "studies": [
        "Volume@tv-basicstudies",
        "MASimple@tv-basicstudies"
      ],
      "show_popup_button": true,
      "popup_width": "1000",
      "popup_height": "650",
      "no_referral_id": true
    };

    try {
      // 위젯 생성
      new window.TradingView.widget({
        ...widgetConfig,
        container_id: containerRef.current
      });
    } catch (error) {
      console.error('TradingView 위젯 생성 실패:', error);
      // 폴백 UI 표시
      if (containerRef.current) {
        containerRef.current.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f8f9fa; border-radius: 8px; flex-direction: column;">
            <div style="text-align: center; color: #666;">
              <div style="font-size: 48px; margin-bottom: 16px;">📈</div>
              <h3 style="margin: 0 0 8px 0; color: #333;">차트 로딩 중...</h3>
              <p style="margin: 0; font-size: 14px;">종목: ${symbol}</p>
              <p style="margin: 8px 0 0 0; font-size: 12px; color: #999;">
                잠시 후 TradingView 차트가 표시됩니다
              </p>
            </div>
          </div>
        `;
      }
    }
  };

  return (
    <div className="w-full h-full relative">
      <div 
        ref={containerRef}
        className="w-full h-full"
        style={{ 
          minHeight: '400px',
          width: width,
          height: height
        }}
      />
      
      {/* 차트가 로드되지 않을 경우를 위한 폴백 */}
      <div className="absolute inset-0 flex items-center justify-center bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="text-4xl mb-4">📈</div>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">실시간 차트</h3>
          <p className="text-sm text-gray-600">{symbol} - 차트 로딩 중...</p>
        </div>
      </div>
    </div>
  );
};

export default TradingViewChart; 