#!/usr/bin/env python3
"""
detect.py — 연결된 모든 디스플레이 위치/크기 출력
portrait_frame 폴더에서: python detect.py
"""
import subprocess
import sys


def main():
    print()
    print("=" * 50)
    print("  PortraitFrame — Display Detection")
    print("=" * 50)

    # Tkinter 기본 화면 크기
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.update()
        sw = r.winfo_screenwidth()
        sh = r.winfo_screenheight()
        r.destroy()
        print(f"\n  Primary display (Tkinter): {sw} x {sh}")
    except Exception as e:
        print(f"  tkinter error: {e}")
        sw, sh = 0, 0

    # system_profiler 로 실제 연결된 디스플레이 목록
    print("\n  Connected displays (system_profiler):")
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPDisplaysDataType"],
            text=True, timeout=10
        )
        # Resolution 라인만 파싱
        for line in out.splitlines():
            s = line.strip()
            if any(k in s for k in ("Resolution", "Display", "UI Looks", "Mirror")):
                print(f"    {s}")
    except Exception as e:
        print(f"    system_profiler error: {e}")

    # geometry 후보 출력
    print()
    print("  ─" * 25)
    print("  config.yaml geometry 후보:")
    print()
    if sw > 0:
        # 가장 흔한 레이아웃
        candidates = [
            (f"  오른쪽 모니터:  geometry: \"1440x3440+{sw}+0\""),
            (f"  왼쪽 모니터:   geometry: \"1440x3440-1440+0\""),
            (f"  위쪽 모니터:   geometry: \"1440x3440+0-3440\""),
            (f"  아래쪽 모니터: geometry: \"1440x3440+0+{sh}\""),
        ]
        for c in candidates:
            print(c)
    print()
    print("  → 시스템 설정 > 디스플레이 > 배열 에서 위치 확인 후")
    print("    config.yaml 의 geometry 에 입력하세요.")
    print()


if __name__ == "__main__":
    main()
