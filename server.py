from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
# matplotlib.use('TkAgg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter

class SimpleHandler(BaseHTTPRequestHandler):
  # Class variables to persist the figure across calls
  _heatmap_figure = None
  _heatmap_axes = None
  _heatmap_ims = None
  _heatmap_quivers = None
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

    zoom_levels = [500, 2000]
    
    # Create figure with 2 subplots if it doesn't exist
    if SimpleHandler._heatmap_figure is None:
      SimpleHandler._heatmap_figure, axes_array = plt.subplots(1, len(zoom_levels), figsize=(24, 8))
      SimpleHandler._heatmap_axes = axes_array
      SimpleHandler._heatmap_ims = [None] * len(zoom_levels)
      SimpleHandler._heatmap_quivers = [None] * len(zoom_levels)

    # Generate heatmap for each zoom level
    axes_arr = SimpleHandler._heatmap_axes
    ims_list = SimpleHandler._heatmap_ims
    quivers_list = SimpleHandler._heatmap_quivers
    
    for idx, zoom in enumerate(zoom_levels):
      heatmap_data, U, V, X, Y, x_min, x_max, y_min, y_max, vmin, vmax = self._generate_heatmap_data(food, zoom)
      
      # Access axes array - plt.subplots returns numpy array when nrows*ncols > 1
      if axes_arr is None:
        continue
      ax = axes_arr[idx] if hasattr(axes_arr, '__getitem__') and len(axes_arr) > idx else axes_arr
      
      if ims_list is None or idx >= len(ims_list):
        continue
      
      if ims_list[idx] is None:
        # Create new subplot
        ims_list[idx] = ax.imshow(
          heatmap_data, cmap='plasma', interpolation='bilinear',
          extent=[x_min, x_max, y_min, y_max], aspect='auto', origin='lower',
          vmin=vmin, vmax=vmax,
        )
        ims_list[idx].set_clim(vmin=vmin, vmax=vmax)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_title(f'Food Distribution Heatmap (Zoom: {zoom})')
        ax.grid(True, alpha=0.3)

        # Draw a circle at the center
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        radius = 80
        circle_patch = plt.Circle((center_x, center_y), radius, color='cyan', fill=True, linewidth=3, alpha=0.5)
        ax.add_patch(circle_patch)

        # Add quiver plot for vectors
        vector_magnitude = np.sqrt(U**2 + V**2)
        non_zero_vector_mask = vector_magnitude > 0
        U_masked = np.ma.masked_where(~non_zero_vector_mask, U)
        V_masked = np.ma.masked_where(~non_zero_vector_mask, V)
        
        if quivers_list is not None and idx < len(quivers_list):
          quivers_list[idx] = ax.quiver(
            X, Y, U_masked, V_masked,
            scale=200,
            width=0.003,
            color='white',
            alpha=0.7,
            angles='xy',
            scale_units='xy'
          )
      else:
        # Update existing subplot
        ims_list[idx].set_data(heatmap_data)
        
        # Update quiver vectors
        if quivers_list is not None and idx < len(quivers_list) and quivers_list[idx] is not None:
          vector_magnitude = np.sqrt(U**2 + V**2)
          non_zero_vector_mask = vector_magnitude > 0
          U_masked = np.ma.masked_where(~non_zero_vector_mask, U)
          V_masked = np.ma.masked_where(~non_zero_vector_mask, V)
          quivers_list[idx].set_UVC(U_masked, V_masked)

    plt.show(block=False)
    SimpleHandler._heatmap_figure.canvas.draw_idle()
    SimpleHandler._heatmap_figure.canvas.flush_events()

  def _generate_heatmap_data(self, food, zoom):
    # Extract food positions
    x_coords = [f['x'] for f in food]
    y_coords = [f['y'] for f in food]
    sizes = [f.get('size', 1) for f in food]

    density = 2
    cell_size = math.sqrt(zoom)
    vmin = -(density * cell_size) / 4
    vmax = (density * cell_size) / 4
    x_min, x_max = -zoom, zoom
    y_min, y_max = -zoom, zoom

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

    # Create meshgrid for vector positions (center of each cell)
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    X, Y = np.meshgrid(x_centers, y_centers)
    
    # Rotate and flip meshgrid to match heatmap
    X = np.rot90(X)
    X = np.flipud(X)
    Y = np.rot90(Y)
    Y = np.flipud(Y)

    return heatmap_data, U, V, X, Y, x_min, x_max, y_min, y_max, vmin, vmax

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

