import os
import subprocess
from pathlib import Path
import argparse
import re
import json
from tqdm import tqdm

# --- 인코딩 기본 설정 변수 ---
DEFAULT_CRF_VALUE = 20
DEFAULT_PRESET = "medium" 
NVENC_CQP_VALUE = 23 # CRF 20과 유사한 NVENC CQP 값 (테스트 필요)
NVENC_PRESET = "medium" # NVENC용 프리셋

# --- 고정 설정 변수 ---
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k" 

INPUT_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mkv'] 
OUTPUT_EXTENSION = '.mp4'
FFMPEG_PATH = "ffmpeg" 
FFPROBE_PATH = "ffprobe"

# FFmpeg 시간 출력 포맷을 파싱하기 위한 정규 표현식 (예: time=00:01:23.45)
# NVENC 사용 시 time=00:00:00.00 이런 형태의 출력이 한 줄에 이어서 나올 수도 있어 좀 더 견고하게 수정
TIME_REGEX = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})') 

def time_to_seconds(t_str: str) -> float:
    """HH:MM:SS.ms 문자열을 초(seconds) 단위로 변환합니다."""
    try:
        # 정규식 캡처 그룹 (HH, MM, SS, ms)을 가정하고 파싱
        parts = t_str.split(':')
        if len(parts) == 3:
             # SS.ms 분리
             s_ms = parts[2]
             s, ms_str = s_ms.split('.')
             
             h = float(parts[0])
             m = float(parts[1])
             s = float(s)
             ms = float(ms_str)
             
             # ms는 1/100초를 나타낸다고 가정
             return h * 3600 + m * 60 + s + ms / 100.0 
        return 0.0
    except:
        return 0.0

def get_duration(input_path: Path) -> float:
    """ffprobe를 사용하여 동영상 파일의 총 길이를 초 단위로 얻습니다."""
    try:
        command = [
            FFPROBE_PATH,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(input_path.resolve())
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        duration_info = json.loads(result.stdout)
        
        duration = float(duration_info['format']['duration'])
        return duration
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError, ValueError) as e:
        print(f"    [ERROR] FFprobe 실패: 길이를 가져올 수 없습니다. {e}")
        return 0.0

