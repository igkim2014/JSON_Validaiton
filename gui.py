"""
GUI 모듈 - 테이블 이미지와 판정결과 텍스트 표시 기능 및 스크롤바 추가 (개선된 TE 이미지 검색 적용)
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import fitz
from pdf_to_json import enhanced_pdf_to_json
from json_to_pdf import convert_json_to_pdf
import os
import json
import sys
import threading
import time
import re
import base64
from io import BytesIO
import hashlib
import tempfile
import copy

import pdf2image
from PIL import Image
import io


try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL 모듈을 찾을 수 없습니다. 다음 명령으로 설치할 수 있습니다: pip install pillow")

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 모듈 import
try:
    from config_reader import ConfigReader
    from validator import JSONValidator
except ImportError as e:
    print(f"모듈 임포트 오류: {e}")

# TableImagePopup 클래스 정의 - 이미지와 텍스트를 함께 표시
class TableImagePopup:
    """테이블 이미지와 판정결과 텍스트를 함께 표시하는 팝업 창"""
    
    def __init__(self, parent, title, image_data, text_content=None, validator=None, te_number=None):
        """
        팝업 창 초기화
        
        Args:
            parent (tk.Tk): 부모 창
            title (str): 팝업 창 제목
            image_data (dict): 이미지 데이터 (base64 또는 PIL Image 객체)
            text_content (str): 표시할 텍스트 내용 (선택사항)
            validator (JSONValidator): JSON 검증기 객체 (선택사항)
            te_number (str): TE 번호 (선택사항)
        """
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        self.top.grab_set()
        
        # 인스턴스 변수 초기화
        self.validator = validator
        self.te_number = te_number
        self.zoom_factor = 1.0
        self.table_zoom_factors = {}
        self.figure_zoom_factors = {}
        self.image_assignments = {}
        
        # 디버그 로그 추가
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"\n=== TableImagePopup 초기화 ===")
            print(f"TE 번호: {self.te_number}")
            print(f"Validator 존재: {self.validator is not None}")
            print(f"이미지 데이터 키: {list(image_data.keys()) if isinstance(image_data, dict) else type(image_data)}")
            print(f"텍스트 내용 제공: {text_content is not None}")
        
        # 이미지 관련 변수 초기화
        self.original_image = None
        self.photo = None
        self.image_id = None
        self.zoom_level = 1.0
        
        # 화면 크기 설정
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        window_width = int(screen_width * 0.85)
        window_height = int(screen_height * 0.85)
        
        if window_width < 600:
            window_width = 600
        
        position_right = int(screen_width/2 - window_width/2)
        position_down = int(screen_height/2 - window_height/2)
        
        self.top.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")
        
        self._create_main_container()
        self._create_image_view(image_data)
        
        if text_content or (validator and te_number):
            self._create_text_view(text_content)
        
        self._create_close_button()
        self.top.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        """팝업 창이 닫힐 때 이미지 참조와 캐시를 정리"""
        # 이미지 참조 정리
        if hasattr(self, 'photo'):
            self.photo = None
        if hasattr(self, 'original_image'):
            self.original_image = None
        
        # 캐시 정리
        self.image_assignments.clear()
        self.table_zoom_factors.clear()
        
        # 창 닫기
        self.top.destroy()

    def _create_main_container(self):
        """이미지와 텍스트를 분할 표시하기 위한 메인 컨테이너와 PanedWindow를 생성"""
        # 최상위 프레임
        self.main_container = tk.Frame(self.top)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 스크롤 콘텐츠를 위한 프레임
        self.content_frame = tk.Frame(self.main_container)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # PanedWindow로 좌우 분할 (이미지와 텍스트 영역)
        self.paned_window = tk.PanedWindow(self.content_frame, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # 왼쪽 프레임 (이미지용)
        self.left_frame = tk.Frame(self.paned_window, relief=tk.SUNKEN, borderwidth=2)
        self.paned_window.add(self.left_frame, minsize=300)

        # 오른쪽 프레임 (텍스트용)
        self.right_frame = tk.Frame(self.paned_window, relief=tk.SUNKEN, borderwidth=2)
        self.paned_window.add(self.right_frame, minsize=300)

        # 버튼 프레임을 위한 별도 프레임 (스크롤 영역 외부)
        self.button_container = tk.Frame(self.main_container)
        self.button_container.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 10))

        # 창이 렌더링된 후 분할 비율 설정
        self.top.after(100, self._set_sash_position)

    def _set_sash_position(self):
        """PanedWindow의 분할 비율을 동적으로 설정하여 이미지와 텍스트 영역의 크기를 조정"""
        def set_sash():
            self.top.update_idletasks()
            # PanedWindow의 이전 상태 초기화
            self.paned_window.forget(self.left_frame)
            self.paned_window.forget(self.right_frame)
            self.paned_window.add(self.left_frame, minsize=300)
            self.paned_window.add(self.right_frame, minsize=300)
            # 분할 비율 설정
            width = self.paned_window.winfo_width()
            if width <= 1:  # 비정상적인 너비일 경우 기본값 사용
                width = self.top.winfo_width() or 600
            sash_position = int(width * 0.6)
            self.paned_window.sash_place(0, sash_position, 0)
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"PanedWindow 너비: {width}, 분할선 위치: {sash_position}")
        
        # 렌더링 완료 후 실행
        self.top.after(200, set_sash)

    def _create_image_view2(self, image_data): ## 기존 코드: 판정 근거 표 출력하는 함수
        """
        이미지 표시를 위한 캔버스와 스크롤바를 생성하고 이미지를 표시
        
        Args:
            image_data (dict): 이미지 데이터 (base64 또는 PIL Image 객체)
        """
        # 이미지 프레임 제목
        image_label = tk.Label(self.left_frame, text="판정근거 표 이미지", font=("Arial", 12, "bold"), bg="#e6f2ff")
        image_label.pack(fill=tk.X, padx=5, pady=(5, 0))

        # 캔버스 프레임 (스크롤 포함)
        canvas_frame = tk.Frame(self.left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 캔버스와 스크롤바
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)

        self.canvas = tk.Canvas(
            canvas_frame, 
            bg='white',
            xscrollcommand=h_scrollbar.set, 
            yscrollcommand=v_scrollbar.set
        )

        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)

        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 이미지 표시 처리
        self._display_image(image_data)
    
    ## 여기부터 수정 added by yj

    def _create_image_view(self, image_data):
        """ 보조 문서 뷰어 생성 맟 TE 검색 기능 제공"""
        header_frame = tk.Frame(self.left_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        document_label = tk.Label(header_frame, text="암호모듈 시험 검증기준", 
                                font=("Arial", 12, "bold"), bg="#e6f2ff")
        document_label.pack(side=tk.LEFT)
        
        btn_frame = tk.Frame(header_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        self.document_19790_btn = tk.Button(btn_frame, text="KS_X_ISO_IEC 19790_2015", command=lambda: self._load_internal_document_with_conversion("19790"), bg="#4682B4", fg="white", padx=8)
        self.document_19790_btn.pack(side=tk.LEFT, padx=2)
        
        self.document_24759_btn = tk.Button(btn_frame, text="KS_X_ISO_IEC 24759_2015", command=lambda: self._load_internal_document_with_conversion("24759"), bg="#4682B4", fg="white", padx=8)
        self.document_24759_btn.pack(side=tk.LEFT, padx=2)
        
        search_frame = tk.Frame(self.left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(search_frame, text="검색:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 검색 엔트리 초기화 (TE 번호가 있으면 미리 설정)
        self.document_search_entry = tk.Entry(search_frame, width=20)
        if hasattr(self, 'te_number') and self.te_number:
            self.document_search_entry.insert(0, self.te_number)
        else:
            self.document_search_entry.insert(0, "TE 번호를 입력하세요")
            self.document_search_entry.config(fg='gray')
            self.document_search_entry.bind('<FocusIn>', self._clear_search_placeholder)
        
        self.document_search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.document_search_entry.bind('<Return>', self._search_in_document)
        
        self.document_search_btn = tk.Button(search_frame, text="검색", command=self._search_in_document, bg="#32CD32", fg="white")
        self.document_search_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.document_auto_search_btn = tk.Button(search_frame, text="현재 TE 시험항목", command=self._auto_search_current_te, bg="#FF6347", fg="white")
        self.document_auto_search_btn.pack(side=tk.LEFT, padx=5)
        
        nav_frame = tk.Frame(self.left_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.document_search_info_label = tk.Label(nav_frame, text="문서를 선택하세요", font=("Arial", 9), fg="#666666")
        self.document_search_info_label.pack(side=tk.LEFT)
        
        page_nav_frame = tk.Frame(self.left_frame)
        page_nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.page_info_label = tk.Label(page_nav_frame, text="페이지: -/-", font=("Arial", 9), fg="#333333")
        self.page_info_label.pack(side=tk.LEFT)
        
        page_btn_frame = tk.Frame(page_nav_frame)
        page_btn_frame.pack(side=tk.RIGHT)
        
        self.prev_page_btn = tk.Button(page_btn_frame, text="◀ 이전 페이지", command=self._go_to_prev_page, state=tk.DISABLED, width=12)
        self.prev_page_btn.pack(side=tk.LEFT, padx=2)
        
        self.next_page_btn = tk.Button(page_btn_frame, text="다음 페이지 ▶", command=self._go_to_next_page, state=tk.DISABLED, width=12)
        self.next_page_btn.pack(side=tk.LEFT, padx=2)
        
        canvas_frame = tk.Frame(self.left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white', xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)
        
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 문서 관련 변수 초기화
        self.document = None
        self.current_page = 0
        self.search_results = []
        self.current_search_index = -1
        self.zoom_level = 1.0
        self.photo = None
        self.image_id = None
        
        # 마우스 (확대/축소 + 페이지 스크롤)
        self.canvas.bind("<MouseWheel>", self._on_document_mousewheel)
        self.canvas.bind("<Button-4>", self._on_document_mousewheel)
        self.canvas.bind("<Button-5>", self._on_document_mousewheel)
        
        self.canvas.bind("<Shift-MouseWheel>", self._on_page_scroll)
        self.canvas.bind("<Shift-Button-4>", self._on_page_scroll)
        self.canvas.bind("<Shift-Button-5>", self._on_page_scroll)
        
        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.focus_set() 
        
        self._show_document_initial_message()
        
        # 초기 로드 시 24759 문서 자동 로드
        self.top.after(500, self._auto_load_default_document)

    def _load_internal_document_with_conversion(self, doc_type):
        """문서 로드 시 TE 번호 변환"""
        # 19790 문서인 경우 TE 번호를 [XX.XX] 형식으로 변환
        if doc_type == "19790" and hasattr(self, 'te_number') and self.te_number:
            te_match = re.search(r'TE(\d+)\.(\d+)\.(\d+)', self.te_number)
            if te_match:
                converted_te = f"[{te_match.group(1)}.{te_match.group(2)}]"
                original_te = self.te_number
                self.te_number = converted_te
                
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"19790 문서용 TE 변환: {original_te} → {converted_te}")
                
                self._load_internal_document(doc_type)
                
                self.te_number = original_te
            else:
                self._load_internal_document(doc_type)
        else:
            self._load_internal_document(doc_type)

    def _load_internal_document(self, doc_type):
        """내부에 저장된 문서 로드"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            possible_folders = [
                os.path.join(current_dir, "additional_data", "pdf"),
                current_dir
            ]
            
            if doc_type == "19790":
                possible_filenames = [
                    "KS_X_ISO_IEC_19790_2015.pdf",
                    "KS_X_ISO_IEC 19790_2015.pdf"
                ]
                display_name = "KS X ISO/IEC 19790:2015"
            elif doc_type == "24759":
                possible_filenames = [
                    "KS_X_ISO_IEC_24759_2015.pdf",
                    "KS_X_ISO_IEC 24759_2015.pdf"
                ]
                display_name = "KS X ISO/IEC 24759:2015"
            else:
                messagebox.showerror("오류", "지원되지 않는 문서입니다.")
                return
            
            found_file = None
            for folder in possible_folders:
                for filename in possible_filenames:
                    file_path = os.path.join(folder, filename)
                    if os.path.exists(file_path):
                        found_file = file_path
                        break
                if found_file:
                    break
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"\n=== 문서 검색 디버그 ===")
                print(f"현재 디렉토리: {current_dir}")
                print(f"검색한 폴더들:")
                for folder in possible_folders:
                    print(f"  - {folder} (존재: {os.path.exists(folder)})")
                print(f"검색한 파일명들: {possible_filenames}")
                print(f"찾은 파일: {found_file}")
            
            if found_file:
                self._load_document_file(found_file, display_name)
            else:
                search_info = "검색한 위치:\n"
                for i, folder in enumerate(possible_folders):
                    search_info += f"{i+1}. {folder}\n"
                
                search_info += "\n검색한 파일명:\n"
                for i, filename in enumerate(possible_filenames):
                    search_info += f"{i+1}. {filename}\n"
                
                default_folder = possible_folders[0] 
                if not os.path.exists(default_folder):
                    os.makedirs(default_folder)
                
                messagebox.showwarning(
                    "문서 없음", 
                    f"문서를 찾을 수 없습니다.\n\n"
                    f"{search_info}\n"
                    f"권장 경로:\n{os.path.join(default_folder, possible_filenames[0])}"
                )
            
        except Exception as e:
            messagebox.showerror("오류", f"문서 로드 중 오류 발생: {str(e)}")
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                import traceback
                traceback.print_exc()

    def _get_document_info(self):
        """현재 사용 가능한 문서 정보 반환 - 여러 폴더 검색"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        possible_folders = [
            os.path.join(current_dir, "additional_data", "pdf"),
            current_dir 
        ]
        
        documents = {
            "19790": {
                "title": "KS X ISO/IEC 19790:2015",
                "description": "암호모듈에 대한 보안요구사항",
                "possible_filenames": [
                    "KS_X_ISO_IEC_19790_2015.pdf",
                    "KS_X_ISO_IEC 19790_2015.pdf"
                ]
            },
            "24759": {
                "title": "KS X ISO/IEC 24759:2015",
                "description": "암호모듈에 대한 시험요구사항",
                "possible_filenames": [
                    "KS_X_ISO_IEC_24759_2015.pdf",
                    "KS_X_ISO_IEC 24759_2015.pdf"
                ]
            }
        }
        
        available_docs = {}
        
        for doc_type, info in documents.items():
            found_file = None
            for folder in possible_folders:
                for filename in info["possible_filenames"]:
                    file_path = os.path.join(folder, filename)
                    if os.path.exists(file_path):
                        found_file = file_path
                        break
                if found_file:
                    break
            
            if found_file:
                available_docs[doc_type] = {
                    "title": info["title"],
                    "description": info["description"],
                    "path": found_file,
                    "file": os.path.basename(found_file)
                }
        
        return available_docs

    def _load_document_file(self, file_path, display_name=None):
        """문서를 로드하고 첫 페이지 표시"""
        try:
            self.document = fitz.open(file_path)
            self.current_page = 0
            self.search_results = []
            self.current_search_index = -1
            
            self._display_document_page(0)
            
            if display_name:
                doc_info = f"{display_name} (페이지 {self.current_page + 1}/{len(self.document)})"
            else:
                doc_name = os.path.basename(file_path)
                doc_info = f"{doc_name} (페이지 {self.current_page + 1}/{len(self.document)})"
            
            self.document_search_info_label.config(text=doc_info)
            
            self._update_page_navigation()
            
            # 문서 로드 완료 후 자동으로 TE 검색 실행 (기본 동작)
            if hasattr(self, 'te_number') and self.te_number:
                self.document_search_entry.delete(0, tk.END)
                self.document_search_entry.insert(0, self.te_number)
                self.document_search_entry.config(fg='black')
                self.top.after(500, self._search_in_document)
                
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"문서 로드 완료, TE 자동 검색 예약: {self.te_number}")
            else:
                self.document_search_entry.delete(0, tk.END)
                self.document_search_entry.insert(0, "TE 번호를 입력하세요")
                self.document_search_entry.config(fg='gray')
                self.document_search_entry.bind('<FocusIn>', self._clear_search_placeholder)
                
        except ImportError:
            messagebox.showerror("오류", "PyMuPDF 라이브러리가 필요합니다.\n'pip install PyMuPDF' 명령으로 설치하세요.")
        except Exception as e:
            messagebox.showerror("오류", f"문서 로드 실패: {str(e)}")

    def _display_document_page(self, page_num):
        """PDF 페이지를 캔버스에 표시"""
        try:
            if not self.document or page_num >= len(self.document) or page_num < 0:
                return
                
            page = self.document[page_num]
            
            zoom = self.zoom_level * 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("ppm")
            pil_image = Image.open(io.BytesIO(img_data))
            
            self.photo = ImageTk.PhotoImage(pil_image)
            
            self.canvas.delete("all")
            self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
            self.current_page = page_num
            
            self._update_page_navigation()
            
            self._highlight_search_results(page_num)
            
            if self.search_results:
                search_info = f" - '{self.search_results[0]['term']}' 검색결과: {self.current_search_index + 1}/{len(self.search_results)}"
            else:
                search_info = ""
            
            self.document_search_info_label.config(
                text=f"페이지 {page_num + 1}/{len(self.document)}{search_info}"
            )
            
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"문서 페이지 표시 오류: {str(e)}")

    def _update_page_navigation(self):
        """페이지 네비게이션 버튼 상태 업데이트"""
        if not self.document:
            # 문서가 없을 때 모든 버튼 비활성화
            self.prev_page_btn.config(state=tk.DISABLED)
            self.next_page_btn.config(state=tk.DISABLED)
            self.page_info_label.config(text="페이지: -/-")
            return
        
        total_pages = len(self.document)
        current_display = self.current_page + 1
        
        self.page_info_label.config(text=f"페이지: {current_display}/{total_pages}")
        
        self.prev_page_btn.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_page_btn.config(state=tk.NORMAL if self.current_page < total_pages - 1 else tk.DISABLED)

    def _go_to_prev_page(self):
        """이전 페이지로 이동"""
        if self.document and self.current_page > 0:
            self._display_document_page(self.current_page - 1)

    def _go_to_next_page(self):
        """다음 페이지로 이동"""
        if self.document and self.current_page < len(self.document) - 1:
            self._display_document_page(self.current_page + 1)

    def _clear_search_placeholder(self, event):
        """플레이스홀더 텍스트 제거"""
        if self.document_search_entry.get() == "TE 번호를 입력하세요":
            self.document_search_entry.delete(0, tk.END)
            self.document_search_entry.config(fg='black')

    def _search_in_document(self, event=None):
        """문서에서 텍스트 검색"""
        if not self.document:
            messagebox.showwarning("경고", "먼저 문서를 선택하세요.")
            return
            
        search_term = self.document_search_entry.get().strip()
        
        if not search_term or search_term == "TE 번호를 입력하세요":
            return
            
        self.document_search_entry.config(fg='black')
            
        try:
            self.search_results = []
            
            for page_num in range(len(self.document)):
                page = self.document[page_num]
                text_instances = page.search_for(search_term)
                
                for rect in text_instances:
                    self.search_results.append({
                        'page': page_num,
                        'rect': rect,
                        'term': search_term
                    })
            
            if self.search_results:
                self.current_search_index = 0
                self._update_search_navigation()
                self._go_to_search_result(0)
            else:
                self.document_search_info_label.config(text=f"'{search_term}' 검색 결과 없음")
                
        except Exception as e:
            messagebox.showerror("오류", f"검색 중 오류 발생: {str(e)}")

    def _auto_search_current_te(self):
        """현재 TE 번호로 자동 검색"""
        if hasattr(self, 'te_number') and self.te_number:
            self.document_search_entry.config(fg='black')
            
            self.document_search_entry.delete(0, tk.END)
            self.document_search_entry.insert(0, self.te_number)
            self._search_in_document()
        else:
            messagebox.showinfo("안내", "검색할 TE 번호가 없습니다.")

    def _highlight_search_results(self, page_num):
        """현재 페이지의 검색 결과를 하이라이트"""
        try:
            zoom = self.zoom_level * 1.5
            
            for i, result in enumerate(self.search_results):
                if result['page'] == page_num:
                    rect = result['rect']
                    
                    x1, y1, x2, y2 = rect.x0 * zoom, rect.y0 * zoom, rect.x1 * zoom, rect.y1 * zoom
                    
                    if i == self.current_search_index:
                        fill_color = "yellow"
                        outline_color = "red"
                        width = 3
                    else:
                        fill_color = "lightblue"
                        outline_color = "blue"
                        width = 2
                    
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill=fill_color,
                        outline=outline_color,
                        width=width,
                        stipple="gray25", 
                        tags="document_highlight"
                    )
                    
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"하이라이트 표시 오류: {str(e)}")

    def _prev_document_search_result(self):
        """이전 검색 결과로 이동"""
        if self.search_results and self.current_search_index > 0:
            self.current_search_index -= 1
            self._go_to_search_result(self.current_search_index)
            self._update_search_navigation()

    def _next_document_search_result(self):
        """다음 검색 결과로 이동"""
        if self.search_results and self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self._go_to_search_result(self.current_search_index)
            self._update_search_navigation()

    def _go_to_search_result(self, index):
        """특정 검색 결과로 이동"""
        if 0 <= index < len(self.search_results):
            result = self.search_results[index]
            page_num = result['page']
            
            self._display_document_page(page_num)
            
            self.top.after(100, lambda: self._scroll_to_search_result(result['rect']))

    def _scroll_to_search_result(self, rect):
        """검색 결과 위치로 캔버스 스크롤"""
        try:
            zoom = self.zoom_level * 1.5
            
            center_x = (rect.x0 + rect.x1) / 2 * zoom
            center_y = (rect.y0 + rect.y1) / 2 * zoom
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            image_width = self.photo.width()
            image_height = self.photo.height()
            
            if image_width > canvas_width:
                scroll_x = max(0, min(1, (center_x - canvas_width/2) / (image_width - canvas_width)))
                self.canvas.xview_moveto(scroll_x)
                
            if image_height > canvas_height:
                scroll_y = max(0, min(1, (center_y - canvas_height/2) / (image_height - canvas_height)))
                self.canvas.yview_moveto(scroll_y)
                
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"스크롤 이동 오류: {str(e)}")

    def _update_search_navigation(self):
        """검색 네비게이션 상태 업데이트"""
        if self.search_results:
            current = self.current_search_index + 1
            total = len(self.search_results)
            term = self.search_results[0]['term']
            
            self.document_search_info_label.config(text=f"'{term}' 검색결과: {current}/{total}")
        else:
            if self.document:
                total_pages = len(self.document)
                current_display = self.current_page + 1
                self.document_search_info_label.config(text=f"페이지 {current_display}/{total_pages}")

    def _on_page_scroll(self, event):
        """Shift + 마우스휠로 페이지 이동"""
        if not self.document:
            return
        
        if event.num == 4 or event.delta > 0:
            if self.current_page > 0:
                self._display_document_page(self.current_page - 1)
        elif event.num == 5 or event.delta < 0:
            if self.current_page < len(self.document) - 1:
                self._display_document_page(self.current_page + 1)

    def _on_key_press(self, event):
        """키보드 이벤트 처리 (페이지 이동)"""
        if not self.document:
            return
        
        if event.keysym == 'Left' or event.keysym == 'Page_Up':
            if self.current_page > 0:
                self._display_document_page(self.current_page - 1)
        elif event.keysym == 'Right' or event.keysym == 'Page_Down':
            if self.current_page < len(self.document) - 1:
                self._display_document_page(self.current_page + 1)
        elif event.keysym == 'Home':
            self._display_document_page(0)
        elif event.keysym == 'End':
            self._display_document_page(len(self.document) - 1)

    def _on_document_mousewheel(self, event):
        """PDF 뷰어 마우스 휠 이벤트 처리 (확대/축소)"""
        if not self.document:
            return
            
        old_zoom = self.zoom_level
        
        if event.num == 4 or event.delta > 0:  # 확대
            self.zoom_level *= 1.1
        elif event.num == 5 or event.delta < 0:  # 축소
            self.zoom_level *= 0.9
        
        self.zoom_level = max(0.5, min(3.0, self.zoom_level))
        
        if old_zoom != self.zoom_level:
            self._display_document_page(self.current_page)

    def _auto_load_default_document(self):
        """초기 로드 시 기본 문서(24759) 자동 로드"""
        try:
            # 24759 문서를 우선적으로 로드
            available_docs = self._get_document_info()
            
            if "24759" in available_docs:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print("초기 로드: 24759 문서 자동 선택")
                self._load_internal_document("24759")
            elif "19790" in available_docs:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print("초기 로드: 24759 없음, 19790 문서 선택")
                self._load_internal_document("19790")
            else:
                self.canvas.delete("all")
                self.canvas.create_text(
                    200, 150,
                    text="문서 파일을 찾을 수 없습니다.\n\n./additional_data/pdf/ 폴더에\nKS_X_ISO_IEC_24759_2015.pdf 또는\nKS_X_ISO_IEC_19790_2015.pdf\n파일을 저장해주세요.",
                    font=("Arial", 11),
                    fill="red",
                    justify=tk.CENTER,
                    width=350
                )
                    
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"초기 문서 로드 중 오류: {str(e)}")
            self.canvas.delete("all")
            self.canvas.create_text(
                200, 150,
                text=f"문서 로드 중 오류가 발생했습니다.\n\n{str(e)}",
                font=("Arial", 11),
                fill="red",
                justify=tk.CENTER,
                width=350
            )

    def _show_document_initial_message(self):
        """초기 안내 메시지 표시 - 간단한 로딩 메시지만"""
        self.canvas.delete("all")
        
        message = """보조 문서 뷰어

    문서를 로딩 중입니다...

    잠시만 기다려주세요."""
        
        self.canvas.create_text(
            200, 150,
            text=message,
            font=("Arial", 12),
            fill="#666666",
            justify=tk.CENTER,
            width=400
        )
    ### 여기까지

    def _create_text_view(self, text_content=None):
        """텍스트 내용 표시 위한 캔버스와 스크롤바 생성"""
        text_label = tk.Label(self.right_frame, text="내용", 
                            font=("Arial", 12, "bold"), bg="#ffe6e6")
        text_label.pack(fill=tk.X, padx=5, pady=(5, 0))

        canvas_frame = tk.Frame(self.right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.content_canvas = tk.Canvas(canvas_frame, bg="#f5f5f5", yscrollcommand=v_scrollbar.set)
        v_scrollbar.config(command=self.content_canvas.yview)

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 마우스 휠 바인딩 추가
        self.content_canvas.bind("<MouseWheel>", self._on_content_mousewheel)
        self.content_canvas.bind("<Button-4>", self._on_content_mousewheel)
        self.content_canvas.bind("<Button-5>", self._on_content_mousewheel)

        self.content_frame = tk.Frame(self.content_canvas)
        self.content_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.content_frame.bind("<Configure>", 
                            lambda e: self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all")))

        # 텍스트 내용 표시
        if text_content:
            self._display_text_content(text_content)
        elif self.validator and self.te_number:
            try:
                text_data, table_data, figure_data = self._safe_get_test_data()
                self._display_mixed_content(text_data, table_data, figure_data)
            except Exception as e:
                error_label = tk.Label(self.content_frame, text=f"데이터 로드 중 오류 발생: {str(e)}", 
                                    fg="red", font=("Arial", 10))
                error_label.pack(pady=10)

    def _on_content_mousewheel(self, event):
        """오른쪽 패널 캔버스의 마우스 휠 스크롤 처리"""
        if event.num == 4 or event.delta > 0:
            self.content_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.content_canvas.yview_scroll(1, "units")

    def _safe_get_test_data(self):
        """validator로부터 테스트 데이터를 안전하게 조회하여 반환"""
        try:
            return self._get_independent_test_data()
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"데이터 조회 중 오류: {str(e)}")
            return [f"데이터 조회 중 오류: {str(e)}", [], []]

    def _get_independent_test_data(self):
        """TE 번호에 해당하는 테스트 데이터를 독립적으로 조회하여 반환"""
        try:
            # validator의 메서드를 직접 호출하되, 결과를 즉시 복사
            result = self.validator._get_test_requirements_to_judgment(self.te_number)
            
            # 결과가 리스트가 아니면 기본값 반환
            if not isinstance(result, list) or len(result) != 3:
                return [f"{self.te_number}에 대한 데이터를 찾을 수 없습니다.", [], []]
            
            # 깊은 복사로 독립성 보장
            text_data = copy.deepcopy(result[0]) if result[0] else []
            table_data = copy.deepcopy(result[1]) if result[1] else []
            figure_data = copy.deepcopy(result[2]) if result[2] else []
            
            return [text_data, table_data, figure_data]
            
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"독립적 데이터 조회 중 오류: {str(e)}")
            return [f"{self.te_number} 데이터 조회 중 오류: {str(e)}", [], []]
        

    def _display_text_content(self, text_content):
        """기본 텍스트 내용을 표시"""
        text_widget = tk.Text(
            self.content_frame, 
            wrap=tk.WORD, 
            height=20, 
            bg="#f9f9f9", 
            font=("Arial", 10),
            relief=tk.SOLID,
            bd=1
        )
        text_widget.insert(tk.END, text_content)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    ##여기부터 added by yj
    def _is_text_block_content(self, text):
        """텍스트가 [텍스트 블록] 내용인지 확인 - 더 관대한 조건"""
        if not text:
            return False
        
        text_str = str(text).strip()
        
        if '[텍스트 블록]' in text_str:
            return True
        
        lines = text_str.split('\n')
        if len(lines) == 1 and len(text_str.strip()) < 20:
            exclude_patterns = [
                '시험결과보고서',
                'V3.00',
                '보고서',
                '문서',
                '페이지',
                '번호'
            ]
            if any(pattern == text_str.strip() for pattern in exclude_patterns):
                return True
        
        return False

    def _display_mixed_content(self, text_data, table_data, figure_data):
        """텍스트, 표 이미지, Figure 이미지를 JSON 검출 순서대로 표시"""
        try:
            import os
            
            if not isinstance(text_data, list):
                text_data = [text_data] if text_data else []
            if not isinstance(table_data, list):
                table_data = []
            if not isinstance(figure_data, list):
                figure_data = []
            
            if text_data and len(text_data) == 1 and isinstance(text_data[0], str):
                if any(keyword in text_data[0] for keyword in ["오류", "찾을 수 없습니다", "로드되지 않았습니다"]):
                    label = tk.Label(self.content_frame, text=text_data[0], font=("Arial", 10), fg="red")
                    label.pack(pady=5)
                    return
            
            text_content_by_page = {}
            
            for item in text_data:
                if isinstance(item, dict):
                    page_number = item.get('page_number', 'Unknown')
                    text_content = item.get('text', '')
                    
                    # 모든 페이지 텍스트 포함 (필터링 최소화)
                    if text_content is not None:
                        text_content = str(text_content)
                        if text_content.strip():
                            if page_number not in text_content_by_page:
                                text_content_by_page[page_number] = []
                            text_content_by_page[page_number].append(text_content)
                            
                elif isinstance(item, tuple) and len(item) >= 3:
                    section_type, page_number, content = item[0], item[1], item[2]
                    if section_type != "보완 이미지" and section_type != "텍스트 블록":
                        if page_number not in text_content_by_page:
                            text_content_by_page[page_number] = []
                        
                        if content is not None:
                            formatted_content = self._format_text_content(content, section_type)
                            if formatted_content and formatted_content.strip():
                                text_content_by_page[page_number].append(formatted_content)
            
            if text_content_by_page:
                page_numbers = sorted(text_content_by_page.keys())
                if len(page_numbers) == 1:
                    page_range = f"페이지 {page_numbers[0]}"
                else:
                    page_range = f"페이지 {page_numbers[0]}-{page_numbers[-1]}"
                
                header = tk.Label(
                    self.content_frame, 
                    text=f"페이지 내용 ({page_range})", 
                    font=("Arial", 11, "bold"), 
                    bg="#e6e6ff"
                )
                header.pack(fill=tk.X, pady=(10, 2))
                
                # 모든 페이지의 텍스트 내용을 페이지 순서대로 결합
                all_page_contents = []
                for page_number in page_numbers:
                    page_contents = text_content_by_page[page_number]
                    if page_contents:
                        page_text = "\n\n".join(page_contents)
                        cleaned_page_text = self._minimal_clean_text(page_text)
                        if cleaned_page_text:
                            all_page_contents.append(cleaned_page_text)
                
                if all_page_contents:
                    final_text = "\n\n\n".join(all_page_contents)
                    
                    text_lines = final_text.split('\n')
                    widget_height = min(25, max(10, len(text_lines)))
                    
                    text_widget = tk.Text(
                        self.content_frame, 
                        wrap=tk.WORD, 
                        height=widget_height, 
                        bg="#f9f9f9", 
                        font=("Arial", 10),
                        relief=tk.SOLID,
                        bd=1
                    )
                    text_widget.insert(tk.END, final_text)
                    text_widget.config(state=tk.DISABLED)
                    text_widget.pack(fill=tk.X, padx=5, pady=2)

            if not hasattr(self, 'zoom_factor'):
                self.zoom_factor = 1.0

            self._display_unified_content_by_json_order(table_data, figure_data)
                
            if not text_content_by_page and not table_data and not figure_data:
                no_content_label = tk.Label(
                    self.content_frame,
                    text=f"{getattr(self, 'te_number', 'TE')}에 대한 내용을 찾을 수 없습니다.",
                    font=("Arial", 12),
                    fg="#666666"
                )
                no_content_label.pack(pady=20)
                
        except Exception as e:
            error_label = tk.Label(
                self.content_frame,
                text=f"내용 표시 중 오류 발생: {str(e)}",
                font=("Arial", 10),
                fg="red"
            )
            error_label.pack(pady=10)
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"_display_mixed_content 오류: {str(e)}")
                import traceback
                traceback.print_exc()

    def _minimal_clean_text(self, text):
        """최소한의 텍스트 정리만 수행 - 모든 내용 보존"""
        if text is None:
            return ""
        
        text = str(text)
        
        import re
        
        text = re.sub(r'\[페이지\s*텍스트\]\s*:\s*', '', text)
        text = re.sub(r'\[페이지\s*출력\]\s*:\s*', '', text)
        text = re.sub(r'\[텍스트\s*블록\]\s*:\s*', '', text)
        
        text = text.strip()
        
        text = re.sub(r'\n\s*\n\s*\n\s*\n+', '\n\n', text)
        
        return text

    def _format_text_content(self, content, section_type):
        """텍스트 내용 포맷팅 - 모든 내용 보존"""
        if content is None:
            return ""
        
        if isinstance(content, str):
            return content
        elif isinstance(content, dict) and 'text' in content:
            text_value = content['text']
            if text_value is None:
                return ""
            return str(text_value)
        elif isinstance(content, list):
            filtered_items = [str(item) for item in content if item is not None]
            return ' '.join(filtered_items)
        else:
            return str(content)
    ##여기까지

    def _display_mixed_content2(self, text_data, table_data, figure_data):
        """텍스트, 표 이미지, Figure 이미지를 JSON 검출 순서대로 표시"""
        try:
            # 데이터 유효성 검사
            if not isinstance(text_data, list):
                text_data = [text_data] if text_data else []
            if not isinstance(table_data, list):
                table_data = []
            if not isinstance(figure_data, list):
                figure_data = []
            
            # 텍스트가 오류 메시지인 경우 처리
            if text_data and len(text_data) == 1 and isinstance(text_data[0], str):
                if any(keyword in text_data[0] for keyword in ["오류", "찾을 수 없습니다", "로드되지 않았습니다"]):
                    label = tk.Label(self.content_frame, text=text_data[0], font=("Arial", 10), fg="red")
                    label.pack(pady=5)
                    return
            
            # 텍스트 섹션 - 안전한 처리
            combined_text_by_page = {}
            
            for item in text_data:
                if isinstance(item, tuple) and len(item) >= 3:
                    section_type, page_number, content = item[0], item[1], item[2]
                    if section_type != "보완 이미지":
                        if page_number not in combined_text_by_page:
                            combined_text_by_page[page_number] = []
                        
                        formatted_content = self._format_text_content(content, section_type)
                        if formatted_content.strip():
                            combined_text_by_page[page_number].append(formatted_content)
            
            # 페이지별로 합쳐진 텍스트 표시
            for page_number, content_list in combined_text_by_page.items():
                if content_list:
                    header = tk.Label(
                        self.content_frame, 
                        text=f"텍스트 내용 (페이지 {page_number})", 
                        font=("Arial", 11, "bold"), 
                        bg="#e6e6ff"
                    )
                    header.pack(fill=tk.X, pady=(10, 2))
                    
                    combined_content = "\n\n".join(content_list)
                    
                    text_widget = tk.Text(
                        self.content_frame, 
                        wrap=tk.WORD, 
                        height=8, 
                        bg="#f9f9f9", 
                        font=("Arial", 10),
                        relief=tk.SOLID,
                        bd=1
                    )
                    text_widget.insert(tk.END, combined_content)
                    text_widget.config(state=tk.DISABLED)
                    text_widget.pack(fill=tk.X, padx=5, pady=2)

            # 확대/축소 비율 초기값
            if not hasattr(self, 'zoom_factor'):
                self.zoom_factor = 1.0

            # 테이블과 Figure를 JSON 검출 순서대로 통합 처리
            self._display_unified_content_by_json_order(table_data, figure_data)
                
            # 내용이 없는 경우 안내 메시지
            if not combined_text_by_page and not table_data and not figure_data:
                no_content_label = tk.Label(
                    self.content_frame,
                    text=f"{getattr(self, 'te_number', 'TE')}에 대한 내용을 찾을 수 없습니다.",
                    font=("Arial", 12),
                    fg="#666666"
                )
                no_content_label.pack(pady=20)
                
        except Exception as e:
            error_label = tk.Label(
                self.content_frame,
                text=f"내용 표시 중 오류 발생: {str(e)}",
                font=("Arial", 10),
                fg="red"
            )
            error_label.pack(pady=10)
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"_display_mixed_content 오류: {str(e)}")
                import traceback
                traceback.print_exc()

    def _format_text_content(self, content, section_type):
        """텍스트 콘텐츠 포맷팅"""
        return f"[{section_type}]:\n{content}"

    def _display_unified_content_by_json_order(self, table_data, figure_data):
        """테이블과 Figure를 JSON 검출 순서대로 통합하여 표시 (캡션 기반 매칭 개선)"""
        try:
            # 1. 모든 콘텐츠를 페이지 순서와 문서 내 위치로 통합
            unified_content = []
            
            # 테이블 데이터 추가 (이미지 필요성 사전 판단)
            for idx, table in enumerate(table_data):
                if isinstance(table, dict):
                    page_num = table.get('page', 0)
                    if isinstance(page_num, str):
                        try:
                            page_num = int(re.findall(r'\d+', page_num)[0]) if re.findall(r'\d+', page_num) else 0
                        except:
                            page_num = 0
                    
                    # 이미지 필요성 판단
                    needs_image = self._table_needs_image(table)
                    
                    unified_content.append({
                        'type': 'table',
                        'data': table,
                        'original_index': idx,
                        'page_num': page_num,
                        'caption': table.get('caption', ''),
                        'needs_image': needs_image,
                        'sort_key': f"{page_num:03d}_table_{idx:03d}"
                    })
            
            # Figure 데이터 추가
            for idx, figure in enumerate(figure_data):
                if isinstance(figure, dict):
                    page_num = figure.get('page', 0)
                    if isinstance(page_num, str):
                        try:
                            page_num = int(re.findall(r'\d+', page_num)[0]) if re.findall(r'\d+', page_num) else 0
                        except:
                            page_num = 0
                    
                    unified_content.append({
                        'type': 'figure',
                        'data': figure,
                        'original_index': idx,
                        'page_num': page_num,
                        'caption': figure.get('caption', ''),
                        'sort_key': f"{page_num:03d}_figure_{idx:03d}"
                    })
            
            # 2. 페이지 순서와 문서 내 위치로 정렬
            unified_content.sort(key=lambda x: x['sort_key'])
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"\n=== 통합 콘텐츠 정렬 결과 ===")
                for i, content in enumerate(unified_content):
                    needs_img = content.get('needs_image', 'N/A') if content['type'] == 'table' else 'N/A'
                    print(f"{i+1}. {content['type']} - 페이지 {content['page_num']}: {content['caption'][:50]}... (이미지 필요: {needs_img})")
            
            # 3. 테이블 이미지 파일을 캡션 기반으로 매칭
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted_table_images")
            image_assignments = self._smart_match_table_images(unified_content, output_dir)
            
            # 4. 순서대로 콘텐츠 표시
            for content in unified_content:
                if content['type'] == 'table':
                    self._display_single_table_with_smart_matching(
                        content['data'], 
                        content['original_index'], 
                        image_assignments
                    )
                    
                elif content['type'] == 'figure':
                    self._display_single_figure_ordered(content['data'], content['original_index'])
                    
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"통합 콘텐츠 표시 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()
            
            error_label = tk.Label(
                self.content_frame,
                text=f"콘텐츠 표시 중 오류 발생: {str(e)}",
                font=("Arial", 10),
                fg="red"
            )
            error_label.pack(pady=10)

    def _display_single_table_with_smart_matching(self, table, original_idx, image_assignments):
        """스마트 매칭 결과를 사용하여 테이블과 해당 이미지를 표시"""
        # 헤더 프레임
        header_frame = tk.Frame(self.content_frame)
        header_frame.pack(fill=tk.X, pady=(15, 2))
        
        # 테이블 제목
        table_caption = table.get('caption', '').strip()
        page_num = table.get('page', 'Unknown')
        
        header = tk.Label(
            header_frame, 
            text=f"표 {original_idx + 1} (페이지 {page_num})", 
            font=("Arial", 11, "bold"), 
            bg="#e6ffe6"
        )
        header.pack(side=tk.LEFT)
        
        # 줌 버튼들 추가
        zoom_in_btn = tk.Button(
            header_frame, 
            text="+", 
            command=lambda: self._zoom_in_table(table, original_idx), 
            width=2, 
            bg="#e6f2ff"
        )
        zoom_in_btn.pack(side=tk.RIGHT, padx=2)
        
        zoom_out_btn = tk.Button(
            header_frame, 
            text="-", 
            command=lambda: self._zoom_out_table(table, original_idx), 
            width=2, 
            bg="#e6f2ff"
        )
        zoom_out_btn.pack(side=tk.RIGHT, padx=2)
        
        # 테이블 캡션 표시
        if table_caption:
            caption_label = tk.Label(
                self.content_frame, 
                text=f"캡션: {table_caption}", 
                font=("Arial", 9, "italic"),
                fg="#666666",
                bg="#f0f0f0",
                wraplength=400,
                justify=tk.LEFT
            )
            caption_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 할당된 이미지 표시
        assigned_image_path = image_assignments.get(original_idx)
        
        if assigned_image_path:
            # 이미지가 할당된 경우
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                filename = os.path.basename(assigned_image_path)
                print(f"테이블 {original_idx + 1} '{table_caption[:30]}...' -> {filename}")
            
            self._display_table_image_from_path(assigned_image_path, os.path.basename(assigned_image_path))
            
            # 디버그 정보 표시
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                debug_label = tk.Label(
                    self.content_frame,
                    text=f"[DEBUG] 테이블 {original_idx + 1} -> 파일: {os.path.basename(assigned_image_path)}",
                    font=("Arial", 8, "italic"),
                    fg="#888888",
                    bg="#f9f9f9"
                )
                debug_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        else:
            # 이미지가 할당되지 않은 경우
            no_image_label = tk.Label(
                self.content_frame, 
                text=f"테이블 내용 (이미지 없음)", 
                font=("Arial", 10, "italic"),
                fg="#888888",
                bg="#f9f9f9"
            )
            no_image_label.pack(pady=5, padx=10)
            
            # 간단한 테이블 텍스트 표시
            self._display_table_as_text(table)
            
            # 디버그 정보 표시
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                debug_label = tk.Label(
                    self.content_frame,
                    text=f"[DEBUG] 테이블 {original_idx + 1} '{table_caption[:30]}...' -> 이미지 없음",
                    font=("Arial", 8, "italic"),
                    fg="#666666",
                    bg="#f0f0f0"
                )
                debug_label.pack(fill=tk.X, padx=5, pady=(0, 5))

    def _smart_match_table_images(self, unified_content, output_dir):
        """캡션, 챕터 번호, 파일명 패턴을 기반으로 테이블 이미지를 스마트 매칭하여 할당"""
        if not os.path.exists(output_dir):
            return {}

        try:
            all_files = [f for f in os.listdir(output_dir) 
                        if any(f.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif'])]
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"폴더 읽기 오류: {output_dir}, 오류: {str(e)}")
            return {}

        # 초기화: 매 호출마다 새로운 파일 목록 사용
        table_files = []
        chapter_files = []
        caption_files = []
        used_files = set()

        for file_name in all_files:
            # Table_X-Y 패턴
            match = re.match(r'^Table_(\d+)-(\d+)', file_name)
            if match:
                page_num = int(match.group(1))
                table_num = int(match.group(2))
                table_files.append({
                    'filename': file_name,
                    'page_num': page_num,
                    'table_num': table_num,
                    'full_path': os.path.join(output_dir, file_name)
                })
            
            # 챕터 번호 기반 파일
            match = re.match(r'^(\d+)_(\d+)_(\d+)_시험_요구사항', file_name)
            if match:
                chapter_num = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
                chapter_files.append({
                    'filename': file_name,
                    'chapter_num': chapter_num,
                    'full_path': os.path.join(output_dir, file_name)
                })
            
            # 캡션 기반 파일
            chapter_match = re.search(r'(\d+_\d+_\d+)_시험_요구사항', file_name)
            if chapter_match:
                chapter_num = chapter_match.group(1).replace('_', '.')
                caption_files.append({
                    'filename': file_name,
                    'chapter_num': chapter_num,
                    'full_path': os.path.join(output_dir, file_name)
                })

        table_files.sort(key=lambda x: (x['page_num'], x['table_num']))

        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"\n=== 스마트 테이블 이미지 매칭 시작 (TE: {self.te_number}) ===")
            print(f"Table_X-Y 파일들 ({len(table_files)}개): {[tf['filename'] for tf in table_files]}")
            print(f"챕터 번호 기반 파일들 ({len(chapter_files)}개): {[cf['filename'] for cf in chapter_files]}")
            print(f"캡션 기반 파일들 ({len(caption_files)}개): {[cf['filename'] for cf in caption_files]}")

        # 이미지가 필요한 테이블들
        tables_needing_images = [content for content in unified_content 
                                if content['type'] == 'table' and content.get('needs_image', False)]

        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"\n이미지가 필요한 테이블들 ({len(tables_needing_images)}개):")
            for i, table in enumerate(tables_needing_images):
                print(f"  {i+1}. '{table['caption'][:50]}...'")

        image_assignments = {}

        # 1단계: 캡션 기반 매칭 (챕터 번호 + 시험요구사항)
        for table_content in tables_needing_images:
            table = table_content['data']
            table_idx = table_content['original_index']
            caption = table.get('caption', '').strip()

            chapter_pattern = r'\d+\.\d+\.\d+'
            chapter_match = re.search(chapter_pattern, caption)
            chapter_num = chapter_match.group() if chapter_match else None

            caption_filename = caption.replace(' ', '_')
            for cf in caption_files:
                if cf['filename'] in used_files:
                    continue
                if chapter_num and cf['chapter_num'] == chapter_num and cf['filename'].startswith(caption_filename):
                    image_assignments[table_idx] = cf['full_path']
                    used_files.add(cf['filename'])
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"✅ 캡션 매칭: '{caption}' -> {cf['filename']} (챕터: {chapter_num})")
                    break

        # 2단계: 챕터 번호 기반 매칭
        for table_content in tables_needing_images:
            table = table_content['data']
            table_idx = table_content['original_index']
            caption = table.get('caption', '').strip()

            if table_idx in image_assignments:
                continue

            chapter_pattern = r'\d+\.\d+\.\d+'
            chapter_match = re.search(chapter_pattern, caption)
            chapter_num = chapter_match.group() if chapter_match else None

            for cf in chapter_files:
                if cf['filename'] in used_files:
                    continue
                if chapter_num and cf['chapter_num'] == chapter_num:
                    image_assignments[table_idx] = cf['full_path']
                    used_files.add(cf['filename'])
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"✅ 챕터 매칭: '{caption}' -> {cf['filename']} (챕터: {chapter_num})")
                    break

        # 3단계: 캡션 기반 Table_X-Y 매칭
        for table_content in tables_needing_images:
            table = table_content['data']
            table_idx = table_content['original_index']
            caption = table.get('caption', '').strip()

            if table_idx in image_assignments:
                continue

            best_match = None
            best_score = 0

            for tf in table_files:
                if tf['filename'] in used_files:
                    continue
                score = self._calculate_caption_match_score(caption, tf['filename'])
                if score > best_score:
                    best_score = score
                    best_match = tf

            if best_match and best_score > 20:
                image_assignments[table_idx] = best_match['full_path']
                used_files.add(best_match['filename'])
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"✅ 캡션 매칭 (Table_X-Y): '{caption}' -> {best_match['filename']} (점수: {best_score})")

        # 4단계: 남은 테이블과 이미지를 순서대로 매칭
        remaining_tables = [t for t in tables_needing_images if t['original_index'] not in image_assignments]
        remaining_table_files = [tf for tf in table_files if tf['filename'] not in used_files]
        remaining_chapter_files = [cf for cf in chapter_files if cf['filename'] not in used_files]
        remaining_caption_files = [cf for cf in caption_files if cf['filename'] not in used_files]

        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"\n순서 매칭 단계: 남은 테이블 {len(remaining_tables)}개, 남은 Table 파일 {len(remaining_table_files)}개, 남은 챕터 파일 {len(remaining_chapter_files)}개, 남은 캡션 파일 {len(remaining_caption_files)}개")

        for i, table_content in enumerate(remaining_tables):
            table_idx = table_content['original_index']
            if i < len(remaining_caption_files):
                matched_file = remaining_caption_files[i]
                image_assignments[table_idx] = matched_file['full_path']
                used_files.add(matched_file['filename'])
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    caption = table_content['caption'][:30]
                    print(f"✅ 순서 매칭 (캡션): '{caption}...' -> {matched_file['filename']}")
            elif i < len(remaining_chapter_files):
                matched_file = remaining_chapter_files[i]
                image_assignments[table_idx] = matched_file['full_path']
                used_files.add(matched_file['filename'])
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    caption = table_content['caption'][:30]
                    print(f"✅ 순서 매칭 (챕터): '{caption}...' -> {matched_file['filename']}")
            elif i < len(remaining_table_files):
                matched_file = remaining_table_files[i]
                image_assignments[table_idx] = matched_file['full_path']
                used_files.add(matched_file['filename'])
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    caption = table_content['caption'][:30]
                    print(f"✅ 순서 매칭 (Table): '{caption}...' -> {matched_file['filename']}")

        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"\n=== 최종 매칭 결과 (TE: {self.te_number}) ===")
            for idx, path in image_assignments.items():
                print(f"테이블 {idx + 1} -> {os.path.basename(path)}")
            print(f"총 {len(image_assignments)}개 할당")

        return image_assignments

    def _calculate_caption_match_score(self, caption, filename):
        """캡션과 파일명 간의 매칭 점수를 계산하여 반환"""
        score = 0
        caption_lower = caption.lower()
        filename_lower = filename.lower()
        
        # 1. 챕터 번호 매칭 (최고 우선순위)
        chapter_pattern_caption = re.findall(r'\d+\.\d+\.\d+', caption_lower)
        chapter_pattern_filename = re.findall(r'\d+_\d+_\d+', filename_lower)
        
        if chapter_pattern_caption and chapter_pattern_filename:
            caption_chapter = chapter_pattern_caption[0].replace('.', '_')
            filename_chapter = chapter_pattern_filename[0]
            
            if caption_chapter == filename_chapter:
                score += 100  # 완전 일치
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"    챕터 완전 일치: {caption_chapter} == {filename_chapter} (+100)")
            elif caption_chapter[:3] == filename_chapter[:3]:  # 앞 2자리 일치 (2_3)
                score += 80
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"    챕터 부분 일치: {caption_chapter[:3]} == {filename_chapter[:3]} (+80)")
        
        # 2. 특별 키워드 매칭
        special_keywords = {
            '시험결과판정근거': ['시험결과', '판정', '근거'],
            '판정근거': ['판정', '근거'],
            '시험결과': ['시험결과', 'result'],
            '표제목': ['표', '제목', 'table'],
            '암호모듈': ['암호모듈', 'module'],
            '구성요소': ['구성요소', 'component'],
            '해시값': ['해시', 'hash'],
            '시험요구사항': ['시험요구사항', '요구사항']
        }
        
        for main_keyword, variants in special_keywords.items():
            if main_keyword in caption_lower:
                for variant in variants:
                    if variant in filename_lower:
                        score += 60
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"    특별 키워드 매칭: {main_keyword} -> {variant} (+60)")
                        break
                break
        
        # 3. Table X-Y 패턴 매칭
        table_pattern_caption = re.search(r'table\s+(\d+)-(\d+)', caption_lower)
        table_pattern_filename = re.search(r'table_(\d+)-(\d+)', filename_lower)
        
        if table_pattern_caption and table_pattern_filename:
            caption_nums = f"{table_pattern_caption.group(1)}-{table_pattern_caption.group(2)}"
            filename_nums = f"{table_pattern_filename.group(1)}-{table_pattern_filename.group(2)}"
            
            if caption_nums == filename_nums:
                score += 90
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"    Table 번호 일치: {caption_nums} == {filename_nums} (+90)")
        
        # 4. 일반 키워드 매칭
        common_keywords = ['표', 'table', '제목', 'title', '시험', 'test', '결과', 'result']
        matched_keywords = 0
        
        for keyword in common_keywords:
            if keyword in caption_lower and keyword in filename_lower:
                matched_keywords += 1
        
        score += matched_keywords * 10
        
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode and matched_keywords > 0:
            print(f"    일반 키워드 매칭: {matched_keywords}개 (+{matched_keywords * 10})")
        
        return score

    def _table_needs_image(self, table):
        """테이블이 이미지를 필요로 하는지 캡션과 셀 데이터를 분석하여 판단"""
        caption = table.get('caption', '').strip().lower()
        cells = table.get('cells', [])

        # 1. 명확히 이미지가 없어야 하는 테이블들
        no_image_keywords = [
            '확인사항', '시험항목', '시험 항목',
            '주요 확인사항', '확인방법'
        ]

        for keyword in no_image_keywords:
            if keyword in caption:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"  이미지 불필요: '{caption}' - 키워드: {keyword}")
                return False

        # 2. 시험요구사항 포함 시 이미지 필요
        if '시험요구사항' in caption or '요구사항' in caption:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"  이미지 필요: '{caption}' - 시험요구사항 포함")
            return True

        # 3. 챕터 번호 포함 시 이미지 필요
        chapter_pattern = r'\d+\.\d+\.\d+'
        if re.search(chapter_pattern, caption):
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"  이미지 필요: '{caption}' - 챕터 번호 포함")
            return True

        for cell in cells:
            cell_text = str(cell.get('text', '')).lower()
            if re.search(chapter_pattern, cell_text):
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"  이미지 필요: '{caption}' - 셀에 챕터 번호 포함")
                return True

        # 4. Table X-Y 형식의 캡션은 이미지 필요
        if re.match(r'^table\s+\d+-\d+', caption):
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"  이미지 필요: '{caption}' - Table X-Y 형식")
            return True

        # 5. 특별한 키워드가 포함된 캡션
        image_keywords = [
            '시험결과판정근거', '판정근거', '시험결과', '표제목',
            '암호모듈', '구성요소', '해시값'
        ]

        for keyword in image_keywords:
            if keyword in caption:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"  이미지 필요: '{caption}' - 특별 키워드: {keyword}")
                return True

        # 6. 복잡한 테이블 (셀이 많은 경우)
        if len(cells) >= 8:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"  이미지 필요: '{caption}' - 복잡한 테이블 (셀 {len(cells)}개)")
            return True

        # 7. 기본값: 중간 정도 복잡도는 이미지 있음으로 간주
        if len(cells) >= 5:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"  이미지 필요: '{caption}' - 중간 복잡도 (셀 {len(cells)}개)")
            return True

        # 8. 그 외는 이미지 없음
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"  이미지 불필요: '{caption}' - 기본값 (셀 {len(cells)}개)")
        return False

    def _display_table_image_from_path(self, image_path, filename):
        """지정된 경로의 테이블 이미지를 확대/축소 비율을 적용하여 표시"""
        try:
            if os.path.exists(image_path):
                image = Image.open(image_path)
                
                # 파일명에서 테이블 인덱스 추출
                table_idx = self._extract_table_index_from_filename(filename)
                
                # 확대/축소 비율 적용
                base_zoom = getattr(self, 'zoom_factor', 1.0)
                table_zoom = self.table_zoom_factors.get(table_idx, 1.0) if hasattr(self, 'table_zoom_factors') else 1.0
                
                # 최종 스케일 팩터 계산
                scale_factor = 0.3 * base_zoom * table_zoom
                new_width = int(image.width * scale_factor)
                new_height = int(image.height * scale_factor)
                resized_image = image.resize((new_width, new_height), Image.LANCZOS)
                
                photo = ImageTk.PhotoImage(resized_image)
                image_label = tk.Label(self.content_frame, image=photo, bg="white", relief=tk.SOLID, bd=1)
                image_label.image = photo  # 참조 유지
                image_label.pack(pady=5, padx=10)
                
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"✅ 테이블 이미지 표시: {filename} (확대비율: {table_zoom:.2f}x)")
            else:
                raise FileNotFoundError(f"파일이 존재하지 않음: {image_path}")
                
        except Exception as e:
            error_label = tk.Label(self.content_frame, text=f"이미지 로드 실패: {filename}", 
                                fg="red", font=("Arial", 9))
            error_label.pack(pady=2)
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"❌ 테이블 이미지 로드 실패: {filename}, 오류: {str(e)}")

    def _extract_table_index_from_filename(self, filename):
        """파일명에서 테이블 인덱스 추출"""
        import re
        # Table_X-Y 패턴에서 Y값을 추출하여 인덱스로 사용
        match = re.search(r'Table_(\d+)-(\d+)', filename)
        if match:
            return int(match.group(2)) - 1  # 0-based index로 변환
        return 0  # 기본값

    def _zoom_in_table(self, table, table_idx):
        """테이블 이미지 확대"""
        if not hasattr(self, 'table_zoom_factors'):
            self.table_zoom_factors = {}
        
        current_zoom = self.table_zoom_factors.get(table_idx, 1.0)
        self.table_zoom_factors[table_idx] = min(2.0, current_zoom + 0.2)
        self._refresh_content()

    def _zoom_out_table(self, table, table_idx):
        """테이블 이미지 축소"""
        if not hasattr(self, 'table_zoom_factors'):
            self.table_zoom_factors = {}
        
        current_zoom = self.table_zoom_factors.get(table_idx, 1.0)
        self.table_zoom_factors[table_idx] = max(0.5, current_zoom - 0.2)
        self._refresh_content()

    def _display_single_figure_ordered(self, figure, original_idx):
        """JSON 검출 순서에 따라 Figure와 해당 이미지를 표시 (로컬 파일 우선)"""
        header_frame = tk.Frame(self.content_frame)
        header_frame.pack(fill=tk.X, pady=(15, 2))
        
        header = tk.Label(
            header_frame, 
            text=f"Figure {original_idx + 1} (페이지 {figure.get('page', 'Unknown')})", 
            font=("Arial", 11, "bold"), 
            bg="#ffe6e6"
        )
        header.pack(side=tk.LEFT)
        
        # 줌 버튼들 추가
        zoom_in_btn = tk.Button(
            header_frame, 
            text="+", 
            command=lambda: self._zoom_in_figure(figure, original_idx), 
            width=2, 
            bg="#e6f2ff"
        )
        zoom_in_btn.pack(side=tk.RIGHT, padx=2)
        
        zoom_out_btn = tk.Button(
            header_frame, 
            text="-", 
            command=lambda: self._zoom_out_figure(figure, original_idx), 
            width=2, 
            bg="#e6f2ff"
        )
        zoom_out_btn.pack(side=tk.RIGHT, padx=2)
        
        # Figure 캡션 표시
        if figure.get('caption'):
            caption_label = tk.Label(
                self.content_frame, 
                text=f"캡션: {figure['caption']}", 
                font=("Arial", 9, "italic"),
                fg="#666666",
                bg="#f0f0f0",
                wraplength=400,
                justify=tk.LEFT
            )
            caption_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Figure 이미지 로드 및 표시
        self._display_single_figure_image(figure)

    def _display_single_figure_image(self, figure):
        """
        개별 Figure 이미지를 확대/축소 비율을 적용하여 표시 (로컬 파일 우선)
        """
        image_loaded = False
        
        # Figure 인덱스 추출
        figure_idx = figure.get('original_index', 0)
        
        # 1. 로컬 폴더에서 Figure 이미지 파일 검색 시도
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"Figure {figure_idx + 1} 로컬 이미지 검색 시작...")
        
        local_image_path = self._find_local_figure_image(figure, figure_idx)
        
        if local_image_path:
            try:
                # 로컬 파일에서 이미지 로드
                image = Image.open(local_image_path)
                
                # 확대/축소 비율 적용
                base_zoom = getattr(self, 'zoom_factor', 1.0)
                figure_zoom = self.figure_zoom_factors.get(figure_idx, 1.0) if hasattr(self, 'figure_zoom_factors') else 1.0
                scale_factor = 0.7 * base_zoom * figure_zoom
                
                new_width = int(image.width * scale_factor)
                new_height = int(image.height * scale_factor)
                enlarged_image = image.resize((new_width, new_height), Image.LANCZOS)
                
                photo = ImageTk.PhotoImage(enlarged_image)
                image_label = tk.Label(self.content_frame, image=photo, bg="white", relief=tk.SOLID, bd=1)
                image_label.image = photo
                image_label.pack(pady=5, padx=10)
                
                image_loaded = True
                
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"✅ Figure 로컬 이미지 표시 성공: {os.path.basename(local_image_path)} (확대비율: {figure_zoom:.2f}x)")
                    
            except Exception as e:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"❌ Figure 로컬 이미지 로드 실패: {local_image_path}, 오류: {str(e)}")
        
        # 2. 로컬 이미지가 없으면 JSON base64 데이터 사용 (fallback)
        if not image_loaded and figure.get('base64'):
            try:
                base64_data = figure['base64']
                if base64_data.startswith('data:image'):
                    base64_parts = base64_data.split(',', 1)
                    if len(base64_parts) > 1:
                        base64_data = base64_parts[1]
                
                image_bytes = base64.b64decode(base64_data)
                image = Image.open(BytesIO(image_bytes))
                
                # 확대/축소 비율 적용
                base_zoom = getattr(self, 'zoom_factor', 1.0)
                figure_zoom = self.figure_zoom_factors.get(figure_idx, 1.0) if hasattr(self, 'figure_zoom_factors') else 1.0
                scale_factor = 0.7 * base_zoom * figure_zoom
                
                new_width = int(image.width * scale_factor)
                new_height = int(image.height * scale_factor)
                enlarged_image = image.resize((new_width, new_height), Image.LANCZOS)
                
                photo = ImageTk.PhotoImage(enlarged_image)
                image_label = tk.Label(self.content_frame, image=photo, bg="white", relief=tk.SOLID, bd=1)
                image_label.image = photo
                image_label.pack(pady=5, padx=10)
                
                image_loaded = True
                
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"✅ Figure base64 이미지 표시 (fallback) (확대비율: {figure_zoom:.2f}x)")
                    
            except Exception as e:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"❌ Figure base64 이미지 로드 실패: {str(e)}")
        
        # 3. 이미지 로드 실패 시 메시지 표시
        if not image_loaded:
            no_image_label = tk.Label(
                self.content_frame, 
                text="Figure 이미지를 찾을 수 없습니다.",
                font=("Arial", 10, "italic"),
                fg="#888888",
                bg="#f9f9f9"
            )
            no_image_label.pack(pady=5, padx=10)
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"❌ Figure 이미지 표시 실패: 로컬 파일과 base64 데이터 모두 없음")

    def _find_local_figure_image(self, figure, figure_idx):
        """
        로컬 extracted_images 폴더에서 Figure 이미지 파일을 검색
        
        Args:
            figure (dict): Figure 데이터
            figure_idx (int): Figure 인덱스
            
        Returns:
            str: 파일 경로 또는 None
        """
        try:
            # extracted_images 폴더 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_folder = os.path.join(current_dir, "extracted_images")
            
            if not os.path.exists(image_folder):
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"extracted_images 폴더가 존재하지 않음: {image_folder}")
                return None
            
            # 지원되는 이미지 확장자
            supported_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
            
            # 폴더 내 파일 목록 가져오기
            try:
                all_files = [f for f in os.listdir(image_folder) 
                           if any(f.lower().endswith(ext) for ext in supported_extensions)]
            except Exception as e:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"폴더 읽기 오류: {image_folder}, 오류: {str(e)}")
                return None
            
            if not all_files:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"extracted_images 폴더에 이미지 파일이 없음: {image_folder}")
                return None
            
            # Figure 정보 추출
            caption = figure.get('caption', '').strip()
            page_num = figure.get('page', 'Unknown')
            te_number = getattr(self, 'te_number', '')
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"Figure 검색 정보: 캡션='{caption}', 페이지={page_num}, TE={te_number}")
                print(f"사용 가능한 파일: {all_files[:5]}...")  # 처음 5개만 표시
            
            # 1단계: 캡션 기반 정확한 매칭
            best_match = None
            best_score = 0
            
            for file_name in all_files:
                score = self._calculate_figure_match_score(file_name, caption, page_num, te_number, figure_idx)
                
                if score > best_score:
                    best_score = score
                    best_match = file_name
                    
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode and score > 0:
                    print(f"  파일 매칭: {file_name} -> 점수: {score}")
            
            if best_match and best_score > 30:  # 임계값 설정
                matched_path = os.path.join(image_folder, best_match)
                if os.path.exists(matched_path):
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"✅ Figure 이미지 매칭 성공: {best_match} (점수: {best_score})")
                    return matched_path
            
            # 2단계: Figure 패턴 기반 순서 매칭
            figure_files = [f for f in all_files if 'figure' in f.lower() or 'fig' in f.lower()]
            figure_files.sort()  # 파일명 순으로 정렬
            
            if figure_idx < len(figure_files):
                fallback_file = figure_files[figure_idx]
                fallback_path = os.path.join(image_folder, fallback_file)
                if os.path.exists(fallback_path):
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"✅ Figure 이미지 순서 매칭: {fallback_file} (인덱스: {figure_idx})")
                    return fallback_path
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"❌ Figure 이미지 매칭 실패: 적절한 파일을 찾을 수 없음")
            
            return None
            
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"로컬 Figure 이미지 검색 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()
            return None

    def _calculate_figure_match_score(self, filename, caption, page_num, te_number, figure_idx):
        """
        파일명과 Figure 정보 간의 매칭 점수를 계산
        
        Args:
            filename (str): 파일명
            caption (str): Figure 캡션
            page_num (str/int): 페이지 번호
            te_number (str): TE 번호
            figure_idx (int): Figure 인덱스
            
        Returns:
            int: 매칭 점수 (높을수록 좋은 매칭)
        """
        score = 0
        filename_lower = filename.lower()
        caption_lower = caption.lower() if caption else ''
        
        # 1. TE 번호 매칭 (최고 우선순위)
        if te_number:
            te_variants = [
                te_number.lower(),
                te_number.replace('.', '_').lower(),
                te_number.replace('.', '-').lower(),
                te_number.replace('te', '').replace('.', '_').lower()
            ]
            
            for te_variant in te_variants:
                if te_variant in filename_lower:
                    score += 100
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"    TE 번호 매칭: {te_variant} in {filename_lower} (+100)")
                    break
        
        # 2. Figure 키워드 매칭
        figure_keywords = ['figure', 'fig']
        for keyword in figure_keywords:
            if keyword in filename_lower and keyword in caption_lower:
                score += 80
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"    Figure 키워드 매칭: {keyword} (+80)")
                break
        
        # 3. 페이지 번호 매칭
        if page_num and str(page_num) != 'Unknown':
            page_patterns = [
                f'page{page_num}',
                f'p{page_num}',
                f'_{page_num}_',
                f'-{page_num}-'
            ]
            
            for pattern in page_patterns:
                if pattern in filename_lower:
                    score += 60
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"    페이지 번호 매칭: {pattern} (+60)")
                    break
        
        # 4. Figure 번호 매칭 (캡션에서 추출)
        figure_number_match = re.search(r'figure\s*(\d+)', caption_lower)
        if figure_number_match:
            fig_num = figure_number_match.group(1)
            fig_patterns = [
                f'figure{fig_num}',
                f'fig{fig_num}',
                f'_{fig_num}_',
                f'-{fig_num}-'
            ]
            
            for pattern in fig_patterns:
                if pattern in filename_lower:
                    score += 90
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"    Figure 번호 매칭: {pattern} (+90)")
                    break
        
        # 5. 인덱스 기반 매칭
        index_patterns = [
            f'_{figure_idx + 1}_',
            f'-{figure_idx + 1}-',
            f'_{figure_idx + 1}.',
            f'-{figure_idx + 1}.'
        ]
        
        for pattern in index_patterns:
            if pattern in filename_lower:
                score += 40
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"    인덱스 매칭: {pattern} (+40)")
                break
        
        # 6. 일반 키워드 매칭
        common_keywords = ['image', 'img', 'picture', 'pic']
        for keyword in common_keywords:
            if keyword in filename_lower and ('figure' in caption_lower or 'fig' in caption_lower):
                score += 20
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"    일반 키워드 매칭: {keyword} (+20)")
                break
        
        return score

    def _zoom_in_figure(self, figure, figure_idx):
        """Figure 이미지 확대"""
        if not hasattr(self, 'figure_zoom_factors'):
            self.figure_zoom_factors = {}
        
        current_zoom = self.figure_zoom_factors.get(figure_idx, 1.0)
        self.figure_zoom_factors[figure_idx] = min(2.0, current_zoom + 0.2)
        self._refresh_content()

    def _zoom_out_figure(self, figure, figure_idx):
        """Figure 이미지 축소"""
        if not hasattr(self, 'figure_zoom_factors'):
            self.figure_zoom_factors = {}
        
        current_zoom = self.figure_zoom_factors.get(figure_idx, 1.0)
        self.figure_zoom_factors[figure_idx] = max(0.5, current_zoom - 0.2)
        self._refresh_content()

    def _refresh_content(self):
        """확대/축소 비율을 반영하여 콘텐츠를 다시 렌더링"""
        try:
            # 기존 오른쪽 패널 콘텐츠 모두 제거
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            # 데이터 다시 로드 및 표시
            if self.validator and self.te_number:
                text_data, table_data, figure_data = self._safe_get_test_data()
                self._display_mixed_content(text_data, table_data, figure_data)
            
            # 스크롤 영역 업데이트
            self.content_frame.update_idletasks()
            self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print("콘텐츠 새로고침 완료")
                
        except Exception as e:
            error_label = tk.Label(self.content_frame, text=f"새로고침 중 오류: {str(e)}", 
                                fg="red", font=("Arial", 10))
            error_label.pack(pady=10)
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"콘텐츠 새로고침 오류: {str(e)}")
                import traceback
                traceback.print_exc()

    def _display_table_as_text(self, table):
        """테이블 내용을 텍스트로 표시"""
        cells = table.get('cells', [])
        if cells:
            text_widget = tk.Text(
                self.content_frame, 
                wrap=tk.WORD, 
                height=5, 
                bg="#f9f9f9", 
                font=("Arial", 10),
                relief=tk.SOLID,
                bd=1
            )
            for cell in cells:
                cell_text = str(cell.get('text', ''))
                text_widget.insert(tk.END, cell_text + "\n")
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(fill=tk.X, padx=5, pady=2)

    def _display_image(self, image_data):
        """
        이미지 데이터를 처리하여 캔버스에 표시
        
        Args:
            image_data (dict): 이미지 데이터
        """
        image = None
        self.original_image = None
        self.zoom_level = 1.0
        
        try:
            if isinstance(image_data, Image.Image):
                image = image_data
            elif isinstance(image_data, dict):
                if 'base64' in image_data and image_data['base64']:
                    base64_data = image_data['base64']
                    if base64_data.startswith('data:image'):
                        base64_parts = base64_data.split(',', 1)
                        if len(base64_parts) > 1:
                            base64_data = base64_parts[1]
                    image_bytes = base64.b64decode(base64_data)
                    image = Image.open(BytesIO(image_bytes))
                elif 'file_path' in image_data and image_data['file_path']:
                    file_path = image_data['file_path']
                    if os.path.exists(file_path):
                        image = Image.open(file_path)
                elif 'src' in image_data and image_data['src']:
                    src = image_data['src']
                    if os.path.exists(src):
                        image = Image.open(src)
                elif 'url' in image_data and image_data['url']:
                    url = image_data['url']
                    if os.path.exists(url):
                        image = Image.open(url)
                else:
                    raise ValueError("이미지 데이터가 없습니다.")
            else:
                raise ValueError("지원되지 않는 이미지 데이터 형식입니다.")
            
            if image:
                self.original_image = image
                orig_width, orig_height = image.size
                screen_width = self.top.winfo_screenwidth() * 0.7
                screen_height = self.top.winfo_screenheight() * 0.7
                
                if orig_width > screen_width or orig_height > screen_height:
                    width_ratio = screen_width / orig_width
                    height_ratio = screen_height / orig_height
                    ratio = min(width_ratio, height_ratio)
                    new_width = int(orig_width * ratio)
                    new_height = int(orig_height * ratio)
                    image = image.resize((new_width, new_height), Image.LANCZOS)
                    self.zoom_level = ratio
                
                self.photo = ImageTk.PhotoImage(image)
                self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
                
                self.canvas.bind("<MouseWheel>", self._on_mousewheel)
                self.canvas.bind("<Button-4>", self._on_mousewheel)
                self.canvas.bind("<Button-5>", self._on_mousewheel)
        
        except Exception as e:
            error_text = f"이미지 로드 중 오류 발생: {str(e)}"
            self.canvas.create_text(
                10, 10, 
                text=error_text, 
                anchor=tk.NW, 
                fill="red", 
                font=("Arial", 12)
            )

    def _on_mousewheel(self, event):
        """
        마우스 휠 이벤트 처리 - 이미지 확대/축소
        
        Args:
            event: 마우스 이벤트
        """
        if not hasattr(self, 'original_image') or self.original_image is None:
            return
            
        old_zoom = self.zoom_level
        
        if event.num == 4 or event.delta > 0:  # 확대
            self.zoom_level *= 1.1
        elif event.num == 5 or event.delta < 0:  # 축소
            self.zoom_level *= 0.9
        
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        
        if old_zoom != self.zoom_level:
            self._update_image_display()

    def _update_image_display(self):
        """현재 줌 레벨에 맞게 이미지를 업데이트"""
        if self.original_image:
            orig_width, orig_height = self.original_image.size
            new_width = int(orig_width * self.zoom_level)
            new_height = int(orig_height * self.zoom_level)
            resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(resized_image)
            if self.image_id:
                self.canvas.itemconfig(self.image_id, image=self.photo)
            else:
                self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def _create_close_button(self):
        """닫기 버튼 생성"""
        close_btn = tk.Button(
            self.button_container, 
            text="닫기", 
            command=self.top.destroy,
            width=10,
            bg="#f0f0f0"
        )
        close_btn.pack(pady=10)


        
class JSONValidatorGUI:
    def __init__(self, root):
        """
        GUI 인터페이스 초기화
        
        Args:
            root (tk.Tk): Tkinter 루트 창
        """
        self.root = root
        self.root.title("Machine Readable 시험결과보고서 변환 및 판정 도구")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        self.is_validating = False
        self.validation_completed = False
        self.stop_progress_animation = False
        
        self.found_paths = {}
        self.table_paths = []
        self.test_contents = {}
        
        try:
            self.validator = JSONValidator()
        except NameError:
            messagebox.showerror("오류", "필요한 모듈을 불러올 수 없습니다. 프로그램을 종료합니다.")
            self.root.destroy()
            return
        
        self._create_widgets()
    
    def _create_widgets(self):
        """GUI 요소를 생성하고 배치"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_file_selection_widgets(main_frame)
        self._create_validation_button(main_frame)
        self._create_progress_widgets(main_frame)
        self._create_result_widgets(main_frame)
        self._create_status_bar()
    
    def _create_file_selection_widgets(self, parent):##added by yj
        """
        파일 선택 관련 위젯을 생성
        
        Args:
            parent (tk.Frame): 부모 프레임
        """
        control_frame = tk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # PDF 파일 선택 라인
        pdf_frame = tk.Frame(control_frame)
        pdf_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.pdf_file_path = tk.StringVar() ## added by yj
        tk.Label(pdf_frame, text="PDF 파일:").pack(side=tk.LEFT, padx=(0, 5))
        tk.Entry(pdf_frame, textvariable=self.pdf_file_path, width=50).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(pdf_frame, text="찾아보기", command=self.browse_pdf_file).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(pdf_frame, text="JSON 파일 변환하기", command=self.browse_pdf_to_json_file).pack(side=tk.LEFT, padx=(0, 5))##
        
        # JSON 파일과 Config 파일 선택 라인
        json_config_frame = tk.Frame(control_frame)
        json_config_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.json_file_path = tk.StringVar()
        tk.Label(json_config_frame, text="JSON 파일:").pack(side=tk.LEFT, padx=(0, 5))
        tk.Entry(json_config_frame, textvariable=self.json_file_path, width=50).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(json_config_frame, text="찾아보기", command=self.browse_json_file).pack(side=tk.LEFT, padx=(0, 5))
        
        self.config_file_path = tk.StringVar()
        tk.Label(json_config_frame, text="Config 파일:").pack(side=tk.LEFT, padx=(20, 5))
        tk.Entry(json_config_frame, textvariable=self.config_file_path, width=50).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(json_config_frame, text="찾아보기", command=self.browse_config_file).pack(side=tk.LEFT, padx=(0, 5))
        
        sample_frame = tk.Frame(parent)
        sample_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Button(sample_frame, text="샘플 Config 파일 생성 (TE 형식)", 
                command=self.create_sample_config, bg="#4682B4", fg="white").pack(side=tk.LEFT)
        
        info_label = tk.Label(
            sample_frame, 
            text="config.txt는 'TE02.03.01' 형식으로 각 줄에 검색할 값을 입력하세요.", 
            font=("Arial", 9, "italic"), 
            fg="#666666"
        )
        info_label.pack(side=tk.LEFT, padx=10)
    
    def _create_validation_button(self, parent):
        """
        검증 버튼 생성
        
        Args:
            parent (tk.Frame): 부모 프레임
        """
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.save_pdf_btn = tk.Button(
            button_frame, 
            text="PDF로 저장", 
            command=self.save_results_to_pdf,
            bg="#4682B4",
            fg="white",
            font=("Arial", 10),
            width=12
        )
        self.save_pdf_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.validate_button = tk.Button(
            button_frame, 
            text="판정 시작", 
            command=self.start_validation, 
            bg="#4CAF50", 
            fg="white", 
            font=("Arial", 12, "bold"), 
            width=20, 
            height=1
        )
        self.validate_button.pack(side=tk.RIGHT, pady=5)
    
    def _create_progress_widgets(self, parent):
        """
        프로그레스 바 관련 위젯 생성
        
        Args:
            parent (tk.Frame): 부모 프레임
        """
        progress_frame = tk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = tk.Label(
            progress_frame, 
            text="", 
            font=("Arial", 10)
        )
        self.progress_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient="horizontal", 
            length=780, 
            mode="indeterminate"
        )
        self.progress_bar.pack(fill=tk.X)
        
        style = ttk.Style()
        style.configure("TProgressbar", thickness=15, troughcolor='#f0f0f0', background='#4CAF50')
    
    def _create_result_widgets(self, parent):
        """
        결과 표시 위젯 생성.
        
        Args:
            parent (tk.Frame): 부모 프레임
        """
        tk.Label(parent, text="검증 결과:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(5, 0))
        
        # result_frame을 PanedWindow로 변경하여 70:30 비율 설정
        self.result_paned = tk.PanedWindow(parent, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
        self.result_paned.pack(fill=tk.BOTH, expand=True)

        # 왼쪽 프레임 (검출 항목, 70%)
        left_frame = tk.Frame(self.result_paned, bd=1, relief=tk.SOLID)
        self.result_paned.add(left_frame, minsize=300, stretch="always")
        tk.Label(left_frame, text="검출 항목", font=("Arial", 11, "bold"), bg="#e6f2ff").pack(fill=tk.X)
        
        # 버튼 영역을 스크롤 가능한 Canvas로 유지
        self.buttons_canvas_frame = tk.Frame(left_frame)
        self.buttons_canvas_frame.pack(fill=tk.BOTH, side=tk.BOTTOM, pady=5)
        
        # Canvas와 Scrollbar 생성
        self.buttons_canvas = tk.Canvas(self.buttons_canvas_frame, bg="#f5f5f5", highlightthickness=0)
        v_scrollbar = tk.Scrollbar(self.buttons_canvas_frame, orient=tk.VERTICAL, command=self.buttons_canvas.yview)
        h_scrollbar = tk.Scrollbar(self.buttons_canvas_frame, orient=tk.HORIZONTAL, command=self.buttons_canvas.xview)
        
        self.buttons_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.buttons_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas 내부에 버튼을 배치할 Frame 생성
        self.buttons_frame = tk.Frame(self.buttons_canvas, bg="#f5f5f5")
        self.canvas_window = self.buttons_canvas.create_window((0, 0), window=self.buttons_frame, anchor="nw")
        
        # Canvas 스크롤 영역 업데이트 및 마우스 휠 이벤트 바인딩
        self.buttons_frame.bind("<Configure>", self._update_scrollregion)
        self.buttons_canvas.bind("<MouseWheel>", self._on_mousewheel_horizontal)
        self.buttons_canvas.bind("<Button-4>", self._on_mousewheel_horizontal)
        self.buttons_canvas.bind("<Button-5>", self._on_mousewheel_horizontal)
        
        self.found_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, bg="#f5f5f5")
        self.found_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 오른쪽 프레임 (누락 항목, 30%)
        right_frame = tk.Frame(self.result_paned, bd=1, relief=tk.SOLID)
        self.result_paned.add(right_frame, minsize=200, stretch="always")
        tk.Label(right_frame, text="누락 항목", font=("Arial", 11, "bold"), bg="#ffe6e6").pack(fill=tk.X)
        self.not_found_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, bg="#f5f5f5")
        self.not_found_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 창 렌더링 후 70:30 비율 설정
        self.root.after(100, self._set_result_paned_sash)

    def _set_result_paned_sash(self):
        """검출 항목과 누락 항목 창의 비율을 70:30으로 설정"""
        self.root.update_idletasks()
        total_width = self.result_paned.winfo_width()
        sash_position = int(total_width * 0.7)  # 70% 지점
        self.result_paned.sash_place(0, sash_position, 0)
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"Result PanedWindow 너비: {total_width}, 분할선 위치: {sash_position}")




    def _update_scrollregion(self, event):
        """Canvas의 스크롤 영역 업데이트"""
        self.buttons_canvas.configure(scrollregion=self.buttons_canvas.bbox("all"))
    

    def _on_mousewheel_horizontal(self, event):
        """
        마우스 휠로 가로 스크롤 처리
        
        Args:
            event: 마우스 휠 이벤트
        """
        if event.num == 4 or event.delta > 0:
            self.buttons_canvas.xview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.buttons_canvas.xview_scroll(1, "units")


    def _create_status_bar(self):
        """상태 표시줄을 생성"""
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def browse_pdf_file(self):
        """pdf 파일 선택 다이얼로그를 여는 동작수행"""
        file_path = filedialog.askopenfilename(filetypes=[("PDF 파일", "*.pdf")])
        if file_path:
            self.pdf_file_path.set(file_path)
    
    def browse_json_file(self):
        """JSON 파일 선택 다이얼로그를 여는 동작수행"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON 파일", "*.json")])
        if file_path:
            self.json_file_path.set(file_path)
    
    def browse_config_file(self):
        """Config 파일 선택 다이얼로그를 여는 동작수행"""
        file_path = filedialog.askopenfilename(filetypes=[("텍스트 파일", "*.txt")])
        if file_path:
            self.config_file_path.set(file_path)

    def browse_pdf_to_json_file(self):
        """PDF를 JSON으로 변환하는 함수"""
        # 선택된 PDF 파일 경로 가져오기
        pdf_path = self.pdf_file_path.get()
    
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("오류", "먼저 PDF 파일을 선택해주세요.")
            return
    
        # PDF와 같은 폴더에 JSON 파일 경로 생성
        pdf_dir = os.path.dirname(pdf_path)  # PDF 파일이 있는 폴더
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]  # 확장자 제거한 파일명
        json_path = os.path.join(pdf_dir, pdf_name + ".json")  # 같은 폴더에 .json 확장자로
    
        # 변환 버튼 비활성화
        self.validate_button.config(state=tk.DISABLED)
        self.status_var.set("PDF를 JSON으로 변환 중...")
        
        # 진행상황 표시
        self.progress_bar.start(10)
        self.progress_label.config(text="PDF 변환 중...")
        
        # 별도 스레드에서 변환 실행
        conversion_thread = threading.Thread(target=self._pdf_to_json_thread, args=(pdf_path, json_path))
        conversion_thread.daemon = True
        conversion_thread.start()

    def _pdf_to_json_thread(self, pdf_path, json_path):
        """PDF → JSON 변환 작업을 수행하는 스레드 함수"""
        try:
            # 로그 함수 정의
            def log_callback(message):
                self.root.after(0, lambda: self.status_var.set(message))
        
            # PDF → JSON 변환 실행
            success = enhanced_pdf_to_json(pdf_path, json_path, log_callback=log_callback)

            if success:
                # JSON → PDF 변환을 위한 recovered PDF 경로 생성
                pdf_dir = os.path.dirname(pdf_path)
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                recovered_pdf_path = os.path.join(pdf_dir, pdf_name + "_recovered.pdf")
            
                # JSON → PDF 변환 실행
                convert_json_to_pdf(json_path, recovered_pdf_path, log_callback=log_callback)
    
            # 메인 스레드에서 완료 처리
            self.root.after(0, lambda: self._pdf_conversion_complete(success, json_path))
        
        except Exception as e:
            error_msg = f"PDF 변환 중 오류 발생: {str(e)}"
            self.root.after(0, lambda: self._pdf_conversion_complete(False, json_path, error_msg))

    def _pdf_conversion_complete(self, success, json_path, error_msg=None):
        """PDF 변환 완료 후 결과 처리"""
        # 진행상황 표시 중지
        self.progress_bar.stop()
        self.progress_bar.config(value=0)
    
        if success:
            # 변환 성공
            self.json_file_path.set(json_path)
            self.progress_label.config(text="PDF → JSON 변환 완료")
            self.status_var.set("변환 완료")
        
            messagebox.showinfo("성공", f"PDF가 JSON으로 변환되었습니다:\n{os.path.basename(json_path)}")
        
        else:
            # 변환 실패
            self.progress_label.config(text="PDF 변환 실패")
            self.status_var.set("변환 실패")
        
            error_message = error_msg if error_msg else "PDF 변환 중 오류가 발생했습니다."
            messagebox.showerror("오류", error_message)
    
            # 버튼 다시 활성화
        self.validate_button.config(state=tk.NORMAL)

    def create_sample_config(self):
        """샘플 config.txt 파일 생성 기능"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt")],
            initialfile="config.txt"
        )
        
        if file_path:
            if ConfigReader.create_sample_config_file(file_path):
                messagebox.showinfo("알림", f"샘플 Config 파일이 생성되었습니다: {file_path}")
                self.config_file_path.set(file_path)
            else:
                messagebox.showerror("오류", "샘플 Config 파일 생성 중 오류가 발생했습니다.")
    
    def update_progress_animation(self):
        """프로그레스 바 애니메이션과 메시지를 업데이트, 계속 진행중으로 표시"""
        progress_steps = [
            "JSON 파일 로드 중...",
            "파일 구조 분석 중...",
            "Config 파일에서 검색할 값 읽는 중...",
            "JSON 구조에서 값 검색 중...",
            "검색 결과 정리 중...",
            "결과 데이터 처리 중..."
        ]
        
        step_index = 0
        animation_dots = 0
        
        while not self.validation_completed and not self.stop_progress_animation:
            base_message = progress_steps[step_index]
            dots = "." * animation_dots
            self.progress_label.config(text=f"{base_message}{dots}")
            self.root.update_idletasks()
            animation_dots = (animation_dots + 1) % 4
            if animation_dots == 0:
                step_index = (step_index + 1) % len(progress_steps)
            time.sleep(0.3)
    
    def start_validation(self):
        """검증 작업을 시작"""
        if self.is_validating:
            return
        
        pdf_path = self.pdf_file_path.get()
        json_path = self.json_file_path.get()
        config_path = self.config_file_path.get()

        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("오류", "유효한 PDF 파일을 선택해주세요.")
            return
        
        if not json_path or not os.path.exists(json_path):
            messagebox.showerror("오류", "유효한 JSON 파일을 선택해주세요.")
            return
        
        if not config_path or not os.path.exists(config_path):
            messagebox.showerror("오류", "유효한 Config 파일을 선택해주세요.")
            return
        
        self.is_validating = True
        self.validation_completed = False
        self.stop_progress_animation = False
        
        self.found_text.delete(1.0, tk.END)
        self.not_found_text.delete(1.0, tk.END)
        self.found_paths = {}
        self.table_paths = []
        self.test_contents = {}
        
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()
        
        self.validate_button.config(text="판정 중...", state=tk.DISABLED, bg="#cccccc")
        self.progress_bar.start(10)
        self.progress_bar.pack(fill=tk.X)
        self.progress_label.config(text="판정을 준비 중입니다...")
        self.status_var.set("판정 중...")
        
        validation_thread = threading.Thread(target=self.validate_in_thread)
        validation_thread.daemon = True
        validation_thread.start()
        
        progress_animation_thread = threading.Thread(target=self.update_progress_animation)
        progress_animation_thread.daemon = True
        progress_animation_thread.start()
    
    def validate_in_thread(self):
        """별도 스레드에서 검증 실행"""
        pdf_path = self.pdf_file_path.get()
        json_path = self.json_file_path.get()
        config_path = self.config_file_path.get()
        
        result = {
            'success': False,
            'error': None,
            'found_items': {},
            'not_found_items': [],
            'search_values': []
        }
        
        try:
            try:
                self.validator.load_json_file(json_path)
            except json.JSONDecodeError:
                result['error'] = "유효하지 않은 JSON 파일입니다."
                return
            except Exception as e:
                result['error'] = f"JSON 파일 로드 중 오류 발생: {str(e)}"
                return
            
            try:
                search_values = ConfigReader.read_config_file(config_path)
                result['search_values'] = search_values
            except Exception as e:
                result['error'] = str(e)
                return
            
            if not search_values:
                result['error'] = "Config 파일에서 검색할 값을 찾을 수 없습니다."
                return
            
            found_items, not_found_items = self.validator.search_value(search_values)
            result['found_items'] = found_items
            result['not_found_items'] = not_found_items
            result['success'] = True
            
            if result['success']:
                for value in found_items.keys():
                    if re.match(r'^TE\d+(\.\d+)+$', value):
                        test_content = self._get_test_content(value)
                        self.test_contents[value] = test_content
            
        except Exception as e:
            result['error'] = f"검증 중 오류 발생: {str(e)}"
        
        finally:
            self.root.after(0, lambda: self.finish_validation(result))
    
    def _get_test_content(self, te_number):
        """
        TE 번호에 해당하는 시험내용 텍스트를 JSON 데이터에서 추출
        
        Args:
            te_number (str): TE 번호 (예: TE02.03.01)
        
        Returns:
            str: 시험내용 텍스트 또는 "시험내용 없음" 메시지
        """
        if not self.validator.json_data:
            return "JSON 데이터가 로드되지 않았습니다."
        
        test_content = []
        
        for page in self.validator.json_data.get("pages", []):
            page_text = page.get("text", "")
            page_number = page.get("page_number", "Unknown")
            
            if te_number in page_text:
                test_content.append(f"페이지 {page_number} 관련 텍스트:\n{page_text.strip()}")
                
                for text_block in page.get("text_blocks", []):
                    if 'text' in text_block:
                        text = text_block['text']
                        if te_number in text or any(keyword in text.lower() for keyword in ["시험", "검증", "결과", "보고서"]):
                            test_content.append(f"텍스트 블록: {text.strip()}")
                
                for table in page.get("tables", []):
                    caption = table.get("caption", "")
                    if te_number in caption or te_number in str(table.get("cells", "")):
                        test_content.append(f"테이블 캡션: {caption}\n테이블 내용: {self._format_table_cells(table.get('cells', []))}")
                
                for image in page.get("images", []):
                    caption = image.get("caption", "")
                    if te_number in caption:
                        test_content.append(f"이미지 캡션: {caption}")
        
        if test_content:
            return "\n\n".join(test_content)
        return f"{te_number}에 대한 시험내용을 찾을 수 없습니다."
    
    def _get_judgment_result(self, te_number):
        """
        TE 번호에 해당하는 '판정결과' 텍스트를 JSON 데이터에서 추출
        
        Args:
            te_number (str): TE 번호 (예: TE02.03.01)
        
        Returns:
            str: 판정결과 텍스트 또는 "판정결과 없음" 메시지
        """
        if not self.validator.json_data:
            return "JSON 데이터가 로드되지 않았습니다."
        
        test_content = []
        judgment_pattern = r'판정\s*결과'
        
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"_get_judgment_result 호출: TE 번호 = {te_number}")
        
        for page in self.validator.json_data.get("pages", []):
            page_text = page.get("text", "")
            page_number = page.get("page_number", "Unknown")
            
            if te_number in page_text and re.search(judgment_pattern, page_text, re.IGNORECASE):
                # 페이지 텍스트에서 '판정결과' 섹션 추출
                lines = page_text.split('\n')
                judgment_section = []
                in_judgment_section = False
                
                for line in lines:
                    line = line.strip()
                    if re.search(judgment_pattern, line, re.IGNORECASE):
                        in_judgment_section = True
                        judgment_section.append(line)
                    elif in_judgment_section:
                        if re.match(r'^\d+\.\d+\.\d+\s+', line):  # 다른 섹션 시작
                            in_judgment_section = False
                            break
                        if line:
                            judgment_section.append(line)
                
                if judgment_section:
                    test_content.append(f"페이지 {page_number} 판정결과:\n" + '\n'.join(judgment_section))
            
            # 텍스트 블록에서 추가 확인
            for text_block in page.get("text_blocks", []):
                if 'text' in text_block:
                    text = text_block['text'].strip()
                    if te_number in text and re.search(judgment_pattern, text, re.IGNORECASE):
                        lines = text.split('\n')
                        judgment_section = []
                        in_judgment_section = False
                        
                        for line in lines:
                            line = line.strip()
                            if re.search(judgment_pattern, line, re.IGNORECASE):
                                in_judgment_section = True
                                judgment_section.append(line)
                            elif in_judgment_section:
                                if re.match(r'^\d+\.\d+\.\d+\s+', line):
                                    in_judgment_section = False
                                    break
                                if line:
                                    judgment_section.append(line)
                        
                        if judgment_section:
                            test_content.append(f"텍스트 블록 판정결과:\n" + '\n'.join(judgment_section))
            
            # 테이블에서 검색
            for table in page.get("tables", []):
                caption = table.get("caption", "")
                cells = table.get("cells", [])
                if te_number in caption or any(te_number in cell.get("text", "") for cell in cells):
                    if "시험결과 판정 근거" in caption or any("시험결과 판정 근거" in cell.get("text", "") for cell in cells):
                        judgment_section = [f"테이블 캡션: {caption}"]
                        for cell in cells:
                            cell_text = cell.get("text", "").strip()
                            if cell_text:
                                judgment_section.append(f"셀: {cell_text}")
                        test_content.append(f"페이지 {page_number} 테이블 판정 근거:\n" + '\n'.join(judgment_section))
        
        if test_content:
            result = "\n\n".join(test_content)
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"_get_judgment_result 결과:\n{result[:200] if result else '없음'}...")
            return result
        return f"{te_number}에 대한 판정결과를 찾을 수 없습니다."
    
    def _format_table_cells(self, cells):
        """
        테이블 셀 데이터를 문자열로 포맷팅 수행
        
        Args:
            cells (list): 테이블 셀 데이터 리스트
        
        Returns:
            str: 포맷팅된 테이블 내용
        """
        if not cells:
            return "테이블 데이터 없음"
        
        formatted = []
        for cell in cells:
            text = cell.get("text", "")
            row_idx = cell.get("row_idx", "")
            col_idx = cell.get("col_idx", "")
            if text:
                formatted.append(f"행 {row_idx}, 열 {col_idx}: {text}")
        
        return "\n".join(formatted) if formatted else "셀 데이터 없음"

    def finish_validation(self, result):
        """검증이 완료된 후 UI 업데이트 수행"""
        self.progress_bar.stop()
        self.validation_completed = True
        self.stop_progress_animation = True
        
        if result['success']:
            found_items = result['found_items']
            not_found_items = result['not_found_items']
            search_values = result['search_values']
            
            self.progress_bar.config(mode="determinate")
            self.progress_bar.config(value=100)
            self.progress_label.config(text="검증 완료")
            
            self.found_paths = found_items
            self._display_results(found_items, not_found_items)
            self._create_test_result_buttons(found_items)
            
            # test_contents를 validator 객체에 저장
            self.validator.test_contents = self.test_contents
            
            self.status_var.set(f"검증 완료 - 찾음: {len(found_items)}, 못 찾음: {len(not_found_items)}")
            messagebox.showinfo("검증 완료", 
                               f"검색할 항목 총 {len(search_values)}개 중\n"
                               f"{len(found_items)}개 발견, {len(not_found_items)}개 누락")
        else:
            self.progress_bar.config(mode="determinate")
            self.progress_bar.config(value=0)
            self.progress_label.config(text=f"오류 발생: {result['error']}")
            
            self.status_var.set("오류 발생")
            
            if result['error'] == "Config 파일에서 검색할 값을 찾을 수 없습니다.":
                result_dialog = messagebox.askyesno(
                    "경고", 
                    "Config 파일에서 검색할 값을 찾을 수 없습니다.\n\n"
                    "샘플 Config 파일을 생성하시겠습니까?"
                )
                
                if result_dialog:
                    self.create_sample_config()
            else:
                messagebox.showerror("오류", result['error'])
        
        self.validate_button.config(text="검증 시작", state=tk.NORMAL, bg="#4CAF50")
        self.is_validating = False
    
    def _display_results2(self, found_items, not_found_items):#이전 출력형식으로 삭제 yj
        """
        검증 결과를 화면에 표시
        
        Args:
            found_items (dict): 찾은 항목 딕셔너리 {값: [경로 리스트]}
            not_found_items (list): 못 찾은 항목 리스트
        """
        te_numbers = []
        
        for value, paths in found_items.items():
            if re.match(r'^TE\d+(\.\d+)+$', value):
                te_numbers.append(value)
            
            self.found_text.insert(tk.END, f"✓ 값 '{value}' 발견\n", "green")
            
            """for i, path in enumerate(paths):
                self.found_text.insert(tk.END, f"  - 경로: {path}\n")
            
            if value in self.test_contents:
                test_content = self.test_contents[value]
                self.found_text.insert(tk.END, f"  시험내용:\n{test_content}\n", "content")
            
            self.found_text.insert(tk.END, "\n")"""
        
        self.te_numbers = te_numbers
        
        for value in not_found_items:
            self.not_found_text.insert(tk.END, f"✗ 값 '{value}' 찾을 수 없음\n", "red")
        
        self.found_text.tag_config("green", foreground="green", font=("Arial", 11, "bold"))
        self.found_text.tag_config("red", foreground="red", font=("Arial", 11, "bold"))
        self.found_text.tag_config("content", font=("Arial", 10), foreground="black")
        self.not_found_text.tag_config("red", foreground="red", font=("Arial", 11, "bold"))

    ##여기부터 added by yj
    def _create_test_result_buttons(self, found_items):
            self.table_paths = []
            te_numbers = []
            
            for value, paths in found_items.items():
                if re.match(r'^TE\d+(\.\d+)+$', value):
                    te_numbers.append(value)
            
            self.te_numbers = te_numbers
            
            if hasattr(self, 'te_numbers') and self.te_numbers:
                tk.Label(
                    self.buttons_frame, 
                    text="시험항목 및 시험결과", 
                    font=("Arial", 10, "bold"),
                    bg="#f5f5f5"
                ).pack(anchor=tk.W, pady=(5, 3))
                
                te_groups = self._group_te_numbers(te_numbers)
                
                for main_te, sub_tes in te_groups.items():
                    self._create_accordion_group(main_te, sub_tes)
            
            if not PIL_AVAILABLE:
                warning_label = tk.Label(
                    self.buttons_frame,
                    text="알림: PIL 라이브러리가 설치되지 않아 테이블 이미지와 일반 이미지를 표시할 수 없습니다. 'pip install pillow'로 설치하세요.",
                    font=("Arial", 9, "italic"),
                    fg="#FF6347",
                    pady=5,
                    bg="#f5f5f5"
                )
                warning_label.pack(fill=tk.X)
            
            self.buttons_frame.update_idletasks()
            self.buttons_canvas.configure(scrollregion=self.buttons_canvas.bbox("all"))
            
            self.buttons_canvas.master.update_idletasks()
            parent_height = self.buttons_canvas.master.winfo_height()
            canvas_height = parent_height
            
            self.buttons_canvas.configure(height=canvas_height)

    def _group_te_numbers(self, te_numbers):
        groups = {}
        
        for te_number in te_numbers:
            main_te = te_number.split('.')[0]
            
            if main_te not in groups:
                groups[main_te] = []
            groups[main_te].append(te_number)
        
        for main_te in groups:
            groups[main_te].sort()
        
        return groups

    def _create_accordion_group(self, main_te, sub_tes):
        group_frame = tk.Frame(self.buttons_frame, bg="#f5f5f5")
        group_frame.pack(fill=tk.X, pady=2)
        
        main_button = tk.Button(
            group_frame,
            text=f"▶ {main_te} 항목 ({len(sub_tes)}개)",
            command=lambda: self._toggle_accordion(main_te, main_button, sub_frame),
            bg="#d4edda",
            fg="#155724",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED,
            padx=10,
            pady=5,
            anchor=tk.W
        )
        main_button.pack(fill=tk.X, padx=2, pady=1)
        
        sub_frame = tk.Frame(group_frame, bg="#f8f9fa")
        
        buttons_container = tk.Frame(sub_frame, bg="#f8f9fa")
        buttons_container.pack(fill=tk.X, padx=10, pady=5)
        
        for i, sub_te in enumerate(sub_tes):
            sub_button = tk.Button(
                buttons_container,
                text=f"📋 {sub_te}",
                command=lambda tn=sub_te: self._show_test_result_popup(tn),
                bg="#e6f2ff",
                fg="#0056b3",
                font=("Arial", 8),
                relief=tk.RAISED,
                padx=8,
                pady=4,
                bd=1
            )
            sub_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, pady=2)
            
            sub_button.bind("<Enter>", lambda e, btn=sub_button: btn.config(bg="#cce7ff"))
            sub_button.bind("<Leave>", lambda e, btn=sub_button: btn.config(bg="#e6f2ff"))
        
        if not hasattr(self, 'accordion_states'):
            self.accordion_states = {}
        
        self.accordion_states[main_te] = {
            'expanded': False,
            'button': main_button,
            'frame': sub_frame
        }

    def _toggle_accordion(self, main_te, main_button, sub_frame):
        state = self.accordion_states[main_te]
        
        if state['expanded']:
            sub_frame.pack_forget()
            main_button.config(
                text=f"▶ {main_te} 항목 ({len([te for te in self.te_numbers if te.startswith(main_te)])}개)",
                bg="#d4edda"
            )
            state['expanded'] = False
        else:
            sub_frame.pack(fill=tk.X, padx=10, pady=2)
            main_button.config(
                text=f"▼ {main_te} 항목 ({len([te for te in self.te_numbers if te.startswith(main_te)])}개)",
                bg="#c3e6cb"
            )
            state['expanded'] = True
        
        self.buttons_frame.update_idletasks()
        self.buttons_canvas.configure(scrollregion=self.buttons_canvas.bbox("all"))

    def _display_results(self, found_items, not_found_items):
            te_numbers = []
            
            for value, paths in found_items.items():
                if re.match(r'^TE\d+(\.\d+)+$', value):
                    te_numbers.append(value)
                
                self.found_text.insert(tk.END, f"✓ 값 '{value}' 발견\n", "green")
            
            self.te_numbers = te_numbers
            
            for value in not_found_items:
                self.not_found_text.insert(tk.END, f"✗ 값 '{value}' 찾을 수 없음\n", "red")
            
            self.found_text.tag_config("green", foreground="green", font=("Arial", 11, "bold"))
            self.found_text.tag_config("red", foreground="red", font=("Arial", 11, "bold"))
            self.found_text.tag_config("content", font=("Arial", 10), foreground="black")
            self.not_found_text.tag_config("red", foreground="red", font=("Arial", 11, "bold"))

    ###여기까지    
    
    def _create_test_result_buttons2(self, found_items):#이전 버튼 형식으로 삭제 yj
        """
        시험결과판정근거 표 버튼과 관련 이미지 버튼을 생성
        
        Args:
            found_items (dict): 찾은 항목 딕셔너리
        """
        self.table_paths = []
        te_numbers = []
        
        for value, paths in found_items.items():
            if re.match(r'^TE\d+(\.\d+)+$', value):
                te_numbers.append(value)
        
        self.te_numbers = te_numbers
        
        if hasattr(self, 'te_numbers') and self.te_numbers:
            tk.Label(
                self.buttons_frame, 
                text="시험결과", 
                font=("Arial", 10, "bold"),
                bg="#f5f5f5"
            ).pack(anchor=tk.W, pady=(5, 3))
            
            table_buttons_frame = tk.Frame(self.buttons_frame, bg="#f5f5f5")
            table_buttons_frame.pack(fill=tk.X, pady=2)
            
            btn_count = 0
            for te_number in self.te_numbers:
                btn = tk.Button(
                    table_buttons_frame, 
                    text=f"{te_number} 결과표",
                    command=lambda tn=te_number: self._show_test_result_popup(tn),
                    bg="#e6f2ff",
                    padx=5,
                    pady=2
                )
                # 가로 배치를 위해 pack 사용 (grid 대신)
                btn.pack(side=tk.LEFT, padx=3, pady=3)
                btn_count += 1
        
            self._create_te_related_image_buttons(te_numbers)
        
        if not PIL_AVAILABLE:
            warning_label = tk.Label(
                self.buttons_frame,
                text="알림: PIL 라이브러리가 설치되지 않아 테이블 이미지와 일반 이미지를 표시할 수 없습니다. 'pip install pillow'로 설치하세요.",
                font=("Arial", 9, "italic"),
                fg="#FF6347",
                pady=5,
                bg="#f5f5f5"
            )
            warning_label.pack(fill=tk.X)
        
        # Canvas 크기 조정
        self.buttons_frame.update_idletasks()
        self.buttons_canvas.configure(scrollregion=self.buttons_canvas.bbox("all"))
        # Canvas 높이를 버튼 프레임 높이에 맞게 제한 (최대 200픽셀)
        canvas_height = min(self.buttons_frame.winfo_reqheight(), 200)
        self.buttons_canvas.configure(height=canvas_height)

    def _analyze_json_structure(self):
        """
        JSON 데이터 구조를 분석하여 이미지 저장 방식을 파악
        """
        if not self.validator.json_data:
            return
        
        print("=== JSON 데이터 구조 분석 ===")
        
        total_pages = len(self.validator.json_data.get("pages", []))
        total_images = 0
        total_tables = 0
        image_locations = []
        
        for page_idx, page in enumerate(self.validator.json_data.get("pages", [])):
            if page is None:
                continue
                
            # 페이지 내 직접 이미지 확인
            page_images = page.get("images", [])
            if page_images:
                total_images += len(page_images)
                for img_idx, img in enumerate(page_images):
                    if img is None:
                        continue
                    image_info = {
                        "location": f"pages[{page_idx}].images[{img_idx}]",
                        "keys": list(img.keys()),
                        "has_base64": "base64" in img,
                        "has_file_path": "file_path" in img,
                        "has_image_data": "image_data" in img,
                        "has_src": "src" in img,
                        "caption": img.get("caption", ""),
                        "image_id": img.get("image_id", "")
                    }
                    image_locations.append(image_info)
                    print(f"페이지 {page_idx} 이미지 {img_idx}: {image_info}")
            
            # 테이블 내 이미지 확인  
            tables = page.get("tables", [])
            if tables:
                total_tables += len(tables)
                for table_idx, table in enumerate(tables):
                    if table is None:
                        continue
                    if "image" in table:
                        img = table["image"]
                        if isinstance(img, dict):
                            image_info = {
                                "location": f"pages[{page_idx}].tables[{table_idx}].image",
                                "keys": list(img.keys()),
                                "has_base64": "base64" in img,
                                "has_file_path": "file_path" in img,
                                "has_image_data": "image_data" in img,
                                "has_src": "src" in img,
                                "table_caption": table.get("caption", ""),
                                "table_id": table.get("table_id", "")
                            }
                            image_locations.append(image_info)
                            print(f"페이지 {page_idx} 테이블 {table_idx} 이미지: {image_info}")
        
        print(f"총 {total_pages}개 페이지, {total_images}개 직접 이미지, {total_tables}개 테이블")
        print(f"발견된 이미지 위치: {len(image_locations)}개")
        
        return image_locations

    def _create_te_related_image_buttons(self, te_numbers):
        """
        검출된 TE 번호와 관련된 이미지에 대한 버튼을 생성
        """
        if not self.validator.json_data or not te_numbers:
            return
        
        try:
            # 디버그 모드 활성화
            if hasattr(self.validator, 'debug_mode'):
                self.validator.debug_mode = True
            
            # 1. 모든 이미지 수집
            all_images = self._collect_all_images_flexible()
            
            if self.validator.debug_mode:
                print(f"=== TE 이미지 검색 디버그 ===")
                print(f"검색할 TE 번호들: {te_numbers}")
                print(f"전체 수집된 이미지 수: {len(all_images)}")
                for i, img in enumerate(all_images):
                    print(f"  이미지 {i+1}: 위치={img.get('location', 'N/A')}, 키={list(img.keys())}")
            
            # 2. 시험결과판정근거 표 이미지 식별
            test_result_images = []
            for te_number in te_numbers:
                image_data = self.validator.get_test_result_image(te_number)
                if image_data and (image_data.get('image') or image_data.get('base64')):
                    test_result_images.append(image_data)
            
            if self.validator.debug_mode:
                print(f"시험결과판정근거 표 이미지 수: {len(test_result_images)}")
            
            # 3. TE 관련 이미지 필터링
            te_related_images = self._filter_te_related_images_improved(all_images, te_numbers, test_result_images)
            
            if self.validator.debug_mode:
                print(f"최종 TE 관련 이미지 수: {len(te_related_images)}")
                for i, img in enumerate(te_related_images):
                    print(f"  TE 이미지 {i+1}: TE={img.get('te_number', 'N/A')}, 캡션={img.get('caption', 'N/A')}")
            
            # 4. 이미지 버튼 생성
            if te_related_images:
                tk.Label(
                    self.buttons_frame, 
                    text="TE 관련 이미지 보기:", 
                    font=("Arial", 10, "bold"),
                    bg="#f5f5f5"
                ).pack(anchor=tk.W, pady=(15, 3))
                
                image_buttons_frame = tk.Frame(self.buttons_frame, bg="#f5f5f5")
                image_buttons_frame.pack(fill=tk.X, pady=2)
                
                img_btn_count = 0
                for img_data in te_related_images:
                    te_num = img_data.get("te_number", "")
                    # 캡션 전체를 사용 (길이 제한 제거)
                    img_desc = f"{te_num} 관련 이미지"
                    if 'caption' in img_data and img_data['caption']:
                        img_desc = f"{te_num}: {img_data['caption']}"
                    
                    img_btn = tk.Button(
                        image_buttons_frame, 
                        text=img_desc,
                        command=lambda idata=img_data: self._show_image_popup_with_data(idata),
                        bg="#e6e6ff",
                        padx=5,
                        pady=2,
                        font=("Arial", 9),  # 폰트 크기 조정
                        wraplength=200,     # 텍스트 줄바꿈 너비 설정
                        justify=tk.LEFT     # 텍스트 왼쪽 정렬
                    )
                    # 가로 배치를 위해 pack 사용
                    img_btn.pack(side=tk.LEFT, padx=3, pady=3)
                    img_btn_count += 1
                    
                    if self.validator.debug_mode:
                        print(f"버튼 생성: TE={te_num}, 캡션={img_desc}")
            else:
                info_label = tk.Label(
                    self.buttons_frame,
                    text="TE 관련 이미지 보기:", 
                    font=("Arial", 10, "bold"),
                    bg="#f5f5f5"
                ).pack(anchor=tk.W, pady=(15, 3))
                
                image_buttons_frame = tk.Frame(self.buttons_frame, bg="#f5f5f5")
                image_buttons_frame.pack(fill=tk.X)
                
                no_images_label = tk.Label(
                    image_buttons_frame,
                    text="TE 관련 이미지를 찾을 수 없습니다.",
                    font=("Arial", 9, "italic"),
                    fg="#666666",
                    pady=5,
                    bg="#f5f5f5"
                )
                no_images_label.pack(anchor=tk.W, padx=5)
                
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"TE 관련 이미지 버튼 생성 중 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
            
            error_label = tk.Label(
                self.buttons_frame,
                text=f"이미지 처리 중 오류 발생: {str(e)}",
                font=("Arial", 9, "italic"),
                fg="red",
                pady=5,
                bg="#f5f5f5"
            )
            error_label.pack(fill=tk.X)
        
        # Canvas 스크롤 영역 업데이트
        self.buttons_frame.update_idletasks()
        self.buttons_canvas.configure(scrollregion=self.buttons_canvas.bbox("all"))

    def _collect_all_images_flexible(self):
        """
        JSON에서 모든 이미지를 유연한 조건으로 수집
        """
        all_images = []
        
        for page_idx, page in enumerate(self.validator.json_data.get("pages", [])):
            if page is None:
                continue
                
            # 1. 페이지 내 직접 이미지
            page_images = page.get("images", [])
            if page_images:
                for img_idx, img in enumerate(page_images):
                    if img is None:
                        continue
                    
                    # 더 유연한 이미지 데이터 확인 (조건 완화)
                    has_image_data = (
                        img.get('base64') or 
                        img.get('file_path') or 
                        img.get('image_data') or 
                        img.get('src') or 
                        img.get('url') or
                        img.get('caption') or  # 캡션만 있어도 이미지로 간주
                        img.get('image_id')    # 이미지 ID만 있어도 포함
                    )
                    
                    if has_image_data:
                        img_copy = img.copy()
                        img_copy['page_idx'] = page_idx
                        img_copy['image_idx'] = img_idx
                        img_copy['location'] = f"pages[{page_idx}].images[{img_idx}]"
                        all_images.append(img_copy)
                        
                        if self.validator.debug_mode:
                            print(f"수집된 페이지 이미지: {img_copy.get('location')}, 키: {list(img.keys())}")
            
            # 2. 테이블 내 이미지
            tables = page.get("tables", [])
            if tables:
                for table_idx, table in enumerate(tables):
                    if table is None:
                        continue
                        
                    if "image" in table and isinstance(table["image"], dict):
                        img = table["image"]
                        has_image_data = (
                            img.get('base64') or 
                            img.get('file_path') or 
                            img.get('image_data') or 
                            img.get('src') or 
                            img.get('url') or
                            table.get('caption') or  # 테이블 캡션도 고려
                            table.get('table_id')    # 테이블 ID도 고려
                        )
                        
                        if has_image_data:
                            img_copy = img.copy()
                            img_copy['page_idx'] = page_idx
                            img_copy['table_idx'] = table_idx
                            img_copy['location'] = f"pages[{page_idx}].tables[{table_idx}].image"
                            img_copy['table_caption'] = table.get('caption', '')
                            img_copy['table_id'] = table.get('table_id', '')
                            all_images.append(img_copy)
                            
                            if self.validator.debug_mode:
                                print(f"수집된 테이블 이미지: {img_copy.get('location')}, 키: {list(img.keys())}")
        
        return all_images

    def _filter_te_related_images_improved(self, all_images, te_numbers, test_result_images):
        """
        수집된 이미지 중에서 TE 관련 이미지만 필터링
        """
        te_related_images = []
        te_numbers_str = [str(te) for te in te_numbers]
        
        for img in all_images:
            # 시험결과판정근거 이미지 제외 조건을 더 엄격하게 적용
            if self._is_test_result_image_strict(img, test_result_images):
                if self.validator.debug_mode:
                    print(f"제외: 시험결과판정근거 표 이미지 - {img.get('location')}, 캡션={img.get('caption', 'N/A')}")
                continue
            
            # TE 번호와 관련성 확인 (개선된 로직)
            related_te = self._find_related_te_number_improved(img, te_numbers_str)
            
            if related_te:
                img_copy = img.copy()
                img_copy['te_number'] = related_te
                
                # 캡션이 없으면 생성
                if 'caption' not in img_copy or not img_copy['caption']:
                    img_copy['caption'] = self._generate_image_caption(img_copy)
                
                te_related_images.append(img_copy)
                
                if self.validator.debug_mode:
                    print(f"포함: TE 관련 이미지 - {img.get('location')}, TE={related_te}, 캡션={img_copy.get('caption', 'N/A')}")
            else:
                if self.validator.debug_mode:
                    print(f"제외: TE 관련성 없음 - {img.get('location')}, 캡션={img.get('caption', 'N/A')}")
        
        return te_related_images

    def _find_related_te_number_improved(self, img, te_numbers_str):
        """
        이미지가 어떤 TE 번호와 관련이 있는지 확인
        """
        te_variants = []
        for te in te_numbers_str:
            te_variants.append(te)
            te_variants.append(te.replace('.', '_'))  # TE02.03.01 -> TE02_03_01
            te_variants.append(te.replace('.', '-'))  # TE02.03.01 -> TE02-03-01
        
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"\n=== TE 번호 매칭 시도: 캡션='{img.get('caption', 'N/A')}', 파일 경로='{img.get('file_path', 'N/A')}' ===")
        
        # 1. 이미지 자체 속성에서 TE 번호 검색
        search_fields = [
            'caption', 'file_path', 'image_id', 'src', 'url', 'alt', 'title',
            'description', 'name', 'filename', 'path', 'table_caption', 'table_id'
        ]
        
        for field in search_fields:
            if field in img and img[field]:
                field_value = str(img[field]).lower()
                for te_variant in te_variants:
                    if te_variant.lower() in field_value:
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"TE 매칭 성공: 필드={field}, 값={field_value}, TE={te_variant}")
                        return te_variant.replace('_', '.').replace('-', '.')  # 원래 TE 형식으로 변환
        
        # 2. Figure 키워드 포함 시 TE 번호 추정
        caption = img.get('caption', '').lower()
        file_path = img.get('file_path', '').lower()
        page_idx = img.get('page_idx', -1)
        
        # 판정근거 페이지 인덱스 확인
        judgment_page_idx = -1
        pages = self.validator.json_data.get("pages", [])
        judgment_pattern = r'판정\s*근거'
        for idx, page in enumerate(pages):
            if page and re.search(judgment_pattern, page.get("text", ""), re.IGNORECASE):
                judgment_page_idx = idx
                break
        
        if page_idx <= judgment_page_idx or judgment_page_idx == -1:
            # 다른 TE 번호가 포함된 경우 제외
            other_te_matches = [m for m in re.findall(r'TE\d+\.\d+\.\d+', caption + " " + file_path) if m not in te_variants]
            if other_te_matches:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"TE 매칭 실패: 다른 TE 번호={other_te_matches}, 캡션={caption}, 파일 경로={file_path}")
                return None
            
            if 'figure' in caption or 'figure' in file_path:
                closest_te = self._find_closest_te_number(img, te_numbers_str)
                if closest_te and closest_te in te_numbers_str:
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"TE 매칭 성공: Figure 기반, 추정된 TE={closest_te}, 캡션={caption}, 파일 경로={file_path}")
                    return closest_te
                else:
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"TE 매칭 실패: Figure 포함 but TE 번호 추정 실패, 캡션={caption}, 파일 경로={file_path}")
        
        # 3. 동일 페이지 및 인접 페이지(±1)에서 TE 번호 검색
        if page_idx != -1:
            pages_to_check = [page_idx]
            if page_idx > 0:
                pages_to_check.append(page_idx - 1)  # 이전 페이지
            if page_idx < len(pages) - 1:
                pages_to_check.append(page_idx + 1)  # 다음 페이지
            
            for check_page_idx in pages_to_check:
                if check_page_idx < len(pages) and check_page_idx <= judgment_page_idx:
                    page = pages[check_page_idx]
                    if page:
                        # 페이지 텍스트에서 TE 번호 검색
                        page_text = page.get("text", "")
                        if page_text:
                            for te_variant in te_variants:
                                if te_variant in page_text:
                                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                        print(f"TE 매칭 성공: 페이지 {check_page_idx} 텍스트, TE={te_variant}")
                                    return te_variant.replace('_', '.').replace('-', '.')
                        
                        # 텍스트 블록에서 TE 번호 검색
                        text_blocks = page.get("text_blocks", [])
                        for text_block in text_blocks:
                            if text_block and 'text' in text_block:
                                block_text = text_block['text']
                                if block_text:
                                    for te_variant in te_variants:
                                        if te_variant in block_text:
                                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                                print(f"TE 매칭 성공: 페이지 {check_page_idx} 텍스트 블록, TE={te_variant}")
                                            return te_variant.replace('_', '.').replace('-', '.')
                        
                        # 테이블에서 TE 번호 검색
                        tables = page.get("tables", [])
                        for table in tables:
                            if table:
                                caption = table.get("caption", "")
                                cells = table.get("cells", [])
                                cell_texts = [cell.get("text", "") for cell in cells if cell and 'text' in cell]
                                
                                for te_variant in te_variants:
                                    if (caption and te_variant in caption) or \
                                    any(te_variant in cell_text for cell_text in cell_texts):
                                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                            print(f"TE 매칭 성공: 페이지 {check_page_idx} 테이블, TE={te_variant}")
                                        return te_variant.replace('_', '.').replace('-', '.')
        
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"TE 매칭 실패: 모든 조건 불만족")
        return None

    def _find_closest_te_number(self, img, te_numbers_str):
        """
        이미지와 가장 가까운 TE 번호를 찾음 (페이지 내 TE 번호 빈도 기반)
        """
        if 'page_idx' not in img:
            return None
        
        page_idx = img['page_idx']
        pages_to_check = [page_idx]
        if page_idx > 0:
            pages_to_check.append(page_idx - 1)
        if page_idx < len(self.validator.json_data.get("pages", [])) - 1:
            pages_to_check.append(page_idx + 1)
        
        te_counts = {te: 0 for te in te_numbers_str}
        
        for check_page_idx in pages_to_check:
            if check_page_idx < len(self.validator.json_data.get("pages", [])):
                page = self.validator.json_data.get("pages", [])[check_page_idx]
                if page:
                    # 페이지 텍스트에서 TE 번호 카운트
                    page_text = page.get("text", "")
                    for te in te_numbers_str:
                        te_variants = [te, te.replace('.', '_'), te.replace('.', '-')]
                        for variant in te_variants:
                            te_counts[te] += page_text.count(variant)
                    
                    # 텍스트 블록에서 TE 번호 카운트
                    for text_block in page.get("text_blocks", []):
                        if text_block and 'text' in text_block:
                            block_text = text_block['text']
                            for te in te_numbers_str:
                                te_variants = [te, te.replace('.', '_'), te.replace('.', '-')]
                                for variant in te_variants:
                                    te_counts[te] += block_text.count(variant)
                    
                    # 테이블에서 TE 번호 카운트
                    for table in page.get("tables", []):
                        caption = table.get("caption", "")
                        cells = table.get("cells", [])
                        cell_texts = [cell.get("text", "") for cell in cells if cell and 'text' in cell]
                        for te in te_numbers_str:
                            te_variants = [te, te.replace('.', '_'), te.replace('.', '-')]
                            for variant in te_variants:
                                if caption:
                                    te_counts[te] += caption.count(variant)
                                for cell_text in cell_texts:
                                    te_counts[te] += cell_text.count(variant)
        
        # 가장 많이 등장한 TE 번호 반환
        if te_counts:
            max_te = max(te_counts, key=te_counts.get)
            if te_counts[max_te] > 0:
                return max_te
        return None
    

    def _generate_image_caption(self, img):
        """
        이미지에 대한 캡션 생성
        """
        te_number = img.get('te_number', '')
        location = img.get('location', '')
        page_idx = img.get('page_idx', 'Unknown')
        
        if 'table' in location:
            return f"{te_number} 테이블 이미지 (페이지 {page_idx + 1})"
        else:
            return f"{te_number} 관련 이미지 (페이지 {page_idx + 1})"

    def _is_test_result_image_strict(self, image_data, test_result_images):
        """
        주어진 이미지가 시험결과판정근거 이미지인지 확인
        """
        if not test_result_images:
            return False
        
        # Figure는 판정근거 표로 간주하지 않음
        caption = image_data.get('caption', '').lower()
        table_caption = image_data.get('table_caption', '').lower()
        
        if 'figure' in caption or 'figure' in table_caption:
            if self.validator.debug_mode:
                print(f"Figure로 식별됨, 판정근거 제외 - 캡션={caption}, 테이블 캡션={table_caption}")
            return False
        
        # "시험결과판정근거" 또는 "Table" 키워드가 포함된 경우만 판정근거로 간주
        judgment_keywords = ['시험결과판정근거', '판정근거', 'judgment', 'result table', 'table']
        
        for keyword in judgment_keywords:
            if keyword in caption or keyword in table_caption:
                if self.validator.debug_mode:
                    print(f"판정근거 키워드 발견: {keyword}, 캡션={caption}, 테이블 캡션={table_caption}")
                return True
        
        # 파일 경로에 판정근거 키워드가 있는 경우
        file_path = image_data.get('file_path', '').lower()
        if file_path:
            for keyword in judgment_keywords:
                if keyword in file_path:
                    if self.validator.debug_mode:
                        print(f"판정근거 키워드 발견: {keyword}, 파일 경로={file_path}")
                    return True
        
        # 이미지 식별자 비교
        image_identifier = self._get_image_identifier(image_data)
        if not image_identifier:
            return False
        
        for test_img in test_result_images:
            test_identifier = self._get_image_identifier(test_img)
            if test_identifier and image_identifier == test_identifier:
                if self.validator.debug_mode:
                    print(f"이미지 식별자 매칭: {image_identifier}")
                return True
        
        return False
    

    def _get_image_identifier(self, img):
        """
        이미지의 고유 식별자를 생성
        """
        if 'base64' in img and img['base64']:
            base64_data = img['base64']
            if base64_data.startswith('data:image'):
                base64_parts = base64_data.split(',', 1)
                if len(base64_parts) > 1:
                    base64_data = base64_parts[1]
            return hashlib.sha256(base64_data.encode()).hexdigest()
        elif 'file_path' in img and img['file_path']:
            return img['file_path']
        elif 'src' in img and img['src']:
            return img['src']
        elif 'url' in img and img['url']:
            return img['url']
        elif 'image_id' in img and img['image_id']:
            return img['image_id']
        
        return None

    # ===== 기존 메소드들 =====

    def _show_image_popup_with_data(self, image_data):
        """
        이미지 데이터를 사용하여 이미지 팝업 표시 (로컬 파일 우선)
        
        Args:
            image_data (dict): 이미지 데이터
        """
        try:
            if not PIL_AVAILABLE:
                messagebox.showwarning(
                    "라이브러리 필요", 
                    "PIL 라이브러리가 설치되지 않아 이미지를 표시할 수 없습니다.\n"
                    "다음 명령으로 설치할 수 있습니다: pip install pillow"
                )
                return
                        
            if image_data:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"이미지 팝업 데이터 키: {list(image_data.keys())}")
                    if 'base64' in image_data:
                        b64_data = image_data['base64']
                        print(f"base64 데이터 시작: {b64_data[:50]}...")
                    if 'file_path' in image_data:
                        print(f"파일 경로: {image_data['file_path']}")
                
                # 로컬 extracted_images 폴더에서 이미지 검색 시도
                enhanced_image_data = self._enhance_image_data_with_local_file(image_data)
                
                title = f"이미지 보기"
                if 'te_number' in enhanced_image_data and enhanced_image_data['te_number']:
                    title = f"{enhanced_image_data['te_number']} 이미지"
                
                if 'caption' in enhanced_image_data and enhanced_image_data['caption']:
                    title = f"{title} - {enhanced_image_data['caption']}"
                
                # ImageViewerPopup 호출
                ImageViewerPopup(self.root, title, enhanced_image_data)
            else:
                messagebox.showinfo(
                    "알림", 
                    "이미지 데이터를 찾을 수 없습니다."
                )
        except Exception as e:
            messagebox.showerror("오류", f"이미지 표시 중 오류 발생: {str(e)}")
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"이미지 표시 중 오류 발생: {str(e)}")
                print(f"이미지 데이터: {image_data}")
                import traceback
                traceback.print_exc()

    def _enhance_image_data_with_local_file(self, image_data):
        """
        이미지 데이터에 로컬 파일 정보를 추가하여 향상된 이미지 데이터 반환
        
        Args:
            image_data (dict): 원본 이미지 데이터
            
        Returns:
            dict: 로컬 파일 정보가 추가된 이미지 데이터
        """
        enhanced_data = image_data.copy()
        
        try:
            # extracted_images 폴더에서 매칭되는 이미지 파일 검색
            local_image_path = self._find_matching_local_image(image_data)
            
            if local_image_path:
                # 로컬 파일 경로를 우선순위로 설정
                enhanced_data['local_file_path'] = local_image_path
                enhanced_data['file_path'] = local_image_path  # ImageViewerPopup에서 우선 사용
                
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"✅ 로컬 이미지 파일 매칭: {os.path.basename(local_image_path)}")
            else:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"❌ 로컬 이미지 파일 매칭 실패, base64 데이터 사용")
        
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"로컬 이미지 검색 중 오류: {str(e)}")
        
        return enhanced_data

    def _find_matching_local_image(self, image_data):
        """
        extracted_images 폴더에서 이미지 데이터와 매칭되는 파일을 검색
        
        Args:
            image_data (dict): 이미지 데이터
            
        Returns:
            str: 매칭된 파일 경로 또는 None
        """
        try:
            # extracted_images 폴더 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_folder = os.path.join(current_dir, "extracted_images")
            
            if not os.path.exists(image_folder):
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"extracted_images 폴더가 존재하지 않음: {image_folder}")
                return None
            
            # 지원되는 이미지 확장자
            supported_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
            
            # 폴더 내 파일 목록 가져오기
            try:
                all_files = [f for f in os.listdir(image_folder) 
                        if any(f.lower().endswith(ext) for ext in supported_extensions)]
            except Exception as e:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"폴더 읽기 오류: {image_folder}, 오류: {str(e)}")
                return None
            
            if not all_files:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"extracted_images 폴더에 이미지 파일이 없음")
                return None
            
            # 이미지 정보 추출
            caption = image_data.get('caption', '').strip()
            te_number = image_data.get('te_number', '')
            page_num = image_data.get('page', image_data.get('page_idx', 'Unknown'))
            image_id = image_data.get('image_id', '')
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"로컬 이미지 검색 정보:")
                print(f"  캡션: '{caption}'")
                print(f"  TE 번호: '{te_number}'")
                print(f"  페이지: {page_num}")
                print(f"  이미지 ID: '{image_id}'")
                print(f"  사용 가능한 파일 수: {len(all_files)}")
            
            # 1단계: 정확한 매칭
            best_match = None
            best_score = 0
            
            for file_name in all_files:
                score = self._calculate_comprehensive_image_match_score(
                    file_name, caption, te_number, page_num, image_id
                )
                
                if score > best_score:
                    best_score = score
                    best_match = file_name
                    
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode and score > 0:
                    print(f"  파일 매칭: {file_name} -> 점수: {score}")
            
            if best_match and best_score > 50:  # 임계값 설정
                matched_path = os.path.join(image_folder, best_match)
                if os.path.exists(matched_path):
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"✅ 최고 점수 매칭: {best_match} (점수: {best_score})")
                    return matched_path
            
            # 2단계: 특정 키워드 기반 매칭
            keyword_matches = self._find_keyword_based_matches(all_files, caption, te_number)
            if keyword_matches:
                first_match = keyword_matches[0]
                matched_path = os.path.join(image_folder, first_match)
                if os.path.exists(matched_path):
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"✅ 키워드 기반 매칭: {first_match}")
                    return matched_path
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"❌ 로컬 이미지 매칭 실패: 적절한 파일을 찾을 수 없음")
            
            return None
            
        except Exception as e:
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"로컬 이미지 검색 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()
            return None


    def _find_keyword_based_matches(self, all_files, caption, te_number):
        """
        키워드 기반으로 매칭되는 파일들을 찾음
        
        Args:
            all_files (list): 모든 파일 목록
            caption (str): 캡션
            te_number (str): TE 번호
            
        Returns:
            list: 매칭된 파일들의 목록
        """
        matches = []
        caption_lower = caption.lower() if caption else ''
        
        # 1. Figure 키워드가 있는 경우
        if 'figure' in caption_lower or 'fig' in caption_lower:
            figure_files = [f for f in all_files if 'figure' in f.lower() or 'fig' in f.lower()]
            matches.extend(figure_files)
        
        # 2. TE 번호가 있는 경우
        if te_number:
            te_variants = [
                te_number.lower(),
                te_number.replace('.', '_').lower(),
                te_number.replace('.', '-').lower()
            ]
            
            for variant in te_variants:
                te_files = [f for f in all_files if variant in f.lower()]
                matches.extend(te_files)
        
        # 3. 중복 제거 및 정렬
        unique_matches = list(set(matches))
        unique_matches.sort()
        
        return unique_matches


    def _calculate_comprehensive_image_match_score(self, filename, caption, te_number, page_num, image_id):
        """
        파일명과 이미지 정보 간의 종합적인 매칭 점수를 계산
        
        Args:
            filename (str): 파일명
            caption (str): 이미지 캡션
            te_number (str): TE 번호
            page_num (str/int): 페이지 번호
            image_id (str): 이미지 ID
            
        Returns:
            int: 매칭 점수 (높을수록 좋은 매칭)
        """
        score = 0
        filename_lower = filename.lower()
        caption_lower = caption.lower() if caption else ''
        
        # 1. TE 번호 매칭 (최고 우선순위, 100점)
        if te_number:
            te_variants = [
                te_number.lower(),
                te_number.replace('.', '_').lower(),
                te_number.replace('.', '-').lower(),
                te_number.replace('te', '').replace('.', '_').lower(),
                te_number.replace('te', '').replace('.', '').lower()
            ]
            
            for te_variant in te_variants:
                if te_variant in filename_lower:
                    score += 100
                    break
        
        # 2. 이미지 ID 매칭 (90점)
        if image_id and image_id.lower() in filename_lower:
            score += 90
        
        # 3. Figure 번호 정확한 매칭 (85점)
        figure_match = re.search(r'figure\s*(\d+)', caption_lower)
        if figure_match:
            fig_num = figure_match.group(1)
            figure_patterns = [
                f'figure{fig_num}',
                f'fig{fig_num}',
                f'figure_{fig_num}',
                f'fig_{fig_num}',
                f'figure-{fig_num}',
                f'fig-{fig_num}'
            ]
            
            for pattern in figure_patterns:
                if pattern in filename_lower:
                    score += 85
                    break
        
        # 4. 페이지 번호 매칭 (70점)
        if page_num and str(page_num) != 'Unknown':
            page_patterns = [
                f'page{page_num}',
                f'p{page_num}',
                f'page_{page_num}',
                f'p_{page_num}',
                f'page-{page_num}',
                f'p-{page_num}',
                f'_{page_num}_',
                f'-{page_num}-'
            ]
            
            for pattern in page_patterns:
                if pattern in filename_lower:
                    score += 70
                    break
        
        # 5. Figure/Fig 키워드 매칭 (60점)
        figure_keywords = ['figure', 'fig']
        for keyword in figure_keywords:
            if keyword in filename_lower and keyword in caption_lower:
                score += 60
                break
        
        # 6. 캡션 주요 단어 매칭 (각각 30점, 최대 90점)
        if caption:
            caption_words = [word for word in caption_lower.split() if len(word) > 3]
            matched_words = 0
            for word in caption_words:
                if word in filename_lower:
                    score += 30
                    matched_words += 1
                    if matched_words >= 3:  # 최대 3개 단어까지만
                        break
        
        # 7. 일반 이미지 키워드 매칭 (20점)
        image_keywords = ['image', 'img', 'picture', 'pic']
        for keyword in image_keywords:
            if keyword in filename_lower:
                score += 20
                break
        
        # 8. 파일 확장자 우선순위 (10점)
        preferred_extensions = ['.png', '.jpg', '.jpeg']
        for ext in preferred_extensions:
            if filename_lower.endswith(ext):
                score += 10
                break
        
        return score


    def _show_test_result_popup(self, te_number):
        """
        시험결과판정근거 표 이미지와 텍스트 내용을 함께 표시하는 팝업
        
        Args:
            te_number (str): TE 번호 (예: "TE02.03.01")
        """
        try:
            if not PIL_AVAILABLE:
                messagebox.showwarning(
                    "라이브러리 필요", 
                    "PIL 라이브러리가 설치되지 않아 테이블 이미지를 표시할 수 없습니다.\n"
                    "다음 명령으로 설치할 수 있습니다: pip install pillow\n"
                    "설치 후 프로그램을 재시작해주세요."
                )
                return
            
            # extracted_table_images 폴더 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_folder = os.path.join(current_dir, "extracted_table_images")
            
            # 폴더가 존재하지 않는 경우 생성
            if not os.path.exists(image_folder):
                try:
                    os.makedirs(image_folder)
                    if self.validator.debug_mode:
                        print(f"폴더 생성됨: {image_folder}")
                except Exception as e:
                    messagebox.showerror(
                        "오류", 
                        f"extracted_table_images 폴더를 생성하는 중 오류 발생: {str(e)}\n"
                        "폴더를 수동으로 생성하고 권한을 확인해주세요."
                    )
                    return
            
            # TE 번호를 파일 이름에 맞게 변환 (예: TE02.03.01 -> TE02_03_01)
            te_number_formatted = te_number.replace(".", "_")
            
            # 디버깅 로그 추가
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"검색 중인 TE 번호: {te_number}, 변환된 형식: {te_number_formatted}")
                print(f"이미지 폴더 경로: {image_folder}")
                print(f"폴더 내 파일 목록: {os.listdir(image_folder)}")
            
            # 이미지 파일 검색
            image_file = None
            supported_extensions = (".png", ".jpg", ".jpeg")
            
            # 파일 이름에서 사용할 패턴 정의 (유연하게 매칭)
            suffix_pattern = r'(시험\s*결과\s*[_]*\s*판정\s*[_]*\s*근거|시험결과[_]*판정[_]*근거)'
            
            # 매칭된 파일 목록 저장
            matching_files = []
            
            # 모든 파일을 검색하여 매칭되는 파일 목록 생성
            for file_name in os.listdir(image_folder):
                file_name_lower = file_name.lower()
                for ext in supported_extensions:
                    # ext 이스케이프 처리
                    escaped_ext = re.escape(ext)
                    # 파일 이름에서 TE 번호 부분 추출
                    pattern = rf'^Table_\d+-\d+_{te_number_formatted}_{suffix_pattern}{escaped_ext}'
                    pattern_no_underscore = rf'^Table_\d+-\d+_{te_number_formatted}{suffix_pattern}{escaped_ext}'
                    
                    if self.validator.debug_mode:
                        print(f"파일 이름: {file_name}")
                        print(f"패턴: {pattern}")
                    
                    if (re.match(pattern, file_name) or re.match(pattern_no_underscore, file_name) or
                        re.match(pattern, file_name_lower) or re.match(pattern_no_underscore, file_name_lower)):
                        full_path = os.path.join(image_folder, file_name)
                        matching_files.append((file_name, full_path))
                        if self.validator.debug_mode:
                            print(f"매칭 성공: {file_name}")
            
            # 디버깅: 매칭된 파일 목록 출력
            if self.validator.debug_mode:
                if matching_files:
                    print("매칭된 파일 목록:")
                    for file_name, full_path in matching_files:
                        print(f"  - {file_name} (경로: {full_path})")
                else:
                    print("매칭된 파일이 없습니다.")
            
            # 매칭된 파일 중 정확한 TE 번호와 일치하는 파일 선택
            if matching_files:
                for file_name, full_path in matching_files:
                    # 파일 이름에서 TE 번호 부분 추출
                    te_match = re.search(r'TE\d+_\d+_\d+', file_name)
                    if te_match:
                        extracted_te = te_match.group()
                        if extracted_te == te_number_formatted:
                            image_file = full_path
                            if self.validator.debug_mode:
                                print(f"선택된 이미지 파일: {image_file} (TE 번호 일치: {extracted_te})")
                            break
            
            # 기존 형식도 지원: [TE 번호]_table.[확장자]
            if not image_file:
                for ext in supported_extensions:
                    potential_file = os.path.join(image_folder, f"{te_number}_table{ext}")
                    potential_file_upper = os.path.join(image_folder, f"{te_number}_table{ext.upper()}")
                    if os.path.exists(potential_file):
                        image_file = potential_file
                        if self.validator.debug_mode:
                            print(f"기존 형식으로 매칭된 이미지 파일: {image_file}")
                        break
                    elif os.path.exists(potential_file_upper):
                        image_file = potential_file_upper
                        if self.validator.debug_mode:
                            print(f"기존 형식(대문자 확장자)으로 매칭된 이미지 파일: {image_file}")
                        break
            
            # 이미지 파일이 없는 경우 validator에서 테이블 이미지 생성 시도
            if not image_file:
                image_data = self.validator.get_test_result_image(te_number)
                if image_data and (image_data.get('image') or image_data.get('base64')):
                    title = f"{te_number} 시험결과판정근거 표"
                    TableImagePopup(
                        self.root, 
                        title, 
                        image_data,
                        validator=self,
                        te_number=te_number
                    )
                    return
                else:
                    messagebox.showinfo(
                        "알림", 
                        f"{te_number}에 해당하는 시험결과판정근거 표 이미지를 찾을 수 없습니다.\n"
                        f"extracted_table_images 폴더에 Table_*_TE{te_number_formatted}_시험결과_판정_근거.[확장자] 또는 {te_number}_table.[확장자] 형식의 파일이 있는지 확인해주세요.\n"
                        f"폴더 경로: {image_folder}"
                    )
                    return
            
            # 이미지 파일 로드 시도
            try:
                with Image.open(image_file) as img:
                    img.verify()  # 이미지 파일이 손상되었는지 확인
                image_data = {
                    "file_path": image_file,
                    "caption": f"{te_number} 시험결과판정근거 표"
                }
                
                # 개선된 팝업 창 표시 - 이미지와 텍스트를 함께 표시
                title = f"{te_number} 시험결과판정근거 표"
                
                # TableImagePopup 호출 시 validator와 te_number 전달
                TableImagePopup(
                    self.root, 
                    title, 
                    image_data,
                    validator=self,
                    te_number=te_number
                )
                
            except Exception as e:
                messagebox.showerror(
                    "오류", 
                    f"이미지 파일을 로드하는 중 오류가 발생했습니다: {str(e)}\n"
                    f"파일 경로: {image_file}\n"
                    "이미지 파일이 손상되었거나 지원되지 않는 형식일 수 있습니다."
                )
                return
            
        except Exception as e:
            messagebox.showerror("오류", f"시험결과판정근거 표 이미지 표시 중 오류 발생: {str(e)}")
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"시험결과판정근거 표 이미지 표시 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()

    def save_results_to_pdf(self):
        """검증 결과를 PDF 문서로 저장"""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        if not self.found_paths and not self.not_found_text.get("1.0", tk.END).strip():
            messagebox.showwarning("알림", "저장할 검증 결과가 없습니다. 먼저 검증을 실행해주세요.")
            return

        pdf_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF 파일", "*.pdf")],
            initialfile="validation_result.pdf"
        )
        if not pdf_path:
            return

        try:
            directory = os.path.dirname(pdf_path)
            if not os.access(directory, os.W_OK):
                messagebox.showerror("오류", f"디렉토리에 쓰기 권한이 없습니다: {directory}\n"
                                            "다른 경로를 선택하거나 디렉토리 권한을 확인해주세요.")
                return

            doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Korean', fontName='MalgunGothic', fontSize=12, leading=14, encoding='utf-8', wordWrap='CJK'))
            styles.add(ParagraphStyle(name='KoreanTitle', fontName='MalgunGothic', fontSize=18, leading=20, encoding='utf-8'))
            styles.add(ParagraphStyle(name='KoreanHeading', fontName='MalgunGothic', fontSize=14, leading=16, encoding='utf-8'))
            styles.add(ParagraphStyle(name='KoreanContent', fontName='MalgunGothic', fontSize=10, leading=12, encoding='utf-8', wordWrap='CJK'))

            # 폰트 파일 동적 검색
            possible_font_paths = [
                r"C:\Windows\Fonts\malgun.ttf",
                r"C:\Windows\Fonts\malgunbd.ttf",
                "/usr/share/fonts/truetype/malgun/malgun.ttf",
                "/usr/share/fonts/noto/NotoSerifCJK-Regular.ttc"
            ]
            font_path = None
            for path in possible_font_paths:
                if os.path.exists(path):
                    font_path = path
                    break
            
            if font_path:
                pdfmetrics.registerFont(TTFont('MalgunGothic', font_path))
            else:
                messagebox.showerror("오류", "맑은 고딕 폰트(malgun.ttf)를 찾을 수 없습니다.\n"
                                            "시스템에 맑은 고딕 또는 Noto Serif CJK 폰트를 설치해주세요.")
                return

            elements = []
            title = "Machine Readable 시험결과보고서 변환 및 판정 검증 결과"
            elements.append(Paragraph(title, styles['KoreanTitle']))
            elements.append(Spacer(1, 0.5*cm))

            date_text = f"날짜: {time.strftime('%Y-%m-%d')}"
            elements.append(Paragraph(date_text, styles['Korean']))
            elements.append(Spacer(1, 1*cm))

            elements.append(Paragraph("검증 요약", styles['KoreanHeading']))
            summary_text = "검증은 JSON 파일과 Config 파일을 사용하여 수행되었습니다."
            elements.append(Paragraph(summary_text, styles['Korean']))

            pdf_file = f"<b>PDF 파일:</b> {self.pdf_file_path.get() or '미지정'}"
            elements.append(Paragraph(json_file, styles['Korean']))
            
            json_file = f"<b>JSON 파일:</b> {self.json_file_path.get() or '미지정'}"
            elements.append(Paragraph(json_file, styles['Korean']))
            
            config_file = f"<b>Config 파일:</b> {self.config_file_path.get() or '미지정'}"
            elements.append(Paragraph(config_file, styles['Korean']))
            
            total_items = len(self.te_numbers) + len(self.not_found_text.get('1.0', tk.END).strip().split('\n')) - 1
            found_count = len(self.found_paths)
            not_found_count = len(self.not_found_text.get('1.0', tk.END).strip().split('\n')) - 1
            summary_stats = f"총 {total_items}개의 항목을 검색하였으며, {found_count}개 발견, {not_found_count}개 누락되었습니다."
            elements.append(Paragraph(summary_stats, styles['Korean']))
            elements.append(Spacer(1, 0.5*cm))

            elements.append(Paragraph("검출 항목", styles['KoreanHeading']))
            for value, paths in self.found_paths.items():
                value_text = f"<b>값:</b> {value}"
                elements.append(Paragraph(value_text, styles['Korean']))
                for path in paths:
                    path_text = f"  - {path}"
                    elements.append(Paragraph(path_text, styles['Korean']))
                if value in self.test_contents:
                    test_content = self.test_contents[value].replace('\n', '<br/>')
                    test_content_text = f"<b>시험내용:</b><br/>{test_content}"
                    elements.append(Paragraph(test_content_text, styles['KoreanContent']))
                elements.append(Spacer(1, 0.5*cm))

            elements.append(Paragraph("누락 항목", styles['KoreanHeading']))
            not_found_items = self.not_found_text.get("1.0", tk.END).strip().split("\n")
            for item in not_found_items:
                if item.strip():
                    value = item.replace("✗ 값 '", "").replace("' 찾을 수 없음", "")
                    item_text = f"- {value}"
                    elements.append(Paragraph(item_text, styles['Korean']))

            doc.build(elements)
            messagebox.showinfo("성공", f"검증 결과가 PDF로 저장되었습니다: {pdf_path}")

        except PermissionError as e:
            messagebox.showerror("오류", f"파일 쓰기 권한 오류: {str(e)}\n"
                                        "PDF 파일이 다른 프로그램에서 열려 있거나 디렉토리에 쓰기 권한이 없습니다.\n"
                                        "파일을 닫고 디렉토리 권한을 확인한 후 다시 시도해주세요.")
        except FileNotFoundError as e:
            messagebox.showerror("오류", f"PDF 저장 중 오류 발생: {str(e)}")
        except Exception as e:
            messagebox.showerror("오류", f"PDF 저장 중 오류 발생: {str(e)}")

    ##여기부터 수정 yj
    def _get_test_requirements_to_judgment(self, te_number):
        """
        TE 번호에 해당하는 '시험요구사항'부터 '판정근거'까지의 텍스트, 표, Figure 데이터를 추출
        항상 3개 요소의 리스트를 반환하도록 보장
        """
        try:
            if not self.validator.json_data:
                return [f"JSON 데이터가 로드되지 않았습니다 (TE: {te_number})", [], []]
            
            text_content = []
            tables_content = []
            figures_content = []
            judgment_pattern = r'판정\s*근거'
            te_variants = [te_number, te_number.replace('.', '_'), te_number.replace('.', '-')]
            other_te_pattern = r'TE\d+\.\d+\.\d+(?<!' + re.escape(te_number) + ')'
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"\n=== _get_test_requirements_to_judgment 호출: TE 번호 = {te_number} ===")
            
            pages = self.validator.json_data.get("pages", [])
            if not pages:
                return [f"{te_number}에 대한 페이지 데이터가 없습니다.", [], []]
            
            # 1단계: 해당 TE 번호가 있는 모든 페이지 찾기
            te_pages = []
            for idx, page in enumerate(pages):
                if page is None:
                    continue
                page_text = page.get("text", "") or ""
                if any(te in page_text for te in te_variants):
                    te_pages.append(idx)
            
            if not te_pages:
                return [f"{te_number}에 대한 페이지를 찾을 수 없습니다.", [], []]
            
            te_start_page = min(te_pages)
            te_end_page = max(te_pages)
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"TE 관련 페이지들: {te_pages}")
                print(f"TE 시작 페이지: {te_start_page}, TE 종료 페이지: {te_end_page}")
            
            # 2단계: 판정근거 페이지 찾기
            judgment_page_idx = -1
            for idx in range(te_start_page, len(pages)):
                page = pages[idx]
                if page is None:
                    continue
                
                page_text = page.get("text", "") or ""
                other_te_matches = re.findall(other_te_pattern, page_text)
                if other_te_matches and idx > te_end_page:
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"다른 TE 번호 발견으로 검색 중단: 페이지 {idx}, TE={other_te_matches}")
                    break
                
                if re.search(judgment_pattern, page_text, re.IGNORECASE):
                    if any(te in page_text for te in te_variants) or idx <= te_end_page + 2:
                        judgment_page_idx = idx
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"판정근거 페이지 발견: {judgment_page_idx}")
                        break
            
            if judgment_page_idx == -1:
                judgment_page_idx = min(te_end_page + 5, len(pages) - 1)
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"판정근거 페이지를 찾지 못함, 확장된 종료 페이지: {judgment_page_idx}")
            
            # 3단계: 데이터 수집 - 더 포괄적인 조건 적용
            pages_to_check = range(te_start_page, min(judgment_page_idx + 1, len(pages)))
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"최종 검색 페이지 범위: {te_start_page}부터 {judgment_page_idx}")
            
            for page_idx in pages_to_check:
                if page_idx >= len(pages):
                    break
                page = pages[page_idx]
                if not page:
                    continue
                    
                page_number = page.get("page_number", f"Unknown_{page_idx}")
                
                # 4단계: 페이지 텍스트 수집
                page_text = page.get("text", "") or ""
                if page_text:
                    should_include_page_text = False
                    
                    # 조건 1: TE 페이지 범위 내의 모든 텍스트
                    if te_start_page <= page_idx <= te_end_page:
                        should_include_page_text = True
                        inclusion_reason = "TE 페이지 범위 내"
                    
                    # 조건 2: 현재 TE 번호가 포함된 텍스트
                    elif any(te in page_text for te in te_variants):
                        should_include_page_text = True
                        inclusion_reason = "TE 번호 포함"
                    
                    # 조건 3: 시험요구사항이 포함된 텍스트
                    elif '시험요구사항' in page_text.lower():
                        should_include_page_text = True
                        inclusion_reason = "시험요구사항 포함"
                    
                    # 조건 4: TE 범위에서 +/- 1 페이지까지 확장
                    elif (te_start_page - 1) <= page_idx <= (judgment_page_idx):
                        # 다른 TE 번호가 단독으로 나타나지 않는 경우에만 포함
                        other_te_matches = [m for m in re.findall(other_te_pattern, page_text) if m not in te_variants]
                        if not other_te_matches:
                            should_include_page_text = True
                            inclusion_reason = "TE 확장 범위 내"
                    
                    if should_include_page_text:
                        # 판정근거 페이지의 경우 판정근거 관련 텍스트만 추출
                        if page_idx == judgment_page_idx and re.search(judgment_pattern, page_text, re.IGNORECASE):
                            judgment_lines = []
                            lines = page_text.split('\n')
                            in_judgment_section = False
                            
                            for line in lines:
                                line = line.strip()
                                if re.search(judgment_pattern, line, re.IGNORECASE):
                                    in_judgment_section = True
                                    judgment_lines.append(line)
                                elif in_judgment_section:
                                    if re.match(r'^\d+\.\d+\.\d+\s+', line):  # 다른 섹션 시작
                                        break
                                    if line:
                                        judgment_lines.append(line)
                            
                            if judgment_lines:
                                text_content.append({
                                    "page_number": page_number,
                                    "text": "\n".join(judgment_lines)
                                })
                                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                    print(f"페이지 텍스트 추가: 페이지 {page_number}, 판정근거 텍스트, 이유={inclusion_reason}")
                        else:
                            # 일반 페이지는 전체 텍스트 포함
                            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                            if lines:
                                text_content.append({
                                    "page_number": page_number,
                                    "text": "\n".join(lines)
                                })
                                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                    print(f"페이지 텍스트 추가: 페이지 {page_number}, 전체 텍스트, 이유={inclusion_reason}")
                    else:
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"페이지 텍스트 제외: 페이지 {page_number}, 포함 조건 불만족")
                
                # 5단계: 표 처리
                for table in page.get("tables", []):
                    if table is None:
                        continue
                    
                    caption_raw = table.get("caption")
                    caption = str(caption_raw or "").strip()
                    cells = table.get("cells", [])
                    is_judgment_table = any(keyword in caption.lower() for keyword in ['판정근거', '시험결과판정근거'])
                    is_requirement_table = '시험요구사항' in caption.lower()
                    
                    other_te_matches = [m for m in re.findall(other_te_pattern, caption) if m not in te_variants]
                    cell_texts = []
                    for cell in cells:
                        if cell and 'text' in cell:
                            cell_text = str(cell.get("text") or "")
                            cell_texts.append(cell_text)
                            other_te_matches.extend([m for m in re.findall(other_te_pattern, cell_text) if m not in te_variants])
                    
                    include_table = True
                    if other_te_matches:
                        current_te_in_table = (any(te in caption for te in te_variants) or 
                                            any(any(te in cell_text for te in te_variants) for cell_text in cell_texts))
                        if not current_te_in_table:
                            include_table = False
                    
                    if include_table:
                        should_include = False
                        
                        if any(te in caption for te in te_variants):
                            should_include = True
                            inclusion_reason = f"캡션에 TE 번호 포함"
                        elif page_idx <= judgment_page_idx and is_judgment_table:
                            should_include = True
                            inclusion_reason = f"판정근거 테이블"
                        elif page_idx in te_pages and not is_requirement_table:
                            should_include = True
                            inclusion_reason = f"TE 페이지 내 테이블"
                        elif te_start_page <= page_idx <= judgment_page_idx and not is_requirement_table:
                            should_include = True
                            inclusion_reason = f"TE 범위 내 테이블"
                        elif any(any(te in cell_text for te in te_variants) for cell_text in cell_texts):
                            should_include = True
                            inclusion_reason = f"셀에 TE 번호 포함"
                        
                        if should_include:
                            table_data = {"page": page_number, "caption": caption, "cells": cells}
                            tables_content.append(table_data)
                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                print(f"표 추가: 페이지 {page_number}, 캡션='{caption[:50]}...', 이유={inclusion_reason}")
                
                # 6단계: Figure 처리
                for image in page.get("images", []):
                    if image is None:
                        continue
                    
                    caption_raw = image.get("caption")
                    caption = str(caption_raw or "").strip()
                    file_path_raw = image.get("file_path")
                    file_path = str(file_path_raw or "").lower()
                    
                    is_figure_match = (
                        any(te in caption for te in te_variants) or 
                        any(te in file_path for te in te_variants) or
                        (page_idx >= te_start_page and page_idx <= judgment_page_idx and 'figure' in caption.lower()) or
                        (page_idx >= te_start_page and page_idx <= judgment_page_idx and 'figure' in file_path) or
                        (page_idx in te_pages and ('figure' in caption.lower() or 'figure' in file_path))
                    )
                    
                    other_te_matches = [m for m in re.findall(other_te_pattern, caption + " " + file_path) if m not in te_variants]
                    include_figure = True
                    
                    if other_te_matches:
                        current_te_in_figure = (any(te in caption for te in te_variants) or 
                                            any(te in file_path for te in te_variants))
                        if not current_te_in_figure:
                            include_figure = False
                    
                    if include_figure and is_figure_match:
                        if self._is_test_result_image_strict(image, []):
                            continue
                        
                        figure_data = {
                            "page": page_number,
                            "caption": caption,
                            "image_id": image.get("image_id", "N/A"),
                            "page_idx": page_idx,
                            "image_idx": page.get("images", []).index(image),
                        }
                        
                        image_data_fields = [
                            'base64', 'file_path', 'src', 'url', 'path', 'filename', 
                            'image_data', 'data', 'content', 'binary_data'
                        ]
                        
                        for field in image_data_fields:
                            if field in image and image[field]:
                                figure_data[field] = image[field]
                        
                        if not caption:
                            figure_data["caption"] = self._generate_image_caption(figure_data)
                        
                        figures_content.append(figure_data)
                        
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"Figure 추가: 페이지 {page_number}, 캡션='{caption}', 파일 경로='{file_path}'")
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"\n=== 수집된 데이터 요약 ===")
                print(f"텍스트 섹션: {len(text_content)}개")
                print(f"테이블: {len(tables_content)}개")
                print(f"Figure: {len(figures_content)}개")
            
            return [text_content, tables_content, figures_content]
            
        except Exception as e:
            error_msg = f"{te_number} 데이터 추출 중 오류 발생: {str(e)}"
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"_get_test_requirements_to_judgment 오류: {str(e)}")
                import traceback
                traceback.print_exc()
            return [error_msg, [], []]
    ##여기까지

    def _get_test_requirements_to_judgment2(self, te_number): ##기존코드 삭제 
        """
        TE 번호에 해당하는 '시험요구사항'부터 '판정근거'까지의 텍스트, 표, Figure 데이터를 추출
        항상 3개 요소의 리스트를 반환하도록 보장
        
        Args:
            te_number (str): TE 번호 (예: "TE02.03.01")
        
        Returns:
            list: [텍스트 섹션, 표 데이터 리스트, Figure 데이터 리스트]
        """
        try:
            if not self.validator.json_data:
                return [f"JSON 데이터가 로드되지 않았습니다 (TE: {te_number})", [], []]
            
            text_content = []
            tables_content = []
            figures_content = []
            judgment_pattern = r'판정\s*근거'
            te_variants = [te_number, te_number.replace('.', '_'), te_number.replace('.', '-')]
            other_te_pattern = r'TE\d+\.\d+\.\d+(?<!' + re.escape(te_number) + ')'  # 현재 TE 번호 제외
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"\n=== _get_test_requirements_to_judgment 호출: TE 번호 = {te_number} ===")
            
            pages = self.validator.json_data.get("pages", [])
            if not pages:
                return [f"{te_number}에 대한 페이지 데이터가 없습니다.", [], []]
            
            # 1단계: 해당 TE 번호가 있는 모든 페이지 찾기
            te_pages = []
            for idx, page in enumerate(pages):
                if page is None:
                    continue
                page_text = page.get("text", "")
                if any(te in page_text for te in te_variants):
                    te_pages.append(idx)
            
            if not te_pages:
                return [f"{te_number}에 대한 페이지를 찾을 수 없습니다.", [], []]
            
            te_start_page = min(te_pages)
            te_end_page = max(te_pages)
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"TE 관련 페이지들: {te_pages}")
                print(f"TE 시작 페이지: {te_start_page}, TE 종료 페이지: {te_end_page}")
            
            # 2단계: TE 페이지 이후에서 해당 TE와 관련된 판정근거 페이지 찾기
            judgment_page_idx = -1
            
            # TE 페이지부터 문서 끝까지 검색하되, 다른 TE가 나타나기 전까지만
            for idx in range(te_start_page, len(pages)):
                page = pages[idx]
                if page is None:
                    continue
                
                page_text = page.get("text", "")
                
                # 다른 TE 번호가 나타나면 검색 중단 (현재 TE 제외)
                other_te_matches = re.findall(other_te_pattern, page_text)
                if other_te_matches and idx > te_end_page:
                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                        print(f"다른 TE 번호 발견으로 검색 중단: 페이지 {idx}, TE={other_te_matches}")
                    break
                
                # 판정근거 패턴 검색
                if re.search(judgment_pattern, page_text, re.IGNORECASE):
                    # 해당 TE와 관련된 판정근거인지 확인
                    if any(te in page_text for te in te_variants) or idx <= te_end_page + 2:  # TE 페이지 + 여유분 2페이지
                        judgment_page_idx = idx
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"판정근거 페이지 발견: {judgment_page_idx}")
                        break
            
            # 판정근거 페이지가 없으면 TE 종료 페이지 + 5페이지까지 확장
            if judgment_page_idx == -1:
                judgment_page_idx = min(te_end_page + 5, len(pages) - 1)
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"판정근거 페이지를 찾지 못함, 확장된 종료 페이지: {judgment_page_idx}")
            
            # 3단계: TE 시작 페이지부터 판정근거 페이지까지 데이터 수집
            pages_to_check = range(te_start_page, min(judgment_page_idx + 1, len(pages)))
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"최종 검색 페이지 범위: {te_start_page}부터 {judgment_page_idx} (총 {len(list(pages_to_check))}개 페이지)")
            
            for page_idx in pages_to_check:
                if page_idx >= len(pages):
                    break
                page = pages[page_idx]
                if not page:
                    continue
                    
                page_number = page.get("page_number", f"Unknown_{page_idx}")
                
                # 4단계: 페이지 텍스트 수집
                page_text = page.get("text", "")
                if page_text:
                    # 다른 TE 번호가 포함된 경우 제외 (현재 TE는 허용)
                    other_te_matches = [m for m in re.findall(other_te_pattern, page_text) if m not in te_variants]
                    include_text = True
                    
                    if other_te_matches and page_idx != te_start_page:
                        # 현재 TE도 함께 포함된 경우는 허용
                        current_te_in_text = any(te in page_text for te in te_variants)
                        if not current_te_in_text:
                            include_text = False
                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                print(f"페이지 텍스트 제외: 페이지 {page_number}, 다른 TE 번호={other_te_matches}")
                    
                    if include_text:
                        if page_idx < judgment_page_idx or (page_idx == judgment_page_idx and not re.search(judgment_pattern, page_text, re.IGNORECASE)):
                            if any(te in page_text for te in te_variants) or '시험요구사항' in page_text.lower() or page_idx in te_pages:
                                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                                if lines:
                                    text_content.append(("페이지 텍스트", page_number, "\n".join(lines)))
                                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                        print(f"텍스트 추가: 페이지 {page_number}, 내용='{lines[0][:50]}...'")
                        elif page_idx == judgment_page_idx:
                            lines = [line.strip() for line in page_text.split('\n') if line.strip() and re.search(judgment_pattern, line, re.IGNORECASE)]
                            if lines:
                                text_content.append(("페이지 텍스트", page_number, "\n".join(lines)))
                                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                    print(f"텍스트 추가: 페이지 {page_number}, 판정근거 관련 내용='{lines[0][:50]}...'")
                
                # 5단계: 텍스트 블록 수집
                for text_block in page.get("text_blocks", []):
                    if text_block and 'text' in text_block:
                        text = text_block['text'].strip()
                        if text:
                            other_te_matches = [m for m in re.findall(other_te_pattern, text) if m not in te_variants]
                            include_block = True
                            
                            if other_te_matches and page_idx != te_start_page:
                                current_te_in_block = any(te in text for te in te_variants)
                                if not current_te_in_block:
                                    include_block = False
                                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                        print(f"텍스트 블록 제외: 페이지 {page_number}, 다른 TE 번호={other_te_matches}")
                            
                            if include_block:
                                if page_idx < judgment_page_idx or (page_idx == judgment_page_idx and not re.search(judgment_pattern, text, re.IGNORECASE)):
                                    if any(te in text for te in te_variants) or '시험요구사항' in text.lower() or page_idx in te_pages:
                                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                                        if lines:
                                            text_content.append(("텍스트 블록", page_number, "\n".join(lines)))
                                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                                print(f"텍스트 블록 추가: 페이지 {page_number}, 내용='{lines[0][:50]}...'")
                                elif page_idx == judgment_page_idx:
                                    if re.search(judgment_pattern, text, re.IGNORECASE):
                                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                                        if lines:
                                            text_content.append(("텍스트 블록", page_number, "\n".join(lines)))
                                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                                print(f"텍스트 블록 추가: 페이지 {page_number}, 판정근거 관련 내용='{lines[0][:50]}...'")
                
                # 6단계: 표 처리
                for table in page.get("tables", []):
                    if table is None:
                        continue
                    caption = table.get("caption", "").strip()
                    cells = table.get("cells", [])
                    is_judgment_table = any(keyword in caption.lower() for keyword in ['판정근거', '시험결과판정근거'])
                    is_requirement_table = '시험요구사항' in caption.lower()
                    
                    # 다른 TE 번호가 포함된 경우 제외
                    other_te_matches = [m for m in re.findall(other_te_pattern, caption) if m not in te_variants]
                    cell_texts = [cell.get("text", "") for cell in cells if cell and 'text' in cell]
                    for cell_text in cell_texts:
                        other_te_matches.extend([m for m in re.findall(other_te_pattern, cell_text) if m not in te_variants])
                    
                    include_table = True
                    if other_te_matches:
                        # 현재 TE도 함께 포함된 경우는 허용
                        current_te_in_table = (any(te in caption for te in te_variants) or 
                                            any(any(te in cell_text for te in te_variants) for cell_text in cell_texts))
                        if not current_te_in_table:
                            include_table = False
                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                print(f"표 제외: 페이지 {page_number}, 캡션='{caption[:50]}...', 다른 TE 번호={other_te_matches}")
                    
                    if include_table:
                        # 테이블 포함 조건을 더 포괄적으로 수정
                        should_include = False
                        
                        # 1. 테이블 캡션에 현재 TE 번호가 포함된 경우
                        if any(te in caption for te in te_variants):
                            should_include = True
                            inclusion_reason = f"캡션에 TE 번호 포함"
                        
                        # 2. 판정근거 테이블인 경우 (판정근거 페이지 이전까지)
                        elif page_idx <= judgment_page_idx and is_judgment_table:
                            should_include = True
                            inclusion_reason = f"판정근거 테이블"
                        
                        # 3. TE 페이지에 있는 테이블 (시험요구사항 테이블 제외)
                        elif page_idx in te_pages and not is_requirement_table:
                            should_include = True
                            inclusion_reason = f"TE 페이지 내 테이블"
                        
                        # 4. TE 시작 페이지와 판정근거 페이지 사이의 모든 테이블 (시험요구사항 제외)
                        elif te_start_page <= page_idx <= judgment_page_idx and not is_requirement_table:
                            should_include = True
                            inclusion_reason = f"TE 범위 내 테이블"
                        
                        # 5. 테이블 셀에 현재 TE 번호가 포함된 경우
                        elif any(any(te in cell_text for te in te_variants) for cell_text in cell_texts):
                            should_include = True
                            inclusion_reason = f"셀에 TE 번호 포함"
                        
                        if should_include:
                            table_data = {"page": page_number, "caption": caption, "cells": cells}
                            tables_content.append(table_data)
                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                print(f"표 추가: 페이지 {page_number}, 캡션='{caption[:50]}...', 이유={inclusion_reason}")
                        else:
                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                print(f"표 제외: 페이지 {page_number}, 캡션='{caption[:50]}...', 이유={'시험요구사항' if is_requirement_table else '포함 조건 불만족'}")
                
                # 7단계: Figure 처리
                for image in page.get("images", []):
                    if image is None:
                        continue
                    
                    caption = image.get("caption", "").strip()
                    file_path = str(image.get("file_path", "")).lower()
                    
                    # Figure 매칭 조건 개선
                    is_figure_match = (
                        any(te in caption for te in te_variants) or 
                        any(te in file_path for te in te_variants) or
                        (page_idx >= te_start_page and page_idx <= judgment_page_idx and 'figure' in caption.lower()) or
                        (page_idx >= te_start_page and page_idx <= judgment_page_idx and 'figure' in file_path) or
                        (page_idx in te_pages and ('figure' in caption.lower() or 'figure' in file_path))
                    )
                    
                    # 다른 TE 번호가 포함된 경우 제외
                    other_te_matches = [m for m in re.findall(other_te_pattern, caption + " " + file_path) if m not in te_variants]
                    include_figure = True
                    
                    if other_te_matches:
                        # 현재 TE도 함께 포함된 경우는 허용
                        current_te_in_figure = (any(te in caption for te in te_variants) or 
                                            any(te in file_path for te in te_variants))
                        if not current_te_in_figure:
                            include_figure = False
                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                print(f"Figure 제외: 페이지 {page_number}, 캡션='{caption}', 파일 경로='{file_path}', 다른 TE 번호={other_te_matches}")
                    
                    if include_figure and is_figure_match:
                        # 판정근거 표로 잘못 분류되지 않도록 확인
                        if self._is_test_result_image_strict(image, []):
                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                print(f"Figure 제외: 페이지 {page_number}, 캡션='{caption}', 파일 경로='{file_path}', 이유=판정근거 표")
                            continue
                        
                        figure_data = {
                            "page": page_number,
                            "caption": caption,
                            "image_id": image.get("image_id", "N/A"),
                            "page_idx": page_idx,
                            "image_idx": page.get("images", []).index(image),
                        }
                        
                        # 모든 가능한 이미지 데이터 속성 복사
                        image_data_fields = [
                            'base64', 'file_path', 'src', 'url', 'path', 'filename', 
                            'image_data', 'data', 'content', 'binary_data'
                        ]
                        
                        for field in image_data_fields:
                            if field in image and image[field]:
                                figure_data[field] = image[field]
                        
                        # 캡션이 없으면 동적으로 생성
                        if not caption:
                            figure_data["caption"] = self._generate_image_caption(figure_data)
                        
                        figures_content.append(figure_data)
                        
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"Figure 추가: 페이지 {page_number}, 캡션='{caption}', 파일 경로='{file_path}', 매칭 조건={is_figure_match}")
                            print(f"  사용 가능한 속성: {[k for k in image.keys() if image.get(k)]}")
                            print(f"  복사된 속성: {[k for k in figure_data.keys() if k not in ['page', 'caption', 'image_id', 'page_idx', 'image_idx']]}")
                    else:
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"Figure 제외: 페이지 {page_number}, 캡션='{caption}', 파일 경로='{file_path}', 매칭 조건={is_figure_match}, 포함 여부={include_figure}")
            
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"\n=== 수집된 데이터 요약 ===")
                print(f"텍스트 섹션: {len(text_content)}개")
                print(f"테이블: {len(tables_content)}개")
                print(f"Figure: {len(figures_content)}개")
                for i, fig in enumerate(figures_content):
                    print(f"  Figure {i+1}: 페이지 {fig['page']}, 캡션='{fig['caption'][:50]}...', 파일 경로='{fig.get('file_path', 'N/A')}'")
            
            return [text_content, tables_content, figures_content]
            
        except Exception as e:
            error_msg = f"{te_number} 데이터 추출 중 오류 발생: {str(e)}"
            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                print(f"_get_test_requirements_to_judgment 오류: {str(e)}")
                import traceback
                traceback.print_exc()
            return [error_msg, [], []]

    def _find_related_te_number_improved(self, img, te_numbers_str):
        """
        이미지가 어떤 TE 번호와 관련이 있는지 확인
        """
        te_variants = []
        for te in te_numbers_str:
            te_variants.append(te)
            te_variants.append(te.replace('.', '_'))  # TE02.03.01 -> TE02_03_01
            te_variants.append(te.replace('.', '-'))  # TE02.03.01 -> TE02-03-01
        
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"\n=== TE 번호 매칭 시도: 캡션='{img.get('caption', 'N/A')}', 파일 경로='{img.get('file_path', 'N/A')}' ===")
        
        # 1. 이미지 자체 속성에서 TE 번호 검색
        search_fields = [
            'caption', 'file_path', 'image_id', 'src', 'url', 'alt', 'title',
            'description', 'name', 'filename', 'path', 'table_caption', 'table_id'
        ]
        
        for field in search_fields:
            if field in img and img[field]:
                field_value = str(img[field]).lower()
                for te_variant in te_variants:
                    if te_variant.lower() in field_value:
                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                            print(f"TE 매칭 성공: 필드={field}, 값={field_value}, TE={te_variant}")
                        return te_variant.replace('_', '.').replace('-', '.')  # 원래 TE 형식으로 변환
        
        # 2. Figure 키워드 포함 시 TE 번호 추정
        caption = img.get('caption', '').lower()
        file_path = img.get('file_path', '').lower()
        if 'figure' in caption or 'figure' in file_path:
            closest_te = self._find_closest_te_number(img, te_numbers_str)
            if closest_te:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"TE 매칭 성공: Figure 기반, 추정된 TE={closest_te}, 캡션={caption}, 파일 경로={file_path}")
                return closest_te
            else:
                if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                    print(f"TE 매칭 실패: Figure 포함 but TE 번호 추정 실패, 캡션={caption}, 파일 경로={file_path}")
                return None
        
        # 3. 동일 페이지 및 인접 페이지(±1)에서 TE 번호 검색
        if 'page_idx' in img:
            page_idx = img['page_idx']
            pages_to_check = [page_idx]
            if page_idx > 0:
                pages_to_check.append(page_idx - 1)  # 이전 페이지
            if page_idx < len(self.validator.json_data.get("pages", [])) - 1:
                pages_to_check.append(page_idx + 1)  # 다음 페이지
            
            for check_page_idx in pages_to_check:
                if check_page_idx < len(self.validator.json_data.get("pages", [])):
                    page = self.validator.json_data.get("pages", [])[check_page_idx]
                    
                    if page:
                        # 페이지 텍스트에서 TE 번호 검색
                        page_text = page.get("text", "")
                        if page_text:
                            for te_variant in te_variants:
                                if te_variant in page_text:
                                    if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                        print(f"TE 매칭 성공: 페이지 {check_page_idx} 텍스트, TE={te_variant}")
                                    return te_variant.replace('_', '.').replace('-', '.')
                        
                        # 텍스트 블록에서 TE 번호 검색
                        text_blocks = page.get("text_blocks", [])
                        for text_block in text_blocks:
                            if text_block and 'text' in text_block:
                                block_text = text_block['text']
                                if block_text:
                                    for te_variant in te_variants:
                                        if te_variant in block_text:
                                            if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                                print(f"TE 매칭 성공: 페이지 {check_page_idx} 텍스트 블록, TE={te_variant}")
                                            return te_variant.replace('_', '.').replace('-', '.')
                        
                        # 테이블에서 TE 번호 검색
                        tables = page.get("tables", [])
                        for table in tables:
                            if table:
                                caption = table.get("caption", "")
                                cells = table.get("cells", [])
                                cell_texts = [cell.get("text", "") for cell in cells if cell and 'text' in cell]
                                
                                for te_variant in te_variants:
                                    if (caption and te_variant in caption) or \
                                    any(te_variant in cell_text for cell_text in cell_texts):
                                        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
                                            print(f"TE 매칭 성공: 페이지 {check_page_idx} 테이블, TE={te_variant}")
                                        return te_variant.replace('_', '.').replace('-', '.')
        
        if hasattr(self.validator, 'debug_mode') and self.validator.debug_mode:
            print(f"TE 매칭 실패: 모든 조건 불만족")
        return None

    def debug_figure_data(self, te_number):
        """
        JSONValidatorGUI 클래스에 추가할 Figure 디버깅 메서드
        """
        if not self.validator or not self.validator.json_data:
            print("JSON 데이터가 로드되지 않았습니다.")
            messagebox.showinfo("디버깅", "JSON 데이터가 로드되지 않았습니다.")
            return
        
        print(f"\n=== {te_number} Figure 데이터 디버깅 ===")
        
        te_variants = [te_number, te_number.replace('.', '_'), te_number.replace('.', '-')]
        found_images = []
        debug_info = []
        
        for page_idx, page in enumerate(self.validator.json_data.get("pages", [])):
            if page is None:
                continue
            
            page_number = page.get("page_number", f"Unknown_{page_idx}")
            page_text = page.get("text", "")
            
            # TE 번호가 페이지에 있는지 확인
            has_te = any(te in page_text for te in te_variants)
            
            images = page.get("images", [])
            if images:
                page_info = f"페이지 {page_number}: TE 포함={has_te}, 이미지 {len(images)}개"
                debug_info.append(page_info)
                print(page_info)
                
                for img_idx, image in enumerate(images):
                    if image is None:
                        continue
                    
                    caption = image.get("caption", "").strip()
                    is_figure = 'figure' in caption.lower()
                    is_te_match = any(te in caption for te in te_variants)
                    is_figure_match = is_figure and (has_te or is_te_match)
                    
                    img_info = f"  이미지 {img_idx}: '{caption}' (Figure={is_figure}, 매칭={is_figure_match})"
                    debug_info.append(img_info)
                    print(img_info)
                    
                    if is_figure_match:
                        found_images.append({
                            'page': page_number,
                            'caption': caption,
                            'has_base64': bool(image.get('base64')),
                            'has_file_path': bool(image.get('file_path')),
                            'available_keys': list(image.keys())
                        })
        
        summary = f"\n총 {len(found_images)}개의 Figure 이미지 발견"
        debug_info.append(summary)
        print(summary)
        
        for i, img in enumerate(found_images):
            img_summary = f"{i+1}. 페이지 {img['page']}: '{img['caption'][:50]}...'"
            img_summary += f" (base64={img['has_base64']}, file_path={img['has_file_path']})"
            debug_info.append(img_summary)
            print(img_summary)
        
        # 결과를 메시지박스로도 표시
        debug_text = "\n".join(debug_info[-10:])  # 마지막 10줄만 표시
        messagebox.showinfo(f"{te_number} Figure 디버깅 결과", debug_text)


    def check_extracted_images_folder(self):
        """
        JSONValidatorGUI 클래스에 추가할 폴더 확인 메서드
        """
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted_table_images")
        
        info_lines = []
        info_lines.append(f"폴더 경로: {output_dir}")
        info_lines.append(f"폴더 존재: {os.path.exists(output_dir)}")
        
        if not os.path.exists(output_dir):
            info_text = "\n".join(info_lines)
            messagebox.showinfo("폴더 확인", info_text)
            return
        
        try:
            all_files = os.listdir(output_dir)
            image_files = [f for f in all_files 
                        if any(f.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif'])]
            
            info_lines.append(f"전체 파일 수: {len(all_files)}")
            info_lines.append(f"이미지 파일 수: {len(image_files)}")
            
            # Figure 관련 파일들 찾기
            figure_files = [f for f in image_files if 'figure' in f.lower() or 'fig' in f.lower()]
            page_files = [f for f in image_files if 'page' in f.lower()]
            
            info_lines.append(f"Figure 관련 파일: {len(figure_files)}개")
            info_lines.append(f"페이지 관련 파일: {len(page_files)}개")
            
            if figure_files:
                info_lines.append("\nFigure 파일들:")
                for filename in sorted(figure_files)[:5]:  # 최대 5개만 표시
                    info_lines.append(f"  {filename}")
                if len(figure_files) > 5:
                    info_lines.append(f"  ... 및 {len(figure_files) - 5}개 더")
            
            info_text = "\n".join(info_lines)
            messagebox.showinfo("이미지 폴더 확인", info_text)
            
            # 콘솔에도 상세 정보 출력
            print("\n".join(info_lines))
            
        except Exception as e:
            error_msg = f"폴더 읽기 오류: {str(e)}"
            messagebox.showerror("오류", error_msg)
            print(error_msg)

    def create_debug_button(self):
        """
        디버깅을 위한 버튼을 추가하는 메서드 (JSONValidatorGUI 클래스에 추가)
        """
        if hasattr(self, 'te_numbers') and self.te_numbers:
            debug_frame = tk.Frame(self.buttons_frame, bg="#f5f5f5")
            debug_frame.pack(fill=tk.X, pady=(10, 5))
            
            debug_label = tk.Label(
                debug_frame,
                text="디버깅 도구:",
                font=("Arial", 10, "bold"),
                bg="#f5f5f5"
            )
            debug_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Figure 데이터 디버깅 버튼
            for te_number in self.te_numbers:
                debug_btn = tk.Button(
                    debug_frame,
                    text=f"{te_number} Figure 디버그",
                    command=lambda tn=te_number: self.debug_figure_data(tn),
                    bg="#ffeecc",
                    padx=3,
                    pady=1,
                    font=("Arial", 8)
                )
                debug_btn.pack(side=tk.LEFT, padx=2)
            
            # 폴더 확인 버튼
            folder_btn = tk.Button(
                debug_frame,
                text="이미지 폴더 확인",
                command=self.check_extracted_images_folder,
                bg="#ccffcc",
                padx=3,
                pady=1,
                font=("Arial", 8)
            )
            folder_btn.pack(side=tk.LEFT, padx=2)

class ImageViewerPopup:
    """이미지를 표시하는 팝업 창 (캡션 표시 기능 추가, 로컬 파일 우선 로드)"""
    
    def __init__(self, parent, title, image_data):
        """
        팝업 창 초기화
        
        Args:
            parent (tk.Tk): 부모 창
            title (str): 팝업 창 제목
            image_data (dict): 이미지 데이터 (base64 또는 경로)
        """
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        self.top.grab_set()
        
        # 이미지 데이터 저장 (캡션 표시용)
        self.image_data = image_data
        
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        position_right = int(screen_width/2 - window_width/2)
        position_down = int(screen_height/2 - window_height/2)
        
        self.top.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")
        
        self.original_image = None
        self.photo = None
        self.image_id = None
        self.zoom_level = 1.0
        
        self._create_image_view(image_data)
        self._create_close_button()
    
    def _create_image_view(self, image_data):
        """
        이미지 뷰 생성 (캡션 표시 기능 추가)
        
        Args:
            image_data (dict): 이미지 데이터 (base64 또는 경로)
        """
        main_frame = tk.Frame(self.top)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 캡션 표시 영역 추가 (이미지 위쪽)
        caption_frame = tk.Frame(main_frame)
        caption_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 캡션 라벨 생성
        self.caption_label = tk.Label(
            caption_frame, 
            text="",
            font=("Arial", 12, "bold"),
            fg="#2E86AB",
            bg="#F8F9FA",
            relief=tk.RIDGE,
            bd=2,
            wraplength=800,  # 긴 캡션 줄바꿈 (고정값 사용)
            justify=tk.LEFT,
            anchor="w"
        )
        
        # 이미지 캔버스 프레임
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        
        self.canvas = tk.Canvas(
            canvas_frame, 
            bg='white',
            xscrollcommand=h_scrollbar.set, 
            yscrollcommand=v_scrollbar.set
        )
        
        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)
        
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._display_image_and_caption(image_data)
    
    def _display_image_and_caption(self, image_data):
        """
        이미지와 캡션을 함께 표시
        
        Args:
            image_data (dict): 이미지 데이터
        """
        # 캡션 표시
        self._display_caption(image_data)
        
        # 이미지 표시
        self._display_image(image_data)
    
    def _display_caption(self, image_data):
        """
        캡션을 표시하는 메서드
        
        Args:
            image_data (dict): 이미지 데이터
        """
        caption_text = ""
        
        # 캡션 정보 수집
        if isinstance(image_data, dict):
            # 1. 기본 캡션
            if 'caption' in image_data and image_data['caption']:
                caption_text = image_data['caption']
            
            # 2. TE 번호 추가
            if 'te_number' in image_data and image_data['te_number']:
                te_number = image_data['te_number']
                if caption_text:
                    caption_text = f"[{te_number}] {caption_text}"
                else:
                    caption_text = f"[{te_number}] 관련 이미지"
            
            # 3. 페이지 정보 추가
            if 'page_idx' in image_data:
                page_num = image_data['page_idx'] + 1
                caption_text += f" (페이지 {page_num})"
            elif 'page' in image_data:
                caption_text += f" (페이지 {image_data['page']})"
            
            # 4. 테이블 캡션이 있는 경우
            if 'table_caption' in image_data and image_data['table_caption']:
                if caption_text:
                    caption_text += f" - 테이블: {image_data['table_caption']}"
                else:
                    caption_text = f"테이블: {image_data['table_caption']}"
            
            # 5. 파일 경로 정보 (선택적)
            if 'file_path' in image_data and image_data['file_path']:
                file_name = os.path.basename(image_data['file_path'])
                caption_text += f" ({file_name})"
        
        # 캡션이 있으면 표시, 없으면 숨김
        if caption_text:
            # 창 너비에 따라 wraplength 동적 설정
            try:
                current_width = self.top.winfo_width()
                wrap_length = max(400, current_width - 100)  # 최소 400, 창너비-100
            except:
                wrap_length = 800  # 기본값
            
            self.caption_label.config(text=caption_text, wraplength=wrap_length)
            self.caption_label.pack(fill=tk.X, padx=5, pady=5)
        else:
            self.caption_label.pack_forget()
    
    def _display_image(self, image_data):
        """
        이미지 데이터를 처리하여 캔버스에 표시 (로컬 파일 우선)
        
        Args:
            image_data (dict): 이미지 데이터
        """
        image = None
        self.original_image = None
        self.zoom_level = 1.0
        image_loaded = False
        
        try:
            if isinstance(image_data, Image.Image):
                image = image_data
                image_loaded = True
            elif isinstance(image_data, dict):
                # 1. 로컬 파일 경로에서 이미지 로드 시도 (우선순위 1)
                local_image_path = self._find_local_image_file(image_data)
                if local_image_path:
                    try:
                        image = Image.open(local_image_path)
                        image_loaded = True
                        print(f"✅ 로컬 이미지 로드 성공: {os.path.basename(local_image_path)}")
                    except Exception as e:
                        print(f"❌ 로컬 이미지 로드 실패: {local_image_path}, 오류: {str(e)}")
                
                # 2. 기존 파일 경로에서 이미지 로드 (우선순위 2)
                if not image_loaded:
                    for path_field in ['file_path', 'src', 'url']:
                        if path_field in image_data and image_data[path_field]:
                            file_path = image_data[path_field]
                            if os.path.exists(file_path):
                                try:
                                    image = Image.open(file_path)
                                    image_loaded = True
                                    print(f"✅ 기존 경로 이미지 로드 성공: {os.path.basename(file_path)}")
                                    break
                                except Exception as e:
                                    print(f"❌ 기존 경로 이미지 로드 실패: {file_path}, 오류: {str(e)}")
                
                # 3. base64 데이터에서 이미지 로드 (fallback)
                if not image_loaded and 'base64' in image_data and image_data['base64']:
                    try:
                        base64_data = image_data['base64']
                        if base64_data.startswith('data:image'):
                            base64_parts = base64_data.split(',', 1)
                            if len(base64_parts) > 1:
                                base64_data = base64_parts[1]
                        image_bytes = base64.b64decode(base64_data)
                        image = Image.open(BytesIO(image_bytes))
                        image_loaded = True
                        print(f"✅ base64 이미지 로드 성공 (fallback)")
                    except Exception as e:
                        print(f"❌ base64 이미지 로드 실패: {str(e)}")
                
                if not image_loaded:
                    raise ValueError("이미지 데이터를 찾을 수 없습니다.")
            else:
                raise ValueError("지원되지 않는 이미지 데이터 형식입니다.")
            
            if image:
                self.original_image = image
                orig_width, orig_height = image.size
                screen_width = self.top.winfo_screenwidth() * 0.7
                screen_height = self.top.winfo_screenheight() * 0.7
                
                if orig_width > screen_width or orig_height > screen_height:
                    width_ratio = screen_width / orig_width
                    height_ratio = screen_height / orig_height
                    ratio = min(width_ratio, height_ratio)
                    new_width = int(orig_width * ratio)
                    new_height = int(orig_height * ratio)
                    image = image.resize((new_width, new_height), Image.LANCZOS)
                    self.zoom_level = ratio
                
                self.photo = ImageTk.PhotoImage(image)
                self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
                
                current_width, current_height = image.size
                info_text = f"이미지 크기: {orig_width}x{orig_height} 픽셀 (표시: {current_width}x{current_height})"
                
                # 창 제목 업데이트 (캡션 제외, 이미지 정보만)
                base_title = self.top.title().split(' - ')[0]  # 기본 제목만 유지
                self.top.title(f"{base_title} - {info_text}")
                
                self.canvas.bind("<MouseWheel>", self._on_mousewheel)
                self.canvas.bind("<Button-4>", self._on_mousewheel)
                self.canvas.bind("<Button-5>", self._on_mousewheel)
        
        except Exception as e:
            error_text = f"이미지 로드 중 오류 발생: {str(e)}"
            self.canvas.create_text(
                10, 10, 
                text=error_text, 
                anchor=tk.NW, 
                fill="red", 
                font=("Arial", 12)
            )
            print(f"❌ 최종 이미지 로드 실패: {str(e)}")

    def _find_local_image_file(self, image_data):
        """
        extracted_images 폴더에서 이미지 파일을 검색
        
        Args:
            image_data (dict): 이미지 데이터
            
        Returns:
            str: 파일 경로 또는 None
        """
        try:
            # extracted_images 폴더 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_folder = os.path.join(current_dir, "extracted_images")
            
            if not os.path.exists(image_folder):
                print(f"extracted_images 폴더가 존재하지 않음: {image_folder}")
                return None
            
            # 지원되는 이미지 확장자
            supported_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
            
            # 폴더 내 파일 목록 가져오기
            try:
                all_files = [f for f in os.listdir(image_folder) 
                           if any(f.lower().endswith(ext) for ext in supported_extensions)]
            except Exception as e:
                print(f"폴더 읽기 오류: {image_folder}, 오류: {str(e)}")
                return None
            
            if not all_files:
                print(f"extracted_images 폴더에 이미지 파일이 없음")
                return None
            
            # 이미지 정보 추출
            caption = image_data.get('caption', '').strip()
            te_number = image_data.get('te_number', '')
            page_num = image_data.get('page', image_data.get('page_idx', 'Unknown'))
            
            print(f"로컬 이미지 검색: 캡션='{caption}', TE={te_number}, 페이지={page_num}")
            
            # 1단계: 정확한 매칭
            best_match = None
            best_score = 0
            
            for file_name in all_files:
                score = self._calculate_image_match_score(file_name, caption, te_number, page_num)
                
                if score > best_score:
                    best_score = score
                    best_match = file_name
                    
                if score > 0:
                    print(f"  파일 매칭: {file_name} -> 점수: {score}")
            
            if best_match and best_score > 30:  # 임계값 설정
                matched_path = os.path.join(image_folder, best_match)
                if os.path.exists(matched_path):
                    print(f"✅ 로컬 이미지 매칭 성공: {best_match} (점수: {best_score})")
                    return matched_path
            
            # 2단계: Figure 키워드 기반 매칭
            if 'figure' in caption.lower() or 'fig' in caption.lower():
                figure_files = [f for f in all_files if 'figure' in f.lower() or 'fig' in f.lower()]
                figure_files.sort()
                
                if figure_files:
                    fallback_file = figure_files[0]  # 첫 번째 Figure 파일 사용
                    fallback_path = os.path.join(image_folder, fallback_file)
                    if os.path.exists(fallback_path):
                        print(f"✅ Figure 키워드 매칭: {fallback_file}")
                        return fallback_path
            
            print(f"❌ 로컬 이미지 매칭 실패: 적절한 파일을 찾을 수 없음")
            return None
            
        except Exception as e:
            print(f"로컬 이미지 검색 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_image_match_score(self, filename, caption, te_number, page_num):
        """
        파일명과 이미지 정보 간의 매칭 점수를 계산
        
        Args:
            filename (str): 파일명
            caption (str): 이미지 캡션
            te_number (str): TE 번호
            page_num (str/int): 페이지 번호
            
        Returns:
            int: 매칭 점수
        """
        score = 0
        filename_lower = filename.lower()
        caption_lower = caption.lower() if caption else ''
        
        # 1. TE 번호 매칭 (최고 우선순위)
        if te_number:
            te_variants = [
                te_number.lower(),
                te_number.replace('.', '_').lower(),
                te_number.replace('.', '-').lower(),
                te_number.replace('te', '').replace('.', '_').lower()
            ]
            
            for te_variant in te_variants:
                if te_variant in filename_lower:
                    score += 100
                    print(f"    TE 번호 매칭: {te_variant} (+100)")
                    break
        
        # 2. Figure 키워드 매칭
        figure_keywords = ['figure', 'fig']
        for keyword in figure_keywords:
            if keyword in filename_lower and keyword in caption_lower:
                score += 80
                print(f"    Figure 키워드 매칭: {keyword} (+80)")
                break
        
        # 3. 페이지 번호 매칭
        if page_num and str(page_num) != 'Unknown':
            page_patterns = [
                f'page{page_num}',
                f'p{page_num}',
                f'_{page_num}_',
                f'-{page_num}-'
            ]
            
            for pattern in page_patterns:
                if pattern in filename_lower:
                    score += 60
                    print(f"    페이지 번호 매칭: {pattern} (+60)")
                    break
        
        # 4. 캡션 키워드 매칭
        if caption:
            caption_words = caption_lower.split()
            for word in caption_words:
                if len(word) > 3 and word in filename_lower:  # 3글자 이상만 매칭
                    score += 30
                    print(f"    캡션 키워드 매칭: {word} (+30)")
        
        # 5. 일반 이미지 키워드 매칭
        image_keywords = ['image', 'img', 'picture', 'pic']
        for keyword in image_keywords:
            if keyword in filename_lower:
                score += 20
                print(f"    이미지 키워드 매칭: {keyword} (+20)")
                break
        
        return score
    
    def _on_mousewheel(self, event):
        """
        마우스 휠 이벤트 처리 - 이미지 확대/축소
        
        Args:
            event: 마우스 이벤트
        """
        if not hasattr(self, 'original_image') or self.original_image is None:
            return
            
        old_zoom = self.zoom_level
        
        if event.num == 4 or event.delta > 0:  # 확대
            self.zoom_level *= 1.1
        elif event.num == 5 or event.delta < 0:  # 축소
            self.zoom_level *= 0.9
        
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        
        if old_zoom != self.zoom_level:
            self._update_image_with_zoom()
    
    def _update_image_with_zoom(self):
        """현재 줌 레벨에 맞게 이미지를 업데이트"""
        if self.original_image:
            orig_width, orig_height = self.original_image.size
            new_width = int(orig_width * self.zoom_level)
            new_height = int(orig_height * self.zoom_level)
            resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(resized_image)
            self.canvas.itemconfig(self.image_id, image=self.photo)
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
            info_text = f"이미지 크기: {orig_width}x{orig_height} 픽셀 (표시: {new_width}x{new_height}, 확대/축소: {self.zoom_level:.2f}x)"
            
            # 창 제목 업데이트 (캡션 제외, 이미지 정보만)
            base_title = self.top.title().split(' - ')[0]  # 기본 제목만 유지
            self.top.title(f"{base_title} - {info_text}")
    
    def _create_close_button(self):
        """닫기 버튼 및 확대/축소 버튼 생성"""
        btn_frame = tk.Frame(self.top)
        btn_frame.pack(pady=10)
        
        zoom_in_btn = tk.Button(
            btn_frame, 
            text="확대 (+)", 
            command=self._zoom_in,
            width=8,
            bg="#e6f2ff"
        )
        zoom_in_btn.pack(side=tk.LEFT, padx=5)
        
        zoom_out_btn = tk.Button(
            btn_frame, 
            text="축소 (-)", 
            command=self._zoom_out,
            width=8,
            bg="#e6f2ff"
        )
        zoom_out_btn.pack(side=tk.LEFT, padx=5)
        
        reset_zoom_btn = tk.Button(
            btn_frame, 
            text="원본 크기", 
            command=self._reset_zoom,
            width=8,
            bg="#e6f2ff"
        )
        reset_zoom_btn.pack(side=tk.LEFT, padx=5)
        
        # 캡션 복사 버튼 추가
        copy_caption_btn = tk.Button(
            btn_frame, 
            text="캡션 복사", 
            command=self._copy_caption,
            width=10,
            bg="#ffe6e6"
        )
        copy_caption_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = tk.Button(
            btn_frame, 
            text="닫기", 
            command=self.top.destroy,
            width=8,
            bg="#f0f0f0"
        )
        close_btn.pack(side=tk.LEFT, padx=5)
        
        help_label = tk.Label(
            self.top,
            text="마우스 휠로 이미지 확대/축소 가능 | 캡션은 이미지 위쪽에 표시됩니다",
            font=("Arial", 9, "italic"),
            fg="#666666"
        )
        help_label.pack(pady=(0, 5))
    
    def _copy_caption(self):
        """캡션을 클립보드에 복사"""
        try:
            caption_text = self.caption_label.cget("text")
            if caption_text:
                self.top.clipboard_clear()
                self.top.clipboard_append(caption_text)
                # 간단한 알림 (토스트 메시지 스타일)
                self._show_toast_message("캡션이 클립보드에 복사되었습니다!")
            else:
                self._show_toast_message("복사할 캡션이 없습니다.")
        except Exception as e:
            self._show_toast_message(f"복사 중 오류: {str(e)}")
    
    def _show_toast_message(self, message):
        """간단한 메시지 표시"""
        toast = tk.Toplevel(self.top)
        toast.title("")
        toast.geometry("300x50")
        toast.transient(self.top)
        toast.grab_set()
        
        # 창을 화면 중앙에 위치
        toast.geometry("+{}+{}".format(
            self.top.winfo_rootx() + 50,
            self.top.winfo_rooty() + 50
        ))
        
        label = tk.Label(toast, text=message, bg="lightgreen", font=("Arial", 10))
        label.pack(expand=True, fill=tk.BOTH)
        
        # 2초 후 자동 닫기
        toast.after(2000, toast.destroy)
    
    def _zoom_in(self):
        """이미지 확대"""
        if hasattr(self, 'original_image') and self.original_image:
            self.zoom_level *= 1.25
            self.zoom_level = min(5.0, self.zoom_level)
            self._update_image_with_zoom()
    
    def _zoom_out(self):
        """이미지 축소"""
        if hasattr(self, 'original_image') and self.original_image:
            self.zoom_level *= 0.8
            self.zoom_level = max(0.1, self.zoom_level)
            self._update_image_with_zoom()
    
    def _reset_zoom(self):
        """원본 크기로 복원"""
        if hasattr(self, 'original_image') and self.original_image:
            self.zoom_level = 1.0
            self._update_image_with_zoom()
