# Simple Multi-User Setup (Browser-Based)

Simple guide for internal multi-user deployment using browser-based user IDs.

## Overview

- **No external authentication** required
- Each browser gets a unique user ID (GUID) stored in localStorage
- User data isolated by user ID
- Perfect for internal/HPC deployments

---

## How It Works

### Frontend (Browser)
1. On first visit, generate a random GUID (e.g., `user_abc123def456`)
2. Store GUID in browser's localStorage
3. Send GUID in `X-User-ID` header with every request

### Backend (Server)
1. Read `X-User-ID` header from requests
2. Store user data in `data/users/{user_id}/`
3. Each user gets isolated documents and indexes

**No passwords, no login forms, no external services.**

---

## Implementation

### Step 1: Update Frontend

Add to `frontend/src/App.vue`:

```vue
<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// Generate or retrieve user ID
const getUserId = () => {
  let userId = localStorage.getItem('asymptote_user_id')

  if (!userId) {
    // Generate new user ID
    userId = 'user_' + Math.random().toString(36).substring(2, 15) +
             Math.random().toString(36).substring(2, 15)
    localStorage.setItem('asymptote_user_id', userId)
    console.log('New user ID created:', userId)
  }

  return userId
}

// Setup axios interceptor to add user ID to all requests
onMounted(() => {
  const userId = getUserId()

  axios.interceptors.request.use((config) => {
    config.headers['X-User-ID'] = userId
    return config
  })
})
</script>
```

That's it for the frontend! Every request now includes the user ID.

### Step 2: Update Backend

Update `main.py` to read the `X-User-ID` header:

```python
from typing import Optional
from fastapi import Header

# Add this helper function after the imports
def get_user_id(x_user_id: Optional[str] = Header(None)) -> Optional[str]:
    """
    Extract user ID from X-User-ID header.

    Returns:
        User ID if multi-user mode enabled, None otherwise
    """
    if settings.enable_multi_user and x_user_id:
        # Sanitize user ID for filesystem
        return "".join(c for c in x_user_id if c.isalnum() or c in "-_")
    return None

def get_user_paths(user_id: Optional[str]) -> tuple[Path, Path]:
    """Get user-specific paths or shared paths."""
    if user_id:
        user_dir = settings.data_dir / "users" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        docs_dir = user_dir / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)

        indexes_dir = user_dir / "indexes"
        indexes_dir.mkdir(parents=True, exist_ok=True)

        return docs_dir, indexes_dir
    else:
        # Shared mode (default)
        return document_dir, settings.data_dir / "indexes"

# Update upload endpoint
@app.post("/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = Depends(get_user_id)
):
    docs_dir, _ = get_user_paths(user_id)

    # Rest of upload logic uses docs_dir instead of document_dir
    ...
```

### Step 3: Enable Multi-User Mode

In `.env`:

```bash
ENABLE_MULTI_USER=true
```

That's it! Now each browser has isolated data.

---

## File Structure

### Without Multi-User (Default)
```
data/
├── documents/     # All users share
└── indexes/       # All users share
```

### With Multi-User
```
data/
└── users/
    ├── user_abc123/
    │   ├── documents/
    │   └── indexes/
    └── user_def456/
        ├── documents/
        └── indexes/
```

---

## User Management

### View All Users

```bash
ls data/users/
```

### Delete a User's Data

```bash
rm -rf data/users/user_abc123/
```

### Reset Your Browser's User ID

In browser console:

```javascript
localStorage.removeItem('asymptote_user_id')
// Refresh page to get new user ID
```

---

## Security Considerations

### ⚠️ This is NOT Secure Authentication

- Users can change their X-User-ID header
- No password protection
- Anyone with the URL can access

### ✅ Acceptable For:

- **Internal networks** (behind firewall)
- **Trusted users** (company intranet, HPC clusters)
- **Development/testing**
- **Single-organization** deployments

### ❌ NOT Acceptable For:

- Public internet
- Untrusted users
- Sensitive/confidential data
- Compliance requirements (HIPAA, SOC2, etc.)

---

## Advanced: Optional Password Protection

If you need basic security, add HTTP Basic Auth:

### Backend (main.py)

```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from secrets import compare_digest

security = HTTPBasic()

def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = compare_digest(credentials.username, "team")
    correct_password = compare_digest(credentials.password, "your-password")
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials.username

# Add to endpoints
@app.post("/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = Depends(get_user_id),
    _: str = Depends(verify_password)  # Require password
):
    ...
```

### Frontend

```javascript
// Set basic auth for all requests
axios.defaults.auth = {
  username: 'team',
  password: 'your-password'
}
```

---

## HPC Deployment

For HPC environments (Slurm, PBS, etc.):

### 1. Deploy on Head Node

```bash
# On head node
cd asymptote
pip install -r requirements.txt

# Run on specific port
PORT=8080 python main.py
```

### 2. Access from Compute Nodes

```bash
# In your job script
export ASYMPTOTE_URL="http://head-node:8080"

# Use from Python
import requests
response = requests.post(
    f"{os.environ['ASYMPTOTE_URL']}/search",
    headers={"X-User-ID": os.environ["USER"]},  # Use HPC username
    json={"query": "test"}
)
```

### 3. Use HPC Username as User ID

Instead of random GUID, use actual HPC username:

```javascript
// frontend/src/App.vue
const getUserId = () => {
  // Try to get from environment or use random
  return process.env.USER || localStorage.getItem('asymptote_user_id') ||
         'user_' + Math.random().toString(36).substring(2, 15)
}
```

---

## Testing

### Test Multi-User Locally

Terminal 1 (User A):
```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "X-User-ID: user_alice" \
  -F "files=@doc1.pdf"
```

Terminal 2 (User B):
```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "X-User-ID: user_bob" \
  -F "files=@doc2.pdf"
```

Check isolation:
```bash
ls data/users/
# Should see: user_alice/ user_bob/

ls data/users/user_alice/documents/
# Should see: doc1.pdf

ls data/users/user_bob/documents/
# Should see: doc2.pdf
```

---

## Comparison with Auth0

| Feature | Simple (This Guide) | Auth0 |
|---------|---------------------|-------|
| Setup Time | 5 minutes | 30 minutes |
| External Dependencies | None | Auth0 account |
| Monthly Cost | $0 | $0-35 |
| Password Protection | No (optional basic auth) | Yes |
| MFA | No | Yes |
| User Management | Manual | Dashboard |
| Best For | Internal/HPC | Production/Public |

---

## Migrating to Auth0 Later

If you need real authentication later, the multi-user structure stays the same:

1. Replace `X-User-ID` header with Auth0 JWT token
2. Extract user ID from JWT instead of header
3. Everything else stays identical

Your data structure is already Auth0-compatible!

---

## Summary

✅ **Simple**: Just add 10 lines of JavaScript
✅ **No Dependencies**: No external services
✅ **HPC-Friendly**: Works on internal networks
✅ **Scalable**: Each user gets isolated storage
⚠️ **Not Secure**: Only for trusted environments

**Perfect for internal HPC deployments where you control the network and trust the users.**
