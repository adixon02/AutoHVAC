const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>AutoHVAC Test</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #0066CC; color: white; padding: 20px; text-align: center; }
        .content { background: #f8f9fa; padding: 30px; margin: 20px 0; }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>AutoHVAC Test Server</h1>
        <p>If you can see this, the server is working!</p>
      </div>
      <div class="content">
        <h2>Connection Test Successful</h2>
        <p>URL: ${req.url}</p>
        <p>Method: ${req.method}</p>
        <p>Time: ${new Date().toLocaleString()}</p>
        <p><strong>Next step:</strong> We'll fix the Next.js server.</p>
      </div>
    </body>
    </html>
  `);
});

const PORT = 3003;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Test server running at:`);
  console.log(`- http://localhost:${PORT}`);
  console.log(`- http://127.0.0.1:${PORT}`);
  console.log(`Press Ctrl+C to stop`);
});