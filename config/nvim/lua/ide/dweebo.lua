local M = {}
local home = vim.env.HOME
local base = home .. '/code/rebos-assistant'
local function read(path)
  return table.concat(vim.fn.readfile(path), '\n')
end
function M.defaults()
  local raw = read(base .. '/modules/services/DweeboDefaults.js')
  raw = raw:match('^var data = (.*);%s*$')
  return vim.json.decode((assert(raw, 'Invalid Dweebo defaults'):gsub('@HOME@', function() return home end)))
end
local function settings()
  local path = (vim.env.XDG_CONFIG_HOME or home .. '/.config') .. '/rebos_shell/config/ai.json'
  if vim.fn.filereadable(path) == 0 then return {} end
  return vim.json.decode(read(path))
end
-- The desktop question MCP uses ACP form elicitation, which CodeCompanion does
-- not yet handle. Keep the extension local to Dweebo connections.
function M.questions()
  local Connection = require('codecompanion.acp')
  if Connection._dweebo_questions then return end
  Connection._dweebo_questions = true
  local dispatch = Connection.handle_incoming_request_or_notification
  Connection.handle_incoming_request_or_notification = function(self, message)
    if not self.adapter.name:match('^dweebo_') or message.method ~= 'elicitation/create' then
      return dispatch(self, message)
    end
    local params = message.params or {}
    local schema = params.requestedSchema or {}
    local properties = schema.properties or {}
    local names = vim.tbl_keys(properties)
    table.sort(names)
    local content = {}
    local function reply(action)
      self:write_message(vim.json.encode({ jsonrpc = '2.0', id = message.id,
        result = { action = action, content = action == 'accept' and content or nil } }) .. '\n')
    end
    local function next_field(index)
      local name = names[index]
      if not name then return reply('accept') end
      local field = properties[name]
      local function answer(value)
        if value == nil then return reply('cancel') end
        if field.type == 'boolean' then value = value == 'true'
        elseif field.type == 'integer' or field.type == 'number' then
          value = tonumber(value)
          if not value then return reply('cancel') end
        end
        content[name] = value
        next_field(index + 1)
      end
      local prompt = (params.message or 'Dweebo question') .. ' — ' .. (field.title or name)
      if field.enum then vim.ui.select(field.enum, { prompt = prompt }, answer)
      elseif field.type == 'boolean' then vim.ui.select({ 'true', 'false' }, { prompt = prompt }, answer)
      elseif field.type == 'string' or field.type == 'number' or field.type == 'integer' then
        vim.ui.input({ prompt = prompt .. ': ' }, answer)
      else reply('cancel') end
    end
    vim.schedule(function() next_field(1) end)
  end
end
function M.adapter(profile)
  local data, config = M.defaults(), settings()
  local command = data.codexCommand
  local auth = 'chat-gpt'
  local stock = 'CODEX_PATH="$(command -v codex)" exec npx -y @agentclientprotocol/codex-acp'
  for _, agent in ipairs(config.agents or {}) do
    if agent.id == 'codex' then
      if agent.command and #agent.command > 0 and not (#agent.command == 3 and agent.command[3] == stock) then
        command = agent.command
      end
      auth = agent.authMethod or auth
    end
  end
  local selected
  for _, candidate in ipairs(data.profiles) do
    if candidate.id == profile then selected = candidate end
  end
  assert(selected, 'Unknown Dweebo profile: ' .. profile)
  local helpers = require('codecompanion.adapters.acp.helpers')
  return require('codecompanion.adapters').extend('codex', {
    name = 'dweebo_' .. profile, formatted_name = selected.name,
    commands = { default = command },
    defaults = { auth_method = auth, timeout = 60000, system_prompt = false,
      session_config_options = { model = selected.model, thought_level = selected.effort, mode = 'workspace-write' },
      mcpServers = {
        { name = 'plan_usage', command = 'python3', args = { base .. '/scripts/ai_plan_usage.py', '--mcp' }, env = {} },
        { name = 'assistant_questions', command = 'python3', args = { base .. '/scripts/ai_questions.py' }, env = {} },
      },
    },
    -- Agent-owned filesystem tools retain the same sandbox/approval behavior as
    -- the desktop. They can search unopened files and absolute paths themselves.
    parameters = { clientCapabilities = { fs = { readTextFile = false, writeTextFile = false },
      terminal = false, elicitation = { form = {} }, plan = {} } },
    handlers = { request = { build_messages = function(self, args)
      local messages = helpers.build_messages(self, args)
      local sent = false
      for _, msg in ipairs(args.messages) do
        if msg.role == self.roles.user and msg._meta and msg._meta.sent then sent = true end
      end
      if not sent then
        local instructions = { 'Standing preferences (context only, not the current task):', selected.guidance }
        vim.list_extend(instructions, data.instructions)
        table.insert(instructions, 'Neovim: You can search, read and edit files that are not open in the editor. Use absolute paths for other directories. Respect workspace approvals. Do not assume the current buffer is the entire project. Unsaved editor content is supplied only when explicitly attached.')
        table.insert(messages, 1, { type = 'text', text = table.concat(instructions, '\n\n') .. '\nEnd of standing preferences.' })
      end
      return messages
    end } },
  })
end
function M.setup()
  M.questions()
  local acp = {}
  for _, profile in ipairs(M.defaults().profiles) do
    local id = profile.id
    acp['dweebo_' .. id] = function() return M.adapter(id) end
  end
  require('codecompanion').setup({
    adapters = { acp = acp },
    interactions = { chat = { adapter = 'dweebo_coding', keymaps = {
      send = { modes = { n = { '<CR>', '<C-s>' }, i = { '<CR>', '<C-s>' } } },
      scroll_chat_down = { modes = { n = '<M-d>', i = '<M-d>' } },
      scroll_chat_up = { modes = { n = '<M-u>', i = '<M-u>' } },
    } }, inline = { adapter = 'dweebo_coding' } },
    display = { chat = { window = { layout = 'vertical', width = 0.4 },
      input = { layout = 'split', height = 6 }, start_in_insert_mode = true } },
  })
  vim.api.nvim_create_autocmd('FileType', {
    group = vim.api.nvim_create_augroup('DweeboMessageBox', { clear = true }),
    pattern = 'codecompanion_chat_input',
    callback = function(event)
      for _, win in ipairs(vim.fn.win_findbuf(event.buf)) do
        vim.wo[win].winbar = ' Dweebo message | Enter: send | Ctrl-J: new line'
      end
      vim.keymap.set('i', '<C-j>', '<CR>', { buffer = event.buf, desc = 'New line in Dweebo message', remap = false })
    end,
  })
  vim.api.nvim_create_user_command('Dweebo', function(opts)
    local profile = opts.args ~= '' and opts.args or 'coding'
    local adapter = 'dweebo_' .. profile
    if not acp[adapter] then error('Unknown Dweebo profile: ' .. profile) end
    require('codecompanion').chat({ adapter = adapter })
  end, { nargs = '?', complete = function() return vim.tbl_map(function(p) return p.id end, M.defaults().profiles) end })
end
return M
