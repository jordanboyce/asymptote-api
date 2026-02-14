<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Search Documents</h2>
      <div class="flex gap-2">
        <button
          v-if="searchStore.searched"
          class="btn btn-sm btn-primary gap-1"
          @click="startNewSearch"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          New
        </button>
        <button
          v-if="cacheStats.count > 0"
          class="btn btn-sm btn-ghost gap-2"
          @click="showHistoryModal = true"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          History ({{ cacheStats.count }})
        </button>
      </div>
    </div>

    <!-- Search Form -->
    <div class="form-control w-full">
      <label class="label">
        <span class="label-text">Enter your search query</span>
      </label>
      <div class="join w-full">
        <input
          v-model="searchStore.query"
          type="text"
          placeholder="e.g., machine learning algorithms"
          class="input input-bordered join-item flex-1"
          @keyup.enter="search"
        />
        <button
          class="btn btn-primary join-item"
          @click="search"
          :disabled="loading || !searchStore.query.trim()"
        >
          <svg v-if="!loading" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <span v-if="loading" class="loading loading-spinner"></span>
          {{ loading ? (useAI && aiActive ? 'AI Processing...' : 'Searching...') : 'Search' }}
        </button>
      </div>
    </div>

    <!-- Number of Results -->
    <div class="form-control w-full max-w-xs">
      <label class="label">
        <span class="label-text">Max Number of results</span>
      </label>
      <input
        v-model.number="searchStore.topK"
        type="number"
        min="1"
        max="50"
        class="input input-bordered w-full max-w-xs"
      />
    </div>

    <!-- AI Controls - Collapsible -->
    <div v-if="hasAnyAvailableProvider" class="collapse collapse-arrow bg-base-200 border border-base-300 rounded-box">
      <input type="checkbox" v-model="aiSectionExpanded" />
      <div class="collapse-title py-3 min-h-0">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <h3 class="font-semibold text-sm">AI Enhancement</h3>
            <span v-if="aiActive" class="badge badge-xs badge-primary">Active</span>
            <span v-if="checkingProviders" class="loading loading-spinner loading-xs"></span>
          </div>
          <div class="flex items-center gap-2" @click.stop>
            <span v-if="aiActive" class="text-xs text-base-content/60">{{ activeFeaturesList }}</span>
            <button
              class="btn btn-xs btn-ghost"
              @click.stop="$emit('switch-tab', 'settings')"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      <div class="collapse-content">
        <!-- Provider Toggles -->
        <div class="space-y-2 pt-2">
          <!-- Anthropic -->
          <label v-if="anthropicAvailable" class="label cursor-pointer justify-start gap-3 py-2 hover:bg-base-300 rounded-lg px-2">
            <input
              type="checkbox"
              class="toggle toggle-sm toggle-primary"
              :checked="selectedProviders.includes('anthropic')"
              @change="toggleProvider('anthropic')"
            />
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="label-text font-medium">Anthropic Claude</span>
                <span class="badge badge-xs badge-primary">Cloud</span>
              </div>
              <p class="text-xs text-base-content/60">High quality - costs API tokens</p>
            </div>
          </label>

          <!-- OpenAI -->
          <label v-if="openaiAvailable" class="label cursor-pointer justify-start gap-3 py-2 hover:bg-base-300 rounded-lg px-2">
            <input
              type="checkbox"
              class="toggle toggle-sm toggle-success"
              :checked="selectedProviders.includes('openai')"
              @change="toggleProvider('openai')"
            />
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="label-text font-medium">OpenAI GPT</span>
                <span class="badge badge-xs badge-success">Cloud</span>
              </div>
              <p class="text-xs text-base-content/60">Fast responses - costs API tokens</p>
            </div>
          </label>

          <!-- Ollama -->
          <label v-if="ollamaAvailable" class="label cursor-pointer justify-start gap-3 py-2 hover:bg-base-300 rounded-lg px-2">
            <input
              type="checkbox"
              class="toggle toggle-sm toggle-info"
              :checked="selectedProviders.includes('ollama')"
              @change="toggleProvider('ollama')"
            />
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="label-text font-medium">Ollama (Local)</span>
                <span class="badge badge-xs badge-info">Free</span>
              </div>
              <p class="text-xs text-base-content/60">Private & free - slower (1-2 min on CPU)</p>
            </div>
          </label>

          <!-- No providers selected warning -->
          <div v-if="availableProviders.length > 0 && selectedProviders.length === 0" class="alert alert-warning py-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>
            <span class="text-xs">Select at least one provider to enable AI features</span>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Feature Prompt (only show if no providers configured at all) -->
    <div v-if="!aiActive && !hasAnyProvider" class="alert alert-info">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <div class="flex-1">
        <h4 class="font-semibold">Want better search results?</h4>
        <p class="text-sm">Add your AI API key in Settings to enable result reranking and AI-powered answer synthesis. Your key stays in your browser and is never stored on the server.</p>
      </div>
      <button class="btn btn-sm btn-primary" @click="$emit('switch-tab', 'settings')">
        Go to Settings
      </button>
    </div>

    <!-- Cache Prompt Dialog -->
    <div v-if="showCachePrompt && cachedData" class="alert alert-success shadow-lg">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-info shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <div class="flex-1">
        <h4 class="font-semibold">Cached results found!</h4>
        <p class="text-sm">
          This search was performed {{ formatTimeAgo(cachedData.timestamp) }}.
          You can use the cached results instantly (no tokens used) or perform a fresh search.
        </p>
        <p class="text-xs text-base-content/70 mt-1">
          Cached: {{ cachedData.results?.length || 0 }} results
          <span v-if="cachedData.aiResponses && cachedData.aiResponses.length > 0">
            &middot; {{ cachedData.aiResponses.length }} AI response(s)
          </span>
        </p>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-sm btn-ghost" @click="useCachedResults">
          Use Cached
        </button>
        <button class="btn btn-sm btn-primary" @click="performFreshSearch">
          Fresh Search
        </button>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ error }}</span>
    </div>

    <!-- AI Synthesis (Multiple Providers) -->
    <div v-if="searchStore.aiResponses && searchStore.aiResponses.length > 0" class="space-y-4">
      <div v-for="(aiResponse, index) in searchStore.aiResponses" :key="index" class="card bg-primary/5 border border-primary/20">
        <div class="card-body">
          <h3 class="card-title text-base">
            <span
              class="badge badge-sm"
              :class="{
                'badge-success': aiResponse.provider === 'openai',
                'badge-primary': aiResponse.provider === 'anthropic',
                'badge-info': aiResponse.provider === 'ollama'
              }"
            >
              AI
            </span>
            {{ getProviderDisplayName(aiResponse.provider) }} Answer
          </h3>
          <div v-if="aiResponse.synthesis" class="prose prose-sm max-w-none whitespace-pre-wrap">{{ aiResponse.synthesis }}</div>
          <div v-if="aiResponse.aiUsage" class="text-xs text-base-content/40 mt-1">
            {{ aiResponse.aiUsage.features_used.join(', ') }}
            <span v-if="aiResponse.aiUsage.total_input_tokens !== undefined">
              &middot; {{ aiResponse.aiUsage.total_input_tokens + aiResponse.aiUsage.total_output_tokens }} tokens
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Synthesis (Legacy Single Provider) -->
    <div v-else-if="searchStore.synthesis" class="card bg-primary/5 border border-primary/20">
      <div class="card-body">
        <h3 class="card-title text-base">
          <span class="badge badge-primary badge-sm">AI</span>
          Answer
        </h3>
        <div class="prose prose-sm max-w-none whitespace-pre-wrap">{{ searchStore.synthesis }}</div>
        <div v-if="searchStore.aiUsage" class="text-xs text-base-content/40 mt-1">
          {{ searchStore.aiUsage.features_used.join(', ') }}
          &middot; {{ searchStore.aiUsage.total_input_tokens + searchStore.aiUsage.total_output_tokens }} tokens
        </div>
      </div>
    </div>

    <!-- Results -->
    <div v-if="searchStore.results.length > 0" class="space-y-4">
      <div class="flex justify-between items-center">
        <h3 class="text-xl font-semibold">Results ({{ searchStore.results.length }})</h3>
        <p class="text-sm text-base-content/70">Query: "{{ searchStore.lastQuery }}"</p>
      </div>

      <div v-for="(result, index) in searchStore.results" :key="index" class="card bg-base-200 shadow-md">
        <div class="card-body">
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <h4 class="card-title text-lg">
                <svg class="w-5 h-5 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                {{ result.filename }}
              </h4>
              <div class="badge badge-primary badge-sm mt-1">Page {{ result.page_number }}</div>
              <div class="badge badge-ghost badge-sm mt-1 ml-2">
                Similarity: {{ (result.similarity_score * 100).toFixed(1) }}%
              </div>
            </div>
          </div>

          <p class="text-sm mt-2" v-html="highlightText(result.text_snippet, searchStore.query)"></p>

          <div class="card-actions justify-end mt-4">
            <a
              :href="result.page_url"
              target="_blank"
              class="btn btn-sm btn-primary"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
              Open Page {{ result.page_number }}
            </a>
            <a
              :href="result.pdf_url"
              target="_blank"
              class="btn btn-sm btn-ghost"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              Download PDF
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- No Results -->
    <div v-else-if="searchStore.searched && !loading" class="alert alert-info">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <span>No results found. Try a different query or upload more documents.</span>
    </div>

    <!-- Search History Modal -->
    <dialog ref="historyModal" class="modal" :class="{ 'modal-open': showHistoryModal }">
      <div class="modal-box max-w-3xl">
        <h3 class="font-bold text-lg mb-4">Search History</h3>

        <div class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="(entry, index) in historyEntries"
            :key="index"
            class="card bg-base-200 hover:bg-base-300 cursor-pointer transition-colors"
            @click="loadHistoryEntry(entry)"
          >
            <div class="card-body p-4">
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1">
                  <div class="font-semibold text-sm">{{ entry.query }}</div>
                  <div class="text-xs text-base-content/60 mt-1">
                    {{ formatTimeAgo(entry.timestamp) }}
                    &middot; {{ entry.results?.length || 0 }} results
                    &middot; Top-{{ entry.topK }}
                    <span v-if="entry.aiResponses && entry.aiResponses.length > 0">
                      &middot; {{ entry.aiResponses.length }} AI response(s)
                    </span>
                  </div>
                </div>
                <button
                  class="btn btn-ghost btn-xs text-error"
                  @click.stop="deleteHistoryEntry(entry)"
                  title="Delete from history"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div v-if="historyEntries.length === 0" class="text-center text-base-content/60 py-8">
            No search history yet
          </div>
        </div>

        <div class="modal-action">
          <button class="btn btn-sm btn-error" @click="clearAllHistory" :disabled="historyEntries.length === 0">
            Clear All
          </button>
          <button class="btn btn-sm" @click="showHistoryModal = false">Close</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showHistoryModal = false">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'
