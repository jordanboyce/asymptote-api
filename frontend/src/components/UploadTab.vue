<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold">Upload Documents</h2>

    <!-- Upload Form -->
    <div class="form-control w-full">
      <label class="label">
        <span class="label-text">Select documents to upload</span>
      </label>
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

    <!-- Selected Files -->
    <div v-if="selectedFiles.length > 0" class="space-y-4">
      <!-- Sticky Action Bar -->
      <div class="sticky top-20 z-10 bg-base-100 p-4 rounded-lg shadow-lg border border-base-300">
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <span class="font-semibold">{{ selectedFiles.length }} file{{ selectedFiles.length !== 1 ? 's' : '' }} selected</span>
            <span class="text-sm text-base-content/70">{{ formatTotalSize() }}</span>
          </div>
          <div class="flex gap-2">
            <button
              class="btn btn-ghost btn-sm"
              @click="clearAll"
              :disabled="uploading"
            >
              Clear All
            </button>
            <button
              class="btn btn-primary btn-sm"
              @click="upload"
              :disabled="uploading || selectedFiles.length === 0"
            >
              <span v-if="uploading" class="loading loading-spinner loading-sm"></span>
              <CloudUpload v-else :size="16" />
              {{ uploading ? 'Uploading...' : 'Upload Now' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Large File Warning -->
      <div v-if="hasLargeFiles()" class="alert alert-warning">
        <AlertTriangle :size="24" class="stroke-current shrink-0" />
        <span class="text-sm">
          <strong>Large file(s) detected.</strong> Large files may take several minutes to process.
          Estimated time: {{ estimateProcessingTime() }}
        </span>
      </div>

      <!-- File List with Max Height -->
      <div class="overflow-x-auto max-h-96 overflow-y-auto border rounded-lg">
        <table class="table table-zebra table-pin-rows">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(file, index) in selectedFiles" :key="index">
              <td class="max-w-xs truncate" :title="file.name">{{ file.name }}</td>
              <td>{{ formatFileSize(file.size) }}</td>
              <td>
                <button
                  class="btn btn-ghost btn-xs text-error"
                  @click="removeFile(index)"
                  :disabled="uploading"
                  title="Remove file"
                >
                  <X :size="16" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Processing Info Alert -->
    <div v-if="uploading" class="alert alert-info">
      <Info :size="24" class="stroke-current shrink-0" />
      <div>
        <h3 class="font-bold">Processing Your Files</h3>
        <div class="text-xs">
          Please keep this page open. Large files may take 1-5 minutes to process.
          <br>The system is extracting text, chunking content, and generating embeddings.
        </div>
      </div>
    </div>

    <!-- Progress -->
    <div v-if="uploading" class="space-y-2">
      <progress class="progress progress-primary w-full" :value="uploadProgress" max="100"></progress>
      <p class="text-sm text-center">{{ uploadProgress }}% - Processing files...</p>
    </div>

    <!-- Success Alert -->
    <div v-if="success" class="alert alert-success">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <h3 class="font-bold">Upload successful!</h3>
        <div class="text-xs">
          Processed {{ uploadResult.documents_processed }} document(s),
          {{ uploadResult.total_pages }} pages,
          {{ uploadResult.total_chunks }} chunks
        </div>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ error }}</span>
    </div>

    <!-- Instructions -->
    <div class="alert alert-info">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <div>
        <h3 class="font-bold">Upload Tips</h3>
        <div class="text-xs">
          <ul class="list-disc list-inside mt-1">
            <li>Supported formats: PDF, TXT, DOCX, CSV, MD, JSON</li>
            <li>Files are processed and indexed automatically</li>
            <li>Larger files may take longer to process</li>
            <li>Duplicate files (by content) are automatically detected</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import { Upload, X, CloudUpload, AlertTriangle, Info } from 'lucide-vue-next'

const emit = defineEmits(['upload-complete'])

const fileInput = ref(null)
const selectedFiles = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)
const success = ref(false)
const error = ref('')
const uploadResult = ref({})

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  selectedFiles.value = files
  success.value = false
  error.value = ''
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0 && fileInput.value) {
    fileInput.value.value = ''
  }
}

const clearAll = () => {
  selectedFiles.value = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  success.value = false
  error.value = ''
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

  // Rough estimate: ~30 seconds per MB (varies with file complexity)
  const estimatedSeconds = Math.ceil(totalMB * 30)

  if (estimatedSeconds < 60) {
    return `~${estimatedSeconds} seconds`
  } else {
    const minutes = Math.ceil(estimatedSeconds / 60)
    return `~${minutes} minute${minutes > 1 ? 's' : ''}`
  }
}

// Warn user before leaving page during upload
const beforeUnloadHandler = (e) => {
  if (uploading.value) {
    e.preventDefault()
    e.returnValue = 'Upload in progress. Are you sure you want to leave? Your upload will be cancelled.'
    return e.returnValue
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnloadHandler)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnloadHandler)
})

const upload = async () => {
  if (selectedFiles.value.length === 0) return

  uploading.value = true
  uploadProgress.value = 0
  success.value = false
  error.value = ''

  const formData = new FormData()
  selectedFiles.value.forEach(file => {
    formData.append('files', file)
  })

  try {
    // Simulate progress
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 500)

    const response = await axios.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    clearInterval(progressInterval)
    uploadProgress.value = 100

    uploadResult.value = response.data
    success.value = true
    selectedFiles.value = []
    if (fileInput.value) {
      fileInput.value.value = ''
    }

    emit('upload-complete')

    // Clear success message after 5 seconds
    setTimeout(() => {
      success.value = false
    }, 5000)
  } catch (err) {
    console.error('Upload error:', err)
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else if (err.message) {
      error.value = `Upload failed: ${err.message}`
    } else {
      error.value = 'Upload failed. Please try again.'
    }
  } finally {
    uploading.value = false
  }
}
</script>
