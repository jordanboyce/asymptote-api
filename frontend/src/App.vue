<template>
  <div class="min-h-screen bg-base-200">
    <!-- Header -->
    <header class="bg-primary text-primary-content shadow-lg sticky top-0 z-50">
      <div class="container mx-auto px-4">
        <div class="flex items-center justify-between py-4">
          <!-- Logo and Title -->
          <div class="flex items-center gap-3">
            <img src="/icon_white.svg" alt="Asymptote" class="h-10 w-10">
            <div>
              <h1 class="text-2xl font-bold">Asymptote</h1>
              <p class="text-xs text-primary-content/80">Semantic Document Search</p>
            </div>
          </div>

          <!-- Stats -->
          <div class="hidden lg:flex items-center gap-4">
            <div class="text-center">
              <div class="text-xl font-bold">{{ stats.documents }}</div>
              <div class="text-xs text-primary-content/70">Documents</div>
            </div>
            <div class="divider divider-horizontal mx-0"></div>
            <div class="text-center">
              <div class="text-xl font-bold">{{ stats.pages }}</div>
              <div class="text-xs text-primary-content/70">Pages</div>
            </div>
            <div class="divider divider-horizontal mx-0"></div>
            <div class="text-center">
              <div class="text-xl font-bold">{{ stats.chunks }}</div>
              <div class="text-xs text-primary-content/70">Chunks</div>
            </div>
          </div>

          <!-- Theme Toggle -->
          <label class="swap swap-rotate btn btn-ghost btn-circle">
            <input type="checkbox" @change="toggleTheme" :checked="isDark" />
            <Sun :size="24" class="swap-on" />
            <Moon :size="24" class="swap-off" />
          </label>
        </div>
      </div>
    </header>

    <!-- Tabs Navigation (Sticky) -->
    <div class="sticky top-[88px] z-40 bg-base-100 border-b border-base-300 shadow-md">
      <div class="container mx-auto px-4">
        <div role="tablist" class="tabs tabs-boxed bg-transparent gap-2 py-3 flex justify-between items-center">
          <a
            role="tab"
            class="tab tab-lg font-semibold transition-all"
            :class="{
              'tab-active bg-primary text-primary-content': activeTab === 'search',
              'hover:bg-base-200': activeTab !== 'search'
            }"
            @click="activeTab = 'search'"
          >
            <Search :size="20" class="mr-2" />
            Search
          </a>
          <a
            role="tab"
            class="tab tab-lg font-semibold transition-all"
            :class="{
              'tab-active bg-primary text-primary-content': activeTab === 'documents',
              'hover:bg-base-200': activeTab !== 'documents'
            }"
            @click="activeTab = 'documents'"
          >
            <FileText :size="20" class="mr-2" />
            Documents
          </a>
          <a
            role="tab"
            class="tab tab-lg font-semibold transition-all"
            :class="{
              'tab-active bg-primary text-primary-content': activeTab === 'settings',
              'hover:bg-base-200': activeTab !== 'settings'
            }"
            @click="activeTab = 'settings'"
          >
            <Settings :size="20" class="mr-2" />
            Settings
          </a>

          <!-- Spacer -->
          <div class="flex-1"></div>

          <!-- Collection Selector -->
          <div class="dropdown dropdown-end">
            <label tabindex="0" class="btn btn-ghost gap-2 normal-case">
              <div
                class="w-3 h-3 rounded-full"
                :style="{ backgroundColor: collectionStore.currentCollection?.color || '#3b82f6' }"
              ></div>
              <span class="max-w-32 truncate">{{ collectionStore.currentCollection?.name || 'Default' }}</span>
              <ChevronDown :size="16" />
            </label>
            <ul tabindex="0" class="dropdown-content z-[100] menu p-2 shadow-lg bg-base-100 rounded-box w-64 text-base-content">
              <li class="menu-title">
                <span>Collections</span>
              </li>
              <li v-for="collection in collectionStore.sortedCollections" :key="collection.id">
                <a
                  @click="selectCollection(collection.id)"
                  :class="{ 'active': collection.id === collectionStore.currentCollectionId }"
                  class="group"
                >
                  <div
                    class="w-3 h-3 rounded-full flex-shrink-0"
                    :style="{ backgroundColor: collection.color }"
                  ></div>
                  <span class="flex-1 truncate">{{ collection.name }}</span>
                  <span class="badge badge-sm badge-ghost">{{ collection.document_count || 0 }}</span>
                  <button
                    @click.stop="openEditCollectionModal(collection)"
                    class="btn btn-ghost btn-xs opacity-0 group-hover:opacity-100 transition-opacity p-1"
                    title="Edit collection"
                  >
                    <Pencil :size="14" />
                  </button>
                </a>
              </li>
              <div class="divider my-1"></div>
              <li>
                <a @click="openCreateCollectionModal" class="text-primary">
                  <Plus :size="16" />
                  New Collection
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab Content -->
    <div class="container mx-auto px-4 mt-6">
      <div class="bg-base-100 rounded-lg shadow-xl p-6">
        <SearchTab v-if="activeTab === 'search'" @stats-updated="loadStats" @switch-tab="switchTab" />
        <DocumentsTab v-if="activeTab === 'documents'" @document-deleted="handleDocumentDeleted" />
        <SettingsTab v-if="activeTab === 'settings'" @data-cleared="handleDataCleared" @stats-updated="loadStats" />
      </div>
    </div>

    <!-- Footer -->
    <footer class="footer footer-center p-10 bg-base-200 text-base-content mt-10">
      <aside>
        <p class="font-bold">Asymptote API Search</p>
        <p>Always approaching understanding, never quite reaching it.</p>
      </aside>
    </footer>

    <!-- Create Collection Modal -->
    <dialog class="modal" :class="{ 'modal-open': showCollectionModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Create New Collection</h3>

        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">Collection Name</span>
          </label>
          <input
            v-model="newCollectionName"
            type="text"
            placeholder="e.g., Research Papers"
            class="input input-bordered w-full"
            @keyup.enter="createCollection"
          />
        </div>

        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">Description (optional)</span>
          </label>
          <textarea
            v-model="newCollectionDescription"
            class="textarea textarea-bordered"
            placeholder="What kind of documents will this collection contain?"
          ></textarea>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">Color</span>
          </label>
          <div class="flex items-center gap-3">
            <input
              v-model="newCollectionColor"
              type="color"
              class="w-12 h-12 rounded cursor-pointer border-2 border-base-300"
            />
            <div class="flex gap-2">
              <button
                v-for="color in ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']"
                :key="color"
                class="w-8 h-8 rounded cursor-pointer border-2"
                :class="newCollectionColor === color ? 'border-base-content' : 'border-transparent'"
                :style="{ backgroundColor: color }"
                @click="newCollectionColor = color"
              ></button>
            </div>
          </div>
        </div>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="showCollectionModal = false" :disabled="creatingCollection">
            Cancel
          </button>
          <button
            class="btn btn-primary"
            @click="createCollection"
            :disabled="!newCollectionName.trim() || creatingCollection"
          >
            <span v-if="creatingCollection" class="loading loading-spinner loading-sm"></span>
            Create Collection
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showCollectionModal = false">close</button>
      </form>
    </dialog>

    <!-- Edit Collection Modal -->
    <dialog class="modal" :class="{ 'modal-open': showEditModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Edit Collection</h3>

        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">Collection Name</span>
          </label>
          <input
            v-model="editCollectionName"
            type="text"
            placeholder="e.g., Research Papers"
            class="input input-bordered w-full"
            :disabled="editingCollectionId === 'default'"
          />
          <label v-if="editingCollectionId === 'default'" class="label">
            <span class="label-text-alt text-warning">Default collection name cannot be changed</span>
          </label>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">Description</span>
          </label>
          <textarea
            v-model="editCollectionDescription"
            class="textarea textarea-bordered"
            placeholder="What kind of documents does this collection contain?"
          ></textarea>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">Color</span>
          </label>
          <div class="flex items-center gap-3">
            <input
              v-model="editCollectionColor"
              type="color"
              class="w-12 h-12 rounded cursor-pointer border-2 border-base-300"
            />
            <div class="flex gap-2">
              <button
                v-for="color in ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']"
                :key="color"
                class="w-8 h-8 rounded cursor-pointer border-2"
                :class="editCollectionColor === color ? 'border-base-content' : 'border-transparent'"
                :style="{ backgroundColor: color }"
                @click="editCollectionColor = color"
              ></button>
            </div>
          </div>
        </div>

        <div class="modal-action justify-between">
          <button
            v-if="editingCollectionId !== 'default'"
            class="btn btn-error btn-outline"
            @click="confirmDeleteCollection"
            :disabled="updatingCollection"
          >
            <Trash2 :size="16" />
            Delete
          </button>
          <div v-else></div>
          <div class="flex gap-2">
            <button class="btn btn-ghost" @click="showEditModal = false" :disabled="updatingCollection">
              Cancel
            </button>
            <button
              class="btn btn-primary"
              @click="updateCollection"
              :disabled="!editCollectionName.trim() || updatingCollection"
            >
              <span v-if="updatingCollection" class="loading loading-spinner loading-sm"></span>
              Save Changes
            </button>
          </div>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showEditModal = false">close</button>
      </form>
    </dialog>

    <!-- Delete Collection Confirmation Modal -->
    <dialog class="modal" :class="{ 'modal-open': showDeleteConfirmModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg text-error mb-4">Delete Collection</h3>
        <p class="mb-2">Are you sure you want to delete <strong>{{ editCollectionName }}</strong>?</p>
        <p class="text-warning mb-4">This will permanently delete all documents and indexes in this collection. This action cannot be undone.</p>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="showDeleteConfirmModal = false" :disabled="deletingCollection">
            Cancel
          </button>
          <button
            class="btn btn-error"
            @click="deleteCollection"
            :disabled="deletingCollection"
          >
            <span v-if="deletingCollection" class="loading loading-spinner loading-sm"></span>
            Delete Collection
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showDeleteConfirmModal = false">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import { Search, FileText, Settings, Sun, Moon, FolderOpen, Plus, ChevronDown, Pencil, Trash2 } from 'lucide-vue-next'
import SearchTab from './components/SearchTab.vue'
import DocumentsTab from './components/DocumentsTab.vue'
import SettingsTab from './components/SettingsTab.vue'
import { useCollectionStore } from './stores/collectionStore'

