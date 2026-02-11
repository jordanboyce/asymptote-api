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

          <!-- Theme Toggle -->
          <label class="swap swap-rotate btn btn-ghost btn-circle">
            <input type="checkbox" @change="toggleTheme" :checked="isDark" />
            <Sun :size="24" class="swap-on" />
            <Moon :size="24" class="swap-off" />
          </label>
        </div>
      </div>
    </header>

    <!-- Stats -->
    <div class="container mx-auto px-4 py-6">
      <div class="stats shadow w-full bg-base-100">
        <div class="stat">
          <div class="stat-title">Total Documents</div>
          <div class="stat-value text-primary">{{ stats.documents }}</div>
        </div>
        <div class="stat">
          <div class="stat-title">Total Pages</div>
          <div class="stat-value text-secondary">{{ stats.pages }}</div>
        </div>
        <div class="stat">
          <div class="stat-title">Indexed Chunks</div>
          <div class="stat-value">{{ stats.chunks }}</div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="container mx-auto px-4">
      <div role="tablist" class="tabs tabs-bordered mb-6">
        <a
          role="tab"
          class="tab"
          :class="{ 'tab-active': activeTab === 'search' }"
          @click="activeTab = 'search'"
        >
          <Search :size="20" class="mr-2" />
          Search
        </a>
        <a
          role="tab"
          class="tab"
          :class="{ 'tab-active': activeTab === 'upload' }"
          @click="activeTab = 'upload'"
        >
          <Upload :size="20" class="mr-2" />
          Upload
        </a>
        <a
          role="tab"
          class="tab"
          :class="{ 'tab-active': activeTab === 'documents' }"
          @click="activeTab = 'documents'"
        >
          <FileText :size="20" class="mr-2" />
          Documents
        </a>
        <a
          role="tab"
          class="tab"
          :class="{ 'tab-active': activeTab === 'settings' }"
          @click="activeTab = 'settings'"
        >
          <Settings :size="20" class="mr-2" />
          Settings
        </a>
      </div>

      <!-- Tab Content -->
      <div class="bg-base-100 rounded-lg shadow-xl p-6">
        <SearchTab v-if="activeTab === 'search'" @stats-updated="loadStats" @switch-tab="switchTab" />
        <UploadTab v-if="activeTab === 'upload'" @upload-complete="handleUploadComplete" />
        <DocumentsTab v-if="activeTab === 'documents'" @document-deleted="handleDocumentDeleted" />
        <SettingsTab v-if="activeTab === 'settings'" @data-cleared="handleDataCleared" />
      </div>
    </div>

    <!-- Footer -->
    <footer class="footer footer-center p-10 bg-base-200 text-base-content mt-10">
      <aside>
        <p class="font-bold">Asymptote API</p>
        <p>Always approaching understanding, never quite reaching it.</p>
      </aside>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Search, Upload, FileText, Settings, Sun, Moon } from 'lucide-vue-next'
import SearchTab from './components/SearchTab.vue'
import UploadTab from './components/UploadTab.vue'
import DocumentsTab from './components/DocumentsTab.vue'
import SettingsTab from './components/SettingsTab.vue'

const activeTab = ref('search')
const isDark = ref(false)
const stats = ref({
  documents: 0,
  pages: 0,
  chunks: 0
})

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

const loadStats = async () => {
  try {
    const [docsResponse, healthResponse] = await Promise.all([
      axios.get('/documents'),
      axios.get('/health')
    ])

    stats.value.documents = docsResponse.data.documents?.length || 0
    stats.value.pages = docsResponse.data.documents?.reduce((sum, doc) => sum + (doc.total_pages || 0), 0) || 0
    stats.value.chunks = healthResponse.data.indexed_chunks || 0
  } catch (error) {
    console.error('Error loading stats:', error)
  }
}

const handleUploadComplete = () => {
  loadStats()
  activeTab.value = 'documents'
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

onMounted(() => {
  loadStats()
  // Initialize theme from localStorage
  const savedTheme = localStorage.getItem('theme') || 'light'
  isDark.value = savedTheme === 'dark'
  document.documentElement.setAttribute('data-theme', savedTheme)
})
</script>
