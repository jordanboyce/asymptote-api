<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold">Documents</h2>

    <!-- Upload Section -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">Upload Documents</h3>

        <!-- Upload Mode Toggle -->
        <div role="tablist" class="tabs tabs-bordered mb-2">
          <button
            role="tab"
            class="tab gap-2"
            :class="{ 'tab-active': uploadMode === 'files' }"
            @click="setUploadMode('files')"
          >
            <FileText :size="16" />
            Select Files
          </button>
          <button
            role="tab"
            class="tab gap-2"
            :class="{ 'tab-active': uploadMode === 'folder' }"
            @click="setUploadMode('folder')"
          >
            <FolderOpen :size="16" />
            Select Folder
          </button>
        </div>

        <!-- File Upload Input -->
        <div v-if="uploadMode === 'files'" class="form-control w-full">
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".pdf,.txt,.docx,.csv,.md,.json"
            class="file-input file-input-bordered w-full"
            @change="handleFileSelect"
          />
          <label class="label">
            <span class="label-text-alt">Select one or more files (PDF, TXT, DOCX, CSV, MD, JSON)</span>
          </label>
        </div>

        <!-- Folder Upload Input -->
        <div v-if="uploadMode === 'folder'" class="form-control w-full">
          <input
            ref="folderInput"
            type="file"
            webkitdirectory
            directory
            class="file-input file-input-bordered w-full"
            @change="handleFolderSelect"
          />
          <label class="label">
            <span class="label-text-alt">Select a folder - only supported file types will be uploaded (PDF, TXT, DOCX, CSV, MD, JSON)</span>
          </label>
        </div>

        <!-- Selected Files -->
        <div v-if="selectedFiles.length > 0" class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold">{{ selectedFiles.length }} file{{ selectedFiles.length !== 1 ? 's' : '' }} selected ({{ formatTotalSize() }})</span>
            <div class="flex gap-2">
              <button
                class="btn btn-ghost btn-sm"
                @click="clearAllFiles"
                :disabled="uploading"
              >
                Clear
              </button>
              <button
                class="btn btn-primary btn-sm"
                @click="upload"
                :disabled="uploading || selectedFiles.length === 0"
              >
                <span v-if="uploading" class="loading loading-spinner loading-sm"></span>
                <CloudUpload v-else :size="16" />
                {{ uploading ? 'Indexing...' : 'Upload Now' }}
              </button>
            </div>
          </div>

          <!-- Large File Warning -->
          <div v-if="hasLargeFiles()" class="alert alert-warning alert-sm">
            <AlertTriangle :size="20" />
            <span class="text-xs">Large file(s) detected. Estimated time: {{ estimateProcessingTime() }}</span>
          </div>

          <!-- File List -->
          <div class="overflow-x-auto max-h-48 overflow-y-auto border rounded">
            <table class="table table-xs table-zebra">
              <tbody>
                <tr v-for="(file, index) in selectedFiles" :key="index">
                  <td class="truncate" :title="file.name">{{ file.name }}</td>
                  <td class="text-right">{{ formatFileSize(file.size) }}</td>
                  <td class="w-8">
                    <button
                      class="btn btn-ghost btn-xs text-error"
                      @click="removeFile(index)"
                      :disabled="uploading"
                    >
                      <X :size="14" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Progress -->
        <div v-if="uploading" class="space-y-2">
          <progress class="progress progress-primary w-full" :value="uploadProgress" max="100"></progress>
          <p class="text-xs text-center">Processing files... {{ uploadProgress }}%</p>
        </div>

        <!-- Success Alert -->
        <div v-if="uploadSuccess" class="alert alert-success alert-sm">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-5 w-5" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-xs">
            Uploaded {{ uploadResult.documents_processed }} document(s) - {{ uploadResult.total_pages }} pages, {{ uploadResult.total_chunks }} chunks
          </span>
        </div>

        <!-- Upload Error -->
        <div v-if="uploadError" class="alert alert-error alert-sm">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-5 w-5" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-xs">{{ uploadError }}</span>
        </div>
      </div>
    </div>

    <!-- Document List Header -->
    <div class="flex justify-between items-center">
      <div class="flex items-center gap-4">
        <h3 class="text-lg font-bold">Your Documents</h3>
        <div v-if="selectedDocuments.length > 0" class="badge badge-primary">
          {{ selectedDocuments.length }} selected
        </div>
      </div>
      <div class="flex gap-2">
        <button
          v-if="selectedDocuments.length > 0"
          class="btn btn-sm btn-error"
          @click="confirmBulkDelete"
          :disabled="deleting"
        >
          <Trash2 :size="16" />
          Delete Selected
        </button>
        <button class="btn btn-sm btn-ghost" @click="loadDocuments">
          <RefreshCw :size="16" />
          Refresh
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Documents Table -->
    <div v-else-if="documents.length > 0" class="overflow-x-auto">
      <table class="table table-zebra">
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                class="checkbox checkbox-sm"
                :checked="isAllSelected"
                @change="toggleSelectAll"
                :disabled="deleting"
              />
            </th>
            <th>Filename</th>
            <th>Pages</th>
            <th>Chunks</th>
            <th>Uploaded</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in documents" :key="doc.document_id" :class="{ 'bg-primary/10': isSelected(doc.document_id) }">
            <td>
              <input
                type="checkbox"
                class="checkbox checkbox-sm"
                :checked="isSelected(doc.document_id)"
                @change="toggleSelect(doc.document_id)"
                :disabled="deleting"
              />
            </td>
            <td>
              <div class="flex items-center gap-3">
                <div class="flex items-center justify-center w-10 h-10 rounded-lg bg-error/20">
                  <FileText :size="24" class="text-error" />
                </div>
                <div>
                  <div class="font-bold">{{ doc.filename }}</div>
                  <div class="text-sm opacity-50">{{ doc.document_id.substring(0, 8) }}...</div>
                </div>
              </div>
            </td>
            <td>{{ doc.total_pages }}</td>
            <td>{{ doc.total_chunks }}</td>
            <td>{{ formatDate(doc.indexed_at) }}</td>
            <td>
              <div class="flex gap-2">
                <a
                  :href="`/documents/${doc.document_id}/pdf?collection_id=${collectionStore.currentCollectionId}`"
                  target="_blank"
                  class="btn btn-ghost btn-xs"
                  title="View PDF"
                >
                  <Eye :size="16" />
                </a>
                <button
                  class="btn btn-ghost btn-xs text-error"
                  @click="confirmDelete(doc)"
                  :disabled="deleting"
                  title="Delete document"
                >
                  <Trash2 :size="16" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- No Documents -->
    <div v-else class="alert alert-info">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <span>No documents found. Upload some documents to get started!</span>
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ error }}</span>
    </div>

    <!-- Delete Confirmation Modal -->
    <dialog ref="deleteModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Confirm Delete</h3>
        <p v-if="documentToDelete" class="py-4">
          Are you sure you want to delete <strong>{{ documentToDelete.filename }}</strong>?
          This will remove the document and all associated metadata from the index.
        </p>
        <p v-else class="py-4">
          Are you sure you want to delete <strong>{{ selectedDocuments.length }} document(s)</strong>?
          This will remove all selected documents and their associated metadata from the index.
        </p>
        <div v-if="!documentToDelete && selectedDocuments.length > 0" class="max-h-40 overflow-y-auto mb-4">
          <ul class="list-disc list-inside text-sm space-y-1">
            <li v-for="docId in selectedDocuments" :key="docId">
              {{ getDocumentName(docId) }}
            </li>
          </ul>
        </div>
        <div class="modal-action">
          <button class="btn" @click="closeDeleteModal" :disabled="deleting">Cancel</button>
          <button class="btn btn-error" @click="documentToDelete ? deleteDocument() : deleteBulk()" :disabled="deleting">
            <span v-if="deleting" class="loading loading-spinner"></span>
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeDeleteModal">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import axios from 'axios'
import { FileText, Eye, Trash2, RefreshCw, CheckSquare, Square, CloudUpload, X, AlertTriangle, FolderOpen } from 'lucide-vue-next'
import { useCollectionStore } from '../stores/collectionStore'

