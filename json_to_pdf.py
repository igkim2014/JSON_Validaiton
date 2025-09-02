#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 실행 환경 및 인코딩 설정

import json  # JSON 데이터 처리를 위한 모듈
import io  # 입출력 스트림 처리를 위한 모듈
import base64  # Base64 인코딩/디코딩을 위한 모듈
import logging  # 로깅을 위한 모듈
import os  # 파일 및 디렉토리 작업을 위한 모듈
import sys  # 시스템 관련 작업을 위한 모듈
import traceback  # 예외 추적을 위한 모듈
import re  # 정규 표현식을 위한 모듈
import unicodedata  # 유니코드 문자 처리를 위한 모듈
from reportlab.pdfgen import canvas  # PDF 생성을 위한 캔버스 모듈
from reportlab.platypus import Table, TableStyle, Paragraph, Frame, PageTemplate, BaseDocTemplate  # PDF 레이아웃 요소
from reportlab.lib import colors  # 색상 정의를 위한 모듈
from reportlab.lib.utils import ImageReader  # 이미지 처리를 위한 모듈
from reportlab.pdfbase import pdfmetrics  # PDF 폰트 메트릭 처리를 위한 모듈
from reportlab.pdfbase.ttfonts import TTFont  # TrueType 폰트 등록을 위한 모듈
from reportlab.lib.styles import ParagraphStyle  # 텍스트 스타일 정의를 위한 모듈
from reportlab.lib.pagesizes import A4  # 페이지 크기 정의를 위한 모듈
from reportlab.lib.units import mm  # 단위 변환을 위한 모듈
from PIL import Image  # 이미지 처리를 위한 PIL 모듈

# 로깅 설정: 로그 레벨을 INFO로 설정하고, 시간/레벨/메시지 형식으로 출력
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # 로깅 형식 및 레벨 설정

def register_fonts():
    """
    폰트 등록 함수
    - 기능: PDF 생성에 사용할 한글 및 기본 폰트(NotoSansKR, MalgunGothic 등)를 등록
    - 반환: 등록된 폰트 상태를 나타내는 딕셔너리 (폰트 이름: 등록 성공 여부)
    - 예외 처리: 폰트 파일이 없거나 등록 실패 시 로그를 남기고 기본 폰트 사용
    """
    fonts_registered = {}  # 등록된 폰트 상태를 저장할 딕셔너리
    
    try:
        # NotoSansKR 폰트 등록 시도
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansKR-Regular.ttf")  # NotoSansKR 폰트 파일 경로 설정
        if os.path.exists(font_path):  # 폰트 파일 존재 여부 확인
            pdfmetrics.registerFont(TTFont("NotoSansKR", font_path))  # NotoSansKR 폰트 등록
            fonts_registered["NotoSansKR"] = True  # 등록 성공 표시
            logging.info(f"[Info] NotoSansKR font loaded: {font_path}")  # 성공 로그 출력
        else:
            logging.info("[Info] NotoSansKR font file not found, using default font")  # 폰트 파일 미존재 로그
            fonts_registered["NotoSansKR"] = False  # 등록 실패 표시
    except Exception as e:
        logging.info(f"[Info] Failed to register NotoSansKR font: {e}, using default font")  # 폰트 등록 실패 로그
        fonts_registered["NotoSansKR"] = False  # 등록 실패 표시

    try:
        # NotoSansKR-Bold 폰트 등록 시도
        font_path_bold = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansKR-Bold.ttf")  # NotoSansKR-Bold 폰트 파일 경로 설정
        if os.path.exists(font_path_bold):  # 폰트 파일 존재 여부 확인
            pdfmetrics.registerFont(TTFont("NotoSansKR-Bold", font_path_bold))  # NotoSansKR-Bold 폰트 등록
            fonts_registered["NotoSansKR-Bold"] = True  # 등록 성공 표시
            logging.info(f"[Info] NotoSansKR-Bold font loaded: {font_path_bold}")  # 성공 로그 출력
        else:
            logging.info("[Info] NotoSansKR-Bold font file not found, using default font")  # 폰트 파일 미존재 로그
            fonts_registered["NotoSansKR-Bold"] = False  # 등록 실패 표시
    except Exception as e:
        logging.info(f"[Info] Failed to register NotoSansKR-Bold font: {e}, using default font")  # 폰트 등록 실패 로그
        fonts_registered["NotoSansKR-Bold"] = False  # 등록 실패 표시

    try:
        # MalgunGothic 폰트 등록 시도
        malgun_font_path = os.path.join(os.path.dirname(__file__), "fonts", "malgun.ttf")  # MalgunGothic 폰트 파일 경로 설정
        if os.path.exists(malgun_font_path):  # 폰트 파일 존재 여부 확인
            pdfmetrics.registerFont(TTFont("MalgunGothic", malgun_font_path))  # MalgunGothic 폰트 등록
            fonts_registered["MalgunGothic"] = True  # 등록 성공 표시
            logging.info(f"[Info] MalgunGothic font loaded: {malgun_font_path}")  # 성공 로그 출력
        else:
            logging.info("[Info] MalgunGothic font file not found, using default font")  # 폰트 파일 미존재 로그
            fonts_registered["MalgunGothic"] = False  # 등록 실패 표시
    except Exception as e:
        logging.info(f"[Info] Failed to register MalgunGothic font: {e}, using default font")  # 폰트 등록 실패 로그
        fonts_registered["MalgunGothic"] = False  # 등록 실패 표시

    try:
        # MalgunGothic-Bold 폰트 등록 시도
        malgun_font_path_bold = os.path.join(os.path.dirname(__file__), "fonts", "malgunbd.ttf")  # MalgunGothic-Bold 폰트 파일 경로 설정
        if os.path.exists(malgun_font_path_bold):  # 폰트 파일 존재 여부 확인
            pdfmetrics.registerFont(TTFont("MalgunGothic-Bold", malgun_font_path_bold))  # MalgunGothic-Bold 폰트 등록
            fonts_registered["MalgunGothic-Bold"] = True  # 등록 성공 표시
            logging.info(f"[Info] MalgunGothic-Bold font loaded: {malgun_font_path_bold}")  # 성공 로그 출력
        else:
            logging.info("[Info] MalgunGothic-Bold font file not found, using default font")  # 폰트 파일 미존재 로그
            fonts_registered["MalgunGothic-Bold"] = False  # 등록 실패 표시
    except Exception as e:
        logging.info(f"[Info] Failed to register MalgunGothic-Bold font: {e}, using default font")  # 폰트 등록 실패 로그
        fonts_registered["MalgunGothic-Bold"] = False  # 등록 실패 표시
    
    return fonts_registered  # 등록된 폰트 상태 딕셔너리 반환

