const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').resolve(__dirname,
    '../../system/apps/shell/modules/services/Battery.qml'), 'utf8');
const functions = source.slice(source.indexOf('    function evaluateBatteryAlert()'), source.indexOf('    Connections {'));
let sent = 0;
const notifications = {
    list: [], triggerListChange() {}, saveNotifications() {},
    notifyInternal(options) { sent++; this.list = [{...options, id: sent, popup: true}]; },
    discardNotifications() { this.list = []; }
};
const ctx = { available: true, isPluggedIn: false, percentage: 20,
    lastBatteryAlertThreshold: 0, Notifications: notifications,
    timeToEmpty: '', PowerProfile: {currentProfile: 'balanced'},
    NotificationUrgency: {Critical: 2} };
vm.createContext(ctx);
vm.runInContext(functions, ctx);
ctx.evaluateBatteryAlert();
const first = notifications.list[0];
for (const percentage of [19, 18, 17, 21]) {
    ctx.percentage = percentage;
    ctx.evaluateBatteryAlert();
    assert.equal(notifications.list[0], first);
    assert.equal(first.summary, `Low battery · ${percentage}%`);
}
assert.equal(sent, 1);
notifications.list = [];
ctx.percentage = 16;
ctx.evaluateBatteryAlert();
assert.equal(notifications.list.length, 0, 'dismissed warning stays dismissed');
ctx.percentage = 10;
ctx.evaluateBatteryAlert();
assert.equal(sent, 2, 'lower threshold escalates');
ctx.percentage = 9;
ctx.evaluateBatteryAlert();
assert.equal(notifications.list[0].summary, 'Very low battery · 9%');
ctx.isPluggedIn = true;
ctx.evaluateBatteryAlert();
assert.equal(notifications.list.length, 0);
ctx.isPluggedIn = false;
ctx.percentage = 20;
ctx.evaluateBatteryAlert();
ctx.percentage = 23;
ctx.evaluateBatteryAlert();
assert.equal(notifications.list.length, 0, 'recovery clears warning');
console.log('Battery notification updates, dismissal, escalation and recovery passed');
