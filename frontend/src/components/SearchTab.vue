<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold">Search Documents</h2>

    <!-- Search Form -->
    <div class="form-control w-full">
      <label class="label">
        <span class="label-text">Enter your search query</span>
      </label>
      <div class="join w-full">
        <input
          v-model="query"
          type="text"
          placeholder="e.g., machine learning algorithms"
          class="input input-bordered join-item flex-1"
          @keyup.enter="search"
        />
        <button
          class="btn btn-primary join-item"
          @click="search"
          :disabled="loading || !query.trim()"
        >
          <svg v-if="!loading" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <span v-if="loading" class="loading loading-spinner"></span>
          {{ loading ? 'Searching...' : 'Search' }}
        </button>
      </div>
    </div>

    <!-- Number of Results -->
    <div class="form-control w-full max-w-xs">
      <label class="label">
        <span class="label-text">Number of results</span>
      </label>
      <input
        v-model.number="topK"
        type="number"
        min="1"
        max="50"
        class="input input-bordered w-full max-w-xs"
      />
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ error }}</span>
    </div>

    <!-- Results -->
    <div v-if="results.length > 0" class="space-y-4">
      <div class="flex justify-between items-center">
        <h3 class="text-xl font-semibold">Results ({{ results.length }})</h3>
        <p class="text-sm text-base-content/70">Query: "{{ lastQuery }}"</p>
      </div>

      <div v-for="(result, index) in results" :key="index" class="card bg-base-200 shadow-md">
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

          <p class="text-sm mt-2" v-html="highlightText(result.text_snippet, query)"></p>

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
    <div v-else-if="searched && !loading" class="alert alert-info">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <span>No results found. Try a different query or upload more documents.</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['stats-updated'])

const query = ref('')
const topK = ref(10)
const results = ref([])
const loading = ref(false)
const error = ref('')
const searched = ref(false)
const lastQuery = ref('')

const highlightText = (text, searchQuery) => {
  if (!searchQuery) return text

  const keywords = searchQuery.toLowerCase().split(/\s+/).filter(k => k.length > 2)
  let result = text

  keywords.forEach(keyword => {
    const regex = new RegExp(`(${keyword})`, 'gi')
    result = result.replace(regex, '<mark class="bg-yellow-300 dark:bg-yellow-600 px-1 rounded">$1</mark>')
  })

  return result
}

const search = async () => {
  if (!query.value.trim()) return

  loading.value = true
  error.value = ''
  searched.value = true
  lastQuery.value = query.value

  try {
    const response = await axios.post('/search', {
      query: query.value,
      top_k: topK.value
    })

    results.value = response.data.results
    emit('stats-updated')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Search failed. Please try again.'
    results.value = []
  } finally {
    loading.value = false
  }
}
</script>
