# Agent Skills

> Create, manage, and share Skills to extend Claude's capabilities in Claude Code.

A Skill is a markdown file that teaches Claude how to do something specific, such as reviewing PRs using your team's standards or generating commit messages in your preferred format. When you ask Claude something that matches a Skill's purpose, Claude automatically applies it.

Skills can also bundle scripts in any language. This means Claude can run Python, Node.js, Bash, or any other scripts you include, giving it capabilities far beyond what's possible in a single prompt. For example, generate interactive visualizations, query databases, process files, call APIs, or produce reports in any format. See [Generate visual output](#generate-visual-output) for an example Skill that uses a Python script to create an interactive codebase visualization.

This guide covers creating Skills, configuring them with metadata and scripts, and sharing them with your team or organization.

## Create your first Skill

This example creates a personal Skill that teaches Claude to explain code using visual diagrams and analogies. Unlike Claude's default explanations, this Skill ensures every explanation includes an ASCII diagram and a real-world analogy.

<Steps>
  <Step title="Check available Skills">
    Before creating a Skill, see what Skills Claude already has access to:

    ```
    What Skills are available?
    ```

    Claude will list any Skills currently loaded. You may see none, or you may see Skills from plugins or your organization.
  </Step>

  <Step title="Create the Skill directory">
    Create a directory for the Skill in your personal Skills folder. Personal Skills are available across all your projects. (You can also create project Skills in `.claude/skills/` to share with your team.)

    ```bash
    mkdir -p ~/.claude/skills/explaining-code
    ```
  </Step>

  <Step title="Write SKILL.md">
    Every Skill needs a `SKILL.md` file. The file starts with YAML metadata between `---` markers and must include a `name` and `description`, followed by Markdown instructions that Claude follows when the Skill is active.

    The `description` is especially important, because Claude uses it to decide when to apply the Skill.

    Create `~/.claude/skills/explaining-code/SKILL.md`:

    ```yaml
    ---
    name: explaining-code
    description: Explains code with visual diagrams and analogies. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
    ---

    When explaining code, always include:

    1. **Start with an analogy**: Compare the code to something from everyday life
    2. **Draw a diagram**: Use ASCII art to show the flow, structure, or relationships
    3. **Walk through the code**: Explain step-by-step what happens
    4. **Highlight a gotcha**: What's a common mistake or misconception?

    Keep explanations conversational. For complex concepts, use multiple analogies.
    ```
  </Step>

  <Step title="Load and verify the Skill">
    Skills are automatically loaded when created or modified. Verify the Skill appears in the list:

    ```
    What Skills are available?
    ```

    You should see `explaining-code` in the list with its description.
  </Step>

  <Step title="Test the Skill">
    Open any file in your project and ask Claude a question that matches the Skill's description:

    ```
    How does this code work?
    ```

    Claude should ask to use the `explaining-code` Skill, then include an analogy and ASCII diagram in its explanation. If the Skill doesn't trigger, try rephrasing to include more keywords from the description, like "explain how this works."
  </Step>
</Steps>

The rest of this guide covers how Skills work, configuration options, and troubleshooting.

## How Skills work

Skills are model-invoked: Claude decides which Skills to use based on your request. You don't need to explicitly call a Skill. Claude automatically applies relevant Skills when your request matches their description.

When you send a request, Claude follows these steps to find and use relevant Skills:

<Steps>
  <Step title="Discovery">
    At startup, Claude loads only the name and description of each available Skill. This keeps startup fast while giving Claude enough context to know when each Skill might be relevant.
  </Step>

  <Step title="Activation">
    When your request matches a Skill's description, Claude asks to use the Skill. You'll see a confirmation prompt before the full `SKILL.md` is loaded into context. Since Claude reads these descriptions to find relevant Skills, write descriptions that include keywords users would naturally say.
  </Step>

  <Step title="Execution">
    Claude follows the Skill's instructions, loading referenced files or running bundled scripts as needed.
  </Step>
</Steps>

### Where Skills live

