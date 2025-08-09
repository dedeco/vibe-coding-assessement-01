# Documentation

This folder contains detailed documentation for the Condominium Analytics Agent project.

## Documentation Files

### Setup & Quick Start
- **[QUICKSTART.md](QUICKSTART.md)** - Complete step-by-step setup guide with manual configuration
- **[QUICK_START.md](QUICK_START.md)** - Fast setup guide for POC demonstrations using automated scripts

### Deployment Guides
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment strategies, data ingestion options, and configuration details
- **[GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md)** - Google Cloud Platform specific deployment instructions
- **[DEPLOY_DECISION.md](DEPLOY_DECISION.md)** - Architecture decisions and deployment strategy rationale

## Quick Navigation

### For New Users
1. Start with [QUICKSTART.md](QUICKSTART.md) for detailed setup
2. Or use [QUICK_START.md](QUICK_START.md) for rapid POC deployment

### For Production Deployment
1. Review [DEPLOY_DECISION.md](DEPLOY_DECISION.md) for architecture understanding
2. Follow [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment options
3. Use [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md) for Google Cloud specific instructions

## Scripts Reference
All automation scripts are located in the `scripts/` directory:
- `build_database.py` - Main database builder and data ingestion
- `populate_test_data.py` - Generate test data for demonstrations
- `test_api_responses.py` - API testing and validation
- `build_and_run.sh` - Automated build and start script
- `deploy.sh` - Deployment automation
- `setup.sh` - Environment setup script