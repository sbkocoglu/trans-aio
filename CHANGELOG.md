## v1.0.1 (04.07.2025)

### Updates

- Changed LLM response format to json. This reduces the chance of LLMs adding their own comments and explanations to the translation
- Added a check for segments that are only a link. These segments will be copied over without translation
- How many segments couldn't be translated is now displayed at the end of the translation process
- Added error handling for not being able to fecth Ollama model list if Ollama is not installed or not running

### Fixes

- Reduced num_predict value for Ollama to 128 (default value) from -1 (infinite)
- Code cleanup

## v1.0.0 (03.07.2025)

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