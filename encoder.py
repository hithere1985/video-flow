import os
import subprocess
from pathlib import Path
import argparse
import re
import json
from tqdm import tqdm # tqdm 모듈 추가

# --- 인코딩 설정 변수 ---
CRF_VALUE = 20
PRESET = "medium" 
VIDEO_CODEC = "libx265"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k" 

INPUT_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mkv'] 
OUTPUT_EXTENSION = '.mp4'
FFMPEG_PATH = "ffmpeg" 
FFPROBE_PATH = "ffprobe" # ffprobe는 ffmpeg 설치 시 함께 제공됨

# FFmpeg 시간 출력 포맷을 파싱하기 위한 정규 표현식 (예: time=00:01:23.45)
TIME_REGEX = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})')

def time_to_seconds(t_str: str) -> float:
    """HH:MM:SS.ms 문자열을 초(seconds) 단위로 변환합니다."""
    # 정규식 대신 문자열 파싱 (좀 더 견고하게)
    try:
        h, m, s = map(float, t_str.split(':'))
        return h * 3600 + m * 60 + s
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
            str(input_path.resolve()) # 절대 경로 사용
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        duration_info = json.loads(result.stdout)
        
        # duration 값이 문자열일 수 있으므로 float으로 변환
        duration = float(duration_info['format']['duration'])
        return duration
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError, ValueError) as e:
        # ffprobe 실행 실패, 파일 못 찾음, JSON 키 에러 등 처리
        print(f"    [ERROR] FFprobe 실패: 길이를 가져올 수 없습니다. {e}")
        return 0.0

def convert_video_file(input_path: Path, output_dir: Path):
    """단일 파일을 인코딩하고 tqdm으로 진행률을 표시합니다."""
    
    # 0. 총 길이 가져오기
    total_duration = get_duration(input_path)
    if total_duration == 0.0:
        print(f"    [SKIP] 길이를 알 수 없어 변환을 건너뜁니다: {input_path.name}")
        return

    # 1. 출력 파일 이름 정의 및 경로 확인
    output_filename = f"{input_path.stem}_CRF{CRF_VALUE}{OUTPUT_EXTENSION}"
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
        
        # 메타데이터 복사 옵션 (출력 옵션)
        "-map_metadata", "0", 
        
        # 비디오 설정
        "-c:v", VIDEO_CODEC,
        "-crf", str(CRF_VALUE),
        "-preset", PRESET,
        "-tag:v", "hvc1", 
        
        # 오디오 설정
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        
        # FFmpeg의 자세한 정보 출력을 억제하고 진행 정보만 표준 오류로 출력하도록 설정
        "-stats", 
        
        # 출력 파일 설정
        str(output_path)
    ]
    
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
        with tqdm(total=total_duration, unit="s", desc=f"  {output_filename}") as pbar:
            while True:
                # stderr에서 한 줄씩 읽기
                line = process.stderr.readline()
                if not line:
                    break
                
                # 'time=' 패턴 찾기
                match = re.search(TIME_REGEX, line)
                
                if match:
                    # 'time=HH:MM:SS' 형태의 문자열 추출
                    current_time_str = match.group(0).replace('time=', '').strip()
                    current_seconds = time_to_seconds(current_time_str)
                    
                    # tqdm 업데이트
                    pbar.update(current_seconds - pbar.n) # 이전 업데이트 값과의 차이만큼 업데이트

        # Popen이 완료될 때까지 대기하고 리턴 코드 확인
        process.wait()

        if process.returncode == 0:
            print(f"    [SUCCESS] 변환 완료: {output_path.name}")
        else:
            print(f"    [ERROR] 변환 실패: {input_path.name} (리턴 코드: {process.returncode})")
            
    except FileNotFoundError:
        print(f"    [FATAL ERROR] FFmpeg 또는 FFprobe 실행 파일을 찾을 수 없습니다. 경로를 확인하세요: {FFMPEG_PATH}")
        return
    except Exception as e:
        print(f"    [ERROR] 예상치 못한 오류: {e}")
        
def process_directory(input_dir: Path, output_dir: Path):
    """주어진 입력 디렉토리를 순회하며 파일을 찾아 지정된 출력 디렉토리에 저장합니다."""
    
    if not input_dir.is_dir():
        print(f"[FATAL ERROR] 지정된 입력 경로가 유효한 디렉토리가 아닙니다: {input_dir}")
        return

    print(f"--- 폴더 검색 시작: {input_dir.resolve()} ---")
    print(f"--- 출력 폴더 지정: {output_dir.resolve()} ---")
    
    for root, _, files in os.walk(input_dir):
        
        for filename in files:
            if filename.lower().endswith(tuple(INPUT_EXTENSIONS)):
                input_path = Path(root) / filename
                
                # convert_video_file 함수는 이제 tqdm을 통해 자체적으로 진행률 표시
                convert_video_file(input_path, output_dir)
    
    print("--- 모든 파일 처리 완료 ---")

# --- main 함수: argparse 로직 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="지정된 폴더와 하위 폴더의 동영상을 H.265 (CRF 20)로 일괄 변환하여 지정된 출력 폴더에 저장합니다."
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
    
    args = parser.parse_args()
    
    input_directory = Path(args.input_path)
    output_directory = Path(args.output_path)
    
    process_directory(input_directory, output_directory)