import { useSearchStore } from '../stores/searchStore'
import { useCollectionStore } from '../stores/collectionStore'

const emit = defineEmits(['stats-updated', 'switch-tab'])

// Use the search store for persistent state
const searchStore = useSearchStore()
const collectionStore = useCollectionStore()

// Local state for loading and error (not persisted)
const loading = ref(false)
const error = ref('')

// Cache prompt state
const showCachePrompt = ref(false)
const cachedData = ref(null)

// History modal state
const showHistoryModal = ref(false)

// AI Section collapsed state
const aiSectionExpanded = ref(localStorage.getItem('asymptote_ai_section_expanded') !== 'false')
watch(aiSectionExpanded, (val) => {
  localStorage.setItem('asymptote_ai_section_expanded', val.toString())
})

// Provider availability state (actual availability, not just localStorage)
const checkingProviders = ref(false)
const ollamaAvailable = ref(false)
const anthropicAvailable = ref(false)
const openaiAvailable = ref(false)

// Provider selection state
const PROVIDER_SELECTION_KEY = 'asymptote_selected_providers'
const selectedProviders = ref([])

// Check which providers have keys/models in localStorage (used for initial check)
const hasAnthropicKey = computed(() => !!localStorage.getItem('ai_api_key_anthropic'))
const hasOpenAIKey = computed(() => !!localStorage.getItem('ai_api_key_openai'))
const hasOllamaModel = computed(() => !!localStorage.getItem('ollama_model'))

