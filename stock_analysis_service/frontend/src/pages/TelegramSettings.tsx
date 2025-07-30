import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { 
  Loader2, 
  Bell, 
  ArrowLeft,
  TrendingUp,
  AlertTriangle,
  Search,
  X
} from "lucide-react";
import { toast } from "sonner";
import { api, userStorage, telegramChannelApi, StockInfo } from "@/lib/api";
import stocksData from "@/data/stocks.json";

interface TelegramChannel {
  channel_id: number;
  channel_name: string;
  channel_username: string;
  channel_url: string;
  channel_description: string;
  is_active: boolean;
}

const TelegramSettings = () => {
  const navigate = useNavigate();
  const [userId, setUserId] = useState<string>('');
  const [channel, setChannel] = useState<TelegramChannel>({
    channel_id: 1,
    channel_name: 'HyperAsset 주식 알림',
    channel_username: 'HyperAssetAlerts',
    channel_url: 'https://t.me/HyperAssetAlerts',
    channel_description: '빗썸 스타일 실시간 주식 알림 채널입니다. 뉴스, 공시, 차트 패턴 등 중요한 정보를 실시간으로 받아보세요!',
    is_active: true
  });

  // 종목 관련 상태
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStocks, setSelectedStocks] = useState<StockInfo[]>([]);

  // 페이지 진입 시 사용자 ID 설정 및 기존 종목 불러오기
  useEffect(() => {
    const currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      navigate('/auth');
      return;
    }
    setUserId(currentUserId);
    
    // 기존 종목 불러오기
    api.getUserConfig(currentUserId).then(cfg => {
      if (cfg && cfg.stocks) {
        setSelectedStocks(cfg.stocks);
      }
    });
  }, [navigate]);

  // 텔레그램 채널 정보 조회
  const { data: channelData, isLoading: isLoadingChannel, error: channelError } = useQuery({
    queryKey: ['telegramChannel', userId],
    queryFn: async () => {
      if (!userId) {
        return {
          channel_id: 1,
          channel_name: 'HyperAsset 주식 알림',
          channel_username: 'HyperAssetAlerts',
          channel_url: 'https://t.me/HyperAssetAlerts',
          channel_description: '빗썸 스타일 실시간 주식 알림 채널입니다. 뉴스, 공시, 차트 패턴 등 중요한 정보를 실시간으로 받아보세요!',
          is_active: true
        };
      }
      
      try {
        const response = await telegramChannelApi.getChannelInfo(userId);
        return response.data;
      } catch (error) {
        console.error('텔레그램 채널 조회 실패:', error);
        return {
          channel_id: 1,
          channel_name: 'HyperAsset 주식 알림',
          channel_username: 'HyperAssetAlerts',
          channel_url: 'https://t.me/HyperAssetAlerts',
          channel_description: '빗썸 스타일 실시간 주식 알림 채널입니다. 뉴스, 공시, 차트 패턴 등 중요한 정보를 실시간으로 받아보세요!',
          is_active: true
        };
      }
    },
    retry: false,
  });

  // 환영 메시지 전송 mutation
  const sendWelcomeMutation = useMutation({
    mutationFn: () => telegramChannelApi.sendSimpleWelcomeMessage(userId),
    onSuccess: (data) => {
      toast.success('�� 환영 메시지가 텔레그램 채널에 전송되었습니다!');
      console.log('환영 메시지 전송 성공:', data);
    },
    onError: (error) => {
      toast.error('❌ 환영 메시지 전송에 실패했습니다.');
      console.error('환영 메시지 전송 실패:', error);
    }
  });

  // 테스트 알림 전송 mutation
  const sendTestNotificationMutation = useMutation({
    mutationFn: () => telegramChannelApi.sendSimpleTestMessage(userId),
    onSuccess: (data) => {
      toast.success('📤 테스트 알림이 전송되었습니다!');
      console.log('테스트 알림 전송 성공:', data);
    },
    onError: (error) => {
      toast.error('❌ 테스트 알림 전송에 실패했습니다.');
      console.error('테스트 알림 전송 실패:', error);
    }
  });

  // 채널 정보 설정
  useEffect(() => {
    if (channelData) {
      setChannel(channelData);
    }
  }, [channelData]);

  // 텔레그램 채널로 이동 핸들러
  const handleChannelJoin = () => {
    if (channelData?.channel_url) {
      window.open(channelData.channel_url, '_blank');
      sendWelcomeMutation.mutate();
      toast.success('📱 텔레그램 채널로 이동합니다!');
    } else {
      toast.error('❌ 채널 정보를 찾을 수 없습니다.');
    }
  };

  // 테스트 알림 전송 함수
  const handleSendTestNotification = () => {
    if (!userId) {
      toast.error('사용자 ID를 찾을 수 없습니다.');
      return;
    }
    sendTestNotificationMutation.mutate();
  };

  // 종목 검색 결과 필터링
  const filteredStocks = stocksData.filter(stock =>
    stock.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    stock.stock_code.includes(searchQuery)
  );

  // 종목 추가
  const addStock = (stock: typeof stocksData[0]) => {
    if (selectedStocks.some(s => s.code === stock.stock_code)) {
      toast.error("이미 추가된 종목입니다.");
      return;
    }
    setSelectedStocks(prev => [...prev, { 
      code: stock.stock_code, 
      name: stock.company_name,
      sector: stock.sector || "기타"
    }]);
    setSearchQuery("");
    toast.success(`${stock.company_name}이(가) 추가되었습니다.`);
  };

  // 종목 제거
  const removeStock = (stockCode: string) => {
    setSelectedStocks(prev => prev.filter(stock => stock.code !== stockCode));
    toast.success("종목이 제거되었습니다.");
  };

  // 로딩 상태 확인
  const isDataLoading = isLoadingChannel;

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-blue-50 to-indigo-100 py-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-full mb-6">
              <Bell className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              📱 텔레그램 알림 설정
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              실시간 주식 알림을 텔레그램으로 받아보세요
            </p>
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto space-y-8">
            
            {/* 뒤로가기 버튼 */}
            <Button 
              variant="outline" 
              onClick={() => navigate('/dashboard')}
              className="mb-6"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              대시보드로 돌아가기
            </Button>

            {/* 로딩 상태 */}
            {isDataLoading && (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                  <p className="text-gray-600">텔레그램 채널 정보를 불러오는 중...</p>
                </div>
              </div>
            )}

            {/* 에러 알림 */}
            {channelError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  텔레그램 설정을 불러오는 중 오류가 발생했습니다. 기본 설정으로 표시됩니다.
                </AlertDescription>
              </Alert>
            )}

            {/* 종목 알림 설정 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-blue-600" />
                  종목 알림 설정
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="text-center space-y-4">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-full">
                    <Bell className="h-8 w-8 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">HypperAsset 주식 실시간 알림</h3>
                    <p className="text-gray-600 mb-6">중요한 주식 정보를 실시간으로 받아보세요</p>
                  </div>
                </div>

                {/* 종목 선택 UI */}
                <div className="space-y-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      placeholder="종목명 또는 종목코드 검색..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 text-lg py-3"
                    />
                  </div>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {searchQuery && filteredStocks.length === 0 && (
                      <p className="text-center text-gray-500 py-4">검색 결과가 없습니다.</p>
                    )}
                    {filteredStocks.slice(0, 20).map((stock) => (
                      <div key={stock.stock_code} className="flex items-center justify-between p-2 border rounded-lg">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{stock.company_name}</span>
                          <span className="text-xs text-gray-400">({stock.stock_code})</span>
                        </div>
                        <Button size="sm" variant="outline" onClick={() => addStock(stock)}>
                          추가
                        </Button>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4">
                    <Label className="text-base font-medium">선택된 종목</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedStocks.length === 0 && <span className="text-gray-400">종목을 추가하세요</span>}
                      {selectedStocks.map((stock) => (
                        <Badge key={stock.code} className="flex items-center gap-1">
                          {stock.name}
                          <Button size="default" variant="ghost" onClick={() => removeStock(stock.code)}>
                            <X className="h-3 w-3" />
                          </Button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="mt-6 flex justify-center">
                    <Button onClick={handleChannelJoin} className="bg-green-600 hover:bg-green-700 text-white px-8">
                      선택한 종목 텔레그램 방으로 이동
                    </Button>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-500">
                      ⚠️ MVP 버전에서는 미래에셋증권 종목만 채팅방이 동작합니다.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 테스트 알림 버튼 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  🧪 테스트 알림
                </CardTitle>
                <AlertDescription>
                  봇이 텔레그램 채널에 메시지를 제대로 보낼 수 있는지 확인합니다
                </AlertDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  onClick={handleSendTestNotification}
                  disabled={sendTestNotificationMutation.isPending}
                  className="w-full bg-orange-500 hover:bg-orange-600 text-white"
                >
                  {sendTestNotificationMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      전송 중...
                    </>
                  ) : (
                    <>
                      🧪 테스트 알림 전송
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
      
      <Footer />
    </div>
  );
};

export default TelegramSettings;