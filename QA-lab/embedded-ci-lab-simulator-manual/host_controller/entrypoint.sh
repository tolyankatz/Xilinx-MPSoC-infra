#!/bin/bash
set -e

# Generate SSH host keys if they do not exist
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
  ssh-keygen -A
fi

# Configure MinIO client alias and ensure required buckets exist
if [ -n "$MINIO_ALIAS" ] && [ -n "$MINIO_ENDPOINT" ] && [ -n "$MINIO_ROOT_USER" ] && [ -n "$MINIO_ROOT_PASSWORD" ]; then
  echo "[host_controller] Configuring MinIO client alias $MINIO_ALIAS -> $MINIO_ENDPOINT"
  mc alias set "$MINIO_ALIAS" "$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" --api S3v4 || true

  echo "[host_controller] Ensuring MinIO buckets exist"
  mc mb "$MINIO_ALIAS/bsp-firmware" || true
  mc mb "$MINIO_ALIAS/test-logs" || true
fi

echo "[host_controller] Starting SSH daemon"
exec /usr/sbin/sshd -D -e
