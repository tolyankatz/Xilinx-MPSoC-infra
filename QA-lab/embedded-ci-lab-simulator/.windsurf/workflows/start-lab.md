---
description: Start all lab services (Gitea, Jenkins, Minio, Host Controller, DUT Simulator)
---

# Start Lab Services

This workflow starts all Docker containers for the BSP validation lab.

## Steps

1. Navigate to the embedded-ci-lab-simulator directory
```bash
cd c:\source\Xilinx\Xilinx-MPSoC-infra\QA-lab\embedded-ci-lab-simulator
```

// turbo
2. Start all services with docker-compose
```bash
docker-compose up -d --build
```

3. Wait for services to be healthy (approximately 30 seconds)

4. Verify all services are running
```bash
docker-compose ps
```

## Expected Output

All services should show status "Up":
- gitea
- minio
- jenkins
- host_controller
- dut_simulator

## Service URLs

Once started, access the services at:
- **Gitea**: http://localhost:3000 (admin/password)
- **Jenkins**: http://localhost:8080 (admin/admin)
- **Minio Console**: http://localhost:9001 (admin/password)

## Troubleshooting

If services fail to start:
- Check Docker is running
- Ensure ports 3000, 8080, 9000, 9001, 2223 are not in use
- Review logs: `docker-compose logs [service-name]`
