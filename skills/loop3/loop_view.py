#!/usr/bin/env python3
"""loop_view.py: 개선 전/후 채점 결과를 나란히 그린다.

사용법: python3 loop_view.py <v1점수> <v2점수>   (각 0~5)
예:     python3 loop_view.py 2 5
"""
import sys

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("사용법: python3 loop_view.py <v1점수> <v2점수>  (각 0~5)")
    try:
        v1, v2 = (max(0, min(5, int(a))) for a in sys.argv[1:3])
    except ValueError:
        sys.exit("점수는 숫자로: python3 loop_view.py 2 5  (각 0~5)")
    print(f"{BOLD}같은 모델 · 같은 문서 · 지시서만 편집{RESET}\n")
    print(f"  편집 전  {RED}{'█' * v1}{RESET}{DIM}{'░' * (5 - v1)}{RESET}  {v1}/5")
    print(f"  편집 후  {GREEN}{'█' * v2}{RESET}{DIM}{'░' * (5 - v2)}{RESET}  {v2}/5")
    lift = v2 - v1
    sign = "+" if lift >= 0 else ""
    print(f"\n  lift {sign}{lift}  {DIM}(오른 것은 모델이 아니라 PROMPT.md다){RESET}")

if __name__ == "__main__":
    main()
