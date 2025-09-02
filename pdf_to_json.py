#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 실행 환경 및 UTF-8 인코딩 설정

import json  # JSON 데이터 처리를 위한 모듈
import os  # 파일 및 디렉토리 작업을 위한 모듈
import logging  # 로깅을 위한 모듈
import pdfplumber  # PDF에서 텍스트와 테이블 추출을 위한 모듈
import fitz  # PDF 처리를 위한 PyMuPDF 모듈
import base64  # Base64 인코딩/디코딩을 위한 모듈
import pytesseract  # OCR 처리를 위한 모듈
from PIL import Image  # 이미지 처리를 위한 모듈
import io  # 입출력 스트림 처리를 위한 모듈
import numpy as np  # 배열 및 이미지 처리에 사용되는 모듈
import cv2  # OpenCV를 이용한 이미지 전처리에 사용
import re  # 정규 표현식을 위한 모듈
from collections import defaultdict  # 기본값 딕셔너리를 위한 모듈

# 로깅 설정: 로그 레벨을 INFO로 설정하고, 시간/레벨/메시지 형식으로 출력
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # 로깅 형식 및 레벨 설정

class PDFExtractor:

    def __init__(self, pdf_file_path, log_callback=None):
    # 기능: PDF 파일에서 텍스트, 테이블, 이미지를 추출하여 JSON 형식으로 변환
    # 로직:
    # 1. PDF 파일 경로와 로그 콜백을 초기화
    # 2. 메타데이터와 페이지별 데이터(텍스트, 테이블, 이미지)를 저장
    # 3. pdfplumber와 fitz로 데이터 추출, OCR로 보완
    # 4. 추출된 데이터를 JSON으로 저장
        self.pdf_file_path = pdf_file_path  # PDF 파일 경로 저장
        self.log_callback = log_callback  # 로그 출력 콜백 함수 저장
        self.doc_info = {  # 추출된 데이터를 저장할 딕셔너리
            "metadata": {  # PDF 메타데이터
                "filename": os.path.basename(pdf_file_path),  # 파일명 추출
                "page_count": 0,  # 페이지 수 초기화
                "CM_name": "",  # 문서 이름 초기화
                "version": "",  # 버전 정보 초기화
                "date": "",  # 날짜 정보 초기화
                "test_organization": ""  # 테스트 기관 정보 초기화
            },
            "pages": []  # 페이지별 데이터 리스트 초기화
        }

    
    def _log(self, message, level="INFO"):
    # 기능: 로그 메시지 출력 (콜백 또는 로깅 모듈 사용)
    # 로직:
    # 1. 메시지와 로그 레벨을 받아 포맷팅
    # 2. 콜백 함수가 있으면 호출, 없으면 로깅 모듈로 출력
        formatted_message = f"[{level}] {message}"  # 메시지 포맷팅
        if self.log_callback:  # 콜백 함수가 있는 경우
            self.log_callback(formatted_message)  # 콜백으로 메시지 전달
        else:  # 콜백 함수가 없는 경우
            if level == "INFO":  # INFO 레벨인 경우
                logging.info(message)  # INFO 로그 출력
            elif level == "ERROR":  # ERROR 레벨인 경우
                logging.error(message)  # ERROR 로그 출력
            elif level == "WARNING":  # WARNING 레벨인 경우
                logging.warning(message)  # WARNING 로그 출력

    
    def _is_inside_bbox(self, text_bbox, table_bbox):
    # 기능: 텍스트 경계 상자가 테이블 경계 상자 내부에 있는지 확인
    # 로직:
    # 1. 텍스트와 테이블의 경계 상자 좌표 비교
    # 2. 텍스트가 테이블 내부에 있으면 True 반환
        tx0, ty0, tx1, ty1 = text_bbox  # 텍스트 경계 상자 좌표 추출
        rx0, ry0, rx1, ry1 = table_bbox  # 테이블 경계 상자 좌표 추출
        return (tx0 >= rx0 and tx1 <= rx1 and ty0 >= ry0 and ty1 <= ry1)  # 텍스트가 테이블 내부인지 확인

    
    def extract(self):
    # 기능: PDF에서 메타데이터, 텍스트, 테이블, 이미지를 추출
    # 로직:
    # 1. pdfplumber와 fitz로 PDF 열기
    # 2. 첫 페이지에서 메타데이터와 콘텐츠 추출
    # 3. 나머지 페이지에서 텍스트, 테이블, 이미지 추출
    # 4. 계층 구조 추론 후 데이터 반환
        pdf = None  # pdfplumber 객체 초기화
        doc = None  # fitz 문서 객체 초기화
        try:
            self._log(f"Extract from: {self.pdf_file_path}")
            pdf = pdfplumber.open(self.pdf_file_path)  # PDF 파일 열기
            doc = fitz.open(self.pdf_file_path)  # fitz로 PDF 문서 열기

            self.doc_info["metadata"]["page_count"] = len(pdf.pages)  # 총 페이지 수 저장
            metadata = doc.metadata  # PDF 메타데이터 추출
            if metadata:  # 메타데이터가 존재하는 경우
                self.doc_info["metadata"]["title"] = metadata.get("title", "")  # 제목 정보 저장

            if pdf.pages:  # 페이지가 존재하는 경우
                first_page = pdf.pages[0]  # 첫 번째 페이지 객체
                first_page_data = {  # 첫 페이지 데이터 구조 초기화
                    "page_number": 1,
                    "width": first_page.width,
                    "height": first_page.height,
                    "text_blocks": [],
                    "tables": [],
                    "images": [],
                    "lines": {"vertical": [], "horizontal": [], "other": []},
                    "text": ""
                }
                fitz_first_page = doc[0]  # fitz 첫 페이지 객체
                self.extract_text_enhanced(first_page, fitz_first_page, first_page_data)  # 텍스트 먼저 추출
                self.extract_tables(first_page, 1, first_page_data, doc=doc)  # 테이블 추출
                self._extract_metadata_from_first_page(first_page_data)  # 첫 페이지에서 메타데이터 추출
                first_page_data["text_blocks"] = self._infer_hierarchy(first_page_data["text_blocks"])  # 계층 구조 추론
                self.doc_info["pages"].append(first_page_data)  # 첫 페이지 데이터 저장

            for i, page_num in enumerate(range(1, len(pdf.pages)), start=2):  # 두 번째 페이지부터 순회
                plumber_page = pdf.pages[page_num]  # pdfplumber 페이지 객체
                fitz_page = doc[page_num]  # fitz 페이지 객체

                page_data = {  # 페이지 데이터 구조 초기화
                    "page_number": i,
                    "width": plumber_page.width,
                    "height": plumber_page.height,
                    "text_blocks": [],
                    "tables": [],
                    "images": [],
                    "lines": {"vertical": [], "horizontal": [], "other": []},
                    "text": ""
                }

                self.extract_text_enhanced(plumber_page, fitz_page, page_data)  # 향상된 텍스트 추출
                self.extract_tables(plumber_page, i, page_data, doc=doc)  # 테이블 추출
                self.extract_images_with_pdfplumber(plumber_page, page_data, output_dir=os.path.dirname(self.pdf_file_path))  # 이미지 추출
                page_data["text_blocks"] = self._infer_hierarchy(page_data["text_blocks"])  # 계층 구조 추론
                self.doc_info["pages"].append(page_data)  # 페이지 데이터 저장

            return self.doc_info  # 추출된 데이터 반환
        except Exception as e:  # 예외 발생 시
            self._log(f"Extraction failed: {e}", level="ERROR")
            return None  # 실패 시 None 반환
        finally:  # 리소스 정리
            if pdf:  # PDF 객체가 존재하는 경우
                pdf.close()  # PDF 파일 닫기
            if doc:  # fitz 문서 객체가 존재하는 경우
                doc.close()  # 문서 닫기

    
    def extract_text_enhanced(self, plumber_page, fitz_page, page_data):
    # 기능: PDF 페이지에서 텍스트 블록을 추출 (공백 및 폰트 정보 보존)
    # 로직:
    # 1. fitz의 rawdict로 텍스트 블록 추출
    # 2. 테이블 내부 텍스트 제외
    # 3. 텍스트 블록 병합 및 계층 구조 추론
        """개선된 텍스트 추출 메서드 - 공백 보존 및 줄바꿈 방지"""
        try:
            raw_dict = fitz_page.get_text("rawdict")  # 원시 텍스트 딕셔너리 추출
            text_blocks = []  # 텍스트 블록 리스트 초기화
            block_idx = 0  # 블록 인덱스 초기화

            table_bboxes = [table["bbox"] for table in page_data.get("tables", [])]  # 테이블 경계 상자 리스트

            for block in raw_dict["blocks"]:  # 텍스트 블록 순회
                if block["type"] == 0:  # 텍스트 블록인 경우 (type 0)
                    block_lines = []  # 블록 내 라인 리스트
                    block_bbox = block["bbox"]  # 블록 경계 상자

                    if any(self._is_inside_bbox(block_bbox, table_bbox) for table_bbox in table_bboxes):  # 테이블 내부 텍스트인지 확인
                        continue  # 테이블 내부면 건너뛰기

                    prev_line_bbox = None  # 이전 라인 경계 상자
                    for line in block["lines"]:  # 라인 순회
                        line_bbox = line["bbox"]  # 라인 경계 상자
                        line_texts = []  # 라인 텍스트 리스트
                        spans_info = []  # 스팬 정보 리스트
                        whitespace_info = []  # 공백 정보 리스트

                        for span in line["spans"]:  # 스팬 순회
                            text = span["text"]  # 스팬 텍스트
                            if text:  # 텍스트가 존재하는 경우
                                spaces = []  # 공백 위치 리스트
                                for i, char in enumerate(text):  # 문자별 순회
                                    if char in (" ", "\t"):  # 공백 또는 탭 문자인 경우
                                        spaces.append({"position": i, "type": "tab" if char == "\t" else "space"})  # 공백 정보 저장
                                whitespace_info.extend(spaces)  # 공백 정보 확장

                                safe_text = text  # 안전한 텍스트 저장
                                spans_info.append({  # 스팬 정보 저장
                                    "text": safe_text,
                                    "bbox": span["bbox"],
                                    "font": span.get("font", "Unknown"),
                                    "size": span.get("size", 10),
                                    "flags": span.get("flags", 0),
                                    "color": span.get("color", 0)
                                })
                                line_texts.append(safe_text)  # 라인 텍스트에 추가

                        if line_texts:  # 라인 텍스트가 존재하는 경우
                            merged_line = "".join(line_texts)  # 라인 텍스트 병합
                            block_lines.append({"text": merged_line, "bbox": line_bbox})  # 블록 라인에 추가

                    if block_lines:  # 블록 라인이 존재하는 경우
                        merged_lines = []  # 병합된 라인 리스트
                        for i, line in enumerate(block_lines):  # 라인별 순회
                            merged_lines.append(line["text"])  # 라인 텍스트 추가
                            if i < len(block_lines) - 1:  # 마지막 라인이 아닌 경우
                                curr_bbox = line["bbox"]  # 현재 라인 경계 상자
                                next_bbox = block_lines[i + 1]["bbox"]  # 다음 라인 경계 상자
                                y_gap = next_bbox[1] - curr_bbox[3]  # y축 간격 계산
                                if y_gap > 2:  # 간격이 2보다 큰 경우
                                    merged_lines.append("\n")  # 줄바꿈 추가

                        merged_text = "".join(merged_lines)  # 전체 텍스트 병합

                        main_font = self._get_main_font(spans_info)  # 주요 폰트 추출
                        is_bold = self._check_bold(spans_info)  # 볼드 여부 확인
                        font_size = self._get_average_size(spans_info)  # 평균 폰트 크기

                        block_id = f"text_{page_data['page_number']}_{block_idx}"  # 블록 ID 생성
                        block_idx += 1  # 블록 인덱스 증가

                        text_blocks.append({  # 텍스트 블록 정보 저장
                            "id": block_id,
                            "text": merged_text,
                            "x0": block_bbox[0],
                            "y0": block_bbox[1],
                            "x1": block_bbox[2],
                            "y1": block_bbox[3],
                            "font": main_font,
                            "is_bold": is_bold,
                            "size": font_size,
                            "spans": spans_info,
                            "level": 0,
                            "parent_id": None,
                            "whitespace_info": whitespace_info
                        })

            merged_blocks = self._merge_text_blocks(text_blocks)  # 텍스트 블록 병합
            merged_blocks.sort(key=lambda b: (round(b["y0"], 1), round(b["x0"], 1)))  # y, x 좌표로 정렬

            page_data["text_blocks"] = merged_blocks  # 페이지 데이터에 텍스트 블록 저장
            page_text = []  # 페이지 전체 텍스트 리스트
            for i, block in enumerate(merged_blocks):  # 블록별 순회
                page_text.append(block["text"])  # 블록 텍스트 추가
                if i < len(merged_blocks) - 1:  # 마지막 블록이 아닌 경우
                    curr_block = block  # 현재 블록
                    next_block = merged_blocks[i + 1]  # 다음 블록
                    y_gap = next_block["y0"] - curr_block["y1"]  # y축 간격
                    if (y_gap > 2 or  # 간격이 2보다 크거나
                        curr_block["size"] != next_block["size"] or  # 폰트 크기가 다르거나
                        curr_block["is_bold"] != next_block["is_bold"] or  # 볼드 여부가 다르거나
                        curr_block["level"] != next_block["level"]):  # 레벨이 다른 경우
                        page_text.append("\n")  # 줄바꿈 추가
            page_data["text"] = "".join(page_text)  # 전체 텍스트 병합

            self._log(f"Extracted {len(merged_blocks)} text blocks on page {page_data['page_number']} (excluding table text)")

            # 텍스트 블록이 없으면 OCR로 보완
            if not merged_blocks:  # 텍스트 블록이 없는 경우
                self._log(f"No text blocks extracted on page {page_data['page_number']}, attempting OCR", level="WARNING")
                ocr_text = self.extract_text_ocr(fitz_page)  # OCR로 텍스트 추출
                if ocr_text:  # OCR 텍스트가 있는 경우
                    # OCR 텍스트를 줄 단위로 분리하여 text_blocks 생성
                    lines = ocr_text.split('\n')  # 줄바꿈으로 분리
                    y_step = page_data["height"] / max(1, len(lines))  # 페이지 높이를 줄 수로 나눔
                    for i, line in enumerate(lines):  # 라인별 순회
                        if line.strip():  # 빈 라인이 아닌 경우
                            block_id = f"text_{page_data['page_number']}_ocr_{i}"  # OCR 블록 ID
                            # 상단 중앙 가정: x는 페이지 중앙, y는 상단부터 순차 배치
                            x_center = page_data["width"] / 2  # 페이지 중앙 x 좌표
                            x0 = x_center - 100  # 임의 너비 (왼쪽)
                            x1 = x_center + 100  # 임의 너비 (오른쪽)
                            y0 = i * y_step  # y 시작 좌표
                            y1 = (i + 1) * y_step  # y 끝 좌표
                            text_blocks.append({  # OCR 텍스트 블록 추가
                                "id": block_id,
                                "text": line.strip(),
                                "x0": x0,
                                "y0": y0,
                                "x1": x1,
                                "y1": y1,
                                "font": "Unknown",
                                "is_bold": False,
                                "size": 10,
                                "spans": [],
                                "level": 0,
                                "parent_id": None,
                                "whitespace_info": [  # 공백 정보 생성
                                    {"position": j, "type": "space"}
                                    for j, char in enumerate(line) if char in (" ", "\t")
                                ]
                            })
                    page_data["text_blocks"] = text_blocks  # OCR 텍스트 블록 저장
                    page_data["text"] = ocr_text  # OCR 전체 텍스트 저장
                    self._log(f"OCR extracted {len(text_blocks)} text blocks on page {page_data['page_number']}")

        except Exception as e:  # 예외 발생 시
            self._log(f"Enhanced text extraction failed: {e}", level="ERROR")
            self.extract_text_line_based(plumber_page, fitz_page, page_data)  # 폴백 메서드 호출

    
    def _merge_line_text(self, spans_info):
    # 기능: 스팬 정보를 기반으로 라인 텍스트 병합
    # 로직:
    # 1. 스팬 간 공백 삽입 여부 결정
    # 2. 텍스트를 공백으로 연결
        if not spans_info:  # 스팬 정보가 없는 경우
            return ""  # 빈 문자열 반환
        
        merged = []  # 병합된 텍스트 리스트
        prev_bbox = None  # 이전 스팬 경계 상자
        
        for span in spans_info:  # 스팬 순회
            text = span["text"]  # 스팬 텍스트 추출
            bbox = span["bbox"]  # 스팬 경계 상자
            
            if prev_bbox:  # 이전 경계 상자가 있는 경우
                gap = bbox[0] - prev_bbox[2]  # 스팬 간 간격 계산
                if gap > span["size"] * 0.2:  # 간격이 폰트 크기의 20% 초과 시
                    merged.append(" ")  # 공백 삽입
            merged.append(text)  # 텍스트 추가
            prev_bbox = bbox  # 현재 경계 상자 저장
        
        return "".join(merged)  # 병합된 텍스트 반환

    
    def _get_main_font(self, spans_info):
    # 기능: 스팬 정보에서 주요 폰트 추출
    # 로직:
    # 1. 폰트별 텍스트 길이 집계
    # 2. 가장 많이 사용된 폰트 반환
        font_counts = defaultdict(int)  # 폰트별 문자 수 카운터
        for span in spans_info:  # 스팬 순회
            font_counts[span["font"]] += len(span["text"])  # 폰트별 문자 수 추가
        
        if font_counts:  # 폰트 카운터가 있는 경우
            return max(font_counts.items(), key=lambda x: x[1])[0]  # 가장 많이 사용된 폰트 반환
        return "Unknown"  # 기본값 반환

   
    def _check_bold(self, spans_info):
    # 기능: 스팬 정보에서 볼드 여부 확인
    # 로직:
    # 1. 폰트 플래그 또는 폰트 이름에 'bold' 포함 여부 확인
    # 2. 볼드인 경우 True 반환
        for span in spans_info:  # 스팬 순회
            if span["flags"] & 16 or "bold" in span["font"].lower():  # 볼드 플래그 또는 이름 확인
                return True  # 볼드임
        return False  # 볼드 아님

    
    def _get_average_size(self, spans_info):
    # 기능: 스팬 정보에서 평균 폰트 크기 계산
    # 로직:
    # 1. 텍스트 길이에 가중치를 둔 폰트 크기 합산
    # 2. 평균 크기 반환
        if not spans_info:  # 스팬 정보가 없는 경우
            return 10  # 기본 크기 반환
        
        total_size = sum(span["size"] * len(span["text"]) for span in spans_info)  # 가중 폰트 크기 합
        total_chars = sum(len(span["text"]) for span in spans_info)  # 총 문자 수
        
        return total_size / total_chars if total_chars > 0 else 10  # 평균 크기 반환

    
    def _merge_text_blocks(self, text_blocks):
    # 기능: 텍스트 블록 병합
    # 로직:
    # 1. y 좌표로 블록 정렬
    # 2. 근접한 블록을 라인 단위로 병합
        if not text_blocks:  # 텍스트 블록이 없는 경우
            return []  # 빈 리스트 반환
        
        text_blocks.sort(key=lambda b: (b["y0"], b["x0"]))  # y, x 좌표로 정렬
        
        merged = []  # 병합된 블록 리스트
        current_line = []  # 현재 라인 블록 리스트
        current_y = None  # 현재 y 좌표
        y_tolerance = 2  # y 좌표 허용 오차
        
        for block in text_blocks:  # 블록 순회
            if current_y is None:  # 첫 블록인 경우
                current_y = block["y0"]  # 현재 y 좌표 설정
                current_line = [block]  # 현재 라인에 블록 추가
            elif abs(block["y0"] - current_y) <= y_tolerance:  # y 좌표가 허용 범위 내인 경우
                current_line.append(block)  # 현재 라인에 블록 추가
            else:  # 새로운 라인 시작
                if current_line:  # 현재 라인이 있는 경우
                    merged.extend(self._merge_line_blocks(current_line))  # 라인 병합
                current_y = block["y0"]  # 새로운 y 좌표 설정
                current_line = [block]  # 새로운 라인 시작
        
        if current_line:  # 마지막 라인 처리
            merged.extend(self._merge_line_blocks(current_line))  # 라인 병합
        
        # 수정: 단락 끝에 줄바꿈 삽입
        merged_with_newlines = []  # 줄바꿈이 추가된 병합 결과
        prev_block = None  # 이전 블록
        for block in merged:  # 병합된 블록 순회
            if prev_block:  # 이전 블록이 있는 경우
                y_gap = block["y0"] - prev_block["y1"]  # y축 간격
                # 단락 끝 판단: y좌표 차이, 폰트 크기, 볼드 여부, 레벨 변경
                if (y_gap > y_tolerance or  # y축 간격이 허용치 초과
                    block["size"] != prev_block["size"] or  # 폰트 크기가 다름
                    block["is_bold"] != prev_block["is_bold"] or  # 볼드 여부가 다름
                    block["level"] != prev_block["level"]):  # 계층 레벨이 다름
                    block["text"] = "\n" + block["text"]  # 단락 끝에 줄바꿈 추가
            merged_with_newlines.append(block)  # 병합 결과에 추가
            prev_block = block  # 이전 블록 업데이트
        
        return merged_with_newlines  # 병합된 블록 반환

    
    def _merge_line_blocks(self, line_blocks):
    # 기능: 같은 라인의 텍스트 블록 병합
    # 로직:
    # 1. x 좌표로 블록 정렬
    # 2. 근접한 블록을 공백으로 연결
        if not line_blocks:  # 라인 블록이 없는 경우
            return []  # 빈 리스트 반환
        
        line_blocks.sort(key=lambda b: b["x0"])  # x 좌표로 정렬
        
        merged = []  # 병합된 블록 리스트
        current = None  # 현재 병합 중인 블록
        
        for block in line_blocks:  # 블록 순회
            if current is None:  # 첫 블록인 경우
                current = block.copy()  # 블록 복사
            else:  # 이후 블록
                gap = block["x0"] - current["x1"]  # 블록 간 간격 계산
                char_width = current["size"] * 0.5  # 문자 너비 추정
                
                if gap <= char_width * 1.5:  # 간격이 문자 너비의 1.5배 이내인 경우
                    current["text"] += " " + block["text"]  # 공백으로 텍스트 병합
                    current["x1"] = block["x1"]  # x1 업데이트
                    current["y1"] = max(current["y1"], block["y1"])  # y1 업데이트
                    current["whitespace_info"].extend(block["whitespace_info"])  # 공백 정보 병합
                else:  # 새로운 블록 시작
                    merged.append(current)  # 현재 블록 추가
                    current = block.copy()  # 새 블록 복사
        
        if current:  # 마지막 블록 처리
            merged.append(current)  # 현재 블록 추가
        
        return merged  # 병합된 블록 반환

    
    def _infer_hierarchy(self, text_blocks):
    # 기능: 텍스트 블록의 계층 구조 추론
    # 로직:
    # 1. 폰트 크기와 x 오프셋으로 계층 레벨 결정
    # 2. 볼드 텍스트와 x 오프셋으로 부모-자식 관계 설정
        if not text_blocks:  # 텍스트 블록이 없는 경우
            return []  # 빈 리스트 반환

        sorted_blocks = sorted(text_blocks, key=lambda b: (b["y0"], b["x0"]))  # y, x 좌표로 정렬
        hierarchy = []  # 계층 구조 리스트
        font_sizes = sorted(set(b["size"] for b in sorted_blocks), reverse=True)  # 폰트 크기 리스트 (내림차순)
        current_level = 0  # 현재 계층 레벨
        last_block = None  # 마지막 블록

        for block in sorted_blocks:  # 블록 순회
            font_size = block["size"]  # 폰트 크기
            x_offset = block["x0"]  # x 오프셋

            if font_sizes:  # 폰트 크기 리스트가 있는 경우
                level = font_sizes.index(font_size) if font_size in font_sizes else len(font_sizes)  # 폰트 크기로 레벨 결정
            else:  # 폰트 크기 리스트가 없는 경우
                level = 0  # 기본 레벨

            if block["is_bold"]:  # 볼드 텍스트인 경우
                level = max(0, level - 1)  # 레벨 감소

            if last_block and x_offset > last_block["x0"] + 5:  # x 오프셋이 이전 블록보다 큰 경우
                level = last_block["level"] + 1  # 하위 레벨 설정
                block["parent_id"] = last_block["id"]  # 부모 ID 설정
            else:  # x 오프셋이 같거나 작은 경우
                block["parent_id"] = None  # 부모 ID 없음

            block["level"] = level  # 레벨 저장
            hierarchy.append(block)  # 계층 구조에 추가
            last_block = block  # 마지막 블록 업데이트

        return hierarchy  # 계층 구조 반환

    
    def _extract_metadata_from_first_page(self, first_page_data):
        """첫 페이지에서 메타데이터 추출 - 개선된 버전"""
        text_blocks = first_page_data["text_blocks"]  # 첫 페이지 텍스트 블록
        
        if not text_blocks:  # 텍스트 블록이 없는 경우
            self._log("No text blocks found for metadata extraction", level="WARNING")
            return  # 함수 종료
        
        # 전체 텍스트를 결합하여 컨텍스트 파악
        full_text = "\n".join([block["text"].strip() for block in text_blocks])  # 전체 텍스트 병합
        
        # 1. CM_name (암호모듈명) 추출 - 더 정확한 패턴 사용
        cm_patterns = [  # 암호모듈명 추출용 정규식 패턴들
            r'암호모듈명\s*[:：]\s*(.+)',
            r'모듈명\s*[:：]\s*(.+)',
            r'제품명\s*[:：]\s*(.+)',
            r'CM\s+Name\s*[:：]\s*(.+)',
            # 특정 키워드 앞의 텍스트를 모듈명으로 추정
            r'^([^:：\n]+?)(?=\s*(?:V\d+\.\d+|버전|Version))'
        ]
        
        for pattern in cm_patterns:  # 패턴별 순회
            match = re.search(pattern, full_text, re.MULTILINE | re.IGNORECASE)  # 정규식 매칭
            if match:  # 매칭된 경우
                self.doc_info["metadata"]["CM_name"] = match.group(1).strip()  # 암호모듈명 저장
                self._log(f"Extracted CM_name: {self.doc_info['metadata']['CM_name']}")
                break  # 첫 번째 매칭으로 종료
        
        # CM_name을 못 찾은 경우, 첫 번째 의미있는 텍스트 블록 사용
        if not self.doc_info["metadata"]["CM_name"]:  # 암호모듈명이 없는 경우
            for block in text_blocks:  # 텍스트 블록 순회
                text = block["text"].strip()  # 블록 텍스트 정리
                # 제목이나 헤더가 아닌 실제 내용으로 보이는 텍스트
                if (text and   # 텍스트가 존재하고
                    not re.match(r'^(시험|결과|보고서|Test|Report)', text, re.IGNORECASE) and  # 헤더가 아니고
                    len(text) > 5 and  # 길이가 5자 초과이고
                    not re.match(r'^\d+$', text)):  # 페이지 번호 제외
                    self.doc_info["metadata"]["CM_name"] = text  # 암호모듈명으로 저장
                    self._log(f"Extracted CM_name from first content block: {text}")
                    break  # 첫 번째 유효한 텍스트로 종료
        
        # 2. 버전 추출 - 이미 잘 동작하는 부분
        version_pattern = r'(?:V|v|버전|Version)\s*(\d+\.\d+(?:\.\d+)?)'  # 버전 패턴
        version_match = re.search(version_pattern, full_text)  # 버전 매칭
        if version_match:  # 버전이 매칭된 경우
            self.doc_info["metadata"]["version"] = f"V{version_match.group(1)}"  # 버전 저장
            self._log(f"Extracted version: {self.doc_info['metadata']['version']}")
        
        # 3. 날짜 추출 - 더 유연한 패턴
        date_patterns = [  # 날짜 추출용 정규식 패턴들
            # 다양한 날짜 형식 지원
            r'(\d{4})\s*[년\-\.]\s*(\d{1,2})\s*[월\-\.]\s*(\d{1,2})\s*일?',
            r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})',
            r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
            # 작성일, 발행일 등의 레이블과 함께
            r'(?:작성일|발행일|날짜|Date)\s*[:：]?\s*(\d{4}[\-\.\/]\d{1,2}[\-\.\/]\d{1,2})',
        ]
        
        for pattern in date_patterns:  # 날짜 패턴별 순회
            match = re.search(pattern, full_text)  # 날짜 매칭
            if match:  # 매칭된 경우
                if len(match.groups()) == 3:  # 연, 월, 일을 각각 추출한 경우
                    year, month, day = match.groups()  # 연, 월, 일 추출
                    if len(year) == 2:  # YY 형식인 경우
                        year = "20" + year  # 20YY 형식으로 변환
                    self.doc_info["metadata"]["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"  # 날짜 저장
                else:  # 전체 날짜 문자열을 추출한 경우
                    self.doc_info["metadata"]["date"] = match.group(1)  # 날짜 저장
                self._log(f"Extracted date: {self.doc_info['metadata']['date']}")
                break  # 첫 번째 매칭으로 종료
        
        # 4. 시험기관명 추출 - 더 정확한 패턴
        org_patterns = [  # 시험기관명 추출용 정규식 패턴들
            r'(?:시험기관|검증기관|평가기관|기관명|Organization)\s*[:：]\s*(.+?)(?=\n|$)',
            r'(?:시험|검증|평가)\s*[:：]\s*(.+?)(?=\n|$)',
            # 페이지 하단의 기관명 (주소나 전화번호 앞)
            r'^([가-힣A-Za-z\s]+(?:연구소|연구원|센터|Institute|Center|Lab))(?=.*(?:주소|전화|Tel|Address))',
        ]
        
        for pattern in org_patterns:  # 기관명 패턴별 순회
            match = re.search(pattern, full_text, re.MULTILINE | re.IGNORECASE)  # 기관명 매칭
            if match:  # 매칭된 경우
                self.doc_info["metadata"]["test_organization"] = match.group(1).strip()  # 시험기관명 저장
                self._log(f"Extracted test_organization: {self.doc_info['metadata']['test_organization']}")
                break  # 첫 번째 매칭으로 종료
        
        # 시험기관을 못 찾은 경우, 하단의 기관명으로 보이는 텍스트 찾기
        if not self.doc_info["metadata"]["test_organization"]:  # 시험기관명이 없는 경우
            # 페이지 하단 1/3 영역의 텍스트 블록들 확인
            page_height = first_page_data.get("height", 800)  # 페이지 높이
            bottom_threshold = page_height * 0.67  # 하단 경계선 (페이지 높이의 67%)
            
            for block in reversed(text_blocks):  # 아래에서부터 검색
                if block["y0"] > bottom_threshold:  # 하단 영역인 경우
                    text = block["text"].strip()  # 블록 텍스트 정리
                    # 기관명으로 보이는 패턴
                    if (re.search(r'(연구소|연구원|센터|기관|Institute|Center|Lab)', text, re.IGNORECASE) or  # 기관 키워드 포함
                        (len(text) > 5 and len(text) < 50 and not re.match(r'^\d', text))):  # 적당한 길이의 텍스트
                        self.doc_info["metadata"]["test_organization"] = text  # 시험기관명 저장
                        self._log(f"Extracted test_organization from bottom: {text}")
                        break  # 첫 번째 유효한 기관명으로 종료
        
        # 디버깅을 위한 로그
        if not self.doc_info["metadata"]["CM_name"]:  # 암호모듈명이 없는 경우
            self._log("Failed to extract CM_name", level="WARNING")
        if not self.doc_info["metadata"]["date"]:  # 날짜가 없는 경우
            self._log("Failed to extract date", level="WARNING")
        if not self.doc_info["metadata"]["test_organization"]:  # 시험기관명이 없는 경우
            self._log("Failed to extract test_organization", level="WARNING")


    def _merge_metadata_lines(self, text_blocks):
        """메타데이터 추출을 위한 같은 줄의 텍스트 블록 병합"""
        if not text_blocks:  # 텍스트 블록이 없는 경우
            return []  # 빈 리스트 반환
        
        # y 좌표로 정렬
        sorted_blocks = sorted(text_blocks, key=lambda b: (b["y0"], b["x0"]))  # y, x 좌표로 정렬
        merged_lines = []  # 병합된 라인 리스트
        current_line = []  # 현재 라인 블록 리스트
        current_y = None  # 현재 y 좌표
        y_tolerance = 3  # y 좌표 허용 오차
        
        for block in sorted_blocks:  # 블록 순회
            if current_y is None:  # 첫 블록인 경우
                current_y = block["y0"]  # 현재 y 좌표 설정
                current_line = [block]  # 현재 라인에 블록 추가
            elif abs(block["y0"] - current_y) <= y_tolerance:  # y 좌표가 허용 범위 내인 경우
                # 같은 줄의 블록
                current_line.append(block)  # 현재 라인에 블록 추가
            else:  # 새로운 줄 시작
                if current_line:  # 현재 라인이 있는 경우
                    # 같은 줄의 블록들을 x 좌표 순으로 정렬하여 병합
                    current_line.sort(key=lambda b: b["x0"])  # x 좌표로 정렬
                    merged_text = " ".join([b["text"].strip() for b in current_line])  # 텍스트 병합
                    merged_block = {  # 병합된 블록 정보
                        "text": merged_text,
                        "x0": current_line[0]["x0"],
                        "y0": current_line[0]["y0"],
                        "x1": current_line[-1]["x1"],
                        "y1": max(b["y1"] for b in current_line),
                        "font": current_line[0].get("font", "Unknown"),
                        "size": current_line[0].get("size", 10),
                        "is_bold": current_line[0].get("is_bold", False)
                    }
                    merged_lines.append(merged_block)  # 병합된 라인 추가
                current_y = block["y0"]  # 새로운 y 좌표 설정
                current_line = [block]  # 새로운 라인 시작
        
        # 마지막 줄 처리
        if current_line:  # 마지막 라인이 있는 경우
            current_line.sort(key=lambda b: b["x0"])  # x 좌표로 정렬
            merged_text = " ".join([b["text"].strip() for b in current_line])  # 텍스트 병합
            merged_block = {  # 병합된 블록 정보
                "text": merged_text,
                "x0": current_line[0]["x0"],
                "y0": current_line[0]["y0"],
                "x1": current_line[-1]["x1"],
                "y1": max(b["y1"] for b in current_line),
                "font": current_line[0].get("font", "Unknown"),
                "size": current_line[0].get("size", 10),
                "is_bold": current_line[0].get("is_bold", False)
            }
            merged_lines.append(merged_block)  # 병합된 라인 추가
        
        return merged_lines  # 병합된 라인 리스트 반환
    
    def extract_text_line_based(self, plumber_page, fitz_page, page_data):
    # 기능: 라인 기반 텍스트 추출 (폴백)
    # 로직:
    # 1. fitz의 dict 형식으로 텍스트 추출
    # 2. 테이블 내부 텍스트 제외
    # 3. 중복 제거 후 텍스트 블록 생성
        try:
            text_blocks_line = []  # 라인 기반 텍스트 블록 리스트
            blocks = fitz_page.get_text("dict")["blocks"]  # dict 형식으로 블록 추출
            block_idx = 0  # 블록 인덱스 초기화

            table_bboxes = [table["bbox"] for table in page_data.get("tables", [])]  # 테이블 경계 상자 리스트

            for b in blocks:  # 블록 순회
                if b["type"] == 0:  # 텍스트 블록인 경우
                    for line in b["lines"]:  # 라인 순회
                        line_bbox = line["bbox"]  # 라인 경계 상자
                        if any(self._is_inside_bbox(line_bbox, table_bbox) for table_bbox in table_bboxes):  # 테이블 내부인지 확인
                            continue  # 테이블 내부면 스킵

                        line_strs = []  # 라인 텍스트 리스트
                        x0, y0, x1, y1 = float('inf'), float('inf'), float('-inf'), float('-inf')  # 경계 상자 초기화
                        font_name = None  # 폰트 이름 초기화
                        font_size = 0  # 폰트 크기 초기화
                        is_bold = False  # 볼드 여부 초기화
                        whitespace_info = []  # 공백 정보 리스트

                        for span in line["spans"]:  # 스팬 순회
                            raw_text = span["text"]  # 원본 텍스트 추출
                            if raw_text:  # 텍스트가 있는 경우
                                safe_text = raw_text  # 안전한 텍스트 (원문 유지)
                                spaces = []  # 공백 정보 리스트
                                for i, char in enumerate(safe_text):  # 문자 순회
                                    if char in (" ", "\t"):  # 공백 또는 탭인 경우
                                        spaces.append({"position": i, "type": "tab" if char == "\t" else "space"})  # 공백 정보 추가
                                whitespace_info.extend(spaces)  # 공백 정보 저장

                                line_strs.append(safe_text)  # 라인 텍스트 추가

                            sx0, sy0, sx1, sy1 = span["bbox"]  # 스팬 경계 상자
                            x0 = min(x0, sx0)  # 최소 x0 업데이트
                            y0 = min(y0, sy0)  # 최소 y0 업데이트
                            x1 = max(x1, sx1)  # 최대 x1 업데이트
                            y1 = max(y1, sy1)  # 최대 y1 업데이트

                            if font_name is None:  # 폰트 이름이 없는 경우
                                font_name = span.get("font", "Unknown")  # 폰트 이름 설정
                                is_bold = "bold" in font_name.lower()  # 볼드 여부 확인
                            font_size = max(font_size, span.get("size", 0))  # 최대 폰트 크기 업데이트

                        has_korean = any('\uAC00' <= c <= '\uD7A3' for c in "".join(line_strs))  # 한글 포함 여부 확인
                        merged_text = " ".join(line_strs)  # 라인 텍스트 공백으로 병합

                        if merged_text:  # 병합된 텍스트가 있는 경우
                            block_id = f"text_{page_data['page_number']}_{block_idx}"  # 블록 ID 생성
                            block_idx += 1  # 블록 인덱스 증가
                            text_blocks_line.append({  # 텍스트 블록 추가
                                "id": block_id,  # 블록 ID
                                "text": merged_text,  # 병합된 텍스트
                                "x0": x0,  # x0 좌표
                                "y0": y0,  # y0 좌표
                                "x1": x1,  # x1 좌표
                                "y1": y1,  # y1 좌표
                                "font": font_name,  # 폰트 이름
                                "is_bold": is_bold,  # 볼드 여부
                                "size": font_size,  # 폰트 크기
                                "level": 0,  # 계층 레벨
                                "parent_id": None,  # 부모 ID
                                "whitespace_info": whitespace_info  # 공백 정보
                            })

            seen = set()  # 중복 체크를 위한 집합
            unique_blocks = []  # 고유 블록 리스트
            for blk in text_blocks_line:  # 텍스트 블록 순회
                key = (blk["text"], round(blk["x0"], 1), round(blk["y0"], 1))  # 중복 확인 키
                if key not in seen and blk["text"]:  # 중복되지 않고 텍스트가 있는 경우
                    seen.add(key)  # 키 추가
                    unique_blocks.append(blk)  # 고유 블록 추가

            unique_blocks.sort(key=lambda b: (b["y0"], b["x0"]))  # y, x 좌표로 정렬

            page_data["text_blocks"] = unique_blocks  # 페이지 데이터에 블록 저장
            # 수정: 블록 간 줄바꿈으로 텍스트 병합, 단락 끝 유지
            page_text = []  # 페이지 텍스트 리스트
            for i, block in enumerate(unique_blocks):  # 블록별 순회
                page_text.append(block["text"])  # 블록 텍스트 추가
                if i < len(unique_blocks) - 1:  # 마지막 블록이 아닌 경우
                    curr_block = block  # 현재 블록
                    next_block = unique_blocks[i + 1]  # 다음 블록
                    y_gap = next_block["y0"] - curr_block["y1"]  # y축 간격
                    if (y_gap > 2 or  # 간격이 2보다 크거나
                        curr_block["size"] != next_block["size"] or  # 폰트 크기가 다르거나
                        curr_block["is_bold"] != next_block["is_bold"] or  # 볼드 여부가 다르거나
                        curr_block["level"] != next_block["level"]):  # 레벨이 다른 경우
                        page_text.append("\n")  # 줄바꿈 추가
            page_data["text"] = "".join(page_text)  # 전체 텍스트 병합

        except Exception as e:  # 예외 발생 시
            self._log(f"Line-based text extraction failed: {e}", level="ERROR")  # 라인 기반 추출 실패 로그

    
    def extract_text_ocr(self, fitz_page):
    # 기능: OCR로 페이지 텍스트 추출
    # 로직:
    # 1. 페이지를 고해상도 이미지로 변환
    # 2. 이미지 전처리 후 pytesseract로 텍스트 추출
        try:
            pix = fitz_page.get_pixmap(dpi=300)  # 300 DPI로 페이지 이미지 생성
            img_data = pix.tobytes()  # 이미지 바이트 데이터 추출
            img = Image.open(io.BytesIO(img_data))  # 이미지 객체 생성
            
            img_np = np.array(img)  # 이미지를 numpy 배열로 변환
            if len(img_np.shape) == 3:  # 컬러 이미지인 경우
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)  # 그레이스케일로 변환
            img_np = cv2.GaussianBlur(img_np, (3, 3), 0)  # 가우시안 블러 적용
            img_np = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]  # 이진화 처리
            img = Image.fromarray(img_np)  # numpy 배열을 이미지로 변환
            
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'  # OCR 설정
            text = pytesseract.image_to_string(img, lang='eng+kor', config=custom_config)  # OCR로 텍스트 추출
            self._log(f"OCR extracted text length: {len(text)}")  # 추출된 텍스트 길이 로그
            return text or ""  # 텍스트 반환
        except Exception as e:  # 예외 발생 시
            self._log(f"OCR failed: {e}", level="ERROR")  # OCR 실패 로그
            return ""  # 빈 문자열 반환

    
    def _clean_table_data(self, raw_data):
        # 기능: 테이블 데이터에서 불필요한 null과 빈 문자열을 제거하여 최적화
        
        # Args:
        #     raw_data: pdfplumber에서 추출한 원본 테이블 데이터
            
        # Returns:
        #     cleaned_data: 최적화된 테이블 데이터
        
        if not raw_data:  # 원본 데이터가 없는 경우
            return []  # 빈 리스트 반환
        
        cleaned_data = []  # 정리된 데이터 리스트
        
        for row in raw_data:  # 행별 순회
            if not row:  # 빈 행은 건너뛰기
                continue
                
            # 각 셀의 null, None, 빈 문자열을 제거
            cleaned_row = []  # 정리된 행
            for cell in row:  # 셀별 순회
                if cell is not None and str(cell).strip() != "":  # 유효한 셀인 경우
                    cleaned_row.append(str(cell).strip())  # 정리된 셀 추가
            
            # 완전히 빈 행이 아닌 경우에만 추가
            if cleaned_row:  # 정리된 행이 있는 경우
                cleaned_data.append(cleaned_row)  # 정리된 데이터에 추가
        
        return cleaned_data  # 정리된 데이터 반환

    def _optimize_table_structure(self, raw_data):
        # 기능: 테이블 구조를 분석하여 키-값 쌍으로 최적화
        # Args:
        #     raw_data: 정리된 테이블 데이터
        # Returns:
        #     optimized_data: 구조화된 테이블 데이터

        if not raw_data or len(raw_data) == 0:  # 데이터가 없거나 빈 경우
            return {"type": "empty", "data": []}  # 빈 테이블 구조 반환
        
        # 테이블 구조 분석
        max_cols = max(len(row) for row in raw_data) if raw_data else 0  # 최대 열 수
        
        # 2열 구조 (키-값 형태)인지 확인
        if max_cols == 2:  # 2열 테이블인 경우
            key_value_pairs = []  # 키-값 쌍 리스트
            for row in raw_data:  # 행별 순회
                if len(row) >= 2:  # 2개 이상의 셀이 있는 경우
                    key_value_pairs.append({  # 키-값 쌍 추가
                        "key": row[0],
                        "value": row[1]
                    })
                elif len(row) == 1:  # 1개 셀만 있는 경우
                    key_value_pairs.append({  # 키만 있는 쌍 추가
                        "key": row[0],
                        "value": ""
                    })
            
            return {  # 키-값 구조 반환
                "type": "key_value",
                "structure": "2_column",
                "data": key_value_pairs
            }
        
        # 일반 테이블 구조
        elif len(raw_data) > 0:  # 데이터가 있는 경우
            # 첫 번째 행을 헤더로 간주할지 판단
            potential_header = raw_data[0] if raw_data else []  # 잠재적 헤더
            
            # 헤더가 있는 경우
            if len(raw_data) > 1:  # 2행 이상인 경우
                return {  # 구조화된 테이블 반환
                    "type": "structured_table",
                    "structure": f"{max_cols}_column",
                    "headers": potential_header,
                    "rows": raw_data[1:]
                }
            else:  # 1행만 있는 경우
                return {  # 단일 행 구조 반환
                    "type": "single_row",
                    "structure": f"{max_cols}_column", 
                    "data": raw_data[0]
                }
        
        return {"type": "unknown", "data": raw_data}  # 알 수 없는 구조 반환

    def _clean_table_data(self, raw_data):
        # 기능: 테이블 데이터에서 불필요한 null과 빈 문자열을 제거하여 최적화
        # Args:
        #     raw_data: pdfplumber에서 추출한 원본 테이블 데이터
            
        # Returns:
        #     cleaned_data: 최적화된 테이블 데이터

        if not raw_data:  # 원본 데이터가 없는 경우
            return []  # 빈 리스트 반환
        
        cleaned_data = []  # 정리된 데이터 리스트
        
        for row in raw_data:  # 행별 순회
            if not row:  # 빈 행은 건너뛰기
                continue
                
            # 각 셀의 null, None, 빈 문자열을 제거
            cleaned_row = []  # 정리된 행
            for cell in row:  # 셀별 순회
                if cell is not None and str(cell).strip() != "":  # 유효한 셀인 경우
                    cleaned_row.append(str(cell).strip())  # 정리된 셀 추가
            
            # 완전히 빈 행이 아닌 경우에만 추가
            if cleaned_row:  # 정리된 행이 있는 경우
                cleaned_data.append(cleaned_row)  # 정리된 데이터에 추가
        
        return cleaned_data  # 정리된 데이터 반환

    def _optimize_table_structure(self, raw_data):
        # 기능: 테이블 구조를 분석하여 키-값 쌍으로 최적화
        
        # Args:
        #     raw_data: 정리된 테이블 데이터
            
        # Returns:
        #     optimized_data: 구조화된 테이블 데이터

        if not raw_data or len(raw_data) == 0:  # 데이터가 없거나 빈 경우
            return {"type": "empty", "data": []}  # 빈 테이블 구조 반환
        
        # 테이블 구조 분석
        max_cols = max(len(row) for row in raw_data) if raw_data else 0  # 최대 열 수
        
        # 2열 구조 (키-값 형태)인지 확인
        if max_cols == 2:  # 2열 테이블인 경우
            key_value_pairs = []  # 키-값 쌍 리스트
            for row in raw_data:  # 행별 순회
                if len(row) >= 2:  # 2개 이상의 셀이 있는 경우
                    key_value_pairs.append({  # 키-값 쌍 추가
                        "key": row[0],
                        "value": row[1]
                    })
                elif len(row) == 1:  # 1개 셀만 있는 경우
                    key_value_pairs.append({  # 키만 있는 쌍 추가
                        "key": row[0],
                        "value": ""
                    })
            
            return {  # 키-값 구조 반환
                "type": "key_value",
                "structure": "2_column",
                "data": key_value_pairs
            }
        
        # 일반 테이블 구조
        elif len(raw_data) > 0:  # 데이터가 있는 경우
            # 첫 번째 행을 헤더로 간주할지 판단
            potential_header = raw_data[0] if raw_data else []  # 잠재적 헤더
            
            # 헤더가 있는 경우
            if len(raw_data) > 1:  # 2행 이상인 경우
                return {  # 구조화된 테이블 반환
                    "type": "structured_table",
                    "structure": f"{max_cols}_column",
                    "headers": potential_header,
                    "rows": raw_data[1:]
                }
            else:  # 1행만 있는 경우
                return {  # 단일 행 구조 반환
                    "type": "single_row",
                    "structure": f"{max_cols}_column", 
                    "data": raw_data[0]
                }
        
        return {"type": "unknown", "data": raw_data}  # 알 수 없는 구조 반환

    def extract_tables(self, plumber_page, page_num, page_data, doc=None):
        # 기능: 표 추출 - 공백, 줄바꿈, 폰트 크기 보존 및 병합된 셀 처리, 최적화된 JSON 구조로 저장

        try:
            if doc is None:  # fitz 문서 객체가 없는 경우
                doc = fitz.open(self.pdf_file_path)  # PDF 파일 열기
            fitz_page = doc[page_num - 1]  # 해당 페이지 객체 가져오기

            table_settings = {  # 테이블 감지 설정
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 5,
                "join_tolerance": 5,
                "edge_min_length": 5,
                "min_words_vertical": 1,
                "min_words_horizontal": 1,
                "intersection_tolerance": 10,
                "text_tolerance": 10
            }

            plumber_tables = plumber_page.find_tables(table_settings=table_settings)  # 테이블 감지
            self._log(f"Found {len(plumber_tables)} tables on page {page_num}")

            table_dir = os.path.join(os.path.dirname(self.pdf_file_path), "extracted_table_images")  # 테이블 이미지 저장 디렉토리
            os.makedirs(table_dir, exist_ok=True)  # 디렉토리 생성

            tables = []  # 테이블 정보 리스트
            for t_idx, table in enumerate(plumber_tables):  # 테이블별 순회
                try:
                    table_bbox = list(table.bbox) if hasattr(table, 'bbox') else None  # 테이블 경계 상자
                    if not table_bbox:  # 경계 상자가 없는 경우
                        self._log(f"Table {t_idx} has no valid bbox, skipping", level="WARNING")
                        continue  # 다음 테이블로 넘어가기

                    # 이미지 생성
                    x0, y0, x1, y1 = table_bbox  # 경계 상자 좌표
                    margin = 5  # 여백
                    x0, y0 = max(0, x0 - margin), max(0, y0 - margin)  # 여백을 포함한 시작 좌표
                    x1, y1 = min(plumber_page.width, x1 + margin), min(plumber_page.height, y1 + margin)  # 여백을 포함한 끝 좌표
                    clip_rect = fitz.Rect(x0, y0, x1, y1)  # 클립 영역

                    pix = fitz_page.get_pixmap(matrix=fitz.Matrix(6, 6), clip=clip_rect)  # 고해상도 이미지 생성
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # PIL 이미지 객체 생성

                    img_byte_arr = io.BytesIO()  # 바이트 스트림 생성
                    img.save(img_byte_arr, format='PNG', quality=100)  # PNG 형식으로 저장
                    img_byte_arr = img_byte_arr.getvalue()  # 바이트 데이터 추출
                    base64_str = base64.b64encode(img_byte_arr).decode('utf-8')  # Base64 인코딩

                    caption = self._find_table_caption(page_data, table_bbox) if hasattr(self, '_find_table_caption') else f"Table {t_idx}"  # 테이블 캡션
                    table_id = f"table_{page_num}_{t_idx}"  # 테이블 ID
                    filename = self._sanitize_filename(caption) + ".png" if hasattr(self, '_sanitize_filename') and caption else f"{table_id}_page{page_num}.png"  # 파일명

                    table_image_path = os.path.join(table_dir, filename)  # 테이블 이미지 경로
                    base, ext = os.path.splitext(table_image_path)  # 파일명과 확장자 분리
                    counter = 1  # 파일명 카운터
                    while os.path.exists(table_image_path):  # 동일한 파일명이 존재하는 경우
                        table_image_path = f"{base}_{counter}{ext}"  # 카운터를 추가한 파일명
                        counter += 1  # 카운터 증가

                    with open(table_image_path, 'wb') as f:  # 이미지 파일 열기
                        f.write(img_byte_arr)  # 이미지 데이터 쓰기
                    self._log(f"Saved table image {t_idx} to: {table_image_path}")

                    # 표 셀 데이터 추출 및 최적화
                    raw_extracted_data = table.extract()  # 원시 테이블 데이터 추출
                    self._log(f"Extracted raw table data with {len(raw_extracted_data)} rows")
                    
                    # 개선: 데이터 정리 및 최적화
                    cleaned_data = self._clean_table_data(raw_extracted_data)  # 데이터 정리
                    optimized_data = self._optimize_table_structure(cleaned_data)  # 구조 최적화
                    
                    self._log(f"Optimized table data: {optimized_data['type']} structure with {len(cleaned_data)} clean rows")

                    tables.append({  # 테이블 정보 추가
                        "id": table_id,
                        "bbox": table_bbox,
                        "caption": caption,
                        "image_path": table_image_path,
                        # "base64_image": base64_str,  # 필요시 주석 해제
                        "raw_data": cleaned_data,  # 정리된 원본 데이터
                        "structured_data": optimized_data,  # 구조화된 데이터
                        "summary": {  # 테이블 요약 정보
                            "total_rows": len(cleaned_data),
                            "structure_type": optimized_data["type"],
                            "columns": optimized_data.get("structure", "unknown")
                        }
                    })

                except Exception as e_inner:  # 개별 테이블 처리 중 예외 발생 시
                    self._log(f"Table {t_idx} extraction failed: {e_inner}", level="ERROR")
                    import traceback  # 트레이스백 모듈 임포트
                    self._log(f"Table extraction traceback: {traceback.format_exc()}", level="DEBUG")

            page_data["tables"] = tables  # 페이지 정보에 테이블 저장
            self._log(f"Successfully extracted {len(tables)} tables from page {page_num}")

        except Exception as e:  # 전체 테이블 추출 중 예외 발생 시
            self._log(f"extract_tables failed on page {page_num}: {e}", level="ERROR")
            import traceback  # 트레이스백 모듈 임포트
            self._log(f"Extract tables traceback: {traceback.format_exc()}", level="DEBUG")

    # 안전한 파일명 변환 함수 (누락된 경우를 대비)
    def _sanitize_filename(self, filename):
        # 기능: 파일명에서 특수문자 제거
        if not filename:  # 파일명이 없는 경우
            return "unknown"  # 기본 파일명 반환
        
        import re  # 정규식 모듈 임포트
        # 특수문자를 언더스코어로 대체
        safe_name = re.sub(r'[<>:"/\\|?*\[\]]', '_', str(filename))  # 특수문자 치환
        # 연속된 언더스코어 제거
        safe_name = re.sub(r'_+', '_', safe_name)  # 연속 언더스코어 축소
        # 앞뒤 공백과 언더스코어 제거
        safe_name = safe_name.strip('_').strip()  # 양쪽 공백과 언더스코어 제거
        
        return safe_name if safe_name else "unknown"  # 처리된 파일명 또는 기본값 반환
    
    def _find_table_caption(self, page_data, table_bbox):
    # 기능: 테이블 캡션 추출
    # 로직:
    # 1. 테이블 위쪽 또는 근처 텍스트 블록 확인
    # 2. 근접성과 좌표 정렬으로 캡션 선택
        try:
            x0, y0, x1, y1 = table_bbox  # 테이블 경계 상자 좌표
            text_blocks = page_data.get("text_blocks", [])  # 텍스트 블록 리스트
            caption = None  # 캡션 초기화
            min_distance = float('inf')  # 최소 거리 초기화
            proximity_threshold = page_data["height"] * 0.15  # 근접성 임계값
            caption_pattern = re.compile(r'^(Table|Figure|그림|Fig\.)\s*\d+.*$', re.IGNORECASE)  # 캡션 패턴

            if not text_blocks:  # 텍스트 블록이 없는 경우
                self._log(f"No text blocks available for table caption on page {page_data['page_number']}", level="WARNING")
                return None  # None 반환

            caption_candidates = []  # 캡션 후보 리스트
            table_center_x = (x0 + x1) / 2  # 테이블 x 중앙 좌표
            for block in text_blocks:  # 텍스트 블록 순회
                bx0 = block.get("x0", 0)  # 블록 x0 좌표
                by0 = block.get("y0", 0)  # 블록 y0 좌표
                bx1 = block.get("x1", 0)  # 블록 x1 좌표
                by1 = block.get("y1", 0)  # 블록 y1 좌표
                text = block.get("text", "").strip()  # 블록 텍스트

                if not text:  # 텍스트가 없는 경우
                    continue  # 다음 블록으로 넘어가기

                # 상단 캡션 우선: 테이블 y0 직전 영역
                is_above = by1 <= y0  # 테이블 위쪽에 있는지 확인
                if not is_above:  # 테이블 위쪽에 없는 경우
                    self._log(f"Skipping block '{text}' at y0={by0:.1f}, y1={by1:.1f} (not above table y0={y0:.1f})")
                    continue  # 다음 블록으로 넘어가기

                # x 좌표: 테이블 중앙과 근접
                block_center_x = (bx0 + bx1) / 2  # 블록 x 중앙 좌표
                x_distance = abs(block_center_x - table_center_x)  # x축 거리
                if x_distance > (x1 - x0) / 2:  # 테이블 너비의 절반 이상 벗어남
                    self._log(f"Skipping block '{text}' at x0={bx0:.1f}, x1={bx1:.1f} (not centered with table x0={x0:.1f}, x1={x1:.1f})")
                    continue  # 다음 블록으로 넘어가기

                # y 거리: 테이블 상단과의 거리
                y_distance = y0 - by1  # y축 거리
                if y_distance > proximity_threshold:  # 근접성 임계값 초과
                    self._log(f"Skipping block '{text}' at y1={by1:.1f} (too far from table y0={y0:.1f}, threshold={proximity_threshold:.1f})")
                    continue  # 다음 블록으로 넘어가기

                normalized_text = re.sub(r'\s+', ' ', text.strip())  # 정규화된 텍스트
                priority = -1 if caption_pattern.match(normalized_text) else 0  # 캡션 패턴 우선순위
                if block.get("is_bold", False):  # 볼드 텍스트인 경우
                    priority -= 1  # 우선순위 증가

                caption_candidates.append({  # 캡션 후보 추가
                    "text": text,
                    "normalized_text": normalized_text,
                    "distance": y_distance,
                    "x_distance": x_distance,
                    "priority": priority,
                    "bbox": [bx0, by0, bx1, by1]
                })
                self._log(f"Caption candidate: '{text}' (normalized: '{normalized_text}') at {bx0:.1f},{by0:.1f}, y_distance={y_distance:.1f}, x_distance={x_distance:.1f}, priority={priority}")

            if caption_candidates:  # 캡션 후보가 있는 경우
                selected = min(caption_candidates, key=lambda c: (c["priority"], c["distance"], c["x_distance"]))  # 최적 캡션 선택
                caption = selected["text"]  # 선택된 캡션
                self._log(f"Selected table caption for table at {table_bbox}: '{caption}' (normalized: '{selected['normalized_text']}', y_distance={selected['distance']:.1f}, x_distance={selected['x_distance']:.1f}, priority={selected['priority']})")
            else:  # 캡션 후보가 없는 경우
                self._log(f"No suitable table caption found for table at {table_bbox}: y0={y0:.1f}, y1={y1:.1f}, x0={x0:.1f}, x1={x1:.1f}")

            return caption  # 캡션 반환
        except Exception as e:  # 예외 발생 시
            self._log(f"Finding table caption failed: {e}", level="ERROR")
            return None  # None 반환

    
    def _sanitize_filename(self, filename):
    # 기능: 파일명 안전화 처리
    # 로직:
    # 1. 제어 문자 및 유효하지 않은 문자 제거
    # 2. 공백과 특수문자를 언더스코어로 대체
    # 3. 최대 길이 제한
        if not filename:  # 파일명이 없는 경우
            self._log("Empty filename provided, using default", level="WARNING")
            return "unnamed"  # 기본 파일명 반환

        # 다중 공백을 단일 공백으로 정규화
        filename = re.sub(r'\s+', ' ', filename.strip())  # 공백 정규화
        filename = re.sub(r'[\n\r\t]', '', filename)  # 줄바꿈 및 제어 문자 제거
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # 유효하지 않은 문자 제거
        filename = re.sub(r'[^\w\s-]', '_', filename)  # 비문자/공백/하이픈을 언더스코어로
        filename = re.sub(r'_+', '_', filename)  # 연속된 언더스코어 축소
        filename = filename.replace(' ', '_')  # 공백을 언더스코어로
        filename = filename.strip('_')  # 양쪽 언더스코어 제거
        filename = filename[:50]  # 최대 50자 제한
        if not filename:  # 정제 후 빈 문자열인 경우
            self._log("Sanitized filename is empty, using default", level="WARNING")
            return "unnamed"  # 기본 파일명 반환
        self._log(f"Sanitized filename: {filename}")
        return filename  # 처리된 파일명 반환

    
    def extract_images_with_pdfplumber(self, plumber_page, page_data, output_dir):
    # 기능: PDF에서 이미지 추출
    # 로직:
    # 1. pdfplumber로 이미지 감지
    # 2. fitz로 이미지 데이터 추출 및 저장
    # 3. 캡션 추출 및 Base64 인코딩
        images = []  # 이미지 정보 리스트
        try:
            self._log(f"Extracting images from page {page_data['page_number']} using pdfplumber")  # 이미지 추출 시작 로그
            plumber_img_list = plumber_page.images  # pdfplumber로 이미지 리스트 추출
            self._log(f"Found {len(plumber_img_list)} images with pdfplumber")  # 감지된 이미지 수 로그

            image_dir = os.path.join(output_dir, "extracted_images")  # 이미지 저장 디렉토리
            os.makedirs(image_dir, exist_ok=True)  # 디렉토리 생성
            self._log(f"Image output directory: {image_dir}")  # 디렉토리 로그

            for idx, img_info in enumerate(plumber_img_list):  # 이미지 순회
                try:
                    x0 = float(img_info.get("x0", 0))  # x0 좌표 추출
                    x1 = float(img_info.get("x1", 0))  # x1 좌표 추출
                    top = float(img_info.get("top", 0))  # 상단 좌표 추출
                    bottom = float(img_info.get("bottom", 0))  # 하단 좌표 추출

                    if x0 > x1:  # x0가 x1보다 큰 경우
                        x0, x1 = x1, x0  # x 좌표 교환
                        self._log(f"Swapped x0, x1 for image {idx}: ({x0}, {x1})")  # 좌표 교환 로그
                    if top > bottom:  # top이 bottom보다 큰 경우
                        top, bottom = bottom, top  # y 좌표 교환
                        self._log(f"Swapped top, bottom for image {idx}: ({top}, {bottom})")  # 좌표 교환 로그

                    w = x1 - x0  # 이미지 너비 계산
                    h = bottom - top  # 이미지 높이 계산
                    min_size = 10.0  # 최소 크기

                    if w <= 0 or h <= 0:  # 크기가 유효하지 않은 경우
                        self._log(f"Invalid image dimensions: {w}x{h}, setting to {min_size}x{min_size}", level="WARNING")  # 경고 로그 출력
                        w = max(w, min_size)  # 최소 너비 설정
                        h = max(h, min_size)  # 최소 높이 설정
                        x1 = x0 + w  # x1 조정
                        bottom = top + h  # bottom 조정

                    doc = fitz.open(self.pdf_file_path)  # PDF 열기
                    mupdf_page = doc[page_data['page_number'] - 1]  # 해당 페이지 객체
                    clip_rect = fitz.Rect(x0, top, x1, bottom)  # 클립 영역 설정

                    if clip_rect.is_empty or not clip_rect.is_valid:  # 클립 영역이 유효하지 않은 경우
                        self._log(f"Invalid clip_rect for image {idx}: {clip_rect}", level="WARNING")  # 경고 로그 출력
                        doc.close()  # PDF 닫기
                        continue  # 다음 이미지로 이동

                    pix = mupdf_page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)  # 이미지 생성
                    img_bytes = pix.tobytes()  # 이미지 바이트 데이터 추출

                    img_size_mb = len(img_bytes) / (1024 * 1024)  # 이미지 크기(MB) 계산
                    if img_size_mb > 5:  # 이미지 크기가 5MB 초과 시
                        self._log(f"Large image data for image {idx}: {img_size_mb:.2f} MB", level="WARNING")  # 경고 로그 출력

                    b64_str = base64.b64encode(img_bytes).decode('utf-8')  # Base64 인코딩

                    caption = self._find_image_caption(page_data, [x0, top, x1, bottom])  # 이미지 캡션 추출
                    if caption:  # 캡션이 있는 경우
                        filename = self._sanitize_filename(caption) + ".png"  # 캡션 기반 파일명
                        self._log(f"Using caption as filename: {filename.replace('\n', '\\\\n')}")  # 파일명 로그
                    else:  # 캡션이 없는 경우
                        filename = f"img_page{page_data['page_number']}_{idx}.png"  # 기본 파일명
                        self._log(f"No caption found, using default filename: {filename}")  # 파일명 로그

                    image_path = os.path.join(image_dir, filename)  # 이미지 파일 경로
                    base, ext = os.path.splitext(image_path)  # 파일명과 확장자 분리
                    counter = 1  # 파일명 카운터
                    while os.path.exists(image_path):  # 파일이 이미 존재하는 경우
                        image_path = f"{base}_{counter}{ext}"  # 파일명에 카운터 추가
                        counter += 1  # 카운터 증가

                    try:  # 이미지 파일 저장 시도
                        with open(image_path, 'wb') as f:  # 이미지 파일 열기
                            f.write(img_bytes)  # 이미지 데이터 쓰기
                        self._log(f"Saved image {idx} to: {image_path}")  # 저장 로그
                    except Exception as e:  # 저장 실패 시
                        self._log(f"Failed to save image {idx} to {image_path}: {e}", level="ERROR")  # 실패 로그
                        fallback_filename = f"img_page{page_data['page_number']}_{idx}.png"  # 폴백 파일명
                        fallback_path = os.path.join(image_dir, fallback_filename)  # 폴백 파일 경로
                        counter = 1  # 카운터 초기화
                        base, ext = os.path.splitext(fallback_path)  # 파일명과 확장자 분리
                        while os.path.exists(fallback_path):  # 파일이 이미 존재하는 경우
                            fallback_path = f"{base}_{counter}{ext}"  # 파일명에 카운터 추가
                            counter += 1  # 카운터 증가
                        try:  # 폴백 경로로 저장 시도
                            with open(fallback_path, 'wb') as f:  # 폴백 파일 열기
                                f.write(img_bytes)  # 이미지 데이터 쓰기
                            self._log(f"Saved image {idx} to fallback path: {fallback_path}")  # 폴백 저장 로그
                            image_path = fallback_path  # 이미지 경로 업데이트
                        except Exception as e2:  # 폴백 저장 실패 시
                            self._log(f"Failed to save image {idx} to fallback path {fallback_path}: {e2}", level="ERROR")  # 실패 로그
                            doc.close()  # PDF 닫기
                            continue  # 다음 이미지로 이동

                    images.append({  # 이미지 정보 추가
                        "image_id": f"img_{page_data['page_number']}_{idx}",  # 이미지 ID
                        "base64": f"data:image/png;base64,{b64_str}",  # Base64 데이터
                        "file_path": image_path,  # 파일 경로
                        "bbox": [x0, top, x1, bottom],  # 경계 상자
                        "width": w,  # 이미지 너비
                        "height": h,  # 이미지 높이
                        "caption": caption  # 이미지 캡션
                    })
                    self._log(f"Extracted image {idx}: {w}x{h}")  # 이미지 추출 로그
                except Exception as e:  # 개별 이미지 처리 중 예외 발생 시
                    self._log(f"Extracting image {idx}: {e}, bbox={img_info.get('x0', 0)},{img_info.get('top', 0)},{img_info.get('x1', 0)},{img_info.get('bottom', 0)}", level="ERROR")  # 이미지 추출 실패 로그
                finally:  # 리소스 정리
                    if 'doc' in locals():  # fitz 문서 객체가 있는 경우
                        doc.close()  # PDF 닫기

        except Exception as e:  # 전체 이미지 추출 중 예외 발생 시
            self._log(f"pdfplumber image extraction: {e}", level="ERROR")  # 이미지 추출 실패 로그

        page_data["images"] = images  # 페이지 데이터에 이미지 저장
        return images  # 이미지 리스트 반환

    
    def _find_image_caption(self, page_data, image_bbox):
    # 기능: 이미지 캡션 추출
    # 로직:
    # 1. 이미지 근처 텍스트 블록 확인
    # 2. 캡션 패턴과 근접성으로 캡션 선택
        try:
            x0, y0, x1, y1 = image_bbox  # 이미지 경계 상자 좌표
            text_blocks = page_data.get("text_blocks", [])  # 텍스트 블록 리스트
            table_bboxes = [table["bbox"] for table in page_data.get("tables", [])]  # 테이블 경계 상자 리스트
            caption = None  # 캡션 초기화
            min_distance = float('inf')  # 최소 거리 초기화
            proximity_threshold = page_data["height"] * 0.1  # 근접성 임계값 (페이지 높이의 10%)
            caption_candidates = []  # 캡션 후보 리스트

            if not text_blocks:  # 텍스트 블록이 없는 경우
                self._log(f"No text blocks available for caption on page {page_data['page_number']}", level="WARNING")  # 경고 로그 출력
                return None  # None 반환

            caption_pattern = re.compile(r'^(Figure|Table|그림|Image|Fig\.)\s*\d+.*$', re.IGNORECASE)  # 캡션 패턴 정의

            for block in text_blocks:  # 텍스트 블록 순회
                bx0 = block.get("x0", 0)  # 블록 x0 좌표
                by0 = block.get("y0", 0)  # 블록 y0 좌표
                bx1 = block.get("x1", 0)  # 블록 x1 좌표
                by1 = block.get("y1", 0)  # 블록 y1 좌표
                text = block.get("text", "").strip()  # 블록 텍스트

                if not text:  # 텍스트가 없는 경우
                    continue  # 다음 블록으로 이동

                is_table_caption = False  # 테이블 캡션 여부
                for table_bbox in table_bboxes:  # 테이블 경계 상자 순회
                    if self._is_inside_bbox([bx0, by0, bx1, by1], table_bbox):  # 테이블 내부인지 확인
                        is_table_caption = True  # 테이블 캡션으로 표시
                        break  # 반복 종료
                if is_table_caption:  # 테이블 캡션인 경우
                    self._log(f"Skipping table caption: '{text}' at ({bx0:.1f}, {by0:.1f})")  # 스킵 로그 출력
                    continue  # 다음 블록으로 이동

                is_near_y = (y0 - proximity_threshold <= by1 <= y1 + proximity_threshold or  # y 좌표 근접성 확인
                            y0 - proximity_threshold <= by0 <= y1 + proximity_threshold)

                if not is_near_y:  # y 좌표가 근처에 없는 경우
                    continue  # 다음 블록으로 이동

                distance = min(abs(by1 - y0), abs(y1 - by0))  # 이미지와의 최소 거리 계산

                priority = 0  # 우선순위 초기화
                if caption_pattern.match(text):  # 캡션 패턴에 맞는 경우
                    priority = -1  # 우선순위 증가

                caption_candidates.append({  # 캡션 후보 추가
                    "text": text,  # 텍스트
                    "distance": distance,  # 거리
                    "priority": priority,  # 우선순위
                    "bbox": [bx0, by0, bx1, by1]  # 경계 상자
                })

            for candidate in caption_candidates:  # 캡션 후보 로그
                self._log(f"Caption candidate: '{candidate['text']}' at {candidate['bbox']}, distance={candidate['distance']:.1f}, priority={candidate['priority']}")  # 후보 로그 출력

            if caption_candidates:  # 캡션 후보가 있는 경우
                selected = min(caption_candidates, key=lambda c: (c["priority"], c["distance"]))  # 우선순위와 거리로 선택
                caption = selected["text"]  # 선택된 캡션
                self._log(f"Selected caption for image at {image_bbox}: '{caption}' (distance={selected['distance']:.1f})")  # 선택 로그
            else:  # 캡션 후보가 없는 경우
                self._log(f"No suitable caption found for image at {image_bbox}")  # 캡션 없음 로그

            return caption  # 캡션 반환
        except Exception as e:  # 예외 발생 시
            self._log(f"Finding image caption: {e}", level="ERROR")  # 캡션 찾기 실패 로그
            return None  # None 반환

    
    def save_json(self, output_json_path):
    # 기능: 추출된 데이터를 JSON 파일로 저장
    # 로직:
    # 1. 출력 디렉토리 생성
    # 2. 테이블 이미지 Base64 데이터 정규화
    # 3. JSON 파일로 데이터 저장
        try:
            output_dir = os.path.dirname(output_json_path)  # 출력 디렉토리 경로
            if output_dir and not os.path.exists(output_dir):  # 디렉토리가 없는 경우
                os.makedirs(output_dir, exist_ok=True)  # 디렉토리 생성
                self._log(f"Created output directory: {output_dir}")  # 디렉토리 생성 로그

            for page in self.doc_info["pages"]:  # 페이지 순회
                if "tables" in page:  # 테이블이 있는 경우
                    for table in page["tables"]:  # 테이블 순회
                        if "image" in table and "base64" in table["image"]:  # 이미지 Base64 데이터가 있는 경우
                            base64_str = table["image"]["base64"]  # Base64 데이터 추출
                            if not base64_str.startswith("data:image/png;base64,"):  # 접두사가 없는 경우
                                table["image"]["base64"] = f"data:image/png;base64,{base64_str}"  # 접두사 추가

            with open(output_json_path, 'w', encoding='utf-8') as f:  # JSON 파일 열기
                json.dump(self.doc_info, f, ensure_ascii=False, indent=2)  # JSON 데이터 쓰기
            self._log(f"JSON saved successfully: {output_json_path}")  # 저장 성공 로그
            return True  # 성공 반환
        except Exception as e:  # 예외 발생 시
            self._log(f"Failed to save JSON: {e}", level="ERROR")  # 저장 실패 로그
            return False  # 실패 반환


