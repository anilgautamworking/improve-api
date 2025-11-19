module.exports = {
  apps: [
    {
      name: 'improve-api',
      script: 'src/api/app.py',
      interpreter: 'venv/bin/python3',
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
      error_file: './logs/pm2-api-error.log',
      out_file: './logs/pm2-api-out.log',
      log_file: './logs/pm2-api-combined.log',
      time: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      // Wait for graceful shutdown
      kill_timeout: 5000,
      wait_ready: true,
      listen_timeout: 10000,
    },
    {
      name: 'prefect-worker',
      script: 'venv/bin/prefect',
      args: 'worker start -p improve-api -q default',
      interpreter: 'none',
      instances: 1,
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'production',
      },
      error_file: './logs/pm2-worker-error.log',
      out_file: './logs/pm2-worker-out.log',
      log_file: './logs/pm2-worker-combined.log',
      time: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      // Prefect worker needs time to connect
      wait_ready: false,
      kill_timeout: 10000,
    },
  ],
};
