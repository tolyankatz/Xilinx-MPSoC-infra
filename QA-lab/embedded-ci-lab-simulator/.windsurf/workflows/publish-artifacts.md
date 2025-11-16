---
description: Publish BSP artifacts to Minio artifact storage
---

# Publish BSP Artifacts to Minio

This workflow demonstrates how to publish BSP build artifacts to Minio.

## Prerequisites

- Lab services running
- BSP artifacts built (BOOT.BIN, image.ub, system.dtb, rootfs/)
- Artifacts located in a directory

## Steps

1. Navigate to the monorepo directory
```bash
cd c:\source\Xilinx\Xilinx-MPSoC-infra\QA-lab\zcu102-bsp-validation-monorepo
```

2. Create sample artifacts (for demonstration)
```bash
mkdir -p sample_build
echo "Sample BOOT.BIN" > sample_build/BOOT.BIN
echo "Sample image.ub" > sample_build/image.ub
echo "Sample system.dtb" > sample_build/system.dtb
mkdir -p sample_build/rootfs
echo "Sample rootfs" > sample_build/rootfs/README.txt
```

3. Make the publish script executable (on Linux/in container)
```bash
docker-compose -f ../embedded-ci-lab-simulator/docker-compose.yml exec host_controller chmod +x /app/test_host/../scripts/publish_artifacts_to_minio.sh
```

4. Publish the artifacts with a build ID
```bash
docker-compose -f ../embedded-ci-lab-simulator/docker-compose.yml exec -w /app/test_host/.. host_controller ./scripts/publish_artifacts_to_minio.sh bsp-dev-123 sample_build
```

## Verification

1. Check Minio Console at http://localhost:9001
2. Navigate to `bsp-artifacts` bucket
3. Look for folder `bsp-dev-123`
4. Verify files are present:
   - BOOT.BIN
   - image.ub
   - system.dtb
   - rootfs/
   - deployment_manifest.yaml
   - build_metadata.json

## List Published Artifacts

```bash
docker-compose -f ../embedded-ci-lab-simulator/docker-compose.yml exec host_controller mc ls --recursive minio/bsp-artifacts/bsp-dev-123/
```

## View Manifest

```bash
docker-compose -f ../embedded-ci-lab-simulator/docker-compose.yml exec host_controller mc cat minio/bsp-artifacts/bsp-dev-123/deployment_manifest.yaml
```

## Usage in Pipeline

In Jenkins, this script is called automatically in the "Publish to Minio" stage:

```groovy
sh "./scripts/publish_artifacts_to_minio.sh ${BUILD_ID} build_output"
```
