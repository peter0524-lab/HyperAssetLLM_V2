import React, { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import { 
  ArrowRight, 
  User, 
  TrendingUp, 
  BarChart3, 
  FileText, 
  Calendar,
  Loader2,
  Settings,
  Play,
  Eye,
  Monitor,
  Terminal,
  Bell
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api, userStorage, UserConfig } from "@/lib/api";
import TradingViewChart from "@/components/TradingViewChart";
import ServiceMonitor from "@/components/ServiceMonitor";
const Dashboard = () => {
  const navigate = useNavigate();
  const [userId, setUserId] = useState<string>('');
  const [selectedStock, setSelectedStock] = useState<{
    code: string;
    name: string;
    sector?: string;
  } | null>(null);
  const [viewMode, setViewMode] = useState<'dashboard' | 'monitor'>('dashboard');
  const [telegramMessageDisclosure, setTelegramMessageDisclosure] = useState<string | null>(null); // 이름 변경
  const [telegramMessageNews, setTelegramMessageNews] = useState<string | null>(null); // 추가
  const [telegramMessageChart, setTelegramMessageChart] = useState<string | null>(null); // 추가
  const [telegramMessageFlow, setTelegramMessageFlow] = useState<string | null>(null); // 추가
  const [telegramMessageReport, setTelegramMessageReport] = useState<string | null>(null); // 추가
  
  // 분석 결과 관리를 위한 상태
  const [analysisResults, setAnalysisResults] = useState<any>({
    news: [],
    chart: [],
    disclosure: [],
    flow: [],
    report: []
  });
  const [selectedAnalysisTab, setSelectedAnalysisTab] = useState<'news' | 'chart' | 'disclosure' | 'flow' | 'report'>('news');

  useEffect(() => {
    // 사용자 ID 확인
    let currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      // 사용자 ID가 없으면 프로필 페이지로 리다이렉트
      navigate('/profile');
      return;
    }
    setUserId(currentUserId);


  }, [navigate] ); // navigate와 telegramMessage가 변경될 때마다 이 훅이 실행됩니다.

 ////////////////////////////////////////////////////////////////////////////////////////////
  useEffect(() => {
    if (telegramMessageDisclosure) { // 기존 telegramMessage 대신 telegramMessageDisclosure 사용
      console.log('Updated telegramMessageDisclosure state in useEffect:', telegramMessageDisclosure);
    }
    if (telegramMessageNews) {
      console.log('Updated telegramMessageNews state in useEffect:', telegramMessageNews);
    }
    if (telegramMessageChart) {
      console.log('Updated telegramMessageChart state in useEffect:', telegramMessageChart);
    }
    if (telegramMessageFlow) {
      console.log('Updated telegramMessageFlow state in useEffect:', telegramMessageFlow);
    }
    if (telegramMessageReport) {
      console.log('Updated telegramMessageReport state in useEffect:', telegramMessageReport);
    }

    // 디버깅 목적으로 setTelegramMessage를 window 객체에 노출 (개발 환경에서만 사용 권장)
    (window as any).setTelegramMessageDisclosure = setTelegramMessageDisclosure; // 이름 변경
    (window as any).setTelegramMessageNews = setTelegramMessageNews; // 추가
    (window as any).setTelegramMessageChart = setTelegramMessageChart; // 추가
    (window as any).setTelegramMessageFlow = setTelegramMessageFlow; // 추가
    (window as any).setTelegramMessageReport = setTelegramMessageReport; // 추가

    // 디버깅 목적으로 telegramMessage 상태 자체를 window 객체에 노출
    (window as any).telegramMessageStateDisclosure = telegramMessageDisclosure; // 이름 변경
    (window as any).telegramMessageStateNews = telegramMessageNews; // 추가
    (window as any).telegramMessageStateChart = telegramMessageChart; // 추가
    (window as any).telegramMessageStateFlow = telegramMessageFlow; // 추가
    (window as any).telegramMessageStateReport = telegramMessageReport; // 추가

  }, [navigate, telegramMessageDisclosure, telegramMessageNews, telegramMessageChart, telegramMessageFlow, telegramMessageReport]); // 모든 관련 상태를 의존성 배열에 추가
///////////////////////////////////////////////////////////////////////////////////////////////////////////////
  // 사용자 설정 조회
  const { data: userConfig, isLoading: isLoadingConfig, error: configError } = useQuery({
    queryKey: ['userConfig', userId],
    queryFn: () => api.getUserConfig(userId),
    enabled: !!userId,
    retry: 1,
  });

  // 🔥 사용자 활성화 서비스 조회 추가
  const { data: userWantedServices, isLoading: isLoadingServices } = useQuery({
    queryKey: ['userWantedServices', userId],
    queryFn: () => api.getUserWantedServices(userId),
    enabled: !!userId,
    retry: 1,
  });

  // 전체 분석 실행
  const executeAnalysisMutation = useMutation({
    mutationFn: api.executeAllAnalysis,
    onSuccess: (data) => {
      toast.success("🎉 전체 분석이 완료되었습니다!");
      console.log('분석 결과:', data);
    },
    onError: (error) => {
      toast.error("❌ 분석 실행 중 오류가 발생했습니다.");
      console.error('분석 오류:', error);
    },
  });

  // 개별 분석 실행
  const executeNewsMutation = useMutation({ 
    mutationFn: api.executeNewsAnalysis,
    onSuccess: (data) => {
      setAnalysisResults(prev => ({
        ...prev,
        news: data.data || []
      }));
      setSelectedAnalysisTab('news');
      toast.success("📰 뉴스 분석이 완료되었습니다!");
      if (data.data && data.data.telegram_message) {
        setTelegramMessageNews(data.data.telegram_message);
      } else {
        setTelegramMessageNews(null);
      }
    },
    onError: (error) => {
      toast.error("❌ 뉴스 분석 실행 중 오류가 발생했습니다.");
      setTelegramMessageNews(null);
    }
  });
  
 const executeDisclosureMutation = useMutation({ 
    mutationFn: api.executeDisclosureAnalysis,
    onSuccess: (data) => {
      setAnalysisResults(prev => ({
        ...prev,
        disclosure: data.data || []
      }));
      setSelectedAnalysisTab('disclosure');
      toast.success("📋 공시 분석이 완료되었습니다!");
      if (data.data && data.data.telegram_message) {
        console.log('Value being passed to setTelegramMessageDisclosure:', data.data.telegram_message);
        setTelegramMessageDisclosure(data.data.telegram_message);
      } else {
        console.log('telegram_message not found in data.data or data.data is null/undefined for disclosure.');
        setTelegramMessageDisclosure(null);
      }
    },
    onError: (error) => {
      toast.error("❌ 공시 분석 실행 중 오류가 발생했습니다.");
      setTelegramMessageDisclosure(null);
    }
  });
  
  const executeChartMutation = useMutation({ 
    mutationFn: api.executeChartAnalysis,
    onSuccess: (data) => {
      setAnalysisResults(prev => ({
        ...prev,
        chart: data.data || []
      }));
      setSelectedAnalysisTab('chart');
      toast.success("📈 차트 분석이 완료되었습니다!");
      if (data.data && data.data.telegram_message) {
        setTelegramMessageChart(data.data.telegram_message);
      } else {
        setTelegramMessageChart(null);
      }
    },
    onError: (error) => {
      toast.error("❌ 차트 분석 실행 중 오류가 발생했습니다.");
      setTelegramMessageChart(null);
    }
  });
  
  const executeReportMutation = useMutation({ 
    mutationFn: api.executeReportAnalysis,
    onSuccess: (data) => {
      setAnalysisResults(prev => ({
        ...prev,
        report: data.data || []
      }));
      setSelectedAnalysisTab('report');
      toast.success("📊 리포트 분석이 완료되었습니다!");
      if (data.data && data.data.telegram_message) {
        setTelegramMessageReport(data.data.telegram_message);
      } else {
        setTelegramMessageReport(null);
      }
    },
    onError: (error) => {
      toast.error("❌ 리포트 분석 실행 중 오류가 발생했습니다.");
      setTelegramMessageReport(null);
    }
  });
  
  const executeFlowMutation = useMutation({ 
    mutationFn: api.executeFlowAnalysis,
    onSuccess: (data) => {
      // 응답 데이터 구조 로깅
      console.log("[Flow Analysis] Response structure:", {
        hasData: !!data?.data,
        dataLength: data?.data?.length,
        hasTelegramMessage: !!data?.data?.telegram_message,
        periods: Object.keys(data?.data?.[0]?.periods || {})
      });

      // 데이터 설정
      setAnalysisResults(prev => ({
        ...prev,
        flow: data.data || []
      }));
      setSelectedAnalysisTab('flow');
      
      // 텔레그램 메시지 처리
      if (data.data?.telegram_message) {
        console.log("[Flow Analysis] Telegram message received:", {
          length: data.data.telegram_message.length,
          preview: data.data.telegram_message.substring(0, 100) + "..."
        });
        setTelegramMessageFlow(data.data.telegram_message);
        toast.success("💰 수급 분석 완료 - 텔레그램 알림이 전송되었습니다");
      } else {
        console.log("[Flow Analysis] No telegram message in response");
        setTelegramMessageFlow(null);
        toast.success("💰 수급 분석이 완료되었습니다!");
      }
    },
    onError: (error: any) => {
      // 상세 오류 정보 로깅
      console.error("[Flow Analysis] Error details:", {
        name: error.name,
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data
      });
      
      toast.error("❌ 수급 분석 실행 중 오류가 발생했습니다.");
      setTelegramMessageFlow(null);
    }
  });

  if (isLoadingConfig || isLoadingServices) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-gray-600">
              {isLoadingConfig ? "사용자 설정을 불러오는 중..." : "서비스 설정을 불러오는 중..."}
            </p>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  if (configError) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <Alert className="max-w-2xl mx-auto">
            <AlertDescription>
              사용자 설정을 불러올 수 없습니다. 프로필을 먼저 설정해주세요.
              <Button 
                onClick={() => navigate('/profile')} 
                className="ml-4"
                size="sm"
              >
                프로필 설정하기
              </Button>
            </AlertDescription>
          </Alert>
        </div>
        <Footer />
      </div>
    );
  }

  const mainStock = userConfig?.stocks?.[0]?.code || "005930";
  
  // 종목 변경 핸들러
  const handleStockChange = (stock: { code: string; name: string; sector?: string }) => {
    setSelectedStock(stock);
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-gray-50 to-white py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <div className="flex justify-center items-center gap-4 mb-6">
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900">
                {viewMode === 'dashboard' ? '📊 투자 대시보드' : '🖥️ 서비스 모니터'}
            </h1>
              
              {/* 뷰 모드 전환 버튼 */}
              <div className="flex bg-gray-100 rounded-lg p-1">
                <Button
                  variant={viewMode === 'dashboard' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('dashboard')}
                  className="px-4"
                >
                  <BarChart3 className="h-4 w-4 mr-2" />
                  대시보드
                </Button>
                <Button
                  variant={viewMode === 'monitor' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('monitor')}
                  className="px-4"
                >
                  <Terminal className="h-4 w-4 mr-2" />
                  서비스 모니터
                </Button>
              </div>
            </div>
            
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              {viewMode === 'dashboard' 
                ? 'AI 기반 주식 분석으로 스마트한 투자 결정을 내리세요'
                : '실시간 마이크로서비스 상태를 모니터링하고 관리하세요'
              }
            </p>
          </div>

          {/* 사용자 정보 카드 */}
          {userConfig && (
            <div className="glass-card max-w-4xl mx-auto p-6 mb-8">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                    <User className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      {userConfig.profile?.username || '사용자'}님
                    </h3>
                    <p className="text-gray-600">
                      관심 종목: {userConfig.stocks?.length || 0}개 |
                      모델: {userConfig.model_type || 'hyperclova'}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button 
                    onClick={() => navigate('/telegram-settings')}
                    className="bg-[#0088cc] hover:bg-[#0077b3] text-white border-0 shadow-md hover:shadow-lg transition-all duration-200"
                    style={{
                      background: 'linear-gradient(135deg, #0088cc 0%, #0077b3 100%)',
                    }}
                  >
                    <svg 
                      className="h-4 w-4 mr-2" 
                      viewBox="0 0 24 24" 
                      fill="currentColor"
                    >
                      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.18-.357.295-.6.295-.002 0-.003 0-.005 0l.213-3.054 5.56-5.022c.24-.213-.054-.334-.373-.121l-6.869 4.326-2.96-.924c-.64-.203-.658-.64.135-.954l11.566-4.458c.538-.196 1.006.128.832.941z"/>
                    </svg>
                    텔레그램 알림
                  </Button>
                  <Button variant="outline" onClick={() => navigate('/profile')}>
                    <Settings className="h-4 w-4 mr-2" />
                    프로필 수정
                  </Button>
                  <Button variant="outline" onClick={() => navigate('/stocks')}>
                    <TrendingUp className="h-4 w-4 mr-2" />
                    종목 관리
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          {viewMode === 'monitor' ? (
            // 서비스 모니터 뷰
            <ServiceMonitor />
          ) : (
            // 기존 대시보드 뷰
            <div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* 왼쪽 컬럼: 빠른 실행 & 실시간 차트 */}
            <div className="lg:col-span-1 space-y-6">
              
              {/* 빠른 분석 실행 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Play className="h-5 w-5 text-primary" />
                    빠른 분석 실행
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Button 
                    onClick={() => executeAnalysisMutation.mutate()}
                    disabled={executeAnalysisMutation.isPending}
                    className="w-full bg-primary hover:bg-primary/90 text-white py-3"
                    size="lg"
                  >
                    {executeAnalysisMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        분석 실행 중...
                      </>
                    ) : (
                      <>
                        🔍 전체 분석 실행
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                  
                  {/* 🔥 분석 실행 버튼들 */}
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeNewsMutation.mutate()}
                      disabled={executeNewsMutation.isPending}
                      className="flex flex-col items-center py-3 h-auto"
                    >
                      <span className="text-lg mb-1">📰</span>
                      <span className="text-xs">뉴스 즉시 실행해보기</span>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeChartMutation.mutate()}
                      disabled={executeChartMutation.isPending}
                      className="flex flex-col items-center py-3 h-auto"
                    >
                      <span className="text-lg mb-1">📈</span>
                      <span className="text-xs">차트 즉시 실행해보기</span>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeDisclosureMutation.mutate()}
                      disabled={executeDisclosureMutation.isPending}
                      className="flex flex-col items-center py-3 h-auto"
                    >
                      <span className="text-lg mb-1">📋</span>
                      <span className="text-xs">공시 즉시 실행해보기</span>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeFlowMutation.mutate()}
                      disabled={executeFlowMutation.isPending}
                      className="flex flex-col items-center py-3 h-auto"
                    >
                      <span className="text-lg mb-1">💰</span>
                      <span className="text-xs">수급 즉시 실행해보기</span>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeReportMutation.mutate()}
                      disabled={executeReportMutation.isPending}
                      className="flex flex-col items-center py-3 h-auto"
                    >
                      <span className="text-lg mb-1">📊</span>
                      <span className="text-xs">리포트 즉시 실행해보기</span>
                    </Button>
                  </div>

                  <Button 
                    onClick={() => navigate('/results')}
                    variant="outline"
                    className="w-full"
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    분석 결과 보기
                  </Button>
                </CardContent>
              </Card>

              {/* 실시간 차트 (왼쪽으로 이동) */}
              <Card className="h-[400px]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    실시간 차트 - {selectedStock ? `${selectedStock.name} (${selectedStock.code})` : mainStock}
                  </CardTitle>
                </CardHeader>
                <CardContent className="h-[320px]">
                  <TradingViewChart 
                    symbol={mainStock} 
                    onStockChange={handleStockChange}
                  />
                </CardContent>
              </Card>
            </div>

            {/* 오른쪽 컬럼: 분석 결과 */}
            <div className="lg:col-span-2">
              <Card className="h-[600px]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    분석 결과
                  </CardTitle>
                </CardHeader>
                <CardContent className="h-[520px] overflow-y-auto">
                  <div data-analysis-results>
                    <AnalysisResults 
                      results={analysisResults}
                      selectedTab={selectedAnalysisTab}
                      onTabChange={setSelectedAnalysisTab}
                      isLoading={executeNewsMutation.isPending || executeChartMutation.isPending || executeDisclosureMutation.isPending || executeFlowMutation.isPending || executeReportMutation.isPending}
                      telegramMessageDisclosure={telegramMessageDisclosure} // 이름 변경
                      telegramMessageNews={telegramMessageNews} // 추가
                      telegramMessageChart={telegramMessageChart} // 추가
                      telegramMessageFlow={telegramMessageFlow} // 추가
                      telegramMessageReport={telegramMessageReport} // 추가
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* 개발 예정 기능들 */}
          <DevelopmentFeatures />
          </div>
        )}
        </div>
      </section>

      <Footer />
    </div>
  );
};

