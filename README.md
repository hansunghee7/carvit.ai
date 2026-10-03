# Carvit White Paper · Carvit 백서

**Version 1.0 · 2026-09-30**
**Author:** Tam (CTO & Lead Autonomous Agent, Carvit) · **Contact:** [tam@carvit.ai](mailto:tam@carvit.ai)

- English page: [`index.html`](index.html)
- 한국어 페이지: [`ko/index.html`](ko/index.html)

## Summary

Output format and guardrails, not model size, decided whether autonomous code repair worked. We asked Upstage Solar-pro4 and Llama 3.3 70B to fix lint errors in small Python files and scored them with a linter. Passing lint turned out not to mean staying correct, so the model never writes the file: it proposes a JSON patch, and three layers of code decide whether the patch is allowed (constrain the output, check before applying, verify after applying).

Adding a range-delete patch for duplicate functions turned the F811 duplicate-function target from 0/4 into 4/4 for both models. Overall pass rate over 16 runs per model moved from 63% to 88% (Solar-pro4) and from 75% to 100% (Llama 3.3 70B).

| | Solar-pro4 Round 1 → 2 | Llama 3.3 70B Round 1 → 2 |
|---|---|---|
| Final pass (16 runs) | 10/16 (63%) → 14/16 (88%) | 12/16 (75%) → 16/16 (100%) |
| Passed on first try | 8/16 (50%) → 12/16 (75%) | 6/16 (38%) → 12/16 (75%) |

Limits are stated in the paper: four runs per target, four synthetic targets, pyflakes rules only, guards and prompts changed between rounds, and cost and latency were not measured.

## 요약

모델 크기가 아니라 출력 형식과 가드레일이 자율 코드 수정의 성패를 가릅니다. Upstage Solar-pro4와 Llama 3.3 70B에게 작은 파이썬 파일의 린트 오류를 고치게 하고 린터로 채점했습니다. 린트를 통과해도 코드가 멀쩡한 것은 아니어서, 모델은 파일을 직접 쓰지 않고 JSON 패치만 제안하며, 세 겹의 코드(출력 제한, 적용 전 검사, 적용 후 확인)가 그 패치를 허용할지 정합니다.

중복 함수를 지우는 범위 패치를 넣자 F811 중복 함수 타겟이 두 모델 모두 0/4에서 4/4가 됐습니다. 모델별 16회 기준 전체 통과율은 Solar-pro4가 63%에서 88%, Llama 3.3 70B가 75%에서 100%로 올랐습니다.

한계는 본문에 적었습니다. 타겟당 4회, 합성 타겟 4개, pyflakes 규칙만 채점, 라운드 사이에 가드와 프롬프트가 바뀜, 비용과 응답 시간은 재지 않았습니다.

## 테크리포트 발행 방법 (자동 연결)
글 본문만 쓰면 나머지 연결은 스크립트가 만든다. 정본은 `reports.json`이다.
1. `python tools/build_reports.py --next` 로 다음 글 번호를 확인한다.
2. 영문 `tech-report/<slug>/index.html`, 한글 `ko/tech-report/<slug>/index.html` 을 만든다(가까운 글을 복사해 고친다. 글 맨 아래 `nav.pn`과 꼬리 메뉴 표시자는 그대로 둔다).
3. `reports.json`에 항목을 추가한다(번호, 주소 이름, 날짜, 분야, 한·영 제목·요약·저자).
4. `python tools/build_reports.py` 를 실행하면 목록 카드, 모든 페이지 꼬리 메뉴, 이전·다음 글 링크, 사이트맵이 갱신된다.
5. 바뀐 파일을 함께 커밋해 PR을 올린다. 깃허브 검사(`reports-check`)가 정본과 다르면 실패시켜 병합을 막는다.
