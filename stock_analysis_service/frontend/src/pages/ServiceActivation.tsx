import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import { 
  Loader2, 
  Save, 
  ArrowRight,
  CheckCircle,
  Settings,
  Newspaper,
  FileText,
  BarChart3,
  TrendingUp,
  Zap,
  Server,
  Cpu
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api, userStorage } from "@/lib/api";

// 서비스 정의
const SERVICE_DEFINITIONS = [
  {
    key: "news_service",
    name: "뉴스 분석 서비스",
    description: "실시간 뉴스 모니터링 및 주가 영향도 분석",
    features: ["실시간 뉴스 수집", "AI 감정 분석", "주가 영향도 예측", "중요 뉴스 알림"],
    icon: <Newspaper className="h-8 w-8" />,
    color: "from-blue-500 to-cyan-500",
    port: 8001
  },
  {
    key: "disclosure_service", 
    name: "공시 분석 서비스",
    description: "기업 공시 자동 분석 및 핵심 정보 추출",
    features: ["공시 자동 수집", "핵심 내용 요약", "재무 영향 분석", "공시 알림"],
    icon: <FileText className="h-8 w-8" />,
    color: "from-green-500 to-emerald-500",
    port: 8002
  },
  {
    key: "report_service",
    name: "리포트 분석 서비스", 
    description: "증권사 리포트 분석 및 투자 의견 종합",
    features: ["리포트 수집", "목표가 분석", "투자 의견 추적", "애널리스트 컨센서스"],
    icon: <BarChart3 className="h-8 w-8" />,
    color: "from-purple-500 to-pink-500",
    port: 8004
  },
  {
    key: "chart_service",
    name: "차트 분석 서비스",
    description: "기술적 분석 및 차트 패턴 인식",
    features: ["기술 지표 분석", "차트 패턴 인식", "지지/저항 분석", "매매 신호 생성"],
    icon: <TrendingUp className="h-8 w-8" />,
    color: "from-orange-500 to-red-500",
    port: 8003
  },
  {
    key: "flow_service",
    name: "자금흐름 분석 서비스",
    description: "기관/외국인 자금 흐름 분석",
    features: ["자금 흐름 추적", "기관 매매 분석", "외국인 동향", "수급 분석"],
    icon: <Zap className="h-8 w-8" />,
    color: "from-yellow-500 to-orange-500",
    port: 8010
  }
];

