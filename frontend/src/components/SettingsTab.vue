<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold">Settings</h2>

    <!-- AI Integration -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">AI Integration</h3>
        <p class="text-sm text-base-content/70 mb-2">
          Connect your own AI provider to get answers from your documents, not just search results.
          Your key is stored only in your browser and sent per request.
        </p>

        <!-- Provider Selection -->
        <div class="form-control mb-3">
          <label class="label">
            <span class="label-text">Provider</span>
          </label>
          <div class="flex gap-2">
            <button
              class="btn btn-sm flex-1 relative"
              :class="aiSettings.provider === 'anthropic' ? 'btn-primary' : 'btn-ghost'"
              @click="setProvider('anthropic')"
            >
              Anthropic
              <span v-if="hasAnthropicKey" class="absolute -top-1 -right-1 badge badge-success badge-xs">&#10003;</span>
            </button>
            <button
              class="btn btn-sm flex-1 relative"
              :class="aiSettings.provider === 'openai' ? 'btn-primary' : 'btn-ghost'"
              @click="setProvider('openai')"
            >
              OpenAI
              <span v-if="hasOpenAIKey" class="absolute -top-1 -right-1 badge badge-success badge-xs">&#10003;</span>
            </button>
            <button
              class="btn btn-sm flex-1 relative"
              :class="aiSettings.provider === 'ollama' ? 'btn-primary' : 'btn-ghost'"
              @click="setProvider('ollama')"
            >
              Ollama
              <span v-if="ollamaAvailable" class="absolute -top-1 -right-1 badge badge-success badge-xs">&#10003;</span>
            </button>
          </div>
        </div>

        <!-- Ollama Model Selection -->
        <div v-if="aiSettings.provider === 'ollama'" class="form-control">
          <div v-if="checkingOllama" class="flex justify-center py-4">
            <span class="loading loading-spinner"></span>
          </div>

          <div v-else-if="!ollamaAvailable" class="alert alert-warning">
            <div>
              <div class="font-bold">Ollama not detected</div>
              <div class="text-sm">Install from <a href="https://ollama.com" target="_blank" class="link link-primary">ollama.com</a></div>
            </div>
          </div>

          <div v-else class="space-y-3">
            <div class="alert alert-success py-2">
              <span class="text-sm">Ollama running - {{ ollamaModels.length }} model(s) available</span>
            </div>

            <select
              v-model="selectedOllamaModel"
              class="select select-bordered w-full"
              @change="saveOllamaModel"
            >
              <option v-for="model in ollamaModels" :key="model.name" :value="model.name">
                {{ model.name }} ({{ formatBytes(model.size) }})
              </option>
            </select>
          </div>

          <button class="btn btn-sm btn-ghost mt-2" @click="checkOllamaStatus">
            Refresh
          </button>
        </div>

        <!-- API Key Input (Cloud Providers) -->
        <div v-else class="form-control">
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
            <span v-if="apiKeyStatus === 'valid'" class="label-text-alt text-success font-semibold">Key valid</span>
            <span v-else-if="apiKeyStatus === 'invalid'" class="label-text-alt text-error font-semibold">Invalid key</span>
            <span v-else-if="apiKeyStatus === 'saved'" class="label-text-alt text-success font-semibold">Saved</span>
          </label>
        </div>

        <!-- Remove Key -->
        <div v-if="aiSettings.provider !== 'ollama' && hasStoredKey && !apiKeyDirty" class="mt-2">
          <button class="btn btn-ghost btn-sm text-error" @click="removeKey">
            Remove stored key
          </button>
        </div>

        <!-- AI Feature Toggles -->
        <div v-if="hasStoredKey || (aiSettings.provider === 'ollama' && ollamaAvailable)" class="divider"></div>
        <div v-if="hasStoredKey || (aiSettings.provider === 'ollama' && ollamaAvailable)" class="space-y-3">
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
                <p class="text-xs text-base-content/60">Use AI to judge which results actually answer your question</p>
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
                <p class="text-xs text-base-content/60">Get a direct answer synthesized from your documents with citations</p>
              </div>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Appearance -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">Appearance</h3>

        <div class="form-control w-full">
          <label class="label">
            <span class="label-text">Theme</span>
          </label>
          <select
            v-model="selectedTheme"
            class="select select-bordered w-full"
            @change="applyTheme"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="cupcake">Cupcake</option>
            <option value="dracula">Dracula</option>
            <option value="nord">Nord</option>
          </select>
        </div>

        <!-- Theme Preview -->
        <div class="mt-4 p-4 rounded-lg border border-base-300 bg-base-100">
          <div class="flex flex-wrap gap-2">
            <button class="btn btn-primary btn-sm">Primary</button>
            <button class="btn btn-secondary btn-sm">Secondary</button>
            <button class="btn btn-accent btn-sm">Accent</button>
          </div>
        </div>
      </div>
    </div>

    <!-- PDF Processing -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">PDF Processing</h3>
        <p class="text-sm text-base-content/70 mb-2">
          Configure how PDFs are processed. OCR is useful for scanned documents but requires significant memory.
        </p>

        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              class="toggle toggle-primary toggle-sm"
              v-model="ocrEnabled"
              @change="saveOCRSettings"
            />
            <div>
              <span class="label-text font-medium">Enable OCR for Scanned PDFs</span>
              <p class="text-xs text-base-content/60">
                Use optical character recognition for image-based PDFs.
                <span class="text-warning">Warning: Requires 4-8GB+ RAM for large documents.</span>
              </p>
            </div>
          </label>
        </div>

        <div v-if="ocrEnabled" class="mt-3 space-y-3">
          <div class="form-control">
            <label class="label">
              <span class="label-text">OCR Engine</span>
            </label>
            <select
              v-model="ocrEngine"
              class="select select-bordered select-sm w-full max-w-xs"
              @change="saveOCRSettings"
            >
              <option value="auto">Auto (best available)</option>
              <option value="pytesseract">Tesseract (lightweight)</option>
              <option value="docling">Docling (high quality, high memory)</option>
              <option value="marker">Marker (high quality, high memory)</option>
            </select>
            <label class="label">
              <span class="label-text-alt text-base-content/60">
                Tesseract is recommended for most use cases. Docling/Marker provide better results but use more memory.
              </span>
            </label>
          </div>

          <div class="alert alert-warning py-2 text-sm">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-5 w-5" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>OCR processing may fail on large PDFs (100+ pages) due to memory limits. Consider splitting large documents.</span>
          </div>
        </div>

        <div v-if="ocrSettingsSaved" class="alert alert-success py-2 mt-3">
          <span>Settings saved. Restart the server for changes to take effect.</span>
        </div>
      </div>
    </div>

    <!-- Danger Zone -->
    <div class="card bg-error/10 border border-error">
      <div class="card-body">
        <h3 class="card-title text-error">Danger Zone</h3>
        <p class="text-sm">Permanently delete all documents and indexes in the current collection.</p>

        <div v-if="clearSuccess" class="alert alert-success">
          <span>All data has been cleared successfully!</span>
        </div>

        <div v-if="clearError" class="alert alert-error">
          <span>{{ clearError }}</span>
        </div>

        <div class="card-actions justify-end">
          <button class="btn btn-error" @click="confirmClearAll" :disabled="clearing">
            <span v-if="clearing" class="loading loading-spinner"></span>
            {{ clearing ? 'Clearing...' : 'Clear All Data' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Clear All Confirmation Modal -->
    <dialog ref="clearModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg text-error">Clear All Data</h3>
        <p class="py-4">
          This will <strong>permanently delete</strong> all documents and indexes in <strong>{{ collectionStore.currentCollection?.name || 'Default' }}</strong>.
        </p>
        <p class="text-sm text-error font-semibold">
          This action cannot be undone.
        </p>
        <div class="modal-action">
          <button class="btn" @click="closeClearModal" :disabled="clearing">Cancel</button>
          <button class="btn btn-error" @click="clearAllData" :disabled="clearing">
            <span v-if="clearing" class="loading loading-spinner"></span>
            {{ clearing ? 'Clearing...' : 'Delete Everything' }}
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
import { useCollectionStore } from '../stores/collectionStore'

const emit = defineEmits(['data-cleared', 'stats-updated'])

const collectionStore = useCollectionStore()

// Theme
const selectedTheme = ref('light')

// Clear data
const clearing = ref(false)
const clearSuccess = ref(false)
const clearError = ref('')
const clearModal = ref(null)

// OCR settings
const ocrEnabled = ref(false)
const ocrEngine = ref('auto')
const ocrSettingsSaved = ref(false)

// AI integration state
const apiKey = ref('')
const showKey = ref(false)
const validatingKey = ref(false)
const apiKeyStatus = ref('')
const apiKeyDirty = ref(false)
const hasStoredKey = ref(false)
const aiSettings = ref({
  provider: 'anthropic',
  rerank: false,
  synthesize: false,
})

// Ollama state
const checkingOllama = ref(false)
const ollamaAvailable = ref(false)
const ollamaModels = ref([])
const selectedOllamaModel = ref('')

// Computed
const hasAnthropicKey = computed(() => !!localStorage.getItem('ai_api_key_anthropic'))
const hasOpenAIKey = computed(() => !!localStorage.getItem('ai_api_key_openai'))

// AI Methods
const setProvider = (provider) => {
  aiSettings.value.provider = provider
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
  loadProviderKey()
  if (provider === 'ollama') {
    checkOllamaStatus()
  }
}

const validateAndSaveKey = async () => {
  if (!apiKey.value.trim()) return
  validatingKey.value = true
  apiKeyStatus.value = ''

  try {
    const response = await axios.post('/api/ai/validate-key', null, {
      headers: {
        'X-AI-Key': apiKey.value.trim(),
        'X-AI-Provider': aiSettings.value.provider,
      }
    })
    if (response.data.valid) {
      const keyName = `ai_api_key_${aiSettings.value.provider}`
      localStorage.setItem(keyName, apiKey.value.trim())
      localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
      hasStoredKey.value = true
      apiKeyDirty.value = false
      apiKeyStatus.value = 'valid'
    } else {
      apiKeyStatus.value = 'invalid'
    }
  } catch {
    apiKeyStatus.value = 'invalid'
  } finally {
    validatingKey.value = false
  }
}

const removeKey = () => {
  const keyName = `ai_api_key_${aiSettings.value.provider}`
  localStorage.removeItem(keyName)
  apiKey.value = ''
  hasStoredKey.value = false
  apiKeyStatus.value = ''
  apiKeyDirty.value = false
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
}

const toggleAI = (feature) => {
  aiSettings.value[feature] = !aiSettings.value[feature]
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
}

const loadProviderKey = () => {
  const keyName = `ai_api_key_${aiSettings.value.provider}`
  const storedKey = localStorage.getItem(keyName)
  if (storedKey) {
    apiKey.value = storedKey
    hasStoredKey.value = true
    apiKeyDirty.value = false
    apiKeyStatus.value = 'saved'
  } else {
    apiKey.value = ''
    hasStoredKey.value = false
    apiKeyDirty.value = false
    apiKeyStatus.value = ''
  }
}

const loadAISettings = () => {
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
  loadProviderKey()
}

// Ollama Methods
const checkOllamaStatus = async () => {
  checkingOllama.value = true
  try {
    const response = await axios.get('/api/ollama/status')
    ollamaAvailable.value = response.data.available
    ollamaModels.value = response.data.models || []

    const savedModel = localStorage.getItem('ollama_model')
    if (savedModel && ollamaModels.value.find(m => m.name === savedModel)) {
      selectedOllamaModel.value = savedModel
    } else if (ollamaModels.value.length > 0) {
      selectedOllamaModel.value = ollamaModels.value[0].name
      localStorage.setItem('ollama_model', selectedOllamaModel.value)
    }
  } catch {
    ollamaAvailable.value = false
    ollamaModels.value = []
  } finally {
    checkingOllama.value = false
  }
}

const saveOllamaModel = () => {
  localStorage.setItem('ollama_model', selectedOllamaModel.value)
}

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// OCR Settings
const loadOCRSettings = async () => {
  try {
    const response = await axios.get('/api/config')
    ocrEnabled.value = response.data.enable_ocr || false
    ocrEngine.value = response.data.ocr_engine || 'auto'
  } catch {
    // Use defaults if config endpoint not available
    ocrEnabled.value = false
    ocrEngine.value = 'auto'
  }
}

const saveOCRSettings = async () => {
  try {
    await axios.post('/api/config', {
      enable_ocr: ocrEnabled.value,
      ocr_engine: ocrEngine.value,
    })
    ocrSettingsSaved.value = true
    setTimeout(() => {
      ocrSettingsSaved.value = false
    }, 5000)
  } catch (error) {
    console.error('Failed to save OCR settings:', error)
  }
}

// Theme
const applyTheme = () => {
  document.documentElement.setAttribute('data-theme', selectedTheme.value)
  localStorage.setItem('theme', selectedTheme.value)
  window.dispatchEvent(new CustomEvent('theme-changed'))
}

// Clear data
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
    const collectionId = collectionStore.currentCollectionId
    const docsResponse = await axios.get(`/documents?collection_id=${collectionId}`)
    const documents = docsResponse.data.documents || []

    for (const doc of documents) {
      await axios.delete(`/documents/${doc.document_id}?collection_id=${collectionId}`)
    }

    clearSuccess.value = true
    clearModal.value?.close()
    emit('data-cleared')

    setTimeout(() => {
      clearSuccess.value = false
    }, 5000)
  } catch (error) {
    clearError.value = error.response?.data?.detail || 'Failed to clear data'
  } finally {
    clearing.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadAISettings()
  loadOCRSettings()

  // Load theme
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    selectedTheme.value = savedTheme
  } else {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    selectedTheme.value = prefersDark ? 'dark' : 'light'
  }

  // Check Ollama if that's the selected provider
  if (aiSettings.value.provider === 'ollama') {
    checkOllamaStatus()
  }
})
</script>
