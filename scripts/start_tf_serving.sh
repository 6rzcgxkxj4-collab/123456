#!/bin/bash
#
# Docker Compose setup for TensorFlow Serving
# This script helps deploy the face recognition model with TensorFlow Serving

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  TensorFlow Serving Deployment Script           ${NC}"
echo -e "${GREEN}================================================${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Configuration
MODEL_NAME="face_recognition"
MODEL_PATH="${PWD}/models/${MODEL_NAME}"
REST_PORT=8501
GRPC_PORT=8500

# Check if model exists
if [ ! -d "$MODEL_PATH" ]; then
    echo -e "${YELLOW}Warning: Model not found at ${MODEL_PATH}${NC}"
    echo "You can export a model using:"
    echo "  python scripts/export_model.py --output ./models/face_recognition"
    echo ""
    echo "Creating model directory..."
    mkdir -p "$MODEL_PATH"
fi

echo -e "\n${GREEN}Starting TensorFlow Serving...${NC}"
echo "Model path: $MODEL_PATH"
echo "REST API port: $REST_PORT"
echo "gRPC port: $GRPC_PORT"

# Run TensorFlow Serving container
docker run -d \
    --name tf-serving-face-recognition \
    -p ${REST_PORT}:8501 \
    -p ${GRPC_PORT}:8500 \
    --mount type=bind,source=${MODEL_PATH},target=/models/${MODEL_NAME} \
    -e MODEL_NAME=${MODEL_NAME} \
    tensorflow/serving

echo -e "\n${GREEN}TensorFlow Serving started!${NC}"
echo ""
echo "API Endpoints:"
echo "  REST: http://localhost:${REST_PORT}/v1/models/${MODEL_NAME}"
echo "  gRPC: localhost:${GRPC_PORT}"
echo ""
echo "To check model status:"
echo "  curl http://localhost:${REST_PORT}/v1/models/${MODEL_NAME}"
echo ""
echo "To stop the service:"
echo "  docker stop tf-serving-face-recognition"
echo "  docker rm tf-serving-face-recognition"
