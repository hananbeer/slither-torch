from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

class SimpleHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    content = b"File not found"

    if self.path == "/bot.js":
      try:
        content = handle_bot(self)
        self.send_response(200)
      except Exception as e:
        content = "error: " + str(e)
        self.send_response(500)
    else:
      self.send_response(404)

    self.end_headers()
    self.wfile.write(content)

  def do_POST(self):
    response = { "error": "Not found" }

    try:
      content_length = int(self.headers.get("Content-Length", 0))
      body = self.rfile.read(content_length)
      data = json.loads(body)

      response = self.handle_ai(data)

      self.send_response(200)
    except Exception as e:
      response = { "error": str(e) }
      self.send_response(404)

    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps(response).encode())

  def handle_bot(self):
    with open("bot.js", "rb") as f:
      content = f.read()

    return content

  def handle_ai(self, signals):
    pass

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

