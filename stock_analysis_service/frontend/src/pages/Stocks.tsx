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
  Building2
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api, userStorage, StockInfo } from "@/lib/api";

// 전체 종목 데이터 import
import stocksData from "@/data/stocks.json";



const Stocks = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedStocks, setSelectedStocks] = useState<StockInfo[]>([]);

  useEffect(() => {
    const currentUserId = userStorage.getUserId();
    if (!currentUserId) {
      navigate('/profile');
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
    if (userConfig) {
      if (userConfig.stocks) {
        setSelectedStocks(userConfig.stocks);
      }
      if (userConfig.model_type) {
  
      }
    }
  }, [userConfig]);

  // 종목 설정 저장
  const updateStocksMutation = useMutation({
    mutationFn: (stocks: StockInfo[]) => api.updateUserStocks(userId, { stocks }),
    onSuccess: () => {
      toast.success("✅ 관심 종목이 저장되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
    },
    onError: (error) => {
      toast.error("❌ 종목 저장 중 오류가 발생했습니다.");
      console.error('종목 저장 오류:', error);
    },
  });

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

  // 종목 설정 저장
  const saveStocksMutation = useMutation({
    mutationFn: async () => {
      await api.updateUserStocks(userId, { stocks: selectedStocks });
    },
    onSuccess: () => {
      toast.success("🎉 종목 설정이 저장되었습니다!");
      queryClient.invalidateQueries({ queryKey: ['userConfig', userId] });
      
      // 모델 선택 페이지로 이동
      setTimeout(() => {
        navigate('/model-selection');
      }, 1500);
    },
    onError: (error) => {
      toast.error("❌ 종목 설정 저장 중 오류가 발생했습니다.");
      console.error('종목 설정 저장 오류:', error);
    },
  });

  // 종목 검색 결과 필터링
  const filteredStocks = stocksData.filter(stock =>
    stock.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    stock.stock_code.includes(searchQuery)
  );

  // 종목 추가
  const addStock = (stock: typeof stocksData[0]) => {
    // 중복 확인
    if (selectedStocks.some(s => s.stock_code === stock.stock_code)) {
      toast.error("이미 추가된 종목입니다.");
      return;
    }

    const newStock: StockInfo = {
      stock_code: stock.stock_code,
      company_name: stock.company_name,
      is_active: true
    };

    setSelectedStocks(prev => [...prev, newStock]);
    setSearchQuery(''); // 검색어 초기화
    toast.success(`${stock.company_name}이(가) 추가되었습니다.`);
  };

  // 종목 제거
  const removeStock = (stockCode: string) => {
    setSelectedStocks(prev => prev.filter(stock => stock.stock_code !== stockCode));
    toast.success("종목이 제거되었습니다.");
  };

  // 종목 활성/비활성 토글
  const toggleStockActive = (stockCode: string) => {
    setSelectedStocks(prev => 
      prev.map(stock => 
        stock.stock_code === stockCode 
          ? { ...stock, is_active: !stock.is_active }
          : stock
      )
    );
  };

  if (isLoadingConfig) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-gray-600">설정을 불러오는 중...</p>
          </div>
        </div>
        <Footer />
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
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              📈 종목 설정
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              관심 종목을 선택하고 AI 분석 모델을 설정해주세요
            </p>
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              
              {/* 왼쪽: 종목 검색 및 추가 */}
              <Card className="h-fit">
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
                    
                    {(searchQuery ? filteredStocks : stocksData.slice(0, 5)).map((stock) => (
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
                          disabled={selectedStocks.some(s => s.stock_code === stock.stock_code)}
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
                <Card>
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
                            key={stock.stock_code}
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                          >
                            <div className="flex items-center gap-3">
                              <button
                                onClick={() => toggleStockActive(stock.stock_code)}
                                className="flex-shrink-0"
                              >
                                <Badge variant={stock.is_active ? "default" : "secondary"}>
                                  {stock.is_active ? "활성" : "비활성"}
                                </Badge>
                              </button>
                              <div>
                                <p className="font-medium">{stock.company_name}</p>
                                <p className="text-sm text-gray-600">{stock.stock_code}</p>
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeStock(stock.stock_code)}
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

            {/* 하단 액션 버튼 */}
            <div className="mt-12 flex justify-center gap-4">
              <Button
                variant="outline"
                onClick={() => navigate('/profile')}
                size="lg"
              >
                이전 단계
              </Button>
              
              <Button
                onClick={() => saveStocksMutation.mutate()}
                disabled={saveStocksMutation.isPending || selectedStocks.length === 0}
                className="bg-primary hover:bg-primary/90 px-8"
                size="lg"
              >
                {saveStocksMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    설정 저장 중...
                  </>
                ) : (
                  <>
                    완료 및 대시보드로
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </>
                )}
              </Button>
            </div>

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
                  <div className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                    2
                  </div>
                  <span className="text-primary font-medium">종목 선택</span>
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
                <strong>참고:</strong> 종목은 언제든지 추가/제거할 수 있으며, 
                AI 모델 변경 시 분석 결과가 달라질 수 있습니다.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Stocks; 