const emit = defineEmits(['document-deleted'])

const collectionStore = useCollectionStore()

// Upload state
const fileInput = ref(null)
const folderInput = ref(null)
const uploadMode = ref('files')  // 'files' or 'folder'
const selectedFiles = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadSuccess = ref(false)
const uploadError = ref('')
const uploadResult = ref({})

// Supported file extensions
const SUPPORTED_EXTENSIONS = ['.pdf', '.txt', '.docx', '.csv', '.md', '.json']

// Document management state
const documents = ref([])
const loading = ref(false)
const deleting = ref(false)
const error = ref('')
const deleteModal = ref(null)
const documentToDelete = ref(null)
const selectedDocuments = ref([])

// Upload functions
const setUploadMode = (mode) => {
  uploadMode.value = mode
  clearAllFiles()
}

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  selectedFiles.value = files
  uploadSuccess.value = false
  uploadError.value = ''
}

const handleFolderSelect = (event) => {
  const allFiles = Array.from(event.target.files)

  // Filter to only supported file types
  const supportedFiles = allFiles.filter(file => {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    return SUPPORTED_EXTENSIONS.includes(ext)
  })

  selectedFiles.value = supportedFiles
  uploadSuccess.value = false
  uploadError.value = ''

  // Show info if some files were filtered out
  const skippedCount = allFiles.length - supportedFiles.length
  if (skippedCount > 0) {
    uploadError.value = `${skippedCount} unsupported file(s) skipped. Only PDF, TXT, DOCX, CSV, MD, and JSON files are supported.`
  }
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0 && fileInput.value) {
    fileInput.value.value = ''
  }
}