# 폰트 등록 실행 및 결과 저장
FONTS_REGISTERED = register_fonts()  # 폰트 등록 함수 호출 및 결과 저장

def convert_json_to_pdf(json_file_path, output_pdf_path, log=None, *args, **kwargs):
    """
    JSON 데이터를 PDF로 변환하는 메인 함수
    - 입력:
        - json_file_path: 입력 JSON 파일 경로
        - output_pdf_path: 출력 PDF 파일 경로
        - log: 로그 출력 함수 (기본값: print)
        - *args, **kwargs: 예상치 못한 인자 처리
    - 기능:
        1. JSON 파일을 읽어 페이지별로 테이블, 텍스트, 이미지를 PDF에 렌더링
        2. 각 페이지의 크기를 설정하고 콘텐츠를 순차적으로 그림
        3. 변환 성공/실패 여부를 반환
    - 반환: 성공 시 True, 실패 시 False
    - 예외 처리: 파일 읽기/쓰기 오류, JSON 파싱 오류 등 처리
    """
    if log is None:  # 로그 함수가 없으면
        log = print  # 기본 print 함수 사용

    # 예상치 못한 인자 처리
    if args or kwargs:  # 예상치 못한 인자가 있는 경우
        log(f"[Warning] Unexpected arguments received - args: {args}, kwargs: {kwargs}")  # 경고 로그 출력

    try:
        # JSON 파일 읽기
        with open(json_file_path, 'r', encoding='utf-8') as f:  # JSON 파일을 UTF-8로 열기
            doc_info = json.load(f)  # JSON 데이터 파싱

        # PDF 캔버스 생성
        pdf = canvas.Canvas(output_pdf_path)  # PDF 캔버스 객체 생성
        page_count = doc_info["metadata"]["page_count"]  # 페이지 수 추출
        log(f"[Info] Processing {page_count} pages")  # 페이지 수 처리 로그 출력

        # 페이지별 처리
        for page_info in doc_info["pages"]:  # 각 페이지 정보 순회
            page_w = page_info["width"]  # 페이지 너비 추출
            page_h = page_info["height"]  # 페이지 높이 추출
            pdf.setPageSize((page_w, page_h))  # 페이지 크기 설정

            # 테이블, 이미지, 텍스트 순으로 렌더링
            rendered_tables = draw_tables_enhanced(pdf, page_info, page_w, page_h, log)  # 테이블 렌더링
            render_images_enhanced(pdf, page_info, page_w, page_h, log, rendered_tables)  # 이미지 렌더링
            render_text_enhanced(pdf, page_info, page_w, page_h, log, rendered_tables)  # 텍스트 렌더링

            pdf.showPage()  # 페이지 완료

        # PDF 저장
        pdf.save()  # PDF 파일 저장
        log(f"[Info] PDF saved to: {output_pdf_path}")  # 저장 완료 로그 출력
        return True  # 성공 반환
    except Exception as e:
        log(f"[Error] Conversion failed: {e}")  # 변환 실패 로그 출력
        log(traceback.format_exc())  # 예외 스택 트레이스 출력
        return False  # 실패 반환

def is_korean_text(text):
    """
    텍스트가 한글을 포함하는지 확인
    - 입력: text (문자열)
    - 기능: 한글 유니코드 범위(AC00-D7A3)를 확인
    - 반환: 한글 포함 시 True, 아니면 False
    """
    return any('\uAC00' <= char <= '\uD7A3' for char in text)  # 한글 유니코드 범위 확인

def has_special_characters(text):
    """
    텍스트에 특수문자(·, ○, □ 등)가 포함되어 있는지 확인
    - 입력: text (문자열)
    - 기능: 정의된 특수문자 집합과 비교
    - 반환: 특수문자 포함 시 True, 아니면 False
    """
    special_chars = {
        '·', '○', '□', '◇', '◆', '★', '☆', '▲', '▼', '♠', '♣', '♥', '♦',
        '※', '▣', '◎', '☞', '▶', '◀', '▽', '△', '◁', '▷', '◊', '♨',
        '℃', '℉', '№', '㎡', '㎢', '㎥', '㎦', '㎧', '㎨', '㎩', '㎪', '㎫',
        '㎬', '㎭', '㎮', '㎯', '㎰', '㎱', '㎲', '㎳', '㎴', '㎵', '㎶', '㎷',
        '㎸', '㎹', '㎺', '㎻', '㎼', '㎽', '㎾', '㎿', '㏀', '㏁', '㏂', '㏃',
        '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
        'ⅰ', 'ⅱ', 'ⅲ', 'ⅳ', 'ⅴ', 'ⅵ', 'ⅶ', 'ⅷ', 'ⅸ', 'ⅹ',
        '→', '←', '↑', '↓', '↔', '↕', '↖', '↗', '↘', '↙',
        '─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼',
        '━', '┃', '┏', '┓', '┗', '┛', '┣', '┫', '┳', '┻', '╋'
    }  # 특수문자 집합 정의
    return any(char in special_chars for char in text)  # 특수문자 포함 여부 확인