const ServiceActivation = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState<string>('');
  const [selectedServices, setSelectedServices] = useState<Record<string, boolean>>({
    news_service: false,
    disclosure_service: false,
    report_service: false,
    chart_service: false,
    flow_service: false
  });
  const [activationPhase, setActivationPhase] = useState<'selection' | 'saving' | 'activating' | 'complete'>('selection');

  useEffect(() => {
    const currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      toast.error("사용자 정보를 찾을 수 없습니다. 다시 로그인해주세요.");
      navigate('/auth');
      return;
    }
    setUserId(currentUserId);
  }, [navigate]);

  // 서비스 토글 핸들러
  const handleServiceToggle = (serviceKey: string, enabled: boolean) => {
    setSelectedServices(prev => ({
      ...prev,
      [serviceKey]: enabled
    }));
  };

  // 서비스 설정 저장 및 활성화
  const activateServicesMutation = useMutation({
    mutationFn: async () => {
      setActivationPhase('saving');
      
             // 1. 서비스 설정 저장
       await api.createUserWantedServices(userId, {
         news_service: selectedServices.news_service,
         disclosure_service: selectedServices.disclosure_service,
         report_service: selectedServices.report_service,
         chart_service: selectedServices.chart_service,
         flow_service: selectedServices.flow_service
       });
      
      // 잠시 대기
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setActivationPhase('activating');
      
      // 2. 활성화된 서비스들 추출
      const activeServices = Object.entries(selectedServices)
        .filter(([_, enabled]) => enabled)
        .map(([key, _]) => key);
      
      if (activeServices.length > 0) {
        // 3. 서비스 활성화 (선택된 서비스들 + orchestrator 포함)
        const servicesWithOrchestrator = [...activeServices, 'orchestrator'];
        await api.activateSelectedServices(userId, servicesWithOrchestrator);
        
        // 활성화 진행 시뮬레이션
        await new Promise(resolve => setTimeout(resolve, 3000));
      }
      
      setActivationPhase('complete');
      
      return { activeServices };
    },
    onSuccess: (data) => {
      toast.success("🎉 모든 설정이 완료되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
      
      // 3초 후 대시보드로 이동
      setTimeout(() => {
        navigate('/dashboard');
      }, 3000);
    },
    onError: (error) => {
      toast.error("❌ 서비스 활성화 중 오류가 발생했습니다.");
      console.error('서비스 활성화 오류:', error);
      setActivationPhase('selection');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // 최소 하나의 서비스 선택 확인
    const hasSelectedService = Object.values(selectedServices).some(enabled => enabled);
    if (!hasSelectedService) {
      toast.error("최소 하나 이상의 서비스를 선택해주세요.");
      return;
    }

    activateServicesMutation.mutate();
  };

  // 선택된 서비스 개수 계산
  const selectedCount = Object.values(selectedServices).filter(Boolean).length;

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-gray-50 to-white py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full mb-6">
              <Settings className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              ⚡ 서비스 활성화
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              원하시는 분석 서비스를 선택하여 맞춤형 투자 인사이트를 받아보세요
            </p>
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto">
            
            {activationPhase === 'selection' && (
              <>
                {/* 서비스 선택 카드들 */}
                <form onSubmit={handleSubmit}>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
                    {SERVICE_DEFINITIONS.map((service) => (
                      <Card 
                        key={service.key}
                        className={`group hover:shadow-xl transition-all duration-300 hover:-translate-y-2 border-0 shadow-lg overflow-hidden ${
                          selectedServices[service.key] ? 'ring-2 ring-primary bg-primary/5' : ''
                        }`}
                      >
                        <CardHeader className="relative pb-4">
                          <div className={`inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r ${service.color} rounded-full mb-4 text-white`}>
                            {service.icon}
                          </div>
                          <CardTitle className="text-xl font-bold text-gray-900 mb-2">
                            {service.name}
                          </CardTitle>
                          <p className="text-gray-600 text-sm">
                            {service.description}
                          </p>
                          
                          {/* 포트 정보 */}
                          <div className="flex items-center gap-2 mt-2">
                            <Server className="h-4 w-4 text-gray-400" />
                            <span className="text-xs text-gray-500">Port: {service.port}</span>
                          </div>
                        </CardHeader>
                        
                        <CardContent className="pt-0">
                          {/* 기능 목록 */}
                          <div className="mb-6">
                            <h4 className="font-semibold text-gray-800 mb-3">주요 기능:</h4>
                            <div className="space-y-2">
                              {service.features.map((feature, index) => (
                                <div key={index} className="flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 bg-primary rounded-full"></div>
                                  <span className="text-sm text-gray-600">{feature}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                          
                          {/* 활성화 스위치 */}
                          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                            <Label htmlFor={service.key} className="font-medium text-gray-900">
                              서비스 활성화
                            </Label>
                            <Switch
                              id={service.key}
                              checked={selectedServices[service.key]}
                              onCheckedChange={(checked) => handleServiceToggle(service.key, checked)}
                            />
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  {/* 선택 요약 및 제출 */}
                  <Card className="shadow-lg">
                    <CardHeader className="text-center">
                      <CardTitle className="text-2xl flex items-center justify-center gap-2">
                        <Cpu className="h-6 w-6 text-primary" />
                        선택된 서비스: {selectedCount}개
                      </CardTitle>
                    </CardHeader>
                    
                    <CardContent className="space-y-6">
                      {selectedCount > 0 && (
                        <div className="bg-blue-50 p-4 rounded-lg">
                          <h4 className="font-semibold text-blue-900 mb-3">활성화될 서비스:</h4>
                          <div className="flex flex-wrap gap-2">
                            {SERVICE_DEFINITIONS
                              .filter(service => selectedServices[service.key])
                              .map(service => (
                                <span 
                                  key={service.key}
                                  className="px-3 py-1 bg-white text-blue-800 text-sm rounded-full border border-blue-200"
                                >
                                  {service.name}
                                </span>
                              ))
                            }
                          </div>
                        </div>
                      )}
                      
                      <Button
                        type="submit"
                        disabled={selectedCount === 0 || activateServicesMutation.isPending}
                        className="w-full bg-primary hover:bg-primary/90 py-4 text-lg"
                        size="lg"
                      >
                        <Save className="mr-2 h-5 w-5" />
                        서비스 활성화 시작 ({selectedCount}개)
                      </Button>
                    </CardContent>
                  </Card>
                </form>
              </>
            )}

            {/* 저장 중 */}
            {activationPhase === 'saving' && (
              <Card className="shadow-lg">
                <CardContent className="text-center py-12">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-100 rounded-full mb-6">
                    <Loader2 className="h-10 w-10 text-blue-600 animate-spin" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-4">
                    모든 설정이 완료되었습니다! 🎉
                  </h3>
                  <p className="text-lg text-gray-600">
                    서비스 설정을 저장하고 있습니다...
                  </p>
                </CardContent>
              </Card>
            )}

            {/* 활성화 중 */}
            {activationPhase === 'activating' && (
              <Card className="shadow-lg">
                <CardContent className="text-center py-12">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-6">
                    <Server className="h-10 w-10 text-green-600 animate-pulse" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-4">
                    원하시는 서비스를 활성화하는 중입니다 ⚡
                  </h3>
                  <p className="text-lg text-gray-600 mb-6">
                    선택하신 서비스들의 포트를 시작하고 있습니다...
                  </p>
                  
                  {/* 프로그레스 바 */}
                  <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                    <div className="bg-green-600 h-3 rounded-full animate-pulse" style={{width: '75%'}}></div>
                  </div>
                  
                  <div className="flex justify-center gap-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className={`w-3 h-3 bg-green-500 rounded-full animate-bounce`} style={{animationDelay: `${i * 0.1}s`}}></div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 완료 */}
            {activationPhase === 'complete' && (
              <Card className="shadow-lg border-green-200 bg-green-50">
                <CardContent className="text-center py-12">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-6">
                    <CheckCircle className="h-10 w-10 text-green-600" />
                  </div>
                  <h3 className="text-2xl font-bold text-green-900 mb-4">
                    🚀 서비스 활성화 완료!
                  </h3>
                  <p className="text-lg text-green-700 mb-6">
                    선택하신 모든 서비스가 성공적으로 활성화되었습니다.
                    <br />곧 대시보드로 이동합니다...
                  </p>
                  
                  <div className="flex items-center justify-center">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin text-green-600" />
                    <span className="text-sm text-green-600">대시보드로 이동 중...</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 진행 단계 안내 */}
            <div className="mt-8 text-center">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">설정 진행 단계</h3>
              <div className="flex items-center justify-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    ✓
                  </div>
                  <span className="text-green-600 font-medium">프로필 설정</span>
                </div>
                <ArrowRight className="h-4 w-4 text-gray-400" />
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    ✓
                  </div>
                  <span className="text-green-600 font-medium">종목 선택</span>
                </div>
                <ArrowRight className="h-4 w-4 text-gray-400" />
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    ✓
                  </div>
                  <span className="text-green-600 font-medium">모델 설정</span>
                </div>
                <ArrowRight className="h-4 w-4 text-gray-400" />
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 ${activationPhase === 'complete' ? 'bg-green-500' : 'bg-primary'} text-white rounded-full flex items-center justify-center text-sm font-bold`}>
                    {activationPhase === 'complete' ? '✓' : '4'}
                  </div>
                  <span className={`${activationPhase === 'complete' ? 'text-green-600' : 'text-primary'} font-medium`}>
                    서비스 활성화
                  </span>
                </div>
              </div>
            </div>

            {/* 안내 정보 */}
            <Alert className="mt-6 border-indigo-200 bg-indigo-50">
              <Settings className="h-4 w-4 text-indigo-600" />
              <AlertDescription className="text-indigo-800">
                <strong>서비스 활성화 안내:</strong> 선택하신 서비스들은 독립적인 포트에서 실행되며, 
                언제든지 대시보드에서 상태를 확인하고 관리할 수 있습니다.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default ServiceActivation; 