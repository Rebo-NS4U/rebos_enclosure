# System monitor process details

Select a resource in System Monitor, then expand a process tree. Indentation shows subprocess ancestry, and each row displays its name, PID, parent PID, CPU, resident memory, disk throughput and open socket count. GPU detail views also show the selected GPU's engine usage.

Collapsed totals include the tree's root process and all sampled descendants exactly once. Direct children of PID 1 form separate trees. Processes whose parents have exited or cannot be sampled appear as separate roots. Network and GPU views retain ancestors for context when descendants match the selected resource.

CPU uses 100% per core. Resident memory includes shared pages. Socket counts are not network throughput. Inaccessible disk counters display “unavailable”; process details are limited to counters accessible to the current user. No command lines or environments are collected.