def has_cjk_symbols(text):
    """
    CJK 기호 및 구두점이 포함되어 있는지 확인
    - 입력: text (문자열)
    - 기능: CJK 기호(3000-303F) 및 일반 구두점(2000-206F) 확인
    - 반환: CJK 기호 포함 시 True, 아니면 False
    """
    for char in text:  # 텍스트의 각 문자 순회
        if unicodedata.category(char) in ['So', 'Sm'] and ord(char) > 0x2000:  # 기호 또는 수학 기호 확인
            return True  # 포함 시 True 반환
        if 0x3000 <= ord(char) <= 0x303F:  # CJK 기호 범위 확인
            return True  # 포함 시 True 반환
        if 0x2000 <= ord(char) <= 0x206F:  # 일반 구두점 범위 확인
            return True  # 포함 시 True 반환
    return False  # 포함되지 않으면 False 반환

def clean_text_for_pdf(text):
    """
    PDF 렌더링을 위해 텍스트 정리
    - 입력: text (문자열)
    - 기능:
        1. NULL 문자 및 서로게이트 페어 문자 제거
        2. 제어 문자(탭, 개행 제외) 제거
        3. 연속 공백 정리
        4. 특수문자는 보존
    - 반환: 정리된 문자열
    """
    if not text:  # 텍스트가 비어 있는 경우
        return ""  # 빈 문자열 반환
    
    # NULL 문자 제거
    text = text.replace('\x00', '')  # NULL 문자 제거
    
    # 서로게이트 페어 및 제어 문자 제거
    cleaned_chars = []  # 정리된 문자 리스트
    for char in text:  # 텍스트의 각 문자 순회
        char_code = ord(char)  # 문자 코드 추출
        if 0xD800 <= char_code <= 0xDFFF:  # 서로게이트 페어 범위 확인
            continue  # 해당 문자 제외
        if char_code < 32 and char not in ['\t', '\n', '\r']:  # 제어 문자 확인 (탭, 개행 제외)
            continue  # 해당 문자 제외
        cleaned_chars.append(char)  # 유효한 문자 추가
    
    text = ''.join(cleaned_chars)  # 정리된 문자 결합
    
    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text)  # 연속 공백을 단일 공백으로 변환
    
    return text.strip()  # 양쪽 공백 제거 후 반환

def get_font_for_text(font_name, text, is_bold, default_font="Helvetica"):
    """
    텍스트에 적합한 폰트 선택
    - 입력:
        - font_name: 요청된 폰트 이름
        - text: 대상 텍스트
        - is_bold: 볼드 여부
        - default_font: 기본 폰트 (기본값: Helvetica)
    - 기능:
        1. 한글, 특수문자, CJK 기호 포함 여부 확인
        2. 유니코드 폰트(NotoSansKR, MalgunGothic) 우선 사용
        3. 폰트 매핑 및 볼드 처리
    - 반환: 선택된 폰트 이름
    """
    font_map = {
        "Arial.Bold": "Helvetica-Bold",  # Arial.Bold 매핑
        "Arial.Regular": "Helvetica",  # Arial.Regular 매핑
        "Gulim.Regular": "NotoSansKR",  # Gulim.Regular 매핑
    }  # 폰트 매핑 딕셔너리
    
    # 유니코드 폰트 필요 여부 확인
    needs_unicode_font = (is_korean_text(text) or 
                         has_special_characters(text) or 
                         has_cjk_symbols(text))  # 한글, 특수문자, CJK 기호 포함 여부 확인
    
    if needs_unicode_font:  # 유니코드 폰트가 필요한 경우
        if FONTS_REGISTERED.get("NotoSansKR", False):  # NotoSansKR 폰트 등록 여부 확인
            if is_bold and FONTS_REGISTERED.get("NotoSansKR-Bold", False):  # 볼드이고 NotoSansKR-Bold가 있는 경우
                return "NotoSansKR-Bold"  # NotoSansKR-Bold 반환
            return "NotoSansKR"  # NotoSansKR 반환
        elif FONTS_REGISTERED.get("MalgunGothic", False):  # MalgunGothic 폰트 등록 여부 확인
            if is_bold and FONTS_REGISTERED.get("MalgunGothic-Bold", False):  # 볼드이고 MalgunGothic-Bold가 있는 경우
                return "MalgunGothic-Bold"  # MalgunGothic-Bold 반환
            return "MalgunGothic"  # MalgunGothic 반환
        else:
            return "Helvetica-Bold" if is_bold else "Helvetica"  # 기본 폰트 반환
    
    # 일반 영문 폰트 매핑
    mapped_font = font_map.get(font_name, default_font)  # 폰트 매핑 조회
    if is_bold and "Bold" not in mapped_font:  # 볼드 요청이고 매핑 폰트가 볼드가 아닌 경우
        mapped_font = mapped_font.replace("Helvetica", "Helvetica-Bold")  # 볼드 폰트로 변경
    return mapped_font  # 최종 폰트 반환

def test_font_compatibility(pdf, font_name, text, size):
    """
    폰트와 텍스트의 호환성 테스트
    - 입력:
        - pdf: PDF 캔버스 객체
        - font_name: 테스트할 폰트 이름
        - text: 테스트할 텍스트
        - size: 폰트 크기
    - 기능: 폰트로 텍스트를 렌더링할 수 있는지 확인
    - 반환: 호환 시 True, 비호환 시 False
    """
    try:
        pdf.setFont(font_name, size)  # 폰트와 크기 설정
        pdf.stringWidth(text, font_name, size)  # 텍스트 너비 계산
        return True  # 호환 가능
    except Exception:
        return False  # 호환 불가

