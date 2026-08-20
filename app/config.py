"""app/config.py — config.yaml 로더"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ViewerConfig:
    interval: int = 300        # 전환 간격 (초)
    mode: str = "random"       # random | sequential
    effect: str = "Fade"       # 효과 이름
    transition_ms: int = 1000  # 효과 전환 시간 (ms)
    bg_color: str = "#000000"
    geometry: str = ""         # "WxH+X+Y"  비면 fullscreen
    wakelock: bool = True


@dataclass
class CloudConfig:
    enabled: bool = False
    base_url: str = ""

@dataclass
class AppConfig:
    library_root: Path = field(default_factory=lambda: Path("./library"))
    images_dir: Path = field(default_factory=lambda: Path("./library/images"))
    rejected_dir: Path = field(default_factory=lambda: Path("./rejected"))
    cloud: CloudConfig = field(default_factory=CloudConfig)
    viewer: ViewerConfig = field(default_factory=ViewerConfig)

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "AppConfig":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"config.yaml not found: {p.resolve()}")
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        lib = data.get("library", {})
        lib_root = Path(lib.get("path", "./library"))
        images_dir = lib_root / lib.get("images_dir", "images")

        c = data.get("cloud", {})
        cloud = CloudConfig(
            enabled=bool(c.get("enabled", False)),
            base_url=str(c.get("base_url", "")).rstrip("/")
        )

        v = data.get("viewer", {})
        viewer = ViewerConfig(
            interval=int(v.get("interval", 300)),
            mode=v.get("mode", "random"),
            effect=str(v.get("effect", "Fade")),
            transition_ms=int(v.get("transition_ms", 1000)),
            bg_color=v.get("bg_color", "#000000"),
            geometry=str(v.get("geometry", "")),
            wakelock=bool(v.get("wakelock", True)),
        )
        return cls(
            library_root=lib_root,
            images_dir=images_dir,
            rejected_dir=Path("./rejected"),
            cloud=cloud,
            viewer=viewer,
        )

    def images_json_path(self) -> Path:
        return self.library_root / "images.json"

    def save_viewer_settings(self, path: str = "config.yaml") -> None:
        import re
        p = Path(path)
        if not p.exists():
            return
        content = p.read_text(encoding="utf-8")
        content = re.sub(r'(\n\s*interval:\s*)\d+', rf'\g<1>{self.viewer.interval}', content)
        content = re.sub(r'(\n\s*effect:\s*)"?[A-Za-z0-9\s]+"?(.*)', rf'\g<1>"{self.viewer.effect}"\g<2>', content)
        content = re.sub(r'(\n\s*wakelock:\s*)(true|false)', rf'\g<1>{"true" if self.viewer.wakelock else "false"}', content, flags=re.IGNORECASE)
        p.write_text(content, encoding="utf-8")
