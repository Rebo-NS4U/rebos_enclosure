local M = {}
local map = vim.keymap.set
function M.setup()
  local options = { termguicolors = true, number = true, relativenumber = true, mouse = 'a',
    clipboard = 'unnamedplus', expandtab = true, shiftwidth = 2, tabstop = 2,
    smartindent = true, breakindent = true, wrap = false, ignorecase = true, smartcase = true,
    cursorline = true, signcolumn = 'yes', splitright = true, splitbelow = true,
    undofile = true, swapfile = true, updatetime = 250, timeoutlen = 400,
    scrolloff = 8, sidescrolloff = 8, completeopt = 'menu,menuone,noselect',
    pumheight = 12, confirm = true, laststatus = 3, showmode = false, showtabline = 2,
    winborder = 'rounded', inccommand = 'split' }
  for name, value in pairs(options) do vim.opt[name] = value end
  vim.opt.shortmess:append('c')
  vim.opt.list = true
  vim.opt.listchars = { tab = '» ', trail = '·', nbsp = '␣' }
  vim.opt.statusline = ' %{mode()}  %f %m%r %= %{v:lua.require("ide.core").status()}  %l:%c  %p%% '
  vim.opt.tabline = '%!v:lua.require("ide.core").tabs()'
  vim.g.netrw_banner = 0
  vim.g.netrw_liststyle = 3
  vim.g.netrw_winsize = 24
  vim.diagnostic.config({ virtual_text = { spacing = 3, prefix = '●' }, severity_sort = true,
    underline = true, update_in_insert = false, float = { border = 'rounded', source = true },
    signs = { text = { [1] = '', [2] = '', [3] = '', [4] = '󰌵' } } })
  map({ 'n', 'i', 'v' }, '<C-s>', '<Esc><Cmd>write<CR>', { desc = 'Save file' })
  map('n', '<leader>w', '<Cmd>write<CR>', { desc = 'Save file' })
  map('n', '<leader>q', '<Cmd>confirm quit<CR>', { desc = 'Quit window' })
  map('n', '<Esc>', '<Cmd>nohlsearch<CR>', { desc = 'Clear search' })
  for key, direction in pairs({ h = 'h', j = 'j', k = 'k', l = 'l' }) do
    map('n', '<C-' .. key .. '>', '<C-w>' .. direction, { desc = 'Focus window ' .. direction })
  end
  map('n', '<leader>sv', '<Cmd>vsplit<CR>', { desc = 'Split vertically' })
  map('n', '<leader>sh', '<Cmd>split<CR>', { desc = 'Split horizontally' })
  map('n', '<S-l>', '<Cmd>bnext<CR>', { desc = 'Next file' })
  map('n', '<S-h>', '<Cmd>bprevious<CR>', { desc = 'Previous file' })
  map('n', '<leader>bd', '<Cmd>confirm bdelete<CR>', { desc = 'Close file' })
  map('v', '<', '<gv'); map('v', '>', '>gv')
  map('t', '<Esc><Esc>', '<C-\\><C-n>', { desc = 'Leave terminal mode' })
  map('n', '<leader>e', '<Cmd>Lexplore<CR>', { desc = 'File explorer' })
  map('n', '<leader>xx', vim.diagnostic.setqflist, { desc = 'Project diagnostics' })
  map('n', '<leader>cd', vim.diagnostic.open_float, { desc = 'Line diagnostics' })
  map('n', '<leader>ca', vim.lsp.buf.code_action, { desc = 'Code action' })
  map('n', '<leader>cr', vim.lsp.buf.rename, { desc = 'Rename symbol' })
  map('n', 'gd', vim.lsp.buf.definition, { desc = 'Go to definition' })
  map('n', 'grr', vim.lsp.buf.references, { desc = 'Find references' })
  map('n', 'gD', vim.lsp.buf.declaration, { desc = 'Go to declaration' })
  map('n', 'gi', vim.lsp.buf.implementation, { desc = 'Go to implementation' })
  map('n', 'K', vim.lsp.buf.hover, { desc = 'Documentation' })
  map('i', '<C-Space>', '<C-x><C-o>', { desc = 'Completion' })
  map('i', '<Tab>', function()
    if vim.fn.pumvisible() == 1 then return '<C-n>' end
    local col = vim.fn.col('.') - 1
    if col > 0 and vim.fn.getline('.'):sub(col, col):match('%w') then return '<C-n>' end
    return '<Tab>'
  end, { expr = true, desc = 'Complete word or indent' })
  local group = vim.api.nvim_create_augroup('RebosIDE', { clear = true })
  vim.api.nvim_create_autocmd('TextYankPost', { group = group, callback = function() vim.hl.on_yank() end })
  vim.api.nvim_create_autocmd({ 'FocusGained', 'BufEnter' }, { group = group, command = 'silent! checktime' })
  vim.api.nvim_create_autocmd('FileType', { group = group, callback = function(ev)
    local lang = vim.treesitter.language.get_lang(vim.bo[ev.buf].filetype)
    if lang then pcall(vim.treesitter.start, ev.buf, lang) end
    if vim.bo[ev.buf].filetype == 'python' then vim.bo[ev.buf].shiftwidth = 4; vim.bo[ev.buf].tabstop = 4 end
  end })
  vim.api.nvim_create_autocmd('BufReadPost', { group = group, callback = function(ev)
    local row = vim.api.nvim_buf_get_mark(ev.buf, '"')[1]
    if row > 0 and row <= vim.api.nvim_buf_line_count(ev.buf) then pcall(vim.api.nvim_win_set_cursor, 0, { row, 0 }) end
  end })
  vim.api.nvim_create_autocmd('LspAttach', { group = group, callback = function(ev)
    local client = vim.lsp.get_client_by_id(ev.data.client_id)
    if not client then return end
    vim.bo[ev.buf].omnifunc = 'v:lua.vim.lsp.omnifunc'
    if not package.loaded['blink.cmp'] and client:supports_method('textDocument/completion') then
      vim.lsp.completion.enable(true, client.id, ev.buf, { autotrigger = true })
    end
    if client:supports_method('textDocument/inlayHint') then vim.lsp.inlay_hint.enable(true, { bufnr = ev.buf }) end
  end })
end
function M.status()
  local count = vim.diagnostic.count(0)
  local clients = vim.lsp.get_clients({ bufnr = 0 })
  local names = vim.tbl_map(function(c) return c.name end, clients)
  return string.format('E:%d W:%d  %s  %s', count[1] or 0, count[2] or 0, table.concat(names, ', '), vim.bo.filetype)
end
function M.tabs()
  local out = {}
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.bo[buf].buflisted then
      local name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(buf), ':t')
      name = (name ~= '' and name or '[New file]'):gsub('%%', '%%%%')
      out[#out + 1] = (buf == vim.api.nvim_get_current_buf() and '%#TabLineSel#' or '%#TabLine#') ..
        ' ' .. buf .. ': ' .. name .. (vim.bo[buf].modified and ' ●' or '') .. ' '
    end
  end
  return table.concat(out) .. '%#TabLineFill#'
end
return M