// Check if any provider is actually available and operational
const hasAnyAvailableProvider = computed(() => ollamaAvailable.value || anthropicAvailable.value || openaiAvailable.value)
const hasAnyProvider = computed(() => hasAnthropicKey.value || hasOpenAIKey.value || hasOllamaModel.value)
const hasBothProviders = computed(() => hasAnthropicKey.value && hasOpenAIKey.value)

const cloudProvidersCount = computed(() => {
  let count = 0
  if (hasAnthropicKey.value) count++
  if (hasOpenAIKey.value) count++
  return count
})

const cloudProvidersSelected = computed(() => {
  return hasAnthropicKey.value && hasOpenAIKey.value &&
         selectedProviders.value.includes('anthropic') &&
         selectedProviders.value.includes('openai')
})

const availableProviders = computed(() => {
  const providers = []
  if (anthropicAvailable.value) providers.push('anthropic')
  if (openaiAvailable.value) providers.push('openai')
  if (ollamaAvailable.value) providers.push('ollama')
  return providers
})

// Check provider availability on mount
const checkProviderAvailability = async () => {
  checkingProviders.value = true

  try {
    // For cloud providers (Anthropic, OpenAI), trust the localStorage key
    // Validation happens at search time - no need to pre-validate
    anthropicAvailable.value = hasAnthropicKey.value
    openaiAvailable.value = hasOpenAIKey.value

    // For Ollama, actually check if it's running since it's a local service
    if (hasOllamaModel.value) {
      try {
        const response = await axios.get('/api/ollama/status')
        ollamaAvailable.value = response.data.available === true
      } catch (e) {
        ollamaAvailable.value = false
      }
    } else {
      ollamaAvailable.value = false
    }
  } finally {
    checkingProviders.value = false

    // Re-initialize selected providers based on actual availability
    reinitializeProviders()
  }
}