def get_fallback_font_for_special_chars(pdf, text, size, is_bold=False):
    """
    특수문자를 위한 폴백 폰트 선택
    - 입력:
        - pdf: PDF 캔버스 객체
        - text: 대상 텍스트
        - size: 폰트 크기
        - is_bold: 볼드 여부
    - 기능: 유니코드 폰트 및 기본 폰트를 순차적으로 테스트하여 호환 폰트 반환
    - 반환: 호환 가능한 폰트 이름
    """
    font_candidates = []  # 폰트 후보 리스트
    
    if FONTS_REGISTERED.get("NotoSansKR", False):  # NotoSansKR 등록 여부 확인
        font_candidates.append("NotoSansKR-Bold" if is_bold and FONTS_REGISTERED.get("NotoSansKR-Bold", False) else "NotoSansKR")  # NotoSansKR 추가
    
    if FONTS_REGISTERED.get("MalgunGothic", False):  # MalgunGothic 등록 여부 확인
        font_candidates.append("MalgunGothic-Bold" if is_bold and FONTS_REGISTERED.get("MalgunGothic-Bold", False) else "MalgunGothic")  # MalgunGothic 추가
    
    font_candidates.extend([
        "Helvetica-Bold" if is_bold else "Helvetica",  # 기본 폰트 추가
        "Times-Bold" if is_bold else "Times-Roman",  # Times 폰트 추가
        "Courier-Bold" if is_bold else "Courier"  # Courier 폰트 추가
    ])  # 기본 폰트 후보 추가
    
    for font in font_candidates:  # 폰트 후보 순회
        if test_font_compatibility(pdf, font, text, size):  # 호환성 테스트
            return font  # 호환 가능한 폰트 반환
    
    return "Helvetica-Bold" if is_bold else "Helvetica"  # 최종 기본 폰트 반환

