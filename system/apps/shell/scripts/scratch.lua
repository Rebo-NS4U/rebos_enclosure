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
vim.opt.updatetime = 300
vim.api.nvim_create_autocmd({ "CursorHoldI", "CursorHold", "InsertLeave", "BufLeave", "FocusLost", "VimLeavePre" }, {
    callback = function()
        if vim.bo.modified and vim.bo.buftype == "" then vim.cmd.update() end
    end,
})
vim.keymap.set({ "n", "i" }, "<C-s>", "<Cmd>update<CR>", { desc = "Save note" })
vim.api.nvim_create_autocmd("VimEnter", {
    callback = function()
        -- Register the other existing note as a buffer without reading its contents.
        local alternate = vim.env.ENCLOSURE_ALTERNATE_NOTE
        if alternate and vim.fn.filereadable(alternate) == 1 then
            local buffer = vim.fn.bufadd(alternate)
            vim.bo[buffer].buflisted = true
        end
        vim.cmd("normal! G$")
        vim.cmd.startinsert({ bang = true })
    end,
})
