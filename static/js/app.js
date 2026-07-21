// MailSort AI — State Management
const state = {
    user: null,
    emails: [],
    metrics: null,
    activeTab: 'overview',
    currentFilter: {
        priority: 'all',
        category: 'all',
        query: ''
    }
};

// DOM Elements Reference
const elements = {
    navLinks: document.querySelectorAll('.sidebar-menu .menu-item'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    userName: document.getElementById('userName'),
    userAvatar: document.getElementById('userAvatar'),
    settingsUserName: document.getElementById('settings-user-name'),
    settingsUserEmail: document.getElementById('settings-user-email'),
    btnSync: document.getElementById('btnSync'),
    syncIcon: document.getElementById('syncIcon'),
    searchInput: document.getElementById('searchInput'),
    
    // Overview KPI Metrics
    metricTotal: document.getElementById('metric-total'),
    metricUrgent: document.getElementById('metric-urgent'),
    metricReply: document.getElementById('metric-reply'),
    metricReadLater: document.getElementById('metric-read-later'),
    
    // Containers
    urgentEmailsList: document.getElementById('urgent-emails-list'),
    inboxEmailsList: document.getElementById('inbox-emails-list'),
    categoryEmailsList: document.getElementById('category-emails-list'),
    categoryTabs: document.getElementById('categoryTabs'),
    
    // Filters
    priorityFilter: document.getElementById('priorityFilter'),
    sortFilter: document.getElementById('sortFilter'),
    
    // Drawer
    drawer: document.getElementById('emailDrawer'),
    drawerOverlay: document.getElementById('drawerOverlay'),
    drawerBody: document.getElementById('drawerBody'),
    btnDrawerClose: document.getElementById('btnDrawerClose'),
    
    // Settings details
    demoStatus: document.getElementById('demoStatus'),
    nlpStatus:  document.getElementById('groqStatus'),
    dbStatus:   document.getElementById('dbStatus')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // 1. Initialize Lucide icons
    lucide.createIcons();
    
    // 2. Register Sidebar Navigation Links
    elements.navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = link.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
    
    // 3. Register Event Listeners
    if (elements.btnSync) elements.btnSync.addEventListener('click', syncEmails);
    if (elements.priorityFilter) elements.priorityFilter.addEventListener('change', handleInboxFilters);
    if (elements.sortFilter) elements.sortFilter.addEventListener('change', handleInboxFilters);
    
    if (elements.btnDrawerClose) elements.btnDrawerClose.addEventListener('click', closeDrawer);
    if (elements.drawerOverlay) elements.drawerOverlay.addEventListener('click', closeDrawer);
    
    // Metric Card Click Filter Navigation
    document.querySelectorAll('.metric-card').forEach(card => {
        card.addEventListener('click', () => {
            const prio = card.getAttribute('data-filter-priority');
            switchTab('inbox');
            if (prio && elements.priorityFilter) {
                elements.priorityFilter.value = prio;
                handleInboxFilters();
            }
        });
    });
    
    // Setup Category Pills Filter Click Handlers
    if (elements.categoryTabs) {
        elements.categoryTabs.querySelectorAll('.cat-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                elements.categoryTabs.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                state.currentFilter.category = pill.getAttribute('data-category');
                renderCategoryFeed();
            });
        });
    }
    
    // Setup Search Input Debouncer
    if (elements.searchInput) {
        let debounceTimer;
        elements.searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = e.target.value.trim();
                handleSearch(query);
            }, 300);
        });
    }
    
    // 4. Load Auth Session and Dashboard Initial Data
    await checkAuthStatus();
    await loadDashboardData();
}

// Check Session Authentication Status
async function checkAuthStatus() {
    try {
        const res = await fetch('/auth/status');
        const data = await res.json();
        
        if (data.authenticated) {
            state.user = data.user;
            
            // Populate profile bar
            if (elements.userName) elements.userName.textContent = data.user.name;
            if (elements.userAvatar) elements.userAvatar.src = data.user.picture || 'https://lh3.googleusercontent.com/a/default-user=s96-c';
            
            // Populate settings profile info
            if (elements.settingsUserName) elements.settingsUserName.textContent = data.user.name;
            if (elements.settingsUserEmail) elements.settingsUserEmail.textContent = data.user.email;
        } else {
            // Not authenticated, redirect to landing login page
            window.location.href = '/';
        }
    } catch (e) {
        console.error("Auth validation request error:", e);
    }
}

