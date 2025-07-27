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
  Eye
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api, userStorage, UserConfig } from "@/lib/api";
import TradingViewChart from "@/components/TradingViewChart";

const Dashboard = () => {
  const navigate = useNavigate();
  const [userId, setUserId] = useState<string>('');
  const [selectedStock, setSelectedStock] = useState<{
    stock_code: string;
    company_name: string;
    sector: string;
  } | null>(null);

  useEffect(() => {
    // 사용자 ID 확인
    let currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      // 사용자 ID가 없으면 프로필 페이지로 리다이렉트
      navigate('/profile');
      return;
    }
    setUserId(currentUserId);
  }, [navigate]);

  // 사용자 설정 조회
  const { data: userConfig, isLoading: isLoadingConfig, error: configError } = useQuery({
    queryKey: ['userConfig', userId],
    queryFn: () => api.getUserConfig(userId),
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
  const executeNewsMutation = useMutation({ mutationFn: api.executeNewsAnalysis });
  const executeDisclosureMutation = useMutation({ mutationFn: api.executeDisclosureAnalysis });
  const executeChartMutation = useMutation({ mutationFn: api.executeChartAnalysis });
  const executeReportMutation = useMutation({ mutationFn: api.executeReportAnalysis });
  const executeFlowMutation = useMutation({ mutationFn: api.executeFlowAnalysis });

  if (isLoadingConfig) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-gray-600">사용자 설정을 불러오는 중...</p>
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

  const mainStock = userConfig?.stocks?.[0]?.stock_code || "005930";
  
  // 종목 변경 핸들러
  const handleStockChange = (stock: { stock_code: string; company_name: string; sector: string }) => {
    setSelectedStock(stock);
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-gray-50 to-white py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              📊 투자 대시보드
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              AI 기반 주식 분석으로 스마트한 투자 결정을 내리세요
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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* 왼쪽 컬럼: 빠른 실행 & 포트폴리오 */}
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
                  
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeNewsMutation.mutate()}
                      disabled={executeNewsMutation.isPending}
                    >
                      📰 뉴스
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeChartMutation.mutate()}
                      disabled={executeChartMutation.isPending}
                    >
                      📈 차트
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeDisclosureMutation.mutate()}
                      disabled={executeDisclosureMutation.isPending}
                    >
                      📋 공시
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => executeFlowMutation.mutate()}
                      disabled={executeFlowMutation.isPending}
                    >
                      💰 수급
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

              {/* 관심 종목 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5 text-primary" />
                      관심 종목
                    </span>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => navigate('/stocks')}
                    >
                      관리
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {userConfig?.stocks?.length > 0 ? (
                    <div className="space-y-3">
                      {userConfig.stocks.slice(0, 5).map((stock) => (
                        <div key={stock.stock_code} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="font-medium">{stock.company_name}</p>
                            <p className="text-sm text-gray-600">{stock.stock_code}</p>
                          </div>
                          <Badge variant={stock.is_active ? "default" : "secondary"}>
                            {stock.is_active ? "활성" : "비활성"}
                          </Badge>
                        </div>
                      ))}
                      {userConfig.stocks.length > 5 && (
                        <p className="text-sm text-gray-500 text-center">
                          +{userConfig.stocks.length - 5}개 더
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-600 mb-4">등록된 관심 종목이 없습니다</p>
                      <Button onClick={() => navigate('/stocks')}>
                        종목 추가하기
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* 오른쪽 컬럼: 실시간 차트 */}
            <div className="lg:col-span-2">
              <Card className="h-[600px]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    실시간 차트 - {selectedStock ? `${selectedStock.company_name} (${selectedStock.stock_code})` : mainStock}
                  </CardTitle>
                </CardHeader>
                <CardContent className="h-[520px]">
                  <TradingViewChart 
                    symbol={mainStock} 
                    onStockChange={handleStockChange}
                  />
                </CardContent>
              </Card>
            </div>
          </div>

          {/* 개발 예정 기능들 */}
          <DevelopmentFeatures />
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

export default Dashboard; 