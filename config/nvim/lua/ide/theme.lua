local M = {}
local path = vim.fn.expand('~/.cache/rebos_shell/effective-palette.json')
local last
local fallback = { primary = '#ffb4a2', secondary = '#e7bdb3', tertiary = '#dac58d',
  overSurface = '#f1dfda', outline = '#a08c88', outlineVariant = '#534340',
  surfaceContainerLow = '#271d1b', surfaceContainerHigh = '#3d3230',
  green = '#b7d085', red = '#ffb4a5', yellow = '#dec56e', blue = '#cebdfe',
  cyan = '#84d5c4', magenta = '#fcb0d5' }
function M.apply(force)
  local ok, lines = pcall(vim.fn.readfile, path)
  local raw = ok and table.concat(lines, '\n') or ''
  if not force and raw == last then return end
  local parsed, p = pcall(vim.json.decode, raw)
  if parsed and type(p) == 'table' then
    p = vim.tbl_extend('force', fallback, p)
    for k, v in pairs(p) do
      if type(v) == 'string' and not v:match('^#%x%x%x%x%x%x$') then p[k] = fallback[k] end
    end
  else p = fallback end
  last = raw
  M.palette = p
  vim.o.background = 'dark'
  vim.g.colors_name = 'rebos'
  local function hi(names, spec)
    for name in names:gmatch('%S+') do vim.api.nvim_set_hl(0, name, spec) end
  end
  hi('Normal NormalNC NormalFloat SignColumn FoldColumn EndOfBuffer', { fg = p.overSurface, bg = 'NONE' })
  hi('FloatBorder WinSeparator', { fg = p.primary, bg = 'NONE' })
  hi('LineNr Comment NonText Whitespace', { fg = p.outline })
  hi('CursorLineNr', { fg = p.primary, bold = true })
  hi('CursorLine', { bg = p.surfaceContainerLow })
  hi('Visual PmenuSel', { bg = p.primary, fg = p.overPrimary or '#561f11' })
  hi('Pmenu PmenuSbar', { bg = p.surfaceContainerLow, fg = p.overSurface })
  hi('PmenuThumb', { bg = p.primary })
  hi('StatusLine TabLineSel', { fg = p.primary, bg = p.surfaceContainerLow, bold = true })
  hi('StatusLineNC TabLine TabLineFill', { fg = p.outline, bg = 'NONE' })
  hi('Search IncSearch CurSearch', { fg = '#000000', bg = p.tertiary })
  hi('MatchParen', { fg = p.magenta, bold = true, underline = true })
  hi('Directory Title Function @function @function.call @method @constructor', { fg = p.primary, bold = true })
  hi('Statement Keyword Conditional Repeat Exception @keyword @operator', { fg = p.magenta })
  hi('String Character @string', { fg = p.green })
  hi('Number Boolean Constant @number @boolean @constant', { fg = p.tertiary })
  hi('Type Structure Typedef @type @module', { fg = p.blue })
  hi('Identifier @variable @variable.parameter', { fg = p.overSurface })
  hi('Special @property @attribute @tag', { fg = p.cyan })
  hi('Operator Delimiter @punctuation', { fg = p.secondary })
  hi('DiagnosticError ErrorMsg GitSignsDelete', { fg = p.red })
  hi('DiagnosticWarn WarningMsg GitSignsChange', { fg = p.yellow })
  hi('DiagnosticInfo', { fg = p.blue })
  hi('DiagnosticHint GitSignsAdd', { fg = p.green })
  hi('DiagnosticUnderlineError', { sp = p.red, undercurl = true })
  hi('DiagnosticUnderlineWarn', { sp = p.yellow, undercurl = true })
  hi('DiffAdd', { bg = p.greenContainer or '#253600' })
  hi('DiffDelete', { bg = p.redContainer or '#561f14' })
  hi('DiffChange DiffText', { bg = p.surfaceContainerHigh })
  hi('SnacksPickerBorder SnacksDashboardHeader WhichKey', { fg = p.primary })
  hi('SnacksPickerMatch WhichKeyGroup', { fg = p.tertiary, bold = true })
  hi('BlinkCmpMenuBorder', { fg = p.primary })
  hi('DapBreakpoint', { fg = p.red })
  hi('DapStopped', { fg = p.green })
  local ansi = { '#000000', p.red, p.green, p.yellow, p.blue, p.magenta, p.cyan, p.overSurface }
  for i, color in ipairs(ansi) do
    vim.g['terminal_color_' .. (i - 1)] = color
    vim.g['terminal_color_' .. (i + 7)] = color
  end
  if package.loaded['lualine'] then
    local function mode(color) return { a = { fg = '#000000', bg = color, gui = 'bold' },
      b = { fg = p.overSurface, bg = p.surfaceContainerLow }, c = { fg = p.outline, bg = 'NONE' } } end
    require('lualine').setup({ options = { theme = { normal = mode(p.primary), insert = mode(p.green),
      visual = mode(p.magenta), replace = mode(p.red), command = mode(p.tertiary), inactive = mode(p.outline) } } })
  end
end
function M.setup()
  M.apply(true)
  local group = vim.api.nvim_create_augroup('RebosPalette', { clear = true })
  vim.api.nvim_create_autocmd({ 'FocusGained', 'ColorScheme' }, { group = group, callback = function() M.apply(true) end })
  -- Poll the JSON rather than watching its inode: the shell replaces it atomically.
  local timer = assert(vim.uv.new_timer())
  timer:start(2000, 2000, vim.schedule_wrap(function() M.apply() end))
  vim.api.nvim_create_autocmd('VimLeavePre', { group = group, callback = function() timer:stop(); timer:close() end })
  vim.api.nvim_create_user_command('ThemeReload', function() M.apply(true) end, {})
end
return M
