

```sh
#run oracle (gold patch solution)
harbor run -p tasks -a oracle -e modal

#run claude code thru openrouter
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_API_KEY=$OPENROUTER_API_KEY
harbor run -p tasks -a claude-code -e modal -m  claude-sonnet-5

#run codex
harbor run -p tasks -a codex -e modal -m  gpt-5.5
```