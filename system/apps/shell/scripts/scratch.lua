-- Use the same live desktop palette as the full editor, without starting its plugins.
local has_theme, theme = pcall(require, "ide.theme")
if has_theme then
    vim.opt.termguicolors = true
    theme.setup()
end
vim.api.nvim_set_hl(0, "WinBar", { link = "StatusLine" })
vim.api.nvim_set_hl(0, "WinBarNC", { link = "StatusLineNC" })
vim.opt.cursorline = true
vim.opt.cursorlineopt = "number"
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.numberwidth = 3
vim.opt.signcolumn = "no"
vim.opt.laststatus = 2
vim.opt.statusline = " %t %m%= %l,%c   %P "
vim.opt.winbar = " Notepad %="
vim.opt.showmode = true
vim.opt.wrap = true
vim.opt.linebreak = true
vim.api.nvim_create_autocmd("VimEnter", {
    callback = function()
        vim.cmd("normal! G$")
        vim.cmd.startinsert({ bang = true })
    end,
})
