import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ServiceFeatures = () => {
  return (
    <section id="features" className="container py-24 sm:py-32 space-y-8">
      <h2 className="text-3xl lg:text-4xl font-bold md:text-center">
        주요 기능
      </h2>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>주간 보고서</CardTitle>
          </CardHeader>
          <CardContent>
            1주일간의 데이터를 종합하여 주간 보고서를 생성하고, 사용자에게 전송합니다.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>주가 원인 분석</CardTitle>
          </CardHeader>
          <CardContent>
            거래량과 주가 등락률을 기반으로 주가 변동의 원인을 분석하여 제공합니다.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>이슈 스케줄러</CardTitle>
          </CardHeader>
          <CardContent>
            실적 발표, 증자 등 주요 일정을 추적하고 사용자에게 미리 알려줍니다.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>사업보고서 AI 요약</CardTitle>
          </CardHeader>
          <CardContent>
            사용자가 원하는 종목의 사업보고서를 AI가 요약하여 제공합니다.
          </CardContent>
        </Card>
      </div>
    </section>
  );
};

export default ServiceFeatures;