def draw_tables_enhanced(pdf, page_info, page_w, page_h, log):
    """
    테이블을 PDF에 렌더링
    - 입력:
        - pdf: PDF 캔버스 객체
        - page_info: 페이지 정보 (JSON 데이터)
        - page_w, page_h: 페이지 너비/높이
        - log: 로그 출력 함수
    - 기능:
        1. 테이블 이미지 렌더링 (base64 인코딩)
        2. 테이블 셀 텍스트 렌더링
        3. 렌더링된 테이블과 셀의 경계 상자 반환
    - 반환: (렌더링된 테이블 경계 상자 리스트, 셀 경계 상자 리스트)
    """
    tables = page_info.get("tables", [])  # 페이지 내 테이블 정보 추출
    if not tables:  # 테이블이 없는 경우
        log("[Info] No tables found on page")  # 테이블 없음 로그 출력
        return ([], [])  # 빈 리스트 반환

    log(f"[Info] Found {len(tables)} tables to process")  # 테이블 수 로그 출력
    rendered_tables = []  # 렌더링된 테이블 경계 상자 리스트
    cell_bboxes = []  # 셀 경계 상자 리스트

    for tbl_idx, tbl in enumerate(tables):  # 테이블 순회
        try:
            image_data = tbl.get("image", {})  # 테이블 이미지 데이터 추출
            bbox = tbl.get("bbox", [0, 0, page_w, page_h])  # 테이블 경계 상자 추출
            x0, y0, x1, y1 = [float(v) for v in bbox[:4]]  # 경계 상자 좌표 변환
            x0, x1 = min(x0, x1), max(x0, x1)  # x 좌표 정규화
            y0, y1 = min(y0, y1), max(y0, y1)  # y 좌표 정규화
            w = x1 - x0  # 테이블 너비 계산
            h = y1 - y0  # 테이블 높이 계산
            y_new = page_h - y1  # PDF 좌표계로 y 변환

            # 최소 크기 설정
            min_dimension = 10  # 최소 크기 정의
            if w <= 0:  # 너비가 유효하지 않은 경우
                log(f"[Warning] Table {tbl_idx} width is invalid: {w}. Setting to minimum {min_dimension}")  # 경고 로그 출력
                w = min_dimension  # 최소 너비 설정
                x1 = x0 + w  # x1 조정
            if h <= 0:  # 높이가 유효하지 않은 경우
                log(f"[Warning] Table {tbl_idx} height is invalid: {h}. Setting to minimum {min_dimension}")  # 경고 로그 출력
                h = min_dimension  # 최소 높이 설정
                y1 = y0 + h  # y1 조정
                y_new = page_h - y1  # y_new 재설정

            # 테이블 이미지 렌더링
            base64_str = image_data.get("base64", "")  # Base64 데이터 추출
            if base64_str:  # Base64 데이터가 있는 경우
                if "base64," in base64_str:  # Base64 접두사 처리
                    base64_str = base64_str.split("base64,")[-1]  # 접두사 제거

                try:
                    img_bytes = base64.b64decode(base64_str)  # Base64 디코딩
                    img = Image.open(io.BytesIO(img_bytes))  # 이미지 열기
                    if img.mode != "RGB":  # RGB 모드가 아닌 경우
                        img = img.convert("RGB")  # RGB로 변환

                    orig_w, orig_h = img.size  # 원본 이미지 크기
                    scale_x = w / orig_w if orig_w > 0 else 1.0  # x 비율 계산
                    scale_y = h / orig_h if orig_h > 0 else 1.0  # y 비율 계산
                    scale = min(scale_x, scale_y)  # 최소 비율 선택
                    
                    new_w = orig_w * scale  # 새 너비 계산
                    new_h = orig_h * scale  # 새 높이 계산

                    # 페이지 경계 초과 방지
                    if x0 + new_w > page_w:  # 너비가 페이지 초과 시
                        new_w = page_w - x0 - 5  # 너비 조정
                    if y_new + new_h > page_h:  # 높이가 페이지 초과 시
                        new_h = page_h - y_new - 5  # 높이 조정

                    img_bytes_io = io.BytesIO()  # 이미지 바이트 스트림 생성
                    img.save(img_bytes_io, format="PNG")  # PNG로 저장
                    img_bytes_io.seek(0)  # 스트림 처음으로 이동

                    rdr = ImageReader(img_bytes_io)  # 이미지 리더 생성
                    pdf.drawImage(rdr, x0, y_new, width=new_w, height=new_h, preserveAspectRatio=True)  # 이미지 렌더링
                    log(f"[Info] Table {tbl_idx} image rendered successfully: {new_w}x{new_h}")  # 성공 로그 출력
                    rendered_tables.append([x0, y0, x0 + new_w, y0 + new_h])  # 렌더링된 경계 상자 추가
                except Exception as e:
                    log(f"[Error] Failed to render table {tbl_idx} image: {e}")  # 이미지 렌더링 실패 로그

            # 셀 텍스트 렌더링
            cells = tbl.get("cells", [])  # 셀 정보 추출
            for cell_idx, cell in enumerate(cells):  # 셀 순회
                try:
                    text = cell.get("text", "")  # 셀 텍스트 추출
                    if not text:  # 텍스트가 없는 경우
                        continue  # 다음 셀로 이동

                    cell_bbox = cell.get("bbox", [x0, y0, x1, y1])  # 셀 경계 상자 추출
                    cx0, cy0, cx1, cy1 = [float(v) for v in cell_bbox]  # 셀 좌표 변환
                    cell_width = cx1 - cx0  # 셀 너비 계산
                    cell_height = cy1 - cy0  # 셀 높이 계산
                    cy_new = page_h - cy1  # PDF 좌표계로 y 변환

                    cell_bboxes.append([cx0, cy0, cx1, cy1])  # 셀 경계 상자 추가

                    if cell_width <= 0 or cell_height <= 0:  # 셀 크기가 유효하지 않은 경우
                        log(f"[Warning] Invalid cell {cell_idx} dimensions: {cell_width}x{cell_height}")  # 경고 로그 출력
                        continue  # 다음 셀로 이동

                    # 텍스트 정리
                    text = clean_text_for_pdf(text)  # PDF용 텍스트 정리
                    if not text.strip():  # 정리 후 텍스트가 비어 있는 경우
                        continue  # 다음 셀로 이동

                    # 폰트 및 스타일 설정
                    font_size = cell.get("font_size", 8)  # 폰트 크기 추출
                    is_bold = cell.get("is_bold", False)  # 볼드 여부 추출
                    pdf_font = get_font_for_text("NotoSansKR", text, is_bold)  # 적합한 폰트 선택
                    
                    if not test_font_compatibility(pdf, pdf_font, text, font_size):  # 폰트 호환성 테스트
                        pdf_font = get_fallback_font_for_special_chars(pdf, text, font_size, is_bold)  # 폴백 폰트 선택
                        log(f"[Info] Using fallback font {pdf_font} for cell {cell_idx}")  # 폴백 폰트 사용 로그

                    text_style = ParagraphStyle(
                        name='CellText',  # 스타일 이름
                        fontName=pdf_font,  # 폰트 이름
                        fontSize=font_size,  # 폰트 크기
                        leading=font_size * 1.2,  # 줄 간격
                        alignment=1,  # 중앙 정렬
                        wordWrap='CJK' if is_korean_text(text) else None,  # 한글일 경우 CJK 워드랩
                        allowWidows=0,  # 단락 분리 방지
                        allowOrphans=0,  # 단락 분리 방지
                        splitLongWords=True,  # 긴 단어 분리 허용
                        spaceShrinkage=0.05,  # 공백 축소 비율
                        encoding='utf-8'  # 인코딩 설정
                    )  # 텍스트 스타일 정의

                    paragraph = Paragraph(text, text_style)  # Paragraph 객체 생성
                    w, h = paragraph.wrap(cell_width, cell_height)  # 텍스트 크기 계산

                    y_offset = (cell_height - h) / 2 if cell_height > h else 0  # y 오프셋 계산
                    paragraph.drawOn(pdf, cx0, cy_new + y_offset)  # 텍스트 렌더링
                    log(f"[Info] Cell {cell_idx} text rendered (font_size={font_size}, font={pdf_font}): {text[:30]}...")  # 성공 로그 출력
                except Exception as e:
                    log(f"[Error] Failed to render cell {cell_idx} text: {e}")  # 셀 텍스트 렌더링 실패 로그

        except Exception as e:
            log(f"[Error] Failed to process table {tbl_idx}: {e}")  # 테이블 처리 실패 로그

    return (rendered_tables, cell_bboxes)  # 렌더링된 테이블과 셀 경계 상자 반환