const reinitializeProviders = () => {
  // Filter to only include providers that are actually available
  const validProviders = selectedProviders.value.filter(p =>
    (p === 'anthropic' && anthropicAvailable.value) ||
    (p === 'openai' && openaiAvailable.value) ||
    (p === 'ollama' && ollamaAvailable.value)
  )

  if (validProviders.length > 0) {
    selectedProviders.value = validProviders
  } else {
    // Default: select all available providers
    const providers = []
    if (anthropicAvailable.value) providers.push('anthropic')
    if (openaiAvailable.value) providers.push('openai')
    if (ollamaAvailable.value) providers.push('ollama')
    selectedProviders.value = providers
  }

  // Save selection
  if (selectedProviders.value.length > 0) {
    localStorage.setItem(PROVIDER_SELECTION_KEY, JSON.stringify(selectedProviders.value))
  }
}

onMounted(() => {
  checkProviderAvailability()
})

// Initialize selected providers from localStorage (will be refined after availability check)
const initializeProviders = () => {
  // Try to load saved selection
  const saved = localStorage.getItem(PROVIDER_SELECTION_KEY)
  if (saved) {
    try {
      const savedProviders = JSON.parse(saved)
      // Initially use saved providers that have keys/models configured
      const validProviders = savedProviders.filter(p =>
        (p === 'anthropic' && hasAnthropicKey.value) ||
        (p === 'openai' && hasOpenAIKey.value) ||
        (p === 'ollama' && hasOllamaModel.value)
      )
      if (validProviders.length > 0) {
        selectedProviders.value = validProviders
        return
      }
    } catch (e) {
      console.error('Failed to load provider selection:', e)
    }
  }

  // Default: select all providers that have keys/models configured
  // (will be refined after actual availability check)
  const providers = []
  if (hasAnthropicKey.value) providers.push('anthropic')
  if (hasOpenAIKey.value) providers.push('openai')
  if (hasOllamaModel.value) providers.push('ollama')
  selectedProviders.value = providers
}
initializeProviders()

