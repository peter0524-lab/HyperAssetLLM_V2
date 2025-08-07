import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { 
  Settings as SettingsIcon, 
  Brain, 
  TrendingUp, 
  Save, 
  ArrowRight,
  Loader2,
  CheckCircle,
  AlertCircle,
  Cpu,
  Sparkles,
  Bell,
  BarChart3,
  FileText,
  Newspaper,
  Activity,
  User,
  Phone
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api, userStorage } from "@/lib/api";

// 사용 가능한 AI 모델 목록
const AI_MODELS = [
  { 
    value: "hyperclova", 
    label: "HyperCLOVA", 
    description: "네이버의 대규모 언어 모델",
    features: ["한국어 특화", "금융 도메인 강화", "빠른 응답속도"],
    icon: "🇰🇷"
  },
  { 
    value: "chatgpt", 
    label: "ChatGPT", 
    description: "OpenAI의 대화형 AI",
    features: ["범용적 성능", "창의적 분석", "글로벌 표준"],
    icon: "🤖"
  },
  { 
    value: "claude", 
    label: "Claude", 
    description: "Anthropic의 AI 어시스턴트",
    features: ["안전성 중시", "논리적 분석", "정확한 추론"],
    icon: "🧠"
  },
  { 
    value: "gemini", 
    label: "Gemini", 
    description: "Google의 차세대 AI",
    features: ["멀티모달", "고성능 분석", "실시간 데이터"],
    icon: "💎"
  }
];

// 서비스 목록
const SERVICES = [
  {
    key: "news_service",
    name: "뉴스 분석",
    description: "실시간 뉴스 모니터링 및 영향도 분석",
    icon: Newspaper,
    color: "text-blue-600"
  },
  {
    key: "disclosure_service", 
    name: "공시 분석",
    description: "기업 공시 정보 실시간 추적",
    icon: FileText,
    color: "text-green-600"
  },
  {
    key: "chart_service",
    name: "차트 분석", 
    description: "기술적 지표 및 차트 패턴 분석",
    icon: BarChart3,
    color: "text-purple-600"
  },
  {
    key: "flow_service",
    name: "자금 흐름",
    description: "기관/외국인 자금 흐름 분석",
    icon: Activity,
    color: "text-orange-600"
  },
  {
    key: "report_service",
    name: "리포트 생성",
    description: "종합 분석 리포트 자동 생성",
    icon: TrendingUp,
    color: "text-red-600"
  }
];

