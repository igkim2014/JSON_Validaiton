"""
메인 실행 파일
"""
import tkinter as tk
import os
import sys


# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# PIL 라이브러리 확인
try:
    from PIL import Image, ImageTk
except ImportError:
    import tkinter.messagebox as messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showwarning(
        "모듈 경고", 
        "PIL 모듈을 찾을 수 없습니다. 이미지 관련 기능이 제한될 수 있습니다.\n\n"
        "다음 명령으로 설치할 수 있습니다: pip install pillow"
    )

# 필요한 모듈이 있는지 확인
required_modules = ['config_reader.py', 'validator.py', 'gui.py']
missing_modules = []

for module in required_modules:
    if not os.path.exists(os.path.join(current_dir, module)):
        missing_modules.append(module)

if missing_modules:
    import tkinter.messagebox as messagebox
    root = tk.Tk()
    root.withdraw() 
    messagebox.showerror(
        "모듈 오류", 
        f"다음 필수 모듈을 찾을 수 없습니다:\n{', '.join(missing_modules)}\n\n"
        f"모든 파일이 같은 디렉토리에 있는지 확인하세요:\n{current_dir}"
    )
    sys.exit(1)

# 모듈 가져오기 시도
try:
    from gui import JSONValidatorGUI
except ImportError as e:
    import tkinter.messagebox as messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "임포트 오류", 
        f"모듈 가져오기 오류: {e}\n\n"
        f"모든 파일이 같은 디렉토리에 있는지 확인하세요:\n{current_dir}"
    )
    sys.exit(1)

def main():
    """프로그램 메인 실행 함수"""
    root = tk.Tk()
    app = JSONValidatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()