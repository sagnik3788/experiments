-- UI enhancements: Noice, Dressing, Which-key, Notify
return {
  -- Noice: Better command line UI
  {
    "folke/noice.nvim",
    event = "VeryLazy",
    opts = {
      cmdline = {
        enabled = true,
        view = "cmdline_popup",
        format = {
          cmdline = { pattern = "^:", icon = " ", lang = "vim" },
          search_down = { pattern = "^/", icon = "  ", lang = "regex" },
          search_up = { pattern = "^%?", icon = "  ", lang = "regex" },
          filter = { pattern = "^:%s*!", icon = "$ ", lang = "bash" },
        },
      },
      messages = {
        enabled = true,
        view = "mini",
      },
      notify = {
        enabled = true,
        view = "mini",
      },
      lsp = {
        override = {
          "vim.lsp.util.convert_input_to_markdown_lines",
          "vim.lsp.util.stylize_markdown",
          "vim.lsp.protocol.completion_item_to_text",
        },
        signature = {
          enabled = false,
        },
      },
      presets = {
        command_palette = true,
        long_message_to_split = true,
        lsp_doc_border = true,
      },
    },
    dependencies = {
      "MunifTanjim/nui.nvim",
      "rcarriga/nvim-notify",
    },
  },

  -- Dressing: Better input UIs
  {
    "stevearc/dressing.nvim",
    event = "VeryLazy",
    opts = {
      input = {
        enabled = true,
        default_prompt = "  Input:",
        title_pos = "center",
        border = "rounded",
        relative = "editor",
      },
      select = {
        enabled = true,
        backend = { "telescope", "builtin" },
      },
    },
  },

  -- Which-key: Show keybinding hints
  {
    "folke/which-key.nvim",
    event = "VeryLazy",
    opts = {
      preset = "classic",
      icons = {
        breadcrumb = " » ",
        separator = "  ",
        group = " ",
      },
      spec = {
        { "<leader>o", group = "OpenCode" },
        { "<leader>c", group = "Code" },
        { "<leader>g", group = "Git" },
        { "<leader>s", group = "Search" },
        { "<leader>t", group = "Toggle" },
        { "<leader>l", group = "LSP" },
      },
    },
  },

  -- Nvim-notify: Pretty notifications
  {
    "rcarriga/nvim-notify",
    event = "VeryLazy",
    opts = {
      timeout = 3000,
      max_height = function()
        return math.floor(vim.o.lines * 0.75)
      end,
      max_width = function()
        return math.floor(vim.o.columns * 0.75)
      end,
      stages = "fade_in_slide_out",
      render = "default",
      top_down = false,
      background_colour = "#1d2021",
    },
  },
}
