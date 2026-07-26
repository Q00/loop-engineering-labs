# STEP 1 프롬프트

AI 코딩 도구에 그대로 붙여 넣으세요.

```
Create a single-file Python program `miniloop.py` (stdlib only, Python 3.10+).

RULES: prompt.txt lists enabled rule names, one per line. Unknown name -> exit 2.
Known rules, always applied in THIS fixed order regardless of file order:
  lowercase       -> str.lower()
  strip-punct     -> delete every char that is not alphanumeric or whitespace
  drop-stopwords  -> replace whole tokens the/a/an/of with "" (keep whitespace)
  collapse-spaces -> squeeze whitespace runs to one space, then strip
  hyphenate       -> replace every space with "-"

run   : apply rules to every tasks.json "train" case, append one JSONL line per
        case to trace.jsonl {run_id, case_id, input, expected, output, passed},
        print JSON {"split":"train","score":<passed/total>,"passed":n,"total":m}.
trace : print only the failed cases of the latest run_id, as
        case_id / input / expected / output, so a human can see the pattern.
gate  : take --candidate FILE. Score the current prompt.txt and the candidate on
        the "heldout" split ONLY (never train, never write to trace.jsonl).
        Accept only on strict improvement. Print JSON
        {"verdict":"accept"|"reject","current":x,"candidate":y}.
        On accept, copy the candidate over prompt.txt.

Exact string match, scores rounded to 3 decimals. case_id = t1..t6 (train) and
h1..h4 (heldout), in file order. No LLM, no network. Same input -> same score.
```
