module.exports = {
  apps: [
    {
      name: 'improve-api',
      script: 'src/api/app.py',
      interpreter: 'python3',
      // cwd will be set automatically by deploy script
      instances: 1,
      exec_mode: 'fork',
      env: {
        FLASK_ENV: 'production',
        FLASK_DEBUG: 'False',
        API_PORT: '3001',
        API_HOST: '127.0.0.1', // Internal only, nginx will proxy
        NODE_ENV: 'production',
      },
      error_file: './logs/pm2-error.log',
      out_file: './logs/pm2-out.log',
      log_file: './logs/pm2-combined.log',
      time: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      // Wait for graceful shutdown
      kill_timeout: 5000,
      wait_ready: true,
      listen_timeout: 10000,
    },
  ],
};