def render_text_enhanced(pdf, page_info, page_w, page_h, log, rendered_tables):
    """
    텍스트 블록을 PDF에 렌더링
    - 입력:
        - pdf: PDF 캔버스 객체
        - page_info: 페이지 정보 (JSON 데이터)
        - page_w, page_h: 페이지 너비/높이
        - log: 로그 출력 함수
        - rendered_tables: 렌더링된 테이블 정보
    - 기능:
        1. 텍스트 블록을 테이블/이미지와 겹치지 않도록 렌더링
        2. 긴 텍스트는 Paragraph로, 짧은 텍스트는 drawString으로 렌더링
        3. 폰트 호환성 및 크기 조정 처리
    """
    text_blocks = page_info.get("text_blocks", [])  # 텍스트 블록 정보 추출
    images = page_info.get("images", [])  # 이미지 정보 추출

    if not text_blocks:  # 텍스트 블록이 없는 경우
        log("[Info] No text blocks found on page")  # 텍스트 블록 없음 로그 출력
        return  # 함수 종료

    log(f"[Info] Found {len(text_blocks)} text blocks to process")  # 텍스트 블록 수 로그 출력

    # 테이블 및 셀 경계 상자 추출
    if isinstance(rendered_tables, tuple) and len(rendered_tables) == 2:  # 렌더링된 테이블이 튜플인 경우
        table_boxes, cell_bboxes = rendered_tables  # 테이블과 셀 경계 상자 분리
    else:
        table_boxes = rendered_tables if rendered_tables else []  # 테이블 경계 상자 설정
        cell_bboxes = []  # 빈 셀 경계 상자
    
    image_boxes = [[float(v) for v in img.get("bbox", [])] for img in images if len(img.get("bbox", [])) == 4]  # 이미지 경계 상자 추출

    def is_inside_any_table_or_image_or_cell(x0, y0, x1, y1, margin=1.0):
        """
        텍스트 블록이 테이블, 이미지, 셀 내부에 있는지 확인
        - 입력: 텍스트 블록의 경계 상자 좌표 (x0, y0, x1, y1), 여백(margin)
        - 반환: 내부에 있으면 True, 아니면 False
        """
        for box in table_boxes + cell_bboxes + image_boxes:  # 테이블, 셀, 이미지 경계 상자 순회
            if len(box) != 4:  # 경계 상자가 유효하지 않은 경우
                continue  # 다음 경계 상자로 이동
            bx0, by0, bx1, by1 = box  # 경계 상자 좌표 추출
            if (x0 < bx1 + margin and x1 > bx0 - margin and
                y0 < by1 + margin and y1 > by0 - margin):  # 겹침 확인
                return True  # 내부에 있음
        return False  # 내부에 없음

    for blk_idx, blk in enumerate(text_blocks):  # 텍스트 블록 순회
        try:
            text = blk.get("text", "")  # 텍스트 추출
            if not text:  # 텍스트가 없는 경우
                log(f"[Warning] Text block {blk_idx} has no text")  # 경고 로그 출력
                continue  # 다음 블록으로 이동

            x0 = float(blk.get("x0", 0))  # x0 좌표 추출
            y0 = float(blk.get("y0", 0))  # y0 좌표 추출
            x1 = float(blk.get("x1", 0))  # x1 좌표 추출
            y1 = float(blk.get("y1", 0))  # y1 좌표 추출
            font_name = blk.get("font", "Arial.Regular")  # 폰트 이름 추출
            is_bold = blk.get("is_bold", False)  # 볼드 여부 추출
            size = float(blk.get("size", 10))  # 폰트 크기 추출

            # 테이블/이미지/셀 내부 확인
            if is_inside_any_table_or_image_or_cell(x0, y0, x1, y1):  # 텍스트가 테이블/이미지/셀 내부에 있는 경우
                log(f"[Info] Text block {blk_idx} skipped (inside table/cell/image): {text[:50]}...")  # 스킵 로그 출력
                continue  # 다음 블록으로 이동

            # 텍스트 정리
            text = clean_text_for_pdf(text)  # PDF용 텍스트 정리
            if not text.strip():  # 정리 후 텍스트가 비어 있는 경우
                log(f"[Warning] Text block {blk_idx} is empty after cleaning")  # 경고 로그 출력
                continue  # 다음 블록으로 이동

            # 폰트 선택 및 호환성 검사
            pdf_font = get_font_for_text(font_name, text, is_bold)  # 적합한 폰트 선택
            if not test_font_compatibility(pdf, pdf_font, text, size):  # 폰트 호환성 테스트
                pdf_font = get_fallback_font_for_special_chars(pdf, text, size, is_bold)  # 폴백 폰트 선택
                log(f"[Info] Using fallback font {pdf_font} for text block {blk_idx}")  # 폴백 폰트 사용 로그
            
            block_width = x1 - x0  # 블록 너비 계산
            block_height = y1 - y0  # 블록 높이 계산

            try:
                pdf.setFont(pdf_font, size)  # 폰트와 크기 설정
                text_width = pdf.stringWidth(text, pdf_font, size)  # 텍스트 너비 계산
                
                # 텍스트 길이에 따라 렌더링 방식 결정
                if text_width > block_width and len(text) > 1:  # 텍스트가 블록 너비를 초과하고 길이가 1 이상인 경우
                    word_wrap = 'CJK' if (is_korean_text(text) or has_special_characters(text)) else None  # 한글 또는 특수문자일 경우 CJK 워드랩
                    text_style = ParagraphStyle(
                        name='Normal',  # 스타일 이름
                        fontName=pdf_font,  # 폰트 이름
                        fontSize=size,  # 폰트 크기
                        leading=size * 1.2,  # 줄 간격
                        wordWrap=word_wrap,  # 워드랩 설정
                        allowWidows=0,  # 단락 분리 방지
                        allowOrphans=0,  # 단락 분리 방지
                        splitLongWords=True,  # 긴 단어 분리 허용
                        spaceShrinkage=0.05,  # 공백 축소 비율
                        encoding='utf-8'  # 인코딩 설정
                    )  # 텍스트 스타일 정의
                    
                    paragraph = Paragraph(text, text_style)  # Paragraph 객체 생성
                    w, h = paragraph.wrap(block_width, float('inf'))  # 텍스트 크기 계산
                    
                    # 높이 초과 시 폰트 크기 조정
                    if h > block_height * 1.5:  # 텍스트 높이가 블록 높이의 1.5배를 초과하는 경우
                        adjusted_size = size * 0.9  # 폰트 크기 90%로 조정
                        text_style.fontSize = adjusted_size  # 조정된 폰트 크기 설정
                        text_style.leading = adjusted_size * 1.2  # 조정된 줄 간격 설정
                        paragraph = Paragraph(text, text_style)  # 새 Paragraph 객체 생성
                        w, h = paragraph.wrap(block_width, float('inf'))  # 텍스트 크기 재계산
                        log(f"[Warning] Text block {blk_idx} font size adjusted: {size} -> {adjusted_size}")  # 폰트 크기 조정 로그
                    
                    y_pdf = page_h - y0 - h  # PDF 좌표계로 y 변환
                    paragraph.drawOn(pdf, x0, y_pdf)  # 텍스트 렌더링
                    log(f"[Info] Text block {blk_idx} rendered with Paragraph (size={text_style.fontSize}, font={pdf_font})")  # 성공 로그 출력
                else:
                    y_pdf = page_h - y0 - size  # PDF 좌표계로 y 변환
                    pdf.drawString(x0, y_pdf, text)  # 텍스트 렌더링
                    log(f"[Info] Text block {blk_idx} rendered with drawString (size={size}, font={pdf_font})")  # 성공 로그 출력
                    
            except Exception as e:
                log(f"[Error] Failed to render text block {blk_idx}: {e}")  # 텍스트 렌더링 실패 로그
                try:
                    # 폴백 렌더링 시도
                    fallback_font = "Helvetica-Bold" if is_bold else "Helvetica"  # 폴백 폰트 선택
                    pdf.setFont(fallback_font, size)  # 폴백 폰트 설정
                    y_pdf = page_h - y0 - size  # PDF 좌표계로 y 변환
                    safe_text = text.replace('·', '•').replace('○', 'O').replace('□', '[]')  # 특수문자 대체
                    pdf.drawString(x0, y_pdf, safe_text)  # 폴백 텍스트 렌더링
                    log(f"[Info] Text block {blk_idx} rendered with fallback font and safe characters")  # 폴백 성공 로그
                except Exception as e2:
                    log(f"[Error] Complete failure to render text block {blk_idx}: {e2}")  # 완전 실패 로그
                    continue  # 다음 블록으로 이동

        except Exception as e:
            log(f"[Warning] Failed to draw text block {blk_idx}: {e}")  # 텍스트 블록 처리 실패 로그

