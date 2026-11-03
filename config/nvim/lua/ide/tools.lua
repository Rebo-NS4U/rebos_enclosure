local M = {}
local map = vim.keymap.set
function M.root()
  return vim.fs.root(0, { '.git', 'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod' }) or vim.fn.getcwd()
end
function M.files()
  local root = M.root()
  local cmd = vim.fn.executable('fd') == 1 and { 'fd', '--type', 'f', '--hidden', '--exclude', '.git' }
    or { 'find', '.', '-type', 'f' }
  vim.system(cmd, { cwd = root, text = true }, vim.schedule_wrap(function(result)
    if result.code ~= 0 then vim.notify(result.stderr, vim.log.levels.ERROR); return end
    local files = vim.split(result.stdout or '', '\n', { trimempty = true })
    vim.ui.select(files, { prompt = 'Find file' }, function(choice)
      if choice then vim.cmd.edit(vim.fn.fnameescape(root .. '/' .. choice)) end
    end)
  end))
end
function M.grep()
  vim.ui.input({ prompt = 'Search project (regex): ' }, function(query)
    if not query or query == '' then return end
    local root = M.root()
    vim.system({ 'rg', '--vimgrep', '--smart-case', '--', query, root }, { text = true }, vim.schedule_wrap(function(result)
      if result.code > 1 then vim.notify(result.stderr, vim.log.levels.ERROR); return end
      vim.fn.setqflist({}, ' ', { title = 'Search: ' .. query,
        lines = vim.split(result.stdout or '', '\n', { trimempty = true }), efm = '%f:%l:%c:%m' })
      if result.code == 1 then vim.notify('No matches') else vim.cmd.copen() end
    end))
  end)
end
function M.terminal(cmd)
  local root = M.root()
  if not cmd and M.term and vim.api.nvim_buf_is_valid(M.term) then
    local win = vim.fn.bufwinid(M.term)
    if win ~= -1 then vim.api.nvim_win_close(win, false); return end
    vim.cmd('botright 14split'); vim.api.nvim_win_set_buf(0, M.term); vim.cmd.startinsert(); return
  end
  vim.cmd('botright 14new')
  if not cmd then M.term = vim.api.nvim_get_current_buf() end
  vim.bo.bufhidden = 'hide'
  vim.fn.jobstart(cmd or { vim.o.shell }, { term = true, cwd = root })
  vim.cmd.startinsert()
end
function M.run()
  vim.ui.input({ prompt = 'Run command: ', default = M.last_command or '' }, function(command)
    if command and command ~= '' then
      M.last_command = command
      M.terminal({ vim.o.shell, '-c', command })
    end
  end)
end
function M.git(args, title)
  vim.system(vim.list_extend({ 'git' }, args), { cwd = M.root(), text = true }, vim.schedule_wrap(function(result)
    if result.code ~= 0 then vim.notify(result.stderr, vim.log.levels.WARN); return end
    vim.cmd('botright new')
    vim.bo.buftype = 'nofile'; vim.bo.bufhidden = 'wipe'; vim.bo.swapfile = false
    vim.api.nvim_buf_set_name(0, title .. ' [' .. vim.api.nvim_get_current_buf() .. ']')
    vim.api.nvim_buf_set_lines(0, 0, -1, false, vim.split(result.stdout or '', '\n'))
    vim.bo.filetype = title == 'Git diff' and 'diff' or 'git'
    vim.bo.modifiable = false
    map('n', 'q', '<Cmd>close<CR>', { buffer = true, desc = 'Close Git view' })
  end))
