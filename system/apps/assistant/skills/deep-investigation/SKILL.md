---
name: deep-investigation
description: Investigate difficult failures and architecture or research questions through discriminating evidence. Skip small routine fixes.
---

Define the observed failure and expected behavior. Keep a compact hypothesis list with the evidence that would distinguish each cause; avoid gathering logs without a question they can resolve.

For bugs, obtain the smallest realistic reproducer, trace the failing boundary, and change one causal assumption at a time. Prefer a regression check that fails before the fix and succeeds after it. For architecture, compare candidates against the user's constraints and identify migration costs, reversibility and failure modes.

For research, open primary sources and keep claim, source, date and uncertainty together. Use connected library documentation tools such as Context7 only after discovery confirms they are available, and match the installed dependency version. A web result or plugin description alone does not establish a conclusion.

Stop when the acceptance criteria are supported. Report the result, decisive evidence, relevant checks and unresolved risks. If blocked, name the smallest missing observation. Do not silently switch models, spawn agents or expand the project.
