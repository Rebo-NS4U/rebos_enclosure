---
name: quick-answer
description: Answer short command, conversion and calculation requests accurately with minimal overhead. Skip extended research and multi-file debugging.
---

Give the requested answer or artifact first. Use no tools for ordinary wording or well-established explanations.

For decimal arithmetic, run `python3 ../../scripts/preset_tools.py calculate 'EXPRESSION'` relative to this skill directory. Supported syntax: decimal literals, parentheses, unary plus/minus, +, -, *, /. Results use 28 significant decimal digits; repeating fractions are rounded, not exact. Do not use it for units or scientific functions. Normalize units explicitly before arithmetic. Never evaluate user expressions with shell substitution or unrestricted eval.

For command answers, establish the relevant platform only if syntax differs. Look up unfamiliar flags in the installed help or official docs. A command suggestion is not an executed action. On an explicitly requested action, run the command through the normal approved execution tool and check its result. For uncertain current facts, use one focused search and open the supporting source. Offer a deeper role only if more investigation is actually needed.