const clearAllFiles = () => {
  selectedFiles.value = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  if (folderInput.value) {
    folderInput.value.value = ''
  }
  uploadSuccess.value = false
  uploadError.value = ''
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const formatTotalSize = () => {
  const total = selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
  return formatFileSize(total)
}

const hasLargeFiles = () => {
  const ONE_MB = 1024 * 1024
  return selectedFiles.value.some(file => file.size > ONE_MB)
}

const estimateProcessingTime = () => {
  const totalBytes = selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
  const totalMB = totalBytes / (1024 * 1024)
  const estimatedSeconds = Math.ceil(totalMB * 30)

  if (estimatedSeconds < 60) {
    return `~${estimatedSeconds} seconds`
  } else {
    const minutes = Math.ceil(estimatedSeconds / 60)
    return `~${minutes} minute${minutes > 1 ? 's' : ''}`
  }
}

const beforeUnloadHandler = (e) => {
  if (uploading.value) {
    e.preventDefault()
    e.returnValue = 'Upload in progress. Are you sure you want to leave?'
    return e.returnValue
  }
}

const upload = async () => {
  if (selectedFiles.value.length === 0) return

  uploading.value = true
  uploadProgress.value = 0
  uploadSuccess.value = false
  uploadError.value = ''

  const formData = new FormData()
  selectedFiles.value.forEach(file => {
    formData.append('files', file)
  })

  try {
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 500)

    const collectionId = collectionStore.currentCollectionId
    const response = await axios.post(`/documents/upload?collection_id=${collectionId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    clearInterval(progressInterval)
    uploadProgress.value = 100

    uploadResult.value = response.data
    uploadSuccess.value = true
    selectedFiles.value = []
    if (fileInput.value) {
      fileInput.value.value = ''
    }
    if (folderInput.value) {
      folderInput.value.value = ''
    }

    // Reload documents list
    await loadDocuments()
    emit('document-deleted')  // Reuse this event to trigger stats update

    setTimeout(() => {
      uploadSuccess.value = false
    }, 5000)
  } catch (err) {
    console.error('Upload error:', err)
    uploadError.value = err.response?.data?.detail || err.message || 'Upload failed. Please try again.'
  } finally {
    uploading.value = false
  }
}

// Document management functions
const isAllSelected = computed(() => {
  return documents.value.length > 0 && selectedDocuments.value.length === documents.value.length
})

const isSelected = (docId) => {
  return selectedDocuments.value.includes(docId)
}

const toggleSelect = (docId) => {
  const index = selectedDocuments.value.indexOf(docId)
  if (index > -1) {
    selectedDocuments.value.splice(index, 1)
  } else {
    selectedDocuments.value.push(docId)
  }
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedDocuments.value = []
  } else {
    selectedDocuments.value = documents.value.map(doc => doc.document_id)
  }
}

const getDocumentName = (docId) => {
  const doc = documents.value.find(d => d.document_id === docId)
  return doc ? doc.filename : 'Unknown'
}

const loadDocuments = async () => {
  loading.value = true
  error.value = ''

  try {
    const collectionId = collectionStore.currentCollectionId
    const response = await axios.get(`/documents?collection_id=${collectionId}`)
    documents.value = response.data.documents || []
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load documents'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleString()
}

const confirmDelete = (doc) => {
  documentToDelete.value = doc
  deleteModal.value?.showModal()
}

const closeDeleteModal = () => {
  if (!deleting.value) {
    deleteModal.value?.close()
    documentToDelete.value = null
  }
}

const deleteDocument = async () => {
  if (!documentToDelete.value) return

  deleting.value = true
  error.value = ''

  try {
    const collectionId = collectionStore.currentCollectionId
    await axios.delete(`/documents/${documentToDelete.value.document_id}?collection_id=${collectionId}`)

    // Remove from local list
    documents.value = documents.value.filter(
      doc => doc.document_id !== documentToDelete.value.document_id
    )

    // Remove from selection if it was selected
    const index = selectedDocuments.value.indexOf(documentToDelete.value.document_id)
    if (index > -1) {
      selectedDocuments.value.splice(index, 1)
    }

    emit('document-deleted')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to delete document'
  } finally {
    deleting.value = false
    closeDeleteModal()
  }
}

const confirmBulkDelete = () => {
  documentToDelete.value = null
  deleteModal.value?.showModal()
}

const deleteBulk = async () => {
  if (selectedDocuments.value.length === 0) return

  deleting.value = true
  error.value = ''

  try {
    // Delete all selected documents
    const collectionId = collectionStore.currentCollectionId
    for (const docId of selectedDocuments.value) {
      await axios.delete(`/documents/${docId}?collection_id=${collectionId}`)
    }

    // Remove deleted documents from local list
    documents.value = documents.value.filter(
      doc => !selectedDocuments.value.includes(doc.document_id)
    )

    // Clear selection
    selectedDocuments.value = []

    emit('document-deleted')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to delete documents'
  } finally {
    deleting.value = false
    closeDeleteModal()
  }
}

// Watch for collection changes
watch(() => collectionStore.currentCollectionId, () => {
  loadDocuments()
  selectedDocuments.value = []  // Clear selection when switching collections
})

onMounted(() => {
  loadDocuments()
  window.addEventListener('beforeunload', beforeUnloadHandler)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnloadHandler)
})
</script>