def convert_video_file(input_path: Path, output_dir: Path, use_gpu: bool):
    """단일 파일을 인코딩하고 tqdm으로 진행률을 표시합니다."""
    
    # --- 0. 모드에 따른 인코더/품질 설정 ---
    if use_gpu:
        VIDEO_CODEC = "hevc_nvenc"
        PRESET = NVENC_PRESET
        QUALITY_PARAM = ["-cq", str(NVENC_CQP_VALUE)] # CQP
        TAG = "NVENC_CQP" + str(NVENC_CQP_VALUE)
        # NVENC 추가 옵션: VBR 모드, HQ 튜닝, 비트레이트 제한 해제
        EXTRA_OPTIONS = ["-rc", "vbr", "-b:v", "0k", "-qmin", "0", "-qmax", "51"]
        print(f"    [INFO] GPU (NVENC) 모드: {VIDEO_CODEC}, CQP={NVENC_CQP_VALUE}")
    else:
        VIDEO_CODEC = "libx265"
        PRESET = DEFAULT_PRESET
        QUALITY_PARAM = ["-crf", str(DEFAULT_CRF_VALUE)] # CRF
        TAG = "CRF" + str(DEFAULT_CRF_VALUE)
        EXTRA_OPTIONS = []
        print(f"    [INFO] CPU (libx265) 모드: {VIDEO_CODEC}, CRF={DEFAULT_CRF_VALUE}")


    # 0. 총 길이 가져오기
    total_duration = get_duration(input_path)
    if total_duration == 0.0:
        print(f"    [SKIP] 길이를 알 수 없어 변환을 건너뜁니다: {input_path.name}")
        return

    # 1. 출력 파일 이름 정의 및 경로 확인
    output_filename = f"{input_path.stem}_{TAG}{OUTPUT_EXTENSION}"
    output_path = output_dir / output_filename
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_path.exists():
        print(f"    [SKIP] 이미 존재함: {output_path.name}")
        return

    print(f"    [START] 변환 시작: {input_path.name}")
    
    # 2. FFmpeg 명령어 구성
    command = [
        FFMPEG_PATH, 
        
        # 입력 파일 설정
        "-i", str(input_path),
        
        # 메타데이터 복사 옵션
        "-map_metadata", "0", 
        
        # 비디오 설정
        "-c:v", VIDEO_CODEC,
    ]
    
    # 품질 및 프리셋, 추가 옵션 통합
    command.extend(QUALITY_PARAM)
    command.extend(["-preset", PRESET])
    command.extend(EXTRA_OPTIONS)
    
    # 공통 HEVC 태그
    command.extend(["-tag:v", "hvc1"])
    
    # 오디오 설정
    command.extend([
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
    ])
    
    # FFmpeg 진행 정보 출력 설정
    command.append("-stats") 
    
    # 출력 파일 설정
    command.append(str(output_path))
    
    # 3. FFmpeg 실행 및 tqdm 연동
    try:
        # Popen을 사용하여 출력을 스트림으로 읽어들임
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # FFmpeg 진행률은 stderr로 출력됨
            text=True,
            bufsize=1
        )
        
        # tqdm 설정 (total은 총 시간(초))
        with tqdm(total=total_duration, unit="s", desc=f"  {output_filename}", miniters=1) as pbar:
            full_stderr = "" # 에러 로그 저장용 변수
            while True:
                # stderr에서 한 줄씩 읽기
                line = process.stderr.readline()
                if not line:
                    break
                
                full_stderr += line
                
                # 'time=' 패턴 찾기
                match = re.search(TIME_REGEX, line)
                
                if match:
                    # 'time=HH:MM:SS.ms' 형태의 문자열 추출
                    current_seconds = time_to_seconds(f"{match.group(1)}:{match.group(2)}:{match.group(3)}.{match.group(4)}")
                    
                    # --- TqdmWarning 해결을 위한 수정 ---
                    # 1. 현재 진행된 시간이 총 시간을 초과하지 않도록 제한(clamp)합니다.
                    clamped_seconds = min(current_seconds, total_duration)
                    
                    # 2. tqdm 업데이트: 현재 진행 상황(clamped_seconds)이 pbar.n보다 클 때만 업데이트
                    if clamped_seconds > pbar.n:
                        pbar.update(clamped_seconds - pbar.n)
                    # ------------------------------------

        # Popen이 완료될 때까지 대기하고 리턴 코드 확인
        process.wait()

        if process.returncode == 0:
            print(f"    [SUCCESS] 변환 완료: {output_path.name}")
        else:
            print(f"    [ERROR] 변환 실패: {input_path.name} (리턴 코드: {process.returncode})")
            # --- 실패 시 에러 로그 출력 ---
            print("    --- FFmpeg Error Log Start (Failed Command) ---")
            print(" ".join(command))
            print("    --- FFmpeg Error Output ---")
            # 전체 에러 출력에서 마지막 몇 줄만 보여주는 것이 유용할 수 있지만, 
            # 디버깅을 위해 전체 로그를 출력합니다.
            print(full_stderr)
            print("    --- FFmpeg Error Log End ---")
            # -------------------------------
            
    except FileNotFoundError:
        print(f"    [FATAL ERROR] FFmpeg 또는 FFprobe 실행 파일을 찾을 수 없습니다. 경로를 확인하세요: {FFMPEG_PATH}")
        return
    except Exception as e:
        print(f"    [ERROR] 예상치 못한 오류: {e}")
        
def process_directory(input_dir: Path, output_dir: Path, use_gpu: bool):
    """주어진 입력 디렉토리를 순회하며 파일을 찾아 지정된 출력 디렉토리에 저장합니다."""
    
    if not input_dir.is_dir():
        print(f"[FATAL ERROR] 지정된 입력 경로가 유효한 디렉토리가 아닙니다: {input_dir}")
        return

    print(f"--- 폴더 검색 시작: {input_dir.resolve()} ---")
    print(f"--- 출력 폴더 지정: {output_dir.resolve()} ---")
    print(f"--- 인코딩 모드: {'GPU (NVENC)' if use_gpu else 'CPU (libx265)'} ---")
    
    for root, _, files in os.walk(input_dir):
        
        for filename in files:
            if filename.lower().endswith(tuple(INPUT_EXTENSIONS)):
                input_path = Path(root) / filename
                
                convert_video_file(input_path, output_dir, use_gpu)
    
    print("--- 모든 파일 처리 완료 ---")

# --- main 함수: argparse 로직 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="지정된 폴더와 하위 폴더의 동영상을 H.265로 일괄 변환하여 지정된 출력 폴더에 저장합니다. GPU(NVENC) 가속 옵션을 제공합니다."
    )
    
    parser.add_argument(
        '--input_path', 
        type=str, 
        required=True, 
        help="변환할 동영상 파일이 있는 루트 폴더 경로를 입력하세요."
    )
    
    parser.add_argument(
        '--output_path', 
        type=str, 
        required=True, 
        help="변환된 파일을 저장할 폴더 경로를 입력하세요. (폴더가 없으면 자동 생성됩니다.)"
    )
    
    # 새로 추가된 GPU 옵션
    parser.add_argument(
        '--gpu', 
        action='store_true', 
        help="NVIDIA NVENC (hevc_nvenc) GPU 가속 인코딩을 사용합니다. (CRF 대신 CQP 23 사용)"
    )
    
    args = parser.parse_args()
    
    input_directory = Path(args.input_path)
    output_directory = Path(args.output_path)
    use_gpu_mode = args.gpu
    
    process_directory(input_directory, output_directory, use_gpu_mode)