import pandas as pd
import json
import os

def convert_excel_to_json():
    """
    엑셀 파일에서 종목 데이터를 읽어서 JSON 형태로 변환
    """
    try:
        # 엑셀 파일 경로들
        excel_files = [
            "../data_1301_20250727.xlsx",
            "../data_1322_20250727.xlsx"
        ]
        
        # 모든 종목 데이터를 저장할 리스트
        all_stocks_data = []
        
        for excel_file in excel_files:
            print(f"\n엑셀 파일 읽는 중: {excel_file}")
            
            try:
                df = pd.read_excel(excel_file)
            except Exception as e:
                print(f"파일 {excel_file} 읽기 실패: {e}")
                continue
        
            # 데이터 구조 확인
            print(f"엑셀 파일의 열 정보:")
            print(df.columns.tolist())
            print(f"\n첫 5행 데이터:")
            print(df.head())
            
            # 열 이름을 확인하고 매핑
            # 일반적인 열 이름 패턴들을 체크
            possible_code_columns = ['종목코드', '코드', 'Code', 'STOCK_CODE', '종목 코드']
            possible_name_columns = ['종목명', '회사명', '종목', 'Name', 'COMPANY_NAME', '회사 이름']
            possible_sector_columns = ['업종', '업종명', 'Sector', 'SECTOR', '산업', '업종 명']
            
            code_column = None
            name_column = None
            sector_column = None
            
            # 열 이름 찾기
            for col in df.columns:
                if col in possible_code_columns:
                    code_column = col
                elif col in possible_name_columns:
                    name_column = col
                elif col in possible_sector_columns:
                    sector_column = col
            
            print(f"\n매핑된 열:")
            print(f"종목코드 열: {code_column}")
            print(f"종목명 열: {name_column}")
            print(f"업종 열: {sector_column}")
            
            if not code_column or not name_column:
                print("Error: 필수 열(종목코드, 종목명)을 찾을 수 없습니다.")
                print("사용 가능한 열:", df.columns.tolist())
                continue
            
            # JSON 형태로 변환
            file_stocks_data = []
            
            for _, row in df.iterrows():
                # 종목코드를 문자열로 변환 (숫자일 경우 6자리로 패딩)
                stock_code = str(row[code_column]).zfill(6) if pd.notna(row[code_column]) else None
                company_name = row[name_column] if pd.notna(row[name_column]) else None
                sector = row[sector_column] if sector_column and pd.notna(row[sector_column]) else "기타"
                
                # 유효한 데이터만 추가
                if stock_code and company_name:
                    file_stocks_data.append({
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "sector": sector
                    })
            
            print(f"파일에서 {len(file_stocks_data)}개의 종목 데이터 변환 완료")
            all_stocks_data.extend(file_stocks_data)
        
        # 중복 제거 (종목코드 기준)
        unique_stocks = {}
        for stock in all_stocks_data:
            stock_code = stock['stock_code']
            if stock_code not in unique_stocks:
                unique_stocks[stock_code] = stock
            else:
                # 중복 발견 시 알림
                existing = unique_stocks[stock_code]
                print(f"중복 종목 발견: {stock_code} - {existing['company_name']} vs {stock['company_name']}")
        
        # 최종 종목 리스트
        stocks_data = list(unique_stocks.values())
        
        print(f"\n총 {len(stocks_data)}개의 고유 종목 데이터 변환 완료 (중복 제거 후)")
        
        # JSON 파일로 저장
        output_file = "frontend/src/data/stocks.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stocks_data, f, ensure_ascii=False, indent=2)
        
        print(f"JSON 파일 저장 완료: {output_file}")
        
        # 샘플 데이터 출력
        print(f"\n샘플 데이터 (처음 10개):")
        for stock in stocks_data[:10]:
            print(f"  {stock['stock_code']}: {stock['company_name']} ({stock['sector']})")
        
        return stocks_data
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    convert_excel_to_json() 