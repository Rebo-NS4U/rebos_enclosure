local map = vim.keymap.set
return {
  { 'folke/snacks.nvim', lazy = false, priority = 1000,
    opts = { picker = { enabled = true }, explorer = { enabled = true },
      input = { enabled = true }, notifier = { enabled = true }, indent = { enabled = true },
      terminal = { enabled = true }, bigfile = { enabled = true }, quickfile = { enabled = true },
      dashboard = { enabled = true, preset = { header = '\nREBO / NEOVIM\n', keys = {
        { icon = ' ', key = 'f', desc = 'Find file', action = ':lua Snacks.picker.files()' },
        { icon = ' ', key = 'g', desc = 'Search project', action = ':lua Snacks.picker.grep()' },
        { icon = ' ', key = 'r', desc = 'Recent files', action = ':lua Snacks.picker.recent()' },
        { icon = ' ', key = 'c', desc = 'Configuration', action = ':edit ~/.config/nvim/init.lua' },
        { icon = '󰋖 ', key = '?', desc = 'IDE guide', action = ':IDEHelp' },
        { icon = ' ', key = 'q', desc = 'Quit', action = ':qa' },
      } } }, },
    config = function(_, opts)
      require('snacks').setup(opts)
      local function bind(key, fn, desc) map('n', key, fn, { desc = desc }) end
      bind('<leader>e', function() Snacks.explorer() end, 'File explorer')
      bind('<leader>ff', function() Snacks.picker.files({ cwd = require('ide.tools').root(), hidden = true }) end, 'Find files')
      bind('<C-p>', function() Snacks.picker.files({ cwd = require('ide.tools').root(), hidden = true }) end, 'Find files')
      bind('<leader>fg', function() Snacks.picker.grep({ cwd = require('ide.tools').root() }) end, 'Search project')
      bind('<leader>fb', function() Snacks.picker.buffers() end, 'Open files')
      bind('<leader>fr', function() Snacks.picker.recent() end, 'Recent files')
      bind('<leader><space>', function() Snacks.picker.smart() end, 'Smart file search')
      bind('<leader>fc', function() Snacks.picker.commands() end, 'Command palette')
      bind('<leader>fk', function() Snacks.picker.keymaps() end, 'Search shortcuts')
      bind('<leader>cs', function() Snacks.picker.lsp_symbols() end, 'Document symbols')
      bind('<leader>cS', function() Snacks.picker.lsp_workspace_symbols() end, 'Workspace symbols')
      bind('gd', function() Snacks.picker.lsp_definitions() end, 'Go to definition')
      bind('grr', function() Snacks.picker.lsp_references() end, 'References')
      bind('<leader>gs', function() Snacks.picker.git_status() end, 'Git status')
      bind('<leader>gl', function() Snacks.picker.git_log() end, 'Git history')
      bind('<leader>tt', function() Snacks.terminal.toggle(nil, { cwd = require('ide.tools').root() }) end, 'Toggle terminal')
      bind('<C-/>', function() Snacks.terminal.toggle(nil, { cwd = require('ide.tools').root() }) end, 'Toggle terminal')
      bind('<leader>bd', function() Snacks.bufdelete() end, 'Close file')
      require('ide.theme').apply(true)
    end },
  { 'folke/which-key.nvim', event = 'VeryLazy', opts = {}, config = function(_, opts)
    require('which-key').setup(opts)
    require('which-key').add({
      { '<leader>f', group = 'Find' }, { '<leader>c', group = 'Code' }, { '<leader>g', group = 'Git' },
      { '<leader>b', group = 'Buffers' }, { '<leader>d', group = 'Debug' }, { '<leader>s', group = 'Splits' },
      { '<leader>t', group = 'Terminal' }, { '<leader>r', group = 'Run' }, { '<leader>x', group = 'Diagnostics' },
      { '<leader>u', group = 'UI' },
    })
  end },
  { 'nvim-tree/nvim-web-devicons', lazy = true },
  { 'nvim-lualine/lualine.nvim', dependencies = { 'nvim-tree/nvim-web-devicons' },
    config = function()
      require('lualine').setup({ options = { globalstatus = true }, sections = {
        lualine_a = { 'mode' }, lualine_b = { 'branch', 'diff', 'diagnostics' },
        lualine_c = { { 'filename', path = 1 } },
        lualine_x = { function()
          local names = vim.tbl_map(function(c) return c.name end, vim.lsp.get_clients({ bufnr = 0 }))
          return table.concat(names, ', ')
        end, 'filetype' }, lualine_y = { 'progress' }, lualine_z = { 'location' },
      } })
      require('ide.theme').apply(true)
    end },
  { 'akinsho/bufferline.nvim', version = '*', dependencies = { 'nvim-tree/nvim-web-devicons' },
    opts = { options = { diagnostics = 'nvim_lsp', always_show_bufferline = true,
      offsets = { { filetype = 'snacks_picker_list', text = 'Explorer' } } } } },
  { 'saghen/blink.cmp', version = '1.*', dependencies = { 'rafamadriz/friendly-snippets' },
    opts = { keymap = { preset = 'default', ['<Tab>'] = { 'select_next', 'snippet_forward', 'fallback' },
      ['<S-Tab>'] = { 'select_prev', 'snippet_backward', 'fallback' }, ['<CR>'] = { 'accept', 'fallback' } },
      completion = { documentation = { auto_show = true }, menu = { border = 'rounded' } },
      signature = { enabled = true, window = { border = 'rounded' } },
      fuzzy = { implementation = 'lua' }, sources = { default = { 'lsp', 'path', 'snippets', 'buffer' } } } },
  { 'neovim/nvim-lspconfig', dependencies = { 'saghen/blink.cmp', 'mason-org/mason.nvim',
      'mason-org/mason-lspconfig.nvim', 'WhoIsSethDaniel/mason-tool-installer.nvim' },
    config = function()
      require('mason').setup({ ui = { border = 'rounded' } })
      vim.lsp.config('*', { capabilities = require('blink.cmp').get_lsp_capabilities() })
      vim.lsp.config('lua_ls', { settings = { Lua = { diagnostics = { globals = { 'vim' } },
        workspace = { checkThirdParty = false }, telemetry = { enable = false } } } })
      require('mason-lspconfig').setup({ ensure_installed = {
        'lua_ls', 'pyright', 'ts_ls', 'html', 'cssls', 'jsonls', 'bashls', 'yamlls', 'clangd',
      } })
      require('mason-tool-installer').setup({ ensure_installed = { 'stylua', 'prettier', 'ruff', 'debugpy' } })
      map('n', '<leader>cm', '<Cmd>Mason<CR>', { desc = 'Manage language tools' })
    end },
  { 'stevearc/conform.nvim', opts = {
    formatters_by_ft = { lua = { 'stylua' }, python = { 'ruff_format' }, rust = { 'rustfmt' },
      javascript = { 'prettier' }, typescript = { 'prettier' }, javascriptreact = { 'prettier' },
      typescriptreact = { 'prettier' }, html = { 'prettier' }, css = { 'prettier' },
      json = { 'prettier' }, jsonc = { 'prettier' }, yaml = { 'prettier' }, markdown = { 'prettier' } },
    format_on_save = function(buf)
      if vim.b[buf].disable_autoformat then return end
      return { timeout_ms = 1500, lsp_format = 'fallback' }
    end,
  }, config = function(_, opts)
    require('conform').setup(opts)
    map({ 'n', 'v' }, '<leader>cf', function() require('conform').format({ async = true, lsp_format = 'fallback' }) end, { desc = 'Format code' })
    map('n', '<leader>uf', function()
      vim.b.disable_autoformat = not vim.b.disable_autoformat
      vim.notify('Format on save: ' .. (vim.b.disable_autoformat and 'off' or 'on'))
    end, { desc = 'Toggle format on save' })
  end },
  { 'lewis6991/gitsigns.nvim', opts = { current_line_blame = false }, config = function(_, opts)
    require('gitsigns').setup(opts)
    for key, action in pairs({ hp = 'preview_hunk', hs = 'stage_hunk', hr = 'reset_hunk', hb = 'blame_line' }) do
      map('n', '<leader>g' .. key, require('gitsigns')[action], { desc = action:gsub('_', ' ') })
    end
    map('n', ']h', function() require('gitsigns').nav_hunk('next') end, { desc = 'Next Git hunk' })
    map('n', '[h', function() require('gitsigns').nav_hunk('prev') end, { desc = 'Previous Git hunk' })
  end },
  { 'folke/trouble.nvim', opts = {}, keys = {
    { '<leader>xx', '<Cmd>Trouble diagnostics toggle<CR>', desc = 'Project diagnostics' },
    { '<leader>xq', '<Cmd>Trouble qflist toggle<CR>', desc = 'Search results' },
  } },
  { 'nvim-mini/mini.pairs', opts = {} },
  { 'nvim-mini/mini.surround', opts = {} },
  { 'mfussenegger/nvim-dap', dependencies = { 'rcarriga/nvim-dap-ui', 'nvim-neotest/nvim-nio', 'mfussenegger/nvim-dap-python' },
    config = function()
      local dap, ui = require('dap'), require('dapui')
      ui.setup()
      local python = vim.fn.stdpath('data') .. '/mason/packages/debugpy/venv/bin/python'
      require('dap-python').setup(python)
      dap.adapters.gdb = { type = 'executable', command = 'gdb', args = { '--interpreter=dap' } }
      local native = { { name = 'Launch executable', type = 'gdb', request = 'launch',
        program = function() return vim.fn.input('Executable: ', require('ide.tools').root() .. '/', 'file') end,
        cwd = '${workspaceFolder}', stopAtBeginningOfMainSubprogram = true } }
      dap.configurations.c = native; dap.configurations.cpp = native; dap.configurations.rust = native
      dap.listeners.after.event_initialized['ide_ui'] = function() ui.open() end
      dap.listeners.before.event_terminated['ide_ui'] = function() ui.close() end
      dap.listeners.before.event_exited['ide_ui'] = function() ui.close() end
      for key, fn in pairs({ ['<F5>'] = dap.continue, ['<F10>'] = dap.step_over,
        ['<F11>'] = dap.step_into, ['<F12>'] = dap.step_out, ['<leader>db'] = dap.toggle_breakpoint,
        ['<leader>dc'] = dap.continue, ['<leader>dq'] = dap.terminate, ['<leader>du'] = ui.toggle }) do
        map('n', key, fn, { desc = 'Debug: ' .. key })
      end
      map('n', '<leader>dB', function() vim.ui.input({ prompt = 'Breakpoint condition: ' }, function(c)
        if c then dap.set_breakpoint(c) end
      end) end, { desc = 'Conditional breakpoint' })
      map({ 'n', 'v' }, '<leader>de', function() ui.eval() end, { desc = 'Evaluate expression' })
      vim.fn.sign_define('DapBreakpoint', { text = '●', texthl = 'DapBreakpoint' })
      vim.fn.sign_define('DapStopped', { text = '▶', texthl = 'DapStopped', linehl = 'CursorLine' })
    end },
}
