"""Check backend quota isolation and remaining allowance formatting."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PlanUsageTests(unittest.TestCase):
    def test_gemini_helper_does_not_query_codex(self):
        for app in ('assistant', 'shell'):
            helper = ROOT / 'system/apps' / app / 'scripts/ai_plan_usage.py'
            result = subprocess.run(['python3', str(helper), '--provider', 'gemini'],
                                    capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            self.assertEqual(data['provider'], 'gemini')
            self.assertNotIn('limits', data)
            self.assertIn('aistudio.google.com', data['error'])

    @unittest.skipUnless(shutil.which('node'), 'Node.js needed to exercise QML JavaScript')
    def test_refresh_never_opens_browser(self):
        for app in ('assistant', 'shell'):
            source = (ROOT / 'system/apps' / app / 'modules/services/AiSession.qml').read_text()
            start = source.index('    function refreshPlanUsage(showInChat) {')
            end = source.index('    function applyPlanUsage(data)', start)
            script = """
let geminiPlanUsage=true, planUsageSummary='', planUsageDetails='', messages=[];
const root={pushSystemMessage: message => messages.push(message), get planUsageDetails() {return planUsageDetails;}};
const Qt={openUrlExternally: () => {throw Error('Unexpected browser launch');}, callLater: fn => fn()};
""" + source[start:end] + """
refreshPlanUsage(false);
refreshPlanUsage(false);
if(messages.length) throw Error('Automatic refresh posted chat messages');
refreshPlanUsage(true);
if(messages.length !== 1) throw Error('Explicit chat request did not report quota status');
if(!planUsageSummary.includes('Gemini')) throw Error('Wrong backend label');
"""
            subprocess.run(['node', '-e', script], check=True)

    @unittest.skipUnless(shutil.which('node'), 'Node.js needed to exercise QML JavaScript')
    def test_remaining_and_stale_response(self):
        for app in ('assistant', 'shell'):
            source = (ROOT / 'system/apps' / app / 'modules/services/AiSession.qml').read_text()
            start = source.index('    function applyPlanUsage(data) {')
            end = source.index('\n    Process {', start)
            script = "let geminiPlanUsage=false, usageRequestedInChat=false, planUsageSummary='', planUsageDetails='';\n"
            script += source[start:end]
            script += '''
for (const [used, left] of [[23,77], [100,0], [0,100], [105,0], [-5,100]]) {
    applyPlanUsage({limits:[{name:'Codex',windows:[{kind:'primary',windowDurationMins:300,usedPercent:used}]}],checkedAt:1});
    if (planUsageSummary !== 'Codex 5h: ' + left + '% left') throw Error(planUsageSummary);
}
geminiPlanUsage=true; planUsageSummary='Gemini';
applyPlanUsage({error:'late Codex response'});
if (planUsageSummary !== 'Gemini') throw Error('Stale provider response');
'''
            subprocess.run(['node', '-e', script], check=True)


if __name__ == '__main__':
    unittest.main()
