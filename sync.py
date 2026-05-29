import os
import shutil
import subprocess
import sys
import io

# Fix Windows console encoding issues for emojis
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Config
def get_git_path():
    git_in_path = shutil.which("git")
    if git_in_path:
        return git_in_path
    
    candidates = [
        r"C:\Users\celeb\AppData\Local\GitHubDesktop\app-3.5.10\resources\app\git\cmd\git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "git"

GIT_PATH = get_git_path()
GIT_REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_github_temp")
LOCAL_STUDY_DIR = r"G:\내 드라이브\[언어 공부]\2. 중국어 암기"

def main():
    print("=" * 60)
    print("🔄 중국어 암기 데이터 동기화 시스템 (Git -> Google Drive)")
    print("=" * 60)

    # 1. Pull latest changes from GitHub Actions
    if not os.path.exists(GIT_REPO_DIR):
        print("❌ 에러: _github_temp 폴더가 존재하지 않습니다. 로컬 환경 설정을 다시 확인하세요.")
        return

    print("📡 1. 깃허브(GitHub)에서 최신 업데이트 데이터를 내려받는 중...")
    try:
        result = subprocess.run(
            [GIT_PATH, "pull"],
            cwd=GIT_REPO_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ 깃허브 다운로드 성공!")
        print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"❌ 깃허브 다운로드 실패: {e}")
        print(e.stderr)
        return
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return

    print("-" * 50)
    print("📂 2. 구글 드라이브 학습 폴더로 파일 복사 및 정리를 진행합니다...")
    print(f"   목표 경로: {LOCAL_STUDY_DIR}")

    # Ensure target directories exist
    db_target = os.path.join(LOCAL_STUDY_DIR, "01_Database")
    daily_target = os.path.join(LOCAL_STUDY_DIR, "02_Daily_Sheets")
    print_target = os.path.join(LOCAL_STUDY_DIR, "03_Print_PDF")

    os.makedirs(db_target, exist_ok=True)
    os.makedirs(daily_target, exist_ok=True)
    os.makedirs(print_target, exist_ok=True)

    # Source directories in the repository
    repo_data_dir = os.path.join(GIT_REPO_DIR, "data")
    db_source = os.path.join(repo_data_dir, "01_Database")
    daily_source = os.path.join(repo_data_dir, "02_Daily_Sheets")
    print_source = os.path.join(repo_data_dir, "03_Print_PDF")

    # Helper function to copy new/updated files
    def copy_folder_contents(src, dest):
        if not os.path.exists(src):
            return 0
        copied_count = 0
        for item in os.listdir(src):
            s_path = os.path.join(src, item)
            d_path = os.path.join(dest, item)
            if os.path.isfile(s_path):
                # Copy file if it doesn't exist or is modified
                if not os.path.exists(d_path) or os.path.getmtime(s_path) > os.path.getmtime(d_path):
                    shutil.copy2(s_path, d_path)
                    print(f"   [복사] {item} -> {os.path.basename(dest)}")
                    copied_count += 1
        return copied_count

    try:
        copied_db = copy_folder_contents(db_source, db_target)
        copied_daily = copy_folder_contents(daily_source, daily_target)
        copied_print = copy_folder_contents(print_source, print_target)

        total_copied = copied_db + copied_daily + copied_print
        print("-" * 50)
        if total_copied > 0:
            print(f"🎉 동기화 완료! 총 {total_copied}개의 파일이 성공적으로 복사 및 동기화되었습니다.")
        else:
            print("✨ 이미 최신 상태입니다. 복사할 파일이 없습니다.")
    except Exception as e:
        print(f"❌ 복사 중 에러 발생: {e}")

    print("=" * 60)

if __name__ == "__main__":
    main()
