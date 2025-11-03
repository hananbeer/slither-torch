from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import matplotlib
# matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

class SimpleHandler(BaseHTTPRequestHandler):
  # Class variables to persist the figure across calls
  _heatmap_figure = None
  _heatmap_axes = None
  _heatmap_im = None
  _heatmap_cbar = None
  _interactive_init = False

  def do_GET(self):
    if self.path == "/bot.js":
      try:
        content = self.handle_bot()
        self.send_response(200)
      except Exception as e:
        content = b"error: " + str(e).encode()
        self.send_response(500)
    elif self.path == "/ai":
      signals = {}
      content = json.dumps(self.handle_ai(signals)).encode()
      print("ai response", content)
      self.send_response(200)
    else:
      content = b"File not found"
      self.send_response(404)

    self.send_header("Content-Type", "application/javascript")
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Content-Length", str(len(content)))
    self.end_headers()
    self.wfile.write(content)

  def do_POST(self):
    if self.path == "/ai":
      try:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        response = self.handle_ai(data)
        print("ai response", response)

        self.send_response(200)
      except Exception as e:
        response = { "error": str(e) }
        self.send_response(200)
    else:
      response = { "error": "Not found" }
      self.send_response(404)

    content = json.dumps(response).encode()
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(content)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(content)

  def handle_bot(self):
    with open("bot.js", "rb") as f:
      content = f.read()

    return content

  def generate_food_heatmap(self, food):
    # Initialize interactive mode on first call
    if not SimpleHandler._interactive_init:
      plt.ion()
      SimpleHandler._interactive_init = True

    if not food or len(food) == 0:
      return

    # Extract food positions
    x_coords = [f['x'] for f in food]
    y_coords = [f['y'] for f in food]
    sizes = [f.get('size', 1) for f in food]

    # Determine grid bounds with 10 units per cell
    cell_size = 10
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    # Expand bounds to align with cell grid
    x_min = (x_min // cell_size) * cell_size
    x_max = ((x_max // cell_size) + 1) * cell_size
    y_min = (y_min // cell_size) * cell_size
    y_max = ((y_max // cell_size) + 1) * cell_size

    # Create grid
    x_bins = np.arange(x_min, x_max + cell_size, cell_size)
    y_bins = np.arange(y_min, y_max + cell_size, cell_size)

    # Create 2D histogram (weighted by food size)
    heatmap_data, x_edges, y_edges = np.histogram2d(
      x_coords, y_coords,
      bins=[x_bins, y_bins],
      weights=sizes
    )

    # Rotate and flip for correct orientation
    heatmap_data = np.rot90(heatmap_data)
    heatmap_data = np.flipud(heatmap_data)

    # Update existing plot or create new one
    if SimpleHandler._heatmap_figure is None or not plt.fignum_exists(SimpleHandler._heatmap_figure.number):
      # Create new figure
      SimpleHandler._heatmap_figure, SimpleHandler._heatmap_axes = plt.subplots(figsize=(10, 10))
      SimpleHandler._heatmap_im = SimpleHandler._heatmap_axes.imshow(
        heatmap_data, cmap='hot', interpolation='nearest',
        extent=[x_min, x_max, y_min, y_max], aspect='auto', origin='lower'
      )
      SimpleHandler._heatmap_cbar = SimpleHandler._heatmap_figure.colorbar(
        SimpleHandler._heatmap_im, ax=SimpleHandler._heatmap_axes, label='Food density (weighted by size)'
      )
      SimpleHandler._heatmap_axes.set_xlabel('X position')
      SimpleHandler._heatmap_axes.set_ylabel('Y position')
      SimpleHandler._heatmap_axes.set_title('Food Distribution Heatmap (10 units per cell)')
      SimpleHandler._heatmap_axes.grid(True, alpha=0.3)
      plt.show(block=False)
    else:
      # Update existing plot
      current_shape = SimpleHandler._heatmap_im.get_array().shape
      if heatmap_data.shape != current_shape:
        # Shape changed, need to clear and redraw
        SimpleHandler._heatmap_axes.clear()
        SimpleHandler._heatmap_im = SimpleHandler._heatmap_axes.imshow(
          heatmap_data, cmap='hot', interpolation='nearest',
          extent=[x_min, x_max, y_min, y_max], aspect='auto', origin='lower'
        )
        SimpleHandler._heatmap_cbar.update_normal(SimpleHandler._heatmap_im)
        SimpleHandler._heatmap_axes.set_xlabel('X position')
        SimpleHandler._heatmap_axes.set_ylabel('Y position')
        SimpleHandler._heatmap_axes.set_title('Food Distribution Heatmap (10 units per cell)')
        SimpleHandler._heatmap_axes.grid(True, alpha=0.3)
      else:
        # Same shape, just update data
        SimpleHandler._heatmap_im.set_data(heatmap_data)
        SimpleHandler._heatmap_im.set_extent([x_min, x_max, y_min, y_max])
        SimpleHandler._heatmap_im.set_clim(vmin=heatmap_data.min(), vmax=heatmap_data.max())
        SimpleHandler._heatmap_cbar.update_normal(SimpleHandler._heatmap_im)
      SimpleHandler._heatmap_figure.canvas.draw()
      SimpleHandler._heatmap_figure.canvas.flush_events()

  def handle_ai(self, signals):
    # print("ai signals", signals)
    player = signals.get("player")
    if not player:
      return { "error": "No player" }

    food = signals.get("food")
    if not food:
      return { "angle": 0, "speedboost": False }

    relative_food = list(map(lambda f: { "x": f['x'] - player['x'], "y": f['y'] - player['y'], "size": f['size'] }, food))
    print("relative food", relative_food)

    self.generate_food_heatmap(relative_food)

    return { "angle": 0, "speedboost": False }

def run(server_class=HTTPServer, handler_class=SimpleHandler, port=8000):
  server_address = ('', port)
  httpd = server_class(server_address, handler_class)
  print(f"Serving HTTP on port {port} ...")
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    print("\nShutting down server.")
    httpd.server_close()

if __name__ == '__main__':
  run()