// Simple AI enable/disable toggle
const useAI = ref(true) // Default to enabled if provider available

// Load AI enabled state from localStorage
const loadAIEnabledState = () => {
  try {
    const saved = localStorage.getItem('asymptote_use_ai')
    if (saved !== null) {
      useAI.value = saved === 'true'
    }
  } catch (e) {
    console.error('Failed to load AI enabled state:', e)
  }
}
loadAIEnabledState()

// Save AI enabled state
const saveAISetting = () => {
  localStorage.setItem('asymptote_use_ai', useAI.value.toString())
}

// Get configured AI settings from Settings tab
const getAISettings = () => {
  try {
    const saved = localStorage.getItem('ai_settings')
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to load AI settings:', e)
  }
  return { rerank: false, synthesize: false }
}

// Check if AI is configured and enabled
const aiActive = computed(() => {
  if (!hasAnyAvailableProvider.value || !useAI.value) return false
  const settings = getAISettings()
  return settings.rerank || settings.synthesize
})

const activeFeaturesList = computed(() => {
  const settings = getAISettings()
  const features = []
  if (settings.rerank) features.push('Reranking')
  if (settings.synthesize) features.push('Synthesis')
  return features.length > 0 ? features.join(' + ') : 'No features enabled'
})

const cacheStats = computed(() => searchStore.getCacheStats())

const historyEntries = computed(() => {
  // Use the reactive cache directly
  return Object.values(searchStore.cache)
    .filter(entry => entry && entry.query && entry.timestamp) // Filter out corrupted entries
    .sort((a, b) => b.timestamp - a.timestamp)
})

const toggleProvider = (provider) => {
  const index = selectedProviders.value.indexOf(provider)
  if (index > -1) {
    // Remove if already selected (but keep at least one selected)
    if (selectedProviders.value.length > 1) {
      selectedProviders.value.splice(index, 1)
    }
  } else {
    // Add if not selected
    selectedProviders.value.push(provider)
  }
  // Save selection to localStorage
  localStorage.setItem(PROVIDER_SELECTION_KEY, JSON.stringify(selectedProviders.value))
}

const selectAllCloudProviders = () => {
  const providers = []
  if (hasAnthropicKey.value) providers.push('anthropic')
  if (hasOpenAIKey.value) providers.push('openai')
  selectedProviders.value = providers
  // Save selection to localStorage
  localStorage.setItem(PROVIDER_SELECTION_KEY, JSON.stringify(selectedProviders.value))
}


const getProviderDisplayName = (provider) => {
  const names = {
    'anthropic': 'Anthropic Claude',
    'openai': 'OpenAI GPT',
    'ollama': 'Ollama'
  }
  return names[provider] || provider
}

