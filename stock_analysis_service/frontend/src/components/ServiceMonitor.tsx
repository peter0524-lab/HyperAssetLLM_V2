import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import { 
  Terminal, 
  Server, 
  Activity, 
  Cpu, 
  HardDrive, 
  Wifi,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Play,
  Square,
  RefreshCw
} from "lucide-react";

interface ServiceStatus {
  status: string;
  port: number;
  pid: number | null;
  started_at: string | null;
  last_health_check: string;
  error_count: number;
  description: string;
  is_running: boolean;
}

interface ServicesStatusData {
  [serviceName: string]: ServiceStatus;
}

const ServiceMonitor: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 서비스 상태 조회
  const { data: servicesData, isLoading, refetch } = useQuery({
    queryKey: ['servicesStatus'],
    queryFn: () => api.getServicesStatus(),
    refetchInterval: autoRefresh ? 5000 : false, // 5초마다 자동 새로고침
    refetchOnWindowFocus: false,
  });

  // 서비스별 정의
  const serviceDefinitions = {
    api_gateway: { name: "API Gateway", color: "blue", icon: <Server className="h-4 w-4" /> },
    user_service: { name: "User Service", color: "green", icon: <Server className="h-4 w-4" /> },
    news_service: { name: "News Service", color: "purple", icon: <Activity className="h-4 w-4" /> },
    disclosure_service: { name: "Disclosure Service", color: "orange", icon: <Activity className="h-4 w-4" /> },
    report_service: { name: "Report Service", color: "pink", icon: <Activity className="h-4 w-4" /> },
    chart_service: { name: "Chart Service", color: "red", icon: <Activity className="h-4 w-4" /> },
    flow_service: { name: "Flow Service", color: "yellow", icon: <Activity className="h-4 w-4" /> },
    orchestrator: { name: "Task Orchestrator", color: "indigo", icon: <Cpu className="h-4 w-4" /> },
  };

  // 로그 추가 함수
  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString('ko-KR');
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev.slice(0, 99)]);
  };

  // 서비스 상태 변화 감지
  useEffect(() => {
    if (servicesData?.success && servicesData?.services) {
      const statusData: ServicesStatusData = servicesData.services;
      
      Object.entries(statusData).forEach(([serviceName, status]) => {
        const def = serviceDefinitions[serviceName as keyof typeof serviceDefinitions];
        if (def) {
          const statusText = status.is_running ? 'RUNNING' : 'STOPPED';
          addLog(`${def.name} (Port: ${status.port}) - Status: ${statusText}`);
        }
      });
    }
  }, [servicesData]);

  // 상태별 색상 반환
  const getStatusColor = (isRunning: boolean, status: string) => {
    if (isRunning) return 'success';
    if (status === 'error' || status === 'failed') return 'destructive';
    return 'secondary';
  };

  // 상태별 아이콘 반환  
  const getStatusIcon = (isRunning: boolean, status: string) => {
    if (isRunning) return <CheckCircle className="h-4 w-4" />;
    if (status === 'error' || status === 'failed') return <XCircle className="h-4 w-4" />;
    return <AlertCircle className="h-4 w-4" />;
  };

  const services = servicesData?.success ? servicesData.services : {};
  const totalServices = Object.keys(services).length;
  const runningServices = Object.values(services).filter((s: any) => s.is_running).length;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gray-900 rounded-lg">
            <Terminal className="h-6 w-6 text-green-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Service Monitor</h2>
            <p className="text-sm text-gray-600">Real-time microservices status monitoring</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
            className="font-mono"
          >
            {isLoading ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            REFRESH
          </Button>
          
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className="font-mono"
          >
            {autoRefresh ? <Square className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
            AUTO-REFRESH
          </Button>
        </div>
      </div>

      {/* 시스템 개요 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gray-900 text-white border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 font-mono">TOTAL SERVICES</p>
                <p className="text-2xl font-bold font-mono">{totalServices}</p>
              </div>
              <Server className="h-8 w-8 text-blue-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 text-white border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 font-mono">RUNNING</p>
                <p className="text-2xl font-bold font-mono text-green-400">{runningServices}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 text-white border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 font-mono">STOPPED</p>
                <p className="text-2xl font-bold font-mono text-red-400">{totalServices - runningServices}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 text-white border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 font-mono">UPTIME</p>
                <p className="text-2xl font-bold font-mono text-blue-400">24h</p>
              </div>
              <Clock className="h-8 w-8 text-blue-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 서비스 상태 */}
        <Card className="bg-gray-900 text-white border-gray-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-green-400 font-mono flex items-center gap-2">
              <Activity className="h-5 w-5" />
              SERVICE_STATUS
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-80">
              <div className="space-y-3">
                {Object.entries(services).map(([serviceName, status]: [string, any]) => {
                  const def = serviceDefinitions[serviceName as keyof typeof serviceDefinitions];
                  if (!def) return null;

                  return (
                    <div key={serviceName} className="flex items-center justify-between p-3 bg-gray-800 rounded border border-gray-700 hover:border-gray-600 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                          {def.icon}
                          <span className="font-mono text-sm font-medium">{def.name}</span>
                        </div>
                        
                        <Badge 
                          variant={getStatusColor(status.is_running, status.status) as any}
                          className="font-mono text-xs"
                        >
                          {getStatusIcon(status.is_running, status.status)}
                          {status.is_running ? 'RUNNING' : 'STOPPED'}
                        </Badge>
                      </div>
                      
                      <div className="text-right">
                        <div className="flex items-center gap-4 text-xs text-gray-400 font-mono">
                          <span>PORT:{status.port}</span>
                          {status.pid && <span>PID:{status.pid}</span>}
                        </div>
                        {status.started_at && (
                          <div className="text-xs text-gray-500 font-mono">
                            Started: {new Date(status.started_at).toLocaleString('ko-KR')}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* 시스템 로그 */}
        <Card className="bg-gray-900 text-white border-gray-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-green-400 font-mono flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              SYSTEM_LOGS
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-80">
              <div className="space-y-1">
                {logs.length === 0 ? (
                  <div className="text-gray-500 font-mono text-sm p-4 text-center">
                    Waiting for system events...
                  </div>
                ) : (
                  logs.map((log, index) => (
                    <div key={index} className="text-sm font-mono text-gray-300 p-2 hover:bg-gray-800 rounded">
                      <span className="text-green-400">$</span> {log}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* 네트워크 모니터링 */}
      <Card className="bg-gray-900 text-white border-gray-700">
        <CardHeader className="pb-3">
          <CardTitle className="text-green-400 font-mono flex items-center gap-2">
            <Wifi className="h-5 w-5" />
            NETWORK_MONITORING
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold font-mono text-blue-400">8005</div>
              <div className="text-xs text-gray-400 font-mono">API_GATEWAY</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold font-mono text-green-400">8006</div>
              <div className="text-xs text-gray-400 font-mono">USER_SERVICE</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold font-mono text-purple-400">8007</div>
              <div className="text-xs text-gray-400 font-mono">NEWS_SERVICE</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold font-mono text-orange-400">8008+</div>
              <div className="text-xs text-gray-400 font-mono">OTHER_SERVICES</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ServiceMonitor; 