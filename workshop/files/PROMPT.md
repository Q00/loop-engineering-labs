# 하네스 생성 프롬프트 (AI 코딩 도구에 그대로 붙여넣는다)

아래 명세대로 miniloop.py 하나를 만들어라. Python 표준 라이브러리만 쓰고, 파일 하나로 끝낸다.

[과제]
회의록에서 나온 지저분한 액션 아이템 한 줄을 정리된 한 줄로 바꾼다.
예: "  [ ] 배포 스크립트 고치기 @민수 ASAP  " → "@민수 배포 스크립트 고치기"

[파일]
- tasks.json : 같은 폴더에 이미 있다. {"id","split","input","expected"} 목록.
               split은 "train" 6개, "heldout" 4개.
- prompt.txt : 같은 폴더에 이미 있다. 지시서. 규칙 이름 한 줄에 하나.

[규칙 사전: prompt.txt에 나올 수 있는 전체 목록]
지시서에 적힌 규칙만 적용한다. 적용 순서는 파일의 줄 순서와 무관하게 아래 순서로 고정한다.
1. strip-checkbox : 앞쪽 공백과 "[ ]"/"[x]" 마커를 제거한다. 마커 뒤 공백은 남긴다.
2. drop-urgency   : "!" 문자를 모두 지우고, "ASAP"/"급함"/"빨리"와 정확히 일치하는
                    토큰(공백 기준)을 제거한다. 남는 공백은 그대로 둔다.
3. assignee-first : "@"로 시작하는 첫 토큰을 문장 맨 앞으로 옮기고 뒤에 공백 하나를 둔다.
                    나머지 텍스트는 글자 그대로 둔다.
4. collapse-spaces: 연속 공백을 하나로 줄이고 앞뒤 공백을 제거한다.

[명령 세 개]
- run   : train 사례를 지시서대로 변환해 expected와 비교한다.
          {"split": "train", "score": 0.333, "passed": 2, "total": 6} 형태로 출력.
          사례마다 한 줄씩 trace.jsonl에 append한다 (id, input, expected, got, pass).
- trace : trace.jsonl의 마지막 run 기준으로, 실패한 사례만 "입력/기대/실제"를 나란히 보여준다.
- gate  : --candidate <파일> 로 받은 새 지시서를 heldout으로만 채점해, 현재 prompt.txt
          점수보다 높을 때만 accept하고 prompt.txt를 그 내용으로 덮어쓴다. 아니면 reject.
          {"verdict": "accept", "current": 0.25, "candidate": 1.0} 형태로 출력.

[불변식: 어기면 다시 만들게 한다]
1. gate는 heldout만 채점한다. train을 쓰지 않고, trace.jsonl에도 쓰지 않는다.
2. 같은 입력이면 항상 같은 점수. 판정에 타임스탬프·난수·네트워크가 끼면 안 된다.
3. 모든 파일 입출력은 encoding="utf-8"로 한다. Windows에서 한글이 깨지지 않게.
