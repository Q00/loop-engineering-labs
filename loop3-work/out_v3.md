<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>pay-api 장애 postmortem</title>
</head>
<body>
  <h1>pay-api 장애 postmortem</h1>
  <section>
    <h2>타임라인</h2>
    <p>장애는 2026-07-12 14:20 전후에 시작되었고, 14:52에 v2.3.0 롤백이 완료되었다. 15:10에는 지표가 정상 수준으로 돌아왔다.</p>
  </section>
  <section>
    <h2>근본 원인</h2>
    <p>v2.3.1이 배포되면서 <code>db_pool_size</code>가 50에서 10으로 변경되었다. canary 없이 직접 배포되어 연결 풀이 고갈되었다.</p>
  </section>
  <section>
    <h2>영향</h2>
    <p>p95 지연시간은 최고 2500ms였고, 오류율은 최고 9.8%였다.</p>
  </section>
  <section>
    <h2>근거</h2>
    <ul>
      <li>v2.3.1 배포와 <code>db_pool_size=10</code>: app.log 3행</li>
      <li>연결 풀 고갈: app.log 7행</li>
      <li>v2.3.0 롤백 완료와 <code>db_pool_size=50</code>: app.log 17행</li>
      <li>p95 2500ms: metrics.jsonl 34행</li>
      <li>오류율 9.8%: metrics.jsonl 33행</li>
    </ul>
  </section>
  <section>
    <h2>재발 방지 액션</h2>
    <ul>
      <li>canary 없는 직배포를 금지하고 단계적 배포를 의무화한다. (담당: deployer 팀)</li>
      <li>데이터베이스 풀 설정값 변경을 배포 전 검증하고 승인한다. (담당: oncall 팀)</li>
    </ul>
  </section>
</body>
</html>
