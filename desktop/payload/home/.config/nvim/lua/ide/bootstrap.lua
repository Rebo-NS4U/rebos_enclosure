local M = {}
local path = vim.fn.stdpath('data') .. '/lazy/lazy.nvim'
function M.load()
  if not vim.uv.fs_stat(path .. '/lua/lazy/init.lua') then return false end
  vim.opt.rtp:prepend(path)
  require('lazy').setup(require('ide.plugins'), {
    change_detection = { notify = false }, checker = { enabled = false },
    install = { colorscheme = { 'habamax' } }, ui = { border = 'rounded' },
  })
  require('ide.theme').apply(true)
  M.loaded = true
  return true
end
function M.install()
  if M.installing then vim.notify('IDE installation is already running'); return end
  if M.loaded then vim.cmd('Lazy sync'); return end
  M.installing = true
  vim.fn.mkdir(vim.fn.fnamemodify(path, ':h'), 'p')
  vim.notify('Installing IDE plugins…')
  vim.system({ 'git', '-c', 'http.connectTimeout=10', 'clone', '--filter=blob:none', '--branch=stable',
    'https://github.com/folke/lazy.nvim.git', path }, { text = true, timeout = 30000 }, vim.schedule_wrap(function(result)
    M.installing = false
    if result.code ~= 0 then
      vim.notify('IDE download unavailable. Built-in tools remain active. Retry :IDEInstall when online.\n' ..
        (result.stderr or ''), vim.log.levels.WARN)
      return
    end
    M.load()
    vim.notify('Plugin manager installed. Plugins are downloading; restart when :Lazy shows installation complete.')
  end))
end
function M.setup()
  vim.api.nvim_create_user_command('IDEInstall', M.install, {})
  if M.load() then return end
  -- Headless checks never initiate downloads. Interactive first launch installs asynchronously.
  vim.api.nvim_create_autocmd('VimEnter', { once = true, callback = function()
    if #vim.api.nvim_list_uis() > 0 then vim.schedule(M.install) end
  end })
end
return M