Where you store a Skill determines who can use it:

| Location   | Path                                             | Applies to                        |
| :--------- | :----------------------------------------------- | :-------------------------------- |
| Enterprise | See managed settings                              | All users in your organization    |
| Personal   | `~/.claude/skills/`                              | You, across all projects          |
| Project    | `.claude/skills/`                                | Anyone working in this repository |
| Plugin     | Bundled with plugins                             | Anyone with the plugin installed  |

If two Skills have the same name, the higher row wins: managed overrides personal, personal overrides project, and project overrides plugin.

#### Automatic discovery from nested directories

When you work with files in subdirectories, Claude Code automatically discovers Skills from nested `.claude/skills/` directories. For example, if you're editing a file in `packages/frontend/`, Claude Code also looks for Skills in `packages/frontend/.claude/skills/`. This supports monorepo setups where packages have their own Skills.

### When to use Skills versus other options

Claude Code offers several ways to customize behavior. The key difference: Skills are triggered automatically by Claude based on your request, while slash commands require you to type `/command` explicitly.

| Use this                                 | When you want to...                                                        | When it runs                               |
| :--------------------------------------- | :------------------------------------------------------------------------- | :----------------------------------------- |
| Skills                                  | Give Claude specialized knowledge (e.g., "review PRs using our standards") | Claude chooses when relevant               |
| Slash commands                          | Create reusable prompts (e.g., `/deploy staging`)                          | You type `/command` to run it              |
| CLAUDE.md                               | Set project-wide instructions (e.g., "use TypeScript strict mode")         | Loaded into every conversation             |
| Subagents                               | Delegate tasks to a separate context with its own tools                    | Claude delegates, or you invoke explicitly |
| Hooks                                   | Run scripts on events (e.g., lint on file save)                            | Fires on specific tool events              |
| MCP servers                             | Connect Claude to external tools and data sources                          | Claude calls MCP tools as needed           |

Skills vs. subagents: Skills add knowledge to the current conversation. Subagents run in a separate context with their own tools. Use Skills for guidance and standards; use subagents when you need isolation or different tool access.

Skills vs. MCP: Skills tell Claude how to use tools; MCP provides the tools. For example, an MCP server connects Claude to your database, while a Skill teaches Claude your data model and query patterns.

## Configure Skills

This section covers Skill file structure, supporting files, tool restrictions, and distribution options.

### Write SKILL.md

The `SKILL.md` file is the only required file in a Skill. It has two parts: YAML metadata (the section between `---` markers) at the top, and Markdown instructions that tell Claude how to use the Skill:

```yaml
---
name: your-skill-name
description: Brief description of what this Skill does and when to use it
---

# Your Skill Name

## Instructions
Provide clear, step-by-step guidance for Claude.

## Examples
Show concrete examples of using this Skill.
```

#### Available metadata fields

You can use the following fields in the YAML frontmatter:

| Field            | Required | Description |
| :--------------- | :------- | :---------- |
| `name`           | Yes      | Skill name. Must use lowercase letters, numbers, and hyphens only (max 64 characters). Should match the directory name. |
| `description`    | Yes      | What the Skill does and when to use it (max 1024 characters). Claude uses this to decide when to apply the Skill. |
| `allowed-tools`  | No       | Tools Claude can use without asking permission when this Skill is active. Supports comma-separated values or YAML-style lists. |
| `model`          | No       | Model to use when this Skill is active. Defaults to the conversation's model. |
| `context`        | No       | Set to `fork` to run the Skill in a forked sub-agent context with its own conversation history. |
| `agent`          | No       | Specify which agent type to use when `context: fork` is set. Defaults to `general-purpose` if not specified. |
| `hooks`          | No       | Define hooks scoped to this Skill's lifecycle. Supports `PreToolUse`, `PostToolUse`, and `Stop` events. |
| `user-invocable` | No       | Controls whether the Skill appears in the slash command menu. Defaults to `true`. |

#### Available string substitutions

Skills support string substitution for dynamic values in the Skill content:

