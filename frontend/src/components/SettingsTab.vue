<template>
  <div class="flex gap-6">
    <!-- Table of Contents Sidebar -->
    <aside class="hidden lg:block w-56 shrink-0">
      <nav class="sticky top-36 space-y-1">
        <div class="text-sm font-semibold text-base-content/60 mb-3 uppercase tracking-wide">Settings</div>

        <!-- Global Section -->
        <div class="text-xs font-semibold text-base-content/50 mt-4 mb-1 uppercase">Global</div>
        <a
          href="#ai-integration"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'ai-integration' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('ai-integration')"
        >
          AI Integration
        </a>
        <a
          href="#search-config"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'search-config' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('search-config')"
        >
          Search Config
        </a>
        <a
          href="#metadata-storage"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'metadata-storage' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('metadata-storage')"
        >
          Metadata Storage
        </a>
        <a
          href="#appearance"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'appearance' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('appearance')"
        >
          Appearance
        </a>

        <!-- Collection Section -->
        <div class="text-xs font-semibold text-base-content/50 mt-4 mb-1 uppercase">Collection</div>
        <a
          href="#collection-info"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'collection-info' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('collection-info')"
        >
          Information
        </a>
        <a
          href="#text-chunking"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'text-chunking' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('text-chunking')"
        >
          Text Chunking
        </a>
        <a
          href="#reindex"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'reindex' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('reindex')"
        >
          Re-index
        </a>
        <a
          href="#index-repair"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'index-repair' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('index-repair')"
        >
          Index Repair
        </a>
        <a
          href="#embedding-model"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'embedding-model' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('embedding-model')"
        >
          Embedding Model
        </a>

        <!-- Other Section -->
        <div class="text-xs font-semibold text-base-content/50 mt-4 mb-1 uppercase">Other</div>
        <a
          href="#backups"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'backups' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('backups')"
        >
          Backups
        </a>
        <a
          href="#api-docs"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'api-docs' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('api-docs')"
        >
          API Docs
        </a>
        <a
          href="#about"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'about' ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('about')"
        >
          About
        </a>
        <a
          href="#danger-zone"
          class="block px-3 py-1.5 text-sm rounded-lg transition-colors"
          :class="activeSection === 'danger-zone' ? 'bg-primary/10 text-error font-medium' : 'hover:bg-base-200 text-base-content/70'"
          @click.prevent="scrollToSection('danger-zone')"
        >
          Danger Zone
        </a>
      </nav>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 min-w-0 space-y-6">
      <div class="flex items-center justify-between">
        <h2 class="text-2xl font-bold">Settings</h2>
      </div>

      <!-- ============ GLOBAL SETTINGS ============ -->

      <!-- AI Integration -->
      <div id="ai-integration" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <h3 class="card-title">AI Integration</h3>
          <p class="text-sm text-base-content/70 mb-2">
            Connect your own AI provider to get answers from your documents, not just search results.
            Your key is stored only in your browser and sent per request. The server never stores it.
          </p>

          <!-- Provider Selection -->
          <div class="form-control mb-3">
            <label class="label">
              <span class="label-text">Provider</span>
            </label>
            <div class="flex gap-2">
              <button
                class="btn btn-sm flex-1 relative"
                :class="aiSettings.provider === 'anthropic' ? 'btn-primary' : 'btn-ghost'"
                @click="setProvider('anthropic')"
              >
                Anthropic
                <span v-if="hasAnthropicKey" class="absolute -top-1 -right-1 badge badge-success badge-xs">&#10003;</span>
              </button>
              <button
                class="btn btn-sm flex-1 relative"
                :class="aiSettings.provider === 'openai' ? 'btn-primary' : 'btn-ghost'"
                @click="setProvider('openai')"
              >
                OpenAI
                <span v-if="hasOpenAIKey" class="absolute -top-1 -right-1 badge badge-success badge-xs">&#10003;</span>
              </button>
              <button
                class="btn btn-sm flex-1 relative"
                :class="aiSettings.provider === 'ollama' ? 'btn-primary' : 'btn-ghost'"
                @click="setProvider('ollama')"
              >
                Ollama
                <span v-if="ollamaAvailable" class="absolute -top-1 -right-1 badge badge-success badge-xs">&#10003;</span>
                <span v-else-if="aiSettings.provider === 'ollama'" class="absolute -top-1 -right-1 badge badge-error badge-xs">&#10007;</span>
              </button>
            </div>
            <label v-if="hasBothKeys" class="label">
              <span class="label-text-alt text-success">
                Both cloud providers configured - AI answers will use both
              </span>
            </label>
            <label v-if="aiSettings.provider === 'ollama' && ollamaAvailable" class="label">
              <span class="label-text-alt text-success">
                Ollama detected - Free local AI (no API costs)
              </span>
            </label>
          </div>

          <!-- Ollama Model Selection -->
          <div v-if="aiSettings.provider === 'ollama'" class="form-control">
            <label class="label">
              <span class="label-text">Ollama Status</span>
            </label>

            <div v-if="checkingOllama" class="flex justify-center py-4">
              <span class="loading loading-spinner"></span>
            </div>

            <div v-else-if="!ollamaAvailable" class="alert alert-warning">
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <div class="font-bold">Ollama not detected</div>
                <div class="text-sm">Install Ollama from <a href="https://ollama.com" target="_blank" class="link link-primary">ollama.com</a> to use local AI models.</div>
              </div>
            </div>

            <div v-else class="space-y-3">
              <div class="alert alert-success">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <div class="font-bold">Ollama is running</div>
                  <div class="text-sm">{{ ollamaModels.length }} model(s) available</div>
                </div>
              </div>

              <label class="label">
                <span class="label-text">Select Model</span>
              </label>
              <select
                v-model="selectedOllamaModel"
                class="select select-bordered w-full"
                @change="saveOllamaModel"
              >
                <option v-for="model in ollamaModels" :key="model.name" :value="model.name">
                  {{ model.name }} ({{ formatBytes(model.size) }})
                </option>
              </select>

              <div v-if="selectedOllamaModel" class="text-xs text-base-content/70 bg-base-300 p-3 rounded">
                <strong>Note:</strong> Ollama runs entirely on your machine. No API costs, complete privacy.
                Performance depends on your hardware.
              </div>
            </div>

            <div class="mt-2">
              <button class="btn btn-sm btn-ghost" @click="checkOllamaStatus">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
          </div>

          <!-- API Key Input (Cloud Providers Only) -->
          <div v-else class="form-control">
            <label class="label">
              <span class="label-text">{{ aiSettings.provider === 'openai' ? 'OpenAI' : 'Anthropic' }} API Key</span>
            </label>
            <div class="join w-full">
              <input
                v-model="apiKey"
                :type="showKey ? 'text' : 'password'"
                :placeholder="aiSettings.provider === 'openai' ? 'sk-...' : 'sk-ant-...'"
                class="input input-bordered join-item flex-1"
                @input="apiKeyDirty = true; apiKeyStatus = ''"
              />
              <button class="btn join-item" @click="showKey = !showKey">
                {{ showKey ? 'Hide' : 'Show' }}
              </button>
              <button
                class="btn btn-primary join-item"
                @click="validateAndSaveKey"
                :disabled="validatingKey || !apiKey.trim()"
              >
                <span v-if="validatingKey" class="loading loading-spinner loading-xs"></span>
                {{ validatingKey ? '' : 'Save' }}
              </button>
            </div>
            <label class="label">
              <span class="label-text-alt">
                <a v-if="aiSettings.provider === 'openai'" href="https://platform.openai.com/api-keys" target="_blank" class="link link-primary">Get an OpenAI key</a>
                <a v-else href="https://console.anthropic.com/settings/keys" target="_blank" class="link link-primary">Get an Anthropic key</a>
              </span>
              <span v-if="apiKeyStatus === 'valid'" class="label-text-alt text-success font-semibold">Key valid</span>
              <span v-else-if="apiKeyStatus === 'invalid'" class="label-text-alt text-error font-semibold">Invalid key</span>
              <span v-else-if="apiKeyStatus === 'saved'" class="label-text-alt text-success font-semibold">Saved</span>
              <span v-else-if="apiKeyStatus === 'error'" class="label-text-alt text-error font-semibold">Error validating</span>
            </label>
            <div v-if="validationError" class="text-xs text-error mt-1 px-1">{{ validationError }}</div>
          </div>

          <!-- Remove Key (Cloud Providers Only) -->
          <div v-if="aiSettings.provider !== 'ollama' && hasStoredKey && !apiKeyDirty" class="mt-2">
            <button class="btn btn-ghost btn-sm text-error" @click="removeKey">
              Remove stored key
            </button>
          </div>

          <!-- AI Feature Toggles -->
          <div v-if="hasStoredKey || (aiSettings.provider === 'ollama' && ollamaAvailable)" class="divider"></div>
          <div v-if="hasStoredKey || (aiSettings.provider === 'ollama' && ollamaAvailable)" class="space-y-3">
            <h4 class="font-semibold text-sm">AI Features</h4>

            <div class="form-control">
              <label class="label cursor-pointer justify-start gap-4">
                <input
                  type="checkbox"
                  class="toggle toggle-primary toggle-sm"
                  :checked="aiSettings.rerank"
                  @change="toggleAI('rerank')"
                />
                <div>
                  <span class="label-text font-medium">Result Reranking</span>
                  <p class="text-xs text-base-content/60">
                    Vector search finds semantically similar text, but similar doesn't always mean relevant.
                    Reranking uses AI to judge which results actually answer your question.
                  </p>
                </div>
              </label>
            </div>

            <div class="form-control">
              <label class="label cursor-pointer justify-start gap-4">
                <input
                  type="checkbox"
                  class="toggle toggle-primary toggle-sm"
                  :checked="aiSettings.synthesize"
                  @change="toggleAI('synthesize')"
                />
                <div>
                  <span class="label-text font-medium">Answer Synthesis</span>
                  <p class="text-xs text-base-content/60">
                    Get a direct answer synthesized from your documents with citations back to specific pages.
                  </p>
                </div>
              </label>
            </div>

            <div v-if="aiSettings.provider === 'ollama'" class="text-xs text-success mt-2">
              Using local Ollama model - Free, no API costs!
            </div>
            <div v-else class="text-xs text-base-content/50 mt-2">
              Estimated cost per search: ~${{ estimatedCost }} (billed to your {{ aiSettings.provider === 'openai' ? 'OpenAI' : 'Anthropic' }} account)
            </div>
          </div>
        </div>
      </div>

      <!-- Search Configuration -->
      <div id="search-config" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <h3 class="card-title">Search Configuration</h3>
          <div class="form-control w-full max-w-xs">
            <label class="label">
              <span class="label-text">Default Number of Results</span>
              <span class="label-text-alt">1-50</span>
            </label>
            <input
              v-model.number="defaultTopK"
              type="number"
              min="1"
              max="50"
              class="input input-bordered w-full"
              @change="saveDefaultTopK"
            />
            <p class="text-xs text-base-content/60 mt-2">Sets the default for new searches. You can override this per search.</p>
          </div>
        </div>
      </div>

      <!-- Metadata Storage (Global) -->
      <div id="metadata-storage" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <div class="flex items-center gap-2">
            <h3 class="card-title">Metadata Storage</h3>
            <span class="badge badge-sm badge-ghost">Global</span>
          </div>
          <p class="text-sm text-base-content/70 mb-4">
            Choose how document metadata is stored. This is a global setting that applies to all collections.
          </p>

          <div class="space-y-4">
            <!-- Current Storage Type -->
            <div class="alert alert-info">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <div>
                <div class="font-bold">Current Storage</div>
                <div class="text-sm capitalize">{{ currentConfig.metadata_storage }}</div>
              </div>
            </div>

            <!-- Storage Selection -->
            <div class="form-control">
              <label class="label cursor-pointer justify-start gap-4">
                <input
                  type="radio"
                  name="storage"
                  class="radio radio-primary"
                  value="json"
                  v-model="selectedStorage"
                  @change="onStorageChange"
                />
                <div class="flex-1">
                  <span class="label-text font-medium">JSON (Simple)</span>
                  <p class="text-xs text-base-content/60">
                    Human-readable, good for &lt;100 documents. Loads entire metadata into memory.
                  </p>
                </div>
              </label>
            </div>

            <div class="form-control">
              <label class="label cursor-pointer justify-start gap-4">
                <input
                  type="radio"
                  name="storage"
                  class="radio radio-primary"
                  value="sqlite"
                  v-model="selectedStorage"
                  @change="onStorageChange"
                />
                <div class="flex-1">
                  <span class="label-text font-medium">SQLite (Scalable)</span>
                  <p class="text-xs text-base-content/60">
                    Database storage, excellent for 1,000+ documents. 50x less memory, 30x faster startup.
                  </p>
                </div>
              </label>
            </div>

            <!-- Warning about restart -->
            <div v-if="storageChanged" class="alert alert-warning">
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <div class="font-bold">Server restart required</div>
                <div class="text-sm">
                  Switching storage types requires restarting the server. Your existing data will remain in the old location.
                  You'll need to re-upload documents to populate the new storage.
                </div>
              </div>
            </div>

            <!-- Apply Button -->
            <button
              class="btn btn-primary"
              :disabled="!storageChanged || applyingStorage"
              @click="applyStorageChange"
            >
              <span v-if="applyingStorage" class="loading loading-spinner loading-sm"></span>
              {{ applyingStorage ? 'Applying...' : 'Apply Storage Change' }}
            </button>

            <!-- Success/Error Messages -->
            <div v-if="storageMessage" class="alert" :class="storageMessageType === 'success' ? 'alert-success' : 'alert-error'">
              <div>{{ storageMessage }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Appearance -->
      <div id="appearance" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <h3 class="card-title">Appearance</h3>
          <p class="text-sm text-base-content/70 mb-4">
            Choose a theme for the interface. Your preference is saved in your browser.
          </p>

          <div class="form-control w-full">
            <label class="label">
              <span class="label-text">Theme</span>
              <span v-if="isUsingSystemTheme" class="label-text-alt text-info">Following system preference</span>
            </label>
            <select
              v-model="selectedTheme"
              class="select select-bordered w-full"
              @change="applyTheme"
            >
              <optgroup label="Light Themes">
                <option value="light">Light</option>
                <option value="cupcake">Cupcake</option>
                <option value="bumblebee">Bumblebee</option>
                <option value="emerald">Emerald</option>
                <option value="corporate">Corporate</option>
                <option value="retro">Retro</option>
                <option value="garden">Garden</option>
                <option value="lofi">Lo-Fi</option>
                <option value="pastel">Pastel</option>
                <option value="fantasy">Fantasy</option>
                <option value="wireframe">Wireframe</option>
                <option value="cmyk">CMYK</option>
                <option value="autumn">Autumn</option>
                <option value="acid">Acid</option>
                <option value="lemonade">Lemonade</option>
                <option value="winter">Winter</option>
                <option value="nord">Nord</option>
                <option value="caramellatte">Caramellatte</option>
                <option value="silk">Silk</option>
              </optgroup>
              <optgroup label="Dark Themes">
                <option value="dark">Dark</option>
                <option value="synthwave">Synthwave</option>
                <option value="cyberpunk">Cyberpunk</option>
                <option value="valentine">Valentine</option>
                <option value="halloween">Halloween</option>
                <option value="forest">Forest</option>
                <option value="aqua">Aqua</option>
                <option value="black">Black</option>
                <option value="luxury">Luxury</option>
                <option value="dracula">Dracula</option>
                <option value="business">Business</option>
                <option value="night">Night</option>
                <option value="coffee">Coffee</option>
                <option value="dim">Dim</option>
                <option value="sunset">Sunset</option>
                <option value="abyss">Abyss</option>
              </optgroup>
            </select>
          </div>

          <!-- Theme Preview -->
          <div class="mt-4 p-4 rounded-lg border border-base-300 bg-base-100">
            <div class="text-sm font-semibold mb-2">Preview</div>
            <div class="flex flex-wrap gap-2">
              <button class="btn btn-primary btn-sm">Primary</button>
              <button class="btn btn-secondary btn-sm">Secondary</button>
              <button class="btn btn-accent btn-sm">Accent</button>
              <button class="btn btn-neutral btn-sm">Neutral</button>
            </div>
          </div>

          <button
            v-if="!isUsingSystemTheme"
            class="btn btn-sm btn-ghost mt-4 w-fit"
            @click="resetToSystemTheme"
          >
            Reset to system default
          </button>
        </div>
      </div>

      <!-- ============ COLLECTION SETTINGS ============ -->

      <!-- Collection Info -->
      <div id="collection-info" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <h3 class="card-title">Collection Information</h3>
        <div v-if="loading" class="flex justify-center py-4">
          <span class="loading loading-spinner"></span>
        </div>
        <div v-else class="space-y-2">
          <div class="flex justify-between">
            <span class="font-semibold">Status:</span>
            <span class="badge badge-success">{{ health.status }}</span>
          </div>
          <div class="flex justify-between">
            <span class="font-semibold">Indexed Chunks:</span>
            <span>{{ health.indexed_chunks?.toLocaleString() || 0 }}</span>
          </div>
          <div class="flex justify-between">
            <span class="font-semibold">Chunk Size:</span>
            <span>{{ collectionStore.currentCollection?.chunk_size || 500 }} chars</span>
          </div>
          <div class="flex justify-between">
            <span class="font-semibold">Chunk Overlap:</span>
            <span>{{ collectionStore.currentCollection?.chunk_overlap || 50 }} chars</span>
          </div>
          <div class="flex justify-between">
            <span class="font-semibold">Embedding Model:</span>
            <span class="font-mono text-sm">{{ collectionStore.currentCollection?.embedding_model || currentConfig.embedding_model }}</span>
          </div>
          </div>
        </div>
      </div>

      <!-- Text Chunking Configuration (Per-Collection) -->
      <div id="text-chunking" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <div class="flex items-center gap-2">
            <h3 class="card-title">Text Chunking</h3>
          <span class="badge badge-sm badge-primary">Per Collection</span>
        </div>
        <p class="text-sm text-base-content/70 mb-4">
          Break documents into smaller pieces for better search. These settings apply only to the current collection.
        </p>

        <div class="space-y-6">
          <!-- Chunk Size Slider -->
          <div class="form-control w-full">
            <label class="label">
              <span class="label-text font-semibold">Chunk Size: {{ chunkSize }} characters</span>
              <span class="label-text-alt text-base-content/60">~{{ Math.round(chunkSize / 5) }} words</span>
            </label>
            <p class="text-xs text-base-content/60 mb-2">How much text goes into each searchable piece</p>
            <input
              type="range"
              min="200"
              max="2000"
              step="50"
              v-model.number="chunkSize"
              class="range range-primary w-full"
              @input="onChunkingChange"
            />
            <div class="w-full flex justify-between text-xs px-2 mt-1">
              <span class="text-xs opacity-60">200</span>
              <span class="text-xs opacity-60">600</span>
              <span class="text-xs opacity-60">1100</span>
              <span class="text-xs opacity-60">1600</span>
              <span class="text-xs opacity-60">2000</span>
            </div>
          </div>

          <!-- Chunk Overlap Slider -->
          <div class="form-control w-full">
            <label class="label">
              <span class="label-text font-semibold">Chunk Overlap: {{ chunkOverlap }} characters</span>
              <span class="label-text-alt text-base-content/60">~{{ Math.round(chunkOverlap / 5) }} words</span>
            </label>
            <p class="text-xs text-base-content/60 mb-2">How much text chunks share to avoid cutting sentences</p>
            <input
              type="range"
              min="0"
              max="500"
              step="25"
              v-model.number="chunkOverlap"
              class="range range-primary w-full"
              @input="onChunkingChange"
            />
            <div class="w-full flex justify-between text-xs px-2 mt-1">
              <span class="text-xs opacity-60">0</span>
              <span class="text-xs opacity-60">125</span>
              <span class="text-xs opacity-60">250</span>
              <span class="text-xs opacity-60">375</span>
              <span class="text-xs opacity-60">500</span>
            </div>
          </div>

          <!-- What This Means -->
          <div class="alert alert-info">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <div class="text-sm">
              <div class="font-bold mb-1">What you'll get with these settings:</div>
              <div>
                <span v-if="chunkSize < 400">
                  <strong>Small chunks ({{ chunkSize }} chars)</strong> = Very precise results, less context per result.<br>
                  <span class="opacity-70">Best for: FAQs, definitions, keyword searches</span>
                </span>
                <span v-else-if="chunkSize > 1200">
                  <strong>Large chunks ({{ chunkSize }} chars)</strong> = More context, but may include extra info.<br>
                  <span class="opacity-70">Best for: Books, reports, long-form content</span>
                </span>
                <span v-else>
                  <strong>Balanced chunks ({{ chunkSize }} chars)</strong> = Good mix of precision and context.<br>
                  <span class="opacity-70">Best for: Most documents - PDFs, articles, manuals</span>
                </span>
              </div>
              <div class="mt-2 opacity-80">
                10-page document -> <strong>~{{ estimatedChunks }} searchable chunks</strong>
              </div>
            </div>
          </div>

          <!-- Warning about re-indexing -->
          <div v-if="chunkingChanged" class="alert alert-warning">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <div class="font-bold">Re-indexing required</div>
              <div class="text-sm">Changing chunking parameters requires re-indexing all documents.</div>
            </div>
          </div>

          <!-- Apply Button -->
          <button
            class="btn btn-primary"
            :disabled="!chunkingChanged || applyingChunking"
            @click="applyChunkingChange"
          >
            <span v-if="applyingChunking" class="loading loading-spinner loading-sm"></span>
            {{ applyingChunking ? 'Applying...' : 'Apply Chunking Changes' }}
          </button>

          <!-- Success/Error Messages -->
          <div v-if="chunkingMessage" class="alert" :class="chunkingMessageType === 'success' ? 'alert-success' : 'alert-error'">
            <div>{{ chunkingMessage }}</div>
          </div>
          </div>
        </div>
      </div>

      <!-- Re-index Collection -->
      <div id="reindex" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <div class="flex items-center gap-2">
            <h3 class="card-title">Re-index Collection</h3>
            <span class="badge badge-sm badge-primary">Per Collection</span>
          </div>
          <p class="text-sm text-base-content/70 mb-4">
            Re-index all documents in the current collection using the collection's current settings.
            Use this after changing chunk size, overlap, or embedding model to apply new settings to existing documents.
          </p>

        <!-- Reindex Status -->
        <div v-if="reindexJob && (reindexJob.status === 'pending' || reindexJob.status === 'running')" class="space-y-4">
          <div class="alert alert-info">
            <span class="loading loading-spinner"></span>
            <div class="flex-1">
              <div class="font-bold">Re-indexing in progress...</div>
              <div class="text-sm">
                {{ reindexJob.current_file || 'Starting...' }}
              </div>
            </div>
          </div>

          <!-- Progress bar -->
          <div class="w-full">
            <div class="flex justify-between text-sm mb-1">
              <span>Progress</span>
              <span>{{ reindexJob.processed_documents || 0 }} / {{ reindexJob.total_documents || '?' }}</span>
            </div>
            <progress
              class="progress progress-primary w-full"
              :value="reindexJob.processed_documents || 0"
              :max="reindexJob.total_documents || 100"
            ></progress>
          </div>
        </div>

        <!-- Completed status (only show if we watched it complete) -->
        <div v-else-if="showReindexResult && reindexJob && reindexJob.status === 'completed'" class="alert alert-success">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div class="font-bold">Re-indexing completed</div>
            <div class="text-sm">
              {{ reindexJob.processed_documents }} documents processed
            </div>
          </div>
        </div>

        <!-- Failed status (only show if we watched it fail) -->
        <div v-else-if="showReindexResult && reindexJob && reindexJob.status === 'failed'" class="alert alert-error">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div class="font-bold">Re-indexing failed</div>
            <div class="text-sm">{{ reindexJob.error || 'Unknown error' }}</div>
          </div>
        </div>

        <!-- Document count info -->
        <div v-if="!reindexJob || (reindexJob.status !== 'pending' && reindexJob.status !== 'running')" class="stats bg-base-300">
          <div class="stat">
            <div class="stat-title">Documents to re-index</div>
            <div class="stat-value text-2xl">{{ collectionStore.currentCollection?.document_count || 0 }}</div>
            <div class="stat-desc">in {{ collectionStore.currentCollection?.name || 'Default' }}</div>
          </div>
        </div>

        <!-- Reindex button -->
        <div class="flex gap-2">
          <button
            class="btn btn-primary"
            :disabled="reindexing || (reindexJob && (reindexJob.status === 'pending' || reindexJob.status === 'running')) || (collectionStore.currentCollection?.document_count || 0) === 0"
            @click="startReindex"
          >
            <span v-if="reindexing" class="loading loading-spinner loading-sm"></span>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {{ reindexing ? 'Starting...' : 'Re-index Collection' }}
          </button>

          <button
            v-if="reindexJob && (reindexJob.status === 'pending' || reindexJob.status === 'running')"
            class="btn btn-ghost btn-sm"
            @click="refreshReindexStatus"
          >
            Refresh Status
          </button>
        </div>

        <!-- Warning -->
        <div class="text-sm text-base-content/70 mt-2">
          <strong>Note:</strong> Re-indexing may take several minutes for large collections.
          The existing index will be cleared and rebuilt from scratch.
          </div>
        </div>
      </div>

      <!-- Index Repair -->
      <div id="index-repair" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <div class="flex items-center gap-2">
            <h3 class="card-title">Index Repair</h3>
            <span class="badge badge-sm badge-warning">Maintenance</span>
          </div>
          <p class="text-sm text-base-content/70 mb-4">
            Diagnose and repair synchronization issues between the FAISS vector index and metadata database.
            Use this if searches return "No metadata found" errors.
          </p>

          <!-- Diagnose Button -->
          <div class="space-y-4">
            <button
              class="btn btn-outline"
              :disabled="diagnosingIndex"
              @click="diagnoseIndex"
            >
              <span v-if="diagnosingIndex" class="loading loading-spinner loading-sm"></span>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              {{ diagnosingIndex ? 'Diagnosing...' : 'Diagnose Index' }}
            </button>

            <!-- Diagnosis Results -->
            <div v-if="indexDiagnosis" class="space-y-3">
              <!-- Status Badge -->
              <div class="flex items-center gap-2">
                <span class="font-semibold">Status:</span>
                <span
                  class="badge"
                  :class="{
                    'badge-success': indexDiagnosis.status === 'synced',
                    'badge-warning': indexDiagnosis.status === 'out_of_sync',
                    'badge-error': ['missing_index', 'missing_metadata', 'corrupted_index', 'corrupted_metadata'].includes(indexDiagnosis.status)
                  }"
                >
                  {{ indexDiagnosis.status.replace(/_/g, ' ') }}
                </span>
              </div>

              <!-- Counts -->
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 bg-base-300 rounded-lg p-4">
                <div class="text-center">
                  <div class="text-xs text-base-content/60">FAISS Vectors</div>
                  <div class="text-lg font-bold">{{ indexDiagnosis.faiss_count?.toLocaleString() || 0 }}</div>
                </div>
                <div class="text-center">
                  <div class="text-xs text-base-content/60">Metadata Chunks</div>
                  <div class="text-lg font-bold">{{ indexDiagnosis.metadata_count?.toLocaleString() || 0 }}</div>
                </div>
                <div class="text-center">
                  <div class="text-xs text-base-content/60">Embeddings</div>
                  <div class="text-lg font-bold">{{ indexDiagnosis.embeddings_count?.toLocaleString() || 0 }}</div>
                </div>
                <div class="text-center">
                  <div class="text-xs text-base-content/60">Documents</div>
                  <div class="text-lg font-bold" :class="{'text-warning': indexDiagnosis.documents_count === 0 && indexDiagnosis.metadata_count > 0}">
                    {{ indexDiagnosis.documents_count?.toLocaleString() || 0 }}
                  </div>
                </div>
              </div>

              <!-- Issues -->
              <div v-if="indexDiagnosis.issues?.length > 0" class="alert alert-warning">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <div class="font-bold">Issues Found:</div>
                  <ul class="text-sm mt-1 list-disc list-inside">
                    <li v-for="issue in indexDiagnosis.issues" :key="issue">{{ issue }}</li>
                  </ul>
                </div>
              </div>

              <!-- Success if synced -->
              <div v-else-if="indexDiagnosis.status === 'synced'" class="alert alert-success">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Index is synchronized - no repair needed!</span>
              </div>

              <!-- Repair Options -->
              <div v-if="indexDiagnosis.status === 'out_of_sync'" class="space-y-3">
                <div class="divider text-sm text-base-content/50">Repair Options</div>

                <div class="flex flex-wrap gap-2">
                  <button
                    class="btn btn-primary"
                    :disabled="repairingIndex"
                    @click="repairIndex('rebuild')"
                  >
                    <span v-if="repairingIndex === 'rebuild'" class="loading loading-spinner loading-sm"></span>
                    <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Rebuild from Metadata
                  </button>

                  <button
                    v-if="indexDiagnosis.faiss_count > indexDiagnosis.metadata_count"
                    class="btn btn-outline"
                    :disabled="repairingIndex"
                    @click="repairIndex('truncate')"
                  >
                    <span v-if="repairingIndex === 'truncate'" class="loading loading-spinner loading-sm"></span>
                    Truncate FAISS (Fast)
                  </button>

                  <button
                    v-if="indexDiagnosis.orphaned_chunks_count > 0 || (indexDiagnosis.documents_count === 0 && indexDiagnosis.metadata_count > 0)"
                    class="btn btn-warning"
                    :disabled="repairingIndex"
                    @click="repairIndex('repair_documents')"
                  >
                    <span v-if="repairingIndex === 'repair_documents'" class="loading loading-spinner loading-sm"></span>
                    <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Repair Documents Table
                  </button>
                </div>

                <div class="text-xs text-base-content/60">
                  <strong>Rebuild:</strong> Re-embeds all text from metadata. Safer but slower.<br>
                  <strong>Truncate:</strong> Removes orphaned FAISS entries. Faster but only works when FAISS has more entries than metadata.<br>
                  <strong>Repair Documents:</strong> Reconstructs missing document records from chunks. Fixes backups with empty documents table.
                </div>
              </div>
            </div>

            <!-- Repair Result -->
            <div v-if="repairMessage" class="alert" :class="repairMessageType === 'success' ? 'alert-success' : 'alert-error'">
              <div>{{ repairMessage }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Embedding Model Selection (Per-Collection) -->
      <div id="embedding-model" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <div class="flex items-center gap-2">
            <h3 class="card-title">Embedding Model</h3>
            <span class="badge badge-sm badge-primary">Per Collection</span>
          </div>
        <p class="text-sm text-base-content/70 mb-4">
          The embedding model converts text to vectors for semantic search.
          Each collection can use a different model. Changes require re-uploading documents.
        </p>

        <div v-if="loadingModels" class="flex justify-center py-4">
          <span class="loading loading-spinner"></span>
        </div>

        <div v-else class="space-y-4">
          <!-- Current Model Display -->
          <div class="alert alert-info">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <div>
              <div class="font-bold">Current Model for {{ collectionStore.currentCollection?.name || 'Default' }}</div>
              <div class="text-sm">{{ collectionStore.currentCollection?.embedding_model || currentConfig.embedding_model }}</div>
            </div>
          </div>

          <!-- Model Selection -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">Select Embedding Model</span>
            </label>
            <select
              v-model="selectedModel"
              class="select select-bordered w-full"
              @change="onModelChange"
            >
              <option v-for="model in availableModels" :key="model.name" :value="model.name">
                {{ model.name }} - {{ model.description }}
              </option>
            </select>
          </div>

          <!-- Model Details -->
          <div v-if="selectedModelDetails" class="grid grid-cols-2 gap-4 p-4 bg-base-300 rounded-lg">
            <div>
              <div class="text-xs text-base-content/60">Dimensions</div>
              <div class="font-semibold">{{ selectedModelDetails.dimensions }}</div>
            </div>
            <div>
              <div class="text-xs text-base-content/60">Size</div>
              <div class="font-semibold">~{{ selectedModelDetails.size_mb }} MB</div>
            </div>
            <div>
              <div class="text-xs text-base-content/60">Speed</div>
              <div class="font-semibold capitalize">{{ selectedModelDetails.speed }}</div>
            </div>
            <div>
              <div class="text-xs text-base-content/60">Quality</div>
              <div class="font-semibold capitalize">{{ selectedModelDetails.quality }}</div>
            </div>
            <div class="col-span-2">
              <div class="text-xs text-base-content/60">Language Support</div>
              <div class="font-semibold">{{ selectedModelDetails.language }}</div>
            </div>
          </div>

          <!-- Warning about re-indexing -->
          <div v-if="modelChanged" class="alert alert-warning">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <div class="font-bold">Re-upload required</div>
              <div class="text-sm">Changing the embedding model requires re-uploading documents to this collection. New uploads will use the new model.</div>
            </div>
          </div>

          <!-- Apply Button -->
          <button
            class="btn btn-primary"
            :disabled="!modelChanged || applyingConfig"
            @click="applyModelChange"
          >
            <span v-if="applyingConfig" class="loading loading-spinner loading-sm"></span>
            {{ applyingConfig ? 'Applying...' : 'Apply Model Change' }}
          </button>

          <!-- Success/Error Messages -->
            <div v-if="configMessage" class="alert" :class="configMessageType === 'success' ? 'alert-success' : 'alert-error'">
              <div>{{ configMessage }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ============ OTHER SETTINGS ============ -->

      <!-- Backups (v3.0 feature) -->
      <div id="backups" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <div class="flex items-center gap-2">
            <h3 class="card-title">Backup & Restore</h3>
            <span class="badge badge-sm badge-info">v3.0</span>
          </div>
          <p class="text-sm text-base-content/70 mb-4">
            Create backups of your collection indexes and documents. Restore from backups to recover data or migrate between systems.
          </p>

          <!-- Create Backup Section -->
          <div class="space-y-4">
            <div class="divider text-sm text-base-content/50">Create Backup</div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">Description (optional)</span>
              </label>
              <input
                v-model="backupDescription"
                type="text"
                placeholder="e.g., Before major update..."
                class="input input-bordered w-full"
              />
            </div>

            <div class="form-control">
              <label class="label cursor-pointer justify-start gap-4">
                <input
                  type="checkbox"
                  class="checkbox checkbox-primary"
                  v-model="backupIncludeDocuments"
                />
                <div>
                  <span class="label-text font-medium">Include source documents</span>
                  <p class="text-xs text-base-content/60">Include uploaded files (PDF, DOCX, etc.) in backup. Increases backup size.</p>
                </div>
              </label>
            </div>

            <button
              class="btn btn-primary"
              :disabled="creatingBackup"
              @click="createBackup"
            >
              <span v-if="creatingBackup" class="loading loading-spinner loading-sm"></span>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
              </svg>
              {{ creatingBackup ? 'Creating...' : 'Create Backup' }}
            </button>

            <div v-if="backupMessage" class="alert" :class="backupMessageType === 'success' ? 'alert-success' : 'alert-error'">
              <div>{{ backupMessage }}</div>
            </div>
          </div>

          <!-- Existing Backups Section -->
          <div class="space-y-4 mt-6">
            <div class="divider text-sm text-base-content/50">
              Existing Backups
              <button class="btn btn-xs btn-ghost ml-2" @click="loadBackups" :disabled="loadingBackups">
                <svg class="w-4 h-4" :class="{ 'animate-spin': loadingBackups }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>

            <div v-if="loadingBackups" class="flex justify-center py-4">
              <span class="loading loading-spinner"></span>
            </div>

            <div v-else-if="backups.length === 0" class="text-center py-4 text-base-content/50">
              <svg class="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
              <p>No backups yet</p>
            </div>

            <div v-else class="space-y-3">
              <div v-for="backup in backups" :key="backup.filename" class="bg-base-300 rounded-lg p-4">
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <div class="font-medium text-sm">{{ backup.collection_id || 'default' }}</div>
                    <div class="text-xs text-base-content/60 mt-1">
                      {{ formatBackupDate(backup.created_at) }} · {{ backup.size_mb?.toFixed(2) || '?' }} MB
                    </div>
                    <div v-if="backup.description" class="text-xs text-base-content/70 mt-1 italic">
                      "{{ backup.description }}"
                    </div>
                    <div class="flex flex-wrap gap-1 mt-2">
                      <span v-if="backup.includes_documents" class="badge badge-xs badge-success">Includes docs</span>
                      <span v-else class="badge badge-xs badge-ghost">Index only</span>
                      <span class="badge badge-xs badge-outline">{{ backup.storage_type || 'json' }}</span>
                    </div>
                  </div>
                  <div class="flex gap-1">
                    <button
                      class="btn btn-xs btn-ghost"
                      title="Download"
                      @click="downloadBackup(backup.filename)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </button>
                    <button
                      class="btn btn-xs btn-primary"
                      title="Restore"
                      :disabled="restoringBackup === backup.filename"
                      @click="confirmRestore(backup)"
                    >
                      <span v-if="restoringBackup === backup.filename" class="loading loading-spinner loading-xs"></span>
                      <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </button>
                    <button
                      class="btn btn-xs btn-ghost text-error"
                      title="Delete"
                      :disabled="deletingBackup === backup.filename"
                      @click="confirmDeleteBackup(backup)"
                    >
                      <span v-if="deletingBackup === backup.filename" class="loading loading-spinner loading-xs"></span>
                      <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Restore Confirmation Modal -->
      <dialog ref="restoreModal" class="modal">
        <div class="modal-box">
          <h3 class="font-bold text-lg">Restore Backup</h3>
          <p class="py-4">
            Restore from backup: <strong>{{ selectedBackup?.filename }}</strong>
          </p>
          <div class="form-control mb-4">
            <label class="label cursor-pointer justify-start gap-4">
              <input
                type="checkbox"
                class="checkbox checkbox-warning"
                v-model="restoreOverwrite"
              />
              <div>
                <span class="label-text font-medium">Overwrite existing data</span>
                <p class="text-xs text-base-content/60">Replace current collection data with backup contents</p>
              </div>
            </label>
          </div>
          <div v-if="restoreOverwrite" class="alert alert-warning mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span class="text-sm">This will replace all existing data in the collection!</span>
          </div>
          <div class="modal-action">
            <button class="btn" @click="closeRestoreModal">Cancel</button>
            <button class="btn btn-primary" @click="restoreBackup" :disabled="restoringBackup">
              <span v-if="restoringBackup" class="loading loading-spinner loading-sm"></span>
              {{ restoringBackup ? 'Restoring...' : 'Restore' }}
            </button>
          </div>
        </div>
        <form method="dialog" class="modal-backdrop">
          <button @click="closeRestoreModal">close</button>
        </form>
      </dialog>

      <!-- Delete Backup Confirmation Modal -->
      <dialog ref="deleteBackupModal" class="modal">
        <div class="modal-box">
          <h3 class="font-bold text-lg text-error">Delete Backup</h3>
          <p class="py-4">
            Are you sure you want to delete this backup?<br>
            <strong>{{ selectedBackup?.filename }}</strong>
          </p>
          <p class="text-sm text-base-content/70">This action cannot be undone.</p>
          <div class="modal-action">
            <button class="btn" @click="closeDeleteBackupModal">Cancel</button>
            <button class="btn btn-error" @click="deleteBackup" :disabled="deletingBackup">
              <span v-if="deletingBackup" class="loading loading-spinner loading-sm"></span>
              {{ deletingBackup ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>
        <form method="dialog" class="modal-backdrop">
          <button @click="closeDeleteBackupModal">close</button>
        </form>
      </dialog>

      <!-- API Documentation -->
      <div id="api-docs" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <h3 class="card-title">API Documentation</h3>
          <p class="text-sm">Access the interactive API documentation to explore all endpoints.</p>
          <div class="card-actions">
            <a href="/docs" target="_blank" class="btn btn-primary btn-sm">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
              Open API Docs
            </a>
          </div>
        </div>
      </div>

      <!-- About -->
      <div id="about" class="card bg-base-200 scroll-mt-36">
        <div class="card-body">
          <h3 class="card-title">About Asymptote</h3>
          <div class="prose prose-sm max-w-none">
            <p>
              <strong>Asymptote</strong> is a self-hosted semantic search engine for documents.
              Upload documents (PDF, TXT, DOCX, CSV, Markdown, JSON), search their contents using natural language,
              and get back relevant passages with direct links to the source.
            </p>
            <p class="text-sm italic">
              Why "Asymptote"? In mathematics, an asymptote is a line that a curve approaches but never
              quite reaches. Like semantic search continuously approaching perfect understanding of your
              documents - getting closer with every query, but always refining, always learning.
            </p>
            <div class="mt-4">
              <h4 class="font-semibold mb-2">Technology Stack:</h4>
              <ul class="text-sm space-y-1">
                <li><strong>Backend:</strong> FastAPI (Python)</li>
                <li><strong>Frontend:</strong> Vue 3 + Vite + Tailwind CSS + DaisyUI</li>
                <li><strong>Embeddings:</strong> sentence-transformers (all-MiniLM-L6-v2)</li>
                <li><strong>Vector Search:</strong> FAISS (Facebook AI Similarity Search)</li>
                <li><strong>Document Processing:</strong> pypdf, pdfplumber, python-docx, pandas</li>
                <li><strong>Metadata Storage:</strong> SQLite or JSON</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Danger Zone -->
      <div id="danger-zone" class="card bg-error/10 border border-error scroll-mt-36">
        <div class="card-body">
          <h3 class="card-title text-error">Danger Zone</h3>
        <p class="text-sm">Permanently delete all documents, indexes, and data. This action cannot be undone.</p>

        <!-- Success Alert -->
        <div v-if="clearSuccess" class="alert alert-success">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>All data has been cleared successfully!</span>
        </div>

        <!-- Error Alert -->
        <div v-if="clearError" class="alert alert-error">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ clearError }}</span>
        </div>

        <div class="card-actions justify-end">
          <button class="btn btn-error" @click="confirmClearAll" :disabled="clearing">
            <svg v-if="!clearing" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
            <span v-if="clearing" class="loading loading-spinner"></span>
            {{ clearing ? 'Clearing...' : 'Clear All Data' }}
          </button>
        </div>
      </div>
      </div>

      <!-- Clear All Confirmation Modal -->
      <dialog ref="clearModal" class="modal">
        <div class="modal-box">
          <h3 class="font-bold text-lg text-error">Clear All Data</h3>
          <p class="py-4">
            This will <strong>permanently delete</strong>:
          </p>
          <ul class="list-disc list-inside space-y-1 text-sm mb-4">
            <li>All uploaded documents</li>
            <li>All vector embeddings and indexes</li>
            <li>All metadata (documents, chunks, search history)</li>
          </ul>
          <p class="text-sm text-error font-semibold">
            This action cannot be undone. Are you absolutely sure?
          </p>
          <div class="modal-action">
            <button class="btn" @click="closeClearModal" :disabled="clearing">Cancel</button>
            <button class="btn btn-error" @click="clearAllData" :disabled="clearing">
              <span v-if="clearing" class="loading loading-spinner"></span>
              {{ clearing ? 'Clearing...' : 'Yes, Delete Everything' }}
            </button>
          </div>
        </div>
        <form method="dialog" class="modal-backdrop">
          <button @click="closeClearModal">close</button>
        </form>
      </dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'
import { useCollectionStore } from '../stores/collectionStore'

const emit = defineEmits(['data-cleared', 'stats-updated'])

const collectionStore = useCollectionStore()

// Table of contents navigation
const activeSection = ref('collection-info')
const sectionIds = [
  'ai-integration',
  'search-config',
  'metadata-storage',
  'appearance',
  'collection-info',
  'text-chunking',
  'reindex',
  'index-repair',
  'embedding-model',
  'backups',
  'api-docs',
  'about',
  'danger-zone'
]

const scrollToSection = (sectionId) => {
  const element = document.getElementById(sectionId)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeSection.value = sectionId
  }
}

const handleScroll = () => {
  // Find which section is currently in view
  const scrollPosition = window.scrollY + 200 // Offset for header

  for (let i = sectionIds.length - 1; i >= 0; i--) {
    const element = document.getElementById(sectionIds[i])
    if (element && element.offsetTop <= scrollPosition) {
      activeSection.value = sectionIds[i]
      break
    }
  }
}

// System info
const loading = ref(false)
const health = ref({})
const defaultTopK = ref(parseInt(localStorage.getItem('asymptote_default_top_k')) || 10)
const selectedTheme = ref('light')

// Save default top_k to localStorage
const saveDefaultTopK = () => {
  const value = Math.max(1, Math.min(50, defaultTopK.value || 10))
  defaultTopK.value = value
  localStorage.setItem('asymptote_default_top_k', value.toString())
}
const clearing = ref(false)
const clearSuccess = ref(false)
const clearError = ref('')
const clearModal = ref(null)

// AI integration state
const apiKey = ref('')
const showKey = ref(false)
const validatingKey = ref(false)
const apiKeyStatus = ref('')
const apiKeyDirty = ref(false)
const hasStoredKey = ref(false)
const validationError = ref('')
const aiSettings = ref({
  provider: 'anthropic',
  rerank: false,
  synthesize: false,
})

// Ollama state
const checkingOllama = ref(false)
const ollamaAvailable = ref(false)
const ollamaModels = ref([])
const selectedOllamaModel = ref('')

// Config state
const loadingModels = ref(false)
const currentConfig = ref({
  embedding_model: '',
  chunk_size: 600,
  chunk_overlap: 100,
  metadata_storage: 'json',
})
const availableModels = ref([])
const selectedModel = ref('')
const chunkSize = ref(600)
const chunkOverlap = ref(100)
const selectedStorage = ref('json')

// UI State
const applyingConfig = ref(false)
const applyingChunking = ref(false)
const applyingStorage = ref(false)
const configMessage = ref('')
const configMessageType = ref('success')
const chunkingMessage = ref('')
const chunkingMessageType = ref('success')
const storageMessage = ref('')
const storageMessageType = ref('success')

// Reindex state
const reindexing = ref(false)
const reindexJob = ref(null)
const reindexPollInterval = ref(null)
const showReindexResult = ref(false) // Only show completed/failed status when we watched it complete

// Backup state (v3.0)
const backups = ref([])
const loadingBackups = ref(false)
const creatingBackup = ref(false)
const restoringBackup = ref(null) // filename of backup being restored
const deletingBackup = ref(null) // filename of backup being deleted
const backupDescription = ref('')
const backupIncludeDocuments = ref(true)
const backupMessage = ref('')
const backupMessageType = ref('success')
const selectedBackup = ref(null)
const restoreOverwrite = ref(false)
const restoreModal = ref(null)
const deleteBackupModal = ref(null)

// Index repair state
const diagnosingIndex = ref(false)
const indexDiagnosis = ref(null)
const repairingIndex = ref(null) // 'rebuild' or 'truncate' when repairing
const repairMessage = ref('')
const repairMessageType = ref('success')


// Computed
const hasAnthropicKey = computed(() => !!localStorage.getItem('ai_api_key_anthropic'))
const hasOpenAIKey = computed(() => !!localStorage.getItem('ai_api_key_openai'))
const hasBothKeys = computed(() => hasAnthropicKey.value && hasOpenAIKey.value)

const estimatedCost = computed(() => {
  let cost = 0
  const multiplier = hasBothKeys.value ? 2 : 1
  if (aiSettings.value.rerank) cost += 0.0005 * multiplier
  if (aiSettings.value.synthesize) cost += 0.015 * multiplier
  return cost.toFixed(4)
})

const selectedModelDetails = computed(() => {
  return availableModels.value.find(m => m.name === selectedModel.value)
})

const modelChanged = computed(() => {
  const currentModel = collectionStore.currentCollection?.embedding_model || currentConfig.value.embedding_model
  return selectedModel.value !== currentModel
})

const chunkingChanged = computed(() => {
  const currentChunkSize = collectionStore.currentCollection?.chunk_size || currentConfig.value.chunk_size
  const currentChunkOverlap = collectionStore.currentCollection?.chunk_overlap || currentConfig.value.chunk_overlap
  return chunkSize.value !== currentChunkSize || chunkOverlap.value !== currentChunkOverlap
})

const storageChanged = computed(() => {
  return selectedStorage.value !== currentConfig.value.metadata_storage
})

const estimatedChunks = computed(() => {
  const avgDocSize = 10 * 5000 // 10 pages * 5000 chars/page
  const effectiveChunkSize = chunkSize.value - chunkOverlap.value
  return Math.ceil(avgDocSize / effectiveChunkSize)
})

// AI Methods
const setProvider = (provider) => {
  aiSettings.value.provider = provider
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
  loadProviderKey()
}

const validateAndSaveKey = async () => {
  if (!apiKey.value.trim()) return
  validatingKey.value = true
  apiKeyStatus.value = ''
  validationError.value = ''

  try {
    const response = await axios.post('/api/ai/validate-key', null, {
      headers: {
        'X-AI-Key': apiKey.value.trim(),
        'X-AI-Provider': aiSettings.value.provider,
      }
    })
    if (response.data.valid) {
      const keyName = `ai_api_key_${aiSettings.value.provider}`
      localStorage.setItem(keyName, apiKey.value.trim())
      localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
      hasStoredKey.value = true
      apiKeyDirty.value = false
      apiKeyStatus.value = 'valid'
      validationError.value = ''
    } else {
      apiKeyStatus.value = 'invalid'
      if (response.data.error) {
        validationError.value = response.data.error
      } else {
        validationError.value = 'The API key was rejected. Please check it and try again.'
      }
    }
  } catch (err) {
    apiKeyStatus.value = 'error'
    validationError.value = err.response?.data?.detail || 'Network error. Check your connection and try again.'
  } finally {
    validatingKey.value = false
  }
}

const removeKey = () => {
  const keyName = `ai_api_key_${aiSettings.value.provider}`
  localStorage.removeItem(keyName)
  apiKey.value = ''
  hasStoredKey.value = false
  apiKeyStatus.value = ''
  apiKeyDirty.value = false

  const hasAnthropicKey = localStorage.getItem('ai_api_key_anthropic')
  const hasOpenAIKey = localStorage.getItem('ai_api_key_openai')
  if (!hasAnthropicKey && !hasOpenAIKey) {
    aiSettings.value = { ...aiSettings.value, rerank: false, synthesize: false }
  }
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
}

const toggleAI = (feature) => {
  aiSettings.value[feature] = !aiSettings.value[feature]
  localStorage.setItem('ai_settings', JSON.stringify(aiSettings.value))
}

const loadProviderKey = () => {
  const keyName = `ai_api_key_${aiSettings.value.provider}`
  const storedKey = localStorage.getItem(keyName)
  if (storedKey) {
    apiKey.value = storedKey
    hasStoredKey.value = true
    apiKeyDirty.value = false
    apiKeyStatus.value = 'saved'
  } else {
    apiKey.value = ''
    hasStoredKey.value = false
    apiKeyDirty.value = false
    apiKeyStatus.value = ''
  }
}

const loadAISettings = () => {
  const storedSettings = localStorage.getItem('ai_settings')
  if (storedSettings) {
    try {
      const parsed = JSON.parse(storedSettings)
      aiSettings.value = {
        provider: parsed.provider || 'anthropic',
        rerank: !!parsed.rerank,
        synthesize: !!parsed.synthesize,
      }
    } catch { /* use defaults */ }
  }
  loadProviderKey()
}

// Health/Settings Methods
const loadHealth = async () => {
  loading.value = true
  try {
    const collectionId = collectionStore.currentCollectionId
    const response = await axios.get(`/health?collection_id=${collectionId}`)
    health.value = response.data
  } catch (error) {
    console.error('Error loading health:', error)
  } finally {
    loading.value = false
  }
}

// Check if using system theme (no manual override)
const isUsingSystemTheme = ref(!localStorage.getItem('theme'))

const applyTheme = () => {
  document.documentElement.setAttribute('data-theme', selectedTheme.value)
  localStorage.setItem('theme', selectedTheme.value)
  isUsingSystemTheme.value = false
  // Notify App.vue of theme change
  window.dispatchEvent(new CustomEvent('theme-changed'))
}

const resetToSystemTheme = () => {
  localStorage.removeItem('theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  selectedTheme.value = prefersDark ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', selectedTheme.value)
  isUsingSystemTheme.value = true
  // Notify App.vue of theme change
  window.dispatchEvent(new CustomEvent('theme-changed'))
}

const confirmClearAll = () => {
  clearSuccess.value = false
  clearError.value = ''
  clearModal.value?.showModal()
}

const closeClearModal = () => {
  if (!clearing.value) {
    clearModal.value?.close()
  }
}

const clearAllData = async () => {
  clearing.value = true
  clearError.value = ''
  clearSuccess.value = false

  try {
    const collectionId = collectionStore.currentCollectionId
    const docsResponse = await axios.get(`/documents?collection_id=${collectionId}`)
    const documents = docsResponse.data.documents || []

    for (const doc of documents) {
      await axios.delete(`/documents/${doc.document_id}?collection_id=${collectionId}`)
    }

    clearSuccess.value = true
    clearModal.value?.close()
    await loadHealth()
    emit('data-cleared')

    setTimeout(() => {
      clearSuccess.value = false
    }, 5000)
  } catch (error) {
    clearError.value = error.response?.data?.detail || 'Failed to clear data. Please try again.'
  } finally {
    clearing.value = false
  }
}

// Ollama Methods
const checkOllamaStatus = async () => {
  checkingOllama.value = true
  try {
    const response = await axios.get('/api/ollama/status')
    ollamaAvailable.value = response.data.available
    ollamaModels.value = response.data.models || []

    const savedModel = localStorage.getItem('ollama_model')
    if (savedModel && ollamaModels.value.find(m => m.name === savedModel)) {
      selectedOllamaModel.value = savedModel
    } else if (ollamaModels.value.length > 0) {
      selectedOllamaModel.value = ollamaModels.value[0].name
      localStorage.setItem('ollama_model', selectedOllamaModel.value)
    }
  } catch (error) {
    console.error('Failed to check Ollama status:', error)
    ollamaAvailable.value = false
    ollamaModels.value = []
  } finally {
    checkingOllama.value = false
  }
}

const saveOllamaModel = () => {
  localStorage.setItem('ollama_model', selectedOllamaModel.value)
}

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// Config Methods
const loadConfig = async () => {
  try {
    // Load global config
    const response = await axios.get('/api/config')
    currentConfig.value = response.data
    selectedStorage.value = response.data.metadata_storage

    // Load collection-specific settings
    const collection = collectionStore.currentCollection
    if (collection) {
      chunkSize.value = collection.chunk_size || response.data.chunk_size
      chunkOverlap.value = collection.chunk_overlap || response.data.chunk_overlap
      selectedModel.value = collection.embedding_model || response.data.embedding_model
    } else {
      chunkSize.value = response.data.chunk_size
      chunkOverlap.value = response.data.chunk_overlap
      selectedModel.value = response.data.embedding_model
    }
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

const loadAvailableModels = async () => {
  loadingModels.value = true
  try {
    const response = await axios.get('/api/config/embedding-models')
    availableModels.value = response.data.models
  } catch (error) {
    console.error('Failed to load models:', error)
  } finally {
    loadingModels.value = false
  }
}

const onModelChange = () => {
  configMessage.value = ''
}

const onChunkingChange = () => {
  chunkingMessage.value = ''
}

const onStorageChange = () => {
  storageMessage.value = ''
}

const applyModelChange = async () => {
  applyingConfig.value = true
  configMessage.value = ''

  try {
    // Update collection-specific embedding model
    const collectionId = collectionStore.currentCollectionId
    await collectionStore.updateCollection(collectionId, {
      embedding_model: selectedModel.value
    })

    configMessageType.value = 'success'
    configMessage.value = 'Collection embedding model updated. Re-upload documents to apply the new model.'

    // Reload collections to get updated settings
    await collectionStore.loadCollections()
    await loadConfig()
  } catch (error) {
    configMessageType.value = 'error'
    configMessage.value = 'Error: ' + (error.response?.data?.detail || error.message)
  } finally {
    applyingConfig.value = false
  }
}

const applyChunkingChange = async () => {
  applyingChunking.value = true
  chunkingMessage.value = ''

  try {
    // Update collection-specific settings
    const collectionId = collectionStore.currentCollectionId
    await collectionStore.updateCollection(collectionId, {
      chunk_size: chunkSize.value,
      chunk_overlap: chunkOverlap.value
    })

    chunkingMessageType.value = 'success'
    chunkingMessage.value = 'Collection settings updated. Re-upload documents to apply new chunking settings.'

    // Reload collections to get updated settings
    await collectionStore.loadCollections()
    await loadConfig()
  } catch (error) {
    chunkingMessageType.value = 'error'
    chunkingMessage.value = 'Error: ' + (error.response?.data?.detail || error.message)
  } finally {
    applyingChunking.value = false
  }
}

const applyStorageChange = async () => {
  applyingStorage.value = true
  storageMessage.value = ''

  try {
    const response = await axios.post('/api/config', {
      metadata_storage: selectedStorage.value
    })

    if (response.data.success) {
      storageMessageType.value = 'success'
      if (response.data.requires_restart) {
        storageMessage.value = 'Configuration updated. Please restart the server. You will need to re-upload documents to populate the new storage.'
      } else {
        storageMessage.value = 'Configuration updated successfully.'
      }
      await loadConfig()
    } else {
      storageMessageType.value = 'error'
      storageMessage.value = 'Failed to update configuration: ' + (response.data.errors?.join(', ') || 'Unknown error')
    }
  } catch (error) {
    storageMessageType.value = 'error'
    storageMessage.value = 'Error: ' + (error.response?.data?.detail || error.message)
  } finally {
    applyingStorage.value = false
  }
}

// Reindex Methods
const startReindex = async () => {
  reindexing.value = true
  showReindexResult.value = true // We're watching this job, so show result when done
  try {
    const collectionId = collectionStore.currentCollectionId
    const response = await axios.post(`/api/collections/${collectionId}/reindex`)
    reindexJob.value = {
      id: response.data.job_id,
      status: 'pending',
      collection_id: collectionId
    }
    // Start polling for status
    startReindexPolling()
  } catch (error) {
    console.error('Failed to start reindex:', error)
    reindexJob.value = {
      status: 'failed',
      error: error.response?.data?.detail || error.message
    }
  } finally {
    reindexing.value = false
  }
}

const refreshReindexStatus = async () => {
  try {
    const response = await axios.get('/api/reindex/status')
    reindexJob.value = response.data

    // If completed or failed, stop polling and refresh everything
    if (response.data.status === 'completed' || response.data.status === 'failed') {
      stopReindexPolling()
      if (response.data.status === 'completed') {
        // Refresh health stats
        await loadHealth()
        // Reload collections to update document counts
        await collectionStore.loadCollections()
        // Emit event to refresh parent stats (header)
        emit('stats-updated')
      }
    }
  } catch (error) {
    // No active job
    if (error.response?.status === 404) {
      reindexJob.value = null
    }
  }
}

const startReindexPolling = () => {
  stopReindexPolling() // Clear any existing interval
  reindexPollInterval.value = setInterval(refreshReindexStatus, 2000)
}

const stopReindexPolling = () => {
  if (reindexPollInterval.value) {
    clearInterval(reindexPollInterval.value)
    reindexPollInterval.value = null
  }
}

// Backup Methods (v3.0)
const loadBackups = async () => {
  loadingBackups.value = true
  try {
    const response = await axios.get('/api/backups')
    backups.value = response.data.backups || []
  } catch (error) {
    console.error('Failed to load backups:', error)
    backups.value = []
  } finally {
    loadingBackups.value = false
  }
}

const createBackup = async () => {
  creatingBackup.value = true
  backupMessage.value = ''

  try {
    const collectionId = collectionStore.currentCollectionId
    const response = await axios.post('/api/backups', null, {
      params: {
        collection_id: collectionId,
        description: backupDescription.value,
        include_documents: backupIncludeDocuments.value
      }
    })

    backupMessageType.value = 'success'
    backupMessage.value = `Backup created: ${response.data.filename} (${response.data.size_mb?.toFixed(2)} MB)`
    backupDescription.value = ''

    // Refresh backup list
    await loadBackups()
  } catch (error) {
    backupMessageType.value = 'error'
    backupMessage.value = error.response?.data?.detail || 'Failed to create backup'
  } finally {
    creatingBackup.value = false
  }
}

const confirmRestore = (backup) => {
  selectedBackup.value = backup
  restoreOverwrite.value = false
  restoreModal.value?.showModal()
}

const closeRestoreModal = () => {
  restoreModal.value?.close()
  selectedBackup.value = null
}

const restoreBackup = async () => {
  if (!selectedBackup.value) return

  restoringBackup.value = selectedBackup.value.filename

  try {
    const response = await axios.post(`/api/backups/${selectedBackup.value.filename}/restore`, null, {
      params: {
        overwrite: restoreOverwrite.value
      }
    })

    backupMessageType.value = 'success'
    backupMessage.value = `Restored ${response.data.files_restored?.indexes || 0} index files and ${response.data.files_restored?.documents || 0} documents`

    closeRestoreModal()

    // Refresh health stats and collections
    await loadHealth()
    await collectionStore.loadCollections()
    emit('stats-updated')
  } catch (error) {
    backupMessageType.value = 'error'
    backupMessage.value = error.response?.data?.detail || 'Failed to restore backup'
  } finally {
    restoringBackup.value = null
  }
}

const confirmDeleteBackup = (backup) => {
  selectedBackup.value = backup
  deleteBackupModal.value?.showModal()
}

const closeDeleteBackupModal = () => {
  deleteBackupModal.value?.close()
  selectedBackup.value = null
}

const deleteBackup = async () => {
  if (!selectedBackup.value) return

  deletingBackup.value = selectedBackup.value.filename

  try {
    await axios.delete(`/api/backups/${selectedBackup.value.filename}`)

    closeDeleteBackupModal()
    await loadBackups()
  } catch (error) {
    backupMessageType.value = 'error'
    backupMessage.value = error.response?.data?.detail || 'Failed to delete backup'
  } finally {
    deletingBackup.value = null
  }
}

const downloadBackup = (filename) => {
  window.open(`/api/backups/${filename}/download`, '_blank')
}

const formatBackupDate = (isoString) => {
  if (!isoString) return 'Unknown'
  try {
    const date = new Date(isoString)
    return date.toLocaleString()
  } catch {
    return isoString
  }
}

// Index Repair Methods
const diagnoseIndex = async () => {
  diagnosingIndex.value = true
  indexDiagnosis.value = null
  repairMessage.value = ''

  try {
    const collectionId = collectionStore.currentCollectionId
    const response = await axios.get(`/api/index/diagnose?collection_id=${collectionId}`)
    indexDiagnosis.value = response.data
  } catch (error) {
    console.error('Failed to diagnose index:', error)
    repairMessageType.value = 'error'
    repairMessage.value = error.response?.data?.detail || 'Failed to diagnose index'
  } finally {
    diagnosingIndex.value = false
  }
}

const repairIndex = async (method) => {
  repairingIndex.value = method
  repairMessage.value = ''

  try {
    const collectionId = collectionStore.currentCollectionId
    const response = await axios.post(`/api/index/repair?collection_id=${collectionId}&method=${method}`)

    if (response.data.success) {
      repairMessageType.value = 'success'
      repairMessage.value = response.data.message || 'Index repaired successfully!'

      // Re-diagnose to show updated status
      await diagnoseIndex()

      // Refresh health stats
      await loadHealth()
      emit('stats-updated')
    } else {
      repairMessageType.value = 'error'
      repairMessage.value = response.data.error || 'Repair failed'
    }
  } catch (error) {
    console.error('Failed to repair index:', error)
    repairMessageType.value = 'error'
    repairMessage.value = error.response?.data?.detail || 'Failed to repair index'
  } finally {
    repairingIndex.value = null
  }
}

// Watch for collection changes
watch(() => collectionStore.currentCollectionId, async () => {
  await loadHealth()
  await loadConfig()
  // Reset reindex result display when switching collections
  showReindexResult.value = false
  // Check for any active reindex job
  await checkForActiveReindexJob()
})

// Check for active reindex job (only shows result alert if job is currently running)
const checkForActiveReindexJob = async () => {
  try {
    const response = await axios.get('/api/reindex/status')
    reindexJob.value = response.data
    // Only show result and start polling if job is actively running
    if (response.data.status === 'pending' || response.data.status === 'running') {
      showReindexResult.value = true
      startReindexPolling()
    }
  } catch (error) {
    // No active job - that's fine
    if (error.response?.status === 404) {
      reindexJob.value = null
    }
  }
}

// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadHealth(),
    loadConfig(),
    loadAvailableModels(),
    loadBackups()
  ])
  loadAISettings()
  checkOllamaStatus()

  // Check for any active reindex job (only shows alert if job is currently running)
  await checkForActiveReindexJob()

  // Load theme preference (check system if no saved preference)
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    selectedTheme.value = savedTheme
    isUsingSystemTheme.value = false
  } else {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    selectedTheme.value = prefersDark ? 'dark' : 'light'
    isUsingSystemTheme.value = true
  }

  // Add scroll listener for table of contents
  window.addEventListener('scroll', handleScroll)
  handleScroll() // Initialize active section
})

// Cleanup on unmount
onUnmounted(() => {
  stopReindexPolling()
  window.removeEventListener('scroll', handleScroll)
})
</script>
