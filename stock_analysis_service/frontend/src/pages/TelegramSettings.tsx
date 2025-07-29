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
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { 
  Loader2, 
  Bell, 
  CheckCircle, 
  XCircle, 
  ArrowLeft,
  MessageSquare,
  TrendingUp,
  FileText,
  BarChart3,
  AlertTriangle,
  Settings,
  TestTube
} from "lucide-react";
import { toast } from "sonner";
import { api, userStorage, telegramChannelApi } from "@/lib/api";

interface TelegramChannel {
  channel_id: number;
  channel_name: string;
  channel_username: string;
  channel_url: string;
  channel_description: string;
  is_active: boolean;
}

interface TelegramSubscription {
  user_id: string;
  channel_id: number;
  news_alerts: boolean;
  disclosure_alerts: boolean;
  chart_alerts: boolean;
  price_alerts: boolean;
  weekly_reports: boolean;
  error_alerts: boolean;
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
  const [subscription, setSubscription] = useState<TelegramSubscription>({
    user_id: '',
    channel_id: 1,
    news_alerts: true,
    disclosure_alerts: true,
    chart_alerts: true,
    price_alerts: true,
    weekly_reports: false,
    error_alerts: false,
    is_active: true,
  });
  const [isSaving, setIsSaving] = useState(false);

