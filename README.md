# Video-Flow

## Project Overview

**`Video-Flow`** is an automated pipeline designed to efficiently manage video archives and optimize them for cloud storage.

With a single "click" (or command execution), it handles the complex process of **FFmpeg encoding** and **Google Photos upload**. It compresses high-capacity original video files using the **H.265 (HEVC)** codec at **optimal quality (CRF 20)**, **preserves the original metadata (e.g., creation date)**, and automatically backs them up to Google Photos.

---

## Key Features

* **H.265 (HEVC) Encoding:** Uses FFmpeg to convert videos to the highly space-efficient H.265 codec.
* **CRF 20 Quality Assurance:** Guarantees consistent **visual quality** while achieving maximum size reduction.
* **Metadata Preservation:** Copies the original file's **creation timestamp** to the converted file, ensuring accurate sorting in Google Photos (`-map_metadata 0`).
* **Automated Google Photos Upload:** Seamlessly uploads the finalized files via the Google Photos Library API. (Not yet)
* **`tqdm` Progress Bar:** Provides a visual progress bar during encoding for real-time monitoring.
* **Batch/Recursive Processing:** Scans all files within the designated root and subfolders for video conversion.

---

## Getting Started

### 1. Prerequisites & Installation

This script runs on Python 3.x and requires FFmpeg and several Python libraries.

```bash
# Install required Python libraries
pip install tqdm requests google-auth google-auth-oauthlib google-auth-httplib2

# Verify FFmpeg and FFprobe installation
# Ensure 'ffmpeg' and 'ffprobe' are accessible in your system's PATH.
```

### 2. Google Photos Authentication

Uploading to Google Photos requires an authentication file.

1.  **Google Cloud Project Setup:** Create a new project in the Google API Console and enable the **Photos Library API**.
2.  **Create OAuth 2.0 Client ID:** Choose **'Desktop app'** as the application type and create the client ID.
3.  **Download Credentials:** Save the downloaded JSON file into the same folder as the script and rename it to **`client_secret.json`**.

---

## Running the Script

The script requires an **input path (`--input_path`)**. The **output path (`--output_path`)** is optional. If `--output_path` is not provided, a new folder named `[INPUT_FOLDER_NAME]_encoded` will be created in the same directory as the input folder.

### Command Structure

Use the following command structure:

`python main.py --input_path [SOURCE_FOLDER_PATH] [--output_path [DESTINATION_FOLDER_PATH]] [--gpu]`

### Example (WSL/Linux)

For example, on WSL or Linux systems:

`python main.py --input_path /mnt/c/Users/User/Videos/Original --output_path /mnt/d/H265_Backup --gpu`

Or, using the default output path:

`python main.py --input_path /mnt/c/Users/User/Videos/Original`
(This will create `/mnt/c/Users/User/Videos/Original_encoded`)

### First Run Authentication

On the first execution, a web browser will open requesting your Google account login. Once authenticated, a **`token.json`** file will be created for automatic future logins.

---

## Configuration (`encoder.py` internal)

You can customize the encoding settings at the top of the `encoder.py` file.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DEFAULT_CRF_VALUE` | `20` | CRF value for CPU (libx265) encoding. (Lower = Higher quality/Larger size. 18-24 is recommended.) |
| `DEFAULT_PRESET` | "medium" | Encoding speed vs. efficiency trade-off for CPU (libx265) encoding. |
| `NVENC_CQP_VALUE` | `23` | CQP value for GPU (NVENC) encoding. (Similar to CRF 20, requires testing.) |
| `NVENC_PRESET` | "medium" | Encoding speed vs. efficiency trade-off for GPU (NVENC) encoding. |
| `AUDIO_BITRATE` | "192k" | Audio quality (using AAC codec). |
| `FFMPEG_PATH` | "ffmpeg" | Path to the FFmpeg executable. |
| `FFPROBE_PATH` | "ffprobe" | Path to the FFprobe executable. |

---

## 🇰🇷 한국어 안내 (Korean Guide)

### 프로젝트 요약

**`Video-Flow`**는 FFmpeg을 이용하여 고용량 영상을 **H.265 (CRF 20)**로 압축하고, 메타데이터를 보존한 채 **Google Photos에 자동으로 업로드**하는 파이썬 스크립트입니다.

### 핵심 기능

* **자동 압축:** CRF 20으로 품질을 유지하며 용량 최적화
* **메타데이터 보존:** Google 포토에서 촬영 시점이 정확히 유지됨
* **자동 백업:** 인증 후 명령어 한 번으로 변환 및 업로드 완료

### 실행 방법

1.  **필수 라이브러리 설치:** `pip install tqdm requests google-auth google-auth-oauthlib google-auth-httplib2`
2.  **인증 파일 준비:** Google Cloud에서 발급받은 `client_secret.json`을 스크립트 폴더에 저장합니다.
3.  **실행 명령어:**
    
    `python main.py --input_path [원본_폴더_경로] [--output_path [결과_폴더_경로]] [--gpu]`
    
    `--output_path`를 지정하지 않으면, `[원본_폴더_경로]`와 동일한 위치에 `[원본_폴더_이름]_encoded` 폴더가 생성됩니다.
    `--gpu` 옵션을 사용하면 NVIDIA NVENC (hevc_nvenc) GPU 가속 인코딩을 사용합니다.
