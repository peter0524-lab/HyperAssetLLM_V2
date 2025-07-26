import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  FileText, 
  TrendingUp, 
  BarChart3, 
  Newspaper,
  ScrollText,
  DollarSign,
  ArrowLeft,
  Calendar,
  Clock,
  Eye,
  Download,
  Zap
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const Results = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('news');

  // 샘플 데이터 (실제로는 API에서 가져와야 함)
  const sampleResults = {
    news: {
      status: "completed",
      timestamp: "2024-01-26 14:30:00",
      results: [
        {
          id: 1,
          title: "삼성전자, 4분기 실적 발표 예정",
          summary: "삼성전자가 다음 주 4분기 실적을 발표할 예정입니다. 반도체 업황 회복에 따른 실적 개선이 기대됩니다.",
          impact_score: 0.85,
          stock_code: "005930",
          similar_case: "2023년 2분기 실적 발표 시 +5.2% 상승",
          timestamp: "2024-01-26 14:15:00"
        },
        {
          id: 2,
          title: "SK하이닉스, 중국 공장 증설 발표",
          summary: "SK하이닉스가 중국 우시 공장 증설을 발표했습니다. HBM 메모리 생산 능력 확대가 목적입니다.",
          impact_score: 0.78,
          stock_code: "000660",
          similar_case: "2022년 생산능력 확대 발표 시 +3.8% 상승",
          timestamp: "2024-01-26 13:45:00"
        }
      ]
    },
    disclosure: {
      status: "completed",
      timestamp: "2024-01-26 14:25:00",
      results: [
        {
          id: 1,
          title: "삼성전자 주요사항보고서 제출",
          type: "주요사항보고서",
          summary: "신규 반도체 공장 건설 관련 투자 계획을 공시했습니다. 총 투자금액은 20조원 규모입니다.",
          stock_code: "005930",
          filing_date: "2024-01-26",
          similar_case: "2022년 대규모 투자 발표 시 +7.1% 상승"
        }
      ]
    },
    chart: {
      status: "completed",
      timestamp: "2024-01-26 14:20:00",
      results: [
        {
          id: 1,
          stock_code: "005930",
          pattern: "골든크로스",
          description: "20일 이동평균선이 60일 이동평균선을 상향 돌파했습니다.",
          confidence: 0.82,
          similar_case: "2023년 8월 골든크로스 발생 후 +12.5% 상승",
          recommendation: "매수 관심"
        },
        {
          id: 2,
          stock_code: "000660",
          pattern: "상승 삼각형",
          description: "상승 삼각형 패턴이 형성되었으며, 돌파 시점을 주시해야 합니다.",
          confidence: 0.75,
          similar_case: "2023년 5월 유사 패턴 돌파 후 +8.3% 상승",
          recommendation: "관찰 필요"
        }
      ]
    },
    report: {
      status: "completed",
      timestamp: "2024-01-26 14:35:00",
      summary: {
        total_stocks: 5,
        positive_signals: 3,
        neutral_signals: 2,
        negative_signals: 0,
        overall_sentiment: "긍정적",
        key_insights: [
          "반도체 업황 개선으로 인한 주요 종목들의 상승 전망",
          "4분기 실적 시즌 도래로 실적 서프라이즈 가능성",
          "기술적 지표상 대부분 종목이 상승 신호 발생"
        ]
      }
    },
    flow: {
      status: "completed", 
      timestamp: "2024-01-26 14:40:00",
      results: [
        {
          id: 1,
          stock_code: "005930",
          type: "외국인 매수",
          description: "최근 3일간 외국인 순매수가 지속되고 있습니다.",
          amount: "1,250억원",
          trend: "증가",
          similar_case: "2023년 9월 외국인 순매수 지속 후 +6.8% 상승"
        },
        {
          id: 2,
          stock_code: "000660",
          type: "기관 매수",
          description: "국내 기관투자자들의 매수 세력이 유입되고 있습니다.",
          amount: "840억원", 
          trend: "증가",
          similar_case: "2023년 7월 기관 매수 확대 후 +4.2% 상승"
        }
      ]
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'running': return 'bg-yellow-100 text-yellow-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getImpactColor = (score: number) => {
    if (score >= 0.8) return 'bg-red-100 text-red-800';
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  const getImpactText = (score: number) => {
    if (score >= 0.8) return '높음';
    if (score >= 0.6) return '보통';
    return '낮음';
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* 헤더 섹션 */}
      <section className="bg-gradient-to-br from-gray-50 to-white py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
                📊 분석 결과
              </h1>
              <p className="text-lg text-gray-600">
                AI 기반 종합 주식 분석 결과를 확인하세요
              </p>
            </div>
            <Button 
              variant="outline" 
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              대시보드로
            </Button>
          </div>

          {/* 분석 상태 요약 */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { key: 'news', label: '뉴스 분석', icon: Newspaper, count: sampleResults.news.results.length },
              { key: 'disclosure', label: '공시 분석', icon: ScrollText, count: sampleResults.disclosure.results.length },
              { key: 'chart', label: '차트 분석', icon: BarChart3, count: sampleResults.chart.results.length },
              { key: 'report', label: '종합 리포트', icon: FileText, count: 1 },
              { key: 'flow', label: '수급 분석', icon: DollarSign, count: sampleResults.flow.results.length }
            ].map(({ key, label, icon: Icon, count }) => (
              <Card key={key} className={`cursor-pointer transition-all hover:shadow-md ${activeTab === key ? 'ring-2 ring-primary' : ''}`} onClick={() => setActiveTab(key)}>
                <CardContent className="p-4 text-center">
                  <Icon className="h-6 w-6 mx-auto mb-2 text-primary" />
                  <p className="text-sm font-medium text-gray-900">{label}</p>
                  <p className="text-lg font-bold text-primary">{count}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-5 mb-8">
              <TabsTrigger value="news" className="flex items-center gap-2">
                <Newspaper className="h-4 w-4" />
                뉴스
              </TabsTrigger>
              <TabsTrigger value="disclosure" className="flex items-center gap-2">
                <ScrollText className="h-4 w-4" />
                공시
              </TabsTrigger>
              <TabsTrigger value="chart" className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                차트
              </TabsTrigger>
              <TabsTrigger value="report" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                리포트
              </TabsTrigger>
              <TabsTrigger value="flow" className="flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                수급
              </TabsTrigger>
            </TabsList>

            {/* 뉴스 분석 결과 */}
            <TabsContent value="news" className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold">뉴스 분석 결과</h3>
                <Badge className={getStatusColor(sampleResults.news.status)}>
                  {sampleResults.news.status === 'completed' ? '완료' : '진행중'}
                </Badge>
              </div>
              
              <div className="grid gap-6">
                {sampleResults.news.results.map((news) => (
                  <Card key={news.id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg font-semibold leading-tight">
                          {news.title}
                        </CardTitle>
                        <Badge className={getImpactColor(news.impact_score)}>
                          영향도: {getImpactText(news.impact_score)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {news.timestamp}
                        </span>
                        <span>종목: {news.stock_code}</span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-700 mb-4">{news.summary}</p>
                      <Alert className="border-blue-200 bg-blue-50">
                        <Zap className="h-4 w-4 text-blue-600" />
                        <AlertDescription className="text-blue-800">
                          <strong>유사 사례:</strong> {news.similar_case}
                        </AlertDescription>
                      </Alert>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* 공시 분석 결과 */}
            <TabsContent value="disclosure" className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold">공시 분석 결과</h3>
                <Badge className={getStatusColor(sampleResults.disclosure.status)}>
                  완료
                </Badge>
              </div>
              
              <div className="grid gap-6">
                {sampleResults.disclosure.results.map((disclosure) => (
                  <Card key={disclosure.id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg font-semibold">
                          {disclosure.title}
                        </CardTitle>
                        <Badge variant="outline">{disclosure.type}</Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {disclosure.filing_date}
                        </span>
                        <span>종목: {disclosure.stock_code}</span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-700 mb-4">{disclosure.summary}</p>
                      <Alert className="border-green-200 bg-green-50">
                        <TrendingUp className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-800">
                          <strong>유사 사례:</strong> {disclosure.similar_case}
                        </AlertDescription>
                      </Alert>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* 차트 분석 결과 */}
            <TabsContent value="chart" className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold">차트 분석 결과</h3>
                <Badge className={getStatusColor(sampleResults.chart.status)}>
                  완료
                </Badge>
              </div>
              
              <div className="grid gap-6">
                {sampleResults.chart.results.map((chart) => (
                  <Card key={chart.id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg font-semibold">
                          {chart.pattern} - {chart.stock_code}
                        </CardTitle>
                        <Badge variant="outline">
                          신뢰도: {(chart.confidence * 100).toFixed(0)}%
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-700 mb-4">{chart.description}</p>
                      <div className="flex items-center gap-2 mb-4">
                        <Badge className="bg-blue-100 text-blue-800">
                          {chart.recommendation}
                        </Badge>
                      </div>
                      <Alert className="border-purple-200 bg-purple-50">
                        <BarChart3 className="h-4 w-4 text-purple-600" />
                        <AlertDescription className="text-purple-800">
                          <strong>유사 사례:</strong> {chart.similar_case}
                        </AlertDescription>
                      </Alert>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* 종합 리포트 */}
            <TabsContent value="report" className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold">종합 리포트</h3>
                <div className="flex gap-2">
                  <Badge className={getStatusColor(sampleResults.report.status)}>
                    완료
                  </Badge>
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    PDF 다운로드
                  </Button>
                </div>
              </div>
              
              <div className="grid gap-6">
                {/* 요약 통계 */}
                <Card>
                  <CardHeader>
                    <CardTitle>포트폴리오 요약</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900">{sampleResults.report.summary.total_stocks}</p>
                        <p className="text-sm text-gray-600">총 종목 수</p>
                      </div>
                      <div className="text-center p-4 bg-green-50 rounded-lg">
                        <p className="text-2xl font-bold text-green-600">{sampleResults.report.summary.positive_signals}</p>
                        <p className="text-sm text-gray-600">긍정 신호</p>
                      </div>
                      <div className="text-center p-4 bg-yellow-50 rounded-lg">
                        <p className="text-2xl font-bold text-yellow-600">{sampleResults.report.summary.neutral_signals}</p>
                        <p className="text-sm text-gray-600">중립 신호</p>
                      </div>
                      <div className="text-center p-4 bg-red-50 rounded-lg">
                        <p className="text-2xl font-bold text-red-600">{sampleResults.report.summary.negative_signals}</p>
                        <p className="text-sm text-gray-600">부정 신호</p>
                      </div>
                    </div>
                    
                    <div className="text-center mb-6">
                      <Badge className="bg-green-100 text-green-800 text-lg px-4 py-2">
                        전체 전망: {sampleResults.report.summary.overall_sentiment}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                {/* 핵심 인사이트 */}
                <Card>
                  <CardHeader>
                    <CardTitle>핵심 인사이트</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {sampleResults.report.summary.key_insights.map((insight, index) => (
                        <Alert key={index} className="border-blue-200 bg-blue-50">
                          <Eye className="h-4 w-4 text-blue-600" />
                          <AlertDescription className="text-blue-800">
                            {insight}
                          </AlertDescription>
                        </Alert>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* 수급 분석 결과 */}
            <TabsContent value="flow" className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold">수급 분석 결과</h3>
                <Badge className={getStatusColor(sampleResults.flow.status)}>
                  완료
                </Badge>
              </div>
              
              <div className="grid gap-6">
                {sampleResults.flow.results.map((flow) => (
                  <Card key={flow.id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg font-semibold">
                          {flow.type} - {flow.stock_code}
                        </CardTitle>
                        <Badge className={flow.trend === '증가' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {flow.trend}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-700 mb-2">{flow.description}</p>
                      <p className="text-lg font-semibold text-primary mb-4">거래 규모: {flow.amount}</p>
                      <Alert className="border-indigo-200 bg-indigo-50">
                        <DollarSign className="h-4 w-4 text-indigo-600" />
                        <AlertDescription className="text-indigo-800">
                          <strong>유사 사례:</strong> {flow.similar_case}
                        </AlertDescription>
                      </Alert>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>

          {/* 하단 액션 버튼 */}
          <div className="mt-12 text-center">
            <Button 
              onClick={() => navigate('/dashboard')}
              className="bg-primary hover:bg-primary/90 px-8"
              size="lg"
            >
              새로운 분석 실행하기
            </Button>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Results; 