const collectionStore = useCollectionStore()

const activeTab = ref('search')
const isDark = ref(false)
const stats = ref({
  documents: 0,
  pages: 0,
  chunks: 0
})

// Create collection modal state
const showCollectionModal = ref(false)
const newCollectionName = ref('')
const newCollectionDescription = ref('')
const newCollectionColor = ref('#3b82f6')
const creatingCollection = ref(false)

// Edit collection modal state
const showEditModal = ref(false)
const editingCollectionId = ref('')
const editCollectionName = ref('')
const editCollectionDescription = ref('')
const editCollectionColor = ref('#3b82f6')
const updatingCollection = ref(false)

// Delete confirmation modal state
const showDeleteConfirmModal = ref(false)
const deletingCollection = ref(false)

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

const loadStats = async () => {
  try {
    const collectionId = collectionStore.currentCollectionId
    const [docsResponse, healthResponse] = await Promise.all([
      axios.get(`/documents?collection_id=${collectionId}`),
      axios.get(`/health?collection_id=${collectionId}`)
    ])

    stats.value.documents = docsResponse.data.documents?.length || 0
    stats.value.pages = docsResponse.data.documents?.reduce((sum, doc) => sum + (doc.total_pages || 0), 0) || 0
    stats.value.chunks = healthResponse.data.indexed_chunks || 0
  } catch (error) {
    console.error('Error loading stats:', error)
  }
}

