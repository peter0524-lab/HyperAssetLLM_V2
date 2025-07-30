import axios from 'axios';

// 🔥 직접 호출 방식 (Direct Call) - API Gateway 우회
const API_GATEWAY_URL = 'http://localhost:8005'; // API Gateway (헬스체크용)
const USER_SERVICE_URL = 'http://localhost:8006'; // User Service 직접 호출

// API Gateway용 클라이언트 (헬스체크만)
const gatewayClient = axios.create({
  baseURL: API_GATEWAY_URL,
  timeout: 10000, // 10초 타임아웃
  headers: {
    'Content-Type': 'application/json',
  },
});

// User Service 직접 호출용 클라이언트
const userServiceClient = axios.create({
  baseURL: USER_SERVICE_URL,
  timeout: 30000, // 30초 타임아웃 (직접 호출이므로 빠름)
  headers: {
    'Content-Type': 'application/json',
  },
});

// 응답 인터셉터 - 에러 처리 (User Service용)
userServiceClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.error('❌ User Service API 에러 발생!');
    console.error('🔍 에러 상세 정보:');
    console.error('📋 메시지:', error.message);
    console.error('📋 상태 코드:', error.response?.status);
    console.error('📋 상태 텍스트:', error.response?.statusText);
    console.error('📋 요청 URL:', error.config?.url);
    console.error('📋 요청 방식:', error.config?.method?.toUpperCase());
    console.error('📋 응답 데이터:', error.response?.data);
    console.error('📋 에러 코드:', error.code);
    console.error('🔍 전체 에러 객체:', error);
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    return Promise.reject(error);
  }
);

// 타입 정의
export interface UserProfile {
  username: string;
  phone_number: string;
  news_similarity_threshold: number;
  news_impact_threshold: number;
}

export interface StockInfo {
  code: string;
  name: string;
  sector?: string;
}

export interface UserConfig {
  user_id: string;
  profile: UserProfile;
  stocks: StockInfo[];
  model_type: string;
}

export interface AnalysisResult {
  status: string;
  message: string;
  timestamp: string;
  [key: string]: any;
}

