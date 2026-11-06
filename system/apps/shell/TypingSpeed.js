.pragma library

// Net correct characters, five characters per word. Pauses over five seconds
// stop the clock; restored text and chapter jumps never add to the count.
function create() { return {elapsed: 0, lastTick: 0, lastInput: 0}; }
function tick(state, now, active) {
    var elapsed = state.elapsed;
    if (active && state.lastTick && state.lastInput)
        elapsed += Math.max(0, Math.min(now, state.lastInput + 5000) - state.lastTick);
    return {elapsed: elapsed, lastTick: now, lastInput: state.lastInput};
}
function record(state, now) {
    var next = tick(state, now, true);
    next.lastInput = now;
    return next;
}
function pause(state) { return {elapsed: state.elapsed, lastTick: 0, lastInput: 0}; }
function rate(state, correct, now) {
    if (state.elapsed < 1000 || !state.lastInput || now - state.lastInput >= 5000) return 0;
    return Math.max(0, Math.round(correct * 12000 / state.elapsed));
}