const escapeRegExp = (str) => {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

const highlightText = (text, searchQuery) => {
  if (!searchQuery) return text

  const keywords = searchQuery.toLowerCase().split(/\s+/).filter(k => k.length > 2)
  let result = text

  keywords.forEach(keyword => {
    const regex = new RegExp(`(${escapeRegExp(keyword)})`, 'gi')
    result = result.replace(regex, '<mark class="bg-yellow-300 dark:bg-yellow-600 px-1 rounded">$1</mark>')
  })

  return result
}

const formatTimeAgo = (timestamp) => {
  const seconds = Math.floor((Date.now() - timestamp) / 1000)

  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`
  return `${Math.floor(seconds / 86400)} days ago`
}

const useCachedResults = () => {
  if (!cachedData.value) return

  // Load cached results into the store
  searchStore.setSearchResults({
    query: cachedData.value.query,
    results: cachedData.value.results,
    synthesis: cachedData.value.synthesis,
    ai_usage: cachedData.value.ai_usage,
    aiResponses: cachedData.value.aiResponses
  })

  showCachePrompt.value = false
  cachedData.value = null
  emit('stats-updated')
}

const performFreshSearch = async () => {
  showCachePrompt.value = false
  cachedData.value = null
  await executeSearch()
}

const loadHistoryEntry = (entry) => {
  // Load the cached entry
  searchStore.setSearchResults({
    query: entry.query,
    results: entry.results,
    synthesis: entry.synthesis,
    ai_usage: entry.ai_usage,
    aiResponses: entry.aiResponses
  })

  // Update the query and topK values
  searchStore.setQuery(entry.query)
  searchStore.setTopK(entry.topK)

  showHistoryModal.value = false
  emit('stats-updated')
}

const deleteHistoryEntry = (entry) => {
  searchStore.deleteCacheEntry(entry.query, entry.topK)
}

const clearAllHistory = () => {
  if (confirm('Clear all search history? This cannot be undone.')) {
    searchStore.clearSearchCache()
    showHistoryModal.value = false
  }
}

const startNewSearch = () => {
  // Clear the current search state
  searchStore.clearResults()
  searchStore.setQuery('')
  error.value = ''
  showCachePrompt.value = false
  cachedData.value = null
}

const search = async () => {
  if (!searchStore.query.trim()) return

  error.value = ''

  // Check for cached results first
  const cached = searchStore.getCachedResult(searchStore.query, searchStore.topK)
  if (cached) {
    cachedData.value = cached
    showCachePrompt.value = true
    return
  }

  // No cache found, perform fresh search
  await executeSearch()
}

const executeSearch = async () => {
  loading.value = true
  error.value = ''

  try {
    const aiSettingsRaw = localStorage.getItem('ai_settings')
    const aiSettings = aiSettingsRaw ? JSON.parse(aiSettingsRaw) : {}

    // Check if AI features are enabled AND the user has AI toggle enabled
    const aiEnabled = useAI.value && (aiSettings.rerank || aiSettings.synthesize)

    // If AI is enabled and we have multiple providers selected
    if (aiEnabled && selectedProviders.value.length > 0) {
      // Execute searches for each selected provider in parallel
      const searchPromises = selectedProviders.value.map(async (provider) => {
        const body = {
          query: searchStore.query,
          top_k: searchStore.topK,
          ai: {
            provider: provider,
            rerank: !!aiSettings.rerank,
            synthesize: !!aiSettings.synthesize
          }
        }

        let headers = {}

        // Set headers based on provider type
        if (provider === 'ollama') {
          const ollamaModel = localStorage.getItem('ollama_model') || 'llama3.2'
          headers['X-Ollama-Model'] = ollamaModel
        } else {
          // Cloud providers need API key
          const key = localStorage.getItem(`ai_api_key_${provider}`)
          if (!key) return null
          headers['X-AI-Key'] = key
        }

        try {
          const collectionId = collectionStore.currentCollectionId
          const response = await axios.post(`/search?collection_id=${collectionId}`, body, { headers })
          return {
            provider,
            results: response.data.results,
            synthesis: response.data.synthesis,
            aiUsage: response.data.ai_usage
          }
        } catch (err) {
          console.error(`Search with ${provider} failed:`, err)
          return {
            provider,
            error: err.response?.data?.detail || `${provider} search failed`
          }
        }
      })

      const providerResults = await Promise.all(searchPromises)
      const validResults = providerResults.filter(r => r !== null)

      // Use results from the first successful search, or combine if multiple
      const primaryResult = validResults.find(r => !r.error)
      if (!primaryResult) {
        throw new Error(validResults[0]?.error || 'All AI searches failed')
      }

      // Collect AI responses from all providers
      const aiResponses = validResults
        .filter(r => !r.error && (r.synthesis || r.aiUsage))
        .map(r => ({
          provider: r.provider,
          synthesis: r.synthesis,
          aiUsage: r.aiUsage
        }))

      searchStore.setSearchResults({
        query: searchStore.query,
        results: primaryResult.results,
        aiResponses: aiResponses
      })
    } else {
      // Regular search without AI
      const body = {
        query: searchStore.query,
        top_k: searchStore.topK
      }

      const collectionId = collectionStore.currentCollectionId
      const response = await axios.post(`/search?collection_id=${collectionId}`, body)
      searchStore.setSearchResults({
        query: searchStore.query,
        results: response.data.results
      })
    }

    emit('stats-updated')
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Search failed. Please try again.'
    searchStore.clearResults()
  } finally {
    loading.value = false
  }
}
</script>