| Variable               | Description |
| :--------------------- | :---------- |
| `$ARGUMENTS`           | All arguments passed when invoking the Skill. If `$ARGUMENTS` is not present in the content, arguments are appended as `ARGUMENTS: <value>`. |
| `${CLAUDE_SESSION_ID}` | The current session ID. Useful for logging, creating session-specific files, or correlating Skill output with sessions. |

Example using substitutions:

```yaml
---
name: session-logger
description: Log activity for this session
---

Log the following to logs/${CLAUDE_SESSION_ID}.log:

$ARGUMENTS
```

### Update or delete a Skill

To update a Skill, edit its `SKILL.md` file directly. To remove a Skill, delete its directory. Changes take effect immediately.

### Add supporting files with progressive disclosure

Skills share Claude's context window with conversation history, other Skills, and your request. To keep context focused, use progressive disclosure: put essential information in `SKILL.md` and detailed reference material in separate files that Claude reads only when needed.

This approach lets you bundle comprehensive documentation, examples, and scripts without consuming context upfront. Claude loads additional files only when the task requires them.

Tip: Keep `SKILL.md` under 500 lines for optimal performance. If your content exceeds this, split detailed reference material into separate files.

#### Example: multi-file Skill structure

Claude discovers supporting files through links in your `SKILL.md`. The following example shows a Skill with detailed documentation in separate files and utility scripts that Claude can execute without reading:

```
my-skill/
├── SKILL.md (required - overview and navigation)
├── reference.md (detailed API docs - loaded when needed)
├── examples.md (usage examples - loaded when needed)
└── scripts/
    └── helper.py (utility script - executed, not loaded)
```

The `SKILL.md` file references these supporting files so Claude knows they exist:

```markdown
## Overview

[Essential instructions here]

## Additional resources

- For complete API details, see [reference.md](reference.md)
- For usage examples, see [examples.md](examples.md)

## Utility scripts

To validate input files, run the helper script. It checks for required fields and returns any validation errors:
```bash
python scripts/helper.py input.txt
```
```

Tip: Keep references one level deep. Link directly from `SKILL.md` to reference files. Deeply nested references may result in partial reads.

Bundle utility scripts for zero-context execution. Scripts in your Skill directory can be executed without loading their contents into context. Claude runs the script and only the output consumes tokens.

### Restrict tool access with allowed-tools

Use the `allowed-tools` frontmatter field to limit which tools Claude can use when a Skill is active. You can specify tools as a comma-separated string or a YAML list.

```yaml
---
name: reading-files-safely
description: Read files without making changes. Use when you need read-only file access.
allowed-tools: Read, Grep, Glob
---
```

Or use YAML-style lists for better readability:

```yaml
---
name: reading-files-safely
description: Read files without making changes. Use when you need read-only file access.
allowed-tools:
  - Read
  - Grep
  - Glob
---
```

### Run Skills in a forked context

Use `context: fork` to run a Skill in an isolated sub-agent context with its own conversation history.

```yaml
---
name: code-analysis
description: Analyze code quality and generate detailed reports
context: fork
---
```

### Define hooks for Skills

Skills can define hooks that run during the Skill's lifecycle.

```yaml
---
name: secure-operations
description: Perform operations with additional security checks
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh $TOOL_INPUT"
          once: true
---
```

### Control Skill visibility

Skills can be invoked in three ways:

1. Manual invocation: You type `/skill-name` in the prompt
2. Programmatic invocation: Claude calls it via the Skill tool
3. Automatic discovery: Claude reads the Skill's description and loads it when relevant

The `user-invocable` field controls only manual invocation.

### Skills and subagents

There are two ways Skills and subagents can work together:

#### Give a subagent access to Skills

Subagents do not automatically inherit Skills from the main conversation. To give a custom subagent access to specific Skills, list them in the subagent's `skills` field.

```yaml
---
name: code-reviewer
description: Review code for quality and best practices
skills: pr-review, security-check
---
```

#### Run a Skill in a subagent context

