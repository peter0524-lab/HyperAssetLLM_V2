import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Phone, CheckCircle, XCircle, ArrowRight, Download } from "lucide-react";
import { toast } from "sonner";
import { api, userStorage } from "@/lib/api";

//페이지 진입시 초기화화
const Auth = () => {
  const navigate = useNavigate();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [isChecking, setIsChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<'checking' | 'loading-data' | 'exists' | 'not-exists' | null>(null);

  // 전화번호 형식 검증
  const validatePhoneNumber = (phone: string) => {
    const phoneRegex = /^010\d{8}$/;
    return phoneRegex.test(phone);
  };

  // 전화번호 자동 포맷팅
  const formatPhoneNumber = (value: string) => {
    // 숫자만 추출
    const numbers = value.replace(/[^\d]/g, '');
    
    // 010으로 시작하지 않으면 010 추가
    if (numbers.length > 0 && !numbers.startsWith('010')) {
      return '010' + numbers.slice(0, 8);
    }
    
    // 최대 11자리까지만
    return numbers.slice(0, 11);
  };

  // 사용자 프로필 확인 mutation
  const checkProfileMutation = useMutation({
    mutationFn: async (inputPhoneNumber: string) => {
      setIsChecking(true);
      setCheckResult('checking');
      
      // 1초 프로필 확인 시뮬레이션
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      try {
        // 전화번호로 사용자 확인 API 호출 (User Service 직접 호출)
        console.log('🔍 사용자 확인 API 호출 시작 (직접 호출)');
        console.log('📱 전화번호:', inputPhoneNumber);
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://hyperasset.site';
        console.log('🔗 직접 호출 URL:', `${API_BASE_URL}/users/check?phone_number=${inputPhoneNumber}`);
        
        const response = await fetch(`${API_BASE_URL}/users/check?phone_number=${inputPhoneNumber}`);
        const userCheckResult: any = await response.json();
        console.log('✅ User Service 직접 호출 응답:', userCheckResult);
        
        // API 응답 구조: { success: true, data: { exists: true, user_id: "...", username: "..." } }
        if (userCheckResult.success && userCheckResult.data && userCheckResult.data.exists) {
          console.log('✅ 실제 프로필 찾음 (직접 호출):', userCheckResult);
          return { 
            exists: true, 
            user_id: userCheckResult.data.user_id,
            username: userCheckResult.data.username 
          };
        } else {
          console.log('❌ 사용자 존재하지 않음 (직접 호출)');
          return { exists: false, error: 'User not found' };
        }
      } catch (error: any) {
        console.log('❌ User Service 직접 호출 에러:', error.response?.status);
        
        // 404는 사용자 없음
        if (error.response?.status === 404) {
          return { exists: false, error: 'User not found' };
        }
        
        // 서버 에러 등은 에러로 throw
        throw error;
      }
    },
    onSuccess: (data) => {
      setIsChecking(false);
      
      if (data.exists) {
        // 프로필이 존재하는 경우 - 정보 로딩 단계로 이동
        setCheckResult('loading-data');
        
        // 사용자 정보 저장
        userStorage.setUserId(phoneNumber);
        if (data.user_id) {
          userStorage.setRealUserId(data.user_id); // 실제 DB 사용자 ID 저장
        }
        
        // 2초 후 대시보드로 이동
        setTimeout(() => {
          setCheckResult('exists');
          
          setTimeout(() => {
            toast.success("✅ 정보를 성공적으로 불러왔습니다!");
            navigate('/dashboard');
          }, 1500);
        }, 2000);
        
      } else {
        // 프로필이 없는 경우
        setCheckResult('not-exists');
        
        // 사용자 정보 저장
        userStorage.setUserId(phoneNumber);
        
        // 1.5초 후 프로필 설정으로 이동
        setTimeout(() => {
          toast.info("📝 새로운 프로필을 생성하겠습니다!");
          navigate('/profile');
        }, 1500);
      }
    },
    onError: (error: any) => {
      setIsChecking(false);
      console.error('프로필 확인 중 에러:', error);
      
      // 네트워크 에러나 서버가 꺼진 경우
      if (!error.response) {
        toast.error("서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.");
        setCheckResult(null);
        return;
      }
      
      // 500번대 서버 에러
      if (error.response?.status >= 500) {
        toast.error("서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
        setCheckResult(null);
        return;
      }
      
      // 404나 기타 클라이언트 에러는 신규 사용자로 처리
      if (error.response?.status >= 400 && error.response?.status < 500) {
        setCheckResult('not-exists');
        userStorage.setUserId(phoneNumber);
        
        setTimeout(() => {
          toast.info("📝 새로운 프로필을 생성하겠습니다!");
          navigate('/profile');
        }, 1500);
      } else {
        // 기타 알 수 없는 에러
        toast.error("알 수 없는 오류가 발생했습니다. 다시 시도해주세요.");
        setCheckResult(null);
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!phoneNumber.trim()) {
      toast.error("전화번호를 입력해주세요.");
      return;
    }

    if (!validatePhoneNumber(phoneNumber)) {
      toast.error("올바른 전화번호 형식이 아닙니다. (예: 01012345678)");
      return;
    }

    checkProfileMutation.mutate(phoneNumber);
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    setPhoneNumber(formatted);
  };

  const handleReset = () => {
    setCheckResult(null);
    setIsChecking(false);
    setPhoneNumber("");
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-gray-50 to-white py-24">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6">
              <Phone className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              🚀 HyperAsset 시작하기
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              전화번호를 입력하여 프로필을 확인하고 맞춤형 투자 분석을 시작해보세요
            </p>
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-md mx-auto">
            <Card className="shadow-lg border-0">
              <CardHeader className="text-center pb-6">
                <CardTitle className="text-2xl font-bold text-gray-900">
                  사용자 인증
                </CardTitle>
              </CardHeader>
              
              <CardContent className="space-y-6">
                {!checkResult && (
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="phoneNumber" className="text-sm font-medium text-gray-700">
                        전화번호
                      </Label>
                      <Input
                        id="phoneNumber"
                        type="tel"
                        placeholder="01036707735"
                        value={phoneNumber}
                        onChange={handlePhoneChange}
                        className="text-lg py-3"
                        disabled={isChecking}
                        maxLength={11}
                      />
                      <p className="text-xs text-gray-500">
                        * 하이픈(-) 없이 11자리 숫자만 입력해주세요
                      </p>
                    </div>
                    
                    <Button 
                      type="submit" 
                      className="w-full py-3 text-lg font-semibold"
                      disabled={isChecking || !validatePhoneNumber(phoneNumber)}
                    >
                      {isChecking ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          확인 중...
                        </>
                      ) : (
                        <>
                          프로필 확인하기
                          <ArrowRight className="ml-2 h-5 w-5" />
                        </>
                      )}
                    </Button>
                  </form>
                )}

                {/* 로딩 상태 - 프로필 확인 */}
                {checkResult === 'checking' && (
                  <div className="text-center py-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                      <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      프로필 확인 중...
                    </h3>
                    <p className="text-gray-600">
                      고객님의 프로필이 있는지 확인하고 있습니다
                    </p>
                  </div>
                )}

                {/* 로딩 상태 - 정보 불러오기 */}
                {checkResult === 'loading-data' && (
                  <div className="text-center py-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                      <Download className="h-8 w-8 text-green-600 animate-bounce" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      정보를 불러오는 중입니다 📊
                    </h3>
                    <p className="text-gray-600">
                      기존 설정과 포트폴리오 정보를 가져오고 있습니다
                    </p>
                    <div className="mt-4">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-green-600 h-2 rounded-full animate-pulse" style={{width: '70%'}}></div>
                      </div>
                      <p className="text-sm text-gray-500 mt-2">잠시만 기다려주세요...</p>
                    </div>
                  </div>
                )}

                {/* 프로필 있음 - 완료 */}
                {checkResult === 'exists' && (
                  <div className="text-center py-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                      <CheckCircle className="h-8 w-8 text-green-600" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      환영합니다! 🎉
                    </h3>
                    <p className="text-gray-600 mb-4">
                      기존 프로필로 대시보드에 접속합니다
                    </p>
                    <div className="flex items-center justify-center">
                      <Loader2 className="mr-2 h-4 w-4 animate-spin text-blue-600" />
                      <span className="text-sm text-blue-600">대시보드로 이동 중...</span>
                    </div>
                  </div>
                )}

                {/* 프로필 없음 */}
                {checkResult === 'not-exists' && (
                  <div className="text-center py-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 rounded-full mb-4">
                      <XCircle className="h-8 w-8 text-orange-600" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      신규 사용자입니다! 📝
                    </h3>
                    <p className="text-gray-600 mb-4">
                      맞춤형 프로필 설정을 시작하겠습니다
                    </p>
                    <div className="flex items-center justify-center">
                      <Loader2 className="mr-2 h-4 w-4 animate-spin text-orange-600" />
                      <span className="text-sm text-orange-600">프로필 설정으로 이동 중...</span>
                    </div>
                  </div>
                )}

                {/* 다시 시도 버튼 */}
                {(checkResult === 'exists' || checkResult === 'not-exists') && (
                  <div className="text-center pt-4">
                    <Button 
                      variant="outline" 
                      onClick={handleReset}
                      className="text-sm"
                    >
                      다른 번호로 다시 시도
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 안내 정보 */}
            <Alert className="mt-6 border-blue-200 bg-blue-50">
              <Phone className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                <strong>보안 안내:</strong> 입력하신 전화번호는 안전하게 암호화되어 저장됩니다.
                기존 사용자는 저장된 설정으로 바로 대시보드에 접속하며, 신규 사용자는 맞춤형 프로필 설정을 진행합니다.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Auth; 