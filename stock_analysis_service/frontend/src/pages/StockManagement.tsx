import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import { 
  TrendingUp, 
  Search, 
  Plus, 
  X, 
  Save, 
  ArrowRight,
  Loader2,
  CheckCircle,
  AlertCircle,
  Building2,
  Settings
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api, userStorage, StockInfo } from "@/lib/api";

// 전체 종목 데이터 import
import stocksData from "@/data/stocks.json";

const StockManagement = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedStocks, setSelectedStocks] = useState<StockInfo[]>([]);

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
      if (userConfig.data.stocks) {
        // 🔧 백엔드에서 받은 데이터를 StockInfo 형식으로 변환
        const convertedStocks: StockInfo[] = userConfig.data.stocks.map((stock: any) => ({
          code: stock.stock_code,
          name: stock.stock_name,
          sector: stock.sector || '기타' // sector가 없으면 기본값 설정
        }));
        setSelectedStocks(convertedStocks);
      }
    }
  }, [userConfig]);

  // 종목 설정 저장
  const updateStocksMutation = useMutation({
    mutationFn: (stocks: StockInfo[]) => api.updateUserStocks(userId, { stocks }),
    onSuccess: () => {
      toast.success("✅ 관심 종목이 저장되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
      
      // 저장 완료 후 1초 뒤 대시보드로 이동
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    },
    onError: (error) => {
      toast.error("❌ 종목 저장 중 오류가 발생했습니다.");
      console.error('종목 저장 오류:', error);
    },
  });

  // 종목 추가
  const addStock = (stock: typeof stocksData[0]) => {
    const newStock: StockInfo = {
      code: stock.stock_code,
      name: stock.company_name,
      sector: stock.sector
    };
    
    if (!selectedStocks.some(s => s.code === stock.stock_code)) {
      setSelectedStocks(prev => [...prev, newStock]);
      toast.success(`✅ ${stock.company_name} 종목이 추가되었습니다!`);
    } else {
      toast.info("이미 추가된 종목입니다.");
    }
  };

  // 종목 제거
  const removeStock = (stockCode: string) => {
    const stockToRemove = selectedStocks.find(s => s.code === stockCode);
    setSelectedStocks(prev => prev.filter(s => s.code !== stockCode));
    if (stockToRemove) {
      toast.success(`✅ ${stockToRemove.name} 종목이 제거되었습니다!`);
    }
  };

  // 검색 필터링
  const filteredStocks = stocksData.filter(stock =>
    stock.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    stock.stock_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    stock.sector.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoadingConfig) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-gray-600">종목 정보를 불러오고 있습니다...</p>
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
              <TrendingUp className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              📈 종목 관리
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              관심 종목을 추가하고 관리하여 AI 분석을 최적화하세요
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
              
              {/* 왼쪽: 종목 검색 */}
              <Card className="shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Search className="h-5 w-5 text-primary" />
                    종목 검색
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* 검색 입력 */}
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      placeholder="종목명 또는 종목코드 검색..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 text-lg py-3"
                    />
                  </div>

                  {/* 검색 결과 */}
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {searchQuery && filteredStocks.length === 0 && (
                      <p className="text-center text-gray-500 py-4">
                        검색 결과가 없습니다
                      </p>
                    )}
                    
                    {(searchQuery ? filteredStocks : stocksData.slice(0, 10)).map((stock) => (
                      <div 
                        key={stock.stock_code}
                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <Building2 className="h-4 w-4 text-gray-400" />
                          <div>
                            <p className="font-medium">{stock.company_name}</p>
                            <p className="text-sm text-gray-600">
                              {stock.stock_code} • {stock.sector}
                            </p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => addStock(stock)}
                          disabled={selectedStocks.some(s => s.code === stock.stock_code)}
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          추가
                        </Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 오른쪽: 선택된 종목 및 설정 */}
              <div className="space-y-6">
                
                {/* 선택된 종목 목록 */}
                <Card className="shadow-lg">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-primary" />
                        관심 종목 ({selectedStocks.length}개)
                      </span>
                      {selectedStocks.length > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => updateStocksMutation.mutate(selectedStocks)}
                          disabled={updateStocksMutation.isPending}
                        >
                          {updateStocksMutation.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-1" />
                          ) : (
                            <Save className="h-4 w-4 mr-1" />
                          )}
                          저장
                        </Button>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {selectedStocks.length === 0 ? (
                      <div className="text-center py-8">
                        <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-600 mb-2">선택된 종목이 없습니다</p>
                        <p className="text-sm text-gray-500">
                          왼쪽에서 관심 종목을 검색하여 추가해주세요
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3 max-h-64 overflow-y-auto">
                        {selectedStocks.map((stock) => (
                          <div 
                            key={stock.code}
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                          >
                            <div className="flex items-center gap-3">
                              <div className="flex-shrink-0">
                                <Badge variant="default">
                                  활성
                                </Badge>
                              </div>
                              <div>
                                <p className="font-medium">{stock.name}</p>
                                <p className="text-sm text-gray-600">{stock.code}</p>
                                {stock.sector && (
                                  <p className="text-xs text-gray-500">{stock.sector}</p>
                                )}
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeStock(stock.code)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

              </div>
            </div>

            {/* 저장 버튼 */}
            <div className="mt-8 flex justify-center">
              <Button
                onClick={() => updateStocksMutation.mutate(selectedStocks)}
                disabled={
                  updateStocksMutation.isPending ||
                  selectedStocks.length === 0
                }
                className="bg-primary hover:bg-primary/90 text-white py-3 px-8 text-lg"
                size="lg"
              >
                {updateStocksMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    저장 중...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-5 w-5" />
                    종목 설정 저장
                  </>
                )}
              </Button>
            </div>

            {/* 성공 메시지 */}
            {updateStocksMutation.isSuccess && (
              <Alert className="mt-6 border-green-200 bg-green-50">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  종목 설정이 성공적으로 저장되었습니다! 대시보드로 이동합니다...
                </AlertDescription>
              </Alert>
            )}

            {/* 안내 정보 */}
            <Alert className="mt-6 border-blue-200 bg-blue-50">
              <AlertCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                <strong>종목 관리 안내:</strong> 관심 종목을 추가하면 AI가 해당 종목에 대한 
                뉴스, 차트, 공시, 수급 분석을 실시간으로 제공합니다. 
                종목은 언제든지 추가/제거할 수 있습니다.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default StockManagement;
