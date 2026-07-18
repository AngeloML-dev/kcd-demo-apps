/**
 * KCD Peru 2026 — Vue 3 App
 * Estado reactivo + SSE handler + acciones
 */
import { createApp, ref, reactive, computed, watch, onMounted, nextTick } from 'vue';

// ── Constants ──
const EXAMPLES = [
  'Despliega una API de usuarios con PostgreSQL en staging con 3 replicas',
  'Necesito un microservicio de pagos en produccion con 2 replicas',
  'Crea un servicio de notificaciones en staging',
];
const OWNER_OPTIONS = ['backend-team', 'platform-team', 'data-team', 'frontend-team'];
const FLOW_NODES = [
  { id: 'ollama', label: 'Ollama' },
  { id: 'backstage', label: 'Backstage' },
  { id: 'github', label: 'GitHub' },
  { id: 'argocd', label: 'ArgoCD' },
  { id: 'pods', label: 'Pods' },
];
const STEP_IDS = ['ollama', 'backstage', 'github', 'argocd', 'pods'];
const CONFETTI_COLORS = ['#4ade80', '#38bdf8', '#a78bfa', '#fbbf24', '#f472b6'];

// ── Markdown renderer (code blocks → terminal) ──
function renderMarkdown(text) {
  // Escape HTML first
  const esc = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Replace fenced code blocks with terminal widget
  const rendered = esc.replace(/```(\w*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    const label = lang || 'shell';
    const trimmed = code.replace(/\n$/, '');
    return `<div class="terminal-block"><div class="terminal-header"><span class="terminal-dot red"></span><span class="terminal-dot yellow"></span><span class="terminal-dot green"></span><span class="terminal-label">${label}</span></div><pre class="terminal-body"><code>${trimmed}</code></pre></div>`;
  });
  // Wrap remaining plain text lines in paragraphs (skip if already wrapped in a div)
  return rendered;
}

function makeSteps() {
  return STEP_IDS.map((id, i) => ({
    id, num: i + 1, status: 'hidden', msg: '', detail: '', prUrl: '', pods: [],
  }));
}

// ── App ──
const app = createApp({
  setup() {
    // State
    const services = reactive({ ollama: false, backstage: false, github: false, argocd: false, kubectl: false });
    const ollamaModel = ref('');
    const prompt = ref('');
    const isDeploying = ref(false);
    const messages = reactive([]);
    const showFlow = ref(false);
    const flowStates = reactive({ ollama: 'idle', backstage: 'idle', github: 'idle', argocd: 'idle', pods: 'idle' });
    const intent = ref(null);
    const intentMode = ref('hidden');
    const intentTitle = ref('Intent parseado por Ollama');
    const missingFields = ref([]);
    const missingValues = reactive({});
    const missingErrors = reactive({});
    const editForm = reactive({ service_name: '', environment: 'staging', replicas: 1, port: 8080, owner: 'backend-team' });
    const doneResult = ref(null);
    const timerVisible = ref(false);
    const timerDisplay = ref('0.0s');
    const steps = reactive(makeSteps());

    // Refs
    const particlesRef = ref(null);
    const doneRef = ref(null);
    const chatArea = ref(null);
    const promptInput = ref(null);

    // Auto-scroll chat area to bottom
    function scrollToBottom() {
      nextTick(() => {
        if (chatArea.value) chatArea.value.scrollTop = chatArea.value.scrollHeight;
      });
    }

    // Internal
    let currentES = null;
    let timerInterval = null;
    let timerStart = 0;

    // ── Computed ──
    const visibleSteps = computed(() => steps.filter(s => s.status !== 'hidden'));

    const intentFields = computed(() => {
      if (!intent.value) return [];
      const d = intent.value;
      return [
        { label: 'Servicio', value: d.service_name },
        { label: 'Ambiente', value: d.environment },
        { label: 'Replicas', value: d.replicas },
        { label: 'Puerto', value: d.port },
        { label: 'Base de datos', value: d.has_database ? d.db_type : 'No' },
        { label: 'Owner', value: d.owner || 'backend-team' },
      ];
    });

    function flowArrowLit(index) {
      const st = flowStates[FLOW_NODES[index].id];
      return st === 'completed' || st === 'warning' || st === 'skipped';
    }

    // ── Timer ──
    function startTimer() {
      timerStart = Date.now();
      timerVisible.value = true;
      timerInterval = setInterval(() => {
        timerDisplay.value = ((Date.now() - timerStart) / 1000).toFixed(1) + 's';
      }, 100);
    }
    function stopTimer() {
      clearInterval(timerInterval);
      setTimeout(() => { timerVisible.value = false; }, 3000);
    }

    // ── Reset ──
    function resetState() {
      const fresh = makeSteps();
      steps.forEach((s, i) => Object.assign(s, fresh[i]));
      Object.keys(flowStates).forEach(k => flowStates[k] = 'idle');
      showFlow.value = false;
      intent.value = null;
      intentMode.value = 'hidden';
      intentTitle.value = 'Intent parseado por Ollama';
      doneResult.value = null;
      missingFields.value = [];
      Object.keys(missingValues).forEach(k => delete missingValues[k]);
      Object.keys(missingErrors).forEach(k => delete missingErrors[k]);
    }

    // ── SSE Event Handler ──
    function handleEvent(event, data, fromGet) {
      switch (event) {
        case 'services':
          Object.assign(services, data);
          break;

        case 'chat':
          messages.push({ type: 'agent', text: data.message });
          showFlow.value = false;
          steps.forEach(s => s.status = 'hidden');
          isDeploying.value = false;
          stopTimer();
          scrollToBottom();
          break;

        case 'missing_fields':
          intent.value = data.intent;
          missingFields.value = data.fields;
          data.fields.forEach(f => { missingValues[f.field] = ''; missingErrors[f.field] = false; });
          intentMode.value = 'missing';
          showFlow.value = false;
          steps.forEach(s => s.status = 'hidden');
          messages.push({ type: 'agent', text: 'Necesito algunos datos mas para continuar con el deployment.' });
          isDeploying.value = false;
          stopTimer();
          scrollToBottom();
          break;

        case 'intent':
          intent.value = data;
          if (fromGet) {
            intentMode.value = 'confirm';
            showFlow.value = false;
            steps.forEach(s => s.status = 'hidden');
            isDeploying.value = false;
            stopTimer();
          }
          scrollToBottom();
          break;

        case 'step_start': {
          const step = steps.find(s => s.id === data.id);
          if (step) { step.status = 'running'; step.msg = data.msg; }
          flowStates[data.id] = 'active';
          scrollToBottom();
          break;
        }
        case 'step_done': {
          const step = steps.find(s => s.id === data.id);
          if (step) {
            step.status = 'done';
            if (data.pr_url) step.prUrl = data.pr_url;
            if (data.pods) step.pods = data.pods;
          }
          flowStates[data.id] = 'completed';
          scrollToBottom();
          break;
        }
        case 'step_warn': {
          const step = steps.find(s => s.id === data.id);
          if (step) {
            step.status = 'warn'; step.msg = data.msg; step.detail = data.msg;
            if (data.pods) step.pods = data.pods;
          }
          flowStates[data.id] = 'warning';
          scrollToBottom();
          break;
        }
        case 'step_skip': {
          const step = steps.find(s => s.id === data.id);
          if (step) { step.status = 'skip'; step.msg = data.msg; }
          flowStates[data.id] = 'skipped';
          scrollToBottom();
          break;
        }

        case 'done':
          doneResult.value = data;
          isDeploying.value = false;
          stopTimer();
          nextTick(() => spawnConfetti());
          scrollToBottom();
          break;
      }
    }

    // ── SSE via GET (initial prompt) ──
    function deploy() {
      const text = prompt.value.trim();
      if (!text || isDeploying.value) return;

      resetState();
      messages.push({ type: 'user', text });
      prompt.value = '';
      isDeploying.value = true;
      showFlow.value = true;
      startTimer();
      scrollToBottom();

      if (currentES) currentES.close();
      const es = new EventSource('/api/deploy?prompt=' + encodeURIComponent(text));
      currentES = es;

      const SSE_EVENTS = ['services', 'chat', 'missing_fields', 'intent',
                          'step_start', 'step_done', 'step_warn', 'step_skip', 'done'];
      SSE_EVENTS.forEach(evt => {
        es.addEventListener(evt, e => {
          handleEvent(evt, JSON.parse(e.data), true);
          if (['chat', 'missing_fields', 'intent', 'done'].includes(evt)) es.close();
        });
      });
      es.onerror = () => { isDeploying.value = false; stopTimer(); es.close(); };
    }

    // ── SSE via POST (confirmed intent) ──
    function deployWithIntent(intentData) {
      resetState();
      isDeploying.value = true;
      showFlow.value = true;
      flowStates.ollama = 'completed';
      startTimer();

      fetch('/api/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent: intentData }),
      }).then(resp => {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function processChunk({ done, value }) {
          if (done) { isDeploying.value = false; stopTimer(); return; }
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop();
          let eventName = '';
          for (const line of lines) {
            if (line.startsWith('event: ')) eventName = line.slice(7).trim();
            else if (line.startsWith('data: ') && eventName) {
              handleEvent(eventName, JSON.parse(line.slice(6)), false);
              eventName = '';
            }
          }
          reader.read().then(processChunk);
        }
        reader.read().then(processChunk);
      }).catch(() => { isDeploying.value = false; stopTimer(); });
    }

    // ── User Actions ──
    function confirmDeploy() {
      if (!intent.value) return;
      const data = { ...intent.value };
      intentMode.value = 'hidden';
      deployWithIntent(data);
    }

    function cancelDeploy() {
      intentMode.value = 'hidden';
      showFlow.value = false;
      messages.push({ type: 'agent', text: 'Deployment cancelado. Puedes escribir un nuevo request o modificar el anterior.' });
      isDeploying.value = false;
      stopTimer();
    }

    function applyEdits() {
      const cleaned = editForm.service_name.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/^-+|-+$/g, '');
      intent.value = {
        ...intent.value,
        service_name: cleaned,
        environment: editForm.environment,
        replicas: editForm.replicas || 1,
        port: editForm.port || 8080,
        owner: editForm.owner,
      };
      intentTitle.value = 'Intent actualizado';
      intentMode.value = 'confirm';
    }

    function submitMissing() {
      let valid = true;
      missingFields.value.forEach(f => {
        if (!missingValues[f.field]?.trim()) { missingErrors[f.field] = true; valid = false; }
        else { missingErrors[f.field] = false; }
      });
      if (!valid) return;

      missingFields.value.forEach(f => {
        let val = missingValues[f.field].trim();
        if (f.field === 'service_name') val = val.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/^-+|-+$/g, '');
        intent.value[f.field] = val;
      });
      intentMode.value = 'hidden';
      deployWithIntent(intent.value);
    }

    // ── Watchers ──
    watch(intentMode, (mode) => {
      if (mode === 'edit' && intent.value) {
        Object.assign(editForm, {
          service_name: intent.value.service_name,
          environment: intent.value.environment,
          replicas: intent.value.replicas,
          port: intent.value.port,
          owner: intent.value.owner || 'backend-team',
        });
      }
    });

    // ── Confetti ──
    function spawnConfetti() {
      if (!doneRef.value) return;
      for (let i = 0; i < 30; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = Math.random() * 100 + '%';
        piece.style.top = '-10px';
        piece.style.background = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
        piece.style.animationDelay = (Math.random() * 0.5) + 's';
        piece.style.animationDuration = (1 + Math.random()) + 's';
        doneRef.value.appendChild(piece);
      }
    }

    // ── Init ──
    onMounted(() => {
      // Particles
      if (particlesRef.value) {
        for (let i = 0; i < 20; i++) {
          const p = document.createElement('div');
          p.className = 'particle';
          const size = Math.random() * 4 + 2;
          p.style.width = size + 'px'; p.style.height = size + 'px';
          p.style.left = Math.random() * 100 + '%';
          p.style.animationDuration = (Math.random() * 20 + 15) + 's';
          p.style.animationDelay = (Math.random() * 20) + 's';
          particlesRef.value.appendChild(p);
        }
      }
      // Service status
      fetch('/api/status').then(r => r.json()).then(s => {
        if (s.model) { ollamaModel.value = s.model; delete s.model; }
        Object.assign(services, s);
      }).catch(() => {});
    });

    return {
      // State
      services, ollamaModel, prompt, isDeploying, messages, showFlow, flowStates,
      intent, intentMode, intentTitle, missingFields, missingValues, missingErrors,
      editForm, steps, doneResult, timerVisible, timerDisplay,
      // Refs
      particlesRef, doneRef, chatArea, promptInput,
      // Constants
      examples: EXAMPLES, ownerOptions: OWNER_OPTIONS, flowNodes: FLOW_NODES,
      // Computed
      visibleSteps, intentFields, flowArrowLit,
      // Helpers
      renderMarkdown,
      // Actions
      deploy, confirmDeploy, cancelDeploy, applyEdits, submitMissing,
    };
  },
});

app.mount('#app');
