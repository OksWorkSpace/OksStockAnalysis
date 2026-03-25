import json
from pathlib import Path


# 싱글톤 세팅 클래스
class SettingsManager:
    def __init__(self):
        # 1. 경로 설정 (현재 파일 기준 settings.json 위치)
        self.current_dir = Path(__file__).resolve().parent
        self.setting_path = self.current_dir / "settings.json"

        # 2. 기본값 설정
        self.data_folder = ""
        self.np_path = ""
        self.darts_path = ""

        # 3. 객체 생성 시 자동으로 불러오기
        self.load_settings()

    def save_settings(self):
        """현재 메모리에 있는 설정값을 JSON 파일로 저장"""
        dic_settings = {
            "data_folder": self.data_folder,
            "np_path": self.np_path,
            "darts_path": self.darts_path
        }
        try:
            with open(self.setting_path, "w", encoding='utf-8') as f:
                json.dump(dic_settings, f, indent=4, ensure_ascii=False)  # type: ignore
            print(f"설정 저장 완료: {self.setting_path}")
        except Exception as e:
            print(f"저장 중 오류 발생: {e}")

    def load_settings(self):
        """JSON 파일에서 설정값을 읽어옴. 파일이 없으면 기본값 생성"""
        if self.setting_path.exists():
            try:
                with open(self.setting_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    self.data_folder = data.get("data_folder", "")
                    self.np_path = data.get("np_path", "")
                    self.darts_path = data.get("darts_path", "")
                print(f"설정 로드 완료: {self.data_folder}")
            except Exception as e:
                print(f"로드 중 오류 발생: {e}")
        else:
            # 파일이 없을 경우 기본 경로 생성 로직
            default_data_path = self.current_dir.parent / "data"
            default_data_path.mkdir(parents=True, exist_ok=True)

            self.data_folder = str(default_data_path)
            self.save_settings()  # 기본값으로 파일 생성
            print("설정 파일이 없어 기본값을 생성했습니다.")


# 모듈 자체에서 인스턴스를 하나 생성해서 내보냄
settings = SettingsManager()