// Load Dashboard Data & Metrics from API
async function loadDashboardData() {
    try {
        const res = await fetch('/api/dashboard');
        const data = await res.json();
        
        if (data.success) {
            state.metrics = data.metrics;
            state.emails = data.recent_emails;
            
            updateMetricsUI();
            renderOverviewFeed();
            renderInboxFeed();
            renderCategoryFeed();
            
            // Initialize analytics charts if active tab
            if (state.activeTab === 'analytics' && typeof loadAnalyticsData === 'function') {
                loadAnalyticsData();
            }
        }
    } catch (e) {
        console.error("Dashboard statistics loading failed:", e);
        showToast("Failed to load inbox metrics", "error");
    }
}

// Update KPI Metric Cards
function updateMetricsUI() {
    if (!state.metrics) return;
    if (elements.metricTotal) elements.metricTotal.textContent = state.metrics.total;
    if (elements.metricUrgent) elements.metricUrgent.textContent = state.metrics.urgent;
    if (elements.metricReply) elements.metricReply.textContent = state.metrics.reply_now;
    if (elements.metricReadLater) elements.metricReadLater.textContent = state.metrics.read_later;
}

// Render Simple Email Rows in Overview Highlights Card
function renderOverviewFeed() {
    if (!elements.urgentEmailsList) return;
    
    // Filter Urgent and Reply Now emails
    const priorityItems = state.emails.filter(e => e.priority === 'Urgent' || e.priority === 'Reply Now');
    
    if (priorityItems.length === 0) {
        elements.urgentEmailsList.innerHTML = `
            <div style="text-align: center; padding: 2.5rem; color: var(--text-muted); font-size: 0.95rem;">
                <i data-lucide="sparkles" style="width: 24px; height: 24px; color: var(--accent); margin-bottom: 0.5rem; display: block; margin-left: auto; margin-right: auto;"></i>
                No high-priority action items pending. You're all caught up!
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    let html = '';
    priorityItems.slice(0, 5).forEach(em => {
        const dotColor = em.priority === 'Urgent' ? '#EF4444' : '#3B82F6';
        const senderName = em.sender.split('<')[0].replace(/"/g, '').trim();
        html += `
            <div class="simple-email-row" onclick="openEmailDetails('${em.gmail_id}')">
                <div class="simple-email-left">
                    <span class="simple-email-dot" style="background-color: ${dotColor}"></span>
                    <div class="simple-email-meta">
                        <span class="simple-email-subject">${escapeHTML(em.subject)}</span>
                        <span class="simple-email-sender">${escapeHTML(senderName)}</span>
                    </div>
                </div>
                <span class="badge ${em.priority === 'Urgent' ? 'badge-urgent' : 'badge-reply'}">${em.priority}</span>
            </div>
        `;
    });
    
    elements.urgentEmailsList.innerHTML = html;
}

// Render Email Card Feed in Main Inbox Tab
function renderInboxFeed() {
    if (!elements.inboxEmailsList) return;
    
    let filtered = [...state.emails];
    
    // Apply Priority filter
    const prio = elements.priorityFilter ? elements.priorityFilter.value : 'all';
    if (prio !== 'all') {
        filtered = filtered.filter(e => e.priority === prio);
    }
    
    // Apply Sort filter
    filtered.sort((a, b) => b.created_at - a.created_at);
    
    buildEmailsListGrid(filtered, elements.inboxEmailsList);
}

// Render Email Cards in Categories Tab
function renderCategoryFeed() {
    if (!elements.categoryEmailsList) return;
    
    let filtered = [...state.emails];
    const cat = state.currentFilter.category;
    
    if (cat !== 'all') {
        filtered = filtered.filter(e => e.category === cat);
    }
    
    buildEmailsListGrid(filtered, elements.categoryEmailsList);
}

// Helper to Build Dynamic Email Cards Grid
function buildEmailsListGrid(list, container) {
    if (list.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted); background: white; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
                <i data-lucide="inbox" style="width: 40px; height: 40px; margin-bottom: 1rem; color: var(--text-light); display: block; margin-left: auto; margin-right: auto;"></i>
                <p style="font-weight: 500;">No emails match the selected filters.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    let html = '';
    list.forEach(em => {
        let badgeClass = 'badge-ignore';
        if (em.priority === 'Urgent') badgeClass = 'badge-urgent';
        else if (em.priority === 'Reply Now') badgeClass = 'badge-reply';
        else if (em.priority === 'Read Later') badgeClass = 'badge-read';
        
        const senderName = em.sender.split('<')[0].replace(/"/g, '').trim();
        const attachmentsHtml = em.attachments && em.attachments.length > 0 
            ? `<div class="email-attachments"><i data-lucide="paperclip" style="width: 14px; height: 14px;"></i> <span>${em.attachments.length} attachment(s)</span></div>`
            : '';
            
        const deadlineHtml = em.deadline 
            ? `<div class="email-deadline"><i data-lucide="calendar" style="width: 14px; height: 14px;"></i> <span>Deadline: ${escapeHTML(em.deadline)}</span></div>`
            : '';
            
        const formattedDate = formatDateString(em.created_at);
        const unreadIndicator = em.status === 'unread' ? '<span style="color:var(--primary); font-weight:bold; margin-right:6px;">●</span>' : '';
        
        html += `
            <div class="email-card" onclick="openEmailDetails('${em.gmail_id}')">
                <div class="email-card-header">
                    <span class="email-sender">${unreadIndicator}${escapeHTML(senderName)}</span>
                    <span class="email-date">${formattedDate}</span>
                </div>
                <h3 class="email-subject">${escapeHTML(em.subject)}</h3>
                <div class="email-badges-row">
                    <span class="badge ${badgeClass}">${em.priority}</span>
                    <span class="badge badge-category">${em.category}</span>
                </div>
                <p class="email-summary">${escapeHTML(em.summary || em.body.substring(0, 150) + '...')}</p>
                <div class="email-meta-footer">
                    ${attachmentsHtml}
                    ${deadlineHtml}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    lucide.createIcons();
}

// Trigger Google Gmail Ingestion Sync
async function syncEmails() {
    elements.syncIcon.classList.add('animate-spin');
    elements.btnSync.disabled = true;
    elements.btnSync.querySelector('span').textContent = 'Syncing...';
    
    const skeletons = Array(3).fill(0).map(() => `
        <div class="skeleton-card">
            <div class="skeleton-shimmer"></div>
        </div>
    `).join('');
    
    if (elements.inboxEmailsList) elements.inboxEmailsList.innerHTML = skeletons;
    if (elements.urgentEmailsList) elements.urgentEmailsList.innerHTML = skeletons;
    
    try {
        const res = await fetch('/api/fetch-emails');
        const data = await res.json();
        
        if (data.success) {
            showToast("Inbox synced successfully", "success");
            await loadDashboardData();
        } else {
            showToast("Sync failed: " + (data.details || "API Error"), "error");
        }
    } catch (e) {
        console.error("Inbox sync request error:", e);
        showToast("Server request failed", "error");
    } finally {
        elements.syncIcon.classList.remove('animate-spin');
        elements.btnSync.disabled = false;
        elements.btnSync.querySelector('span').textContent = 'Sync Inbox';
        
        renderOverviewFeed();
        renderInboxFeed();
        renderCategoryFeed();
    }
}

// Open Sliding Detail Drawer
async function openEmailDetails(gmailId) {
    elements.drawerOverlay.classList.add('active');
    elements.drawer.classList.add('active');
    elements.drawerBody.innerHTML = `
        <div style="display:flex; justify-content:center; align-items:center; height:300px; width:100%;">
            <i class="animate-spin" data-lucide="refresh-cw" style="width: 32px; height: 32px; color: var(--primary);"></i>
        </div>
    `;
    lucide.createIcons();
    
    try {
        const res = await fetch(`/api/email/${gmailId}`);
        const data = await res.json();
        
        if (data.success) {
            const em = data.email;
            
            // Mark email read in local memory list
            const memEm = state.emails.find(e => e.gmail_id === gmailId);
            if (memEm) {
                memEm.status = 'read';
                renderOverviewFeed();
                renderInboxFeed();
                renderCategoryFeed();
            }
            
            let badgeClass = 'badge-ignore';
            if (em.priority === 'Urgent') badgeClass = 'badge-urgent';
            else if (em.priority === 'Reply Now') badgeClass = 'badge-reply';
            else if (em.priority === 'Read Later') badgeClass = 'badge-read';
            
            const deadlineText = em.deadline 
                ? `<span class="badge badge-urgent">Deadline: ${escapeHTML(em.deadline)}</span>`
                : '';
                
            const replyBlockHtml = em.suggested_reply
                ? `
                    <div class="detail-section-card">
                        <div class="detail-section-title">AI Suggested Reply Template</div>
                        <textarea class="suggested-reply-box" id="replyTextarea">${escapeHTML(em.suggested_reply)}</textarea>
                        <div class="suggested-reply-actions">
                            <button class="btn btn-primary" onclick="copyReplyText()">
                                <i data-lucide="copy" style="width:14px; height:14px;"></i> Copy Reply Template
                            </button>
                        </div>
                    </div>
                  `
                : '';
                
            elements.drawerBody.innerHTML = `
                <div class="drawer-email-meta">
                    <h1>${escapeHTML(em.subject)}</h1>
                    <div class="drawer-meta-sender-date">
                        <span class="drawer-sender">From: ${escapeHTML(em.sender)}</span>
                        <span class="drawer-date">${formatDateString(em.created_at)}</span>
                    </div>
                </div>
                
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                    <div class="email-badges-row">
                        <span class="badge ${badgeClass}">${em.priority}</span>
                        <span class="badge badge-category">${em.category}</span>
                    </div>
                    ${deadlineText}
                </div>
                
                <!-- Classification Reason -->
                <div class="detail-section-card" style="border-left: 4px solid var(--primary);">
                    <div class="detail-section-title">Classification Reason</div>
                    <p style="font-size:0.925rem; line-height:1.5; color:var(--text-main);">${escapeHTML(em.reason)}</p>
                </div>

                <!-- Groq AI Executive Summary -->
                <div class="detail-section-card">
                    <div class="detail-section-title">AI Summary</div>
                    <p style="font-size:0.95rem; line-height:1.55; color:var(--text-main); font-weight:500;">${escapeHTML(em.summary)}</p>
                </div>

                <!-- Suggested Reply -->
                ${replyBlockHtml}

                <!-- Original Email Text -->
                <div class="detail-section-card">
                    <div class="detail-section-title">Original Email Body</div>
                    <div class="original-body-text">${escapeHTML(em.body)}</div>
                </div>
            `;
            lucide.createIcons();
        } else {
            showToast("Failed to fetch email details", "error");
            closeDrawer();
        }
    } catch (e) {
        console.error("Failed to load email details:", e);
        closeDrawer();
    }
}

function closeDrawer() {
    elements.drawerOverlay.classList.remove('active');
    elements.drawer.classList.remove('active');
}

// Copy AI Draft Template to Clipboard
function copyReplyText() {
    const textarea = document.getElementById('replyTextarea');
    if (!textarea) return;
    
    textarea.select();
    navigator.clipboard.writeText(textarea.value);
    showToast("Suggested reply copied to clipboard", "success");
}

// Search Query Handler
async function handleSearch(query) {
    if (!query) {
        await loadDashboardData();
        return;
    }
    
    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        
        if (data.success) {
            switchTab('inbox');
            buildEmailsListGrid(data.emails, elements.inboxEmailsList);
            showToast(`Found ${data.emails.length} matching email(s)`, "success");
        }
    } catch (e) {
        console.error("Search query error:", e);
    }
}

// Filter Trigger Handler
function handleInboxFilters() {
    renderInboxFeed();
}

// Sidebar Tab Switcher
function switchTab(tabId) {
    state.activeTab = tabId;
    
    elements.navLinks.forEach(link => {
        if (link.getAttribute('data-tab') === tabId) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
    
    elements.tabPanels.forEach(panel => {
        if (panel.id === `tab-${tabId}`) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
    
    if (tabId === 'analytics' && typeof loadAnalyticsData === 'function') {
        loadAnalyticsData();
    }
}

// Toast Notification Handler
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = type === 'success' ? 'check-circle' : 'alert-circle';
    
    toast.innerHTML = `
        <i data-lucide="${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    lucide.createIcons();
    
    setTimeout(() => toast.classList.add('show'), 50);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Date Formatter Helper
function formatDateString(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    const today = new Date();
    
    if (date.toDateString() === today.toDateString()) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// HTML Escape Helper
function escapeHTML(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Global Window Function Attachments
window.switchTab = switchTab;
window.copyReplyText = copyReplyText;
window.openEmailDetails = openEmailDetails;
