import React, { useState } from 'react';
import { TrendingUp, Search, Activity } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import stocksData from "@/data/stocks.json";

interface TradingViewChartProps {
  symbol: string;
  theme?: 'light' | 'dark';
  width?: string | number;
  height?: string | number;
  locale?: string;
  timezone?: string;
  onStockChange?: (stock: { stock_code: string; company_name: string; sector: string }) => void;
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({
  symbol: initialSymbol = "005930",
  theme = "light",
  width = "100%",
  height = "100%",
  onStockChange
}) => {
  const [selectedStock, setSelectedStock] = useState(() => {
    // 초기 종목 정보 찾기
    return stocksData.find(stock => stock.stock_code === initialSymbol) || stocksData[0];
  });
  const [searchQuery, setSearchQuery] = useState("");

  // 한국 주식 심볼을 TradingView 형식으로 변환
  const getTradingViewSymbol = (koreanSymbol: string) => {
    // 한국 주식의 경우 여러 형식 시도
    // 1. KRX 형식 (한국거래소)
    return `KRX:${koreanSymbol}`;
    // 참고: 다른 시도할 수 있는 형식들:
    // - `KOSPI:${koreanSymbol}` 
    // - `${koreanSymbol}.KQ` (코스닥)
    // - `${koreanSymbol}.KS` (코스피)
  };

  // 검색 결과 필터링
  const filteredStocks = stocksData.filter(stock =>
    stock.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    stock.stock_code.includes(searchQuery)
  ).slice(0, 10); // 최대 10개만 표시

  // 종목 선택 핸들러
  const handleStockSelect = (stock: typeof stocksData[0]) => {
    setSelectedStock(stock);
    setSearchQuery("");
    // 상위 컴포넌트에 변경 사항 전달
    onStockChange?.(stock);
  };

  // TradingView iframe 위젯 URL 생성
  const getTradingViewEmbedUrl = (stockCode: string) => {
    const tradingViewSymbol = getTradingViewSymbol(stockCode);
    const params = new URLSearchParams({
      symbol: tradingViewSymbol,
      theme: theme === "dark" ? "dark" : "light",
      interval: "D",
      timezone: "Asia/Seoul",
      locale: "ko",
      toolbar_bg: "#f1f3f6",
      enable_publishing: "false",
      allow_symbol_change: "false",
      referral_id: "2588"
    });
    
    return `https://www.tradingview.com/widgetembed/?${params.toString()}`;
  };

  return (
    <div 
      className="w-full h-full relative bg-white border border-gray-200 rounded-lg overflow-hidden"
      style={{ 
        width: width,
        height: height,
        minHeight: '500px'
      }}
    >
      {/* 헤더 - 종목 검색 */}
      <div className="border-b border-gray-200 p-4 bg-gray-50">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            실시간 차트
          </h2>
        </div>
        
        {/* 종목 검색 */}
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="종목명 또는 종목코드를 검색하세요..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="text-sm text-gray-600">
              현재: <span className="font-semibold">{selectedStock.company_name}</span> ({selectedStock.stock_code})
            </div>
          </div>
          
          {/* 검색 결과 드롭다운 */}
          {searchQuery && filteredStocks.length > 0 && (
            <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-md shadow-lg mt-1 z-10 max-h-60 overflow-y-auto">
              {filteredStocks.map((stock) => (
                <button
                  key={stock.stock_code}
                  onClick={() => handleStockSelect(stock)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                >
                  <div className="font-medium text-gray-900">{stock.company_name}</div>
                  <div className="text-sm text-gray-600">{stock.stock_code} • {stock.sector}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 차트 영역 */}
      <div className="flex-1" style={{ height: 'calc(100% - 120px)' }}>
        {/* 개발 환경에서는 대체 UI, 프로덕션에서는 실제 차트 */}
        {process.env.NODE_ENV === 'development' ? (
          /* 개발 환경 - 대체 UI */
          <div className="flex items-center justify-center bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg h-full">
            <div className="text-center p-8">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {selectedStock.company_name} 차트
              </h3>
              <p className="text-gray-600 mb-4">
                종목코드: {selectedStock.stock_code} | 업종: {selectedStock.sector}
              </p>
              
              {/* 샘플 차트 시뮬레이션 */}
              <div className="flex items-end justify-center gap-2 mb-6">
                {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95].map((height, index) => (
                  <div
                    key={index}
                    className="w-4 bg-blue-500 rounded-t"
                    style={{ height: `${height}px` }}
                  />
                ))}
              </div>
              
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <p className="text-sm text-yellow-800">
                  <strong>🔧 개발 모드:</strong> 실시간 차트는 프로덕션 환경에서 정상 작동합니다.
                  <br />현재는 로컬 개발 환경에서 CORS 제한을 피하기 위한 대체 UI입니다.
                </p>
              </div>
              <div className="mt-4 text-xs text-gray-500">
                TradingView 심볼: {getTradingViewSymbol(selectedStock.stock_code)}
              </div>
            </div>
          </div>
        ) : (
          /* 프로덕션 환경 - 실제 TradingView 차트 */
          <iframe
            src={getTradingViewEmbedUrl(selectedStock.stock_code)}
            width="100%"
            height="100%"
            style={{ minHeight: '400px', border: 'none' }}
            title={`${selectedStock.company_name} 실시간 차트`}
            allowFullScreen
          />
        )}
      </div>
    </div>
  );
};

export default TradingViewChart; 