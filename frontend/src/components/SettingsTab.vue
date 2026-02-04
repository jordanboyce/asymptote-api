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

    <!-- Search Configuration -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">Search Configuration</h3>
        <div class="space-y-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">Default Number of Results</span>
            </label>
            <input
              v-model.number="defaultTopK"
              type="number"
              min="1"
              max="50"
              class="input input-bordered w-full max-w-xs"
            />
            <label class="label">
              <span class="label-text-alt">Number of results to return by default (1-50)</span>
            </label>
          </div>
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
import { ref, onMounted } from 'vue'
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

  // Load theme preference
  const savedTheme = localStorage.getItem('theme') || 'light'
  isDark.value = savedTheme === 'dark'
})
</script>
