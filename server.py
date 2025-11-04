from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import matplotlib
# matplotlib.use('TkAgg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter

class SimpleHandler(BaseHTTPRequestHandler):
  # Class variables to persist the figure across calls
  _heatmap_figure = None
  _heatmap_axes = None
  _heatmap_im = None
  _heatmap_quiver = None
  _interactive_init = False

  def do_GET(self):
    if self.path == "/bot.js":
      try:
        content = self.handle_bot()
        self.send_response(200)
      except Exception as e:
        content = b"error: " + str(e).encode()
        self.send_response(500)
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
        #print("ai response", response)

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
      # plt.ion()
      SimpleHandler._interactive_init = True

    if not food or len(food) == 0:
      return

    # Extract food positions
    x_coords = [f['x'] for f in food]
    y_coords = [f['y'] for f in food]
    sizes = [f.get('size', 1) for f in food]

    vmin = -25
    vmax = 25
    cell_size = 30
    x_min, x_max = -2000, 2000
    y_min, y_max = -2000, 2000

    # Create grid covering the full range
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
    
    # Apply Gaussian filter to create spillover effect
    heatmap_data = gaussian_filter(heatmap_data, sigma=0.1)

    # Calculate vector fields from deltas
    # Create arrays to store aggregated vectors per cell
    num_y_cells = len(y_bins) - 1
    num_x_cells = len(x_bins) - 1
    U = np.zeros((num_y_cells, num_x_cells))  # X component
    V = np.zeros((num_y_cells, num_x_cells))  # Y component
    cell_counts = np.zeros((num_y_cells, num_x_cells))  # Count of items per cell

    # Aggregate deltas per cell
    for f in food:
      x = f['x']
      y = f['y']
      delta = f.get('delta')
      
      if delta is None or not isinstance(delta, (list, tuple)) or len(delta) < 2:
        continue
      
      mag = np.sqrt(delta[0]**2 + delta[1]**2)
      if mag > 100:
        continue

      delta = [delta[0] * 500, delta[1] * -500]

      # Find which cell this food item belongs to
      x_idx = np.digitize(x, x_bins) - 1
      y_idx = np.digitize(y, y_bins) - 1
      
      # Ensure indices are within bounds
      if 0 <= x_idx < num_x_cells and 0 <= y_idx < num_y_cells:
        # Add delta to cell (will be averaged later)
        U[y_idx, x_idx] += delta[0]
        V[y_idx, x_idx] += delta[1]
        cell_counts[y_idx, x_idx] += 1

    # Average vectors per cell (avoid division by zero)
    non_zero_mask = cell_counts > 0
    U[non_zero_mask] /= cell_counts[non_zero_mask]
    V[non_zero_mask] /= cell_counts[non_zero_mask]

    # Rotate and flip vectors to match heatmap orientation
    U = np.rot90(U)
    U = np.flipud(U)
    V = np.rot90(V)
    V = np.flipud(V)

    # Create mask for non-zero vectors (only show vectors where magnitude > 0)
    vector_magnitude = np.sqrt(U**2 + V**2)
    non_zero_vector_mask = vector_magnitude > 0

    # Create meshgrid for vector positions (center of each cell)
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    X, Y = np.meshgrid(x_centers, y_centers)
    
    # Rotate and flip meshgrid to match heatmap
    X = np.rot90(X)
    X = np.flipud(X)
    Y = np.rot90(Y)
    Y = np.flipud(Y)

    # Mask vectors to only show non-empty ones
    U_masked = np.ma.masked_where(~non_zero_vector_mask, U)
    V_masked = np.ma.masked_where(~non_zero_vector_mask, V)

    # Update existing plot or create new one
    if SimpleHandler._heatmap_figure is None:
      # Create new figure
      SimpleHandler._heatmap_figure, SimpleHandler._heatmap_axes = plt.subplots(figsize=(8, 8))
      SimpleHandler._heatmap_im = SimpleHandler._heatmap_axes.imshow(
        heatmap_data, cmap='plasma', interpolation='bilinear',
        extent=[x_min, x_max, y_min, y_max], aspect='auto', origin='lower',
        vmin=vmin, vmax=vmax,
      )
      # viridis, plasma, inferno, magma, cividis, turbo.
      SimpleHandler._heatmap_im.set_clim(vmin=vmin, vmax=vmax)
      SimpleHandler._heatmap_axes.set_xlim(x_min, x_max)
      SimpleHandler._heatmap_axes.set_ylim(y_min, y_max)
      # SimpleHandler._heatmap_axes.set_xlabel('X position')
      # SimpleHandler._heatmap_axes.set_ylabel('Y position')
      SimpleHandler._heatmap_axes.set_title('Food Distribution Heatmap')
      SimpleHandler._heatmap_axes.grid(True, alpha=0.3)


      # Draw a circle at the center of the heatmap figure
      center_x = (x_min + x_max) / 2
      center_y = (y_min + y_max) / 2
      radius = 80  # or pick an appropriate radius based on domain
      circle_patch = plt.Circle((center_x, center_y), radius, color='cyan', fill=True, linewidth=3, alpha=0.5)
      SimpleHandler._heatmap_axes.add_patch(circle_patch)
      # SimpleHandler._heatmap_center_circle = circle_patch

      # Add quiver plot for vectors (only non-empty vectors will be shown due to masking)
      SimpleHandler._heatmap_quiver = SimpleHandler._heatmap_axes.quiver(
        X, Y, U_masked, V_masked,
        scale=200,  # Adjust scale to control arrow size (higher = smaller arrows)
        width=0.003,  # Arrow width
        color='white',
        alpha=0.7,
        angles='xy',
        scale_units='xy'
      )

      plt.show(block=False)
    else:
      # Update existing plot (shape is always the same now with fixed range)
      SimpleHandler._heatmap_im.set_data(heatmap_data)
      #SimpleHandler._heatmap_im.set_clim(vmin=heatmap_data.min(), vmax=heatmap_data.max())
      
      # Update quiver vectors (recalculate mask for updated vectors)
      if SimpleHandler._heatmap_quiver is not None:
        vector_magnitude = np.sqrt(U**2 + V**2)
        non_zero_vector_mask = vector_magnitude > 0
        U_masked = np.ma.masked_where(~non_zero_vector_mask, U)
        V_masked = np.ma.masked_where(~non_zero_vector_mask, V)
        SimpleHandler._heatmap_quiver.set_UVC(U_masked, V_masked)
      
      SimpleHandler._heatmap_figure.canvas.draw_idle()
      SimpleHandler._heatmap_figure.canvas.flush_events()

  def handle_ai(self, signals):
    # print("ai signals", signals)
    player = signals.get("player")
    if not player:
      return { "error": "No player" }

    food = signals.get("food")
    prey = signals.get("prey")
    enemies = signals.get("enemies")
    if food:
      for enemy in enemies:
        for i, enemy_part in enumerate(enemy['parts']):
          food.append({
            'x': enemy_part['x'],
            'y': enemy_part['y'],
            'size': -enemy_part['size'] * (5 if i == 0 else 1),
            'delta': enemy_part.get('delta')
          })

      for p in prey:
        p['size'] = 50

      food += prey

      relative_food = list(map(lambda f: { 
        "x": f['x'] - player['x'], 
        "y": -(f['y'] - player['y']), 
        "size": f['size'],
        "delta": f.get('delta')
      }, food))
      # print("relative food", relative_food)
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