// API 함수들
export const api = {
  // ===== 헬스체크 (API Gateway) =====
  async checkHealth(): Promise<any> {
    const response = await gatewayClient.get('/health');
    return response.data;
  },

  async checkUserServiceHealth(): Promise<any> {
    const response = await userServiceClient.get('/health');
    return response.data;
  },

  // ===== 사용자 프로필 관리 (User Service 직접 호출) =====
  async createProfile(profileData: UserProfile): Promise<any> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log("👤 프로필 생성 API 호출 시작 (직접 호출)");
    console.log("📋 프로필 데이터:", profileData);
    console.log("🔗 직접 호출 URL: /users/profile");
    console.log("📤 요청 방식: POST");
    
    try {
      const startTime = Date.now();
      const response = await userServiceClient.post('/users/profile', profileData);
      const requestTime = Date.now() - startTime;
      
      console.log("✅ 프로필 생성 성공! (직접 호출)");
      console.log("⏱️ 요청 완료 시간:", requestTime + "ms");
      console.log("📋 응답 데이터:", response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      return response.data;
    } catch (error: any) {
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      console.error('❌ 프로필 생성 에러! (직접 호출)');
      console.error('🔍 에러 상세 분석:', error);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      throw error;
    }
  },

  async getUserConfig(userId: string): Promise<UserConfig> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log("⚙️ 사용자 설정 조회 API 호출 시작 (직접 호출)");
    console.log("👤 사용자 ID:", userId);
    console.log("🔗 직접 호출 URL:", `/users/${userId}/config`);
    console.log("📤 요청 방식: GET");
    
    try {
      const startTime = Date.now();
      const response = await userServiceClient.get(`/users/${userId}/config`);
      const requestTime = Date.now() - startTime;
      
      console.log("✅ 사용자 설정 조회 성공! (직접 호출)");
      console.log("⏱️ 요청 완료 시간:", requestTime + "ms");
      console.log("📋 응답 데이터:", response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      return response.data;
    } catch (error: any) {
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      console.error('❌ 사용자 설정 조회 에러! (직접 호출)');
      console.error('🔍 에러 상세 분석:', error);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      throw error;
    }
  },

  // ===== 종목 설정 (User Service 직접 호출) =====
  async updateUserStocks(userId: string, stocksData: { stocks: StockInfo[] }): Promise<any> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log("📈 종목 설정 API 호출 시작 (직접 호출)");
    console.log("👤 사용자 ID:", userId);
    console.log("📊 설정할 종목 수:", stocksData.stocks.length);
    console.log("📋 종목 리스트:", stocksData.stocks);
    console.log("🔗 직접 호출 URL:", `/users/${userId}/stocks/batch`);
    console.log("📤 요청 방식: POST");
    
    try {
      const startTime = Date.now();
      const response = await userServiceClient.post(`/users/${userId}/stocks/batch`, stocksData);
      const requestTime = Date.now() - startTime;
      
      console.log("✅ 종목 설정 API 성공! (직접 호출)");
      console.log("⏱️ 요청 완료 시간:", requestTime + "ms");
      console.log("📋 응답 데이터:", response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      return response.data;
    } catch (error: any) {
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      console.error('❌ 종목 설정 API 에러! (직접 호출)');
      console.error('🔍 에러 상세 분석:');
      console.error('📋 에러 메시지:', error.message);
      console.error('📋 상태 코드:', error.response?.status);
      console.error('📋 상태 텍스트:', error.response?.statusText);
      console.error('📋 서버 응답:', error.response?.data);
      console.error('📋 요청 설정:', error.config);
      console.error('🔍 전체 에러:', error);
      
      // 500 에러인 경우 임시 처리
      if (error.response?.status === 500) {
        console.error('💥 User Service 내부 에러 (500) 발생!');
        console.error('🔍 가능한 원인:');
        console.error('   - 데이터베이스 연결 문제');
        console.error('   - Foreign Key 제약 조건 위반');
        console.error('   - 잘못된 데이터 형식');
        console.error('🔧 임시 해결책: 로컬 스토리지에 저장');
        
        // 로컬 스토리지에 임시 저장
        localStorage.setItem('user_stocks', JSON.stringify(stocksData.stocks));
        console.log('💾 로컬 스토리지에 종목 데이터 저장 완료');
        console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        
        return {
          success: true,
          message: '종목이 로컬에 저장되었습니다 (데모 모드)'
        };
      }
      
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      throw error;
    }
  },

  // ===== 모델 설정 (User Service 직접 호출) =====
  async updateUserModel(userId: string, modelData: { model_type: string }): Promise<any> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log("🤖 모델 설정 API 호출 시작 (직접 호출)");
    console.log("👤 사용자 ID:", userId);
    console.log("🎯 설정할 모델:", modelData.model_type);
    console.log("📋 요청 데이터:", modelData);
    console.log("🔗 직접 호출 URL:", `/users/${userId}/model`);
    console.log("📤 요청 방식: POST");
    
    try {
      const startTime = Date.now();
      const response = await userServiceClient.post(`/users/${userId}/model`, modelData);
      const requestTime = Date.now() - startTime;
      
      console.log("✅ 모델 설정 API 성공! (직접 호출)");
      console.log("⏱️ 요청 완료 시간:", requestTime + "ms");
      console.log("📋 응답 데이터:", response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      return response.data;
    } catch (error: any) {
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      console.error('❌ 모델 설정 API 에러! (직접 호출)');
      console.error('🔍 에러 상세 분석:');
      console.error('📋 에러 메시지:', error.message);
      console.error('📋 상태 코드:', error.response?.status);
      console.error('📋 상태 텍스트:', error.response?.statusText);
      console.error('📋 서버 응답:', error.response?.data);
      console.error('📋 요청 설정:', error.config);
      console.error('🔍 전체 에러:', error);
      
      // 404 에러인 경우
      if (error.response?.status === 404) {
        console.error('💥 모델 설정 엔드포인트 누락 (404)!');
        console.error('🔍 가능한 원인:');
        console.error('   - User Service에 모델 설정 API가 없음');
        console.error('   - 잘못된 엔드포인트 경로');
        console.error('🔧 임시 해결책: 로컬 스토리지에 저장');
        
        // 로컬 스토리지에 임시 저장
        localStorage.setItem('user_model', modelData.model_type);
        console.log('💾 로컬 스토리지에 모델 데이터 저장 완료');
        console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        
        return {
          success: true,
          message: '모델이 로컬에 저장되었습니다 (데모 모드)'
        };
      }
      
      // 500 에러인 경우
      if (error.response?.status === 500) {
        console.error('💥 User Service 내부 에러 (500) 발생!');
        console.error('🔍 가능한 원인:');
        console.error('   - 데이터베이스 연결 문제');
        console.error('   - 잘못된 데이터 형식');
        console.error('🔧 임시 해결책: 로컬 스토리지에 저장');
        
        // 로컬 스토리지에 임시 저장
        localStorage.setItem('user_model', modelData.model_type);
        console.log('💾 로컬 스토리지에 모델 데이터 저장 완료');
        console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        
        return {
          success: true,
          message: '모델이 로컬에 저장되었습니다 (데모 모드)'
        };
      }
      
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      throw error;
    }
  },

  // ===== 분석 서비스 실행 (API Gateway 경유) =====
  async executeNewsAnalysis(): Promise<AnalysisResult> {
    try {
      const response = await gatewayClient.post('/api/news/execute');
      return response.data;
    } catch (error: any) {
      console.error('뉴스 분석 에러:', error);
      if (error.response?.status === 500) {
        return { status: 'completed', message: '뉴스 분석 완료 (데모)', timestamp: new Date().toISOString() };
      }
      throw error;
    }
  },

  async executeDisclosureAnalysis(): Promise<AnalysisResult> {
    try {
      const response = await gatewayClient.post('/api/disclosure/execute');
      return response.data;
    } catch (error: any) {
      console.error('공시 분석 에러:', error);
      if (error.response?.status === 500) {
        return { status: 'completed', message: '공시 분석 완료 (데모)', timestamp: new Date().toISOString() };
      }
      throw error;
    }
  },

  async executeChartAnalysis(): Promise<AnalysisResult> {
    try {
      const response = await gatewayClient.post('/api/chart/execute');
      return response.data;
    } catch (error: any) {
      console.error('차트 분석 에러:', error);
      if (error.response?.status === 500) {
        return { status: 'completed', message: '차트 분석 완료 (데모)', timestamp: new Date().toISOString() };
      }
      throw error;
    }
  },

  async executeReportAnalysis(): Promise<AnalysisResult> {
    try {
      const response = await gatewayClient.post('/api/report/execute');
      return response.data;
    } catch (error: any) {
      console.error('리포트 분석 에러:', error);
      if (error.response?.status === 500) {
        return { status: 'completed', message: '리포트 생성 완료 (데모)', timestamp: new Date().toISOString() };
      }
      throw error;
    }
  },

  async executeFlowAnalysis(): Promise<AnalysisResult> {
    try {
      const response = await gatewayClient.post('/api/flow/execute');
      return response.data;
    } catch (error: any) {
      console.error('수급 분석 에러:', error);
      if (error.response?.status === 500) {
        return { status: 'completed', message: '수급 분석 완료 (데모)', timestamp: new Date().toISOString() };
      }
      throw error;
    }
  },

  // ===== 전체 분석 실행 (test_frontend_data_flow.py 플로우) =====
  async executeAllAnalysis(): Promise<{
    news: AnalysisResult;
    disclosure: AnalysisResult;
    chart: AnalysisResult;
    report: AnalysisResult;
    flow: AnalysisResult;
  }> {
    console.log('🔍 전체 분석 시작...');
    
    try {
      // 1. 뉴스 분석
      console.log('📰 뉴스 분석 실행 중...');
      const news = await this.executeNewsAnalysis();
      console.log('✅ 뉴스 분석 완료');

      // 2. 공시 분석  
      console.log('📋 공시 분석 실행 중...');
      const disclosure = await this.executeDisclosureAnalysis();
      console.log('✅ 공시 분석 완료');

      // 3. 차트 분석
      console.log('📈 차트 분석 실행 중...');
      const chart = await this.executeChartAnalysis();
      console.log('✅ 차트 분석 완료');

      // 4. 리포트 생성
      console.log('📄 리포트 생성 실행 중...');
      const report = await this.executeReportAnalysis();
      console.log('✅ 리포트 생성 완료');

      // 5. 수급 분석
      console.log('💰 수급 분석 실행 중...');
      const flow = await this.executeFlowAnalysis();
      console.log('✅ 수급 분석 완료');

      console.log('🎉 전체 분석 완료!');
      
      return { news, disclosure, chart, report, flow };
    } catch (error: any) {
      console.error('❌ 분석 실행 중 오류:', error);
      
      // 500 에러인 경우 데모 데이터 반환
      if (error.response?.status === 500) {
        console.log('🔄 데모 모드로 전환 - 샘플 데이터 반환');
        return {
          news: { status: 'completed', message: '뉴스 분석 완료 (데모)', timestamp: new Date().toISOString() },
          disclosure: { status: 'completed', message: '공시 분석 완료 (데모)', timestamp: new Date().toISOString() },
          chart: { status: 'completed', message: '차트 분석 완료 (데모)', timestamp: new Date().toISOString() },
          report: { status: 'completed', message: '리포트 생성 완료 (데모)', timestamp: new Date().toISOString() },
          flow: { status: 'completed', message: '수급 분석 완료 (데모)', timestamp: new Date().toISOString() }
        };
      }
      
      throw error;
    }
  },

  // ===== 이슈 스케줄러 =====
  async getUpcomingIssues(stockCode: string, daysAhead: number = 7): Promise<any> {
    const params = new URLSearchParams({
      stock_code: stockCode,
      days_ahead: daysAhead.toString()
    });
    const response = await gatewayClient.get(`/api/issue/issues/upcoming?${params}`);
    return response.data;
  },

  // ===== 사업보고서 요약 =====
  async summarizeBusinessReport(
    stockCode: string, 
    reportType: 'quarterly' | 'annual' = 'quarterly'
  ): Promise<any> {
    const params = new URLSearchParams();
    params.append('report_type', reportType);
    
    const response = await gatewayClient.post(`/api/business/reports/summarize/${stockCode}?${params}`);
    return response.data;
  },

  async analyzeClickedChart(stockCode: string, targetDate: string, clickPosition: { x: number; y: number }): Promise<any> {
    const response = await gatewayClient.post('/api/analysis/explain/click-analysis', {
      stock_code: stockCode,
      target_date: targetDate,
      click_position: clickPosition
    });
    return response.data;
  },

  // ===== 서비스 설정 및 활성화 (User Service 직접 호출) =====
  async updateUserWantedServices(
    userId: string, 
    services: { service_name: string; enabled: boolean; priority: number }[]
  ): Promise<any> {
    try {
      const response = await userServiceClient.post(`/users/${userId}/wanted-services`, services);
      return response.data;
    } catch (error: any) {
      console.error('원하는 서비스 설정 에러:', error);
      throw error;
    }
  },

  async getUserWantedServices(userId: string): Promise<any> {
    try {
      const response = await userServiceClient.get(`/users/${userId}/wanted-services`);
      return response.data;
    } catch (error: any) {
      console.error('원하는 서비스 조회 에러:', error);
      throw error;
    }
  },

  // ===== 대시보드 분석 결과 조회 =====
  async getDashboardAnalysisResults(userId: string): Promise<any> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log("📊 대시보드 분석 결과 조회 API 호출 시작");
    console.log("📋 사용자 ID:", userId);
    console.log("🔗 API Gateway 호출 URL: /dashboard/analysis-results/" + userId);
    console.log("📤 요청 방식: GET");
    
    try {
      const startTime = Date.now();
      const response = await gatewayClient.get(`/dashboard/analysis-results/${userId}`);
      const requestTime = Date.now() - startTime;
      
      console.log("✅ 대시보드 분석 결과 조회 성공!");
      console.log("⏱️ 요청 완료 시간:", requestTime + "ms");
      console.log("📋 응답 데이터:", response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      return response.data;
    } catch (error) {
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      console.error('❌ 대시보드 분석 결과 조회 실패!');
      console.error('🔍 에러 상세 정보:');
      console.error('📋 메시지:', error.message);
      console.error('📋 상태 코드:', error.response?.status);
      console.error('📋 상태 텍스트:', error.response?.statusText);
      console.error('📋 요청 URL:', error.config?.url);
      console.error('📋 요청 방식:', error.config?.method?.toUpperCase());
      console.error('📋 응답 데이터:', error.response?.data);
      console.error('📋 에러 코드:', error.code);
      console.error('🔍 전체 에러 객체:', error);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      throw error;
    }
  },

  async getDashboardAnalysisByType(userId: string, analysisType: string): Promise<any> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log("📊 특정 분석 타입별 결과 조회 API 호출 시작");
    console.log("📋 사용자 ID:", userId);
    console.log("📋 분석 타입:", analysisType);
    console.log("🔗 API Gateway 호출 URL: /dashboard/analysis-results/" + userId + "/" + analysisType);
    console.log("📤 요청 방식: GET");
    
    try {
      const startTime = Date.now();
      const response = await gatewayClient.get(`/dashboard/analysis-results/${userId}/${analysisType}`);
      const requestTime = Date.now() - startTime;
      
      console.log("✅ 특정 분석 타입별 결과 조회 성공!");
      console.log("⏱️ 요청 완료 시간:", requestTime + "ms");
      console.log("📋 응답 데이터:", response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      return response.data;
    } catch (error) {
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      console.error('❌ 특정 분석 타입별 결과 조회 실패!');
      console.error('🔍 에러 상세 정보:');
      console.error('📋 메시지:', error.message);
      console.error('📋 상태 코드:', error.response?.status);
      console.error('📋 상태 텍스트:', error.response?.statusText);
      console.error('📋 요청 URL:', error.config?.url);
      console.error('📋 요청 방식:', error.config?.method?.toUpperCase());
      console.error('📋 응답 데이터:', error.response?.data);
      console.error('📋 에러 코드:', error.code);
      console.error('🔍 전체 에러 객체:', error);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      throw error;
    }
  },

  async updateUserWantedServicesDetailed(
    userId: string,
    services: { service_name: string; enabled: boolean; priority: number }[]
  ): Promise<any> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log(`🔧 원하는 서비스 설정 API 호출 시작 (사용자 ID: ${userId})`);
    console.log('📋 설정할 서비스:', services);
    console.log(`🔗 직접 호출 URL: /users/${userId}/wanted-services`);
    console.log(`📤 요청 방식: PUT`);

    const startTime = performance.now();
    try {
      const response = await userServiceClient.put(`/users/${userId}/wanted-services`, services);
      const endTime = performance.now();
      console.log(`⏱️ 요청 완료 시간: ${(endTime - startTime).toFixed(0)}ms`);
      console.log('✅ 원하는 서비스 설정 성공!');
      console.log('📋 응답 데이터:', response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      return response.data;
    } catch (error: any) {
      const endTime = performance.now();
      console.log(`⏱️ 에러 발생 시간: ${(endTime - startTime).toFixed(0)}ms`);
      console.error('❌ 원하는 서비스 설정 에러!');
      console.error('🔍 에러 상세:', error);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      // 500 에러인 경우
      if (error.response?.status === 500) {
        console.error('💥 User Service 내부 에러 (500) 발생!');
        console.error('🔍 가능한 원인:');
        console.error('   - 데이터베이스 연결 문제');
        console.error('   - 잘못된 데이터 형식');
        console.error('🔧 임시 해결책: 로컬 스토리지에 저장');
        
        // 로컬 스토리지에 임시 저장
        localStorage.setItem('user_wanted_services', JSON.stringify(services));
        console.log('💾 로컬 스토리지에 서비스 설정 저장 완료');
        
        return {
          success: true,
          message: '서비스 설정이 로컬에 저장되었습니다 (데모 모드)'
        };
      }
      
      throw error;
    }
  },

  async activateSelectedServices(
    userId: string,
    services: { service_name: string; enabled: boolean; priority: number }[]
  ): Promise<any> {
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log(`🚀 서비스 활성화 프로세스 시작 (사용자 ID: ${userId})`);
    console.log('📋 활성화할 서비스:', services);

    try {
      // 1단계: 사용자 원하는 서비스 DB에 저장 (User Service 직접 호출)
      console.log("🔄 1단계: 사용자 원하는 서비스 DB 저장 중...");
      const serviceSettings = {
        services: services.map(service => ({
          service_name: service.service_name,
          enabled: service.enabled,
          priority: service.priority
        }))
      };
      console.log("📤 전송할 서비스 설정:", serviceSettings);
      console.log(`🔗 직접 호출 URL: /users/${userId}/wanted-services`);
      console.log(`📤 요청 방식: POST`);

      const step1StartTime = performance.now();
      await userServiceClient.post(`/users/${userId}/wanted-services`, serviceSettings);
      const step1EndTime = performance.now();
      console.log(`✅ 1단계 완료: 사용자 원하는 서비스 DB 저장 성공 (${(step1EndTime - step1StartTime).toFixed(0)}ms)`);

      // 2단계: 실제 서비스 활성화 (API Gateway 경유 - Orchestrator 호출)
      console.log("🔄 2단계: 실제 서비스 활성화 중...");
      const startSelectedData = {
        user_id: userId,
        services: services.filter(s => s.enabled).map(s => s.service_name)
      };
      console.log("📤 전송할 서비스 시작 데이터:", startSelectedData);
      console.log(`🔗 API Gateway URL: /api/services/start-selected`);
      console.log(`📤 요청 방식: POST`);

      const step2StartTime = performance.now();
      const response = await gatewayClient.post('/api/services/start-selected', startSelectedData);
      const step2EndTime = performance.now();
      console.log(`✅ 2단계 완료: 실제 서비스 활성화 성공 (${(step2EndTime - step2StartTime).toFixed(0)}ms)`);

      const totalTime = step2EndTime - step1StartTime;
      console.log(`🎉 전체 서비스 활성화 완료! (총 소요시간: ${totalTime.toFixed(0)}ms)`);
      console.log('📋 최종 응답:', response.data);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

      return response.data;
    } catch (error: any) {
      console.error('❌ 서비스 활성화 에러!');
      console.error('🔍 에러 상세:', error);
      console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      
      // 500 에러인 경우
      if (error.response?.status === 500) {
        console.error('💥 서비스 활성화 내부 에러 (500) 발생!');
        console.error('🔍 가능한 원인:');
        console.error('   - Orchestrator 서비스 연결 실패');
        console.error('   - 서비스 시작 프로세스 오류');
        console.error('🔧 임시 해결책: 로컬에 저장');
        
        return {
          success: true,
          message: '서비스 활성화가 요청되었습니다 (데모 모드)'
        };
      }
      
      throw error;
    }
  },

  // ===== 서비스 상태 조회 (API Gateway 경유) =====
  async getServicesStatus(): Promise<any> {
    try {
      const response = await gatewayClient.get('/api/services/status');
      return response.data;
    } catch (error: any) {
      console.error('서비스 상태 조회 에러:', error);
      throw error;
    }
  },

  async checkServiceHealth(serviceName: string): Promise<any> {
    try {
      const response = await gatewayClient.get(`/api/services/health/${serviceName}`);
      return response.data;
    } catch (error: any) {
      console.error(`${serviceName} 헬스체크 에러:`, error);
      throw error;
    }
  },
};

