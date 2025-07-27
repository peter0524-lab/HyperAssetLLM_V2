
import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { ArrowRight, Loader2, Server, CheckCircle, AlertCircle } from "lucide-react";
import LottieAnimation from "./LottieAnimation";
import { api } from "@/lib/api";
import { toast } from "sonner";

const Hero = () => {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [lottieData, setLottieData] = useState<any>(null);
  const [isMobile, setIsMobile] = useState(false);
  const [isStartingServices, setIsStartingServices] = useState(false);
  const [startupPhase, setStartupPhase] = useState<'starting' | 'checking' | 'complete' | 'error'>('starting');

  // 서비스 시작 함수
  const handleStartDashboard = async () => {
    setIsStartingServices(true);
    setStartupPhase('starting');

    try {
      // 1단계: 핵심 서비스 시작 시도
      toast.info("🚀 서비스를 시작하고 있습니다...");
      
      // 🔥 실제로 서버를 시작하는 API 호출 (타임아웃 무시)
      try {
        await api.startCoreServices();
      } catch (error) {
        console.log("start-core API 호출 실패, 서비스 상태 확인으로 진행:", error);
        // API 호출 실패해도 계속 진행
      }
      
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

  useEffect(() => {
    // Check if mobile on mount and when window resizes
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    // Lottie 애니메이션 로딩을 안전하게 처리
    fetch('/loop-header.lottie')
      .then(response => {
        if (!response.ok) {
          throw new Error('Lottie file not found');
        }
        
        // dotLottie 파일인지 확인 (ZIP 형식)
        const contentType = response.headers.get('content-type');
        if (contentType?.includes('zip') || contentType?.includes('application/octet-stream')) {
          throw new Error('dotLottie format not supported, using fallback');
        }
        
        return response.json();
      })
      .then(data => setLottieData(data))
      .catch(error => {
        // 조용히 fallback 처리 (콘솔 경고 제거)
        setLottieData(null);
      });
  }, []);

  useEffect(() => {
    // Skip effect on mobile
    if (isMobile) return;
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current || !imageRef.current) return;
      
      const {
        left,
        top,
        width,
        height
      } = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - left) / width - 0.5;
      const y = (e.clientY - top) / height - 0.5;

      imageRef.current.style.transform = `perspective(1000px) rotateY(${x * 2.5}deg) rotateX(${-y * 2.5}deg) scale3d(1.02, 1.02, 1.02)`;
    };
    
    const handleMouseLeave = () => {
      if (!imageRef.current) return;
      imageRef.current.style.transform = `perspective(1000px) rotateY(0deg) rotateX(0deg) scale3d(1, 1, 1)`;
    };
    
    const container = containerRef.current;
    if (container) {
      container.addEventListener("mousemove", handleMouseMove);
      container.addEventListener("mouseleave", handleMouseLeave);
    }
    
    return () => {
      if (container) {
        container.removeEventListener("mousemove", handleMouseMove);
        container.removeEventListener("mouseleave", handleMouseLeave);
      }
    };
  }, [isMobile]);
  
  useEffect(() => {
    // Skip parallax on mobile
    if (isMobile) return;
    
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const elements = document.querySelectorAll('.parallax');
      elements.forEach(el => {
        const element = el as HTMLElement;
        const speed = parseFloat(element.dataset.speed || '0.1');
        const yPos = -scrollY * speed;
        element.style.setProperty('--parallax-y', `${yPos}px`);
      });
    };
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isMobile]);
  
  return (
    <section 
      className="overflow-hidden relative bg-cover" 
      id="hero" 
      style={{
        backgroundImage: 'url("/Header-background.webp")',
        backgroundPosition: 'center 30%', 
        padding: isMobile ? '100px 12px 40px' : '120px 20px 60px'
      }}
    >
      <div className="absolute -top-[10%] -right-[5%] w-1/2 h-[70%] bg-hyper-asset-gradient opacity-20 blur-3xl rounded-full"></div>
      
      <div className="container px-4 sm:px-6 lg:px-8" ref={containerRef}>
        <div className="flex flex-col lg:flex-row gap-6 lg:gap-12 items-center">
          <div className="w-full lg:w-1/2">
            <div 
              className="hyper-asset-chip mb-3 sm:mb-6 opacity-0 animate-fade-in" 
              style={{ animationDelay: "0.1s" }}
            >
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-hyper-asset-500 text-white mr-2">01</span>
              <span>Purpose</span>
            </div>
            
            <h1 
              className="section-title text-3xl sm:text-4xl lg:text-5xl xl:text-6xl leading-tight opacity-0 animate-fade-in" 
              style={{ animationDelay: "0.3s" }}
            >
              HyperAsset: Where AI<br className="hidden sm:inline" />Meets Customize Stock
            </h1>
            
            <p 
              style={{ animationDelay: "0.5s" }} 
              className="section-subtitle mt-3 sm:mt-6 mb-4 sm:mb-8 leading-relaxed opacity-0 animate-fade-in text-gray-950 font-normal text-base sm:text-lg text-left"
            >
              Manage your stock By AI.
            </p>
            
            <div 
              className="flex flex-col sm:flex-row gap-4 opacity-0 animate-fade-in" 
              style={{ animationDelay: "0.7s" }}
            >
              <button 
                onClick={handleStartDashboard}
                disabled={isStartingServices}
                className="flex items-center justify-center group w-full sm:w-auto text-center transition-all duration-300 hover:scale-105 hover:shadow-lg disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:scale-100" 
                style={{
                  backgroundColor: '#FE5C02',
                  borderRadius: '1440px',
                  boxSizing: 'border-box',
                  color: '#FFFFFF',
                  cursor: isStartingServices ? 'not-allowed' : 'pointer',
                  fontSize: '14px',
                  lineHeight: '20px',
                  padding: '16px 24px', // Slightly reduced padding for mobile
                  border: '1px solid white',
                }}
              >
                {isStartingServices ? (
                  <>
                    <Loader2 className="mr-2 w-4 h-4 animate-spin" />
                    서비스 시작 중...
                  </>
                ) : (
                  <>
                    🚀 대시보드 시작하기
                    <ArrowRight className="ml-2 w-4 h-4 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </button>
            </div>
          </div>
          
          <div className="w-full lg:w-1/2 relative mt-6 lg:mt-0">
            {lottieData ? (
              <div className="relative z-10 animate-fade-in" style={{ animationDelay: "0.9s" }}>
                <LottieAnimation 
                  animationPath={lottieData} 
                  className="w-full h-auto max-w-lg mx-auto"
                  loop={true}
                  autoplay={true}
                />
              </div>
            ) : (
              <>
              <div className="absolute inset-0 bg-dark-900 rounded-2xl sm:rounded-3xl -z-10 shadow-xl"></div>
              <div className="relative transition-all duration-500 ease-out overflow-hidden rounded-2xl sm:rounded-3xl shadow-2xl">
                <img 
                  ref={imageRef} 
                  src="/lovable-uploads/5663820f-6c97-4492-9210-9eaa1a8dc415.png" 
                  alt="Atlas Robot" 
                  className="w-full h-auto object-cover transition-transform duration-500 ease-out" 
                  style={{ transformStyle: 'preserve-3d' }} 
                />
                <div className="absolute inset-0" style={{ backgroundImage: 'url("/hero-image.jpg")', backgroundSize: 'cover', backgroundPosition: 'center', mixBlendMode: 'overlay', opacity: 0.5 }}></div>
              </div>
              </>
            )}
          </div>
        </div>
      </div>

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
      
      <div className="hidden lg:block absolute bottom-0 left-1/4 w-64 h-64 bg-pulse-100/30 rounded-full blur-3xl -z-10 parallax" data-speed="0.05"></div>
    </section>
  );
};

export default Hero;
