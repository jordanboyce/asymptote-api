<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold">Settings & Information</h2>

    <!-- System Info -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">System Information</h3>
        <div v-if="loading" class="flex justify-center py-4">
          <span class="loading loading-spinner"></span>
        </div>
        <div v-else class="space-y-2">
          <div class="flex justify-between">
            <span class="font-semibold">Status:</span>
            <span class="badge badge-success">{{ health.status }}</span>
          </div>
          <div class="flex justify-between">
            <span class="font-semibold">Indexed Chunks:</span>
            <span>{{ health.indexed_chunks?.toLocaleString() || 0 }}</span>
          </div>
          <div class="flex justify-between">
            <span class="font-semibold">Embedding Model:</span>
            <span class="font-mono text-sm">all-MiniLM-L6-v2</span>
          </div>
          <div class="flex justify-between">
            <span class="font-semibold">Vector Dimensions:</span>
            <span>384</span>
          </div>
        </div>
      </div>
    </div>

    <!-- API Documentation -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">API Documentation</h3>
        <p class="text-sm">Access the interactive API documentation to explore all endpoints.</p>
        <div class="card-actions">
          <a href="/docs" target="_blank" class="btn btn-primary btn-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
            Open API Docs
          </a>
        </div>
      </div>
    </div>

    <!-- AI Integration -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">AI Integration</h3>
        <p class="text-sm text-base-content/70 mb-2">
          Connect your own AI provider to get answers from your documents, not just search results.
          Your key is stored only in your browser and sent per request. The server never stores it.
        </p>

        <!-- Provider Selection -->
        <div class="form-control mb-3">
          <label class="label">
            <span class="label-text">Provider</span>
          </label>
          <div class="flex gap-2">
            <button
              class="btn btn-sm flex-1"
              :class="aiSettings.provider === 'anthropic' ? 'btn-primary' : 'btn-ghost'"
              @click="setProvider('anthropic')"
            >
              Anthropic
            </button>
            <button
              class="btn btn-sm flex-1"
              :class="aiSettings.provider === 'openai' ? 'btn-primary' : 'btn-ghost'"
              @click="setProvider('openai')"
            >
              OpenAI
            </button>
          </div>
        </div>

        <!-- API Key Input -->
        <div class="form-control">
          <label class="label">
            <span class="label-text">{{ aiSettings.provider === 'openai' ? 'OpenAI' : 'Anthropic' }} API Key</span>
          </label>
          <div class="join w-full">
            <input
              v-model="apiKey"
              :type="showKey ? 'text' : 'password'"
              :placeholder="aiSettings.provider === 'openai' ? 'sk-...' : 'sk-ant-...'"
              class="input input-bordered join-item flex-1"
              @input="apiKeyDirty = true; apiKeyStatus = ''"
            />
            <button class="btn join-item" @click="showKey = !showKey">
              {{ showKey ? 'Hide' : 'Show' }}
            </button>
            <button
              class="btn btn-primary join-item"
              @click="validateAndSaveKey"
              :disabled="validatingKey || !apiKey.trim()"
            >
              <span v-if="validatingKey" class="loading loading-spinner loading-xs"></span>
              {{ validatingKey ? '' : 'Save' }}
            </button>
          </div>
          <label class="label">
            <span class="label-text-alt">
              <a v-if="aiSettings.provider === 'openai'" href="https://platform.openai.com/api-keys" target="_blank" class="link link-primary">Get an OpenAI key</a>
              <a v-else href="https://console.anthropic.com/settings/keys" target="_blank" class="link link-primary">Get an Anthropic key</a>
            </span>
            <span v-if="apiKeyStatus === 'valid'" class="label-text-alt text-success font-semibold">✓ Key valid</span>
            <span v-else-if="apiKeyStatus === 'invalid'" class="label-text-alt text-error font-semibold">✗ Invalid key</span>
            <span v-else-if="apiKeyStatus === 'saved'" class="label-text-alt text-success font-semibold">✓ Saved</span>
            <span v-else-if="apiKeyStatus === 'error'" class="label-text-alt text-error font-semibold">✗ Error validating</span>
          </label>
          <div v-if="validationError" class="text-xs text-error mt-1 px-1">{{ validationError }}</div>
        </div>

        <!-- Remove Key -->
        <div v-if="hasStoredKey && !apiKeyDirty" class="mt-2">
          <button class="btn btn-ghost btn-sm text-error" @click="removeKey">
            Remove stored key
          </button>
        </div>

        <!-- AI Feature Toggles -->
        <div v-if="hasStoredKey" class="divider"></div>
        <div v-if="hasStoredKey" class="space-y-3">
          <h4 class="font-semibold text-sm">AI Features</h4>

          <div class="form-control">
            <label class="label cursor-pointer justify-start gap-4">
              <input
                type="checkbox"
                class="toggle toggle-primary toggle-sm"
                :checked="aiSettings.rerank"
                @change="toggleAI('rerank')"
              />
              <div>
                <span class="label-text font-medium">Result Reranking</span>
                <p class="text-xs text-base-content/60">
                  Vector search finds semantically similar text, but similar doesn't always mean relevant.
                  Reranking uses AI to judge which results actually answer your question. Most useful with large document collections.
                </p>
              </div>
            </label>
          </div>

          <div class="form-control">
            <label class="label cursor-pointer justify-start gap-4">
              <input
                type="checkbox"
                class="toggle toggle-primary toggle-sm"
                :checked="aiSettings.synthesize"
                @change="toggleAI('synthesize')"
              />
              <div>
                <span class="label-text font-medium">Answer Synthesis</span>
                <p class="text-xs text-base-content/60">
                  Instead of reading through individual results, get a direct answer synthesized from your documents with citations back to specific pages.
                </p>
              </div>
            </label>
          </div>

          <div class="text-xs text-base-content/50 mt-2">
            Estimated cost per search: ~${{ estimatedCost }} (billed to your {{ aiSettings.provider === 'openai' ? 'OpenAI' : 'Anthropic' }} account)
          </div>
        </div>
      </div>
    </div>

    <!-- Search Configuration -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">Search Configuration</h3>
        <div class="form-control">
          <label class="label">
            <span class="label-text">Default Number of Results</span>
            <span class="label-text-alt">1-50</span>
          </label>
          <input
            v-model.number="defaultTopK"
            type="number"
            min="1"
            max="50"
            class="input input-bordered w-full max-w-xs"
          />
        </div>
      </div>
    </div>

    <!-- About -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">About Asymptote</h3>
        <div class="prose prose-sm max-w-none">
          <p>
            <strong>Asymptote</strong> is a self-hosted semantic search engine for PDF documents.
            Upload PDFs, search their contents using natural language, and get back relevant passages
            with direct links to the source pages.
          </p>
          <p class="text-sm italic">
            Why "Asymptote"? In mathematics, an asymptote is a line that a curve approaches but never
            quite reaches. Like semantic search continuously approaching perfect understanding of your
            documents - getting closer with every query, but always refining, always learning.
          </p>
          <div class="mt-4">
            <h4 class="font-semibold mb-2">Technology Stack:</h4>
            <ul class="text-sm space-y-1">
              <li><strong>Backend:</strong> FastAPI (Python)</li>
              <li><strong>Frontend:</strong> Vue 3 + Vite + Tailwind CSS + DaisyUI</li>
              <li><strong>Embeddings:</strong> sentence-transformers (all-MiniLM-L6-v2)</li>
              <li><strong>Vector Search:</strong> FAISS (Facebook AI Similarity Search)</li>
              <li><strong>PDF Processing:</strong> pypdf + pdfplumber</li>
              <li><strong>Metadata Storage:</strong> SQLite or JSON</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Theme Toggle -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">Appearance</h3>
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              class="toggle toggle-primary"
              :checked="isDark"
              @change="toggleTheme"
            />
            <span class="label-text">Dark Mode</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Danger Zone -->
    <div class="card bg-error/10 border border-error">
      <div class="card-body">
        <h3 class="card-title text-error">Danger Zone</h3>
        <p class="text-sm">Permanently delete all documents, indexes, and data. This action cannot be undone.</p>

        <!-- Success Alert -->
        <div v-if="clearSuccess" class="alert alert-success">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>All data has been cleared successfully!</span>
        </div>

        <!-- Error Alert -->
        <div v-if="clearError" class="alert alert-error">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ clearError }}</span>
        </div>

        <div class="card-actions justify-end">
          <button class="btn btn-error" @click="confirmClearAll" :disabled="clearing">
            <svg v-if="!clearing" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
            <span v-if="clearing" class="loading loading-spinner"></span>
            {{ clearing ? 'Clearing...' : 'Clear All Data' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Clear All Confirmation Modal -->
    <dialog ref="clearModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg text-error">⚠️ Clear All Data</h3>
        <p class="py-4">
          This will <strong>permanently delete</strong>:
        </p>
        <ul class="list-disc list-inside space-y-1 text-sm mb-4">
          <li>All uploaded PDF files</li>
          <li>All vector embeddings and indexes</li>
          <li>All metadata (documents, chunks, search history)</li>
        </ul>
        <p class="text-sm text-error font-semibold">
          This action cannot be undone. Are you absolutely sure?
        </p>
        <div class="modal-action">
          <button class="btn" @click="closeClearModal" :disabled="clearing">Cancel</button>
          <button class="btn btn-error" @click="clearAllData" :disabled="clearing">
            <span v-if="clearing" class="loading loading-spinner"></span>
            {{ clearing ? 'Clearing...' : 'Yes, Delete Everything' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeClearModal">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits(['data-cleared'])

const loading = ref(false)
const health = ref({})
const defaultTopK = ref(10)
const isDark = ref(false)
const clearing = ref(false)
const clearSuccess = ref(false)
const clearError = ref('')
const clearModal = ref(null)

// AI integration state
const apiKey = ref('')
const showKey = ref(false)
const validatingKey = ref(false)
const apiKeyStatus = ref('')
const apiKeyDirty = ref(false)
const hasStoredKey = ref(false)
const validationError = ref('')
const aiSettings = ref({
  provider: 'anthropic',
  rerank: false,
  synthesize: false,
})

const estimatedCost = computed(() => {
  let cost = 0
  if (aiSettings.value.rerank) cost += 0.0005
  if (aiSettings.value.synthesize) cost += 0.015
  return cost.toFixed(4)
})

const setProvider = (provider) => {
  // If switching providers, clear the saved key since it won't work for the other
  if (provider !== aiSettings.value.provider && hasStoredKey.value) {
    removeKey()
  }
  aiSettings.value.provider = provider
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
}

const validateAndSaveKey = async () => {
  if (!apiKey.value.trim()) return
  validatingKey.value = true
  apiKeyStatus.value = ''
  validationError.value = ''

  try {
    const response = await axios.post('/api/ai/validate-key', null, {
      headers: {
        'X-AI-Key': apiKey.value.trim(),
        'X-AI-Provider': aiSettings.value.provider,
      }
    })
    if (response.data.valid) {
      localStorage.setItem('ai_api_key', apiKey.value.trim())
      localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
      hasStoredKey.value = true
      apiKeyDirty.value = false
      apiKeyStatus.value = 'valid'
      validationError.value = ''
    } else {
      apiKeyStatus.value = 'invalid'
      if (response.data.error) {
        validationError.value = response.data.error
      } else {
        validationError.value = 'The API key was rejected. Please check it and try again.'
      }
    }
  } catch (err) {
    apiKeyStatus.value = 'error'
    validationError.value = err.response?.data?.detail || 'Network error. Check your connection and try again.'
  } finally {
    validatingKey.value = false
  }
}

const removeKey = () => {
  localStorage.removeItem('ai_api_key')
  apiKey.value = ''
  hasStoredKey.value = false
  apiKeyStatus.value = ''
  apiKeyDirty.value = false
  aiSettings.value = { ...aiSettings.value, rerank: false, synthesize: false }
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
}

const toggleAI = (feature) => {
  aiSettings.value[feature] = !aiSettings.value[feature]
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
}

const loadAISettings = () => {
  const storedKey = localStorage.getItem('ai_api_key')
  if (storedKey) {
    apiKey.value = storedKey
    hasStoredKey.value = true
    apiKeyDirty.value = false
    apiKeyStatus.value = 'saved'
  }
  const storedSettings = localStorage.getItem('ai_settings')
  if (storedSettings) {
    try {
      const parsed = JSON.parse(storedSettings)
      aiSettings.value = {
        provider: parsed.provider || 'anthropic',
        rerank: !!parsed.rerank,
        synthesize: !!parsed.synthesize,
      }
    } catch { /* use defaults */ }
  }
}

const loadHealth = async () => {
  loading.value = true
  try {
    const response = await axios.get('/health')
    health.value = response.data
  } catch (error) {
    console.error('Error loading health:', error)
  } finally {
    loading.value = false
  }
}

const toggleTheme = () => {
  isDark.value = !isDark.value
  const theme = isDark.value ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
}

const confirmClearAll = () => {
  clearSuccess.value = false
  clearError.value = ''
  clearModal.value?.showModal()
}

const closeClearModal = () => {
  if (!clearing.value) {
    clearModal.value?.close()
  }
}

const clearAllData = async () => {
  clearing.value = true
  clearError.value = ''
  clearSuccess.value = false

  try {
    // Get all documents
    const docsResponse = await axios.get('/documents')
    const documents = docsResponse.data.documents || []

    // Delete each document
    for (const doc of documents) {
      await axios.delete(`/documents/${doc.document_id}`)
    }

    clearSuccess.value = true
    clearModal.value?.close()

    // Reload health to show 0 chunks
    await loadHealth()

    // Emit event to parent to refresh stats
    emit('data-cleared')

    // Clear success message after 5 seconds
    setTimeout(() => {
      clearSuccess.value = false
    }, 5000)
  } catch (error) {
    clearError.value = error.response?.data?.detail || 'Failed to clear data. Please try again.'
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  loadHealth()
  loadAISettings()

  // Load theme preference
  const savedTheme = localStorage.getItem('theme') || 'light'
  isDark.value = savedTheme === 'dark'
})
</script>
