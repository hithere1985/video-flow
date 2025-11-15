import argparse
from pathlib import Path
from encoder import process_directory

def main():
    """
    커맨드 라인 인자를 파싱하고 인코딩 프로세스를 시작합니다.
    """
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
        default=None,
        help="변환된 파일을 저장할 폴더 경로를 입력하세요. (폴더가 없으면 자동 생성됩니다.) 지정하지 않으면 입력 폴더 내 'encoded_videos' 폴더에 저장됩니다."
    )
    
    parser.add_argument(
        '--gpu', 
        action='store_true', 
        help="NVIDIA NVENC (hevc_nvenc) GPU 가속 인코딩을 사용합니다. (CRF 대신 CQP 23 사용)"
    )
    
    args = parser.parse_args()
    
    input_directory = Path(args.input_path)
    use_gpu_mode = args.gpu

    if args.output_path:
        output_directory = Path(args.output_path)
    else:
        output_directory = input_directory.parent / f"{input_directory.name}_encoded"
        print(f"[INFO] 출력 경로가 지정되지 않아 '{output_directory}' 폴더로 자동 설정됩니다.")
    
    process_directory(input_directory, output_directory, use_gpu_mode)

if __name__ == "__main__":
    main()
