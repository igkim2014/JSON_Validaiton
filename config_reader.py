"""
config.txt 파일을 읽고 검색할 값을 추출하는 모듈
"""
import re
import os

class ConfigReader:
    @staticmethod
    def read_config_file(file_path):
        """
        config.txt 파일에서 검색할 값들을 읽어옵니다.
        다음과 같은 형식을 지원합니다:
        1. 값만 직접 나열된 형식 (예: TE02.03.01)
        2. '* 값' 형식 (예: * TE02.03.01)
        3. 'ID: 값' 형식 (예: ID: TE02.03.01)
        
        Args:
            file_path (str): 설정 파일 경로
            
        Returns:
            list: 검색할 값들의 리스트
        
        Raises:
            Exception: 파일 읽기 중 오류 발생 시
        """
        search_values = []
        
        if not os.path.exists(file_path):
            raise Exception(f"파일을 찾을 수 없습니다: {file_path}")
        
        try:
            # 다양한 인코딩으로 시도
            encodings = ['utf-8', 'euc-kr', 'cp949']
            file_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        file_content = file.read()
                    break  # 성공적으로 읽었으면 루프 종료
                except UnicodeDecodeError:
                    continue
            
            if file_content is None:
                raise Exception("파일 인코딩을 확인할 수 없습니다.")
            
            # 여러 형식의 라인을 처리
            lines = file_content.splitlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue  # 빈 줄이나 주석 줄 무시
                
                # 1. 패턴 1: '* 값' 형식
                match = re.search(r'^\*\s*(.*?)\s*$', line)
                if match and match.group(1):
                    search_values.append(match.group(1))
                    continue
                
                # 2. 패턴 2: 'ID: 값' 형식
                match = re.search(r'ID:\s*(.*?)\s*$', line)
                if match and match.group(1):
                    search_values.append(match.group(1))
                    continue
                
                # 3. 패턴 3: 값만 있는 형식 (TE02.03.01 같은 형식)
                # TE로 시작하는 값 패턴 (예: TE02.03.01)
                if re.match(r'^TE\d+\.\d+\.\d+$', line):
                    search_values.append(line)
                    continue
                
                # 4. 일반적인 값 패턴 (alphanumeric과 '.', '-', '_'만 포함된 값)
                if re.match(r'^[a-zA-Z0-9\.\-_]+$', line):
                    search_values.append(line)
                    continue
            
            # 중복 제거
            search_values = list(dict.fromkeys(search_values))
            
            # 디버깅을 위한 출력
            if not search_values:
                print(f"경고: '{file_path}' 파일에서 검색할 값을 찾을 수 없습니다.")
                print(f"파일 내용: \n{file_content}")
            
            return search_values
            
        except Exception as e:
            raise Exception(f"Config 파일 읽기 오류: {str(e)}")
    
    @staticmethod
    def create_sample_config_file(file_path):
        """
        샘플 config.txt 파일을 생성합니다.
        
        Args:
            file_path (str): 생성할 파일 경로
        """
        # 사용자가 제공한 형식으로 샘플 생성
        sample_content = """# 검색할 값 목록
# 각 줄에 검색할 값을 입력하세요

TE02.03.01
TE02.07.02
TE02.09.01
TE02.10.01
TE02.11.01
"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(sample_content)
            return True
        except Exception:
            return False