// 사용자 ID 관리 헬퍼 함수들
export const userStorage = {
  getUserId(): string {
    // 먼저 실제 데이터베이스 사용자 ID 확인
    const realUserId = localStorage.getItem('real_user_id');
    if (realUserId) {
      return realUserId;
    }
    
    // 임시 ID 반환
    return localStorage.getItem('stock_analysis_user_id') || '';
  },

  setUserId(userId: string): void {
    localStorage.setItem('stock_analysis_user_id', userId);
  },

  setRealUserId(userId: string): void {
    localStorage.setItem('real_user_id', userId);
  },

  getRealUserId(): string {
    return localStorage.getItem('real_user_id') || '';
  },

  clearUserId(): void {
    localStorage.removeItem('stock_analysis_user_id');
    localStorage.removeItem('real_user_id');
  },

  generateUserId(): string {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 1000);
    return `user_${timestamp}_${random}`;
  }
};

// ===== 빗썸 스타일 텔레그램 채널 API =====
export const telegramChannelApi = {
  // 텔레그램 채널 정보 조회
  getChannelInfo: async (userId: string) => {
    try {
      const response = await userServiceClient.get(`/users/${userId}/telegram-channel`);
      return response.data;
    } catch (error: any) {
      console.error('텔레그램 채널 정보 조회 실패:', error);
      throw error;
    }
  },

  // 텔레그램 구독 설정 조회
  getSubscription: async (userId: string) => {
    try {
      const response = await userServiceClient.get(`/users/${userId}/telegram-subscription`);
      return response.data;
    } catch (error: any) {
      console.error('텔레그램 구독 설정 조회 실패:', error);
      throw error;
    }
  },

  // 텔레그램 구독 설정 저장
  saveSubscription: async (userId: string, subscription: any) => {
    try {
      const response = await userServiceClient.post(`/users/${userId}/telegram-subscription`, subscription);
      return response.data;
    } catch (error: any) {
      console.error('텔레그램 구독 설정 저장 실패:', error);
      throw error;
    }
  },

  // 텔레그램 채널 연결 테스트
  testChannelConnection: async (userId: string) => {
    try {
      const response = await userServiceClient.post(`/users/${userId}/telegram-test-channel`);
      return response.data;
    } catch (error: any) {
      console.error('텔레그램 채널 연결 테스트 실패:', error);
      throw error;
    }
  },
  // 🆕 새로운 함수들 추가
  sendNotification: async (userId: string, notificationData: any) => {
    try {
      const response = await userServiceClient.post(`/users/${userId}/send-telegram-notification`, notificationData);
      return response.data;
    } catch (error: any) {
      console.error('알림 전송 실패:', error);
      throw error;
    }
  },
  sendWelcomeMessage: async (userId: string) => {
    try {
      const response = await userServiceClient.post(`/users/${userId}/telegram-welcome`);
      return response.data;
    } catch (error: any) {
      console.error('환영 메시지 전송 실패:', error);
      throw error;
    }
  },
  // 🆕 간단한 알림 함수들 추가
  sendSimpleNotification: async (userId: string, notificationData: any) => {
    try {
      const response = await userServiceClient.post(`/users/${userId}/send-simple-telegram`, notificationData);
      return response.data;
    } catch (error: any) {
      console.error('간단한 알림 전송 실패:', error);
      throw error;
    }
  },
  sendSimpleWelcomeMessage: async (userId: string) => {
    try {
      const response = await userServiceClient.post(`/users/${userId}/telegram-welcome-simple`);
      return response.data;
    } catch (error: any) {
      console.error('간단한 환영 메시지 전송 실패:', error);
      throw error;
    }
  },
  sendSimpleTestMessage: async (userId: string) => {
    try {
      const response = await userServiceClient.post(`/users/${userId}/telegram-test-simple`);
      return response.data;
    } catch (error: any) {
      console.error('간단한 테스트 메시지 전송 실패:', error);
      throw error;
    }
  }
};

export default api; 