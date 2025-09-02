"""
JSONValidator 모듈 - NoneType 오류 수정 버전
"""
import json
import os
import re
import base64
from io import BytesIO
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL 모듈을 찾을 수 없습니다. '다음 명령으로 설치할 수 있습니다: pip install pillow'")

class JSONValidator:
    def __init__(self):
        """JSON 검증 기능 초기화"""
        self.json_data = None
        self.debug_mode = True  # 디버그 모드 활성화
        
    def load_json_file(self, file_path):
        """
        JSON 파일을 읽어서 파싱
        
        Args:
            file_path (str): JSON 파일 경로
            
        Returns:
            bool: 성공 여부
            
        Raises:
            json.JSONDecodeError: 유효하지 않은 JSON 파일
            FileNotFoundError: 파일을 찾을 수 없음
            Exception: 기타 오류
        """
        if self.debug_mode:
            print(f"JSON 파일 로드 중: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            if self.debug_mode:
                print(f"JSON 파일 로드 완료. 페이지 수: {len(self.json_data.get('pages', []))}")
            return True
        except FileNotFoundError:
            if self.debug_mode:
                print(f"오류: 파일을 찾을 수 없음 - {file_path}")
            self.json_data = None
            return False
        except json.JSONDecodeError as e:
            if self.debug_mode:
                print(f"오류: 유효하지 않은 JSON 파일 - {e}")
            self.json_data = None
            return False
        except Exception as e:
            if self.debug_mode:
                print(f"오류: JSON 파일 로드 중 기타 오류 - {e}")
            self.json_data = None
            return False
    
    def search_value(self, search_values):
        """
        여러 값들을 JSON 데이터에서 검색
        
        Args:
            search_values (list): 검색할 값들의 리스트
            
        Returns:
            tuple: (찾은 값 딕셔너리, 못 찾은 값 리스트)
        """
        if self.debug_mode:
            print(f"검색 값: {search_values}")
        found_items = {}
        not_found_items = []
        
        if self.json_data is None:
            if self.debug_mode:
                print("오류: JSON 데이터가 로드되지 않음")
            return found_items, search_values if search_values else []
        
        if not search_values or not isinstance(search_values, (list, tuple)):
            if self.debug_mode:
                print("오류: search_values가 None이거나 리스트가 아님")
            return found_items, []
        
        for value in search_values:
            if value is None:
                continue
                
            paths = []
            value_str = str(value)
            
            pages = self.json_data.get("pages", [])
            if pages is None:
                pages = []
                
            for page in pages:
                if page is None:
                    continue
                    
                page_text = page.get("text", "")
                if page_text is None:
                    page_text = ""
                    
                if value_str in page_text:
                    page_num = page.get('page_number', 'Unknown')
                    paths.append(f"페이지 {page_num}")
                
                text_blocks = page.get("text_blocks", [])
                if text_blocks is None:
                    text_blocks = []
                    
                for text_block in text_blocks:
                    if text_block is None:
                        continue
                        
                    if 'text' in text_block:
                        block_text = text_block.get('text', '')
                        if block_text is None:
                            block_text = ''
                            
                        if value_str in block_text:
                            page_num = page.get('page_number', 'Unknown')
                            paths.append(f"페이지 {page_num} - 텍스트 블록")
                
                tables = page.get("tables", [])
                if tables is None:
                    tables = []
                    
                for table in tables:
                    if table is None:
                        continue
                        
                    caption = table.get("caption", "")
                    if caption is None:
                        caption = ""
                        
                    cells = table.get("cells", [])
                    if cells is None:
                        cells = []
                    cells_str = str(cells)
                    
                    if value_str in caption or value_str in cells_str:
                        page_num = page.get('page_number', 'Unknown')
                        table_caption = caption if caption else 'No Caption'
                        paths.append(f"페이지 {page_num} - 테이블: {table_caption}")
            
            if paths:
                found_items[value] = paths
            else:
                not_found_items.append(value)
        
        if self.debug_mode:
            print(f"찾은 항목: {found_items}")
            print(f"찾지 못한 항목: {not_found_items}")
        
        return found_items, not_found_items
    
    def _search_in_json(self, json_data, search_value, path=""):
        """
        JSON 데이터에서 특정 값을 재귀적으로 검색
        
        Args:
            json_data (dict/list): 검색할 JSON 데이터
            search_value (str): 검색할 값
            path (str): 현재 탐색 중인 JSON 경로
            
        Returns:
            list: 발견된 경로 리스트
        """
        found_paths = []
        
        if json_data is None:
            if self.debug_mode:
                print("오류: json_data가 None임")
            return found_paths
        
        if search_value is None:
            return found_paths
            
        search_value_str = str(search_value)
        
        if isinstance(json_data, dict):
            for key, value in json_data.items():
                if key is None or value is None:
                    continue
                    
                new_path = f"{path}.{key}" if path else key
                
                if str(key) == search_value_str:
                    found_paths.append(f"{new_path} = {value}")
                elif str(value) == search_value_str:
                    found_paths.append(f"{new_path} = {value}")
                    
                if key == "caption" and isinstance(value, str) and value is not None and search_value_str in value:
                    found_paths.append(f"{new_path} = {value}")
                
                if key == "file_path" and isinstance(value, str) and value is not None and search_value_str in value:
                    found_paths.append(f"{new_path} = {value}")
                
                if key == "pages" and isinstance(value, list) and value is not None:
                    for i, page in enumerate(value):
                        if page is None:
                            continue
                        page_index_path = f"{new_path}[{i}]"
                        actual_page_num = i + 1
                        
                        if isinstance(page, dict):
                            page_specific_paths = self._search_in_json(
                                page, 
                                search_value, 
                                f"{page_index_path}(페이지 {actual_page_num})"
                            )
                            found_paths.extend(page_specific_paths)
                    continue
                
                if key == "tables" and isinstance(value, list) and value is not None:
                    for i, table in enumerate(value):
                        if table is None:
                            continue
                        table_path = f"{new_path}[{i}]"
                        if isinstance(table, dict):
                            table_specific_paths = self._search_in_json(
                                table, 
                                search_value, 
                                f"{table_path}(테이블 {i+1})"
                            )
                            found_paths.extend(table_specific_paths)
                    continue
                
                if key == "cells" and isinstance(value, list) and value is not None:
                    for i, cell in enumerate(value):
                        if cell is None:
                            continue
                        cell_path = f"{new_path}[{i}]"
                        if isinstance(cell, dict):
                            cell_specific_paths = self._search_in_json(
                                cell, 
                                search_value, 
                                f"{cell_path}(셀 {i+1})"
                            )
                            found_paths.extend(cell_specific_paths)
                    continue
                
                if isinstance(value, (dict, list)) and value is not None:
                    sub_paths = self._search_in_json(value, search_value, new_path)
                    found_paths.extend(sub_paths)
                    
        elif isinstance(json_data, list):
            for i, item in enumerate(json_data):
                if item is None:
                    continue
                    
                new_path = f"{path}[{i}]"
                
                if str(item) == search_value_str:
                    found_paths.append(f"{new_path} = {item}")
                
                if isinstance(item, (dict, list)):
                    sub_paths = self._search_in_json(item, search_value, new_path)
                    found_paths.extend(sub_paths)
        
        return found_paths

    def format_search_results(self, results):
        """
        검색 결과를 읽기 쉬운 형식으로 포맷
        
        Args:
            results (dict): search_value 함수의 결과
            
        Returns:
            str: 포맷된 검색 결과
        """
        output = "검증 결과:\n"
        output += "=" * 50 + "\n"
        
        if not results:
            output += "검색된 항목이 없습니다.\n"
            return output
        
        for value, paths in results.items():
            output += f"✓ 항목 '{value}' 발견:\n"
            for path in paths:
                output += f"  - {path}\n"
            output += "\n"
        
        return output
    
    def find_test_result_table(self, te_number):
        """
        TE 번호에 해당하는 시험결과판정근거 테이블을 찾음
        
        Args:
            te_number (str): 검색할 TE 번호 (예: "TE02.03.01")
            
        Returns:
            dict: 시험결과판정근거 테이블 정보 또는 None
        """
        if self.json_data is None:
            if self.debug_mode:
                print("오류: JSON 데이터가 로드되지 않음")
            return None
        
        if te_number is None:
            if self.debug_mode:
                print("오류: te_number가 None임")
            return None
            
        te_number_str = str(te_number)
        debug_info = {"searched_tables": [], "searched_text_blocks": []}
            
        pages = self.json_data.get("pages", [])
        if pages is None:
            pages = []
            
        for page_idx, page in enumerate(pages):
            if page is None:
                continue
                
            # 1. 테이블에서 검색
            tables = page.get("tables", [])
            if tables is None:
                tables = []
                
            for table_idx, table in enumerate(tables):
                if table is None:
                    continue
                    
                table_debug = {
                    "page_idx": page_idx,
                    "table_idx": table_idx,
                    "table_id": table.get("table_id", ""),
                    "caption": table.get("caption", ""),
                    "has_cells": "cells" in table,
                    "has_image": "image" in table,
                    "te_number_in_caption": False,
                    "te_number_match": False,
                    "result_table_match": False
                }
                
                caption = table.get("caption", "")
                if caption and te_number_str in caption and "시험결과판정근거" in caption:
                    table_debug["te_number_match"] = True
                    table_debug["result_table_match"] = True
                    debug_info["matched_table"] = table_debug
                    if self.debug_mode:
                        print(f"테이블 발견: 페이지 {page_idx+1}, 테이블 {table_idx}, 캡션: {caption}")
                    return {
                        "page_index": page_idx,
                        "table_index": table_idx,
                        "page_number": page_idx + 1,
                        "table_data": table
                    }
                
                if "image" in table and isinstance(table.get("image"), dict):
                    file_path = table["image"].get("file_path", "")
                    if file_path and te_number_str in file_path and "시험결과판정근거" in file_path:
                        table_debug["te_number_match"] = True
                        table_debug["result_table_match"] = True
                        debug_info["matched_table"] = table_debug
                        if self.debug_mode:
                            print(f"테이블 발견: 페이지 {page_idx+1}, 테이블 {table_idx}, 파일 경로: {file_path}")
                        return {
                            "page_index": page_idx,
                            "table_index": table_idx,
                            "page_number": page_idx + 1,
                            "table_data": table
                        }
                
                has_te_match = False
                is_result_table = False
                cells = table.get("cells", [])
                if cells is None:
                    cells = []
                    
                if isinstance(cells, list):
                    for cell in cells:
                        if cell is None:
                            continue
                        cell_text = cell.get("text", "")
                        if cell_text is None:
                            cell_text = ""
                        if "시험결과판정근거" in cell_text:
                            is_result_table = True
                            table_debug["result_table_match"] = True
                        if te_number_str in cell_text:
                            has_te_match = True
                            table_debug["te_number_match"] = True
                    
                    if is_result_table and has_te_match:
                        debug_info["matched_table"] = table_debug
                        if self.debug_mode:
                            print(f"테이블 발견: 페이지 {page_idx+1}, 테이블 {table_idx}, 셀에서 매칭")
                        return {
                            "page_index": page_idx,
                            "table_index": table_idx,
                            "page_number": page_idx + 1,
                            "table_data": table
                        }
                
                debug_info["searched_tables"].append(table_debug)
            
            # 2. text_blocks에서 검색 (조건 완화)
            text_blocks = page.get("text_blocks", [])
            if text_blocks is None:
                text_blocks = []
                
            for block_idx, text_block in enumerate(text_blocks):
                if text_block is None:
                    continue
                    
                block_text = text_block.get("text", "")
                if block_text is None:
                    block_text = ""
                    
                text_block_debug = {
                    "page_idx": page_idx,
                    "block_idx": block_idx,
                    "text": block_text[:50] + "..." if len(block_text) > 50 else block_text,
                    "te_number_match": False,
                    "result_table_match": False
                }
                
                # 조건 완화: TE 번호만 있으면 가상 테이블 생성
                if te_number_str in block_text:
                    text_block_debug["te_number_match"] = True
                    debug_info["matched_text_block"] = text_block_debug
                    
                    # 가상 테이블 데이터 생성
                    if self.debug_mode:
                        print(f"text_block에서 TE 번호 발견: 페이지 {page_idx+1}, 블록 {block_idx}, 텍스트: {block_text[:50]}...")
                    return {
                        "page_index": page_idx,
                        "table_index": -1,  # 테이블이 아닌 text_block에서 찾았으므로 -1
                        "page_number": page_idx + 1,
                        "table_data": {
                            "caption": f"{te_number_str} 시험결과판정근거 (Text Block)",
                            "cells": [
                                {"row_idx": 0, "col_idx": 0, "text": te_number_str},
                                {"row_idx": 0, "col_idx": 1, "text": "시험결과판정근거"},
                                {"row_idx": 1, "col_idx": 0, "text": "내용"},
                                {"row_idx": 1, "col_idx": 1, "text": block_text[:100]}  # 텍스트 블록 내용 추가
                            ]
                        }
                    }
                
                debug_info["searched_text_blocks"].append(text_block_debug)
        
        # 3. 느슨한 조건으로 테이블 검색
        for page_idx, page in enumerate(pages):
            if page is None:
                continue
            tables = page.get("tables", [])
            if tables is None:
                tables = []
            for table_idx, table in enumerate(tables):
                if table is None:
                    continue
                caption = table.get("caption", "")
                if caption and te_number_str in caption:
                    if self.debug_mode:
                        print(f"느슨한 조건으로 테이블 발견: 페이지 {page_idx+1}, 테이블 {table_idx}, 캡션: {caption}")
                    return {
                        "page_index": page_idx,
                        "table_index": table_idx,
                        "page_number": page_idx + 1,
                        "table_data": table
                    }
        
        # 4. 느슨한 조건으로 파일 경로 검색
        for page_idx, page in enumerate(pages):
            if page is None:
                continue
            tables = page.get("tables", [])
            if tables is None:
                tables = []
            for table_idx, table in enumerate(tables):
                if table is None:
                    continue
                if "image" in table and isinstance(table.get("image"), dict):
                    file_path = table["image"].get("file_path", "")
                    if file_path and te_number_str in file_path:
                        if self.debug_mode:
                            print(f"느슨한 조건으로 테이블 발견: 페이지 {page_idx+1}, 테이블 {table_idx}, 파일 경로: {file_path}")
                        return {
                            "page_index": page_idx,
                            "table_index": table_idx,
                            "page_number": page_idx + 1,
                            "table_data": table
                        }
        
        # 5. 느슨한 조건으로 테이블 ID 검색
        for page_idx, page in enumerate(pages):
            if page is None:
                continue
            tables = page.get("tables", [])
            if tables is None:
                tables = []
            for table_idx, table in enumerate(tables):
                if table is None:
                    continue
                table_id = table.get("table_id", "")
                if table_id and te_number_str in table_id:
                    if self.debug_mode:
                        print(f"느슨한 조건으로 테이블 발견: 페이지 {page_idx+1}, 테이블 {table_idx}, 테이블 ID: {table_id}")
                    return {
                        "page_index": page_idx,
                        "table_index": table_idx,
                        "page_number": page_idx + 1,
                        "table_data": table
                    }
        
        if self.debug_mode:
            print(f"디버그 정보: {json.dumps(debug_info, indent=2, ensure_ascii=False)}")
        return None
    
    def get_test_result_table_data(self, te_number):
        """
        TE 번호에 해당하는 시험결과판정근거 테이블 데이터를 가져옴
        
        Args:
            te_number (str): 검색할 TE 번호 (예: "TE02.03.01")
            
        Returns:
            dict: 테이블 데이터 또는 None
        """
        if self.json_data is None:
            if self.debug_mode:
                print("오류: JSON 데이터가 로드되지 않음")
            return None
        
        if te_number is None:
            if self.debug_mode:
                print("오류: te_number가 None임")
            return None
        
        # 시험결과판정근거 테이블 찾기
        table_info = self.find_test_result_table(te_number)
        if not table_info:
            if self.debug_mode:
                print(f"테이블을 찾을 수 없음: {te_number}")
            return None
        
        # 테이블 데이터 포맷팅
        table_data = table_info["table_data"]
        if table_data is None:
            return None
            
        page_number = table_info["page_number"]
        table_number = table_info["table_index"]
        
        # text_block에서 찾은 경우
        if table_number == -1:
            cells = table_data.get("cells", [])
            return {
                "page_number": page_number,
                "table_number": table_number,
                "te_number": te_number,
                "has_image": False,
                "rows": 2,
                "cols": 2,
                "grid": [
                    [te_number, "시험결과판정근거"],
                    [cells[2]["text"] if len(cells) > 2 else "내용", cells[3]["text"] if len(cells) > 3 else ""]
                ],
                "cells": cells,
                "caption": table_data.get("caption", "")
            }
        
        # 이미지 여부 확인
        has_image = "image" in table_data and isinstance(table_data.get("image"), dict)
        
        # 이미지가 있는 경우 이미지 정보 반환
        if has_image:
            return {
                "page_number": page_number,
                "table_number": table_number,
                "te_number": te_number,
                "has_image": True,
                "image_data": table_data["image"],
                "caption": table_data.get("caption", "")
            }
        
        # 셀 데이터가 있는 경우 셀 정보 반환
        cells = table_data.get("cells", [])
        if cells is None:
            cells = []
            
        if isinstance(cells, list) and len(cells) > 0:
            # 셀 데이터 정리
            rows = table_data.get("rows", 0)
            cols = table_data.get("cols", 0)
            
            # 행과 열 수가 명시적으로 지정되지 않은 경우 셀 데이터에서 유추
            if rows == 0 or cols == 0:
                max_row = 0
                max_col = 0
                for cell in cells:
                    if cell is None:
                        continue
                    row = cell.get("row_idx", cell.get("row", 0))
                    col = cell.get("col_idx", cell.get("col", 0))
                    if row is None:
                        row = 0
                    if col is None:
                        col = 0
                    max_row = max(max_row, row)
                    max_col = max(max_col, col)
                rows = max_row + 1
                cols = max_col + 1
            
            # 2D 그리드로 변환
            grid = [[" " for _ in range(cols)] for _ in range(rows)]
            
            for cell in cells:
                if cell is None:
                    continue
                row = cell.get("row_idx", cell.get("row", 0))
                col = cell.get("col_idx", cell.get("col", 0))
                text = cell.get("text", "")
                
                if row is None:
                    row = 0
                if col is None:
                    col = 0
                if text is None:
                    text = ""
                
                if 0 <= row < rows and 0 <= col < cols:
                    grid[row][col] = text
            
            return {
                "page_number": page_number,
                "table_number": table_number,
                "rows": rows,
                "cols": cols,
                "grid": grid,
                "cells": cells,
                "te_number": te_number,
                "has_image": False,
                "caption": table_data.get("caption", "")
            }
        
        # 셀 데이터도 이미지도 없는 경우
        return None
    
    def create_table_image(self, table_data):
        """
        테이블 데이터로부터 이미지를 생성
        
        Args:
            table_data (dict): 테이블 데이터
            
        Returns:
            PIL.Image 또는 None: 생성된 이미지
        """
        if not PIL_AVAILABLE:
            if self.debug_mode:
                print("오류: PIL 모듈이 설치되지 않음")
            return None
            
        if table_data is None:
            if self.debug_mode:
                print("오류: table_data가 None임")
            return None
            
        if table_data.get("has_image", False) and "image_data" in table_data:
            try:
                image_data = table_data["image_data"]
                if image_data is None:
                    return None
                    
                base64_data = image_data.get("base64", "")
                
                if base64_data:
                    if base64_data.startswith("data:"):
                        base64_data = base64_data.split(",", 1)[1]
                    image_bytes = base64.b64decode(base64_data)
                    image = Image.open(BytesIO(image_bytes))
                    return image
                    
            except Exception as e:
                if self.debug_mode:
                    print(f"이미지 데이터 처리 오류: {e}")
        
        try:
            rows = table_data.get("rows", 5)
            cols = table_data.get("cols", 5)
            grid = table_data.get("grid", [])
            te_number = table_data.get("te_number", "")
            
            if grid is None:
                grid = []
            if te_number is None:
                te_number = ""
            
            cell_width = 150
            cell_height = 80
            padding = 10
            
            img_width = cols * cell_width + 1
            img_height = rows * cell_height + 1
            
            img = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(img)
            
            try:
                for font_name in ["arial.ttf", "AppleGothic.ttf", "gulim.ttc", "malgun.ttf", "NotoSansCJK-Regular.ttc"]:
                    try:
                        font = ImageFont.truetype(font_name, 12)
                        break
                    except:
                        continue
                else:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            for i in range(rows + 1):
                y = i * cell_height
                draw.line([(0, y), (img_width, y)], fill='black', width=1)
            
            for i in range(cols + 1):
                x = i * cell_width
                draw.line([(x, 0), (x, img_height)], fill='black', width=1)
            
            for r in range(rows):
                for c in range(cols):
                    x = c * cell_width + padding
                    y = r * cell_height + padding
                    
                    if r < len(grid) and c < len(grid[r]):
                        text = str(grid[r][c])
                    else:
                        text = ""
                    
                    if te_number in text or "시험결과판정근거" in text:
                        bg_color = (255, 255, 204) if te_number in text else (230, 242, 255)
                        draw.rectangle(
                            [(c * cell_width + 1, r * cell_height + 1), 
                             ((c + 1) * cell_width - 1, (r + 1) * cell_height - 1)],
                            fill=bg_color
                        )
                    
                    max_width = cell_width - (padding * 2)
                    wrapped_text = self._wrap_text(text, font, max_width)
                    
                    if wrapped_text is None:
                        if self.debug_mode:
                            print(f"오류: wrapped_text가 None임 - text: {text}")
                        wrapped_text = [""]
                    
                    line_y = y
                    for line in wrapped_text:
                        if line is None:
                            line = ""
                        draw.text((x, line_y), line, font=font, fill='black')
                        line_y += 14
            
            return img
            
        except Exception as e:
            if self.debug_mode:
                print(f"테이블 이미지 생성 오류: {e}")
            return None
    
    def _wrap_text(self, text, font, max_width):
        """
        텍스트를 지정된 너비에 맞게 줄바꿈 수행
        
        Args:
            text (str): 원본 텍스트
            font (ImageFont): 사용할 폰트
            max_width (int): 최대 너비
            
        Returns:
            list: 줄바꿈된 텍스트 라인 리스트
        """
        lines = []
        
        if text is None:
            return [""]
        
        text = str(text)
        
        if not text:
            return [""]
        
        if font is None:
            if self.debug_mode:
                print("오류: font가 None임")
            return [text]
        
        words = text.split()
        if not words:
            return [""]
        
        current_line = words[0]
        
        for word in words[1:]:
            if hasattr(font, 'getsize'):
                test_width = font.getsize(current_line + " " + word)[0]
            else:
                test_width = len(current_line + " " + word) * 8
            
            if test_width <= max_width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def get_test_result_image(self, te_number):
        """
        TE 번호에 해당하는 시험결과판정근거 테이블 이미지 생성
        
        Args:
            te_number (str): 검색할 TE 번호 (예: "TE02.03.01")
            
        Returns:
            dict: {
                "image": 이미지 객체 또는 None,
                "base64": base64 인코딩된 이미지 문자열 또는 None,
                "page_number": 페이지 번호,
                "table_number": 테이블 번호,
                "te_number": TE 번호
            }
        """
        if self.json_data is None:
            if self.debug_mode:
                print("오류: JSON 데이터가 로드되지 않음")
            return None
        
        if te_number is None:
            if self.debug_mode:
                print("오류: te_number가 None임")
            return None
        
        table_data = self.get_test_result_table_data(te_number)
        if not table_data:
            if self.debug_mode:
                print(f"테이블 데이터를 찾을 수 없음: {te_number}")
            return None
        
        if table_data.get("has_image", False) and "image_data" in table_data:
            try:
                image_data = table_data["image_data"]
                if image_data is None:
                    return None
                    
                base64_data = image_data.get("base64", "")
                
                if base64_data:
                    if base64_data.startswith("data:"):
                        base64_data = base64_data.split(",", 1)[1]
                    image_bytes = base64.b64decode(base64_data)
                    image = Image.open(BytesIO(image_bytes))
                    
                    return {
                        "image": image,
                        "base64": base64_data,
                        "page_number": table_data.get("page_number", 0),
                        "table_number": table_data.get("table_number", 0),
                        "te_number": te_number,
                        "caption": table_data.get("caption", "")
                    }
            except Exception as e:
                if self.debug_mode:
                    print(f"이미지 데이터 처리 오류: {e}")
        
        image = self.create_table_image(table_data)
        base64_str = self.image_to_base64(image) if image else None
        
        return {
            "image": image,
            "base64": base64_str,
            "page_number": table_data.get("page_number", 0),
            "table_number": table_data.get("table_number", 0),
            "te_number": te_number,
            "caption": table_data.get("caption", "")
        }
    
    def image_to_base64(self, img):
        """
        PIL 이미지를 base64 문자열로 변환
        
        Args:
            img (PIL.Image): 변환할 이미지
            
        Returns:
            str: base64 인코딩된 문자열
        """
        if img is None:
            return None
            
        if not PIL_AVAILABLE:
            if self.debug_mode:
                print("오류: PIL 모듈이 설치되지 않음")
            return None
            
        try:
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return img_str
        except Exception as e:
            if self.debug_mode:
                print(f"이미지 변환 오류: {e}")
            return None
        
    def get_image_data(self, image_id):
        """
        이미지 ID에 해당하는 이미지 데이터를 가져옴
        
        Args:
            image_id (str): 이미지 ID
            
        Returns:
            dict: 이미지 데이터 또는 None
        """
        if self.json_data is None:
            if self.debug_mode:
                print("오류: JSON 데이터가 로드되지 않음")
            return None
        
        if image_id is None:
            if self.debug_mode:
                print("오류: image_id가 None임")
            return None
            
        image_id_str = str(image_id)
        debug_info = {"searched_images": []}
            
        pages = self.json_data.get("pages", [])
        if pages is None:
            pages = []
            
        for page_idx, page in enumerate(pages):
            if page is None:
                continue
                
            images = page.get("images", [])
            if images is None:
                images = []
                
            for image_idx, image in enumerate(images):
                if image is None:
                    continue
                    
                if image.get("image_id") == image_id_str:
                    return image
            
            tables = page.get("tables", [])
            if tables is None:
                tables = []
                
            for table_idx, table in enumerate(tables):
                if table is None:
                    continue
                    
                if "image" in table and isinstance(table.get("image"), dict):
                    image_data = table["image"]
                    image_data["page_idx"] = page_idx
                    image_data["table_idx"] = table_idx
                    image_data["image_id"] = table.get("table_id", f"table_{page_idx}_{table_idx}")
                    
                    if table.get("table_id") == image_id_str:
                        return image_data
        
        if self.debug_mode:
            print(f"디버그 정보: {json.dumps(debug_info, indent=2, ensure_ascii=False)}")
        return None