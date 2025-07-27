import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Mail, Github, Linkedin, User, GraduationCap, Brain, Database, Loader2, Server, CheckCircle, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { toast } from "sonner";

const Contact = () => {
  const navigate = useNavigate();
  const [isStartingServices, setIsStartingServices] = useState(false);
  const [startupPhase, setStartupPhase] = useState<'starting' | 'checking' | 'complete' | 'error'>('starting');

  // 서비스 시작 함수 (Hero.tsx와 동일)
  const handleStartDashboard = async () => {
    setIsStartingServices(true);
    setStartupPhase('starting');

    try {
      // 1단계: 핵심 서비스 시작 시도
      toast.info("🚀 서비스를 시작하고 있습니다...");
      
      // 2단계: 서비스 상태 확인 (폴링)
      setStartupPhase('checking');
      let attempts = 0;
      const maxAttempts = 30; // 30초 제한
      
      while (attempts < maxAttempts) {
        try {
          const statusResponse = await api.getServicesStatus();
          
          if (statusResponse.success && statusResponse.data) {
            const services = statusResponse.data;
            const userServiceRunning = services.user_service?.is_running;
            const apiGatewayRunning = services.api_gateway?.is_running;
            
            if (userServiceRunning && apiGatewayRunning) {
              // 서비스 시작 완료
              setStartupPhase('complete');
              toast.success("✅ 서비스가 성공적으로 시작되었습니다!");
              
              // 잠시 대기 후 인증 페이지로 이동
              setTimeout(() => {
                setIsStartingServices(false);
                navigate('/auth');
              }, 1500);
              return;
            }
          }
        } catch (error) {
          console.log(`서비스 상태 확인 시도 ${attempts + 1}: 대기 중...`);
        }
        
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 2000)); // 2초 대기
      }
      
      // 시간 초과
      throw new Error('서비스 시작 시간이 초과되었습니다');
      
    } catch (error) {
      console.error('서비스 시작 실패:', error);
      setStartupPhase('error');
      toast.error("❌ 서비스 시작에 실패했습니다. 잠시 후 다시 시도해주세요.");
      
      setTimeout(() => {
        setIsStartingServices(false);
      }, 3000);
    }
  };

  const teamMembers = [
    {
      name: "이태환",
      major: "데이터사이언스학부 데이터사이언스전공",
      role: "Lead Developer & Data Scientist",
      description: "AI 기반 주식 분석 시스템 개발 및 데이터 파이프라인 설계를 담당합니다.",
      skills: ["Python", "React", "Machine Learning", "Data Engineering"],
      icon: <Database className="h-8 w-8" />,
      color: "from-blue-500 to-cyan-500"
    },
    {
      name: "정현도",
      major: "데이터사이언스학부 심리뇌과학전공",
      role: "Psychology & UX Researcher",
      description: "사용자 경험 설계와 투자 심리학 분석을 통한 서비스 최적화를 담당합니다.",
      skills: ["UX Design", "Psychology", "User Research", "Behavioral Analysis"],
      icon: <Brain className="h-8 w-8" />,
      color: "from-purple-500 to-pink-500"
    },
    {
      name: "김민겸",
      major: "데이터사이언스학부 심리뇌과학전공",
      role: "Cognitive Science & Data Analyst",
      description: "인지과학 기반 데이터 분석과 사용자 행동 패턴 연구를 담당합니다.",
      skills: ["Data Analysis", "Cognitive Science", "Statistics", "R"],
      icon: <GraduationCap className="h-8 w-8" />,
      color: "from-green-500 to-teal-500"
    }
  ];

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="relative bg-gradient-to-br from-gray-50 via-white to-gray-50 py-24 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full">
          <div className="absolute top-10 left-10 w-72 h-72 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
          <div className="absolute top-10 right-10 w-72 h-72 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
        </div>
        
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6">
              <User className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
              우리 팀을 만나보세요
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              HyperAsset을 만든 한양대학교 데이터사이언스학부 학생들입니다.
              <br />
              각자의 전문성을 살려 혁신적인 투자 분석 플랫폼을 개발하고 있습니다.
            </p>
          </div>
        </div>
      </section>

      {/* 팀 멤버 섹션 */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {teamMembers.map((member, index) => (
              <Card key={index} className="group hover:shadow-xl transition-all duration-300 hover:-translate-y-2 border-0 shadow-lg overflow-hidden">
                <CardHeader className="relative pb-0">
                  <div className={`absolute inset-0 bg-gradient-to-br ${member.color} opacity-5 group-hover:opacity-10 transition-opacity duration-300`} />
                  <div className="relative z-10">
                    <div className={`inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r ${member.color} rounded-full mb-4 group-hover:scale-110 transition-transform duration-300`}>
                      <div className="text-white">
                        {member.icon}
                      </div>
                    </div>
                    <CardTitle className="text-2xl font-bold text-gray-900 mb-2">
                      {member.name}
                    </CardTitle>
                    <div className="flex items-center gap-2 text-primary font-medium mb-2">
                      <GraduationCap className="h-4 w-4" />
                      <span className="text-sm">한양대학교</span>
                    </div>
                    <p className="text-gray-600 text-sm mb-3">
                      {member.major}
                    </p>
                    <div className={`inline-block px-3 py-1 bg-gradient-to-r ${member.color} text-white text-xs font-medium rounded-full`}>
                      {member.role}
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="pt-6">
                  <p className="text-gray-600 mb-6 leading-relaxed">
                    {member.description}
                  </p>
                  
                  {/* 스킬 태그 */}
                  <div className="flex flex-wrap gap-2 mb-6">
                    {member.skills.map((skill, skillIndex) => (
                      <span 
                        key={skillIndex}
                        className="px-3 py-1 bg-gray-100 text-gray-700 text-xs rounded-full hover:bg-gray-200 transition-colors duration-200"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                  
                  {/* 연락처 버튼들 */}
                  <div className="flex gap-3">
                    <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 text-gray-700 rounded-lg transition-all duration-200 hover:scale-105">
                      <Mail className="h-4 w-4" />
                      <span className="text-sm font-medium">Email</span>
                    </button>
                    <button className="p-2 bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 text-gray-700 rounded-lg transition-all duration-200 hover:scale-105">
                      <Github className="h-4 w-4" />
                    </button>
                    <button className="p-2 bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 text-gray-700 rounded-lg transition-all duration-200 hover:scale-105">
                      <Linkedin className="h-4 w-4" />
                    </button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA 섹션 */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
              함께 혁신을 만들어가세요
            </h2>
            <p className="text-xl text-blue-100 mb-8">
              HyperAsset은 데이터사이언스와 심리학을 결합한 차세대 투자 플랫폼입니다.
              우리와 함께 스마트한 투자의 미래를 경험해보세요.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button 
                onClick={handleStartDashboard}
                disabled={isStartingServices}
                className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-lg hover:bg-gray-50 transition-colors duration-200 hover:scale-105 transform disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center"
              >
                {isStartingServices ? (
                  <>
                    <Loader2 className="mr-2 w-4 h-4 animate-spin" />
                    서비스 시작 중...
                  </>
                ) : (
                  '대시보드 시작하기'
                )}
              </button>
              <button 
                onClick={() => window.location.href = '/'}
                className="px-8 py-4 border-2 border-white text-white font-semibold rounded-lg hover:bg-white hover:text-blue-600 transition-all duration-200 hover:scale-105 transform"
              >
                서비스 소개 보기
              </button>
            </div>
          </div>
        </div>
      </section>

      <Footer />
      
      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes blob {
            0% {
              transform: translate(0px, 0px) scale(1);
            }
            33% {
              transform: translate(30px, -50px) scale(1.1);
            }
            66% {
              transform: translate(-20px, 20px) scale(0.9);
            }
            100% {
              transform: translate(0px, 0px) scale(1);
            }
          }
          .animate-blob {
            animation: blob 7s infinite;
          }
          .animation-delay-2000 {
            animation-delay: 2s;
          }
          .animation-delay-4000 {
            animation-delay: 4s;
          }
        `
      }} />

      {/* 서비스 시작 로딩 모달 */}
      {isStartingServices && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
            <div className="text-center">
              <div className="mb-6">
                {startupPhase === 'starting' && (
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                    <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
                  </div>
                )}
                {startupPhase === 'checking' && (
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 rounded-full mb-4">
                    <Server className="h-8 w-8 text-orange-600 animate-pulse" />
                  </div>
                )}
                {startupPhase === 'complete' && (
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                    <CheckCircle className="h-8 w-8 text-green-600" />
                  </div>
                )}
                {startupPhase === 'error' && (
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                    <AlertCircle className="h-8 w-8 text-red-600" />
                  </div>
                )}
              </div>

              <h3 className="text-xl font-bold text-gray-900 mb-3">
                {startupPhase === 'starting' && '🚀 HyperAsset 서비스 시작 중...'}
                {startupPhase === 'checking' && '🔍 서비스 상태 확인 중...'}
                {startupPhase === 'complete' && '✅ 서비스 시작 완료!'}
                {startupPhase === 'error' && '❌ 서비스 시작 실패'}
              </h3>

              <p className="text-gray-600 mb-6">
                {startupPhase === 'starting' && '백엔드 서비스를 준비하고 있습니다. 잠시만 기다려주세요.'}
                {startupPhase === 'checking' && '서비스들이 정상적으로 실행되었는지 확인하고 있습니다.'}
                {startupPhase === 'complete' && '모든 서비스가 성공적으로 시작되었습니다. 곧 이동합니다.'}
                {startupPhase === 'error' && '서비스 시작 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.'}
              </p>

              {(startupPhase === 'starting' || startupPhase === 'checking') && (
                <div className="flex items-center justify-center space-x-2">
                  {[0, 1, 2].map((index) => (
                    <div
                      key={index}
                      className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                      style={{ animationDelay: `${index * 0.2}s` }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Contact; 