end
function M.format()
  local ft, buf = vim.bo.filetype, vim.api.nvim_get_current_buf()
  local configs = {
    lua = { 'stylua', '-' }, python = { 'ruff', 'format', '--stdin-filename', vim.api.nvim_buf_get_name(buf), '-' },
    rust = { 'rustfmt', '--edition', '2021' },
  }
  local web = { javascript = true, typescript = true, javascriptreact = true, typescriptreact = true,
    json = true, jsonc = true, html = true, css = true, yaml = true, markdown = true }
  local cmd = configs[ft]
  if web[ft] then cmd = { 'prettier', '--stdin-filepath', vim.api.nvim_buf_get_name(buf) } end
  if cmd and vim.fn.executable(cmd[1]) == 1 then
    local tick = vim.api.nvim_buf_get_changedtick(buf)
    vim.system(cmd, { text = true, stdin = table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), '\n') .. '\n', cwd = M.root() },
      vim.schedule_wrap(function(result)
        if result.code ~= 0 then vim.notify(result.stderr, vim.log.levels.ERROR); return end
        if not vim.api.nvim_buf_is_valid(buf) or tick ~= vim.api.nvim_buf_get_changedtick(buf) then
          vim.notify('Buffer changed while formatting; retry'); return
        end
        local lines = vim.split(result.stdout or '', '\n')
        if lines[#lines] == '' then table.remove(lines) end
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
      end))
  else
    for _, client in ipairs(vim.lsp.get_clients({ bufnr = buf })) do
      if client:supports_method('textDocument/formatting') then vim.lsp.buf.format({ async = true }); return end
    end
    vim.notify('No formatter for ' .. ft .. '. Use :IDEInstall, then :Mason.', vim.log.levels.INFO)
  end
end
function M.setup()
  vim.ui.select = require('ide.picker').select
  map('n', '<leader>ff', M.files, { desc = 'Find files' })
  map('n', '<C-p>', M.files, { desc = 'Find files' })
  map('n', '<leader>fg', M.grep, { desc = 'Search project' })
  map('n', '<leader>fb', function()
    local bufs = vim.tbl_filter(function(b) return vim.bo[b].buflisted end, vim.api.nvim_list_bufs())
    vim.ui.select(bufs, { prompt = 'Open files', format_item = function(b) return vim.api.nvim_buf_get_name(b) end },
      function(b) if b then vim.api.nvim_set_current_buf(b) end end)
  end, { desc = 'Open files' })
  map('n', '<leader>tt', function() M.terminal() end, { desc = 'Toggle terminal' })
  map('n', '<C-/>', function() M.terminal() end, { desc = 'Toggle terminal' })
  map('n', '<leader>rr', M.run, { desc = 'Run project command' })
  map('n', '<leader>gs', function() M.git({ 'status', '--short', '--branch' }, 'Git status') end, { desc = 'Git status' })
  map('n', '<leader>gd', function() M.git({ 'diff' }, 'Git diff') end, { desc = 'Git diff' })
  map('n', '<leader>cf', M.format, { desc = 'Format file' })
  map('n', '<leader>cs', vim.lsp.buf.document_symbol, { desc = 'Document symbols' })
  map('n', '<leader>?', '<Cmd>IDEHelp<CR>', { desc = 'IDE guide' })
  map('n', '<F5>', function()
    vim.cmd('packadd termdebug')
    vim.cmd.Termdebug()
  end, { desc = 'Start GDB debugger' })
  vim.api.nvim_create_user_command('IDEHelp', function()
    vim.cmd('tabnew ' .. vim.fn.fnameescape(vim.fn.stdpath('config') .. '/README.md'))
  end, {})
  -- These also work without a plugin manager, whenever the executables exist.
  local servers = {
    lua_ls = { cmd = { 'lua-language-server' }, filetypes = { 'lua' }, root_markers = { '.luarc.json', '.git' },
      settings = { Lua = { diagnostics = { globals = { 'vim' } }, telemetry = { enable = false } } } },
    pyright = { cmd = { 'pyright-langserver', '--stdio' }, filetypes = { 'python' }, root_markers = { 'pyproject.toml', '.git' } },
    ts_ls = { cmd = { 'typescript-language-server', '--stdio' }, filetypes = { 'javascript', 'typescript', 'javascriptreact', 'typescriptreact' }, root_markers = { 'tsconfig.json', 'package.json', '.git' } },
    clangd = { cmd = { 'clangd' }, filetypes = { 'c', 'cpp' }, root_markers = { 'compile_commands.json', '.git' } },
    rust_analyzer = { cmd = { 'rust-analyzer' }, filetypes = { 'rust' }, root_markers = { 'Cargo.toml', '.git' } },
    bashls = { cmd = { 'bash-language-server', 'start' }, filetypes = { 'sh', 'bash' }, root_markers = { '.git' } },
  }
  for name, config in pairs(servers) do
    local available = vim.fn.executable(config.cmd[1]) == 1
    if available and name == 'rust_analyzer' then
      available = vim.system({ config.cmd[1], '--version' }, { text = true, timeout = 3000 }):wait().code == 0
    end
    if available then vim.lsp.config(name, config); vim.lsp.enable(name) end
  end
end
return M