// 개발 예정 기능 컴포넌트
const DevelopmentFeatures = () => {
  const features = [
    {
      icon: <Calendar className="h-8 w-8 text-orange-500" />,
      title: "이슈 스케줄러",
      description: "유상증자, 실적발표 등 중요 일정을 사전에 알려드립니다.",
      eta: "2024년 2분기",
      comingSoon: true
    },
    {
      icon: <FileText className="h-8 w-8 text-blue-500" />,
      title: "사업보고서 요약",
      description: "AI가 사업보고서를 투자 관점에서 요약해드립니다.",
      eta: "2024년 2분기",
      comingSoon: true
    },
    {
      icon: <TrendingUp className="h-8 w-8 text-green-500" />,
      title: "주가 원인 분석",
      description: "차트를 클릭하면 해당 시점의 주가 변동 원인을 분석합니다.",
      eta: "2024년 3분기",
      comingSoon: true
    }
  ];

  return (
    <div className="mt-16">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">🚀 개발 예정 기능</h2>
        <p className="text-lg text-gray-600">더욱 강력한 기능들이 준비되고 있습니다</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {features.map((feature, index) => (
          <Card key={index} className="relative overflow-hidden hover:shadow-lg transition-all duration-300">
            {feature.comingSoon && (
              <div className="absolute top-4 right-4">
                <Badge variant="secondary" className="bg-orange-100 text-orange-700">
                  개발 중
                </Badge>
              </div>
            )}
            <CardContent className="p-6">
              <div className="mb-4">{feature.icon}</div>
              <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-gray-600 mb-4 leading-relaxed">
                {feature.description}
              </p>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Calendar className="h-4 w-4" />
                <span>{feature.eta}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// 분석 결과 컴포넌트
interface AnalysisResultsProps {
  results: any;
  selectedTab: 'news' | 'chart' | 'disclosure' | 'flow' | 'report';
  onTabChange: (tab: 'news' | 'chart' | 'disclosure' | 'flow' | 'report') => void;
  isLoading: boolean;
  telegramMessageDisclosure?: string | null; // 기존, 이제 명시적으로 이름 지정
  telegramMessageNews?: string | null; // 새로 추가
  telegramMessageChart?: string | null; // 새로 추가
  telegramMessageFlow?: string | null; // 새로 추가
  telegramMessageReport?: string | null; // 새로 추가
}

const AnalysisResults = ({ results, selectedTab, onTabChange, isLoading,
  telegramMessageDisclosure, telegramMessageNews, telegramMessageChart,
  telegramMessageFlow, telegramMessageReport
}: AnalysisResultsProps) => {
  
  const tabs = [
    { id: 'news', label: '뉴스 분석', icon: '📰' },
    { id: 'chart', label: '차트 분석', icon: '📈' },
    { id: 'disclosure', label: '공시 분석', icon: '📋' },
    { id: 'flow', label: '수급 분석', icon: '💰' },
    { id: 'report', label: '리포트 분석', icon: '📊' },
  ];

  // 탭 변경 핸들러
  const handleTabChange = (tabId: string) => {
    onTabChange(tabId as any);
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-50';
      case 'negative': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const renderNewsResults = () => (
    <div className="space-y-4">
      {results.news.length > 0 ? (
        results.news.map((item: any, index: number) => (
          <div key={index} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
              <h4 className="font-medium text-gray-900">{item.title}</h4>
              <div className="flex gap-2">
                <Badge className={getSentimentColor(item.sentiment)}>
                  {item.sentiment === 'positive' ? '긍정' : '부정'}
                </Badge>
                <Badge className={getImpactColor(item.impact_score)}>
                  {item.impact_score > 0.7 ? '높음' : item.impact_score > 0.4 ? '보통' : '낮음'}
                </Badge>
              </div>
            </div>
            <p className="text-gray-600 text-sm mb-2">{item.summary}</p>
            <p className="text-xs text-gray-500">{item.created_at}</p>
          </div>
        ))
      ) : (
        selectedTab === 'news' && telegramMessageNews ? (
          <Alert className="mt-4">
              <Bell className="h-4 w-4" />
              <AlertDescription className="whitespace-pre-line text-sm text-gray-800">
                <div dangerouslySetInnerHTML={{ __html: telegramMessageNews }} />
              </AlertDescription>
          </Alert>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>뉴스 분석 결과가 없습니다.</p>
            <p className="text-sm mt-2">왼쪽의 "뉴스 즉시 실행해보기" 버튼을 클릭해보세요.</p>
          </div>
        )
      )}
    </div>
  );

  const renderChartResults = () => (
    <div className="space-y-4">
      {results.chart.length > 0 ? (
        results.chart.map((item: any, index: number) => (
          <div key={index} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-medium text-gray-900">차트 분석</h4>
              <Badge variant="outline">{item.date}</Badge>
            </div>
            <div className="space-y-2 text-sm">
              {item.golden_cross && <p className="text-green-600">✓ 골든크로스</p>}
              {item.dead_cross && <p className="text-red-600">✗ 데드크로스</p>}
              {item.bollinger_touch && <p className="text-blue-600">📊 볼린저 밴드 터치</p>}
              {item.rsi_condition && <p className="text-orange-600">📈 RSI 조건</p>}
              {item.volume_surge && <p className="text-purple-600">📊 거래량 급증</p>}
            </div>
            <p className="text-xs text-gray-500 mt-2">종가: {item.close_price?.toLocaleString()}원</p>
          </div>
        ))
      ) : (
        selectedTab === 'chart' && telegramMessageChart ? (
          <Alert className="mt-4">
              <Bell className="h-4 w-4" />
              <AlertDescription className="whitespace-pre-line text-sm text-gray-800">
                <div dangerouslySetInnerHTML={{ __html: telegramMessageChart }} />
              </AlertDescription>
          </Alert>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>차트 분석 결과가 없습니다.</p>
            <p className="text-sm mt-2">왼쪽의 "차트 즉시 실행해보기" 버튼을 클릭해보세요.</p>
          </div>
        )
      )}
    </div>
  );

  const renderDisclosureResults = () => (
    <div className="space-y-4">
      {results.disclosure.length > 0 ? (
        results.disclosure.map((item: any, index: number) => (
          <div key={index} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
              <h4 className="font-medium text-gray-900">{item.report_nm}</h4>
              <Badge className={getSentimentColor(item.sentiment)}>
                {item.sentiment === 'positive' ? '긍정' : '부정'}
              </Badge>
            </div>
            <p className="text-gray-600 text-sm mb-2">{item.summary}</p>
            <p className="text-xs text-gray-500">{item.rcept_dt}</p>
          </div>
        ))
        ) : (
            selectedTab === 'disclosure' && telegramMessageDisclosure ? ( // 현재 탭이 'disclosure'이고 telegramMessage가 있을 때만 Alert 표시
              <Alert className="mt-4"> {/* style={{ backgroundColor: 'lightblue', border: '2px solid blue' }}는 제거했습니다. */}
                  <Bell className="h-4 w-4" />
                  <AlertDescription className="whitespace-pre-line text-sm text-gray-800">
                    <div dangerouslySetInnerHTML={{ __html: telegramMessageDisclosure }} />
                  </AlertDescription>
              </Alert>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <p>공시 분석 결과가 없습니다.</p>
          <p className="text-sm mt-2">왼쪽의 "공시 즉시 실행해보기" 버튼을 클릭해보세요.</p>
        </div>
      ))}
    </div>
  );

  const renderFlowResults = () => (
    <div className="space-y-4">
      {results.flow.length > 0 ? (
        results.flow.map((item: any, index: number) => (
          <div key={index} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-medium text-gray-900">수급 분석 - {item.stock_code}</h4>
              <Badge className="bg-blue-100 text-blue-700">
                분석 완료
              </Badge>
            </div>
            
            {/* 기간별 분석 결과 */}
            <div className="space-y-3">
              {Object.entries(item.periods || {}).map(([periodName, periodData]: [string, any]) => (
                <div key={periodName} className="border-l-4 border-blue-200 pl-3">
                  <h5 className="font-medium text-sm text-gray-700 mb-2">{periodName} 분석</h5>
                  
                  {periodData.error ? (
                    <p className="text-red-500 text-sm">{periodData.error}</p>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
                      {/* 기관 수급 */}
                      <div className="bg-gray-50 p-2 rounded">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-gray-600">기관</span>
                          <Badge className={`text-xs ${periodData.inst_direction === '매수' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {periodData.inst_direction}
                          </Badge>
                        </div>
                        <p className={`font-medium ${periodData.avg_inst_net > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {periodData.avg_inst_net?.toLocaleString()}주
                        </p>
                        <p className="text-xs text-gray-500">강도: {periodData.inst_strength}</p>
                      </div>
                      
                      {/* 외국인 수급 */}
                      <div className="bg-gray-50 p-2 rounded">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-gray-600">외국인</span>
                          <Badge className={`text-xs ${periodData.foreign_direction === '매수' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {periodData.foreign_direction}
                          </Badge>
                        </div>
                        <p className={`font-medium ${periodData.avg_foreign_net > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {periodData.avg_foreign_net?.toLocaleString()}주
                        </p>
                        <p className="text-xs text-gray-500">강도: {periodData.foreign_strength}</p>
                      </div>
                      
                      {/* 개인 수급 */}
                      <div className="bg-gray-50 p-2 rounded">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-gray-600">개인</span>
                          <Badge className={`text-xs ${periodData.individ_direction === '매수' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {periodData.individ_direction}
                          </Badge>
                        </div>
                        <p className={`font-medium ${periodData.avg_individ_net > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {periodData.avg_individ_net?.toLocaleString()}주
                        </p>
                        <p className="text-xs text-gray-500">강도: {periodData.individ_strength}</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            
            {/* 분석 정보 */}
            <div className="mt-3 pt-3 border-t text-xs text-gray-500">
              <p>데이터 기간: {item.periods?.['3일']?.earliest_date || 'N/A'} ~ {item.periods?.['3일']?.latest_date || 'N/A'}</p>
            </div>
          </div>
        ))
      ) : (
        selectedTab === 'flow' && telegramMessageFlow ? (
          <Alert className="mt-4">
              <Bell className="h-4 w-4" />
              <AlertDescription className="whitespace-pre-line text-sm text-gray-800">
                <div dangerouslySetInnerHTML={{ __html: telegramMessageFlow }} />
              </AlertDescription>
          </Alert>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>수급 분석 결과가 없습니다.</p>
            <p className="text-sm mt-2">왼쪽의 "수급 즉시 실행해보기" 버튼을 클릭해보세요.</p>
          </div>
        )
      )}
    </div>
  );

  const renderReportResults = () => (
    <div className="space-y-4">
      {results.report.length > 0 ? (
        results.report.map((item: any, index: number) => (
          <div key={index} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
              <h4 className="font-medium text-gray-900">리포트 분석</h4>
              <Badge className={item.recommendation === '매수' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                  {item.recommendation}
                </Badge>
                {item.target_price && (
                  <Badge variant="outline">목표가: {item.target_price?.toLocaleString()}원</Badge>
                )}
            </div>
            <p className="text-gray-600 text-sm mb-2">{item.summary}</p>
            <p className="text-xs text-gray-500">{item.report_date}</p>
          </div>
        ))
      ) : (
        selectedTab === 'report' && telegramMessageReport ? (
          <Alert className="mt-4">
              <Bell className="h-4 w-4" />
              <AlertDescription className="whitespace-pre-line text-sm text-gray-800">
                <div dangerouslySetInnerHTML={{ __html: telegramMessageReport }} />
              </AlertDescription>
          </Alert>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>리포트 분석 결과가 없습니다.</p>
            <p className="text-sm mt-2">왼쪽의 "리포트 즉시 실행해보기" 버튼을 클릭해보세요.</p>
          </div>
        )
      )}
    </div>
  ); // <-- 이 닫는 괄호가 중요합니다.

  if (isLoading) { // 이 if 블록은 renderReportResults 함수 외부에 있어야 합니다.
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-gray-600">분석 실행 중...</p>
          <p className="text-sm text-gray-500 mt-2">잠시만 기다려주세요</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      {/* 탭 네비게이션 */}
      <div className="flex space-x-1 mb-4 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            data-tab={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`px-3 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              selectedTab === tab.id
                ? 'bg-primary text-white'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <span className="mr-1">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>



      {/* 결과 내용 */}
      <div className="space-y-4">
        {selectedTab === 'news' && renderNewsResults()}
        {selectedTab === 'chart' && renderChartResults()}
        {selectedTab === 'disclosure' && renderDisclosureResults()}
        {selectedTab === 'flow' && renderFlowResults()}
        {selectedTab === 'report' && renderReportResults()}
      </div>
    </div>
  );
};

export default Dashboard; 