const Settings = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState<string>('');
  
  // 설정 상태
  const [selectedModel, setSelectedModel] = useState<string>('hyperclova');
  const [newsSimilarityThreshold, setNewsSimilarityThreshold] = useState<number>(0.8);
  const [newsImpactThreshold, setNewsImpactThreshold] = useState<number>(0.6);
  const [selectedServices, setSelectedServices] = useState<Record<string, boolean>>({
    news_service: false,
    disclosure_service: false,
    report_service: false,
    chart_service: false,
    flow_service: false
  });


  useEffect(() => {
    const currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      toast.error("사용자 정보를 찾을 수 없습니다. 다시 로그인해주세요.");
      navigate('/auth');
      return;
    }
    setUserId(currentUserId);
  }, [navigate]);

  // 사용자 설정 조회
  const { data: userConfig, isLoading: isLoadingConfig } = useQuery({
    queryKey: ['userConfig', userId],
    queryFn: () => api.getUserConfig(userId),
    enabled: !!userId,
    retry: 1,
  });

  // 사용자 설정이 로드되면 현재 상태에 반영
  useEffect(() => {
    if (userConfig?.data) {
      console.log("🔍 Settings - userConfig.data:", userConfig.data);
      
      setSelectedModel(userConfig.data.model_type || 'hyperclova');
      setNewsSimilarityThreshold(userConfig.data.news_similarity_threshold || 0.8);
      setNewsImpactThreshold(userConfig.data.news_impact_threshold || 0.6);
      
      // 활성화된 서비스 설정 - 디버깅 로그 추가
      console.log("🔍 Settings - active_services:", userConfig.data.active_services);
      
      if (userConfig.data.active_services) {
        const services = userConfig.data.active_services;
        console.log("🔍 Settings - 서비스 데이터:", services);
        
        const newSelectedServices = {
          news_service: Boolean(services.news_service) || false,
          disclosure_service: Boolean(services.disclosure_service) || false,
          report_service: Boolean(services.report_service) || false,
          chart_service: Boolean(services.chart_service) || false,
          flow_service: Boolean(services.flow_service) || false
        };
        
        console.log("🔍 Settings - 설정할 서비스 상태:", newSelectedServices);
        setSelectedServices(newSelectedServices);
      } else {
        console.log("🔍 Settings - active_services가 없음, 기본값 사용");
        // active_services가 없으면 기본값으로 설정
        setSelectedServices({
          news_service: false,
          disclosure_service: false,
          report_service: false,
          chart_service: false,
          flow_service: false
        });
      }
    }
  }, [userConfig]);

  // 모델 설정 저장
  const updateModelMutation = useMutation({
    mutationFn: (model_type: string) => api.updateUserModel(userId, { model_type }),
    onSuccess: () => {
      toast.success("✅ AI 모델이 설정되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
    },
    onError: (error) => {
      toast.error("❌ 모델 설정 중 오류가 발생했습니다.");
      console.error('모델 설정 오류:', error);
    },
  });

  // 뉴스 임계값 설정 저장
  const updateThresholdsMutation = useMutation({
    mutationFn: (thresholds: { news_similarity_threshold: number; news_impact_threshold: number }) => 
      api.updateUserProfile(userId, thresholds),
    onSuccess: () => {
      toast.success("✅ 뉴스 임계값이 설정되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
    },
    onError: (error) => {
      toast.error("❌ 임계값 설정 중 오류가 발생했습니다.");
      console.error('임계값 설정 오류:', error);
    },
  });

  // 서비스 활성화 저장
  const updateServicesMutation = useMutation({
    mutationFn: async () => {
      // 백엔드가 기대하는 형식으로 변환 (배열 형태)
      const serviceArray = Object.entries(selectedServices).map(([service_name, enabled]) => ({
        service_name,
        enabled,
        priority: 1
      }));
      
      return await api.updateUserWantedServicesDetailed(userId, serviceArray);
    },
    onSuccess: () => {
      toast.success("✅ 서비스 설정이 저장되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
    },
    onError: (error) => {
      toast.error("❌ 서비스 설정 중 오류가 발생했습니다.");
      console.error('서비스 설정 오류:', error);
    },
  });

  // 서비스 토글 핸들러
  const handleServiceToggle = (serviceKey: string, enabled: boolean) => {
    setSelectedServices(prev => ({
      ...prev,
      [serviceKey]: enabled
    }));
  };

  // 전체 설정 저장
  const handleSaveAll = async () => {
    try {
      // 모델 설정
      await updateModelMutation.mutateAsync(selectedModel);
      
      // 임계값 설정
      await updateThresholdsMutation.mutateAsync({
        news_similarity_threshold: newsSimilarityThreshold,
        news_impact_threshold: newsImpactThreshold
      });
      
      // 서비스 설정
      await updateServicesMutation.mutateAsync();
      
      toast.success("✅ 모든 설정이 저장되었습니다!");
      
      // 저장 완료 후 1초 뒤 대시보드로 이동
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
      
    } catch (error) {
      toast.error("❌ 설정 저장 중 오류가 발생했습니다.");
    }
  };

  if (isLoadingConfig) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-gray-600">설정을 불러오고 있습니다...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-gray-50 to-white py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
                                        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6">
                              <SettingsIcon className="h-8 w-8 text-white" />
                            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              ⚙️ 환경 설정
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              AI 주식 분석을 위한 모든 설정을 한 곳에서 관리하세요
            </p>
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto">
            
                         {/* 설정 섹션들 */}
             <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
               
               {/* AI 모델 설정 */}
              <Card className="shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5 text-primary" />
                    AI 모델 선택
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger>
                      <SelectValue placeholder="AI 모델을 선택하세요" />
                    </SelectTrigger>
                    <SelectContent>
                      {AI_MODELS.map((model) => (
                        <SelectItem key={model.value} value={model.value}>
                          <div className="flex items-center gap-2">
                            <span>{model.icon}</span>
                            <span>{model.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  {/* 선택된 모델 정보 */}
                  {selectedModel && (
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">
                          {AI_MODELS.find(m => m.value === selectedModel)?.icon}
                        </span>
                        <div>
                          <h4 className="font-semibold">
                            {AI_MODELS.find(m => m.value === selectedModel)?.label}
                          </h4>
                          <p className="text-sm text-gray-600">
                            {AI_MODELS.find(m => m.value === selectedModel)?.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* 뉴스 임계값 설정 */}
              <Card className="shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Newspaper className="h-5 w-5 text-primary" />
                    뉴스 분석 설정
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      📰 뉴스 유사도 임계값
                    </Label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.1"
                        value={newsSimilarityThreshold}
                        onChange={(e) => setNewsSimilarityThreshold(parseFloat(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                        {newsSimilarityThreshold.toFixed(1)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      높을수록 더 유사한 뉴스만 필터링됩니다
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      📊 뉴스 영향도 임계값
                    </Label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.1"
                        value={newsImpactThreshold}
                        onChange={(e) => setNewsImpactThreshold(parseFloat(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                        {newsImpactThreshold.toFixed(1)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      높을수록 더 영향력 있는 뉴스만 알림을 받습니다
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* 서비스 활성화 설정 */}
              <Card className="shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    서비스 활성화
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {SERVICES.map((service) => {
                    const IconComponent = service.icon;
                    return (
                      <div key={service.key} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <IconComponent className={`h-5 w-5 ${service.color}`} />
                          <div>
                            <h4 className="font-medium">{service.name}</h4>
                            <p className="text-sm text-gray-600">{service.description}</p>
                          </div>
                        </div>
                        <Switch
                          checked={selectedServices[service.key]}
                          onCheckedChange={(checked) => handleServiceToggle(service.key, checked)}
                        />
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </div>

            {/* 저장 버튼 */}
            <div className="mt-8 flex justify-center">
                             <Button
                 onClick={handleSaveAll}
                 disabled={
                   updateModelMutation.isPending ||
                   updateThresholdsMutation.isPending ||
                   updateServicesMutation.isPending
                 }
                 className="bg-primary hover:bg-primary/90 text-white py-3 px-8 text-lg"
                 size="lg"
               >
                 {updateModelMutation.isPending ||
                  updateThresholdsMutation.isPending ||
                  updateServicesMutation.isPending ? (
                   <>
                     <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                     저장 중...
                   </>
                 ) : (
                   <>
                     <Save className="mr-2 h-5 w-5" />
                     모든 설정 저장
                   </>
                 )}
               </Button>
            </div>

                         {/* 성공 메시지 */}
             {(updateModelMutation.isSuccess ||
               updateThresholdsMutation.isSuccess ||
               updateServicesMutation.isSuccess) && (
               <Alert className="mt-6 border-green-200 bg-green-50">
                 <CheckCircle className="h-4 w-4 text-green-600" />
                 <AlertDescription className="text-green-800">
                   설정이 성공적으로 저장되었습니다!
                 </AlertDescription>
               </Alert>
             )}

            {/* 안내 정보 */}
            <Alert className="mt-6 border-blue-200 bg-blue-50">
              <AlertCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                <strong>설정 안내:</strong> 모든 설정은 실시간으로 저장되며, 
                변경사항은 즉시 분석 서비스에 반영됩니다.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Settings;