const handleDocumentDeleted = () => {
  loadStats()
}

const handleDataCleared = () => {
  loadStats()
}

const switchTab = (tabName) => {
  activeTab.value = tabName
}

const selectCollection = (collectionId) => {
  collectionStore.setCurrentCollection(collectionId)
}

const openCreateCollectionModal = () => {
  newCollectionName.value = ''
  newCollectionDescription.value = ''
  newCollectionColor.value = '#3b82f6'
  showCollectionModal.value = true
}

const createCollection = async () => {
  if (!newCollectionName.value.trim()) return

  creatingCollection.value = true
  try {
    const collection = await collectionStore.createCollection({
      name: newCollectionName.value.trim(),
      description: newCollectionDescription.value.trim(),
      color: newCollectionColor.value
    })
    collectionStore.setCurrentCollection(collection.id)
    showCollectionModal.value = false
  } catch (err) {
    console.error('Failed to create collection:', err)
  } finally {
    creatingCollection.value = false
  }
}

const openEditCollectionModal = (collection) => {
  editingCollectionId.value = collection.id
  editCollectionName.value = collection.name
  editCollectionDescription.value = collection.description || ''
  editCollectionColor.value = collection.color || '#3b82f6'
  showEditModal.value = true
}

const updateCollection = async () => {
  if (!editCollectionName.value.trim()) return

  updatingCollection.value = true
  try {
    await collectionStore.updateCollection(editingCollectionId.value, {
      name: editingCollectionId.value === 'default' ? undefined : editCollectionName.value.trim(),
      description: editCollectionDescription.value.trim(),
      color: editCollectionColor.value
    })
    showEditModal.value = false
  } catch (err) {
    console.error('Failed to update collection:', err)
  } finally {
    updatingCollection.value = false
  }
}

const confirmDeleteCollection = () => {
  showDeleteConfirmModal.value = true
}

const deleteCollection = async () => {
  deletingCollection.value = true
  try {
    await collectionStore.deleteCollection(editingCollectionId.value)
    showDeleteConfirmModal.value = false
    showEditModal.value = false
    // Switch to default collection if we deleted the current one
    if (collectionStore.currentCollectionId === editingCollectionId.value) {
      collectionStore.setCurrentCollection('default')
    }
  } catch (err) {
    console.error('Failed to delete collection:', err)
  } finally {
    deletingCollection.value = false
  }
}

// Watch for collection changes to reload stats
watch(() => collectionStore.currentCollectionId, () => {
  loadStats()
})

onMounted(async () => {
  // Load collections first
  await collectionStore.loadCollections()

  // Then load stats for current collection
  loadStats()

  // Initialize theme from localStorage
  const savedTheme = localStorage.getItem('theme') || 'light'
  isDark.value = savedTheme === 'dark'
  document.documentElement.setAttribute('data-theme', savedTheme)
})
</script>
