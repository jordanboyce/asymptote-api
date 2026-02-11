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
          <div class="hidden md:flex items-center gap-6">
            <div class="text-center">
              <div class="text-2xl font-bold">{{ stats.documents }}</div>
              <div class="text-xs text-primary-content/70">Documents</div>
            </div>
            <div class="divider divider-horizontal mx-0"></div>
            <div class="text-center">
              <div class="text-2xl font-bold">{{ stats.pages }}</div>
              <div class="text-xs text-primary-content/70">Pages</div>
            </div>
            <div class="divider divider-horizontal mx-0"></div>
            <div class="text-center">
              <div class="text-2xl font-bold">{{ stats.chunks }}</div>
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
        <div role="tablist" class="tabs tabs-boxed bg-transparent gap-2 py-3">
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
        </div>
      </div>
    </div>

    <!-- Tab Content -->
    <div class="container mx-auto px-4 mt-6">
      <div class="bg-base-100 rounded-lg shadow-xl p-6">
        <SearchTab v-if="activeTab === 'search'" @stats-updated="loadStats" @switch-tab="switchTab" />
        <DocumentsTab v-if="activeTab === 'documents'" @document-deleted="handleDocumentDeleted" />
        <SettingsTab v-if="activeTab === 'settings'" @data-cleared="handleDataCleared" />
      </div>
    </div>

    <!-- Footer -->
    <footer class="footer footer-center p-10 bg-base-200 text-base-content mt-10">
      <aside>
        <p class="font-bold">Asymptote API Search</p>
        <p>Always approaching understanding, never quite reaching it.</p>
      </aside>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Search, FileText, Settings, Sun, Moon } from 'lucide-vue-next'
import SearchTab from './components/SearchTab.vue'
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
