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
          v-if="!loading"
          class="btn btn-primary join-item"
          @click="search"
          :disabled="!searchStore.query.trim()"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          Search
        </button>
        <button
          v-else
          class="btn btn-error join-item"
          @click="cancelSearch"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
          Cancel
        </button>
      </div>
      <div v-if="loading" class="text-sm text-base-content/60 mt-2">
        <span class="loading loading-spinner loading-xs mr-2"></span>
        {{ aiActive ? (selectedProviders.includes('ollama') ? 'AI processing... (Ollama may take a while)' : 'AI processing...') : 'Searching...' }}
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

    <!-- AI Provider Selection - Only show if features are enabled in Settings -->
    <div v-if="hasAnyProvider && aiFeaturesEnabled" class="card bg-base-200 p-3">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
          <span class="font-medium text-sm">AI Providers</span>
          <span class="text-xs text-base-content/60">({{ activeFeaturesList }})</span>
        </div>
        <button class="btn btn-xs btn-ghost" @click="$emit('switch-tab', 'settings')">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
      <div class="flex flex-wrap gap-2">
        <!-- Anthropic -->
        <label v-if="hasAnthropicKey" class="flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
               :class="selectedProviders.includes('anthropic') ? 'bg-primary/20 border border-primary' : 'bg-base-300 hover:bg-base-100'">
          <input type="checkbox" class="checkbox checkbox-xs checkbox-primary"
                 :checked="selectedProviders.includes('anthropic')"
                 @change="toggleProvider('anthropic')" />
          <span class="text-sm">Claude</span>
        </label>
        <!-- OpenAI -->
        <label v-if="hasOpenAIKey" class="flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
               :class="selectedProviders.includes('openai') ? 'bg-success/20 border border-success' : 'bg-base-300 hover:bg-base-100'">
          <input type="checkbox" class="checkbox checkbox-xs checkbox-success"
                 :checked="selectedProviders.includes('openai')"
                 @change="toggleProvider('openai')" />
          <span class="text-sm">ChatGPT</span>
        </label>
        <!-- Ollama -->
        <div v-if="ollamaAvailable" class="tooltip tooltip-bottom" data-tip="Slower than cloud models, but free and private">
          <label class="flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
                 :class="selectedProviders.includes('ollama') ? 'bg-info/20 border border-info' : 'bg-base-300 hover:bg-base-100'">
            <input type="checkbox" class="checkbox checkbox-xs checkbox-info"
                   :checked="selectedProviders.includes('ollama')"
                   @change="toggleProvider('ollama')" />
            <span class="text-sm">Ollama</span>
            <span class="text-xs opacity-60">local</span>
          </label>
        </div>
      </div>
      <p v-if="selectedProviders.length === 0" class="text-xs text-base-content/60 mt-2">
        No providers selected - search will not use AI
      </p>
      <p v-else-if="selectedProviders.length > 1" class="text-xs text-base-content/60 mt-2">
        {{ selectedProviders.length }} providers selected - results from each will be shown
      </p>
      <p v-if="selectedProviders.includes('ollama') && selectedProviders.length === 1" class="text-xs text-info mt-2">
        Ollama runs locally - slower but private and free
      </p>
    </div>

    <!-- AI Feature Prompt (only show if no AI configured) -->
    <div v-if="!hasAnyProvider" class="alert alert-info">
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
                <!-- Format-aware icon -->
                <svg v-if="result.source_format === 'csv'" class="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
                <svg v-else-if="result.source_format === 'pdf'" class="w-5 h-5 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <svg v-else-if="result.source_format === 'md'" class="w-5 h-5 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>
                </svg>
                <svg v-else class="w-5 h-5 text-base-content/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                {{ result.filename }}
              </h4>
              <div class="flex flex-wrap gap-1 mt-1">
                <!-- Page/Row indicator -->
                <div v-if="result.source_format === 'csv' && result.csv_row_number" class="badge badge-success badge-sm">
                  Row {{ result.csv_row_number }}
                </div>
                <div v-else class="badge badge-primary badge-sm">
                  Page {{ result.page_number }}
                </div>
                <!-- Similarity score -->
                <div class="badge badge-ghost badge-sm">
                  Similarity: {{ (result.similarity_score * 100).toFixed(1) }}%
                </div>
                <!-- Extraction method indicator (for OCR) -->
                <div v-if="result.extraction_method === 'ocr'" class="badge badge-warning badge-sm">
                  OCR
                </div>
                <div v-else-if="result.extraction_method === 'hybrid'" class="badge badge-info badge-sm">
                  Hybrid
                </div>
                <!-- Format badge -->
                <div v-if="result.source_format" class="badge badge-outline badge-sm">
                  {{ result.source_format.toUpperCase() }}
                </div>
              </div>
            </div>
          </div>

          <!-- CSV Table View (v3.0 feature) -->
          <div v-if="result.source_format === 'csv' && result.csv_columns && result.csv_values" class="mt-3 overflow-x-auto">
            <table class="table table-xs table-zebra">
              <thead>
                <tr>
                  <th v-for="col in result.csv_columns" :key="col" class="bg-base-300 text-xs font-semibold">
                    {{ col }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td v-for="col in result.csv_columns" :key="col" class="text-sm">
                    <span v-html="highlightText(String(result.csv_values[col] || ''), searchStore.query)"></span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Standard text snippet (for non-CSV or CSV without row data) -->
          <p v-else class="text-sm mt-2" v-html="highlightText(result.text_snippet, searchStore.query)"></p>

          <div class="card-actions justify-end mt-4">
            <a
              :href="result.page_url"
              target="_blank"
              class="btn btn-sm btn-primary"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
              {{ result.source_format === 'csv' ? 'Open Row' : 'Open Page' }} {{ result.source_format === 'csv' ? result.csv_row_number : result.page_number }}
            </a>
            <a
              :href="result.pdf_url"
              target="_blank"
              class="btn btn-sm btn-ghost"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              Download
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

    <!-- Welcome State (shown when no search has been performed yet) -->
    <div v-else-if="!searchStore.searched && !loading" class="flex justify-center py-8">
      <!-- Large 3D Card with all content inside -->
      <div class="hover-3d hover-3d-logo">
        <figure class="w-full max-w-xl rounded-3xl bg-gradient-to-br from-primary/10 to-secondary/10 border border-base-300 shadow-xl p-8 flex flex-col items-center justify-center">
          <!-- Logo (switches based on theme - black for light themes, white for dark themes) -->
          <img src="/icon_black.svg" alt="Asymptote" class="logo-light h-32 opacity-80 mb-6" style="filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));">
          <img src="/icon_white.svg" alt="Asymptote" class="logo-dark h-32 opacity-80 mb-6" style="filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.3));">

          <!-- Title and Description -->
          <h3 class="text-2xl font-bold text-base-content/80 mb-2">Ready to Search</h3>
          <p class="text-base-content/60 text-center max-w-md mb-6">
            Enter a query above to semantically search through your documents.
            Results are ranked by meaning, not just keywords.
          </p>

          <!-- Feature Badges -->
          <div class="flex flex-wrap justify-center gap-2 text-xs">
            <span class="badge badge-primary badge-outline">Semantic Search</span>
            <span class="badge badge-secondary badge-outline">AI-Powered</span>
            <span class="badge badge-accent badge-outline">Multi-Format Support</span>
          </div>
        </figure>
        <!-- 8 empty divs needed for the 3D effect -->
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
      </div>
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

// AbortController for cancelling ongoing searches
let abortController = null

// Cache prompt state
const showCachePrompt = ref(false)
const cachedData = ref(null)

// History modal state
const showHistoryModal = ref(false)

// AI Settings - Read from Settings tab's localStorage values
// API keys and feature toggles (rerank/synthesize) are managed in Settings
// Provider selection for each search is managed here

// Check which providers have keys/models configured
const hasAnthropicKey = computed(() => !!localStorage.getItem('ai_api_key_anthropic'))
const hasOpenAIKey = computed(() => !!localStorage.getItem('ai_api_key_openai'))
const hasOllamaModel = computed(() => !!localStorage.getItem('ollama_model'))
const hasAnyProvider = computed(() => hasAnthropicKey.value || hasOpenAIKey.value || ollamaAvailable.value)

// Provider availability (for Ollama, we need to check if it's actually running)
const ollamaAvailable = ref(false)

// Selected providers for this search session
const PROVIDER_SELECTION_KEY = 'asymptote_selected_providers'
const selectedProviders = ref([])

// Initialize selected providers from localStorage
const initializeProviders = () => {
  const saved = localStorage.getItem(PROVIDER_SELECTION_KEY)
  if (saved) {
    try {
      selectedProviders.value = JSON.parse(saved)
    } catch (e) {
      selectedProviders.value = []
    }
  }
}

// Toggle a provider on/off
const toggleProvider = (provider) => {
  const index = selectedProviders.value.indexOf(provider)
  if (index > -1) {
    selectedProviders.value.splice(index, 1)
  } else {
    selectedProviders.value.push(provider)
  }
  localStorage.setItem(PROVIDER_SELECTION_KEY, JSON.stringify(selectedProviders.value))
}

// Check Ollama availability and initialize providers on mount
const checkOllamaAvailability = async () => {
  try {
    const response = await axios.get('/api/ollama/status')
    ollamaAvailable.value = response.data.available === true
    // If Ollama is available and no model is saved, save the first available model
    if (ollamaAvailable.value && !hasOllamaModel.value && response.data.models?.length > 0) {
      localStorage.setItem('ollama_model', response.data.models[0].name)
    }
  } catch (e) {
    ollamaAvailable.value = false
  }

  // After checking availability, initialize/validate selected providers
  initializeProviders()

  // Filter out any providers that are no longer available
  const validProviders = selectedProviders.value.filter(p => {
    if (p === 'anthropic') return hasAnthropicKey.value
    if (p === 'openai') return hasOpenAIKey.value
    if (p === 'ollama') return ollamaAvailable.value
    return false
  })

  // If no saved selection or all were invalid, default to all available
  if (selectedProviders.value.length === 0 || validProviders.length === 0) {
    const defaults = []
    if (hasAnthropicKey.value) defaults.push('anthropic')
    if (hasOpenAIKey.value) defaults.push('openai')
    if (ollamaAvailable.value) defaults.push('ollama')
    selectedProviders.value = defaults
    localStorage.setItem(PROVIDER_SELECTION_KEY, JSON.stringify(defaults))
  } else {
    selectedProviders.value = validProviders
    localStorage.setItem(PROVIDER_SELECTION_KEY, JSON.stringify(validProviders))
  }
}

onMounted(() => {
  checkOllamaAvailability()
})

// Get configured AI settings from Settings tab (features only - rerank/synthesize)
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

// Check if AI features are enabled in Settings
const aiFeaturesEnabled = computed(() => {
  const settings = getAISettings()
  return settings.rerank || settings.synthesize
})

// Check if AI will be used for this search (features enabled + providers selected)
const aiActive = computed(() => {
  return aiFeaturesEnabled.value && selectedProviders.value.length > 0
})

const activeFeaturesList = computed(() => {
  const settings = getAISettings()
  const features = []
  if (settings.rerank) features.push('Reranking')
  if (settings.synthesize) features.push('Synthesis')
  return features.length > 0 ? features.join(' + ') : 'None'
})

const cacheStats = computed(() => searchStore.getCacheStats())

const historyEntries = computed(() => {
  // Get cache for current collection (cache is collection-aware: { collectionId: { "query|topK": entry } })
  const collectionId = collectionStore.currentCollectionId || 'default'
  const collectionCache = searchStore.cache[collectionId] || {}
  return Object.values(collectionCache)
    .filter(entry => entry && entry.query && entry.timestamp) // Filter out corrupted entries
    .sort((a, b) => b.timestamp - a.timestamp)
})

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

const cancelSearch = () => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  loading.value = false
  // Note: Backend/Ollama may continue processing, but we stop waiting for the response
  error.value = 'Search cancelled (backend may still be processing)'
}

