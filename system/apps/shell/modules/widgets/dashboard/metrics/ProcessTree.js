// Build disjoint process trees. Keep ancestors of metric matches for context.
function groups(rows, metric, gpuDevice) {
    const nodes = {};
    const value = row => gpuDevice ? (row.gpu[gpuDevice] || 0) : (row[metric === "network" ? "sockets" : metric] || 0);
    for (const row of rows) nodes[row.pid] = {row: row, children: []};
    const roots = [];
    for (const row of rows) {
        const parent = nodes[row.ppid];
        // PID 1 is an unhelpful umbrella for almost every application.
        if (parent && row.ppid > 1 && row.ppid !== row.pid)
            parent.children.push(nodes[row.pid]);
        else roots.push(nodes[row.pid]);
    }
    const visited = new Set();
    function walk(node, depth, output, total) {
        if (visited.has(node.row.pid)) return;
        visited.add(node.row.pid);
        const row = node.row;
        output.push(Object.assign({}, row, {depth: depth}));
        for (const key of ["cpu", "ram", "disk", "sockets"]) total[key] += row[key] || 0;
        for (const dev of Object.keys(row.gpu || {})) total.gpu[dev] = (total.gpu[dev] || 0) + row.gpu[dev];
        node.children.sort((a, b) => value(b.row) - value(a.row) || a.row.pid - b.row.pid);
        for (const child of node.children) walk(child, depth + 1, output, total);
    }
    const result = [];
    // The second pass also handles malformed/cyclic samples without dropping rows.
    for (const node of roots.concat(Object.values(nodes))) {
        if (visited.has(node.row.pid)) continue;
        const group = {ppid: node.row.pid, name: node.row.name, children: [], cpu: 0, ram: 0, disk: 0, sockets: 0, gpu: {}};
        walk(node, 0, group.children, group);
        if (gpuDevice && !group.children.some(row => gpuDevice in (row.gpu || {}))) continue;
        if (metric === "network" && !group.sockets) continue;
        result.push(group);
    }
    return result.sort((a, b) => value(b) - value(a) || a.ppid - b.ppid);
}
