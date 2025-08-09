#!/bin/bash

# GCP Deployment Script for Condominium Analytics Agent
# Project: andresousa-pso-upskilling

set -e

# Configuration
PROJECT_ID="andresousa-pso-upskilling"
SERVICE_NAME="condominium-analytics"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment to GCP...${NC}"

# Check if required tools are installed
check_dependencies() {
    echo -e "${YELLOW}Checking dependencies...${NC}"

    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}gcloud CLI is not installed. Please install it first.${NC}"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install it first.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Dependencies check passed.${NC}"
}

# Set up GCP project
setup_gcp() {
    echo -e "${YELLOW}Setting up GCP project...${NC}"

    # Set the project
    gcloud config set project ${PROJECT_ID}

    # Enable required APIs
    echo -e "${YELLOW}Enabling required APIs...${NC}"
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable containerregistry.googleapis.com

    echo -e "${GREEN}GCP setup completed.${NC}"
}

# Build and push Docker image
build_and_push() {
    echo -e "${YELLOW}Building Docker image...${NC}"

    # Build the image
    docker build -t ${IMAGE_NAME} .

    # Configure Docker to use gcloud as credential helper
    gcloud auth configure-docker

    # Push to Google Container Registry
    echo -e "${YELLOW}Pushing image to GCR...${NC}"
    docker push ${IMAGE_NAME}

    echo -e "${GREEN}Image built and pushed successfully.${NC}"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    echo -e "${YELLOW}Deploying to Cloud Run...${NC}"

    gcloud run deploy ${SERVICE_NAME} \
        --image=${IMAGE_NAME} \
        --platform=managed \
        --region=${REGION} \
        --allow-unauthenticated \
        --port=8000 \
        --memory=2Gi \
        --cpu=2 \
        --timeout=900 \
        --concurrency=100 \
        --max-instances=10 \
        --quiet

    # Get the service URL
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

    echo -e "${GREEN}Deployment completed!${NC}"
    echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
    echo -e "${GREEN}Health check: ${SERVICE_URL}/health${NC}"
    echo -e "${GREEN}API docs: ${SERVICE_URL}/docs${NC}"
}

# Set environment variables (optional)
set_env_vars() {
    echo -e "${YELLOW}Setting environment variables...${NC}"

    # Prompt for Claude API key if not set
    if [ -z "$CLAUDE_API_KEY" ]; then
        echo -e "${YELLOW}Enter your Claude API key (or press Enter to skip):${NC}"
        read -s CLAUDE_API_KEY
    fi

    if [ ! -z "$CLAUDE_API_KEY" ]; then
        gcloud run services update ${SERVICE_NAME} \
            --region=${REGION} \
            --set-env-vars="CLAUDE_API_KEY=${CLAUDE_API_KEY}" \
            --quiet
        echo -e "${GREEN}Environment variables updated.${NC}"
    fi
}

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up local Docker images...${NC}"
    docker rmi ${IMAGE_NAME} 2>/dev/null || true
}

# Main execution
main() {
    echo -e "${GREEN}=== GCP Deployment for Condominium Analytics Agent ===${NC}"
    echo -e "${GREEN}Project ID: ${PROJECT_ID}${NC}"
    echo -e "${GREEN}Service Name: ${SERVICE_NAME}${NC}"
    echo -e "${GREEN}Region: ${REGION}${NC}"
    echo ""

    check_dependencies
    setup_gcp
    build_and_push
    deploy_to_cloud_run
    set_env_vars
    cleanup

    echo -e "${GREEN}=== Deployment completed successfully! ===${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "1. Visit the service URL to test the application"
    echo -e "2. Check the health endpoint to verify all components are working"
    echo -e "3. Upload your PDF files and test the analytics functionality"
    echo -e "4. Monitor logs with: gcloud logs tail --log-filter=\"resource.type=cloud_run_revision\""
}

# Handle script interruption
trap cleanup EXIT

# Check if running with help flag
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "GCP Deployment Script for Condominium Analytics Agent"
    echo ""
    echo "Usage: ./deploy.sh [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  CLAUDE_API_KEY    Your Claude API key (optional)"
    echo ""
    echo "Prerequisites:"
    echo "  - gcloud CLI installed and authenticated"
    echo "  - Docker installed and running"
    echo "  - Project ${PROJECT_ID} exists and you have permissions"
    exit 0
fi

# Run main function
main
