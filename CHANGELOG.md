## v1.0.0 (07.03.2025)

### Updates

- Added support for Ollama (switched to LangChain for LLM operations)
- Added Translation Threads to settings with a tooltip
- Added Test_Document.mqxliff (A random Wikipedia page, 200 segments, EN > DE)
- Updated requirements.txt

### Fixes

- Fixed "Cancel" button not cancelling the translation process
- Fixed LLM translation prompt for segments without context

### Known Issues

- LLMs like Ollama tend to add their explanations and comments after the translation. This is a known issue with LLMs and requires manual intervention to remove these comments.