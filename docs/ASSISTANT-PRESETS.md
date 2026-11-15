# Assistant presets

Do remains the default for implementing and verifying application changes.
The other presets use distinct task methods; selecting a role does not silently
change it to another role or authorize delegation.

| Preset | Specialty | Completion evidence |
| --- | --- | --- |
| Do | Focused implementation and debugging | Relevant behavior checks |
| Deep | Root-cause investigation, architecture and complex research | Tested hypotheses, regression checks or cited findings; explicit uncertainty |
| Symphony | Bounded issue execution | Acceptance criteria mapped to validation and a review handoff |
| Light | Linux configs, desktop troubleshooting and small scripts | Minimal reversible fix plus parser or behavior validation |
| Quick | Direct answers, commands, rewrites and calculations | Answer first; targeted verification when needed |
| Know | Sourced explanations, teaching and comparisons | Clear reasoning, concrete examples and evidence beside claims |

Model and reasoning settings are unchanged. Role guidance is delivered when a
conversation first uses it, when its text changes, or when the user changes roles.
Existing conversations receive revised guidance on their next prompt. QML changes
hot-reload; no desktop service restart is required.