def render_images_enhanced(pdf, page_info, page_w, page_h, log, rendered_tables):
    """
    이미지를 PDF에 렌더링
    - 입력:
        - pdf: PDF 캔버스 객체
        - page_info: 페이지 정보 (JSON 데이터)
        - page_w, page_h: 페이지 너비/높이
        - log: 로그 출력 함수
        - rendered_tables: 렌더링된 테이블 정보
    - 기능:
        1. base64 인코딩된 이미지를 디코딩하여 렌더링
        2. 테이블 내부 이미지 제외
        3. 페이지 경계 및 크기 조정
    - 반환: 렌더링된 이미지 경계 상자 리스트
    """
    images = page_info.get("images", [])  # 이미지 정보 추출
    if not images:  # 이미지가 없는 경우
        log("[Info] No images found on page")  # 이미지 없음 로그 출력
        return []  # 빈 리스트 반환
    
    log(f"[Info] Found {len(images)} images to process")  # 이미지 수 로그 출력

    # 테이블 경계 상자 추출
    if isinstance(rendered_tables, tuple) and len(rendered_tables) == 2:  # 렌더링된 테이블이 튜플인 경우
        table_boxes, _ = rendered_tables  # 테이블 경계 상자 추출
    else:
        table_boxes = rendered_tables if rendered_tables else []  # 테이블 경계 상자 설정

    def is_inside_any_table(x0, y0, x1, y1, margin=2.0):
        """
        이미지가 테이블 내부에 있는지 확인
        - 입력: 이미지 경계 상자 좌표 (x0, y0, x1, y1), 여백(margin)
        - 반환: 내부에 있으면 True, 아니면 False
        """
        for box in table_boxes:  # 테이블 경계 상자 순회
            if len(box) != 4:  # 경계 상자가 유효하지 않은 경우
                continue  # 다음 경계 상자로 이동
            bx0, by0, bx1, by1 = box  # 경계 상자 좌표 추출
            if (x0 >= bx0 - margin and x1 <= bx1 + margin and
                y0 >= by0 - margin and y1 <= by1 + margin):  # 이미지와 테이블 겹침 확인
                log(f"[Info] Image skipped (inside table, image_bbox=({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}), table_bbox=({bx0:.1f}, {by0:.1f}, {bx1:.1f}, {by1:.1f}))")  # 스킵 로그 출력
                return True  # 내부에 있음
        return False  # 내부에 없음

    rendered_image_boxes = []  # 렌더링된 이미지 경계 상자 리스트

    for idx, img in enumerate(images):  # 이미지 순회
        try:
            base64_str = img.get("base64", "")  # Base64 데이터 추출
            if not base64_str:  # Base64 데이터가 없는 경우
                log(f"[Warning] Image {idx} has no base64 data (bbox={img.get('bbox', [])})")  # 경고 로그 출력
                continue  # 다음 이미지로 이동
            
            bbox = img.get("bbox", [])  # 이미지 경계 상자 추출
            if len(bbox) < 4:  # 경계 상자가 유효하지 않은 경우
                log(f"[Warning] Image {idx} has invalid bbox: {bbox}")  # 경고 로그 출력
                continue  # 다음 이미지로 이동
                
            x0, y0, x1, y1 = [float(v) for v in bbox[:4]]  # 경계 상자 좌표 변환
            
            # 경계 상자 정규화
            if x0 > x1:  # x0가 x1보다 큰 경우
                x0, x1 = x1, x0  # x 좌표 교환
            if y0 > y1:  # y0가 y1보다 큰 경우
                y0, y1 = y1, y0  # y 좌표 교환
                
            w = x1 - x0  # 이미지 너비 계산
            h = y1 - y0  # 이미지 높이 계산
            y_new = page_h - y1  # PDF 좌표계로 y 변환

            # 최소 크기 설정
            min_size = 20.0  # 최소 크기 정의
            if w <= 0 or h <= 0:  # 크기가 유효하지 않은 경우
                log(f"[Warning] Invalid dimensions for image {idx}: w={w}, h={h}. Using {min_size}x{min_size}")  # 경고 로그 출력
                w = max(w, min_size)  # 최소 너비 설정
                h = max(h, min_size)  # 최소 높이 설정
                x1 = x0 + w  # x1 조정
                y1 = y0 + h  # y1 조정
                y_new = page_h - y1  # y_new 재설정

            # 테이블 내부 확인
            if is_inside_any_table(x0, y0, x1, y1):  # 이미지가 테이블 내부에 있는 경우
                continue  # 다음 이미지로 이동

            # 페이지 경계 조정
            if x0 < 0:  # x0가 페이지 경계를 벗어난 경우
                log(f"[Warning] Adjusted x0 from {x0} to 0 for image {idx}")  # 경고 로그 출력
                x0 = 0  # x0 조정
            if y_new < 0:  # y_new가 페이지 경계를 벗어난 경우
                log(f"[Warning] Adjusted y_new from {y_new} to 0 for image {idx}")  # 경고 로그 출력
                y_new = 0  # y_new 조정
            if x0 + w > page_w:  # 너비가 페이지 초과 시
                w = max(page_w - x0 - 5, min_size)  # 너비 조정
                log(f"[Warning] Adjusted width from {x1-x0} to {w} for image {idx}")  # 경고 로그 출력
            if y_new + h > page_h:  # 높이가 페이지 초과 시
                h = max(page_h - y_new - 5, min_size)  # 높이 조정
                log(f"[Warning] Adjusted height from {y1-y0} to {h} for image {idx}")  # 경고 로그 출력

            # base64 데이터 정리
            base64_str_clean = base64_str  # Base64 데이터 복사
            if "," in base64_str:  # Base64 접두사 처리
                base64_str_clean = base64_str.split(",")[-1]  # 접두사 제거
            base64_str_clean = re.sub(r'\s+', '', base64_str_clean)  # 공백 제거

            # base64 데이터 크기 확인
            base64_size_mb = len(base64_str_clean) / (1024 * 1024)  # Base64 데이터 크기(MB) 계산
            if base64_size_mb > 5:  # 데이터 크기가 5MB 초과 시
                log(f"[Warning] Large base64 data for image {idx}: {base64_size_mb:.2f} MB")  # 경고 로그 출력

            try:
                img_bytes = base64.b64decode(base64_str_clean)  # Base64 디코딩
                img_pil = Image.open(io.BytesIO(img_bytes))  # 이미지 열기
                
                if img_pil.mode != "RGB":  # RGB 모드가 아닌 경우
                    img_pil = img_pil.convert("RGB")  # RGB로 변환
                
                orig_w, orig_h = img_pil.size  # 원본 이미지 크기
                if orig_w <= 0 or orig_h <= 0:  # 원본 크기가 유효하지 않은 경우
                    log(f"[Warning] Invalid original image size for image {idx}: {orig_w}x{orig_h}")  # 경고 로그 출력
                    continue  # 다음 이미지로 이동
                
                # 이미지 크기 조정
                scale_x = w / orig_w  # x 비율 계산
                scale_y = h / orig_h  # y 비율 계산
                scale = min(scale_x, scale_y)  # 최소 비율 선택
                
                new_w = max(orig_w * scale, min_size)  # 새 너비 계산
                new_h = max(orig_h * scale, min_size)  # 새 높이 계산
                
                # 중앙 정렬
                x_offset = (w - new_w) / 2  # x 오프셋 계산
                y_offset = (h - new_h) / 2  # y 오프셋 계산
                
                final_x = x0 + x_offset  # 최종 x 좌표
                final_y = y_new + y_offset  # 최종 y 좌표
                
                # 페이지 경계 확인
                if final_x < 0 or final_y < 0 or final_x + new_w > page_w or final_y + new_h > page_h:  # 페이지 경계를 벗어난 경우
                    log(f"[Warning] Image {idx} out of page bounds: final_bbox=({final_x:.1f}, {final_y:.1f}, {final_x+new_w:.1f}, {final_y+new_h:.1f})")  # 경고 로그 출력
                    continue  # 다음 이미지로 이동
                
                img_bytes_io = io.BytesIO()  # 이미지 바이트 스트림 생성
                img_pil.save(img_bytes_io, format="PNG")  # PNG로 저장
                img_bytes_io.seek(0)  # 스트림 처음으로 이동
                
                rdr = ImageReader(img_bytes_io)  # 이미지 리더 생성
                pdf.drawImage(rdr, final_x, final_y, 
                            width=new_w, height=new_h, preserveAspectRatio=True)  # 이미지 렌더링
                log(f"[Info] Image {idx} drawn successfully at ({final_x:.1f}, {final_y:.1f}) size {new_w:.1f}x{new_h:.1f}, bbox=({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")  # 성공 로그 출력
                
                rendered_image_boxes.append([x0, y0, x1, y1])  # 렌더링된 경계 상자 추가
                
            except base64.binascii.Error as e:
                log(f"[Error] Base64 decode error for image {idx}: {e}, bbox=({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}), base64_prefix={base64_str[:50]}...")  # Base64 디코딩 오류 로그
                continue  # 다음 이미지로 이동
            except Exception as e:
                log(f"[Error] Failed to process image data for image {idx}: {e}, bbox=({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")  # 이미지 처리 실패 로그
                log(f"[Error] Traceback: {traceback.format_exc()}")  # 스택 트레이스 출력
                continue  # 다음 이미지로 이동
                
        except Exception as e:
            log(f"[Error] Failed to draw image {idx}: {e}, bbox={img.get('bbox', [])}")  # 이미지 렌더링 실패 로그
            log(f"[Error] Traceback: {traceback.format_exc()}")  # 스택 트레이스 출력
    
    return rendered_image_boxes  # 렌더링된 이미지 경계 상자 리스트 반환