const executeSearch = async () => {
  // Create new AbortController for this search
  abortController = new AbortController()
  const signal = abortController.signal

  loading.value = true
  error.value = ''

  try {
    const aiSettings = getAISettings()
    const useAI = aiActive.value

    if (useAI && selectedProviders.value.length > 0) {
      // Execute search with each selected provider in parallel
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
        if (provider === 'ollama') {
          headers['X-Ollama-Model'] = localStorage.getItem('ollama_model') || 'llama3.2'
        } else {
          const key = localStorage.getItem(`ai_api_key_${provider}`)
          if (key) headers['X-AI-Key'] = key
        }

        try {
          const collectionId = collectionStore.currentCollectionId
          const response = await axios.post(`/search?collection_id=${collectionId}`, body, { headers, signal })
          return {
            provider,
            results: response.data.results,
            synthesis: response.data.synthesis,
            aiUsage: response.data.ai_usage
          }
        } catch (err) {
          // Check if this was a cancellation
          if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
            throw err // Re-throw to be caught by outer catch
          }
          console.error(`Search with ${provider} failed:`, err)
          return { provider, error: err.response?.data?.detail || `${provider} failed` }
        }
      })

      const providerResults = await Promise.all(searchPromises)
      const successfulResults = providerResults.filter(r => !r.error)

      if (successfulResults.length === 0) {
        throw new Error(providerResults[0]?.error || 'All AI searches failed')
      }

      // Use results from first successful provider, collect all AI responses
      const aiResponses = successfulResults
        .filter(r => r.synthesis || r.aiUsage)
        .map(r => ({ provider: r.provider, synthesis: r.synthesis, aiUsage: r.aiUsage }))

      searchStore.setSearchResults({
        query: searchStore.query,
        results: successfulResults[0].results,
        aiResponses
      })
    } else {
      // Regular search without AI
      const body = { query: searchStore.query, top_k: searchStore.topK }
      const collectionId = collectionStore.currentCollectionId
      const response = await axios.post(`/search?collection_id=${collectionId}`, body, { signal })
      searchStore.setSearchResults({
        query: searchStore.query,
        results: response.data.results
      })
    }

    emit('stats-updated')
  } catch (err) {
    // Check if this was a cancellation - don't show as error
    if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
      error.value = 'Search cancelled'
      return
    }
    error.value = err.response?.data?.detail || err.message || 'Search failed. Please try again.'
    searchStore.clearResults()
  } finally {
    loading.value = false
    abortController = null
  }
}
</script>
