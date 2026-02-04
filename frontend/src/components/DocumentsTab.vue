<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <div class="flex items-center gap-4">
        <h2 class="text-2xl font-bold">Manage Documents</h2>
        <div v-if="selectedDocuments.length > 0" class="badge badge-primary badge-lg">
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
                  :href="`/documents/${doc.document_id}/pdf`"
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
      <span>No documents found. Upload some PDFs to get started!</span>
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
          This will remove the PDF file and all associated metadata from the index.
        </p>
        <p v-else class="py-4">
          Are you sure you want to delete <strong>{{ selectedDocuments.length }} document(s)</strong>?
          This will remove all PDF files and their associated metadata from the index.
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
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { FileText, Eye, Trash2, RefreshCw, CheckSquare, Square } from 'lucide-vue-next'

const emit = defineEmits(['document-deleted'])

const documents = ref([])
const loading = ref(false)
const deleting = ref(false)
const error = ref('')
const deleteModal = ref(null)
const documentToDelete = ref(null)
const selectedDocuments = ref([])

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
    const response = await axios.get('/documents')
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
    await axios.delete(`/documents/${documentToDelete.value.document_id}`)

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
    for (const docId of selectedDocuments.value) {
      await axios.delete(`/documents/${docId}`)
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

onMounted(() => {
  loadDocuments()
})
</script>
