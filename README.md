# Slither Bot

serve the script, eg. `python -m http.server`

then go to http://slither.com/io open dev tools and inject the script:

```javascript
let script = document.createElement('script'); script.origin = 'anonymous'; script.src = 'http://localhost:8000/bot.js'; document.body.appendChild(script)
```

## structures

`slither` - current player

`os` - mapping of players by id


slither.nk = name
slither.xx, .yy = position?
slither.rex, .rey = direction?
slither.gptz = body points?
slither.ang = angle in radians (0..2pi where 0 = 3 oclock and going clockwise)

.wmd = is boosting
.sfr = amount boosted?

.dead = check if my slither is alive
(also simply if slither == null)


also:

foods, preys



os, foods, preys
foods.filter(x=>x)

create food map:

foods.filter(f=>f).map(f=>{return {xx: f.xx - slither.xx, yy: f.yy - slither.yy, delta: Math.abs(f.xx - f.rx)}})[0]

similarly with prey map and enemies map (set of os - slither)
