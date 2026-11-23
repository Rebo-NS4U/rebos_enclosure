vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.numberwidth = 3
vim.opt.signcolumn = "no"
vim.opt.laststatus = 2
vim.opt.statusline = " scratch %=%l,%c   %P "
vim.opt.winbar = " ── scratch ──────────────────────── %=%{mode() ==# 'i' ? 'insert' : 'normal'} "
vim.opt.wrap = true
vim.opt.linebreak = true
vim.opt.updatetime = 300
vim.api.nvim_create_autocmd({ "CursorHoldI", "CursorHold", "InsertLeave", "FocusLost", "VimLeavePre" }, {
    callback = function()
        if vim.bo.modified and vim.bo.buftype == "" then vim.cmd.update() end
    end,
})
vim.api.nvim_create_autocmd("VimEnter", {
    callback = function()
        vim.cmd("normal! G$")
        vim.cmd.startinsert({ bang = true })
    end,
})
