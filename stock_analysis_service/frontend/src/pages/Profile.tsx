import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import { 
  User, 
  Phone, 
  Mail, 
  Save, 
  ArrowRight,
  Loader2,
  CheckCircle,
  AlertCircle
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api, userStorage, UserProfile } from "@/lib/api";

const Profile = () => {
  const navigate = useNavigate();
  const [userId, setUserId] = useState<string>('');
  const [isNewUser, setIsNewUser] = useState<boolean>(false);

  // 폼 상태
  const [formData, setFormData] = useState<UserProfile>({
    username: '',
    phone_number: '',
    news_similarity_threshold: 0.8,
    news_impact_threshold: 0.6,
  });

  useEffect(() => {
    let currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      // 새 사용자 - ID 생성
      currentUserId = userStorage.generateUserId();
      userStorage.setUserId(currentUserId);
      setIsNewUser(true);
    }
    setUserId(currentUserId);
    console.log('사용자 ID:', currentUserId);
  }, []);

  // 기존 사용자 설정 조회 (새 사용자가 아닌 경우)
  const { data: userConfig, isLoading: isLoadingConfig } = useQuery({
    queryKey: ['userConfig', userId],
    queryFn: () => api.getUserConfig(userId),
    enabled: !!userId && !isNewUser,
    retry: 1,
  });

  // 사용자 설정 데이터가 로드되면 폼에 반영
  useEffect(() => {
    if (userConfig?.profile) {
      setFormData(userConfig.profile);
    }
  }, [userConfig]);

  // 프로필 생성/수정
  const createProfileMutation = useMutation({
    mutationFn: (profileData: UserProfile) => api.createProfile(profileData),
    onSuccess: (data) => {
      console.log('프로필 생성 성공:', data);
      toast.success("✅ 프로필이 성공적으로 저장되었습니다!");
      
      // 사용자 ID 업데이트 (백엔드에서 반환된 ID 사용)
      console.log('🔍 API 응답 전체:', data);
      console.log('🔍 data.data:', data?.data);
      console.log('🔍 data.data.user_id:', data?.data?.user_id);
      
      if (data?.data?.user_id) {
        const realUserId = data.data.user_id;
        console.log('💾 실제 DB user_id로 localStorage 업데이트:', realUserId);
        userStorage.setUserId(realUserId);
        userStorage.setRealUserId(realUserId); // 실제 DB 사용자 ID 저장
        setUserId(realUserId);
      } else {
        console.error('❌ 응답에서 user_id를 찾을 수 없습니다:', data);
      }
      
      // 다음 단계로 이동
      setTimeout(() => {
        navigate('/stocks');
      }, 1500);
    },
    onError: (error: any) => {
      console.error('프로필 생성 실패:', error);
      
      // 전화번호 중복 에러 처리
      if (error?.response?.data?.detail?.includes('전화번호')) {
        toast.error("❌ 이미 등록된 전화번호입니다. 다른 번호를 사용해주세요.");
      } else {
        toast.error("❌ 프로필 저장 중 오류가 발생했습니다.");
      }
    },
  });

  // 폼 데이터 변경 핸들러
  const handleInputChange = (field: keyof UserProfile, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 폼 제출
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // 유효성 검사
    if (!formData.username.trim()) {
      toast.error("이름을 입력해주세요.");
      return;
    }
    
    if (!formData.phone_number.trim()) {
      toast.error("전화번호를 입력해주세요.");
      return;
    }

    // 전화번호 형식 검사 (11자리 숫자)
    const phoneRegex = /^010\d{8}$/;
    if (!phoneRegex.test(formData.phone_number.replace(/[^0-9]/g, ''))) {
      toast.error("올바른 전화번호 형식을 입력해주세요. (예: 01012345678)");
      return;
    }

    // 전화번호에서 숫자만 추출
    const cleanedFormData = {
      ...formData,
      phone_number: formData.phone_number.replace(/[^0-9]/g, '')
    };

    console.log('프로필 데이터 전송:', cleanedFormData);
    createProfileMutation.mutate(cleanedFormData);
  };

  // 대시보드로 바로 이동 (기존 사용자)
  const goToDashboard = () => {
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-gray-50 to-white py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              👤 사용자 프로필
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              AI 기반 주식 분석을 위한 개인 설정을 완료해주세요
            </p>
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl mx-auto">
            
            {/* 프로필 설정 카드 */}
            <Card className="shadow-lg">
              <CardHeader className="text-center pb-4">
                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <User className="h-8 w-8 text-primary" />
                </div>
                <CardTitle className="text-2xl">
                  {isNewUser ? '프로필 생성' : '프로필 수정'}
                </CardTitle>
                <p className="text-gray-600 mt-2">
                  {isNewUser ? 
                    '새로운 계정을 위한 기본 정보를 입력해주세요' : 
                    '기존 정보를 수정할 수 있습니다'
                  }
                </p>
              </CardHeader>
              
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  
                  {/* 이름 입력 */}
                  <div className="space-y-2">
                    <Label htmlFor="username" className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      이름 *
                    </Label>
                    <Input
                      id="username"
                      type="text"
                      placeholder="예: 김투자"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      className="text-lg py-3"
                      required
                    />
                  </div>

                  {/* 전화번호 입력 */}
                  <div className="space-y-2">
                    <Label htmlFor="phone_number" className="flex items-center gap-2">
                      <Phone className="h-4 w-4" />
                      전화번호 *
                    </Label>
                    <Input
                      id="phone_number"
                      type="tel"
                      placeholder="예: 01012345678"
                      value={formData.phone_number}
                      onChange={(e) => handleInputChange('phone_number', e.target.value)}
                      className="text-lg py-3"
                      required
                    />
                    <p className="text-sm text-gray-500">
                      하이픈 없이 숫자만 입력해주세요
                    </p>
                  </div>

                  {/* 뉴스 유사도 임계값 */}
                  <div className="space-y-2">
                    <Label htmlFor="news_similarity_threshold" className="flex items-center gap-2">
                      📰 뉴스 유사도 임계값
                    </Label>
                    <div className="flex items-center gap-4">
                      <input
                        id="news_similarity_threshold"
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.1"
                        value={formData.news_similarity_threshold}
                        onChange={(e) => handleInputChange('news_similarity_threshold', parseFloat(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                        {formData.news_similarity_threshold.toFixed(1)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      높을수록 더 유사한 뉴스만 필터링됩니다
                    </p>
                  </div>

                  {/* 뉴스 영향도 임계값 */}
                  <div className="space-y-2">
                    <Label htmlFor="news_impact_threshold" className="flex items-center gap-2">
                      📊 뉴스 영향도 임계값
                    </Label>
                    <div className="flex items-center gap-4">
                      <input
                        id="news_impact_threshold"
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.1"
                        value={formData.news_impact_threshold}
                        onChange={(e) => handleInputChange('news_impact_threshold', parseFloat(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                        {formData.news_impact_threshold.toFixed(1)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      높을수록 더 영향력 있는 뉴스만 알림을 받습니다
                    </p>
                  </div>

                  {/* 제출 버튼 */}
                  <div className="flex gap-4 pt-4">
                    <Button
                      type="submit"
                      disabled={createProfileMutation.isPending}
                      className="flex-1 bg-primary hover:bg-primary/90 py-3 text-lg"
                      size="lg"
                    >
                      {createProfileMutation.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          저장 중...
                        </>
                      ) : (
                        <>
                          <Save className="mr-2 h-5 w-5" />
                          저장
                        </>
                      )}
                    </Button>
                  </div>
                </form>

                {/* 성공 메시지 */}
                {createProfileMutation.isSuccess && (
                  <Alert className="mt-6 border-green-200 bg-green-50">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <AlertDescription className="text-green-800">
                      프로필이 성공적으로 저장되었습니다! 잠시 후 종목 설정 페이지로 이동합니다.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* 진행 단계 안내 */}
            <div className="mt-8 text-center">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">설정 진행 단계</h3>
              <div className="flex items-center justify-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                    1
                  </div>
                  <span className="text-primary font-medium">프로필 설정</span>
                </div>
                <ArrowRight className="h-4 w-4 text-gray-400" />
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gray-200 text-gray-600 rounded-full flex items-center justify-center text-sm font-bold">
                    2
                  </div>
                  <span className="text-gray-600">종목 선택</span>
                </div>
                <ArrowRight className="h-4 w-4 text-gray-400" />
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gray-200 text-gray-600 rounded-full flex items-center justify-center text-sm font-bold">
                    3
                  </div>
                  <span className="text-gray-600">모델 설정</span>
                </div>
              </div>
            </div>

            {/* 안내 정보 */}
            <Alert className="mt-6 border-blue-200 bg-blue-50">
              <AlertCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                <strong>안내:</strong> 전화번호는 중복 방지를 위해 사용되며, 
                분석 결과 알림을 위한 용도입니다. 개인정보는 안전하게 보호됩니다.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Profile; 