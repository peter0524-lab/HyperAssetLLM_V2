import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { 
  Brain, 
  Save, 
  ArrowRight,
  Loader2,
  CheckCircle,
  AlertCircle,
  Cpu,
  Sparkles
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

const ModelSelection = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('hyperclova');

  useEffect(() => {
    const currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      toast.error("사용자 정보를 찾을 수 없습니다. 다시 로그인해주세요.");
      navigate('/auth');
      return;
    }
    setUserId(currentUserId);
  }, [navigate]);

  // 기존 설정 조회
  const { data: userConfig, isLoading: isLoadingConfig } = useQuery({
    queryKey: ['userConfig', userId],
    queryFn: () => api.getUserConfig(userId),
    enabled: !!userId,
    retry: 1,
  });

  // 기존 모델 설정 반영
  useEffect(() => {
    if (userConfig?.model_type) {
      setSelectedModel(userConfig.model_type);
    }
  }, [userConfig]);

  // 모델 설정 저장
  const updateModelMutation = useMutation({
    mutationFn: async (modelType: string) => {
      await api.updateUserModel(userId, { model_type: modelType });
    },
    onSuccess: () => {
      toast.success("🎉 AI 모델 설정이 완료되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
      
      // 서비스 활성화 페이지로 이동
      setTimeout(() => {
        navigate('/service-activation');
      }, 1500);
    },
    onError: (error) => {
      toast.error("❌ 모델 설정 저장 중 오류가 발생했습니다.");
      console.error('모델 설정 오류:', error);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateModelMutation.mutate(selectedModel);
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
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-600 rounded-full mb-6">
              <Brain className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              🧠 AI 모델 선택
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              주식 분석에 사용할 AI 모델을 선택하여 맞춤형 투자 인사이트를 받아보세요
            </p>
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            
            {/* 모델 선택 카드 */}
            <form onSubmit={handleSubmit}>
              <Card className="shadow-lg">
                <CardHeader className="text-center pb-6">
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Cpu className="h-8 w-8 text-primary" />
                  </div>
                  <CardTitle className="text-2xl">AI 분석 모델 설정</CardTitle>
                  <p className="text-gray-600 mt-2">
                    각 모델의 특성을 확인하고 투자 스타일에 맞는 AI를 선택하세요
                  </p>
                </CardHeader>
                
                <CardContent className="space-y-8">
                  
                  {/* 모델 선택 드롭다운 */}
                  <div className="space-y-4">
                    <Label htmlFor="model-select" className="text-lg font-semibold flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      AI 모델 선택
                    </Label>
                    <Select value={selectedModel} onValueChange={setSelectedModel}>
                      <SelectTrigger id="model-select" className="text-lg py-4 h-auto">
                        <SelectValue placeholder="AI 모델을 선택하세요" />
                      </SelectTrigger>
                      <SelectContent>
                        {AI_MODELS.map((model) => (
                          <SelectItem key={model.value} value={model.value} className="py-4">
                            <div className="flex items-start gap-3">
                              <span className="text-2xl">{model.icon}</span>
                              <div className="flex flex-col">
                                <span className="font-semibold text-base">{model.label}</span>
                                <span className="text-sm text-gray-600">{model.description}</span>
                              </div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* 선택된 모델 정보 */}
                  {selectedModel && (
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-lg border border-blue-200">
                      <div className="flex items-start gap-4">
                        <div className="text-3xl">
                          {AI_MODELS.find(m => m.value === selectedModel)?.icon}
                        </div>
                        <div className="flex-1">
                          <h3 className="text-xl font-bold text-gray-900 mb-2">
                            {AI_MODELS.find(m => m.value === selectedModel)?.label}
                          </h3>
                          <p className="text-gray-700 mb-4">
                            {AI_MODELS.find(m => m.value === selectedModel)?.description}
                          </p>
                          
                          <div className="space-y-2">
                            <h4 className="font-semibold text-gray-800">주요 특징:</h4>
                            <div className="flex flex-wrap gap-2">
                              {AI_MODELS.find(m => m.value === selectedModel)?.features.map((feature, index) => (
                                <span 
                                  key={index}
                                  className="px-3 py-1 bg-white bg-opacity-80 text-sm text-gray-700 rounded-full border"
                                >
                                  {feature}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 제출 버튼 */}
                  <div className="pt-6">
                    <Button
                      type="submit"
                      disabled={updateModelMutation.isPending}
                      className="w-full bg-primary hover:bg-primary/90 py-4 text-lg"
                      size="lg"
                    >
                      {updateModelMutation.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          설정 저장 중...
                        </>
                      ) : (
                        <>
                          <Save className="mr-2 h-5 w-5" />
                          저장하고 시작하기
                        </>
                      )}
                                         </Button>
                   </div>
                 </CardContent>
               </Card>
             </form>

             {/* 성공 메시지 */}
             {updateModelMutation.isSuccess && (
               <Alert className="mt-6 border-green-200 bg-green-50">
                 <CheckCircle className="h-4 w-4 text-green-600" />
                 <AlertDescription className="text-green-800">
                   AI 모델 설정이 완료되었습니다! 잠시 후 대시보드로 이동합니다.
                 </AlertDescription>
               </Alert>
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
                  <div className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                    3
                  </div>
                  <span className="text-primary font-medium">모델 설정</span>
                </div>
              </div>
            </div>

            {/* 안내 정보 */}
            <Alert className="mt-6 border-purple-200 bg-purple-50">
              <Brain className="h-4 w-4 text-purple-600" />
              <AlertDescription className="text-purple-800">
                <strong>AI 모델 팁:</strong> 한국 주식 분석에는 HyperCLOVA를 추천합니다. 
                각 모델은 언제든지 대시보드에서 변경할 수 있습니다.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default ModelSelection; 