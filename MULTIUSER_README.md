# Multi-User Support - Simple Internal Deployment

## Quick Summary

**Simple browser-based multi-user support for internal/HPC deployments.**

- ✅ **No Auth0, no passwords, no complexity**
- ✅ **Browser generates random user ID (GUID)**
- ✅ **Stored in localStorage, sent in headers**
- ✅ **Each user gets isolated data storage**
- ✅ **Perfect for trusted internal networks/HPC**

---

## How It Works

```
┌─────────────┐
│   Browser   │  Generates user_abc123
│ localStorage│  Stores in localStorage
└──────┬──────┘
       │ X-User-ID: user_abc123
       ▼
┌─────────────┐
│   Backend   │  Reads header
│   FastAPI   │  Routes to data/users/user_abc123/
└─────────────┘
```

### Data Structure

```
data/
└── users/
    ├── user_abc123/
    │   ├── documents/
    │   │   ├── report.pdf
    │   │   └── notes.txt
    │   └── indexes/
    │       ├── faiss.index
    │       └── metadata.db
    └── user_xyz789/
        ├── documents/
        └── indexes/
```

---

## Setup (5 Minutes)

### Step 1: Enable in Config

**`.env`**:
```bash
ENABLE_MULTI_USER=true
```

### Step 2: Add Frontend Code

**`frontend/src/App.vue`** - Add to `<script setup>`:

```javascript
const initUserTracking = () => {
  let userId = localStorage.getItem('asymptote_user_id')
  if (!userId) {
    userId = 'user_' + Math.random().toString(36).substring(2, 15) +
                        Math.random().toString(36).substring(2, 15)
    localStorage.setItem('asymptote_user_id', userId)
  }
  axios.interceptors.request.use((config) => {
    config.headers['X-User-ID'] = userId
    return config
  })
}

onMounted(() => {
  initUserTracking()
  // ... rest of code
})
```

### Step 3: Update Backend

See **[SIMPLE_MULTIUSER_CODE.md](SIMPLE_MULTIUSER_CODE.md)** for exact code to add to `main.py`.

**Summary**: Add functions to read `X-User-ID` header and route to user-specific directories.

---

## Testing

### Browser Console

```javascript
// Check your user ID
localStorage.getItem('asymptote_user_id')

// Reset (get new user)
localStorage.removeItem('asymptote_user_id')
location.reload()
```

### Command Line

```bash
# Upload as user Alice
curl -H "X-User-ID: alice" \
  -F "files=@test.pdf" \
  http://localhost:8000/documents/upload

# Upload as user Bob
curl -H "X-User-ID: bob" \
  -F "files=@test.pdf" \
  http://localhost:8000/documents/upload

# Verify isolation
ls data/users/alice/documents/
ls data/users/bob/documents/
```

---

## HPC Integration

### Use HPC Username

Instead of random GUID, use actual HPC username:

**Frontend**:
```javascript
// In job submission or SSH environment
const userId = process.env.USER || 'user_' + Math.random().toString(36).substring(2, 15)
```

**Backend API Call** (from Python job):
```python
import os
import requests

user_id = os.environ.get('USER', 'default_user')

response = requests.post(
    "http://hpc-head-node:8000/search",
    headers={"X-User-ID": user_id},
    json={"query": "machine learning", "top_k": 5}
)
```

### SLURM Job Example

```bash
#!/bin/bash
#SBATCH --job-name=asymptote_search
#SBATCH --time=01:00:00

# Use HPC username as user ID
USER_ID=$USER

# Query Asymptote API
curl -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "optimization algorithms", "top_k": 10}' \
  http://head-node:8000/search
```

---

## Security Notes

### ⚠️ This is NOT Secure Authentication

**Anyone can:**
- Change their X-User-ID header
- Access any user's data by guessing user IDs
- No password protection

### ✅ Acceptable For:

- **Internal networks** (behind firewall/VPN)
- **Trusted users** (company, research lab)
- **HPC clusters** (controlled access)
- **Development environments**

### ❌ NOT Acceptable For:

- **Public internet**
- **Untrusted users**
- **Sensitive data** (HIPAA, financial, etc.)
- **Production SaaS**

---

## Adding Basic Security

If you need minimal security:

### Option 1: HTTP Basic Auth

```python
# main.py
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from secrets import compare_digest

security = HTTPBasic()

def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    if not (compare_digest(credentials.username, "team") and
            compare_digest(credentials.password, "your-password")):
        raise HTTPException(status_code=401)
    return credentials.username

# Add to endpoints
@app.post("/documents/upload")
async def upload_documents(
    ...,
    _: str = Depends(verify_password)  # Require password
):
    ...
```

### Option 2: VPN/Firewall

Deploy behind VPN or firewall - simplest and most secure for internal use.

### Option 3: IP Whitelist

```python
# main.py
ALLOWED_IPS = {"10.0.0.0/8", "192.168.0.0/16"}  # Internal ranges

@app.middleware("http")
async def check_ip(request: Request, call_next):
    client_ip = request.client.host
    if not any(ipaddress.ip_address(client_ip) in ipaddress.ip_network(net)
               for net in ALLOWED_IPS):
        raise HTTPException(status_code=403, detail="Access denied")
    return await call_next(request)
```

---

## Management

### List All Users

```bash
ls -la data/users/
```

### User Storage Usage

```bash
du -sh data/users/*/
```

### Delete User Data

```bash
rm -rf data/users/user_abc123/
```

### Backup User Data

```bash
tar -czf backup_user_abc123.tar.gz data/users/user_abc123/
```

---

## Comparison

| Feature | Simple (This) | Auth0 | No Multi-User |
|---------|---------------|-------|---------------|
| Setup | 5 min | 30 min | 0 min |
| External Deps | None | Auth0 | None |
| Cost | $0 | $0-35/mo | $0 |
| Security | Basic | Strong | None |
| Best For | Internal/HPC | Production | Single user |

---

## Files to Check

- **[MULTIUSER_SIMPLE.md](MULTIUSER_SIMPLE.md)** - Full guide with examples
- **[SIMPLE_MULTIUSER_CODE.md](SIMPLE_MULTIUSER_CODE.md)** - Exact code to add
- **`.env.example`** - Configuration template

---

## FAQ

**Q: Can users see each other's documents?**
A: Not through the UI, but they could by changing the X-User-ID header.

**Q: Is this production-ready?**
A: For internal networks, yes. For public internet, no.

**Q: Can I use real usernames instead of GUIDs?**
A: Yes! Perfect for HPC - use `$USER` environment variable.

**Q: How do I backup everything?**
A: `tar -czf backup.tar.gz data/users/`

**Q: Can I migrate to Auth0 later?**
A: Yes! The data structure is compatible.

---

## Summary

**Perfect for:**
- Internal company deployments
- HPC/research clusters
- Development environments
- Trusted user groups

**Implementation:**
- Frontend: 10 lines of JavaScript
- Backend: 50 lines of Python
- No external dependencies
- Works with existing infrastructure

**Next Steps:**
1. Add frontend code (5 min)
2. Add backend code (10 min)
3. Set `ENABLE_MULTI_USER=true`
4. Test with `curl`
5. Deploy to your HPC/internal network

🎉 **Done!** Simple multi-user support without authentication complexity.
