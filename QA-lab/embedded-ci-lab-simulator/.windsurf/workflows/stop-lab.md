---
description: Stop all lab services and cleanup
---

# Stop Lab Services

This workflow stops all Docker containers for the BSP validation lab.

## Steps

1. Navigate to the embedded-ci-lab-simulator directory
```bash
cd c:\source\Xilinx\Xilinx-MPSoC-infra\QA-lab\embedded-ci-lab-simulator
```

// turbo
2. Stop all services
```bash
docker-compose down
```

## Optional: Clean Up Volumes

To remove all persistent data (Gitea repos, Jenkins configs, Minio artifacts):

**WARNING: This will delete all data!**

```bash
docker-compose down -v
```

## Verify Cleanup

Check that all containers are stopped:
```bash
docker-compose ps
```

Should show no running containers.
