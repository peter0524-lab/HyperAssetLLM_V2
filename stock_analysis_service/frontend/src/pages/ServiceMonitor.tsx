import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { 
  Server, 
  Activity, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  RefreshCw,
  Network,
  Zap,
  Clock,
  TrendingUp
} from "lucide-react";
import { toast } from "sonner";

interface ServiceStatus {
  name: string;
  port: number;
  portOpen: boolean;
  serviceRunning: boolean;
  healthCheck: boolean;
  responseTime?: number;
  lastCheck: string;
  uptime?: string;
  error?: string;
}

interface SystemMetrics {
  totalServices: number;
  runningServices: number;
  healthyServices: number;
  avgResponseTime: number;
}

const ServiceMonitor = () => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics>({
    totalServices: 0,
    runningServices: 0,
    healthyServices: 0,
    avgResponseTime: 0
  });
  const [isLoading, setIsLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // 서비스 목록 정의
  const serviceDefinitions = [
    { name: "Simple Server Starter", port: 9998, icon: "🚀" },
            { name: "Simple Server Starter", port: 9998, icon: "📡" },
    { name: "Orchestrator", port: 8000, icon: "🎯" },
    { name: "News Service", port: 8001, icon: "📰" },
    { name: "Disclosure Service", port: 8002, icon: "📋" },
    { name: "Chart Service", port: 8003, icon: "📈" },
    { name: "Report Service", port: 8004, icon: "📊" },
    { name: "API Gateway", port: 8005, icon: "🌐" },
    { name: "User Service", port: 8006, icon: "👤" },
    { name: "Flow Analysis Service", port: 8010, icon: "💰" }
  ];

  // 서비스 상태 확인 함수
  const checkServiceStatus = async (service: typeof serviceDefinitions[0]): Promise<ServiceStatus> => {
    const startTime = Date.now();
    
    try {
      // 헬스체크 요청
      const response = await fetch(`http://localhost:${service.port}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });
      
      const responseTime = Date.now() - startTime;
      const isHealthy = response.ok;
      
      return {
        name: service.name,
        port: service.port,
        portOpen: true, // 응답이 왔다면 포트는 열려있음
        serviceRunning: true, // 응답이 왔다면 서비스는 실행 중
        healthCheck: isHealthy,
        responseTime,
        lastCheck: new Date().toLocaleTimeString(),
        uptime: "Unknown" // 실제 구현 시 서비스에서 제공
      };
    } catch (error) {
      // 포트가 열려있는지 별도 확인 (실제로는 백엔드 API 필요)
      return {
        name: service.name,
        port: service.port,
        portOpen: false, // 연결 실패 시 포트 닫힘으로 가정
        serviceRunning: false,
        healthCheck: false,
        responseTime: Date.now() - startTime,
        lastCheck: new Date().toLocaleTimeString(),
        error: error instanceof Error ? error.message : "Connection failed"
      };
    }
  };

  // 모든 서비스 상태 확인
  const fetchAllServiceStatus = async () => {
    setIsLoading(true);
    console.log("🔍 서비스 상태 확인 시작...");
    
    try {
      // 백엔드 API 호출
      const response = await fetch('http://localhost:8005/api/monitoring/services-status', {
        method: 'GET',
        signal: AbortSignal.timeout(15000) // 15초 타임아웃
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setServices(data.services);
        setMetrics(data.metrics);
        setLastUpdate(new Date());
        console.log(`✅ 서비스 상태 확인 완료: ${data.metrics.healthyServices}/${data.metrics.totalServices} 정상`);
      } else {
        throw new Error(data.error || '서비스 상태 확인 실패');
      }
      
    } catch (error) {
      console.error("❌ 서비스 상태 확인 실패:", error);
      
      // 백엔드 API 실패 시 프론트엔드에서 직접 확인 (fallback)
      console.log("🔄 Fallback: 프론트엔드에서 직접 확인...");
      const statusPromises = serviceDefinitions.map(service => checkServiceStatus(service));
      const statuses = await Promise.all(statusPromises);
      
      setServices(statuses);
      
      // 메트릭 계산
      const totalServices = statuses.length;
      const runningServices = statuses.filter(s => s.serviceRunning).length;
      const healthyServices = statuses.filter(s => s.healthCheck).length;
      const avgResponseTime = statuses
        .filter(s => s.responseTime)
        .reduce((sum, s) => sum + (s.responseTime || 0), 0) / 
        statuses.filter(s => s.responseTime).length || 0;
      
      setMetrics({
        totalServices,
        runningServices,
        healthyServices,
        avgResponseTime: Math.round(avgResponseTime)
      });
      
      setLastUpdate(new Date());
      toast.error("백엔드 API 연결 실패. 프론트엔드에서 직접 확인 중입니다.");
      
    } finally {
      setIsLoading(false);
    }
  };

  // 자동 새로고침
  useEffect(() => {
    fetchAllServiceStatus();
    
    if (autoRefresh) {
      const interval = setInterval(fetchAllServiceStatus, 10000); // 10초마다
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  // 상태별 색상 및 아이콘
  const getStatusDisplay = (service: ServiceStatus) => {
    if (service.healthCheck) {
      return {
        color: "bg-green-500",
        textColor: "text-green-700",
        bgColor: "bg-green-50",
        icon: <CheckCircle className="h-4 w-4" />,
        status: "정상",
        badge: "success"
      };
    } else if (service.serviceRunning) {
      return {
        color: "bg-yellow-500",
        textColor: "text-yellow-700",
        bgColor: "bg-yellow-50",
        icon: <AlertTriangle className="h-4 w-4" />,
        status: "경고",
        badge: "warning"
      };
    } else if (service.portOpen) {
      return {
        color: "bg-orange-500",
        textColor: "text-orange-700",
        bgColor: "bg-orange-50",
        icon: <Network className="h-4 w-4" />,
        status: "포트만 열림",
        badge: "warning"
      };
    } else {
      return {
        color: "bg-red-500",
        textColor: "text-red-700",
        bgColor: "bg-red-50",
        icon: <XCircle className="h-4 w-4" />,
        status: "중단",
        badge: "destructive"
      };
    }
  };

  const healthPercentage = metrics.totalServices > 0 
    ? Math.round((metrics.healthyServices / metrics.totalServices) * 100) 
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <Activity className="h-8 w-8 text-blue-600" />
              서비스 모니터링 대시보드
            </h1>
            <p className="text-slate-600 mt-2">
              실시간 서비스 상태 및 성능 모니터링
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="text-sm text-slate-500">
              마지막 업데이트: {lastUpdate.toLocaleTimeString()}
            </div>
            <Button
              onClick={fetchAllServiceStatus}
              disabled={isLoading}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              새로고침
            </Button>
            <Button
              onClick={() => setAutoRefresh(!autoRefresh)}
              variant={autoRefresh ? "default" : "outline"}
              size="sm"
            >
              <Zap className="h-4 w-4 mr-2" />
              자동새로고침 {autoRefresh ? "ON" : "OFF"}
            </Button>
          </div>
        </div>

        {/* 전체 메트릭 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">전체 서비스</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.totalServices}</div>
              <p className="text-xs text-muted-foreground">등록된 서비스</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">실행 중</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{metrics.runningServices}</div>
              <p className="text-xs text-muted-foreground">활성 서비스</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">정상 상태</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{metrics.healthyServices}</div>
              <p className="text-xs text-muted-foreground">헬스체크 통과</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">평균 응답시간</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.avgResponseTime}ms</div>
              <p className="text-xs text-muted-foreground">평균 지연시간</p>
            </CardContent>
          </Card>
        </div>

        {/* 전체 시스템 상태 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              전체 시스템 상태
            </CardTitle>
            <CardDescription>
              시스템 전체 건강도: {healthPercentage}%
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={healthPercentage} className="w-full h-3" />
            <div className="flex justify-between text-sm text-muted-foreground mt-2">
              <span>정상: {metrics.healthyServices}개</span>
              <span>전체: {metrics.totalServices}개</span>
            </div>
          </CardContent>
        </Card>

        {/* 서비스 상세 목록 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {services.map((service) => {
            const statusDisplay = getStatusDisplay(service);
            const serviceIcon = serviceDefinitions.find(s => s.port === service.port)?.icon || "🔧";
            
            return (
              <Card key={service.port} className={`transition-all duration-200 hover:shadow-lg ${statusDisplay.bgColor}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <span className="text-2xl">{serviceIcon}</span>
                      {service.name}
                    </CardTitle>
                    <Badge variant={statusDisplay.badge as any}>
                      {statusDisplay.status}
                    </Badge>
                  </div>
                  <CardDescription>
                    포트 {service.port}
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-3">
                  {/* 상태 표시기 */}
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${statusDisplay.color}`}></div>
                    <span className={`text-sm font-medium ${statusDisplay.textColor}`}>
                      {statusDisplay.icon}
                      <span className="ml-2">{statusDisplay.status}</span>
                    </span>
                  </div>

                  <Separator />

                  {/* 상세 정보 */}
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">포트 상태:</span>
                      <span className={service.portOpen ? "text-green-600" : "text-red-600"}>
                        {service.portOpen ? "열림" : "닫힘"}
                      </span>
                    </div>
                    
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">서비스 실행:</span>
                      <span className={service.serviceRunning ? "text-green-600" : "text-red-600"}>
                        {service.serviceRunning ? "실행 중" : "중단"}
                      </span>
                    </div>
                    
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">헬스체크:</span>
                      <span className={service.healthCheck ? "text-green-600" : "text-red-600"}>
                        {service.healthCheck ? "정상" : "실패"}
                      </span>
                    </div>

                    {service.responseTime && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">응답시간:</span>
                        <span className="font-mono">{service.responseTime}ms</span>
                      </div>
                    )}

                    <div className="flex justify-between">
                      <span className="text-muted-foreground">마지막 확인:</span>
                      <span className="font-mono text-xs">{service.lastCheck}</span>
                    </div>

                    {service.error && (
                      <div className="mt-2 p-2 bg-red-50 rounded text-red-700 text-xs">
                        <strong>오류:</strong> {service.error}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* 로딩 상태 */}
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin mr-2" />
            <span>서비스 상태 확인 중...</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ServiceMonitor; 