Use `context: fork` and `agent` to run a Skill in a forked subagent with its own separate context.

### Distribute Skills

You can share Skills in several ways:

- Project Skills: Commit `.claude/skills/` to version control.
- Plugins: Create a `skills/` directory in your plugin with Skill folders containing `SKILL.md` files.
- Managed: Administrators can deploy Skills organization-wide.

## Examples

### Simple Skill (single file)

```
commit-helper/
└── SKILL.md
```

```yaml
---
name: generating-commit-messages
description: Generates clear commit messages from git diffs. Use when writing commit messages or reviewing staged changes.
---

# Generating Commit Messages

## Instructions

1. Run `git diff --staged` to see changes
2. Suggest a commit message with:
   - Summary under 50 characters
   - Detailed description
   - Affected components

## Best practices

- Use present tense
- Explain what and why, not how
```

### Use multiple files

```
pdf-processing/
├── SKILL.md              # Overview and quick start
├── FORMS.md              # Form field mappings and filling instructions
├── REFERENCE.md          # API details for pypdf and pdfplumber
└── scripts/
    ├── fill_form.py      # Utility to populate form fields
    └── validate.py       # Checks PDFs for required fields
```

### Generate visual output

This example creates a codebase explorer: an interactive tree view where you can expand and collapse directories, see file sizes at a glance, and identify file types by color.

Create the Skill directory:

```bash
mkdir -p ~/.claude/skills/codebase-visualizer/scripts
```

Create `~/.claude/skills/codebase-visualizer/SKILL.md`:

```yaml
---
name: codebase-visualizer
description: Generate an interactive collapsible tree visualization of your codebase. Use when exploring a new repo, understanding project structure, or identifying large files.
allowed-tools: Bash(python:*)
---

# Codebase Visualizer

Generate an interactive HTML tree view that shows your project's file structure with collapsible directories.

## Usage

Run the visualization script from your project root:

```bash
python ~/.claude/skills/codebase-visualizer/scripts/visualize.py .
```

This creates `codebase-map.html` in the current directory and opens it in your default browser.

## What the visualization shows

- Collapsible directories: Click folders to expand/collapse
- File sizes: Displayed next to each file
- Colors: Different colors for different file types
- Directory totals: Shows aggregate size of each folder
```

Create `~/.claude/skills/codebase-visualizer/scripts/visualize.py`. The script scans a directory tree and generates a self-contained HTML file with a summary sidebar, a bar chart, and a collapsible tree.

To test, open Claude Code in any project and ask "Visualize this codebase." Claude runs the script, generates `codebase-map.html`, and opens it in your browser.

## Troubleshooting

### View and test Skills

To see which Skills Claude has access to, ask Claude a question like "What Skills are available?" Claude loads all available Skill names and descriptions into the context window when a conversation starts, so it can list the Skills it currently has access to.

To test a specific Skill, ask Claude to do a task that matches the Skill's description.

### Skill not triggering

The description field is how Claude decides whether to use your Skill. Vague descriptions like "Helps with documents" don't give Claude enough information to match your Skill to relevant requests.

### Skill doesn't load

Check the file path. Skills must be in the correct directory with the exact filename `SKILL.md` (case-sensitive). Check the YAML syntax. Invalid YAML in the frontmatter prevents the Skill from loading.

### Skill has errors

Check dependencies are installed. Check script permissions. Check file paths use forward slashes.

### Multiple Skills conflict

If Claude uses the wrong Skill, make descriptions distinct with specific trigger terms.

### Plugin Skills not appearing

Clear the plugin cache and reinstall:

```bash
rm -rf ~/.claude/plugins/cache
```

Then restart Claude Code and reinstall the plugin.

## Next steps

- Authoring best practices: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices
- Agent Skills overview: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview
- Use Skills in the Agent SDK: https://docs.claude.com/en/docs/agent-sdk/skills
- Get started with Agent Skills: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/quickstart

---

To find navigation and other pages in this documentation, fetch the llms.txt file at: https://code.claude.com/docs/llms.txt
