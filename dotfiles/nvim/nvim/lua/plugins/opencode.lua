-- OpenCode AI integration for Neovim
return {
  {
    "NickvanDyke/opencode.nvim",
    dependencies = {
      {
        "folke/snacks.nvim",
        opts = {
          input = { enabled = true },
          terminal = { enabled = true },
        },
      },
    },
    ---@type opencode.Opts
    opts = {},
    config = function()
      -- Keymaps for opencode
      local keymap = vim.keymap.set

      -- Ask about selected code or ask a question
      keymap({ "n", "x" }, "<leader>oa", function()
        require("opencode").ask()
      end, { desc = "OpenCode: Ask" })

      -- Toggle inline AI assistant
      keymap({ "n", "x" }, "<leader>ot", function()
        require("opencode").toggle()
      end, { desc = "OpenCode: Toggle" })

      -- Open in terminal
      keymap("n", "<leader>oc", function()
        vim.cmd("terminal opencode")
      end, { desc = "OpenCode: Terminal" })
    end,
  },
}