def enhanced_pdf_to_json(pdf_file_path, output_json_path, log_callback=None):
# 기능: PDF 파일을 JSON으로 변환하는 메인 함수
# 로직:
# 1. 입력 파일과 출력 경로 확인
# 2. PDFExtractor로 데이터 추출
# 3. 결과를 JSON 파일로 저장
    try:
        if not os.path.exists(pdf_file_path):  # PDF 파일이 없는 경우
            if log_callback:  # 콜백 함수가 있는 경우
                log_callback(f"[ERROR] PDF file not found: {pdf_file_path}")  # 오류 로그 출력
            else:  # 콜백 함수가 없는 경우
                print(f"[Error] PDF file not found: {pdf_file_path}")  # 콘솔 출력
            return False  # 실패 반환
        
        output_dir = os.path.dirname(output_json_path)  # 출력 디렉토리 경로
        if output_dir and not os.path.exists(output_dir):  # 디렉토리가 없는 경우
            os.makedirs(output_dir, exist_ok=True)  # 디렉토리 생성
            if log_callback:  # 콜백 함수가 있는 경우
                log_callback(f"[INFO] Created output directory: {output_dir}")  # 디렉토리 생성 로그
            else:  # 콜백 함수가 없는 경우
                print(f"[Info] Created output directory: {output_dir}")  # 콘솔 출력
        
        if log_callback:  # 콜백 함수가 있는 경우
            log_callback(f"[INFO] Starting extraction from: {pdf_file_path}")  # 추출 시작 로그
        else:  # 콜백 함수가 없는 경우
            print(f"[Info] Starting extraction from: {pdf_file_path}")  # 콘솔 출력
        
        extractor = PDFExtractor(pdf_file_path, log_callback=log_callback)  # PDFExtractor 객체 생성
        doc_info = extractor.extract()  # 데이터 추출
        
        if not doc_info:  # 추출 실패 시
            if log_callback:  # 콜백 함수가 있는 경우
                log_callback("[ERROR] Extraction failed.")  # 오류 로그 출력
            else:  # 콜백 함수가 없는 경우
                print("[Error] Extraction failed.")  # 콘솔 출력
            return False  # 실패 반환
        
        if log_callback:  # 콜백 함수가 있는 경우
            log_callback(f"[INFO] Saving to JSON: {output_json_path}")  # JSON 저장 시작 로그
        else:  # 콜백 함수가 없는 경우
            print(f"[Info] Saving to JSON: {output_json_path}")  # 콘솔 출력
        
        success = extractor.save_json(output_json_path)  # JSON 저장
        
        if success:  # 저장 성공 시
            if log_callback:  # 콜백 함수가 있는 경우
                log_callback(f"[INFO] JSON saved successfully: {output_json_path}")
            else:  # 콜백 함수가 없는 경우
                print(f"[Info] JSON saved successfully: {output_json_path}")
        else:  # 저장 실패 시
            if log_callback:  # 콜백 함수가 있는 경우
                log_callback("[ERROR] Failed to save JSON.")
            else:  # 콜백 함수가 없는 경우
                print("[Error] Failed to save JSON.")
        
        return success  # 성공/실패 여부 반환
    except Exception as e:  # 예외 발생 시
        if log_callback:  # 콜백 함수가 있는 경우
            log_callback(f"[ERROR] Unexpected error: {e}")
        else:  # 콜백 함수가 없는 경우
            print(f"[Error] Unexpected error: {e}")
        return False  # 실패 반환