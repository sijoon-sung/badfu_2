# 연구를 정리할 때 참고한 글

2026년 10월 19일 원문을 읽고 아래 원칙을 적용했다. 생물정보학 분야에서 쓰인 연구 관리 지침을 계산 실험 정리에 적용한 것이며 BadFU 방법의 성능 근거는 아니다.

| 참고 글 | 적용한 원칙 | 이 폴더에 반영한 방식 |
|---|---|---|
| [Noble 2023 프로젝트 정의](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1010786) | 문제·입출력·중심 가설과 검증 수단부터 좁힘 | 각 갈래의 핵심 질문과 다음 확인 하나 |
| [Noble 2009 계산 연구 폴더 구성](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000424) | 논리적 프로젝트 구조와 재실행 가능한 실험 기록 | 재현·정화·탐지를 최상위로, 파생 방법을 그 아래로 |
| [Wilson 외 2017 계산 연구 실무](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005510) | 개요를 짧게 유지하고 코드·원자료·결과를 구분하며 중복을 줄임 | 기존 구현을 복제하지 않고 경로·해시로 연결 |
| [Pautasso 2013 문헌 검토](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003149) | 범위와 제외 기준을 정하고 단순 나열보다 비판적 종합 | 주요 근거만 남기고 나머지는 제외 이유와 함께 보관 |

이 구조에서 새 방법을 늘릴 기준은 실험 수가 아니라 **기존법으로 해결되지 않는 문제가 있고, 그 차이를 확인할 비교가 있는가**다. 세부 학습률·시드·패치 수 변경은 부모 방법 안의 설정과 결과로 관리한다.
