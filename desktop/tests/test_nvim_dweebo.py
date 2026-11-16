"""Exercise the real editor adapter without a model call or desktop session."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LAZY = Path.home() / '.local/share/nvim/lazy'


@unittest.skipUnless(shutil.which('nvim') and (LAZY / 'codecompanion.nvim').is_dir(),
                     'Neovim and installed CodeCompanion required')
class DweeboEditorTest(unittest.TestCase):
    def test_profiles_context_and_questions(self):
        script = r'''
local root, lazy = arg[1], arg[2]
vim.opt.rtp:prepend(root .. '/config/nvim')
vim.opt.rtp:prepend(lazy .. '/codecompanion.nvim')
vim.opt.rtp:prepend(lazy .. '/plenary.nvim')
local dweebo = require('ide.dweebo')
dweebo.setup()
local data = dweebo.defaults()
assert(#data.profiles == 6)
for _, profile in ipairs(data.profiles) do
  local a = dweebo.adapter(profile.id)
  assert(a.defaults.auth_method == 'chat-gpt')
  assert(a.defaults.session_config_options.model == profile.model)
  assert(a.defaults.session_config_options.thought_level == profile.effort)
  assert(a.defaults.session_config_options.mode == 'workspace-write')
  assert(not a.parameters.clientCapabilities.fs.writeTextFile)
  assert(a.parameters.clientCapabilities.elicitation.form)
  assert(a.commands.default[3]:find('codex_workspace.py',1,true))
  local build = a.handlers.request.build_messages
  local initial = build(a, {messages={{role='user', content='Do my task',_meta={}}}, capabilities={}})
  assert(initial[1].text:find(profile.guidance,1,true))
  assert(initial[1].text:find('GitHub workflow:',1,true))
  assert(initial[1].text:find('not open in the editor',1,true))
  assert(initial[1].text:find('Keep Token Optimizer enabled',1,true))
  assert(initial[#initial].text == 'Do my task')
  local followup = build(a, {messages={
    {role='user', content='Previous', _meta={sent=true}},
    {role='user', content='Continue', _meta={}},
  }, capabilities={}})
  assert(#followup == 1 and followup[1].text == 'Continue')
end
local Connection = require('codecompanion.acp')
local reply
local fake = {adapter={name='dweebo_coding'}, write_message=function(_, raw) reply=vim.json.decode(raw) end}
vim.ui.select = function(options, _, cb) cb(options[2]) end
vim.ui.input = function(_, cb) cb('details') end
Connection.handle_incoming_request_or_notification(fake, {
  id=17, method='elicitation/create',params={message='Choose',requestedSchema={properties={
    answer={type='string',enum={'First','Second'}}, details={type='string'},
  }}}
})
assert(vim.wait(1000,function() return reply ~= nil end))
assert(reply.id == 17 and reply.result.action == 'accept')
assert(reply.result.content.answer == 'Second' and reply.result.content.details == 'details')
reply=nil
vim.ui.select=function(_,_,cb) cb(nil) end
Connection.handle_incoming_request_or_notification(fake, {
  id=18,method='elicitation/create',params={requestedSchema={properties={answer={type='string',enum={'A','B'}}}}}
})
assert(vim.wait(1000,function() return reply ~= nil end))
assert(reply.result.action == 'cancel')
print('PASS Dweebo profiles, first-turn instructions, followups and question forms')
'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'test.lua'
            path.write_text(script)
            result = subprocess.run(['nvim', '--headless', '-u', 'NONE', '-l', str(path),
                                     str(ROOT), str(LAZY)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS Dweebo', result.stdout + result.stderr)