  // 모든 Hook을 항상 실행되도록 배치
  useEffect(() => {
    const currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      navigate('/auth');
      return;
    }
    setUserId(currentUserId);
    setSubscription(prev => ({ ...prev, user_id: currentUserId }));
  }, [navigate]);

  // 텔레그램 채널 정보 조회 (React Hooks 규칙 준수)
  const { data: channelData, isLoading: isLoadingChannel, error: channelError } = useQuery({
    queryKey: ['telegramChannel', userId],
    queryFn: async () => {
      if (!userId) {
        // userId가 없으면 기본값 반환
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
        // 기본 채널 정보 반환
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
    retry: false, // 에러 시 재시도 안함
  });

  // 사용자 구독 설정 조회 (React Hooks 규칙 준수)
  const { data: subscriptionData, isLoading: isLoadingSubscription, error: subscriptionError } = useQuery({
    queryKey: ['telegramSubscription', userId],
    queryFn: async () => {
      if (!userId) {
        // userId가 없으면 기본값 반환
        return {
          user_id: '',
          channel_id: 1,
          news_alerts: true,
          disclosure_alerts: true,
          chart_alerts: true,
          price_alerts: true,
          weekly_reports: false,
          error_alerts: false,
          is_active: true,
        };
      }
      
      try {
        const response = await telegramChannelApi.getSubscription(userId);
        return response.data;
      } catch (error) {
        console.error('텔레그램 구독 설정 조회 실패:', error);
        // 기본 구독 설정 반환
        return {
          user_id: userId,
          channel_id: 1,
          news_alerts: true,
          disclosure_alerts: true,
          chart_alerts: true,
          price_alerts: true,
          weekly_reports: false,
          error_alerts: false,
          is_active: true,
        };
      }
    },
    retry: false, // 에러 시 재시도 안함
  });

  // 구독 설정 저장
  const saveSubscriptionMutation = useMutation({
    mutationFn: async (data: TelegramSubscription) => {
      const response = await telegramChannelApi.saveSubscription(userId, data);
      return response.data;
    },
    onSuccess: () => {
      toast.success('텔레그램 알림 설정이 저장되었습니다!');
    },
    onError: (error) => {
      console.error('텔레그램 설정 저장 실패:', error);
      toast.error('설정 저장에 실패했습니다. 다시 시도해주세요.');
    },
  });

  // 🆕 환영 메시지 전송 mutation
  const sendWelcomeMutation = useMutation({
    mutationFn: () => telegramChannelApi.sendSimpleWelcomeMessage(userId),
    onSuccess: (data) => {
      toast.success('🎉 환영 메시지가 텔레그램 채널에 전송되었습니다!');
      console.log('환영 메시지 전송 성공:', data);
    },
    onError: (error) => {
      toast.error('❌ 환영 메시지 전송에 실패했습니다.');
      console.error('환영 메시지 전송 실패:', error);
    }
  });

  // 🆕 테스트 알림 전송 mutation (하나로 통합)
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

  // 🆕 채널 참여 핸들러 수정 - 자동 환영 메시지 전송
  const handleChannelJoin = () => {
    if (channelData?.channel_url) {
      // 채널 URL로 이동
      window.open(channelData.channel_url, '_blank');
      
      // 🆕 자동으로 환영 메시지 전송
      sendWelcomeMutation.mutate();
      
      toast.success('📱 텔레그램 채널로 이동합니다!');
    } else {
      toast.error('❌ 채널 정보를 찾을 수 없습니다.');
    }
  };

  // 🆕 테스트 알림 전송 함수 (봇이 채널에 글을 쓰는지 확인용)
  const handleSendTestNotification = () => {
    if (!userId) {
      toast.error('사용자 ID를 찾을 수 없습니다.');
      return;
    }
    sendTestNotificationMutation.mutate();
  };

  // 채널 정보 설정
  useEffect(() => {
    if (channelData) {
      setChannel(channelData);
    }
  }, [channelData]);

  // 구독 정보 설정
  useEffect(() => {
    if (subscriptionData) {
      setSubscription(subscriptionData);
    }
  }, [subscriptionData]);

  const handleSave = () => {
    if (!userId) {
      toast.error('사용자 정보를 찾을 수 없습니다.');
      return;
    }
    
    saveSubscriptionMutation.mutate(subscription);
  };

  const handleNotificationToggle = (key: keyof Omit<TelegramSubscription, 'user_id' | 'channel_id' | 'is_active'>) => {
    setSubscription(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  // 🆕 간단한 채널 참여 핸들러
  const handleSimpleChannelJoin = () => {
    if (channelData?.channel_url) {
      // 채널 URL로 이동
      window.open(channelData.channel_url, '_blank');
      
      // 🆕 간단한 환영 메시지 전송
      sendWelcomeMutation.mutate();
      
      toast.success('📱 텔레그램 채널로 이동합니다!');
    } else {
      toast.error('❌ 채널 정보를 찾을 수 없습니다.');
    }
  };

  // 🆕 간단한 테스트 알림 전송 함수
  const handleSendSimpleTestNotification = () => {
    sendTestNotificationMutation.mutate();
  };

  // 🆕 사용자 정의 알림 전송 함수
  const handleSendCustomNotification = () => {
    const customNotification = {
      type: 'general',
      message: `🧪 사용자 정의 테스트 알림\n\n안녕하세요! HyperAsset 텔레그램 알림 테스트입니다.\n\n✅ 이 메시지가 보이면 채널 연결이 정상입니다!`
    };
    
    // This mutation is no longer used for simple custom notifications
    // as the sendSimpleNotificationMutation was removed.
    // If you need to send a custom notification, you'd need to re-add it or
    // implement a new mutation for that specific use case.
    // For now, we'll keep the function but it won't do anything.
    console.warn("handleSendCustomNotification is deprecated as sendSimpleNotificationMutation is removed.");
  };

  // 로딩 상태 확인
  const isDataLoading = isLoadingChannel || isLoadingSubscription;

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
            {(channelError || subscriptionError) && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  텔레그램 설정을 불러오는 중 오류가 발생했습니다. 기본 설정으로 표시됩니다.
                </AlertDescription>
              </Alert>
            )}

            {/* 디버그 정보 */}
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                🧪 디버그 모드: User ID: {userId} | 채널: {channelData?.channel_name || channel?.channel_name} | 구독 활성화: {subscriptionData?.is_active !== undefined ? (subscriptionData.is_active ? '예' : '아니오') : (subscription.is_active ? '예' : '아니오')} | 로딩: {isDataLoading ? '예' : '아니오'}
              </AlertDescription>
            </Alert>

            {/* 상세 디버그 정보 */}
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                📊 상세 정보: API 채널 데이터: {channelData ? '있음' : '없음'} | API 구독 데이터: {subscriptionData ? '있음' : '없음'} | 에러: {channelError || subscriptionError ? '있음' : '없음'}
              </AlertDescription>
            </Alert>

            {/* 텔레그램 채널 구독 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-blue-600" />
                  텔레그램 알림
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
                  
                  <Button 
                    onClick={handleChannelJoin}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 text-lg"
                    size="lg"
                  >
                    📱 텔레그램 알림으로 이동
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* 🆕 테스트 알림 버튼 (하나로 통합) */}
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

            {/* 알림 유형 설정 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-blue-600" />
                  알림 유형 설정
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-4">
                  {/* 뉴스 알림 */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <FileText className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <Label className="text-base font-medium">뉴스 알림</Label>
                        <p className="text-sm text-gray-500">중요한 주식 뉴스를 실시간으로 받아보세요</p>
                      </div>
                    </div>
                    <Switch
                      checked={subscription.news_alerts}
                      onCheckedChange={() => handleNotificationToggle('news_alerts')}
                    />
                  </div>

                  {/* 공시 알림 */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-100 rounded-lg">
                        <MessageSquare className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <Label className="text-base font-medium">공시 알림</Label>
                        <p className="text-sm text-gray-500">기업 공시 정보를 빠르게 확인하세요</p>
                      </div>
                    </div>
                    <Switch
                      checked={subscription.disclosure_alerts}
                      onCheckedChange={() => handleNotificationToggle('disclosure_alerts')}
                    />
                  </div>

                  {/* 차트 알림 */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-purple-100 rounded-lg">
                        <BarChart3 className="h-5 w-5 text-purple-600" />
                      </div>
                      <div>
                        <Label className="text-base font-medium">차트 패턴 알림</Label>
                        <p className="text-sm text-gray-500">중요한 차트 패턴을 놓치지 마세요</p>
                      </div>
                    </div>
                    <Switch
                      checked={subscription.chart_alerts}
                      onCheckedChange={() => handleNotificationToggle('chart_alerts')}
                    />
                  </div>

                  {/* 가격 알림 */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-orange-100 rounded-lg">
                        <TrendingUp className="h-5 w-5 text-orange-600" />
                      </div>
                      <div>
                        <Label className="text-base font-medium">가격 변동 알림</Label>
                        <p className="text-sm text-gray-500">주요 종목의 가격 변동을 실시간으로</p>
                      </div>
                    </div>
                    <Switch
                      checked={subscription.price_alerts}
                      onCheckedChange={() => handleNotificationToggle('price_alerts')}
                    />
                  </div>

                  {/* 주간 리포트 */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-indigo-100 rounded-lg">
                        <Settings className="h-5 w-5 text-indigo-600" />
                      </div>
                      <div>
                        <Label className="text-base font-medium">주간 리포트</Label>
                        <p className="text-sm text-gray-500">주간 주식 시장 요약 리포트</p>
                      </div>
                    </div>
                    <Switch
                      checked={subscription.weekly_reports}
                      onCheckedChange={() => handleNotificationToggle('weekly_reports')}
                    />
                  </div>

                  {/* 에러 알림 */}
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-red-100 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-red-600" />
                      </div>
                      <div>
                        <Label className="text-base font-medium">시스템 에러 알림</Label>
                        <p className="text-sm text-gray-500">중요한 시스템 이슈 알림</p>
                      </div>
                    </div>
                    <Switch
                      checked={subscription.error_alerts}
                      onCheckedChange={() => handleNotificationToggle('error_alerts')}
                    />
                  </div>
                </div>

                {/* 설정 저장 버튼 */}
                <div className="mt-8 pt-6 border-t border-gray-200">
                  <div className="flex justify-end">
                    <Button 
                      onClick={handleSave} 
                      disabled={saveSubscriptionMutation.isPending}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-8"
                    >
                      {saveSubscriptionMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          저장 중...
                        </>
                      ) : (
                        '설정 저장'
                      )}
                    </Button>
                  </div>
                </div>
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