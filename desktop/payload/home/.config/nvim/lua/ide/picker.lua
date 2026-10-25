local M = {}
function M.select(items, opts, callback)
  opts = opts or {}
  if #items == 0 then callback(nil); return end
  local records = {}
  for idx, item in ipairs(items) do
    records[#records + 1] = { text = (opts.format_item and opts.format_item(item) or tostring(item)):gsub('\n', ' '), idx = idx }
  end
  local height = math.max(1, math.min(14, vim.o.lines - 8, #items))
  local width = math.max(20, math.min(90, vim.o.columns - 6))
  local row = math.max(1, math.floor((vim.o.lines - height - 5) / 2))
  local col = math.floor((vim.o.columns - width) / 2)
  local input, list = vim.api.nvim_create_buf(false, true), vim.api.nvim_create_buf(false, true)
  vim.bo[input].bufhidden = 'wipe'; vim.bo[list].bufhidden = 'wipe'
  local listwin = vim.api.nvim_open_win(list, false, { relative = 'editor', row = row + 3, col = col,
    width = width, height = height, style = 'minimal', border = 'rounded', focusable = false })
  local inputwin = vim.api.nvim_open_win(input, true, { relative = 'editor', row = row, col = col,
    width = width, height = 1, style = 'minimal', border = 'rounded', title = ' ' .. (opts.prompt or 'Select') .. ' ' })
  vim.wo[listwin].cursorline = true
  local matches, selected, closed = records, 1, false
  local function render()
    local lines = {}
    for i = 1, math.min(#matches, 200) do lines[i] = ' ' .. matches[i].text end
    if #lines == 0 then lines = { ' No matches' } end
    vim.api.nvim_buf_set_lines(list, 0, -1, false, lines)
    if #matches > 0 then vim.api.nvim_win_set_cursor(listwin, { selected, 0 }) end
  end
  local function finish(accept)
    if closed then return end
    closed = true
    local record = accept and matches[selected] or nil
    vim.cmd.stopinsert()
    if vim.api.nvim_win_is_valid(inputwin) then vim.api.nvim_win_close(inputwin, true) end
    if vim.api.nvim_win_is_valid(listwin) then vim.api.nvim_win_close(listwin, true) end
    vim.schedule(function() callback(record and items[record.idx] or nil, record and record.idx or nil) end)
  end
  local function move(delta)
    local count = math.min(#matches, 200)
    if count == 0 then return end
    selected = ((selected - 1 + delta) % count) + 1
    render()
  end
  vim.api.nvim_create_autocmd({ 'TextChangedI', 'TextChanged' }, { buffer = input, callback = function()
    local query = vim.api.nvim_buf_get_lines(input, 0, 1, false)[1] or ''
    matches = query == '' and records or vim.fn.matchfuzzy(records, query, { key = 'text' })
    selected = 1
    render()
  end })
  vim.api.nvim_create_autocmd('WinClosed', { pattern = tostring(inputwin), once = true, callback = function() finish(false) end })
  local function bind(key, fn) vim.keymap.set({ 'i', 'n' }, key, fn, { buffer = input, nowait = true }) end
  bind('<CR>', function() finish(true) end)
  bind('<Esc>', function() finish(false) end)
  bind('<C-c>', function() finish(false) end)
  bind('<Down>', function() move(1) end); bind('<C-n>', function() move(1) end)
  bind('<Up>', function() move(-1) end); bind('<C-p>', function() move(-1) end)
  render()
  vim.cmd.startinsert()
end
return M
