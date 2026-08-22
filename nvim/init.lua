vim.g.mapleader = " "

vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.number = true
vim.opt.relativenumber = true

vim.opt.clipboard = "unnamedplus,unnamed"

vim.keymap.set("n", "<leader>w", vim.cmd.write, {})
vim.keymap.set("n", "<leader>q", vim.cmd.quit, {})

-- Create new file
vim.keymap.set("n", "<leader><C-n>", function()
  vim.ui.input({ prompt = "New file: " }, function(path)
    if not path or path == "" then
      return
    end

    vim.fn.mkdir(vim.fn.fnamemodify(path, ":h"), "p")
    vim.cmd.edit(vim.fn.fnameescape(path))
  end)
end)

vim.cmd.colorscheme("retrobox")

-- Fuzzy finding
vim.pack.add({ "https://github.com/ibhagwan/fzf-lua" })
local fzf = require("fzf-lua")
fzf.setup({
  winopts = {
    height = 1.0,
    width = 1.0,
    row = 0,
    col = 0,
  },
})

vim.keymap.set("n", "<leader>ff", fzf.files, {})
vim.keymap.set("n", "<leader>fg", fzf.live_grep, {})
vim.keymap.set("n", "<leader>fb", fzf.buffers, {})
vim.keymap.set("n", "<leader>gs", fzf.git_status, {})

-- Matching pairs
vim.pack.add({ "https://github.com/windwp/nvim-autopairs" })
require("nvim-autopairs").setup()

-- LSP
local lsps = {}

table.insert(lsps, "clangd")
vim.lsp.config("clangd", {
  cmd = { "clangd" },
  filetypes = { "c", "cpp" },
  root_markers = { "compile_commands.json", "compile_flags.txt", ".git" },
})

table.insert(lsps, "lua_ls")
vim.lsp.config("lua_ls", {
  cmd = { "lua-language-server" },
  filetypes = { "lua" },
  root_markers = { ".luarc.json", ".luarc.jsonc", ".git" },
})

vim.lsp.enable(lsps)
vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(args)
    local opts = { buffer = args.buf }

    vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
    vim.keymap.set("n", "gD", vim.lsp.buf.declaration, opts)
    vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
    vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, opts)
    vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, opts)
    vim.keymap.set("i", "<C-k>", vim.lsp.buf.signature_help, opts)
    vim.keymap.set("n", "<leader>gr", fzf.lsp_references, opts)
    vim.keymap.set("n", "<leader>e", fzf.diagnostics_document, opts)

    vim.lsp.completion.enable(true, args.data.client_id, args.buf, {
      autotrigger = false,
    })

    vim.keymap.set("i", "<C-Space>", function() vim.lsp.completion.get() end, opts)
  end,
})
