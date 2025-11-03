
/*
install by running this in dev tools:

let script = document.createElement('script'); script.origin = 'anonymous'; script.src = 'http://localhost:8000/bot.js'; document.body.appendChild(script)
*/

let sampleRateFps = 5

let el_playButton;
let el_gameCanvas;
let el_captureCanvas;
let el_captureCtx;

let isPlaying = false

function isAlive() {
  return el_playButton.style.opacity == '0.38';
}

function getGameCanvasElement() {
  return document.querySelectorAll('canvas[class="nsi"]')[0];
}

function getPlayButtonElement() {
  return document.querySelector('div[class="btnt nsi sadg1"]');
}

function getScoreTextElement() {
  return [1];
}

function getLastScoreTextElement() {
  return document.querySelector('#lastscore > b');
}

function getScore() {
  let elements = document.querySelectorAll('div > span > span')
  if (!elements || elements.length < 2) {
    return 0
  }

  return parseInt(elements[1].innerText)
}

function getLastScore() {
  return parseInt(getLastScoreTextElement().innerText)
}

function createSecondaryCanvas(width, height) {
  let canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function captureFrame() {
  el_captureCtx.drawImage(el_gameCanvas, 0, 0, el_captureCanvas.width, el_captureCanvas.height);
  let pixels = el_captureCtx.getImageData(0, 0, el_captureCanvas.width, el_captureCanvas.height);
  // Encode pixels to a flat array and return it
  // Assuming we want to return a Uint8ClampedArray or Array of pixel values
  // pixels.data is a Uint8ClampedArray of [r,g,b,a,...]
  return Array.from(pixels.data);
}

let previousMousePosition = {
  clientX: 0,
  clientY: 0,
}
function setMoveDirection(angle) {
  angle = (angle % 360) * Math.PI / 180
  previousMousePosition = {
    angle,
    x: document.body.clientWidth / 2 + 100 * Math.cos(angle),
    y: document.body.clientHeight / 2 + 100 * Math.sin(angle),
  }

  const event = new MouseEvent("mousemove", {
    clientX: previousMousePosition.x,
    clientY: previousMousePosition.y,
  });

  window.dispatchEvent(event);
}

function setSpeedboost(enabled) {
  window.dispatchEvent(new MouseEvent(enabled ? "mousedown" : "mouseup", {
    clientX: previousMousePosition.x,
    clientY: previousMousePosition.y,
    button: 0 // Left click
  }))
}

let inflightQuery = false
async function aiQuery() {
  let response = await fetch(SERVER_URL, {
    method: 'POST',
    body: JSON.stringify({
      frame: captureFrame(),
    }),
  }).then(response => response.json())

  return response.angle, response.speedboost
}


async function gameLoop() {
  if (!isAlive()) {
    if (isPlaying) {
      console.warn('game ended. final score:', getLastScore())
      isPlaying = false
    }
    return
  } else {
    if (!isPlaying) {
      console.log('game started!')
      isPlaying = true
    }
  }

  if (inflightQuery) {
    console.warn('dropping frame due to inflight query')
    return
  }

  inflightQuery = true
  // let resp = await aiQuery()
  console.log('here would be ai query', getScore())
  inflightQuery = false
}

function install() {
  el_captureCanvas = createSecondaryCanvas(256, 256);
  el_captureCtx = el_captureCanvas.getContext('2d');

  el_gameCanvas = getGameCanvasElement();

  el_playButton = getPlayButtonElement()

  // some elements not added to DOM before first game starts
  el_playButton.click();

  console.log('installed! starting game loop')

  setInterval(gameLoop, 1000 / sampleRateFps)
}

install()
