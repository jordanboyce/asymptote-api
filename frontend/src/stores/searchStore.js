import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useSearchStore = defineStore('search', () => {
  // Search state
  const query = ref('')
  const topK = ref(10)
  const results = ref([])
  const lastQuery = ref('')
  const synthesis = ref('')
  const aiUsage = ref(null)
  const searched = ref(false)

  // Support for multiple AI providers
  const aiResponses = ref([])  // Array of {provider, synthesis, aiUsage}

  // Search cache
  const CACHE_KEY = 'asymptote_search_cache'
  const MAX_CACHE_SIZE = 20
  const cacheCount = ref(0) // Reactive cache count for UI updates
  const cache = ref({}) // Reactive cache data for UI updates

  // Actions
  function setSearchResults(data) {
    results.value = data.results || []
    lastQuery.value = data.query || ''
    searched.value = true

    // Handle single AI response (backward compatibility)
    if (data.synthesis || data.ai_usage) {
      synthesis.value = data.synthesis || ''
      aiUsage.value = data.ai_usage || null
    }

    // Handle multiple AI responses
    if (data.aiResponses && data.aiResponses.length > 0) {
      aiResponses.value = data.aiResponses
    } else {
      aiResponses.value = []
    }

    // Cache the search results
    if (data.query) {
      cacheSearchResult(data)
    }
  }

  function getCacheKey(query, topK) {
    return `${query.toLowerCase().trim()}|${topK}`
  }

  function cacheSearchResult(data) {
    try {
      const cacheKey = getCacheKey(data.query, topK.value)

      // Normalize query to lowercase for consistency
      const normalizedQuery = data.query.toLowerCase().trim()

      // Create cache entry
      const entry = {
        query: normalizedQuery,
        topK: topK.value,
        results: data.results,
        aiResponses: data.aiResponses || [],
        synthesis: data.synthesis,
        ai_usage: data.ai_usage,
        timestamp: Date.now()
      }

      // Add to cache (or update if exists)
      cache.value[cacheKey] = entry

      // Keep only the most recent MAX_CACHE_SIZE entries
      const entries = Object.entries(cache.value)
        .sort((a, b) => b[1].timestamp - a[1].timestamp)
        .slice(0, MAX_CACHE_SIZE)

      cache.value = Object.fromEntries(entries)
      localStorage.setItem(CACHE_KEY, JSON.stringify(cache.value))

      // Sync cache count
      syncCacheCount()
    } catch (error) {
      console.error('Failed to cache search results:', error)
    }
  }

  function getSearchCache() {
    // Return the reactive cache ref value
    return cache.value
  }

  function getCachedResult(query, topKValue) {
    const cacheKey = getCacheKey(query, topKValue)
    return cache.value[cacheKey] || null
  }

  function clearSearchCache() {
    cache.value = {}
    localStorage.removeItem(CACHE_KEY)
    syncCacheCount()
  }

  function deleteCacheEntry(query, topKValue) {
    const cacheKey = getCacheKey(query, topKValue)
    delete cache.value[cacheKey]
    // Trigger reactivity by creating a new object
    cache.value = { ...cache.value }
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache.value))
    syncCacheCount()
  }

  function getCacheStats() {
    const entries = Object.values(cache.value)
    // Always compute count from actual cache to ensure accuracy
    const actualCount = entries.length
    return {
      count: actualCount,
      totalSize: JSON.stringify(cache.value).length,
      oldest: entries.length > 0 ? Math.min(...entries.map(e => e.timestamp)) : null,
      newest: entries.length > 0 ? Math.max(...entries.map(e => e.timestamp)) : null
    }
  }

  // Initialize cache from localStorage on store creation
  function initializeCache() {
    try {
      const cached = localStorage.getItem(CACHE_KEY)
      if (!cached) {
        cache.value = {}
        cacheCount.value = 0
        return
      }

      const loadedCache = JSON.parse(cached)

      // Validate and clean cache entries
      const validCache = {}
      for (const [key, entry] of Object.entries(loadedCache)) {
        // Only keep entries with required fields
        if (entry && entry.query && entry.timestamp && entry.topK) {
          validCache[key] = entry
        }
      }

      cache.value = validCache
      cacheCount.value = Object.keys(validCache).length

      // If we cleaned anything, save the cleaned cache
      if (Object.keys(validCache).length !== Object.keys(loadedCache).length) {
        localStorage.setItem(CACHE_KEY, JSON.stringify(validCache))
      }
    } catch (error) {
      console.error('Failed to load search cache:', error)
      cache.value = {}
      cacheCount.value = 0
    }
  }

  // Sync cache count from actual cache
  function syncCacheCount() {
    cacheCount.value = Object.keys(cache.value).length
  }

  initializeCache()

  function clearResults() {
    results.value = []
    synthesis.value = ''
    aiUsage.value = null
    aiResponses.value = []
    searched.value = false
  }

  function setQuery(newQuery) {
    query.value = newQuery
  }

  function setTopK(value) {
    topK.value = value
  }

  return {
    // State
    query,
    topK,
    results,
    lastQuery,
    synthesis,
    aiUsage,
    searched,
    aiResponses,
    cache, // Reactive cache ref
    // Actions
    setSearchResults,
    clearResults,
    setQuery,
    setTopK,
    // Cache functions
    getCachedResult,
    getSearchCache,
    clearSearchCache,
    deleteCacheEntry,
    getCacheStats,
    syncCacheCount
  }
})
