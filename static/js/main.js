/**
 * SmartDB AI Agent - Main Logic
 */

const App = {
    state: {
        isConnected: false,
        isExecuting: false,
        settings: {}
    },

    init() {
        this.loadSettings();
        this.setupEventListeners();
        this.checkStatus();
    },

    setupEventListeners() {
        // Tab Switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // DB Type Toggle
        const dbTypeSelect = document.getElementById('dbType');
        if (dbTypeSelect) {
            dbTypeSelect.addEventListener('change', () => {
                this.toggleDbSettings();
                this.saveSettings();
            });
            this.toggleDbSettings(); // run once on init
        }

        // File Input Handling
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files[0]) {
                    document.getElementById('sqliteFile').value = e.target.files[0].name;
                    this.saveSettings();
                }
            });
        }

        // Auto-save on input for other fields
        ['apiKey', 'host', 'port', 'database', 'username', 'aiModel'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('blur', () => this.saveSettings());
                el.addEventListener('input', () => this.saveSettings());
            }
        });
    },

    switchTab(tabName) {
        // Remove active class from all tabs and contents
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        // Add to current
        const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
        const content = document.getElementById(`${tabName}Tab`);

        if (btn) btn.classList.add('active');
        if (content) content.classList.add('active');
    },

    toggleDbSettings() {
        const type = document.getElementById('dbType').value;
        const sqlite = document.getElementById('sqliteSettings');
        const server = document.getElementById('serverSettings');

        if (type === 'sqlite') {
            sqlite.classList.remove('hidden');
            server.classList.add('hidden');
        } else {
            sqlite.classList.add('hidden');
            server.classList.remove('hidden');
        }
    },

    async connect() {
        this.saveSettings();
        const btn = document.getElementById('btnConnect');
        this.setLoading(btn, true, 'جاري الاتصال...');

        try {
            const data = this.getFormData();
            const res = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();

            if (result.success) {
                this.showToast('تم الاتصال بنجاح', 'success');
                this.updateStatus(true);
            } else {
                this.showToast(result.message, 'error');
                this.updateStatus(false);
            }
        } catch (e) {
            this.showToast('خطأ في الاتصال: ' + e.message, 'error');
        } finally {
            this.setLoading(btn, false, 'اتصال');
        }
    },

    async executeQuery() {
        const query = document.getElementById('queryInput').value.trim();
        if (!query) {
            this.showToast('الرجاء إدخال استعلام', 'warning');
            return;
        }

        this.saveSettings();
        const btn = document.getElementById('btnExecute');
        this.setLoading(btn, true, 'جاري المعالجة...');

        // Clear previous results
        document.getElementById('dataResults').innerHTML = '<div class="empty-state">جاري التفكير...</div>';
        document.getElementById('sqlDisplay').textContent = '-- جاري توليد SQL...';

        try {
            const aiModel = document.getElementById('aiModel').value;
            const res = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, ai_model: aiModel })
            });
            const result = await res.json();

            // Always show SQL if available
            if (result.sql_query) {
                document.getElementById('sqlDisplay').textContent = result.sql_query;
                // Highlight syntax (simple)
                // hljs.highlightElement(document.getElementById('sqlDisplay'));
            }

            if (result.success) {
                this.renderTable(result.data, result.columns);
                this.switchTab('data');
                this.showToast('تم التنفيذ بنجاح', 'success');
            } else {
                document.getElementById('dataResults').innerHTML = `
                    <div class="error-state">
                        <h3>حدث خطأ</h3>
                        <p>${result.message}</p>
                    </div>
                `;
                this.showToast(result.message, 'error');
            }

        } catch (e) {
            this.showToast('خطأ في النظام: ' + e.message, 'error');
            document.getElementById('dataResults').innerHTML = `<div class="error-state">${e.message}</div>`;
        } finally {
            this.setLoading(btn, false, 'نفذ الأمر 🚀');
        }
    },

    renderTable(data, columns) {
        if (!data || !data.length) {
            document.getElementById('dataResults').innerHTML = '<div class="empty-state">لا توجد نتائج</div>';
            return;
        }

        let html = '<div class="table-container"><table class="data-table"><thead><tr>';
        columns.forEach(col => html += `<th>${col}</th>`);
        html += '</tr></thead><tbody>';

        data.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                let val = row[col];
                if (val === null || val === undefined) val = '-';
                if (typeof val === 'object') val = JSON.stringify(val);
                html += `<td>${val}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        document.getElementById('dataResults').innerHTML = html;
    },

    setLoading(btn, isLoading, text) {
        if (isLoading) {
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-small"></span> ${text}`;
        } else {
            btn.disabled = false;
            btn.innerHTML = text;
        }
    },

    updateStatus(isConnected) {
        this.state.isConnected = isConnected;
        const badge = document.getElementById('connectionBadge');
        if (isConnected) {
            badge.className = 'status-badge status-connected';
            badge.innerHTML = '<span class="status-dot"></span> متصل';
        } else {
            badge.className = 'status-badge status-disconnected';
            badge.innerHTML = '<span class="status-dot"></span> غير متصل';
        }
    },

    showToast(msg, type = 'info') {
        // Create simple toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} fade-in`;
        toast.textContent = msg;

        // Ensure toast container exists
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position: fixed; bottom: 20px; left: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
            document.body.appendChild(container);
        }

        // Toast Styles
        toast.style.cssText = `
            padding: 12px 24px;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            font-size: 0.9rem;
            min-width: 200px;
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    getFormData() {
        const type = document.getElementById('dbType').value;
        const data = {
            api_key: document.getElementById('apiKey').value,
            db_type: type
        };

        if (type === 'sqlite') {
            data.sqlite_file = document.getElementById('sqliteFile').value;
        } else {
            data.host = document.getElementById('host').value;
            data.port = document.getElementById('port').value;
            data.database = document.getElementById('database').value;
            data.username = document.getElementById('username').value;
            data.password = document.getElementById('password').value;
        }
        return data;
    },

    saveSettings() {
        const settings = {
            apiKey: document.getElementById('apiKey').value,
            aiModel: document.getElementById('aiModel').value,
            dbType: document.getElementById('dbType').value,
            sqliteFile: document.getElementById('sqliteFile').value,
            host: document.getElementById('host').value,
            database: document.getElementById('database').value,
            username: document.getElementById('username').value
        };
        localStorage.setItem('smartDbSettings', JSON.stringify(settings));
    },

    loadSettings() {
        // Load from server first
        fetch('/api/settings')
            .then(res => res.json())
            .then(data => {
                if (data.api_key) document.getElementById('apiKey').value = data.api_key;
                if (data.db_type) {
                    document.getElementById('dbType').value = data.db_type;
                    this.toggleDbSettings();
                }
                if (data.sqlite_file) document.getElementById('sqliteFile').value = data.sqlite_file;
                if (data.ai_model) document.getElementById('aiModel').value = data.ai_model;

                // If local storage has newer data, it might override, but for now server is source of truth
                // We could merge here if needed
            })
            .catch(err => console.error('Error loading settings:', err));

        // Fallback/Legacy: LocalStorage
        const saved = localStorage.getItem('smartDbSettings');
        if (saved) {
            const s = JSON.parse(saved);
            // Only populate if empty (server fetch is async so this might race, 
            // but usually server is preferred)
            // Ideally we wait for server, but simple approach:
            if (!document.getElementById('apiKey').value && s.apiKey) document.getElementById('apiKey').value = s.apiKey;
        }
    },

    checkStatus() {
        fetch('/api/status')
            .then(r => r.json())
            .then(data => this.updateStatus(data.db_connected));
    },

    useSampleDb() {
        document.getElementById('sqliteFile').value = 'data/sample_store.db';
        this.saveSettings();
    }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => App.init());
