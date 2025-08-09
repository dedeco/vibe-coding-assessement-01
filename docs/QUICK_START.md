# 🚀 Quick Start Guide - Vector Database Population

**For POC demonstration - choose one approach:**

## Option 1: Instant Setup (Recommended for Demo)

```bash
# One command - builds database with test data and verifies
python scripts/build_database.py --source test --reset

# Start API
cd src/web && python app.py

# Test it works
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How much was spent on electricity?"}'
```

**Result:** 579 diverse documents, ready in 30 seconds ✅

## Option 2: Real PDF Data

```bash
# Build from your actual PDF files
python scripts/build_database.py --source pdf --reset

# Start API
cd src/web && python app.py
```

**Result:** Real trial balance data from your PDFs 📄

## Option 3: Docker Deployment

Add to your `Dockerfile`:
```dockerfile
COPY scripts/build_database.py /app/
COPY scripts/populate_test_data.py /app/
RUN python scripts/build_database.py --source test --reset
CMD ["python", "src/web/app.py"]
```

## Option 4: Auto-build Script

```bash
# Use the generated build script
chmod +x build_and_run.sh
./scripts/build_and_run.sh
```

---

## 🎯 Which Option to Choose?

| Use Case | Recommended | Why |
|----------|-------------|-----|
| **Demo/Presentation** | Option 1 (test data) | Fast, diverse, no dependencies |
| **Development** | Option 1 (test data) | Predictable, no PDF requirements |
| **Production POC** | Option 2 (real PDFs) | Actual data, realistic responses |
| **Container Deploy** | Option 3 (Docker) | Repeatable, scalable |
| **Quick Demo** | Option 4 (script) | One command, full setup |

## ✅ Verification

After building, verify with:
```bash
python scripts/test_api_responses.py
```

Should show: "✅ No hardcoded response issues found!"