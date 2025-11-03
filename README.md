# Slither Bot

serve the script, eg. `python -m http.server`

then go to http://slither.com/io open dev tools and inject the script:

```javascript
let script = document.createElement('script'); script.origin = 'anonymous'; script.src = 'http://localhost:8000/bot.js'; document.body.appendChild(script)
```
